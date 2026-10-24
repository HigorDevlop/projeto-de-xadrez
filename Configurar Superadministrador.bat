@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute iniciar.bat primeiro para instalar as dependencias.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" configure_owner.py
pause
