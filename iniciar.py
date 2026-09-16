from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"


def virtualenv_python() -> Path:
    executable = "python.exe" if os.name == "nt" else "python"
    return VENV / ("Scripts" if os.name == "nt" else "bin") / executable


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    if not VENV.is_dir():
        print("Criando o ambiente virtual...")
        run([sys.executable, "-m", "venv", str(VENV)])

    python = virtualenv_python()
    if not python.is_file():
        raise RuntimeError(f"Interpretador do ambiente virtual não encontrado: {python}")

    print("Instalando as dependências...")
    run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    print("Abra http://127.0.0.1:8501 para usar o aplicativo.")
    run([str(python), "-m", "streamlit", "run", "app.py",
         "--server.address", "127.0.0.1", "--server.port", "8501"])


if __name__ == "__main__":
    main()