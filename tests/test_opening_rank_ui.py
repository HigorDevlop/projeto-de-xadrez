import pytest

from opening_course_state import select_course
from opening_ranking_state import ranking_state
from preparation_state import save_plan
from test_browser_components import browser_page
from test_opening_course_ui import course_server, saved, ROOT


@pytest.mark.parametrize('width', [1366, 390])
def test_saved_hundred_point_levels_survive_catalog_and_course(browser_page, course_server, monkeypatch, width):
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
        card = page.locator('[data-id=italian]')
        expect(card).to_be_visible()
        card.click()
        expect(page.get_by_role('heading',name='Italian Game',exact=True)).to_be_visible()
        expect(page.locator('.reference-rank')).to_be_visible()
        expect(page.locator('.reference-rank-caption')).to_contain_text('0/')
        assert saved(folder)['practice_ranking']['units'] == int(points*2)
        from opening_ranking_state import rank_summary
        score=rank_summary(saved(folder))
        assert score['rank']==rank and score['level']==level and score['level_points']==within
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if points == 499.5:
            page.screenshot(path=str(ROOT / f'tests/artifacts/aberturas-xp-{width}.png'), full_page=True)
