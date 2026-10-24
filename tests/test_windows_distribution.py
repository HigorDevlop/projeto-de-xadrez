"""Exercise the bundled runtime without relying on the developer Python."""
from pathlib import Path
import os
import socket
import subprocess
import time
from urllib.request import urlopen
import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=Path(os.environ.get('COACH_TEST_INSTALL_DIR',str(ROOT/'.build-tools/payload')))
RUNTIME=PAYLOAD/'runtime/python.exe'


def test_installed_entry_keeps_private_data_outside_program_directory(tmp_path,monkeypatch):
    from installed_entry import configure_data
    names=('COACH_CLASSROOM_DB','COACH_BOOK_LIBRARY','COACH_BOOK_POSITION_DIR','COACH_DESKTOP_STATE',
           'ACERVO_PREPARATION_DIR','ACERVO_PERFORMANCE_DIR','ACERVO_USER_PREFERENCE','ACERVO_APPEARANCE_PREFERENCE')
    for key in names:monkeypatch.delenv(key,raising=False)
    base=configure_data(tmp_path)
    assert base==tmp_path/'CoachChess'
    assert all(Path(os.environ[key]).is_relative_to(base) for key in names)
    for key in names:monkeypatch.delenv(key,raising=False)


@pytest.fixture
def runtime_server(tmp_path):
    if not RUNTIME.exists():pytest.skip('Distribution runtime not built')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=dict(os.environ)
    for key in list(env):
        if key.startswith(('PYTHON','COACH_','ACERVO_','STOCKFISH','BERSERK')):env.pop(key)
    env['PATH']=str(Path(os.environ['WINDIR'])/'System32')
    code=("from installed_entry import configure_data;configure_data("+repr(str(tmp_path))+ ");"
          "import sys;sys.argv=['streamlit','run','app.py','--server.headless=true',"
          "'--server.address=127.0.0.1','--server.port="+str(port)+"'];"
          "from streamlit.web.cli import main;main()")
    log=(tmp_path/'server.log').open('w',encoding='utf8')
    process=subprocess.Popen([str(RUNTIME),'-I','-c',code],cwd=PAYLOAD/'app',env=env,stdout=log,stderr=log,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(200):
            if process.poll() is not None:
                log.flush();pytest.fail((tmp_path/'server.log').read_text(encoding='utf8'))
            try:
                urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=1).close();break
            except OSError:time.sleep(.1)
        yield f'http://127.0.0.1:{port}'
    finally:
        process.terminate();process.wait(timeout=15);log.close()


def test_bundled_app_registers_plays_and_analyses_without_external_network(browser_page,runtime_server):
    page=browser_page
    page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(runtime_server) else route.abort())
    page.goto(runtime_server)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('amigo-instalador')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-instalada-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    board=page.locator('.st-key-analysis_board_focus')
    board.locator('[data-square="e2"]').click();board.locator('[data-square="e4"]').click()
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 1')
    page.get_by_role('button',name='Analisar Partida',exact=False).click()
    page.get_by_role('button',name='Iniciar análise',exact=True).click()
    expect(page.locator('.quality-summary')).to_contain_text('Stockfish 19',timeout=45000)
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    private=list((PAYLOAD/'app').rglob('*.sqlite3*'))
    assert not private
