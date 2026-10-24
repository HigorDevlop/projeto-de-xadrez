import time

import pytest

from test_browser_components import browser_page
from test_opening_course_ui import course_server, current, saved, ROOT


@pytest.mark.parametrize('width', [1366, 390])
def test_home_search_ranking_and_pause(browser_page, course_server, width):
    from playwright.sync_api import expect
    expect.set_options(timeout=15000)
    page = browser_page
    page.set_default_timeout(15000)
    url, folder = course_server
    page.set_viewport_size(dict(width=width, height=900))
    page.goto(url)
    expect(page.locator('.card')).to_have_count(12)
    expect(page.locator('.card .preview svg')).to_have_count(12)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(ROOT / f'tests/artifacts/aberturas-home-{width}.png'), full_page=True)
    page.get_by_role('button',name='Ver todas ›').first.click()
    search = page.get_by_role('searchbox')
    search.fill('Sicilian')
    expect(page.locator('.card')).to_have_count(1)
    search.fill('inexistente')
    expect(page.get_by_text('Nenhuma abertura encontrada.')).to_be_visible()
    search.fill('')
    page.get_by_role('button',name='Voltar às aberturas',exact=True).click()
    page.locator('[data-id=london]').click()
    page.get_by_role('button', name='Treinar', exact=True).click()
    page.get_by_role('button', name='Pausar treino', exact=True).click()
    expect(page.get_by_role('button', name='Retomar treino', exact=True)).to_be_visible()
    paused = current(folder)
    assert paused['paused']
    page.wait_for_timeout(1800)
    assert current(folder)['history'] == paused['history']
    page.get_by_role('button', name='Retomar treino', exact=True).click()
    expect(page.get_by_role('button',name='Pausar treino',exact=True)).to_be_visible()
    assert current(folder)['history'] == paused['history']
    from opening_training_state import expected_move
    uci = expected_move(saved(folder), current(folder))
    page.locator('[data-square='+uci[:2]+'].movable').click()
    page.locator('[data-square='+uci[2:4]+']').click()
    deadline = time.monotonic() + 15
    while current(folder)['history'] == paused['history'] and time.monotonic() < deadline:
        page.wait_for_timeout(50)
    assert current(folder)['history'] != paused['history']
