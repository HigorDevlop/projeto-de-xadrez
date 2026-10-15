import pytest

from test_browser_components import browser_page
from test_opening_course_ui import course_server


@pytest.mark.parametrize('width', [1366, 390])
def test_short_tutorial_opens_playable_lesson(browser_page, course_server, width):
    from playwright.sync_api import expect
    page = browser_page
    page.set_viewport_size(dict(width=width, height=900))
    page.goto(course_server[0])
    page.get_by_text("Como funciona o treino", exact=True).click()
    tutorial = page.locator('.tutorial')
    expect(tutorial.get_by_role('heading', name='Veja a dica e jogue')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    runs = page.locator('#fixture-runs').get_attribute('data-runs')
    tutorial.get_by_role('button', name='Próximo', exact=True).click()
    expect(tutorial.get_by_text('Sem erro: 2 pontos', exact=False)).to_be_visible()
    tutorial.get_by_role('button', name='Próximo', exact=True).click()
    expect(tutorial.get_by_text('100 pontos por nível.', exact=False)).to_be_visible()
    assert page.locator('#fixture-runs').get_attribute('data-runs') == runs
    page.emulate_media(reduced_motion='reduce')
    assert tutorial.locator('.tiles span').evaluate('el=>getComputedStyle(el).animationName') == 'none'
    tutorial.get_by_role('button', name='Começar a jogar', exact=True).click()
    expect(page.locator('.board')).to_be_visible(timeout=15000)
    expect(page.locator('.square.movable').first).to_be_visible(timeout=15000)
    expect(page.get_by_role('button', name='Voltar ao curso')).to_be_visible()


def test_skip_tutorial_starts_practice(browser_page, course_server):
    from playwright.sync_api import expect
    page = browser_page
    page.goto(course_server[0])
    page.get_by_text("Como funciona o treino", exact=True).click()
    page.get_by_role('button', name='Jogar agora', exact=False).click()
    expect(page.locator('.board')).to_be_visible(timeout=15000)
