"""Open Acervo in a desktop window using the installed Edge or Chrome."""
from pathlib import Path
import ctypes
import importlib.util
import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent


def browser_executable():
    for folder, suffix in (
        ('PROGRAMFILES(X86)', 'Microsoft/Edge/Application/msedge.exe'),
        ('PROGRAMFILES', 'Microsoft/Edge/Application/msedge.exe'),
        ('LOCALAPPDATA', 'Microsoft/Edge/Application/msedge.exe'),
        ('PROGRAMFILES', 'Google/Chrome/Application/chrome.exe'),
        ('LOCALAPPDATA', 'Google/Chrome/Application/chrome.exe'),
    ):
        path = Path(os.environ.get(folder, '')) / suffix
        if path.is_file():
            return path
    return None


def start_server():
    if importlib.util.find_spec('streamlit') is None:
        raise RuntimeError('Execute iniciar.bat uma vez para instalar as dependências. Depois abra Acervo Desktop.bat.')
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 8501))
        except OSError:
            sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    log_dir = ROOT / 'data' / 'desktop'
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'server.log').open('a', encoding='utf-8') as log:
        process = subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
             '--server.address=127.0.0.1', f'--server.port={port}',
             '--server.headless=true', '--browser.gatherUsageStats=false'],
            cwd=ROOT, stdout=log, stderr=log,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'O aplicativo não iniciou. Consulte {log_dir / "server.log"}.')
            try:
                with urlopen(url + '/_stcore/health', timeout=1) as response:
                    if response.read() == b'ok':
                        return url, process
            except OSError:
                pass
            time.sleep(.15)
        raise RuntimeError('O aplicativo demorou para iniciar. Tente abrir novamente.')
    except Exception:
        process.terminate()
        process.wait(timeout=10)
        raise


def main():
    try:
        url, _ = start_server()
        url += '/?view=aberturas'
        browser = browser_executable()
        if browser:
            # A hidden pythonw launcher must still show the interactive window.
            startup = None
            if os.name == 'nt':
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = 1  # SW_SHOWNORMAL
            subprocess.Popen([str(browser), '--app=' + url, '--window-size=1440,960'],
                             startupinfo=startup)
        else:
            webbrowser.open(url)
    except Exception as error:
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(0, str(error), 'Acervo Desktop', 0x10)
        else:
            raise


if __name__ == '__main__':
    main()
