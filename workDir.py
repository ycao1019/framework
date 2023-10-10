import os
import json
import re
import shutil
import subprocess
import docker
from ecsclient.cli.clitoolbox import cliUtil
from git import Repo
from ecs.utils import is_file, load_json
from ecsclient.cli.imageinfo import ImageInfo
try: 
    from ecsclient.buildtools.infer import InferenceBuild
except ImportError:
    print ("")  
    print ("ERROR: MiSSING PYTHON PACKAGES!  It seems that certain python packages may not be installed.")  
    print ("please navigate to the root folder of the project and run 'pip install -e ./inference_framework'")  
    os._exit(0)          

try: 
    from termcolor import *
    import colorama
    import yaml
except ImportError:
    print ("ERROR: MiSSING PYTHON PACKAGES! it seems that certain python packages may not be installed.")  
    print ("please run 'pip install -r cli_requirements.txt' before running this application")  
    os._exit(0)      

ct = cliUtil()
"""
        print_parm = '''
        {
            "printlevel": 4,
            "printfloder": "n",
            "printcomment": "y",
            "printline": "y",            
            "projectid": "",
            "key": "",
            "value": "",            
            "action": "newproject"            
        }
        '''
        print_parm = '''
        {
            "printlevel": 1,
            "printfloder": "y",
            "printcomment": "n",
            "printline": "n",
            "projectid": ""
        }
        '''
"""


