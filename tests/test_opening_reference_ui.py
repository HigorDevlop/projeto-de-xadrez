import time
import pytest
from test_browser_components import browser_page
from test_opening_course_ui import course_server, saved, current, ROOT
from test_endgame_training import endgame_server


@pytest.mark.parametrize('width',[1440,390])
def test_reference_catalog_and_course(browser_page,course_server,width):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    page=browser_page
    page.set_default_timeout(20000)
    page.set_viewport_size(dict(width=width,height=1000))
    page.goto(course_server[0])
    expect(page.locator('.home')).to_be_visible()
    expect(page.locator('.card')).to_have_count(12)
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.screenshot(path=str(ROOT/f'tests/artifacts/reference-home-{width}.png'),full_page=True)
    page.get_by_role('button',name='Ver todas ›').first.click()
    page.get_by_role('button',name='Outro',exact=True).click()
    page.get_by_role('searchbox').fill('English')
    expect(page.locator('.grid .card')).to_have_count(1)
    page.locator('[data-id=english]').click()
    expect(page.get_by_role('heading',name='English Opening',exact=True)).to_be_visible()
    expect(page.locator('.opening-progress-card')).to_be_visible()
    expect(page.get_by_text('Continuar a trilha',exact=True)).to_have_count(0)
    trophy=page.locator('.st-key-opening_achievements_button button')
    expect(trophy).to_have_count(1)
    expect(trophy).to_be_visible()
    trophy.click()
    expect(page.get_by_role('dialog')).to_be_visible()
    expect(page.get_by_role('dialog')).to_contain_text('Conquistas desta abertura')
    page.keyboard.press('Escape')
    expect(page.get_by_role('dialog')).to_have_count(0)
    expect(page.locator('.node.current')).to_have_count(1)
    page.screenshot(path=str(ROOT/f'tests/artifacts/reference-course-{width}.png'),full_page=True)
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    expect(page.locator('.training-hint')).to_have_count(1)
    page.screenshot(path=str(ROOT/f'tests/artifacts/reference-lesson-{width}.png'),full_page=True)
    assert page.locator('[data-testid=stException]').count()==0


def test_reference_wrong_move_completion_and_streak(browser_page,course_server):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    from opening_training_state import expected_move
    page=browser_page;page.set_default_timeout(20000)
    page.set_viewport_size(dict(width=1440,height=1000))
    url,folder=course_server
    page.goto(url)
    page.locator('[data-id=italian]').click()
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    # Wrong legal move is retained as a visible red arrow until Next.
    page.locator('[data-square=d2]').click();page.locator('[data-square=d4]').click()
    expect(page.get_by_role('button',name='Próximo',exact=True)).to_be_visible()
    expect(page.locator('.training-error-arrow')).to_have_count(1)
    expect(page.locator('.training-hint')).to_have_count(1)
    page.screenshot(path=str(ROOT/'tests/artifacts/reference-error.png'),full_page=True)
    assert current(folder)['history']==[]
    page.get_by_role('button',name='Próximo',exact=True).click()
    expect(page.get_by_role('button',name='Próximo',exact=True)).not_to_be_visible()
    deadline=time.monotonic()+160
    stages=set()
    while time.monotonic()<deadline:
        session=current(folder);stages.add(session['mode'])
        if session['phase']=='complete': break
        if session.get('ui_checkpoint'):
            page.get_by_role('button',name='Continuar',exact=True).click()
            
            for _ in range(100):
                if current(folder)['revision']!=session['revision']:break
                page.wait_for_timeout(50)
            continue
        if session['phase']=='answer':
            revision=f"{session['token']}:{session['revision']}"
            if page.locator('.board').get_attribute('data-revision')!=revision:
                page.wait_for_timeout(50);continue
            uci=expected_move(saved(folder),session)
            page.locator('[data-square='+uci[:2]+'].movable').click()
            page.locator('[data-square='+uci[2:]+']').click()
            for _ in range(100):
                if current(folder)['revision']!=session['revision']:break
                page.wait_for_timeout(50)
        else: page.wait_for_timeout(100)
    else: pytest.fail('A linha não concluiu')
    assert stages=={'learn','recall','quiz'}
    expect(page.get_by_text('Bom trabalho!',exact=True)).to_be_visible()
    awards=page.locator('.st-key-opening_award_status')
    expect(awards.locator('.achievement-unlock')).not_to_have_count(0)
    columns=page.locator('.st-key-opening_lesson_columns').bounding_box()
    assert awards.bounding_box()['y']>=columns['y']+columns['height']-1
    expect(awards.locator('img.achievement-medal').first).to_be_visible()
    assert awards.locator('img.achievement-medal').first.evaluate('(img)=>img.complete&&img.naturalWidth>0')
    page.screenshot(path=str(ROOT/'tests/artifacts/reference-complete.png'),full_page=True)
    page.get_by_role('button',name='Continuar',exact=True).click()
    expect(page.get_by_role('heading',name='Você salvou seu streak!',exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/'tests/artifacts/reference-streak.png'),full_page=True)
    assert sum(item['learned'] for item in saved(folder)['practice_progress'].values())==1
    page.get_by_role('button',name='Continuar',exact=True).click()
    expect(page.locator('.training-hint')).to_have_count(1)
    assert current(folder)['mode']=='learn'
    assert current(folder)['line_id']!=session['line_id']
    page.reload()
    page.locator('[data-id=italian]').click()
    expect(page.locator('.node.learned')).to_have_count(1)
    assert page.locator('[data-testid=stException]').count()==0


