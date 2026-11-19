from pathlib import Path
from PIL import Image
from playwright.sync_api import expect
from test_browser_components import browser_page,mount


def test_coin_uses_real_metal_angles_and_enters_before_vault_turn(browser_page):
    from tactics_orbit import coin_art,machine_art,gum_art
    from tactic_art import theme_symbol
    path=Path(__file__).resolve().parents[1]/'assets/tactics-coin-aged-metal.png'
    with Image.open(path) as image:
        assert image.mode=='RGBA' and image.width==image.height
        assert image.getextrema()[-1]==(0,255)
    page=browser_page;page.set_viewport_size(dict(width=1440,height=1000))
    page.clock.install(time='2026-10-25T03:00:00');page.clock.pause_at('2026-10-25T03:00:00')
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo',art=theme_symbol('fork'),sprite=1)],token='real-coin',machine=machine_art(),gums=gum_art(),coin=coin_art()))
    page.get_by_role('button',name='Começar').click()
    # Explicit visibility on carousel spheres must not leak through the reveal.
    assert page.locator('.orbit').evaluate('n=>getComputedStyle(n).opacity')=='0'
    assert page.locator('.coin-surface').evaluate('n=>getComputedStyle(n).backgroundImage').startswith('url("data:image/png;base64,')
    assert page.locator('.machine-coin-entry').evaluate('n=>getComputedStyle(n).backgroundImage')==page.locator('.coin-surface').evaluate('n=>getComputedStyle(n).backgroundImage')
    assert page.locator('.gumball-token').evaluate('n=>getComputedStyle(n).borderWidth')=='0px'
    assert page.locator('.gumball-token').evaluate('n=>getComputedStyle(n,"::before").display')=='none'
    positions=[]
    for milliseconds,label in ((180,'front'),(500,'turn'),(800,'edge')):
        page.evaluate('(t)=>document.getAnimations().forEach(a=>{a.pause();a.currentTime=t})',milliseconds)
        positions.append(page.locator('.coin-surface').evaluate('n=>getComputedStyle(n).backgroundPosition'))
        assert page.locator('.gumball-token').evaluate('n=>new DOMMatrix(getComputedStyle(n).transform).m11')==1
        assert page.locator('.gumball-token').evaluate('n=>new DOMMatrix(getComputedStyle(n).transform).m42')==0
        page.screenshot(path=f'tests/artifacts/real-coin-{label}.png')
    assert len(set(positions))==3
    assert page.evaluate('window.events.length')==0
    page.clock.fast_forward(1000)
    expect(page.locator('.machine-scene')).to_have_attribute('data-phase','crank')
    page.clock.fast_forward(6000)
    assert page.evaluate('window.events[0].value.theme')=='fork'
