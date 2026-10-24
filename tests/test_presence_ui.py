from pathlib import Path
import os
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect
import classroom as rooms
from desktop_presence import api
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


@pytest.fixture
def central_server(tmp_path,monkeypatch):
    path=tmp_path/'central.sqlite3'
    with monkeypatch.context() as context:
        context.setenv('COACH_CLASSROOM_DB',str(path))
        rooms.logout(rooms.bootstrap_owner('superadmin','test-owner-pass'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,COACH_CLASSROOM_DB=str(path))
    process=subprocess.Popen([sys.executable,'-m','uvicorn','mobile_api:app','--host','127.0.0.1','--port',str(port)],
        cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:urlopen(url+'/health',timeout=1).close();break
            except OSError:time.sleep(.1)
        monkeypatch.setenv('COACH_CONTROL_URL',url)
        yield url
    finally:process.terminate();process.wait(timeout=15)


@pytest.fixture
def owner_app(central_server,request,tmp_path,monkeypatch):
    with monkeypatch.context() as context:
        context.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
        rooms.logout(rooms.bootstrap_owner('superadmin','test-owner-pass'))
    return request.getfixturevalue('coach_server')


def test_creator_sees_online_installations_and_can_block_one(browser_page,central_server,owner_app):
    device=str(uuid4());secret=secrets.token_urlsafe(40)
    credential='Installation '+secret
    body={'device':device,'name':'amigo-teste','platform':'windows','version':'0.2.2'}
    assert api(central_server,'/v1/installations/heartbeat',body,credential)['allowed']
    page=browser_page;page.set_viewport_size({'width':1440,'height':1050})
    page.goto(owner_app)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('superadmin')
    page.get_by_role('textbox',name='Senha',exact=True).fill('test-owner-pass')
    page.get_by_role('button',name='Entrar',exact=True).click()
    expect(page.get_by_role('heading',name='Quem está com o aplicativo aberto',exact=True)).to_be_visible()
    page.get_by_role('textbox',name='Senha do painel central',exact=True).fill('test-owner-pass')
    page.get_by_role('button',name='Conectar ao painel central',exact=True).click()
    expect(page.get_by_text('Online agora',exact=True)).to_be_visible()
    login=api(central_server,'/v1/login',{'name':'superadmin','password':'test-owner-pass'})
    inventory=api(central_server,'/v1/admin/installations',authorization='Bearer '+login['token'])['installations']
    assert any(row['name']=='superadmin' for row in inventory), 'O próprio app deve enviar sua presença automaticamente'
    page.get_by_role('combobox',name='Gerenciar dispositivo',exact=True).click()
    page.get_by_role('option',name='amigo-teste',exact=False).click()
    page.get_by_role('button',name='Bloquear dispositivo',exact=True).click()
    expect(page.get_by_role('button',name='Desbloquear dispositivo',exact=True)).to_be_visible()
    assert not api(central_server,'/v1/installations/heartbeat',body,credential)['allowed']
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    output=Path(__file__).parent/'artifacts/presence-owner.png';output.parent.mkdir(exist_ok=True)
    page.screenshot(path=str(output),full_page=True)
