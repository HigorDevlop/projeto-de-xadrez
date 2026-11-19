from pathlib import Path
import json
import pytest
from playwright.sync_api import expect
import classroom as rooms
import classroom_trails as trails
import classroom_training_sessions as sessions
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


@pytest.fixture
def studio_server(tmp_path,monkeypatch,request):
    import test_coach_chess_ui as desktop
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    (tmp_path/'app.py').write_text(f'''
import sys
sys.path.insert(0,{str(root)!r})
import streamlit as st
import classroom as rooms
import classroom_trails as trails
from classroom_materials_ui import teacher_materials
st.set_page_config(layout='wide')
if 'owner' not in st.session_state:
    token=rooms.bootstrap_owner('fixture-owner','password-fixture-123')
    seat=rooms.ensure_admin_room(token)[0]
    draft=trails.edit_draft(token,seat['id'],0,dict(action='add'),[
        dict(title='Estudo inicial',kind='note',payload=dict(text='Controle do centro'),reviewed=True)])
    trails.publish(token,seat['id'],draft['revision'])
    st.session_state.owner=token;st.session_state.seat=seat['id']
teacher_materials(st.session_state.owner,st.session_state.seat)
''',encoding='utf-8')
    return request.getfixturevalue('coach_server')


def test_save_new_load_publish_and_reset_selected_students_trail(browser_page,studio_server,tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    page=browser_page;page.set_default_timeout(45000);expect.set_options(timeout=45000)
    page.set_viewport_size(dict(width=1440,height=1100));page.goto(studio_server)
    def open_manager():
        panel=page.locator('details').filter(has=page.locator('summary').filter(has_text='Sessões de treino e biblioteca'))
        expect(panel).to_have_count(1)
        if not panel.evaluate('element=>element.open'):panel.locator('summary').click()
    open_manager()
    page.get_by_role('textbox',name='Nome para salvar na biblioteca').fill('Sessão de abertura')
    page.get_by_role('button',name='Salvar e criar nova trilha',exact=False).click()
    expect(page.get_by_text('Trilha salva na biblioteca. A nova montagem começa vazia.',exact=True)).to_be_visible()
    token=rooms.login_owner('fixture-owner','password-fixture-123');student=rooms.students(token)[0]['id']
    assert trails.load_draft(token,student)['steps']==[]
    assert len(sessions.progress(token,student))==1
    open_manager()
    page.get_by_role('button',name='Preparar nova sessão com esta trilha',exact=False).click()
    expect(page.get_by_text('Modelo carregado na montagem.',exact=False)).to_be_visible()
    page.get_by_role('button',name='Disponibilizar trilha ao aluno',exact=True).click()
    expect(page.get_by_text('Trilha disponível',exact=False)).to_be_visible()
    assert len(sessions.history(token,student))==1
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path='tests/artifacts/training-session-after-publish.png',full_page=True)
    (tmp_path/'expanders.json').write_text(json.dumps(page.locator('details').evaluate_all('(elements)=>elements.map(e=>({summary:e.querySelector(":scope > summary")?.textContent,html:e.outerHTML.slice(0,500)}))')),encoding='utf-8')
    open_manager()
    page.get_by_text('Confirmo reiniciar a trilha e o progresso atual deste aluno',exact=True).click()
    page.get_by_role('button',name='Reiniciar trilha do zero',exact=False).click()
    expect(page.get_by_text('Trilha reiniciada.',exact=False)).to_be_visible()
    assert sessions.progress(token,student)==[]
    assert len(sessions.library(token))>=1
    assert len(sessions.history(token,student))==2
    page.screenshot(path='tests/artifacts/training-sessions-studio.png',full_page=True)


def test_access_key_field_is_prominent_and_joins_the_room(browser_page,coach_server,tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    seat=rooms.ensure_admin_room(owner)[0]
    rooms.register_user('pupil-key','password-pupil-123')
    page=browser_page;page.set_default_timeout(45000);expect.set_options(timeout=45000)
    page.goto(coach_server)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('pupil-key')
    page.get_by_role('textbox',name='Senha',exact=True).fill('password-pupil-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Partida').click()
    panel=page.locator('.st-key-classroom_join_panel')
    expect(panel.get_by_role('heading',name='Recebeu uma chave do professor?')).to_be_visible()
    panel.get_by_role('textbox',name='Chave de acesso do professor').fill(seat['access_key'])
    page.screenshot(path='tests/artifacts/student-access-key.png',full_page=True)
    panel.get_by_role('button',name='Entrar na sala do professor',exact=False).click()
    expect(page.get_by_role('heading',name='Modo Preparo',exact=True)).to_be_visible()
    assert rooms.students(owner)[0]['linked']
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
