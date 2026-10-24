import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from PIL import Image
from test_browser_components import browser_page
from test_opening_course_ui import course_server, current, saved, ROOT


@pytest.fixture
def coach_server(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    appearance = tmp_path/'appearance.json'
    appearance.write_text(json.dumps({'theme':'Claro', 'background_mode':'Claro'}))
    env = dict(os.environ, ACERVO_USER_PREFERENCE=str(tmp_path/'user.json'),
               COACH_CLASSROOM_DB=str(tmp_path/'classrooms.sqlite3'),
               ACERVO_APPEARANCE_PREFERENCE=str(appearance), ACERVO_PREPARATION_DIR=str(tmp_path/'progress'))
    process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(ROOT/'app.py'),
        '--server.headless=true', f'--server.port={port}', '--browser.gatherUsageStats=false'],
        cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:
                urlopen(url+'/_stcore/health',timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        yield url
    finally:
        process.terminate()
        process.wait(timeout=15)


def test_dark_theme_two_routes_and_monochrome_logo(browser_page,coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    page=browser_page
    import classroom as rooms
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    teacher=rooms.register_professor('teacher','teacher-password-123',rooms.issue_professor_key(owner,'teacher'))
    student=rooms.students(teacher)[0]
    from preparation_state import today
    rooms.save_routine(teacher,student['id'],['italian'],1,1,1,1,list(range(7)),today())
    page.set_viewport_size(dict(width=1440,height=1000))
    page.goto(coach_server)
    expect(page.get_by_role('radio')).to_have_count(2)
    expect(page.get_by_role('radio',name='Usuário',exact=True)).to_be_visible()
    expect(page.get_by_role('radio',name='Professor',exact=True)).to_be_visible()
    expect(page.get_by_role('textbox',name='Código da sala',exact=True)).to_have_count(0)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('usuario-ui')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-usuario-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    expect(page.get_by_role('heading',name='Análise de partidas',exact=True)).to_be_visible()
    navigation=page.locator('.st-key-sidebar_navigation a')
    expect(navigation).to_have_count(5)
    assert [a.inner_text().splitlines()[-1] for a in navigation.all()]==['Partida','Análise','Táticos','Estudo com livros','Aberturas']
    assert page.locator('.stApp').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(10, 10, 10)'
    expect(page.locator('.club-brand')).to_contain_text('Coach Chess')
    logo=page.locator('.club-brand img')
    assert logo.evaluate('(e)=>e.complete && e.naturalWidth>0')
    pixels=Image.open(ROOT/'assets/coach-chess.png').convert('RGB').getdata()
    assert all(red == green == blue for red, green, blue in pixels)
    page.screenshot(path=str(ROOT/'tests/artifacts/coach-analysis-desktop.png'),full_page=True)
    navigation.filter(has_text='Aberturas').click()
    expect(page.locator('.home header strong')).to_contain_text('Coach Chess')
    expect(page.locator('.st-key-sidebar_navigation a')).to_have_count(5)
    expect(page.locator('[data-testid=stSidebar]')).to_be_visible()
    assert page.locator('.stApp').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(10, 10, 10)'
    page.screenshot(path=str(ROOT/'tests/artifacts/coach-openings-desktop.png'),full_page=True)
    assert page.locator('[data-testid=stException]').count()==0


def test_four_state_practice_advances_immediately_and_recovers(browser_page,course_server):
    from playwright.sync_api import expect
    from opening_training_state import expected_move, board_for
    expect.set_options(timeout=30000)
    page=browser_page;page.set_default_timeout(30000)
    page.set_viewport_size(dict(width=1440,height=1000))
    url,folder=course_server
    page.goto(url)
    page.locator('[data-id=italian]').click()
    expect(page.get_by_role('button',name='Aprender com setas',exact=True)).to_have_count(0)
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.training-hint')).to_have_count(1)
    assert current(folder)['mode']=='learn'
    def live_frame():
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            live=current(folder)
            if page.locator('.board').get_attribute('data-revision')==f"{live['token']}:{live['revision']}":
                return live
            page.wait_for_timeout(25)
        raise AssertionError('O tabuleiro e o progresso salvo não sincronizaram')
    # Teach and recall the new line before entering its four-state quiz.
    for _ in range(80):
        live=live_frame()
        if live['mode']=='quiz': break
        revision=f"{live['token']}:{live['revision']}"
        expect(page.locator('.board')).to_have_attribute('data-revision',revision)
        if live.get('ui_checkpoint'):
            page.get_by_role('button',name='Continuar',exact=True).click()
        else:
            uci=expected_move(saved(folder),live)
            page.locator('[data-square='+uci[:2]+'].movable').click()
            page.locator('[data-square='+uci[2:]+']').click()
        expect(page.locator('.board')).not_to_have_attribute('data-revision',revision)
        live_frame()
    assert current(folder)['mode']=='quiz'
    expect(page.get_by_role('button',name='Não sei',exact=True)).to_have_count(0)
    expect(page.get_by_role('button',name='Analisar posição',exact=False)).to_have_count(0)
    expect(page.locator('.reference-counters')).to_be_visible()
    assert page.locator('.reference-counter small').all_text_contents()==['A fazer','Erro','Não sei','Certo']
    session=current(folder);target=session['ply'];initial=list(session['quiz_queue'])
    assert set(session['quiz_states'].values())=={'pending'}

    def play(correct=True):
        live=live_frame()
        revision=f"{live['token']}:{live['revision']}"
        expect(page.locator('.board')).to_have_attribute('data-revision',revision)
        uci=expected_move(saved(folder),live)
        if not correct:
            uci=next(m.uci() for m in board_for(live).legal_moves if m.uci()!=uci)
        page.locator('[data-square='+uci[:2]+'].movable').click()
        page.locator('[data-square='+uci[2:]+']').click()
        expect(page.locator('.board')).not_to_have_attribute('data-revision',revision)
        return live_frame()

    play(False)
    assert current(folder)['ply']==initial[1]
    assert current(folder)['quiz_states'][str(target)]=='wrong'
    assert page.get_by_role('button',name='Próximo',exact=True).count()==0
    seen_recovery=False
    for _ in range(50):
        session=current(folder)
        if session['phase']=='complete':break
        is_target=session['ply']==target
        after=play()
        if is_target and not seen_recovery:
            assert after['quiz_states'][str(target)]=='unknown'
            seen_recovery=True
            expect(page.locator('.reference-counter.unknown div')).to_contain_text('1')
            page.screenshot(path=str(ROOT/'tests/artifacts/coach-recovery-desktop.png'),full_page=True)
    assert seen_recovery
    assert current(folder)['phase']=='complete'
    assert set(current(folder)['quiz_states'].values())=={'correct'}
    expect(page.get_by_text('Bom trabalho!',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Analisar posição',exact=False)).to_have_count(0)
    assert page.locator('[data-testid=stException]').count()==0


def test_openings_header_flame_and_navigation_fit_mobile(browser_page,coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import expect
    from datetime import timedelta
    import classroom as rooms
    from streak_style import login_streak
    from preparation_state import today
    expect.set_options(timeout=40000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    user=rooms.register_user('mobile-user','mobile-password-123')
    for i in range(50):login_streak(user,True,today()-timedelta(days=49-i))
    page=browser_page;page.set_viewport_size({'width':390,'height':844})
    page.goto(coach_server)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('mobile-user')
    page.get_by_role('textbox',name='Senha',exact=True).fill('mobile-password-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    expect(page.locator('.home header strong')).to_contain_text('Coach Chess')
    expect(page.get_by_role('img',name='Chama nível 5, 50 dias',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2')
    page.screenshot(path='tests/artifacts/openings-mobile-top.png',full_page=True)
    page.locator('.st-key-reference_footer').scroll_into_view_if_needed()
    page.screenshot(path='tests/artifacts/openings-mobile-navigation.png')
    buttons=page.locator('.st-key-reference_footer button')
    assert buttons.count()==4
    assert page.locator('.st-key-reference_nav_Aberturas button p').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
    assert max(buttons.nth(i).bounding_box()['y'] for i in range(4))-min(buttons.nth(i).bounding_box()['y'] for i in range(4))<5
    assert page.locator('[data-testid=stException]').count()==0
