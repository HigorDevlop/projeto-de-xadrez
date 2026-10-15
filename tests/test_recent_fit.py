import pytest
from pathlib import Path
from test_browser_components import browser_page, mount
from recent_games import cards_data


@pytest.mark.parametrize('width,height',[(1861,935),(1366,768),(390,844),(844,390)])
def test_recent_cards_fit_available_viewport(browser_page,width,height):
    page=browser_page
    page.set_viewport_size(dict(width=width,height=height))
    game={'pgn':'[White "demo"]\n[Black "opponent"]\n\n1. e4 e5 *','white':{'username':'demo'},'black':{'username':'opponent'}}
    history=[dict(game,url=str(index),end_time=index) for index in range(8)]
    mount(page,'recent_games.py',dict(cards=cards_data(history,'demo',{}),dark=True,revision='fit'))
    page.add_style_tag(content='body{margin:0;padding:180px 12px 0}main{display:block}')
    page.evaluate("window.dispatchEvent(new Event('resize'))")
    page.wait_for_timeout(150)
    grid=page.locator('.recent-grid').bounding_box()
    pager=page.locator('.recent-pages')
    bottom=grid['y']+grid['height']
    if pager.is_visible():
        box=pager.bounding_box()
        bottom=box['y']+box['height']
        last=pager.locator('button').last
        last.click()
        assert page.locator('.game-number').last.text_content() == 'Partida 08'
    assert bottom<=height
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    if width>1050:
        assert page.locator('article').count()==8
    artifacts=Path(__file__).with_name('artifacts')
    page.screenshot(path=str(artifacts/f'home-fit-{width}x{height}.png'))
