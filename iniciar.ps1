$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Instale Python 3.11 ou superior e tente novamente.' }
    & $projectPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências.' }
}
Write-Host 'Abra http://127.0.0.1:8501 para usar o aplicativo.'
& $projectPython -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
