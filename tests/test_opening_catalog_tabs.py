"""The opening catalog has one tab per playing color."""
from design_tokens import palette
from opening_catalog_ui import catalog_cards
from test_browser_components import browser_page, mount


def catalog_data():
    return dict(courses=catalog_cards(), colors=palette(False), selected=[],
                start='2026-09-30', end='2026-10-06', valid=True)


def test_two_color_tabs_keep_selections_and_include_all_black_openings(browser_page):
    page = browser_page
    data = catalog_data()
    mount(page, 'opening_catalog_ui.py', data)
    assert page.get_by_role('tab').all_text_contents() == ['Brancas', 'Pretas']
    assert page.locator('.card').count() == sum(c['side'] == 'white' for c in data['courses'])
    page.locator('[data-id=london]').click()
    page.locator('[data-id=e4]').click()
    page.get_by_role('tab', name='Pretas', exact=True).click()
    black_ids = {c['id'] for c in data['courses'] if c['side'] == 'black'}
    visible_ids = set(page.locator('.card').evaluate_all('(cards)=>cards.map(card=>card.dataset.id)'))
    assert visible_ids == black_ids
    page.locator('[data-id=caro]').click()
    page.locator('[data-id=slav]').click()
    assert page.locator('[data-id=nimzo]').is_disabled()
    page.get_by_role('tab', name='Brancas', exact=True).click()
    assert page.locator('[data-id=london]').get_attribute('aria-pressed') == 'true'
    page.locator('[data-id=london]').click()
    page.get_by_role('tab', name='Pretas', exact=True).click()
    assert page.locator('[data-id=nimzo]').is_enabled()
    page.locator('[data-id=nimzo]').click()
    # Parent rerenders (e.g. date changes) preserve both color selections.
    page.evaluate('(data)=>window.render(data)', data)
    assert page.get_by_role('tab', name='Pretas', exact=True).get_attribute('aria-selected') == 'true'
    assert page.locator('.counter').inner_text() == 'Aberturas Selecionadas: [4/4]'
    page.locator('.confirm').click()
    assert page.evaluate('window.events[0].value.ids') == ['e4', 'caro', 'slav', 'nimzo']


def test_color_tabs_keyboard_wrap_and_mobile_layout(browser_page):
    page = browser_page
    page.set_viewport_size({'width': 390, 'height': 844})
    mount(page, 'opening_catalog_ui.py', catalog_data())
    page.get_by_role('tab', name='Brancas', exact=True).focus()
    for key, label in [('ArrowLeft', 'Pretas'), ('ArrowRight', 'Brancas'),
                       ('End', 'Pretas'), ('Home', 'Brancas'),
                       ('ArrowRight', 'Pretas'), ('ArrowRight', 'Brancas')]:
        page.keyboard.press(key)
        active = page.get_by_role('tab', name=label, exact=True)
        assert active.get_attribute('aria-selected') == 'true'
        assert active.evaluate('(tab)=>document.activeElement===tab')
        assert page.locator('[role=tab][tabindex="0"]').count() == 1
        assert page.get_by_role('tabpanel').get_attribute('aria-labelledby') == active.get_attribute('id')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
