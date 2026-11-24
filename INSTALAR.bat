@echo off
setlocal
cd /d "%~dp0"
set "ROBOT_PY="
if exist ".runtime\python.exe" set "ROBOT_PY=.runtime\python.exe"
if defined ROBOT_PY goto verificar
py -3.12 -c "import struct,sys; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8" >nul 2>&1
if errorlevel 1 goto sinpython
set "ROBOT_PY=py -3.12"
:verificar
%ROBOT_PY% -c "import struct,sys,tkinter; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8"
if errorlevel 1 goto error
if not exist ".venv\Scripts\python.exe" %ROBOT_PY% -m venv .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8"
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto error
".venv\Scripts\python.exe" -c "import cv2,numpy,PIL,requests,tkinter; assert hasattr(cv2.aruco,'ArucoDetector'); print('Dependencias verificadas')"
if errorlevel 1 goto error
echo Instalacion terminada. Ejecute INICIAR_APLICACION.bat
exit /b 0
:sinpython
echo ERROR: necesita Python 3.12 de 64 bits con Tcl/Tk instalado desde python.org.
echo No se modifico su Python global. Instale 3.12 y vuelva a ejecutar este archivo.
pause
exit /b 1
:error
echo ERROR: instalacion incompleta. Revise el mensaje anterior.
pause
exit /b 1