class workSpace:
    def __init__(self):
        colorama.init()
        self.projects_json = {"projects": {}}
        self.projects_name = {"projects_ID": {}}
        self.p_name = ""
        self.alert_msg = colored("***", "red")
        self.alert_words = colored("Invalid input. ", "light_cyan")
        self.alert_projectname_error1 = colored("Project names can only contain alphanumeric characters, '-', or '_' ", "light_cyan")
        self.alert_projectname_error2 = colored("Project name {0} has been used.", "light_cyan")
        self.project_name_msg = None
        self.file_tree = None
        self.test_ct = 0
        self.printfolder = 'y'
        projects = "projects"
        self.root = os.environ['INFERENCE_BASE_DIR']
        self.projects_home = os.path.join(self.root, projects)
        self.template_dir = os.path.join(self.root, "templates")
        self.code_path = os.path.dirname(os.path.abspath(__file__))
        self.project_id = self.get_working_proj()
        self.project_dir = os.path.join(self.projects_home, self.project_id)
        self.invalid_msg = ct.color_red("Invalid input! ")
        self.repo = None
        try:
            self.repo = Repo(self.root)
        except :
            print("Not a valid git repo") 
    
    def showstatus(self):
        # self.clear_screen()

        p_line =  ct.color_blue("-" * 70)
        print (p_line)
        print ("")
        print (" Please bear with us as we work on completing the status function" )
        print ("")
        print (p_line)
        return
    
    def list_project(self):

        print_parm = '''
        {
            "printlevel": 1,
            "printfloder": "y",
            "printcomment": "n",
            "printline": "n",
            "projectid": ""
        }
        '''
        # Convert JSON string to a Python dictionary
        p_parm = json.loads(print_parm)
        p_parm["projectid"] = self.project_id
        projects_json = {"projects": {}}
        self.file_tree = ct.generate_json(self.projects_home)
        projects_json["projects"] = self.get_projects_key(self.file_tree, "projects")
        json_data = json.dumps(projects_json, indent=4)

        project_dict = ct.print_directory_tree(json_data, p_parm)

        print("")
        print(ct.color_blue("Here is a list of existing projects in your local ML framework"))
        
        projects_json = {"projects": {}}
        self.file_tree = ct.generate_json(self.projects_home)
        projects_json["projects"] = self.get_projects_key(self.file_tree, "projects")
        json_data = json.dumps(projects_json, indent=4)
        project_dict = ct.print_directory_tree(json_data, p_parm)
        
        self.print_list(project_dict, self.project_id)

     
    def get_projects_key(self, json_data, root_key):
        for key, value in json_data.items():
            if key.endswith(root_key):
                return value
            elif isinstance(value, dict):
                result = self.get_projects_key(value, root_key)
                if result:
                    return result
        return None        

    
    def current_project(self):
        print(self.project_id)


    def switchproject(self, project_id): 

        print_parm = '''
        {
            "printlevel": 1,
            "printfloder": "y",
            "printcomment": "n",
            "printline": "n",
            "projectid": ""
        }
        '''

        # Convert JSON string to a Python dictionary
        p_parm = json.loads(print_parm)
        p_parm["projectid"] = self.project_id
        current_project_id = self.project_id
        projects_json = {"projects": {}}
        self.file_tree = ct.generate_json(self.projects_home)
        projects_json["projects"] = self.get_projects_key(self.file_tree, "projects")
        json_data = json.dumps(projects_json, indent=4)
        project_dict = ct.print_directory_tree(json_data, p_parm)

        if project_id == "" or project_id is None:
            print("")
            print(ct.color_blue("Here is a list of existing projects in your local ML framework"))
        
            projects_json = {"projects": {}}
            self.file_tree = ct.generate_json(self.projects_home)
            projects_json["projects"] = self.get_projects_key(self.file_tree, "projects")
            json_data = json.dumps(projects_json, indent=4)
            project_dict = ct.print_directory_tree(json_data, p_parm)
        
            selection_number, project_d = self.generate_select_menu(project_dict, current_project_id)
            destination_project = project_d[str(selection_number)]
        else:
            if project_id == current_project_id:
                print("")
                print("The project ID {} entered matches the current project. No project switch was performed.".format(ct.color_red('"'+project_id+'"')))
                return
            
            if not self.find_project(project_dict, project_id):
                print("")
                print("The entered project ID {} does not match any local projects. No project switch was performed.".format(ct.color_red('"'+project_id+'"')))
                return
            else:
                destination_project = project_id
            
        
        # self.move_project_files(destination_project, current_project_id)
        
        self.set_working_proj(destination_project)

        from_p = ct.color_cyan(current_project_id)
        to_p = ct.color_cyan(destination_project)

        print(" ")
        print(" You've successfully switch to project {}.".format(to_p))
        return True
    


    def move_project_files(self, toProject, fromProject):

        # first backup working space ipynb files to 'fromproject'
        source_folder = self.root
        destination_folder = self.root + "/projects/" + fromProject + "/scripts"
        # destination_folder = "path/to/destination/folder"
        extension = ".ipynb"

        # Get a list of files in the source folder
        files = os.listdir(source_folder)

        # Iterate over the files and copy the ones with the specified extension
        for file in files:
            if file.endswith(extension):
                source_path = os.path.join(source_folder, file)
                destination_path = os.path.join(destination_folder, file)
                shutil.copyfile(source_path, destination_path)

        # switch the source and destination folder

        source_folder = self.root + "/projects/" + toProject + "/scripts"
        destination_folder = self.root

        # Get a list of files in the source folder
        if os.path.exists(source_folder) and os.path.isdir(source_folder):
            files = os.listdir(source_folder)
        else:
            os.mkdir(source_folder)
            files = os.listdir(source_folder)

        # Iterate over the files and copy the ones with the specified extension
        for file in files:
            if file.endswith(extension):
                source_path = os.path.join(source_folder, file)
                destination_path = os.path.join(destination_folder, file)
                shutil.copyfile(source_path, destination_path)

    def print_menu(self, menu_message, options, input_msg):
        """Prints a CLI menu with the given message and options."""
        line_width = 70
        option_width = 8
        description_width = line_width - option_width - 2  # Subtract 2 for spacing
        line_separator = ct.color_blue("-" * line_width)
        print(line_separator)
        print(menu_message.center(line_width))
        print(line_separator)
        for index, option in enumerate(options, start=1):
            name, description = option
            option_text = f"{index}. {name}"
            formatted_option = f"{option_text:{option_width}}"
            formatted_description = f"{description:{description_width}}"
            print(f"{formatted_option} {formatted_description}")
        print(line_separator)
        print()

        user_input = input(input_msg)
        while user_input.lower() not in ['c', 'q']:
            print("")
            print(self.invalid_msg)
            user_input = input(input_msg )

        userinput = user_input.lower()
        if userinput == 'q':
            print("Exiting...")
            # Add any additional 
        return userinput
    
    
    def find_project(self, data, match_value):

        for key, value in data.items():
            if value == match_value:
                return True

        return False

    
    def print_list(self, data, match_value):
        max_width = max(len(value) for value in data.values())
        options = []
        selection_numbers = []
        count = 1
        json_output = {}        
        for key, value in data.items():
            if value == match_value:
                msg = ct.color_cyan("current working project")
                options.append(f"    {value.ljust(max_width)} -------- {msg}".format(msg))
            else:
                countstr = ct.color_cyan( str(count) )
                options.append(f"    {value.ljust(max_width)} -------- {countstr}".format(countstr))
                selection_numbers.append(count)
                json_output[str(count)] = value
                count += 1        
        dash_line = '-' * (max_width + 38)
        dash_line = ct.color_cyan(dash_line)
        menu = '\n'.join(options)
        print(f"\n    {dash_line}\n{menu}\n    {dash_line}")

    
    def generate_select_menu(self, data, match_value):
        max_width = max(len(value) for value in data.values())
        options = []
        selection_numbers = []
        count = 1
        json_output = {}

        for key, value in data.items():
            if value == match_value:
                msg = ct.color_cyan("in the current working space")
                options.append(f"    {value.ljust(max_width)} -------- {msg}".format(msg))
            else:
                countstr = ct.color_cyan( str(count) )
                options.append(f"    {value.ljust(max_width)} -------- {countstr}".format(countstr))
                selection_numbers.append(count)
                json_output[str(count)] = value
                count += 1

        dash_line = '-' * (max_width + 38)
        dash_line = ct.color_cyan(dash_line)
        menu = '\n'.join(options)
        print(f"\n    {dash_line}\n{menu}\n    {dash_line}")
        first = str(selection_numbers[0])
        last  = str(selection_numbers[-1])

        sel = ct.color_cyan("(" + str(first) + "-" + str(last) + ")")
        q = ct.color_cyan("'" + "q" + "'")

        print(" ")

        while True:
            selection = input(" Enter the number associated with the project you wish to switch to {}, or enter {} to exit: ".format(sel, q))
            if selection.isdigit() and 1 <= int(selection) <= len(selection_numbers):
                selected_project = selection_numbers[int(selection) - 1]
                break
            elif selection.lower() == "q":
                selected_project = 'q'
                os._exit(0)
            else:
                print(" ")
                print(" {}".format(ct.color_red("Invalid input!")))

        return selected_project, json_output


    def getPorjects(self): 

        print_parm = '''
        {
            "printlevel": 1,
            "printfloder": "y",
            "printcomment": "n",
            "printline": "y",
            "projectid": ""            
        }
        '''
        # Convert JSON string to a Python dictionary
        p_parm = json.loads(print_parm)
        p_parm["projectid"] = self.project_id        
        
        print("")
        print(" Below is a list of existing projects in your local ML framework")
        projects_json = {"projects": {}}

        self.file_tree = ct.generate_json(self.projects_home)
        projects_json["projects"] = self.get_projects_key(self.file_tree, "projects")
        json_data = json.dumps(projects_json, indent=4)

        project_dict = ct.print_directory_tree(json_data, p_parm)
        return project_dict

    def clear_screen(self):
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")


    def is_a_valid_projectname(self, newprojname, project_json):
        p = r'^[a-zA-Z0-9_-]+$'
        # check the p with name
        # pattern_match(name)
        
        if newprojname is None:
            return True

        if not re.match(p, newprojname):
            self.project_name_msg = self.alert_projectname_error1
            return False
        
        for kay, value in project_json.items():
            if value == newprojname:
                self.project_name_msg = self.alert_projectname_error2.format(ct.color_red(newprojname))
                return False
        return True


    def new_project(self, project_id):
        print_parm = '''
        {
            "printlevel": 4,
            "printfloder": "n",
            "printcomment": "y",
            "printline": "y",            
            "projectid": "",
            "key": "",
            "value": "",            
            "action": "newproject"            
        }
        '''

        # Convert JSON string to a Python dictionary
        p_parm = json.loads(print_parm)
        p_parm["projectid"]  = self.project_id


        # self.clear_screen()
        project_json = self.getPorjects()  # parameter 1 show only first level of directory structure
        # exit(0)

        while True:
            if project_id == "" or project_id is None:
                project_id = input(" please enter {0}. To exit, simply type {1}. ".format(ct.color_cyan('new project name'), ct.color_cyan('q')))

            try:
                if project_id == 'q':
                    os._exit(0)
                if not self.is_a_valid_projectname(project_id, project_json):
                    print(self.alert_msg)
                    print(self.project_name_msg)
                    project_id = ""
                else:
                    break
            except ValueError:
                print(self.alert_words )        

        print("Initializing project ...")

        rootpath = self.project_dir
        self.project_id = project_id
        project_models = rootpath + "/models"
        project_src = rootpath + "/src"
        project_tests =  rootpath +  "/tests"

        os.makedirs(project_models)
        os.makedirs(project_src)
        os.makedirs(project_tests)
        
        manifest_template = self.template_dir + "/manifest_template.json"
        
        project_manifest_file = rootpath + "/manifest.json"
        
        shutil.copytree(f'{self.template_dir}/scripts', rootpath, dirs_exist_ok=True)
        shutil.copytree(f'{self.template_dir}/src', project_src, dirs_exist_ok=True)
        shutil.copy (manifest_template, project_manifest_file)
        

        # create an empty requirements.txt
        open(f"{rootpath}/requirements.txt", "x")
       
        with open(project_manifest_file, 'r') as mj:
            template = mj.read()
            template = template.replace('{{project_name}}', project_id)
        with open(project_manifest_file, "w") as target:
            target.write(template)

        # set working project to the current
        self.set_working_proj(project_id)

        # install conda env
        print(f"\ninstall conda env with name '{project_id}'")
        command = [f'. $CONDA_PREFIX/etc/profile.d/conda.sh && source {self.root}/bin/project_env_setup.sh {project_id}'] 
        subprocess.run(command, shell=True)

        self.clear_screen()
        print("You've successfully created a new project ID {0} and set up the associated folders.".format(ct.color_cyan("'" + project_id + "'")))
        print("Here is the {0} below:".format(ct.color_cyan("'to-do list'")))
        print(" ")

        projects_json = {"projects": {}}
        self.file_tree = ct.generate_json(self.projects_home)
        projects_name = {project_id: {}}
        projects_name[project_id] = self.get_projects_key(self.file_tree, project_id)
        projects_json["projects"] = projects_name
        proj_json = json.dumps(projects_json)

        # print(proj_json)
        dummy = ct.print_directory_tree(proj_json, p_parm)
        
        return


    def read_help_json(self):
        with open( os.path.join(self.code_path, 'help.json'), 'r') as f:
            data = json.load(f)
        return data
    

    def print_help(self):
        print("")
        usage = colored("Usage: ", "light_cyan")
        print(usage + "python artifact_mgr.py SUBCOMMAND [ARGS]...")

        leftb  = colored("[", "red") 
        rightb = colored("]", "red")     
        four_blank = " " * 4
        
        data = self.read_help_json()        

        for firstlevel, secondlevel in data.items():
            print(" ")
            ctext = colored(firstlevel, "red")   
            print(leftb + ctext + rightb)
            for key, value in secondlevel.items():
                k_len = len(key)
                suffix = " " * (23 - k_len)
                ctext = colored(key, "light_cyan")   
                print(four_blank + ctext + suffix + value)


    def install_requirements(self, name):
        if name is not None:
            if name != 'force':
                print("")
                print("The entered argument {} for subcommand is invalid.".format(ct.color_red('"'+name+'"')))
                return
        else: 
            menu_message = colored("Menu Function: install dependencies", "light_cyan" )
            input_msg = "Please enter {0} to confirm and continue or {1} to exit: ".format(ct.color_cyan("'c'"), ct.color_cyan("'q'"))
            menu_options = [
                ('The current working project:  ',  ct.color_cyan(self.project_id))]
        
            self.clear_screen()
            returnmsg = self.print_menu(menu_message, menu_options,input_msg )

            if returnmsg != 'c':
                return

        os.environ['INFERENCE_BASE_DIR'] = os.path.abspath(self.root)        
    
        command = [f'. $CONDA_PREFIX/etc/profile.d/conda.sh && source {self.root}/bin/project_env_setup.sh {self.project_id}'] 
        subprocess.run(command, shell=True)



    def test_applicationpy(self, name):
        if self.working_project_absent_warning():
            return

        import pytest

        if name is not None:
            if name != 'force' and name != 'save':
                print("")
                print("The entered argument {} for subcommand is invalid.".format(ct.color_red('"'+name+'"')))
                return
        else: 
            return_items, code = ct.check_artifacts(self.project_id, self.root)
            menu_message = colored("Menu Function: Unit test on application.py", "light_cyan" )
            input_msg = "Please enter {0} to confirm and continue or {1} to exit: ".format(ct.color_cyan("'c'"), ct.color_cyan("'q'"))
            menu_options = [
                ('The current working project:  ',  ct.color_cyan(self.project_id)),
                ('application.py folder:        ',  ct.color_cyan("./projects/" + self.project_id + "/src/application.py"  ))]
        
            if code != 0:
                for key, value in return_items.items():
                    menu_options.append(( key, ct.color_red(value))) 
                    input_msg = "Please enter {0} to  exit: ".format(ct.color_cyan("'q'"))

            self.clear_screen()
            returnmsg = self.print_menu(menu_message, menu_options,input_msg )

            if returnmsg != 'c':
                return

        os.environ['WORKING_PROJECT'] = self.project_id
        # os.environ['INFERENCE_BASE_DIR'] = os.path.abspath('.')
        os.environ['INFERENCE_BASE_DIR'] = os.path.abspath(self.root)        
    
        command = ['pytest', self.root + '/tests/test_application.py'] 
        if name == 'save':
            command = ['pytest', self.root + '/tests/test_application.py', '--save', 'y']
        subprocess.run(command)
        # result = subprocess.run(command, capture_output=True, text=True)
        # print(result)
    
    def register_model(self, name):
        if self.working_project_absent_warning():
            return
            
        if name is not None:
            if name != 'force':
                print("")
                print("The entered argument {} for subcommand is invalid.".format(ct.color_red('"'+name+'"')))
                return
        else: 
            menu_message = colored("Menu Function:  Log and Register model", "light_cyan" )
            input_msg = "Please enter {0} to confirm or {1} to exit: ".format(ct.color_cyan("'c'"), ct.color_cyan("'q'"))
            menu_options = [
                ('The current working project:           ',  ct.color_cyan(self.project_id)),
                ('manifest.json has been updated:        ',  ct.color_cyan("./projects/" + self.project_id + "/manifest.json")),
                ('The model artifacts are in the folder: ',  ct.color_cyan("./projects/" + self.project_id + "/model" ))            
                ]
        
            self.clear_screen()
            returnmsg = self.print_menu(menu_message, menu_options,input_msg )

            if returnmsg != 'c':
                return

        os.environ['WORKING_PROJECT'] = self.project_id
        os.environ['INFERENCE_BASE_DIR'] = os.path.abspath(self.root)        
        with open(self.root + "/global-config.yml", 'r') as f:
            global_settings = yaml.safe_load(f)
            os.environ['MLFLOW_TRACKING_URL'] = global_settings['mlflow_url']

        inference_build = InferenceBuild()
        inference_build.log_model(register = True)
    
    def image_scan(self, name):
        if self.working_project_absent_warning():
            return
            
        # check if docker is up
        try:
            docker_client = docker.from_env()
        except:
            print(ct.color_red("Please start Docker Desktop before building the image!"))
            return
        
        if name is not None:
            if name != 'force':
                print("")
                print("The entered argument {} for subcommand is invalid.".format(ct.color_red('"'+name+'"')))
                return
        else: 
            menu_message = colored("Menu Function:  Local Image Testing & Vulnerability Scan", "light_cyan" )
            input_msg = "Please enter {0} to confirm or {1} to exit: ".format(ct.color_cyan("'c'"), ct.color_cyan("'q'"))
            menu_options = [
                ('The current working project:           ',  ct.color_cyan(self.project_id)),
                ('manifest.json has been updated:        ',  ct.color_cyan("./projects/" + self.project_id + "/manifest.json")),
                ('The model artifacts are in the folder: ',  ct.color_cyan("./projects/" + self.project_id + "/model" )),
                ('Docker Desktop:                        ',  ct.color_cyan("is installed and running" )),            
                ('Prerequisite:                          ',  ct.color_cyan("Successful 'builimage' subcommand completion." )) 
                ]
        
        # self.clear_screen()
            returnmsg = self.print_menu(menu_message, menu_options,input_msg )

            if returnmsg != 'c':
                return

        command = ['docker','run','-v', '/var/run/docker.sock:/var/run/docker.sock', 'aquasec/trivy', 'image', '--security-checks', 'vuln','--timeout', '30m', '' + "ml-inference-" + self.project_id + '' ] 
        # docker run -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --security-checks vuln --timeout 15m ml-inference-{os.environ['WORKING_PROJECT']}
        path = self.root
        subprocess.run(command, cwd=path)
        return

    
    def build_image(self, name):
        if self.working_project_absent_warning():
            return
            
        os.environ['WORKING_PROJECT'] = self.project_id
        os.environ['INFERENCE_BASE_DIR'] = os.path.abspath(self.root)        
        with open(self.root + "/global-config.yml", 'r') as f:
            global_settings = yaml.safe_load(f)
            os.environ['MLFLOW_TRACKING_URL'] = global_settings['mlflow_url']

        inference_build = InferenceBuild()
        # get the latest version of the registered model
        try:
            model_version = inference_build.get_model_version()
        except Exception as error:
            print(ct.color_red(error))
            return
        # check if docker is up
        try:
            docker_client = docker.from_env()
        except:
            print(ct.color_red("Please start Docker Desktop before building the image!"))
            return
        
        if name is not None:
            if name != 'force':
                print("")
                print("The entered argument {} for subcommand is invalid.".format(ct.color_red('"'+name+'"')))
                return
        else: 
            menu_message = colored("Menu Function:  Prepare Dockerfile & Build Image", "light_cyan" )
            input_msg = "Please enter {0} to confirm or {1} to exit: ".format(ct.color_cyan("'c'"), ct.color_cyan("'q'"))
            menu_options = [
                ('The current working project:           ',  ct.color_cyan(self.project_id)),
                ('Registered model version:              ',  ct.color_cyan(model_version)),
                ('manifest.json has been updated:        ',  ct.color_cyan("./projects/" + self.project_id + "/manifest.json")),
                ('The model artifacts are in the folder: ',  ct.color_cyan("./projects/" + self.project_id + "/model" )),
                ('Docker Desktop :                       ',  ct.color_cyan("is installed and running" ))            
                ]
        
            returnmsg = self.print_menu(menu_message, menu_options,input_msg )

            if returnmsg != 'c':
                return

        # result = subprocess.run(command, capture_output=True, text=True)
      
        inference_build.prepare_image()

        build_path = None
        
        build_path = os.path.join(self.root, 'base-image')

        if name == 'force' or not docker_client.images.list(name='ray_base'):
            print('-------------------------------------------')
            print('Start building ray_base image....')
            build_path = os.path.join(self.root, 'base-image')
            cmd_ray_base = ['docker', 'build', '-f', os.path.join(build_path, 'Dockerfile_ray_base'), '-t', 'ray_base', build_path]
            subprocess.run(cmd_ray_base)
            print('ray_base image is built')
            print('-------------------------------------------')
        if name == 'force' or not docker_client.images.list(name='ray_inference'):
            print('-------------------------------------------')
            print('Start building ray_inference image....')
            cmd_ray_inference = ['docker', 'build', '-f', os.path.join(self.root, 'base-image','Dockerfile_ray_inference'), '-t', 'ray_inference', self.root]
            subprocess.run(cmd_ray_inference)
            print('ray_inference image is built')
            print('-------------------------------------------')
        image_name = f"ml-inference-{os.environ['WORKING_PROJECT']}"

        print('-------------------------------------------')
        print(f'Start building {image_name} image....')
        build_path = os.path.join(self.projects_home,  self.project_id, 'docker')
        cmd_local = ['docker', 'build', '-f', os.path.join(build_path, 'Dockerfile_local'), '-t', image_name, build_path]
        complete_process = subprocess.run(cmd_local)
        if complete_process.returncode != 0:
            print(ct.color_red(f'Failed to build {image_name} image'))
        else:
            image_info = load_json(os.path.join(self.project_dir, "model-image-info.json"))
            image_info['success'] = True
            with open(os.path.join(self.project_dir, "model-image-info.json"), "w") as f:
                json.dump(image_info, f, indent=4)
            print(f'{image_name} image is built')
        print('-------------------------------------------')   


    def commit(self, name):
        if self.working_project_absent_warning():
            return
            
        image_json_file = os.path.join(self.project_dir, 'model-image-info.json')
        if not is_file(image_json_file):
            print(f'You need to build the image first using {ct.color_cyan("ecsml imagebuild")}')
            return
        image_info = ImageInfo(**load_json(image_json_file))
        if not image_info.success:
            print(f'You need to successfully build the image using {ct.color_cyan("ecsml imagebuild")}')
            print(f'If you tried to build the image and it failed due to some reason, please solve it and try again')
            return
        menu_message = colored("Menu Function:  Commit your project to github", "light_cyan" )
        input_msg = "Please enter {0} to confirm or {1} to exit: ".format(ct.color_cyan("'c'"), ct.color_cyan("'q'"))
        branch_name = f'model-{self.project_id}-v{image_info.image_version}'
        menu_options = [
                ('The current working project:          ',  ct.color_cyan(self.project_id)),
                ('Registered model version:             ',  ct.color_cyan(image_info.image_version)),  
                ('Git branch to commit:                 ',  ct.color_cyan(branch_name)),     
                ('The image to be created in ECR:       ',  ct.color_cyan(f'{image_info.image_name}:{image_info.image_version}'))      
                ]
        
        returnmsg = self.print_menu(menu_message, menu_options,input_msg )
        if returnmsg != 'c':
            return

        # todo: check if the project is already in the repo

        git, idx = self.repo.git, self.repo.index
        if branch_name not in self.repo.branches:
            git.branch(branch_name)
        git.checkout(branch_name)
        image_file_target_path = os.path.join(self.projects_home, 'model-image-info.json')
        shutil.copyfile(image_json_file, image_file_target_path)
        idx.add(image_file_target_path)
        idx.add(self.project_dir)
        idx.commit(f"Build inference image for model={image_info.image_name}, version={image_info.image_version}" )
        origin = self.repo.remote("origin")
        git.push("--set-upstream", origin, self.repo.head.ref)
        print(f'Now your current local branch is  {ct.color_cyan(branch_name)}.')
        print(f'Please go to  {ct.color_cyan(origin.url[:-4])} to create a pull request')
        print(f'After the pull request is approved and codes are merged, you can usg git commands to switch to main branch and pull the latest codes')


    def get_working_proj(self):
        file_path = os.path.join(self.projects_home, '.current')
        if not os.path.isfile(file_path):
            open(file_path, "x")
            return ""
        else:
            with open(file_path, 'r') as f:
                return f.read()


    def set_working_proj(self, project_name):
        file_path = os.path.join(self.projects_home, '.current')
        with open(file_path, "w+") as f:
            f.write(project_name)


    def working_project_absent_warning(self):
        if not self.get_working_proj():
            print(ct.color_red("You have not select a project to work on; use 'ecsml switch' command to select one!"))
            return True
        return False