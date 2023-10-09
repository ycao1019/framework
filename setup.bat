@echo off

call conda activate base
call conda install python=3.10 ipykernel --yes
call conda install grpcio=1.43.0 -c conda-forge --yes

call pip install -e ./framework/ecsinference
call pip install -e ./framework/ecsclient
call pip install requests-auth-aws-sigv4

FOR /F "usebackq" %%i IN (`cd`) DO set replace=%%i
set "search={{DIR_NAME}}"
set "textfile=./templates/ecsml_bat_template"
set "newfile=./bin/ecsml.bat"
(for /f "delims=" %%i in (%textfile%) do (
    set "line=%%i"
    setlocal enabledelayedexpansion
    set "line=!line:%search%=%replace%!"
    echo(!line!
    endlocal
))>"%newfile%"

call mklink %CONDA_PREFIX%\\ecsml.bat %replace%\\bin\\ecsml.bat