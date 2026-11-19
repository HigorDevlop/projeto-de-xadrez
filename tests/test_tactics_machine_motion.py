import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page,mount


@pytest.mark.parametrize('width',[1440,390])
def test_selection_sways_cabinet_and_rolls_candies_without_moving_street(browser_page,width):
    from tactics_orbit import machine_art,gum_art,coin_art,THEME_COLORS
    from tactic_art import theme_symbol
    page=browser_page;page.set_viewport_size(dict(width=width,height=1000))
    page.clock.install(time='2026-10-26T03:00:00');page.clock.pause_at('2026-10-26T03:00:00')
    themes=[dict(id=theme,label=theme,color=color,sprite=i,art=theme_symbol(theme)) for i,(theme,color) in enumerate(THEME_COLORS.items())]
    data=dict(themes=themes,token='sway',machine=machine_art(),gums=gum_art(),coin=coin_art())
    mount(page,'tactics_orbit.py',data)
    page.get_by_role('button',name='Manual',exact=True).click()
    page.get_by_role('button',name='Começar',exact=True).click()
    street=page.locator('.machine-render')
    before=street.bounding_box()
    page.evaluate('document.getAnimations().forEach(a=>{a.pause();a.currentTime=450})')
    assert street.bounding_box()==before
    assert street.evaluate('n=>getComputedStyle(n).transform')=='none'
    assert 'evenodd' in street.evaluate('n=>getComputedStyle(n).clipPath')
    cabinet=page.locator('.machine-assembly')
    assert cabinet.evaluate('n=>Math.abs(new DOMMatrix(getComputedStyle(n).transform).b)')>.0001
    motions=page.locator('.machine-gum').evaluate_all('nodes=>nodes.map(n=>getComputedStyle(n).translate+" "+getComputedStyle(n).rotate)')
    assert len(set(motions))>5
    assert all(m!='none none' for m in motions)
    assert page.locator('.theme-gums').evaluate('n=>getComputedStyle(n).clipPath').startswith('polygon(')
    assert page.evaluate('window.events.length')==0
    page.screenshot(path=f'tests/artifacts/tactics-machine-sway-{width}.png')
    page.evaluate('document.getAnimations().forEach(a=>{a.currentTime=1900})')
    assert cabinet.evaluate('n=>getComputedStyle(n).transform')=='none'
    assert page.locator('.machine-gum').evaluate_all('nodes=>nodes.every(n=>getComputedStyle(n).translate==="none" && getComputedStyle(n).rotate==="none")')
    page.get_by_role('button',name='Voltar',exact=True).click()
    expect(page.locator('.orbit-start')).to_be_visible()


def test_reduced_motion_keeps_cabinet_and_candies_still(browser_page):
    page=browser_page;page.emulate_media(reduced_motion='reduce')
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo')],token='still'))
    page.get_by_role('button',name='Manual',exact=True).click()
    page.get_by_role('button',name='Começar',exact=True).click()
    assert page.locator('.machine-assembly').evaluate('n=>n.getAnimations().length')==0
    assert page.locator('.machine-gum').evaluate('n=>n.getAnimations().length')==0
