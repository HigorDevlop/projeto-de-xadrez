"""Desktop catalogue filters compose with search without a server rerun."""
import pytest

from test_browser_components import browser_page
from test_opening_course_ui import course_server, ROOT


@pytest.mark.parametrize('width', [1440, 390])
def test_desktop_catalog_filters_and_layout(browser_page, course_server, width):
    from playwright.sync_api import expect
    from opening_repertoires import catalog

    page = browser_page
    page.set_viewport_size(dict(width=width, height=960))
    url, _ = course_server
    page.goto(url)
    expect(page.locator('.card')).to_have_count(12)
    before = page.locator('#fixture-runs').get_attribute('data-runs')
    page.get_by_role('button',name='Ver todas ›').first.click()
    for first in ('e4', 'd4'):
        page.get_by_role('button', name=first, exact=True).click()
        expected = {c['id'] for c in catalog() if c['side']=='white' and c['notation'].split()[0]=='1.'+first}
        seen=set()
        for _ in range(10):
            seen.update(page.locator('.grid .card').evaluate_all('(cards)=>cards.map(c=>c.dataset.id)'))
            next_page=page.get_by_role('button',name='Próxima página',exact=True)
            if next_page.is_disabled():break
            next_page.click()
        assert seen == expected
    page.get_by_role('searchbox').fill('Sicilian')
    expect(page.locator('.empty')).to_be_visible()
    page.get_by_role('button',name='e4',exact=True).click()
    expect(page.locator('.grid .card').first).to_be_visible()
    page.get_by_role('searchbox').fill('')
    page.get_by_role('button',name='Todos',exact=True).click()
    assert page.locator('.grid .card').count() > 1
    assert page.locator('#fixture-runs').get_attribute('data-runs') == before
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    if width > 1000:
        cards = page.locator('.grid .card')
        assert abs(cards.nth(0).bounding_box()['y'] - cards.nth(2).bounding_box()['y']) < 2
    page.screenshot(path=str(ROOT / f'tests/artifacts/desktop-catalog-{width}.png'), full_page=True)
