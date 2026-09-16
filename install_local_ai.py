"""Explicit opt-in installer: python install_local_ai.py (Windows)."""
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen
import zipfile

from local_ai import CONFIG, ensure_running


def main():
    location = Path(os.environ['LOCALAPPDATA']) / 'Acervo' / 'ollama'
    location.mkdir(parents=True, exist_ok=True)
    executable = location / 'ollama.exe'
    models = location.parent / 'models'
    model = 'qwen3.5:4b'
    if not executable.is_file():
        with urlopen('https://api.github.com/repos/ollama/ollama/releases/latest', timeout=30) as response:
            release = json.load(response)
        asset = next(a for a in release['assets'] if a['name'] == 'ollama-windows-amd64.zip')
        expected = asset.get('digest', '').removeprefix('sha256:')
        if len(expected) != 64:
            raise RuntimeError('A versão oficial não publicou o SHA-256 do arquivo.')
        archive = location / 'ollama-windows-amd64.zip'
        digest = hashlib.sha256()
        print('Baixando Ollama', release['tag_name'], flush=True)
        with urlopen(asset['browser_download_url'], timeout=60) as response, archive.open('wb') as output:
            size, last = 0, -1
            while chunk := response.read(4 * 1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
                progress = int(size * 10 / asset['size'])
                if progress != last:
                    print(f'Ollama: {size // 1048576} / {asset["size"] // 1048576} MB', flush=True)
                    last = progress
        if digest.hexdigest() != expected:
            raise RuntimeError('SHA-256 diferente do publicado. Instalação interrompida.')
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if not (location / member.filename).resolve().is_relative_to(location.resolve()):
                    raise RuntimeError('Caminho inválido no pacote.')
            bundle.extractall(location)
        archive.unlink()
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({'executable': str(executable), 'models': str(models)}, indent=2), encoding='utf-8')
    ensure_running()
    for _ in range(60):
        try:
            with urlopen('http://127.0.0.1:11434/api/version', timeout=1) as response:
                print('Ollama ativo:', json.load(response), flush=True)
                break
        except OSError:
            time.sleep(1)
    else:
        raise RuntimeError('Ollama não iniciou; consulte acervo-server.log na instalação.')
    request = Request('http://127.0.0.1:11434/api/pull',
                      data=json.dumps({'model': model, 'stream': True}).encode(),
                      headers={'Content-Type': 'application/json'})
    print('Baixando modelo', model, flush=True)
    previous = None
    with urlopen(request, timeout=600) as response:
        for line in response:
            item = json.loads(line)
            if item.get('error'):
                raise RuntimeError(item['error'])
            percent = int(item.get('completed', 0) * 20 / max(item.get('total', 1), 1)) * 5
            status = (item.get('status'), percent)
            if status != previous:
                print(status, flush=True)
                previous = status
    CONFIG.write_text(json.dumps({'executable': str(executable), 'models': str(models), 'model': model}, indent=2), encoding='utf-8')
    print('IA local instalada e selecionada:', model, flush=True)


if __name__ == '__main__':
    main()
