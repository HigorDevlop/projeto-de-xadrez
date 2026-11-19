import os
from pathlib import Path
import pytest
import classroom as rooms
import classroom_community as community
from test_coach_chess_ui import coach_server
from test_browser_components import browser_page


def test_chat_video_live_stream_and_mobile_layout(coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import sync_playwright,expect
    expect.set_options(timeout=40000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    invite=rooms.issue_professor_key(owner)
    teacher=rooms.register_professor('professor','teacher-password-123',invite)
    seat=rooms.students(teacher)[0]
    user=rooms.register_user('student','student-password-123')
    rooms.join_room(user,seat['access_key'])
    community.publish_video(teacher,'Final de torres','https://example.com/lesson.mp4')
    edge=Path(os.environ.get('PROGRAMFILES(X86)',''))/'Microsoft/Edge/Application/msedge.exe'
    with sync_playwright() as driver:
        browser=driver.chromium.launch(executable_path=str(edge) if edge.exists() else None,headless=True,
            args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
        try:
            host=browser.new_page(viewport={'width':1440,'height':1000})
            pupil=browser.new_page(viewport={'width':1440,'height':1000})
            host.goto(coach_server)
            host.get_by_role('radio',name='Professor',exact=True).click()
            host.get_by_role('textbox',name='Usuário',exact=True).fill('professor')
            host.get_by_role('textbox',name='Senha',exact=True).fill('teacher-password-123')
            host.get_by_role('textbox',name='Chave especial do Professor (obrigatória)',exact=True).fill(invite)
            host.get_by_role('button',name='Entrar',exact=True).click()
            expect(host.get_by_role('heading',name='Modo Preparo',exact=True)).to_be_visible()
            host.get_by_role('tab',name='Conversas',exact=True).click()
            host.get_by_placeholder('Escreva uma mensagem').fill('Olá turma, vamos treinar!')
            host.get_by_placeholder('Escreva uma mensagem').press('Enter')
            expect(host.locator('.bubble')).to_contain_text(['Olá turma, vamos treinar!'])
            pupil.goto(coach_server)
            pupil.get_by_role('textbox',name='Usuário',exact=True).fill('student')
            pupil.get_by_role('textbox',name='Senha',exact=True).fill('student-password-123')
            pupil.get_by_role('button',name='Entrar',exact=True).click()
            pupil.get_by_role('button',name='Abrir sala do Professor',exact=True).click()
            pupil.get_by_role('tab',name='Conversas',exact=True).click()
            expect(pupil.locator('.bubble')).to_contain_text(['Olá turma, vamos treinar!'])
            pupil.get_by_placeholder('Escreva uma mensagem').fill('Boa tarde, professor!')
            pupil.get_by_placeholder('Escreva uma mensagem').press('Enter')
            expect(host.locator('.bubble')).to_have_count(2)
            pupil.set_viewport_size({'width':390,'height':844})
            pupil.screenshot(path='tests/artifacts/classroom-chat-mobile.png',full_page=True)
            host.screenshot(path='tests/artifacts/classroom-chat-desktop.png',full_page=True)
            assert pupil.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2')
            host.get_by_role('tab',name='Aulas',exact=True).click()
            expect(host.get_by_text('Final de torres',exact=True)).to_be_visible()
            host.get_by_role('button',name='Iniciar aula ao vivo',exact=False).click()
            host.get_by_role('button',name='Entrar na aula ao vivo',exact=True).click()
            host.locator('.broadcast').click()
            expect(host.locator('.broadcast')).to_be_disabled()
            pupil.get_by_role('tab',name='Aulas',exact=True).click()
            pupil.get_by_role('button',name='Entrar na aula ao vivo',exact=True).click()
            expect(pupil.locator('.live-status')).to_have_text('Ao vivo',timeout=60000)
            pupil.wait_for_function("()=>{const walk=r=>[...r.querySelectorAll('*')].flatMap(e=>[e,...(e.shadowRoot?walk(e.shadowRoot):[])]);return walk(document).some(e=>e.tagName==='VIDEO'&&e.readyState>=2)}",timeout=30000)
            pupil.screenshot(path='tests/artifacts/classroom-live-mobile.png',full_page=True)
            pupil.get_by_placeholder('Escreva uma mensagem').fill('Estou assistindo à aula!')
            pupil.get_by_placeholder('Escreva uma mensagem').press('Enter')
            expect(host.locator('.bubble').last).to_contain_text('Estou assistindo à aula!')
            expect(pupil.locator('.live-status')).to_have_text('Ao vivo')
            assert host.locator('[data-testid=stException]').count()==0
            assert pupil.locator('[data-testid=stException]').count()==0
            host.get_by_role('button',name='Encerrar aula para todos',exact=True).click()
            expect(pupil.get_by_text('Nenhuma aula ao vivo no momento.',exact=True)).to_be_visible()
        finally:browser.close()


def test_student_can_watch_recordings_from_common_tabs_without_attendance(browser_page,coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import expect
    expect.set_options(timeout=40000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    teacher=rooms.register_professor('teacher','teacher-password-123',rooms.issue_professor_key(owner))
    seat=rooms.students(teacher)[0]
    user=rooms.register_user('viewer','viewer-password-123')
    rooms.join_room(user,seat['access_key'])
    community.publish_video(teacher,'Aula gravada disponível','https://example.com/lesson.mp4')
    page=browser_page;page.set_default_timeout(45000);page.set_viewport_size({'width':1440,'height':1000})
    page.goto(coach_server)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('viewer')
    page.get_by_role('textbox',name='Senha',exact=True).fill('viewer-password-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.get_by_role('link',name='Vídeos gravados',exact=False).click()
    expect(page.get_by_role('heading',name='Vídeos gravados',exact=True)).to_be_visible()
    page.get_by_text('Aula gravada disponível',exact=True).click()
    page.get_by_role('button',name='Assistir',exact=True).click()
    expect(page.locator('video')).to_be_visible()
    expect(page.locator('.clock')).to_have_count(0)
    expect(page.get_by_role('button',name='Abrir sala do Professor',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Excluir vídeo',exact=True)).to_have_count(0)
    with rooms.database() as db:assert db.execute('SELECT COUNT(*) FROM training_visits').fetchone()[0]==0
    assert page.locator('[data-testid=stException]').count()==0
