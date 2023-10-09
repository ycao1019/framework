@echo off
setlocal enabledelayedexpansion
set WORKING_PROJ=%1
set BUILD_DIR=%INFERENCE_BASE_DIR%/projects/%WORKING_PROJ%/build

call conda activate base
call jupyter kernelspec remove %WORKING_PROJ% -y
call conda remove --name %WORKING_PROJ% --all --yes

if exist %BUILD_DIR% (
  rem Delete the folder and all its contents
  rd /s /q %BUILD_DIR%
)