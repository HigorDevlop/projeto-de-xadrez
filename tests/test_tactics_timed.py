import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page,mount,image_asset
from tactics_session import remaining,expired


def test_deadline_is_separate_and_never_negative():
    assert remaining({}) is None
    assert not expired({})
    assert remaining({'tactic_deadline':100},95)==5
    assert remaining({'tactic_deadline':100},101)==0
    assert expired({'tactic_deadline':0})


@pytest.mark.parametrize('minutes',[1,3,5])
def test_machine_then_three_second_countdown(browser_page,minutes):
    page=browser_page
    page.clock.install(time='2026-10-25T03:00:00')
    page.clock.pause_at('2026-10-25T03:00:00')
    from tactic_art import theme_symbol
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo',art=theme_symbol('fork'))],token='one',machine=image_asset('tactics-gumball-cinematic.png'),gums=image_asset('tactics-gumballs-realistic.png'),coin=image_asset('tactics-coin-realistic.png')))
    page.get_by_role('button',name=f'{minutes} min',exact=True).click()
    expect(page.get_by_role('button',name=f'{minutes} min',exact=True)).to_have_attribute('aria-pressed','true')
    page.get_by_role('button',name='Começar').click()
    expect(page.locator('.gumball-machine')).to_be_visible()
    if minutes==3:
        page.clock.run_for(1200)
        page.evaluate("document.getAnimations().forEach(animation=>{animation.pause();animation.currentTime=1200})")
        page.screenshot(path='tests/artifacts/tactics-gumball-cinematic.png')
        page.clock.run_for(0)
    assert page.evaluate('window.events.length')==0
    page.clock.fast_forward(2800 if minutes==3 else 4000)
    expect(page.locator('.gumball-count')).to_have_text('3')
    page.clock.fast_forward(1000)
    expect(page.locator('.gumball-count')).to_have_text('2')
    page.clock.fast_forward(1000)
    expect(page.locator('.gumball-count')).to_have_text('1')
    page.clock.fast_forward(1000)
    assert page.evaluate('window.events[0].value')==dict(theme='fork',minutes=minutes,mechanism='automatic',token='one')
    page.screenshot(path=f'tests/artifacts/tactics-countdown-{minutes}.png')


def test_session_clock_expires_once_and_stops(browser_page):
    page=browser_page;page.clock.install()
    mount(page,'tactics_session.py',dict(remaining=60,duration=60,session='one'))
    expect(page.locator('strong')).to_have_text('01:00')
    page.clock.fast_forward(59000)
    expect(page.locator('strong')).to_have_text('00:01')
    page.clock.fast_forward(1000)
    expect(page.locator('strong')).to_have_text('00:00')
    page.clock.fast_forward(5000)
    assert page.evaluate('window.events')==[dict(key='finish',value='one')]


def test_cinematic_is_packaged_and_mobile_reduced_motion_works(browser_page):
    from tactics_orbit import machine_art
    page=browser_page;page.set_viewport_size(dict(width=390,height=844))
    page.emulate_media(reduced_motion='reduce')
    page.clock.install(time='2026-10-25T03:00:00')
    page.clock.pause_at('2026-10-25T03:00:00')
    art=machine_art()
    assert art.startswith('data:image/png;base64,')
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo',art='<svg></svg>')],token='one',machine=art))
    page.get_by_role('button',name='Começar').click()
    expect(page.locator('.machine-render')).to_be_visible()
    page.wait_for_function('document.querySelector(".machine-render").naturalWidth===1536')
    ball=page.locator('.orb').first.bounding_box()
    assert abs(ball['width']-ball['height'])<2
    assert page.locator('.gumball-machine').evaluate('node=>getComputedStyle(node).transform')=='none'
    assert page.locator('.gumball-token').evaluate('el=>getComputedStyle(el).animationName')=='none'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='tests/artifacts/tactics-cinematic-mobile.png')
    page.clock.fast_forward(7000)
    assert page.evaluate('window.events.length')==1


