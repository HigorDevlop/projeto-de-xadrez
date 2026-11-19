import chess
import pytest
from playwright.sync_api import expect
from interactive_board import position_data,piece_images
from test_browser_components import browser_page,mount,drag


def packet(fen,flip=False,revision=1):
    return dict(position_data(chess.Board(fen),flip),pieces=piece_images(),revision=revision,
                dark=True,trainingMode=True,stableBoard=True,ply=0,total=0,navigation=False)


@pytest.mark.parametrize('fen,origin,target,piece,flip',[
    ('7k/P7/8/8/8/8/8/7K w - - 0 1','a7','a8','q',False),
    ('7k/P7/8/8/8/8/8/7K w - - 0 1','a7','a8','n',True),
    ('1r5k/P7/8/8/8/8/8/7K w - - 0 1','a7','b8','r',False),
    ('7k/8/8/8/8/8/p7/7K b - - 0 1','a2','a1','b',True),
])
def test_click_promotion_waits_for_explicit_choice(browser_page,fen,origin,target,piece,flip):
    page=browser_page;page.set_viewport_size(dict(width=1000,height=1000))
    mount(page,'interactive_board.py',packet(fen,flip))
    page.locator(f'[data-square={origin}]').click();page.locator(f'[data-square={target}]').click()
    expect(page.get_by_role('dialog',name='Escolha a peça da promoção')).to_be_visible()
    expect(page.locator('.promotion-piece')).to_have_count(4)
    expect(page.locator('.promotion-piece>svg')).to_have_count(4)
    assert page.evaluate('window.events.length')==0
    page.locator(f'.promotion-piece[data-piece={piece}]').click()
    event=page.evaluate('window.events[0]')
    assert event['key']=='move'
    assert event['value']['uci']==origin+target+piece
    assert event['value']['fen']==fen
    assert event['value']['revision']==1
    expect(page.get_by_role('dialog')).to_have_count(0)


def test_drag_promotion_wheel_keyboard_and_cancel_preserve_position(browser_page):
    page=browser_page;page.set_viewport_size(dict(width=1000,height=1000))
    fen='7k/P7/8/8/8/8/8/7K w - - 0 1'
    mount(page,'interactive_board.py',packet(fen))
    drag(page,'a7','a8')
    expect(page.get_by_role('dialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.get_by_role('dialog')).to_have_count(0)
    assert page.evaluate('window.events.length')==0
    assert page.locator('.board').get_attribute('data-fen')==fen
    page.locator('[data-square=a7]').click();page.locator('[data-square=a8]').click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.keyboard.press('ArrowRight')
    expect(page.locator('.promotion-center strong')).to_have_text('Torre')
    page.keyboard.press('ArrowLeft')
    expect(page.locator('.promotion-center strong')).to_have_text('Dama')
    stage=page.locator('.promotion-orbit').bounding_box()
    page.mouse.move(stage['x']+stage['width']/2,stage['y']+stage['height']/2)
    page.mouse.down();page.mouse.move(stage['x']+stage['width']*.1,stage['y']+stage['height']/2,steps=12);page.mouse.up()
    expect(page.locator('.promotion-center strong')).to_have_text('Torre')
    assert page.evaluate('window.events.length')==0
    page.keyboard.press('Enter')
    assert page.evaluate('window.events[0].value.uci')=='a7a8r'


def test_wheel_survives_same_position_updates_and_rejects_stale_choice(browser_page):
    page=browser_page
    data=packet('7k/P7/8/8/8/8/8/7K w - - 0 1')
    mount(page,'interactive_board.py',data)
    page.locator('[data-square=a7]').click();page.locator('[data-square=a8]').click()
    page.locator('.promotion-piece[data-piece=n]').evaluate('node=>window.oldPromotion=node')
    page.evaluate('(data)=>window.render(data)',data)
    expect(page.get_by_role('dialog')).to_be_visible()
    page.evaluate('(data)=>window.render(data)',packet(chess.STARTING_FEN,revision=2))
    expect(page.get_by_role('dialog')).to_have_count(0)
    page.evaluate('window.oldPromotion.click()')
    assert page.evaluate('window.events.length')==0


def test_mobile_promotion_stays_inside_board_and_tab_focus_is_contained(browser_page):
    page=browser_page;page.set_viewport_size(dict(width=390,height=844))
    mount(page,'interactive_board.py',packet('7k/8/8/8/8/8/p7/7K b - - 0 1',True))
    page.locator('[data-square=a2]').click();page.locator('[data-square=a1]').click()
    modal=page.get_by_role('dialog').bounding_box();board=page.locator('.board-stage').bounding_box()
    assert modal['x']>=board['x'] and modal['x']+modal['width']<=board['x']+board['width']+1
    assert modal['y']>=board['y'] and modal['y']+modal['height']<=board['y']+board['height']+1
    for _ in range(7):
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.closest(".promotion-dialog")!==null')
    page.screenshot(path='tests/artifacts/promotion-wheel-mobile.png')
    page.get_by_role('button',name='Cancelar · Esc').click()
    assert page.evaluate('window.events.length')==0
