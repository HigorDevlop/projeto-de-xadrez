"""Open Acervo in a desktop window using the installed Edge or Chrome."""
from pathlib import Path
import ctypes
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent


def desktop_state():
    return Path(os.environ.get('COACH_DESKTOP_STATE',ROOT/'data/desktop'))


def _source_version():
    digest=hashlib.sha256()
    assets=[p for p in (ROOT/'assets').glob('*') if p.suffix in ('.js','.css','.svg')]
    for path in sorted([*ROOT.glob('*.py'),*assets]):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _saved_server():
    try:
        saved=json.loads((desktop_state()/'server.json').read_text(encoding='utf8'))
        port,pid=int(saved['port']),int(saved['pid'])
        if not 1024<=port<=65535 or pid<=0:return None
        if os.name=='nt':
            shell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
            command=subprocess.run([str(shell),'-NoProfile','-NonInteractive','-Command',
                "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
                f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine"],
                capture_output=True,text=True,encoding='utf8',errors='replace',timeout=8,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout
        else:
            command=Path(f'/proc/{pid}/cmdline').read_text().replace('\0',' ')
        if str(ROOT/'app.py').casefold() not in command.casefold() or f'--server.port={port}' not in command:
            return None
        url=f'http://127.0.0.1:{port}'
        with urlopen(url+'/_stcore/health',timeout=1) as response:
            if response.read()==b'ok':return url
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):
        return None


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
    version=_source_version()
    if saved:=_saved_server():
        record=json.loads((desktop_state()/'server.json').read_text(encoding='utf8'))
        if record.get('source_version')==version:return saved,None
        # _saved_server verifies this installation's app path, PID, port and health.
        # Reload imported modules after an update, keeping the browser origin stable.
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(int(record['pid'])),'/T','/F'],
                capture_output=True,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:
            import signal
            os.kill(int(record['pid']),signal.SIGTERM)
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            try:
                with socket.create_connection(('127.0.0.1',int(record['port'])),timeout=.2):pass
            except OSError:break
            time.sleep(.1)
    try:
        preferred=int(json.loads((desktop_state()/'server.json').read_text(encoding='utf8'))['port'])
        if not 1024<=preferred<=65535:preferred=8501
    except (OSError,ValueError,KeyError):preferred=8501
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', preferred))
        except OSError:
            sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    log_dir = desktop_state()
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'server.log').open('a', encoding='utf-8') as log:
        process = subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
             '--server.address=127.0.0.1', f'--server.port={port}',
             '--server.fileWatcherType=none',
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
                        (log_dir/'server.json').write_text(json.dumps({'pid':process.pid,'port':port,'source_version':version}),encoding='utf8')
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
            # Keep the app in its own browser process. An already open personal
            # browser can otherwise ignore the startup fullscreen flags.
            profile = desktop_state() / 'browser-profile'
            profile.mkdir(parents=True, exist_ok=True)
            # A hidden pythonw launcher must still show the interactive window.
            startup = None
            if os.name == 'nt':
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = 3  # SW_SHOWMAXIMIZED
            window_process = subprocess.Popen([str(browser), '--user-data-dir=' + str(profile.resolve()),
                              '--no-first-run', '--no-default-browser-check',
                              '--new-window', '--app=' + url, '--start-fullscreen'],
                             startupinfo=startup)
            if os.name == 'nt' and isinstance(getattr(window_process, 'pid', None), int):
                from threading import Thread
                from desktop_identity import apply_to_browser
                Thread(target=apply_to_browser, args=(profile,url,ROOT,sys.executable),
                       name='coach-window-identity', daemon=False).start()
        else:
            webbrowser.open(url)
    except Exception as error:
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(0, str(error), 'Acervo Desktop', 0x10)
        else:
            raise


if __name__ == '__main__':
    main()