def test_coin_enters_external_slot_then_crank_turns_before_gum_exits(browser_page):
    from tactics_orbit import machine_art,coin_art
    from tactic_art import theme_symbol
    page=browser_page
    page.clock.install(time='2026-10-25T03:00:00')
    page.clock.pause_at('2026-10-25T03:00:00')
    mount(page,'tactics_orbit.py',dict(themes=[dict(id='fork',label='Garfo',art=theme_symbol('fork'))],token='coin-test',machine=machine_art(),coin=coin_art()))
    page.get_by_role('button',name='Começar').click()
    curtain=page.locator('.gumball-transition')
    expect(curtain).to_have_attribute('data-phase','coin')
    expect(page.locator('.gumball-glass .gumball-token')).to_have_count(0)
    assert page.locator('.gumball-token').evaluate('node=>getComputedStyle(node).animationName')=='cinematic-coin'
    assert page.locator('.machine-dispensed').evaluate('node=>getComputedStyle(node).opacity')=='0'
    def frame(milliseconds,name):
        page.evaluate('(time)=>document.getAnimations().forEach(animation=>{animation.pause();animation.currentTime=time})',milliseconds)
        page.screenshot(path=f'tests/artifacts/tactics-{name}.png')
    frame(500,'coin-insert')
    assert page.locator('.coin-path').evaluate('node=>getComputedStyle(node).overflow')=='hidden'
    assert page.locator('.gumball-token').evaluate('node=>{const m=new DOMMatrix(getComputedStyle(node).transform);return Math.hypot(m.m11,m.m12,m.m13)}')==pytest.approx(1,abs=.001)
    page.clock.fast_forward(1000)
    expect(curtain).to_have_attribute('data-phase','crank')
    frame(1500,'crank-turn')
    assert page.locator('.vault-rotor').evaluate('node=>getComputedStyle(node).transform') not in ('none','matrix(1, 0, 0, 1, 0, 0)')
    expect(page.locator('.vault-rotor>g')).to_have_count(6)
    assert page.locator('.vault-base').evaluate('node=>getComputedStyle(node).transform')=='none'
    assert page.locator('.machine-crank').evaluate('node=>getComputedStyle(node).backgroundImage')=='none'
    slit=page.locator('.machine-coin-entry i').bounding_box()
    mask=page.locator('.coin-path').bounding_box()
    assert slit['height']>slit['width']*5
    assert abs(mask['x']+mask['width']-slit['x']-slit['width'])<3
    page.clock.fast_forward(1150)
    expect(curtain).to_have_attribute('data-phase','dispense')
    frame(2450,'gum-exit')
    assert page.locator('.machine-hatch').evaluate('node=>getComputedStyle(node).transform')!='none'
    assert page.locator('.machine-dispensed').evaluate('node=>Number(getComputedStyle(node).opacity)')==1
    assert page.evaluate('window.events.length')==0
    page.clock.fast_forward(1850)
    expect(page.locator('.gumball-count')).to_have_text('3')
    # Only the numeral fades: the opaque black backdrop must never flash the machine.
    assert page.locator('.gumball-count').evaluate('node=>node.getAnimations().filter(a=>a instanceof Animation && a.effect.target===node && !(a instanceof CSSTransition)).length')==0
    assert page.locator('.gumball-count span').evaluate('node=>node.getAnimations().length')>=1
    page.clock.fast_forward(3000)
    assert page.evaluate('window.events.length')==1


