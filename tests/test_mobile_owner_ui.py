import pytest
from uuid import uuid4
from playwright.sync_api import expect
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server
import classroom as rooms
import mobile_sync


def test_creator_sees_identified_devices_and_can_block_user(browser_page,coach_server,tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('criador','password-criador-123')
    user=rooms.register_user('amigo-mobile','password-amigo-123')
    identifier=rooms.identity(user)['id']
    mobile_sync.sync(user,str(uuid4()),[{'id':str(uuid4()),'sequence':1,'payload':{'checkpoint':{'ply':1}}}],platform='android',version='0.1.0')
    page=browser_page;page.goto(coach_server)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('criador')
    page.get_by_role('textbox',name='Senha',exact=True).fill('password-criador-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.get_by_role('tab',name='Usuários',exact=True).click()
    expect(page.get_by_role('combobox',name='Gerenciar acesso do usuário')).to_be_visible()
    expect(page.get_by_text('Dispositivos identificados',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Bloquear usuário',exact=True)).to_be_visible()
    page.get_by_role('button',name='Bloquear usuário',exact=True).click()
    expect(page.get_by_role('button',name='Autorizar usuário',exact=True)).to_be_visible()
    assert rooms.identity(user) is None
    assert next(r for r in rooms.admin_overview(owner)['users'] if r['id']==identifier)['status']=='blocked'
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
