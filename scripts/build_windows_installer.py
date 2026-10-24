"""Build a clean, offline-installable Windows package. Run on Windows x64."""
import argparse
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/'.build-tools/payload'
PYTHON_ZIP=ROOT/'.build-tools/python-3.13.17-embed-amd64.zip'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def reset_stage(name):
    target=(PAYLOAD/name).resolve()
    allowed=(ROOT/'.build-tools/payload').resolve()
    if name not in {'app','runtime'} or target.parent!=allowed or not allowed.is_relative_to(ROOT.resolve()):
        raise ValueError('Recusando limpar uma pasta fora do estágio de distribuição.')
    if target.exists():
        # pip can generate bytecode paths beyond MAX_PATH inside dependencies.
        removal_path='\\\\?\\'+str(target) if sys.platform=='win32' else str(target)
        shutil.rmtree(removal_path)
    target.mkdir(parents=True,exist_ok=True)
    return target


def copy_application(target):
    target.mkdir(parents=True,exist_ok=True)
    for source in ROOT.glob('*.py'):shutil.copy2(source,target/source.name)
    for name in ('assets','examples','data/openings','data/tactics'):
        shutil.copytree(ROOT/name,target/name,dirs_exist_ok=True)
    config=target/'.streamlit';config.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'.streamlit/config.toml',config/'config.toml')
    for name in ('README.md','TESTAR_DESKTOP.md','MOBILE_OFFLINE.md','DISTRIBUIR_WINDOWS.md','PAINEL_CENTRAL.md'):
        shutil.copy2(ROOT/name,target/name)
    engines=target/'engines';engines.mkdir(exist_ok=True)
    for name in ('stockfish.exe','Stockfish-COPYING.txt','README.md'):
        shutil.copy2(ROOT/'engines'/name,engines/name)
    for name in ('stockfish-19','berserk'):
        shutil.copytree(ROOT/'engines'/name,engines/name,dirs_exist_ok=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='0.2.2')
    parser.add_argument('--reuse-runtime',action='store_true')
    parser.add_argument('--control-url',default='',help='Endereço HTTPS público do painel central para as instalações distribuídas')
    args=parser.parse_args()
    if sys.platform!='win32':raise SystemExit('O instalador Windows precisa ser montado no Windows.')
    if digest(PYTHON_ZIP)!='9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38':
        raise SystemExit('O pacote de Python não corresponde ao download verificado.')
    runtime=PAYLOAD/'runtime'
    if not args.reuse_runtime:
        runtime=reset_stage('runtime')
        with zipfile.ZipFile(PYTHON_ZIP) as archive:archive.extractall(runtime)
        packages=runtime/'Lib/site-packages'
        subprocess.run([sys.executable,'-m','pip','install','--only-binary=numpy,pandas,pyarrow,opencv-python-headless,pypdfium2',
                        '--target',str(packages),'-r',str(ROOT/'requirements.txt')],check=True)
    (runtime/'python313._pth').write_text('python313.zip\n.\nLib/site-packages\n../app\nimport site\n')
    if not (runtime/'python.exe').is_file():raise SystemExit('Prepare o runtime antes de usar --reuse-runtime.')
    copy_application(reset_stage('app'))
    if args.control_url:
        sys.path.insert(0,str(ROOT))
        from desktop_presence import valid_url
        (PAYLOAD/'app/control-config.json').write_text(json.dumps({'control_url':valid_url(args.control_url)}),encoding='utf8')
    for path in PAYLOAD.rglob('*'):
        if path.is_file() and ('.sqlite3' in path.name or path.suffix=='.log' or path.name in {'appearance.json','last_chesscom_user.json','server.json'}):
            raise SystemExit(f'Dado privado inesperado no pacote: {path}')
    subprocess.run([str(runtime/'python.exe'),'-I','-c',
                    'import streamlit,cv2,numpy,pandas,pyarrow,pypdfium2,chessvision,chess; print("Runtime independente OK")'],check=True)
    (PAYLOAD/'build-manifest.json').write_text(json.dumps({'version':args.version,'python':'3.13.17',
        'engines':{name:digest(PAYLOAD/'app/engines'/name) for name in ('stockfish.exe','berserk/berserk.exe')}},indent=2))
    compiler=ROOT/'.build-tools/inno/ISCC.exe'
    build_log=ROOT/'.build-tools/installer-build.log'
    with build_log.open('w',encoding='utf8') as log:
        result=subprocess.run([str(compiler),f'/DPayload={PAYLOAD}',f'/DAppVersion={args.version}',
                               str(ROOT/'packaging/coach-chess.iss')],stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(build_log.read_text(encoding='utf8')[-5000:])
    installer=ROOT/'dist'/f'CoachChess-Setup-{args.version}-Windows-x64.exe'
    checksum=digest(installer)
    installer.with_suffix('.exe.sha256').write_text(f'{checksum}  {installer.name}\n',encoding='utf8')
    print(f'Instalador pronto: {installer}\nSHA256: {checksum}')


if __name__=='__main__':main()
