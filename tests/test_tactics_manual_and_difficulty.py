import math
import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page,mount
from tactics_progress import RANKS,record,summary
from tactics_difficulty import target_rating,completed,training_range


def test_five_divisions_preserve_existing_points(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    assert len(RANKS)==30 and len({t for t,_ in RANKS})==30
    for i in range(40):
        record('one',str(i),str(i),'fork',True,True)
        if i==7:assert summary('one')['rank']=='Bronze 2'
        if i==31:assert summary('one')['rank']=='Bronze 5'
    assert summary('one')['rank']=='Prata 1'
    assert summary('one')['xp']==200
    assert summary('other')['rank']=='Bronze 1'


def test_difficulty_uses_only_clean_distinct_solutions_and_has_a_ceiling():
    state={};assert target_rating(state)==500
    completed(state,'one',False);assert target_rating(state)==500
    completed(state,'one',True);completed(state,'one',True)
    assert state['tactic_difficulty_hits']==1
    completed(state,'two',True);assert target_rating(state)==600
    for i in range(100):completed(state,str(i),True)
    assert target_rating(state)==3000


def test_offline_selection_grows_and_handles_rare_themes():
    from tactics import fetch_puzzle_range
    from offline_tactics import LocalBankExhausted
    low,high=training_range('fork',0,4000,set(),500)
    assert high<=700
    first=fetch_puzzle_range('fork',low,high)
    low2,high2=training_range('fork',0,4000,{first.id},1700)
    assert low2>high
    assert fetch_puzzle_range('fork',low2,high2,{first.id}).rating>first.rating
    low,high=training_range('underPromotion',0,4000,set(),500)
    assert fetch_puzzle_range('underPromotion',low,high).rating<1100
    with pytest.raises(LocalBankExhausted):training_range('fork',0,10,set(),500)


@pytest.mark.parametrize('width',[1440,390])
def test_manual_coin_drag_and_wheel_hold_until_user_finishes(browser_page,width):
    from tactics_orbit import coin_art,machine_art,gum_art
    from tactic_art import theme_symbol
    page=browser_page;page.set_viewport_size(dict(width=width,height=1000))
    page.clock.install(time='2026-10-25T03:00:00');page.clock.pause_at('2026-10-25T03:00:00')
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo',art=theme_symbol('fork'))],token='manual',machine=machine_art(),gums=gum_art(),coin=coin_art()))
    page.get_by_role('button',name='Manual',exact=True).click()
    page.get_by_role('button',name='Começar',exact=True).click()
    expect(page.locator('.machine-scene')).to_have_attribute('data-phase','manual-coin')
    page.clock.fast_forward(25000)
    assert page.evaluate('window.events.length')==0
    assert page.locator('.machine-hatch').evaluate('n=>getComputedStyle(n).animationName')=='none'
    page.screenshot(path=f'tests/artifacts/tactics-manual-coin-{width}.png')
    coin=page.locator('.gumball-token').bounding_box()
    x,y=coin['x']+coin['width']/2,coin['y']+coin['height']/2
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+coin['width'],y,steps=10);page.mouse.up()
    page.clock.fast_forward(250)
    expect(page.locator('.machine-scene')).to_have_attribute('data-phase','manual-crank')
    page.screenshot(path=f'tests/artifacts/tactics-manual-wheel-{width}.png')
    wheel=page.locator('.machine-crank').bounding_box()
    cx,cy,r=wheel['x']+wheel['width']/2,wheel['y']+wheel['height']/2,wheel['width']*.4
    page.mouse.move(cx+r,cy);page.mouse.down()
    for degrees in range(15,361,15):
        if degrees==180:
            page.mouse.up();page.mouse.down()
        angle=math.radians(degrees);page.mouse.move(cx+r*math.cos(angle),cy+r*math.sin(angle))
    page.mouse.up();page.clock.fast_forward(500)
    assert page.evaluate('window.events.length')==0
    page.clock.fast_forward(2200)
    expect(page.locator('.gumball-count')).to_have_text('3')
    page.clock.fast_forward(3000)
    assert page.evaluate('window.events[0].value.mechanism')=='manual'
    assert page.evaluate('window.events[0].value.theme')=='fork'


def test_manual_cancel_and_keyboard_controls(browser_page):
    page=browser_page
    page.clock.install(time='2026-10-25T03:00:00');page.clock.pause_at('2026-10-25T03:00:00')
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo')],token='keys'))
    page.get_by_role('button',name='Manual',exact=True).click();page.get_by_role('button',name='Começar',exact=True).click()
    page.get_by_role('button',name='Voltar',exact=True).click()
    expect(page.locator('.orbit-start')).to_be_visible()
    page.get_by_role('button',name='Começar',exact=True).click()
    page.locator('.gumball-token').focus();page.keyboard.press('Enter');page.clock.fast_forward(250)
    page.locator('.machine-crank').focus();page.keyboard.press('Enter');page.clock.fast_forward(500);page.clock.fast_forward(5500)
    assert page.evaluate('window.events.length')==1


def test_machine_mode_preference_is_remembered(browser_page):
    page=browser_page
    page.route('http://coach.test/**',lambda route:route.fulfill(body='<html></html>',content_type='text/html'))
    page.goto('http://coach.test/')
    data=dict(themes=[dict(id='fork',label='Garfo')],token='preference')
    mount(page,'tactics_orbit.py',data)
    page.get_by_role('button',name='Manual',exact=True).click()
    mount(page,'tactics_orbit.py',data)
    expect(page.get_by_role('button',name='Manual',exact=True)).to_have_attribute('aria-pressed','true')
