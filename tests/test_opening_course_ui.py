import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import pytest

from test_browser_components import browser_page

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def course_server(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    env = dict(os.environ,ACERVO_PREPARATION_DIR=str(tmp_path))
    process = subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'tests/opening_course_fixture.py'),
        '--server.headless=true',f'--server.port={port}','--browser.gatherUsageStats=false'],cwd=ROOT,env=env,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:
                with urlopen(url+'/_stcore/health',timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        yield url,tmp_path
    finally:
        process.terminate()
        process.wait(timeout=15)


def saved(folder):
    # Windows may briefly lock the destination during its atomic replacement.
    for _ in range(30):
        try:
            return json.loads(next((folder/'openings').glob('*.json')).read_text(encoding='utf8'))
        except (PermissionError, FileNotFoundError):
            time.sleep(.01)
    raise AssertionError('Não foi possível ler o progresso salvo')


def current(folder):
    plan = saved(folder)
    return plan['practice_sessions'][plan['practice_current']]


def wait_phase(page,folder,phases):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        session=current(folder)
        if session['phase'] in phases:
            page.wait_for_timeout(150)
            return session
        page.wait_for_timeout(40)
    pytest.fail('Treinamento não retornou a uma fase interativa')


@pytest.mark.parametrize('width,dark',[(1366,False),(390,True)])
def test_course_trail_training_quiz_and_persistence(browser_page,course_server,width,dark):
    from playwright.sync_api import expect
    expect.set_options(timeout=15000)
    page=browser_page
    page.set_default_timeout(15000)
    url,folder=course_server
    page.set_viewport_size(dict(width=width,height=900))
    page.goto(url+('?theme=dark' if dark else ''))
    page.locator('[data-id=italian]').click()
    expect(page.get_by_role('heading',name='Italiana',exact=True)).to_be_visible()
    expect(page.locator('.node')).to_have_count(7)
    assert page.locator('.node:disabled').count()==6
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    artifacts=ROOT/'tests/artifacts'
    artifacts.mkdir(exist_ok=True)
    page.screenshot(path=str(artifacts/f'aberturas-curso-{width}.png'),full_page=True)
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    expect(page.locator('.training-hint')).to_have_count(1)
    page.screenshot(path=str(artifacts/f'aberturas-aprender-{width}.png'),full_page=True)
    # All learner moves are manual; opponent replies and phase changes are automatic.
    first_line = current(folder)['line_id']
    page.locator('.board').evaluate('''board => {
        window.lessonBoard = board;
        window.lessonSquares = [...board.children];
        window.lessonRuns = document.querySelector('#fixture-runs').dataset.runs;
    }''')
    lesson_deadline = time.monotonic() + 90
    while time.monotonic() < lesson_deadline:
        if any(item['learned'] for item in saved(folder)['practice_progress'].values()):
            break
        session = current(folder)
        if session['phase'] == 'answer':
            assert page.locator('.board').evaluate('''board =>
                board === window.lessonBoard &&
                window.lessonSquares.every((node, index) => node === board.children[index]) &&
                document.querySelector('#fixture-runs').dataset.runs === window.lessonRuns''')
            from opening_training_state import expected_move
            uci = expected_move(saved(folder), session)
            if page.locator('.board').get_attribute('data-revision') != f"{session['token']}:{session['revision']}":
                page.wait_for_timeout(50)
                continue
            page.locator('[data-square='+uci[:2]+'].movable').click()
            page.locator('[data-square='+uci[2:]+']').click()
            deadline = time.monotonic()+10
            while current(folder)['revision'] == session['revision'] and time.monotonic() < deadline:
                page.wait_for_timeout(40)
        else:
            page.wait_for_timeout(350)
    else:
        pytest.fail('A linha não concluiu automaticamente')
    # The next line begins automatically; returning preserves the new progress.
    deadline = time.monotonic() + 15
    while current(folder)['line_id'] == first_line and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert current(folder)['line_id'] != first_line
    expect(page.locator('.board')).to_be_visible()
    page.get_by_role('button',name='Voltar ao curso').click()
    expect(page.locator('.course-trail')).to_be_visible()
    assert page.locator('.node:disabled').count()==5

    assert sum(p['learned'] for p in saved(folder)['practice_progress'].values())==1
    page.get_by_text('Dominar',exact=True).click()
    expect(page.get_by_role('button',name='Revisar agora',exact=True)).to_be_visible()
    page.get_by_text('Aprofundar',exact=True).click()
    expect(page.get_by_text('Explore cada variação e seus lances. A exploração não altera seu domínio.',exact=True)).to_be_visible()
    page.get_by_role('button',name='Todas as aberturas').click()
    page.locator('[data-id=caro]').click()
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    wait_phase(page,folder,('answer',))
    expect(page.locator('[data-square=h8] .file')).to_have_text('h')
    page.get_by_role('button',name='Voltar ao curso').click()
    page.get_by_role('button',name='Todas as aberturas').click()
    page.locator('[data-id=italian]').click()
    expect(page.get_by_role('heading',name='Italiana',exact=True)).to_be_visible()
    expect(page.locator('.course-trail')).to_be_visible()
    assert sum(p['learned'] for p in saved(folder)['practice_progress'].values())==1
    page.reload()
    expect(page.locator('.home')).to_be_visible()
    page.locator('[data-id=italian]').click()
    expect(page.locator('.course-trail')).to_be_visible()
    assert page.locator('.node:disabled').count()==5


def test_dark_mobile_course_has_readable_rank(browser_page,course_server):
    from playwright.sync_api import expect
    page = browser_page
    url, _ = course_server
    page.set_viewport_size(dict(width=390,height=900))
    page.goto(url+'?theme=dark')
    page.locator('[data-id=italian]').click()
    expect(page.locator('.node')).to_have_count(7)
    colors = page.locator('.opening-rank').evaluate('''element => ({
        background: getComputedStyle(element).backgroundColor,
        foreground: getComputedStyle(element.querySelector('strong')).color
    })''')
    def luminance(rgb):
        channels = [int(value) / 255 for value in rgb.removeprefix('rgb(').removesuffix(')').split(',')]
        linear = [value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4 for value in channels]
        return sum(value*weight for value, weight in zip(linear,(.2126,.7152,.0722)))
    light, dark = sorted(map(luminance, colors.values()),reverse=True)
    assert (light+.05)/(dark+.05) >= 4.5
    artifacts = ROOT/'tests/artifacts'
    page.screenshot(path=str(artifacts/'aberturas-curso-390.png'),full_page=True)
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    page.screenshot(path=str(artifacts/'aberturas-aprender-390.png'),full_page=True)