@pytest.mark.parametrize('screen', ['profile', 'award'])
def test_reference_profile_and_award_vectors(browser_page, course_server, screen):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    page = browser_page
    page.set_viewport_size(dict(width=1440,height=1000))
    page.goto(course_server[0]+'/?showcase='+screen)
    heading = 'Perfil' if screen == 'profile' else 'Parabéns!'
    expect(page.get_by_role('heading', name=heading, exact=True)).to_be_visible()
    target = page.locator('.reference-profile-card>img') if screen == 'profile' else page.locator('.reference-award .medal img')
    expect(target).to_be_visible()
    assert target.evaluate('(e)=>e.complete && e.naturalWidth > 0')
    if screen == 'profile':
        expect(page.get_by_text('Italian Game', exact=False)).to_be_visible()
    else:
        expect(page.get_by_text('25/25', exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/f'tests/artifacts/reference-{screen}.png'),full_page=True)
    assert page.locator('[data-testid=stException]').count() == 0


def test_reference_endgame_is_playable(browser_page,endgame_server):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    page=browser_page
    from urllib.parse import urlparse
    page.route('**/*', lambda route: route.continue_() if urlparse(route.request.url).hostname == '127.0.0.1' else route.abort())
    page.goto(endgame_server)
    page.locator('.st-key-reference_nav_Finais button').click(timeout=30000)
    page.get_by_role('button',name='Abrir Oposição direta',exact=True).click()
    page.locator('[data-square=e3]').click()
    page.locator('[data-square=e4]').click()
    expect(page.get_by_text('Você jogou Ke4.',exact=False)).to_be_visible()
    page.reload()
    page.locator('.st-key-reference_nav_Finais button').click(timeout=30000)
    expect(page.get_by_text('Você jogou Ke4.',exact=False)).to_be_visible()
    page.get_by_role('button',name='Repetir a posição',exact=True).click()
    expect(page.get_by_role('button',name='e3: rei branco',exact=True)).to_be_visible()
    page.locator('[data-square=e3]').click()
    page.locator('[data-square=e4]').click()
    expect(page.get_by_text('Lição concluída. Próxima revisão:',exact=False)).to_be_visible()
    expect(page.get_by_role('button',name='Abrir O rei à frente do peão',exact=True)).to_be_enabled()
    page.locator('.st-key-reference_nav_Aberturas button').click()
    expect(page.locator('.home')).to_be_visible()
