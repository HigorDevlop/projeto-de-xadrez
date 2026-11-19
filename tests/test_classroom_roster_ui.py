from playwright.sync_api import expect
import classroom as rooms
import classroom_student_profiles as profiles
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def test_profile_loads_in_background_and_keeps_saved_ratings_when_offline(browser_page,tmp_path,monkeypatch):
    import test_coach_chess_ui as desktop
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    # A dedicated app isolates the public API response from the real network.
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    (tmp_path/'app.py').write_text(f'''
import sys
sys.path.insert(0,{str(root)!r})
import streamlit as st
import classroom as rooms
import chesscom
from pathlib import Path
from classroom_roster_ui import student_record
st.set_page_config(layout='wide')
if 'owner' not in st.session_state:
    token=rooms.bootstrap_owner('fixture-owner','password-fixture-123')
    seat=rooms.ensure_admin_room(token)[0]
    rooms.update_student(token,seat['id'],'Aluno de teste','fixture_chess')
    st.session_state.owner=token;st.session_state.seat=seat['id']
def fetch(username):
    flag=Path({str(tmp_path/'requested')!r})
    if flag.exists():raise ValueError('Consulta indisponível para teste')
    flag.write_text('ok')
    return dict(player_id=987654,ratings={{'Rápidas':1500,'Blitz':1300,'Bullet':None,'Diárias':None}})
chesscom.fetch_player_profile=fetch
student_record(st.session_state.owner,st.session_state.seat)
''',encoding='utf-8')
    # Reuse the server lifecycle with the dedicated app and isolated database.
    generator=desktop.coach_server.__wrapped__(tmp_path/'isolated')
    (tmp_path/'isolated').mkdir()
    try:
        url=next(generator)
        page=browser_page;page.set_default_timeout(30000);page.goto(url)
        dialog=page.get_by_role('dialog')
        expect(dialog).to_contain_text('987654',timeout=30000)
        expect(dialog).to_contain_text('1500')
        dialog.get_by_role('button',name='Atualizar Chess.com',exact=False).click()
        expect(dialog).to_contain_text('Consulta indisponível para teste',timeout=10000)
        expect(dialog).to_contain_text('1500')
        expect(dialog.locator('[data-testid=stException]')).to_have_count(0)
    finally:
        generator.close()


def test_student_card_opens_saved_profile_edits_and_survives_login(browser_page,coach_server,tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    invite=rooms.issue_professor_key(owner)
    teacher=rooms.register_professor('professor','teacher-password-123',invite)
    seat=rooms.students(teacher)[0]
    user=rooms.register_user('ana-aluna','password-aluna-123')
    rooms.save_chesscom_user(user,'ana_chess');rooms.join_room(user,seat['access_key'])
    rooms.update_student(teacher,seat['id'],'Ana Silva','ana_chess')
    profiles.save(teacher,seat['id'],'ana_chess',dict(player_id=123456,name='Ana',
        last_online=1780000000,ratings={'Rápidas':1400,'Blitz':1250,'Bullet':None,'Diárias':None}))
    page=browser_page;page.set_default_timeout(60000);expect.set_options(timeout=60000)
    page.set_viewport_size(dict(width=1440,height=1100));page.goto(coach_server)
    def login():
        page.get_by_role('radio',name='Professor',exact=True).click()
        page.get_by_role('textbox',name='Usuário',exact=True).fill('professor')
        page.get_by_role('textbox',name='Senha',exact=True).fill('teacher-password-123')
        page.get_by_role('textbox',name='Chave especial do Professor (obrigatória)',exact=True).fill(invite)
        page.get_by_role('button',name='Entrar',exact=True).click()
        expect(page.get_by_role('tab',name='Alunos e acessos',exact=True)).to_be_visible()
    login()
    expect(page.locator('.roster-status.linked')).to_have_count(1)
    search=page.get_by_role('textbox',name='Buscar aluno',exact=True)
    search.fill('ANA_CHESS');search.press('Enter')
    expect(page.locator('[class*=st-key-prep_student_open_] button')).to_have_count(1)
    search.fill('nenhum-aluno-corresponde');search.press('Enter')
    expect(page.get_by_text('Nenhum aluno encontrado',exact=True)).to_be_visible()
    page.get_by_role('button',name='Limpar busca e filtros',exact=False).click()
    expect(search).to_have_value('')
    expect(page.locator('[class*=st-key-prep_student_open_] button')).to_have_count(4)
    page.locator('.st-key-roster_filter').get_by_role('combobox').click()
    page.get_by_role('option',name='Contas vinculadas',exact=True).click()
    expect(page.locator('[class*=st-key-prep_student_open_] button')).to_have_count(1)
    page.locator('.st-key-roster_filter').get_by_role('combobox').click()
    page.get_by_role('option',name='Todos os acessos',exact=True).click()
    expect(page.locator('[class*=st-key-prep_student_open_] button').first).to_be_visible()
    page.screenshot(path='tests/artifacts/student-roster-desktop.png',full_page=True)
    page.locator('.st-key-prep_student_open_'+seat['id']+' button').click()
    dialog=page.get_by_role('dialog')
    expect(dialog).to_contain_text('123456')
    expect(dialog).to_contain_text('1400')
    expect(dialog.get_by_role('textbox',name='Usuário Chess.com do aluno')).to_have_value('ana_chess')
    expect(dialog.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path='tests/artifacts/student-record-desktop.png',full_page=True)
    dialog.get_by_role('textbox',name='Nome do aluno',exact=True).fill('Ana Oliveira')
    dialog.get_by_role('button',name='Salvar dados do aluno',exact=False).click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    expect(page.get_by_role('button',name='Ana Oliveira',exact=False)).to_be_visible()
    page.get_by_text('Configurações',exact=True).click()
    page.get_by_role('button',name='Sair e esquecer este navegador',exact=True).click()
    login()
    page.get_by_role('button',name='Ana Oliveira',exact=False).click()
    expect(page.get_by_role('dialog')).to_contain_text('123456')
    page.get_by_role('dialog').get_by_role('button',name='Abrir e editar a trilha deste aluno',exact=False).click()
    expect(page.get_by_role('tab',name='Treino e provas',exact=True)).to_have_attribute('aria-selected','true')
    expect(page.get_by_role('dialog')).to_have_count(0)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.get_by_role('tab',name='Alunos e acessos',exact=True).click()
    page.locator('.st-key-roster_training_'+seat['id']+' button').click()
    expect(page.get_by_role('tab',name='Treino e provas',exact=True)).to_have_attribute('aria-selected','true')
    expect(page.locator('.prep-profile')).to_contain_text('Ana Oliveira')
    page.get_by_role('tab',name='Alunos e acessos',exact=True).click()
    collapse=page.locator('[data-testid=stSidebarCollapseButton] button')
    if collapse.is_visible():collapse.click()
    page.set_viewport_size(dict(width=390,height=844))
    expect(page.locator('.roster-stats')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    page.screenshot(path='tests/artifacts/student-roster-mobile.png',full_page=True)
