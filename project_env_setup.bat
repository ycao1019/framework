@echo off
setlocal enabledelayedexpansion
call conda activate %1 || call :createenv %1
pip install -r %INFERENCE_BASE_DIR%/projects/%1/requirements.txt
exit /B 0

:createenv
    call conda create -n %1 --yes
    call conda activate %1
    call conda install python=3.10 ipykernel --yes
    call conda install grpcio=1.43.0 -c conda-forge --yes
    call python -m ipykernel install --user --name %1 --display-name %1

    call pip install -e %INFERENCE_BASE_DIR%/framework/ecsinference
    call pip install -e %INFERENCE_BASE_DIR%/framework/ecsclient
    call pip install requests-auth-aws-sigv4
    exit /B 0
