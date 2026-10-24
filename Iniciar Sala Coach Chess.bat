@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute iniciar.bat primeiro para instalar as dependencias.
  pause
  exit /b 1
)
echo Coach Chess - Sala na rede local
echo No computador da sala: http://127.0.0.1:8510
echo Nos computadores dos alunos, use um destes enderecos da rede local:
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object { 'http://' + $_.IPAddress + ':8510' }"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address=0.0.0.0 --server.port=8510 --browser.gatherUsageStats=false
pause
