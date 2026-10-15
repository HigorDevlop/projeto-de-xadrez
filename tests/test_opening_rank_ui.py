import pytest

from opening_course_state import select_course
from opening_ranking_state import ranking_state
from preparation_state import save_plan
from test_browser_components import browser_page
from test_opening_course_ui import course_server, ROOT


@pytest.mark.parametrize('width', [1366, 390])
def test_hundred_point_levels_in_catalog_and_course(browser_page, course_server, monkeypatch, width):
    from playwright.sync_api import expect
    expect.set_options(timeout=15000)
    page = browser_page
    url, folder = course_server
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(folder))
    page.set_viewport_size(dict(width=width, height=1000))
    cases = [(99, 'Bronze', 1, 99), (100, 'Bronze', 2, 0),
             (499.5, 'Bronze', 5, 99.5), (500, 'Prata', 1, 0)]
    for points, rank, level, within in cases:
        plan = select_course(None, 'browser-openings', 'italian')
        score = ranking_state(plan)
        score.update(units=int(points * 2), floor=int(points // 500) * 1000)
        save_plan(plan, namespace='openings')
        page.goto(url)
        page.get_by_text("Como funciona o treino", exact=True).click()
        card = page.locator('[data-id=italian]')
        expect(card.locator('.rank')).to_have_text(f'{rank} · nível {level}')
        assert card.locator('progress').get_attribute('value') == str(within / 100).removesuffix('.0')
        page.locator('.tutorial').get_by_role('button', name='Próximo', exact=True).click()
        page.locator('.tutorial').get_by_role('button', name='Próximo', exact=True).click()
        expect(page.get_by_text('100 pontos por nível. Cinco níveis por faixa. Cada abertura tem seu próprio progresso.', exact=True)).to_be_visible()
        card.click()
        expected = f'{within:g}'.replace('.', ',') + ' / 100 XP'
        expect(page.get_by_text(expected, exact=True)).to_be_visible()
        progress = page.locator('.opening-xp-track')
        expect(progress).to_have_attribute('aria-valuenow', str(float(within)))
        page.wait_for_function('''() => {
            const xp = document.querySelector('.opening-rank');
            const header = document.querySelector('[data-testid="stHeader"]');
            return xp && header && xp.getBoundingClientRect().top >= header.getBoundingClientRect().bottom;
        }''')
        xp = page.locator('.opening-rank').bounding_box()
        header = page.locator('[data-testid="stHeader"]').bounding_box()
        back = page.get_by_role('button', name='Todas as aberturas').bounding_box()
        title = page.get_by_role('heading', name='Italiana', exact=True).bounding_box()
        assert xp['y'] + xp['height'] <= back['y']
        assert xp['y'] >= header['y'] + header['height']
        assert xp['y'] < title['y']
        assert page.get_by_text('Próximo rank', exact=True).count() == 0
        assert page.get_by_text('linhas aprendidas', exact=False).count() == 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if points == 499.5:
            page.screenshot(path=str(ROOT / f'tests/artifacts/aberturas-xp-{width}.png'), full_page=True)
