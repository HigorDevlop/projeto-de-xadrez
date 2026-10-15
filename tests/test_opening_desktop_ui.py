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
    for first in ('e4', 'd4'):
        page.get_by_role('button', name='1. ' + first, exact=True).click()
        expected = [c for c in catalog() if c['notation'].split()[0] == '1.' + first]
        expect(page.locator('.card')).to_have_count(len(expected))
        assert set(page.locator('.card').evaluate_all('(cards)=>cards.map(c=>c.dataset.id)')) == {c['id'] for c in expected}
    page.get_by_role('searchbox').fill('siciliana')
    expect(page.locator('.empty')).to_be_visible()
    page.get_by_role('button', name='1. e4', exact=True).click()
    expect(page.locator('.card')).to_have_count(1)
    page.get_by_role('searchbox').fill('')
    page.get_by_role('button', name='Todas', exact=True).click()
    expect(page.locator('.card')).to_have_count(12)
    assert page.locator('#fixture-runs').get_attribute('data-runs') == before
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    if width > 1000:
        cards = page.locator('.rail').first.locator('.card')
        assert abs(cards.nth(0).bounding_box()['y'] - cards.nth(2).bounding_box()['y']) < 2
    page.screenshot(path=str(ROOT / f'tests/artifacts/desktop-catalog-{width}.png'), full_page=True)
