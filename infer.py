import mlflow
from mlflow.tracking.client import MlflowClient

import os
import sys
import shutil
import timeout_decorator
from datetime import datetime
import json
import ecs.utils as utils
import ecs
import docker
from sys import platform

def conditional_timeout(seconds, is_windows):
    def decorator(func):
        if is_windows:
            # Return the function unchanged, not decorated.
            return func
        return timeout_decorator.timeout(seconds)(func)
    return decorator


class InferenceBuild():
    '''
    Make sure 3 env vars are already injected through cli: 
        WORKING_PROJECT
        INFERENCE_BASE_DIR
        MLFLOW_TRACKING_URL
    '''

    def __init__(self):
        self.project_name = os.environ['WORKING_PROJECT']
        self.base_dir = os.environ['INFERENCE_BASE_DIR']
        self.project_dir = os.path.join(self.base_dir, f'projects/{self.project_name}')
        self.mlflow_url = os.environ["MLFLOW_TRACKING_URL"]
        self.model_dir = os.path.join(self.project_dir , 'mlflow_model')
        self.custom_code_path = os.path.join(self.project_dir, 'src')
        self.model_uri = None
        self.model_version = None
        self.validate_project()
        if os.path.exists(self.custom_code_path):
            sys.path.append(self.custom_code_path)


    @conditional_timeout(10, platform.startswith('win'))
    def init_mlfow_experiment(self):
        print(f"Connecting to mlflow server: {self.mlflow_url}")
        mlflow.set_tracking_uri(self.mlflow_url)
        print("Mlflow server connected")
        mlflow.set_experiment(f"/Users/{os.getlogin()}/{self.project_name}")
        self.client = MlflowClient()
    
    
    def validate_project(self):
        assert utils.is_folder(self.project_dir), f"Project directory, '{self.project_dir}', needs to exist"
        assert utils.is_folder(self.custom_code_path), f"src folder, '{self.custom_code_path}', needs to exist"
        assert utils.is_file(os.path.join(self.custom_code_path, "application.py")), "application.py is missing"
        try:
            self.init_mlfow_experiment()
        except Exception as e:
            print(e)
            print(f"Connection timeout; failed to connect to mlflow server.")
            sys.exit(1)
    

    def create_artifacts(self, local=True):
        from application import Application
        app = Application()
        code_dependencies = os.listdir(self.custom_code_path)
        if '__pycache__' in code_dependencies:
            code_dependencies.remove('__pycache__')
        if code_dependencies:
            code_dependencies = [os.path.join(self.custom_code_path, e) for e in code_dependencies]
        if local:
            artifacts={'manifest':f"{self.project_dir}/manifest.json", 'test_data': f"{self.project_dir}/tests", 'models': f"{self.project_dir}/models"}
        else:
            # compress models folder
            utils.dir_compress(f"{self.project_dir}/models", f"{self.project_dir}/build/models")
            utils.file_split(f"{self.project_dir}/build/models.zip", f"{self.project_dir}/build/fragments")
            os.remove(f"{self.project_dir}/build/models.zip")
            artifacts={'manifest':f"{self.project_dir}/manifest.json", 'test_data': f"{self.project_dir}/tests", 'model_fragments': f"{self.project_dir}/build/fragments"}
        return artifacts, app, code_dependencies


    def save_model(self):
        if utils.is_folder(self.model_dir):
            utils.delete_folder(self.model_dir)
        artifacts, app, code_dependencies = self.create_artifacts(local=True)
        #save artifacts locally
        mlflow.pyfunc.save_model(path=self.model_dir, python_model=app, artifacts=artifacts, code_path=code_dependencies if code_dependencies else None)


    def log_model(self, register=False):
        artifacts, app, code_dependencies = self.create_artifacts(local=False)
        if register:
            model_info = mlflow.pyfunc.log_model(artifact_path=self.project_name
                        , python_model=app 
                        , artifacts=artifacts
                        , code_path=code_dependencies if code_dependencies else None
                        ,registered_model_name=self.project_name
                        )
        else:
            model_info = mlflow.pyfunc.log_model(artifact_path=self.project_name
                        , python_model=app 
                        , artifacts=artifacts
                        , code_path=code_dependencies if code_dependencies else None
                        )
        self.model_uri = model_info.model_uri
        if register:
            registered_model = self.client.get_registered_model(self.project_name)
            self.model_version = registered_model.latest_versions[0].version

    def register_model(self):
        if not self.model_uri:
            self.log_model(register=True)
            registered_model = self.client.get_registered_model(self.project_name)
            self.model_version = registered_model.latest_versions[0].version
        else:
            mv = mlflow.register_model(self.model_uri, self.project_name)
            self.model_version = mv.version

    def get_model_version(self):
        registered_model = self.client.get_registered_model(self.project_name)
        self.model_version = registered_model.latest_versions[0].version
        return self.model_version

    def list_registered_models(self):
        return [rm.name for rm in self.client.search_registered_models()]


    def prepare_image(self):
        assert self.model_version, "You need to register your model before preparing the image"
        local_docker = os.path.join(self.base_dir, 'templates', 'Dockerfile-template-local')
        cloud_docker = os.path.join(self.base_dir, 'templates', 'Dockerfile-template-cloud')
        assert os.path.exists(local_docker), "Dockerfile-template-local file is missing"
        assert os.path.exists(cloud_docker), "Dockerfile-template-cloud file is missing"
        docker_path = f'{self.project_dir}/docker/'
        if os.path.exists(docker_path):
            shutil.rmtree(docker_path)
        os.makedirs(docker_path)
        manifest = utils.load_manifest(os.path.join(self.project_dir, 'manifest.json'))
        env_str = ''
        if manifest.deploy_config.env_vars:
            for k,v in manifest.deploy_config.env_vars.items():
                env_str += f'ENV {k}={v}\n'

        replace_dict = {}
        replace_dict["{{MLFLOW_URL}}"] = self.mlflow_url
        replace_dict["{{MODEL_NAME}}"] = self.project_name
        replace_dict["{{MODEL_VERSION}}"] = self.model_version
        replace_dict["{{ENV_VARIABLES}}"] = env_str
        utils.replace_strings_in_file(local_docker,replace_dict, os.path.join(self.project_dir, 'docker/Dockerfile_local'))
        utils.replace_strings_in_file(cloud_docker,replace_dict, os.path.join(self.project_dir, 'docker/Dockerfile'))

        image_name = f'ml-inference-{self.project_name}-dstar'
        image_name = image_name.replace('_','-')
        image_info = {
            "project_name": self.project_name,
            "image_name": image_name,
            "image_version": self.model_version,
            "framework_version": ecs.__version__,
            "creation_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "author": os.getlogin(),
            "success": False
        }

        json_object = json.dumps(image_info, indent=4)
        with open(os.path.join(self.project_dir, 'model-image-info.json'), "w") as target:
            target.write(json_object)


    def build_image(self, force=False):
            docker_client = docker.from_env()
            build_path = None
            import subprocess
            if force or not docker_client.images.list(name='ray_base'):
                print('-------------------------------------------')
                print('Start building ray_base image....')
                build_path = os.path.join(self.base_dir, 'base-image')
                cmd_ray_base = ['docker', 'build', '-f', os.path.join(build_path, 'Dockerfile_ray_base'), '-t', 'ray_base', build_path]
                subprocess.run(cmd_ray_base)
                print('ray_base image is built')
                print('-------------------------------------------')
            if force or not docker_client.images.list(name='ray_inference'):
                print('-------------------------------------------')
                print('Start building ray_inference image....')
                cmd_ray_inference = ['docker', 'build', '-f', os.path.join(self.base_dir, 'base-image','Dockerfile_ray_inference'), '-t', 'ray_inference', self.base_dir]
                subprocess.run(cmd_ray_inference)
                print('ray_inference image is built')
                print('-------------------------------------------')
            image_name = f"ml-inference-{os.environ['WORKING_PROJECT']}"
            print('-------------------------------------------')
            print(f'Start building {image_name} image....')
            build_path = os.path.join(self.project_dir, 'docker')
            cmd_local = ['docker', 'build', '-f', os.path.join(build_path, 'Dockerfile_local'), '-t', image_name, build_path]
            subprocess.run(cmd_local)
            print(f'{image_name} image is built')
            print('-------------------------------------------')

