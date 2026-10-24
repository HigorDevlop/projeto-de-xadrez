@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 (
    echo Nao foi possivel acessar a pasta do Coach Chess.
    pause
    exit /b 1
)

set "SCRIPT=%~dp0.build-tools\maintenance\request-local.ps1"
if not exist "%SCRIPT%" (
    echo Nao foi encontrado o script de manutencao:
    echo "%SCRIPT%"
    pause
    exit /b 1
)

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo A aplicacao das correcoes falhou. Confira a mensagem acima.
pause
exit /b %RESULT%