def test_rotating_carousel_is_preserved_and_machine_uses_same_theme_art(browser_page):
    from tactics_orbit import machine_art,gum_art,THEME_COLORS
    from tactic_art import theme_symbol
    from tactics import THEMES
    page=browser_page;page.set_viewport_size(dict(width=1440,height=1050))
    page.clock.install(time='2026-10-25T03:00:00');page.clock.pause_at('2026-10-25T03:00:00')
    assert set(THEME_COLORS)==set(THEMES.values())
    assert len(set(THEME_COLORS.values()))==len(THEMES)
    mount(page,'tactics_orbit.py',dict(themes=[dict(id=value,label=label,art=theme_symbol(value),color=THEME_COLORS[value],sprite=list(THEME_COLORS).index(value)) for label,value in THEMES.items()],token='same-machine',machine=machine_art(),gums=gum_art()))
    expect(page.locator('.theme-gums .machine-gum')).to_have_count(len(THEMES))
    expect(page.locator('.machine-scene')).to_be_hidden()
    expect(page.locator('.orbit-stage')).to_be_visible()
    page.locator('.machine-render').evaluate('node=>window.originalMachine=node')
    page.screenshot(path='tests/artifacts/tactics-machine-themes.png')
    chosen=page.locator('.orb[data-theme=pin]')
    art=chosen.locator('.orb-diagram').inner_html()
    chosen.click()
    assert page.evaluate('window.originalMachine===document.querySelector(".machine-render") && window.originalMachine.isConnected')
    expect(page.locator('.machine-scene')).to_be_visible()
    backgrounds=page.locator('.machine-gum').evaluate_all('nodes=>nodes.map(node=>getComputedStyle(node).backgroundPosition)')
    assert len(set(backgrounds))==len(THEMES)
    assert all(value!='none' for value in backgrounds)
    assert page.locator('.machine-dispensed').evaluate('node=>getComputedStyle(node).backgroundPosition')==page.locator('.machine-gum[data-theme=pin]').evaluate('node=>getComputedStyle(node).backgroundPosition')
    page.screenshot(path='tests/artifacts/tactics-colored-gums.png')
    assert page.locator('.theme-gums [data-theme=pin] .orb-diagram').inner_html()==art
    assert page.locator('.machine-dispensed .orb-diagram').inner_html()==art
    for icon in page.locator('.machine-gum .orb-diagram,.machine-dispensed .orb-diagram').all():
        assert icon.evaluate('node=>getComputedStyle(node).opacity')=='1'
        assert icon.evaluate('node=>getComputedStyle(node).mixBlendMode')=='normal'
    box=page.locator('.gumball-machine').bounding_box()
    for ball in page.locator('.machine-gum').all():
        position=ball.bounding_box()
        assert box['y']+box['height']*.16<=position['y']<box['y']+box['height']*.44
    expect(page.locator('.machine-dispensed')).to_have_attribute('data-theme','pin')
    page.clock.fast_forward(3200)
    expect(page.locator('.machine-scene')).to_have_attribute('data-phase','zoom')
    page.evaluate('document.getAnimations().forEach(a=>{a.pause();a.currentTime=3700})')
    transform=page.locator('.machine-dispensed').evaluate('node=>new DOMMatrix(getComputedStyle(node).transform).a')
    assert transform>2
    # The shade must sit behind the selected gum, outside any lower stacking context.
    assert page.locator('.gumball-machine').evaluate('node=>getComputedStyle(node).isolation')=='auto'
    page.screenshot(path='tests/artifacts/tactics-selected-gum-zoom.png')
    assert page.evaluate('window.events.length')==0
    page.clock.fast_forward(800)
    expect(page.locator('.gumball-count')).to_have_text('3')
    page.clock.fast_forward(3000)
    assert page.evaluate('window.events[0].value.theme')=='pin'


@pytest.mark.parametrize('width,height',[(1440,1000),(390,844)])
def test_photographic_gums_have_alpha_and_rest_in_the_bowl(browser_page,width,height):
    from pathlib import Path
    from PIL import Image
    from tactics_orbit import gum_art,machine_art,THEME_COLORS
    from tactics import THEMES
    page=browser_page
    page.set_viewport_size(dict(width=width,height=height))
    page.clock.install(time='2026-10-25T03:00:00');page.clock.pause_at('2026-10-25T03:00:00')
    asset=Path(__file__).resolve().parents[1]/'assets/tactics-gumballs-realistic.png'
    with Image.open(asset) as image:
        assert image.mode=='RGBA'
        assert image.getextrema()[-1][0]==0 and image.getextrema()[-1][1]==255
    mount(page,'tactics_orbit.py',dict(themes=[dict(id=theme,label=label,color=THEME_COLORS[theme],sprite=i,art='') for i,(label,theme) in enumerate(THEMES.items())],token='bowl',machine=machine_art(),gums=gum_art()))
    page.get_by_role('button',name='Começar').click()
    expect(page.locator('.machine-gum.gum-photo')).to_have_count(20)
    box=page.locator('.gumball-machine').bounding_box()
    assert page.locator('.theme-gums').evaluate('node=>getComputedStyle(node).clipPath').startswith('polygon(')
    foreground=page.locator('.machine-foreground')
    assert foreground.get_attribute('src')==page.locator('.machine-render').get_attribute('src')
    assert foreground.evaluate('node=>getComputedStyle(node).clipPath').startswith('polygon(')
    assert foreground.evaluate('node=>Number(getComputedStyle(node).zIndex)')>page.locator('.theme-gums').evaluate('node=>Number(getComputedStyle(node).zIndex)')
    for ball in page.locator('.machine-gum').all():
        b=ball.bounding_box()
        assert b['y']>box['y']+box['height']*.30
        # Even the complete circles, before clipping, stay above the brass lip.
        assert b['y']+b['height']<box['y']+box['height']*.435
        assert b['width']<box['width']*.04
        assert ball.evaluate('node=>getComputedStyle(node).borderWidth')=='0px'
    page.evaluate('document.getAnimations().forEach(a=>{a.pause();a.currentTime=500})')
    page.screenshot(path=f'tests/artifacts/tactics-natural-candy-bowl-{width}.png')
