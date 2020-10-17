@echo off
cd %~dp0
for /f %%i in ('where prestic.py') do set prestic_py=%%i
echo prestic_py = %prestic_py%
start pythonw %prestic_py% --service %*
IF "%prestic_py%"=="" pause
