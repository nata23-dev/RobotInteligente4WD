@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: ejecute INSTALAR.bat primero.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 (
  echo ERROR: la aplicacion termino con un error. Revise la consola y logs\robot.log.
  pause
  exit /b 1
)
