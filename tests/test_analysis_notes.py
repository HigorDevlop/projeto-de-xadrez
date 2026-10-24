import chess
from playwright.sync_api import expect
from interactive_board import annotation_rows, game_frames, piece_images, position_data
from test_browser_components import browser_page, mount


def test_notes_match_board_height_and_navigate_without_waiting_for_python(browser_page):
    page=browser_page
    page.set_viewport_size({'width':1400,'height':960})
    pgn='1. e4 {Controle do centro.} e5 2. Nf3 Nc6 *'
    data={**position_data(chess.Board()), 'revision':0, 'ply':0, 'total':4, 'navigation':True,
          'expanded':True, 'epoch':'notes-test', 'frames':game_frames(pgn), 'pieces':piece_images(),
          'analysisNotes':annotation_rows(pgn)}
    mount(page,'interactive_board.py',data)
    panel=page.locator('.analysis-notes')
    expect(panel).to_be_visible()
    page.wait_for_function("Math.abs(document.querySelector('.analysis-notes').getBoundingClientRect().height-document.querySelector('.board').getBoundingClientRect().height)<2")
    board=page.locator('.board').bounding_box();notes=panel.bounding_box()
    assert abs(board['y']-notes['y'])<2
    assert notes['x']>board['x']+board['width']
    page.get_by_role('button',name='1. e4',exact=True).click()
    expect(page.locator('[data-square=e4]')).to_have_attribute('aria-label','e4: peão branco')
    expect(panel.locator('[aria-current=true]')).to_have_text('e4')
    expect(panel.locator('.notes-comment')).to_have_text('Controle do centro.')
    page.get_by_role('button',name='2... Nc6',exact=True).click()
    expect(page.locator('[data-square=c6]')).to_have_attribute('aria-label','c6: cavalo preto')
    page.keyboard.press('ArrowLeft')
    expect(panel.locator('[aria-current=true]')).to_have_text('Nf3')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert panel.bounding_box()['y']>page.locator('.board').bounding_box()['y']


def test_comments_are_attached_to_black_starting_fen():
    pgn='[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/4P3/4K3 b - - 0 17"]\n\n17... Kd7 {Rei ativo.} *'
    row=annotation_rows(pgn)[0]
    assert (row['side'],row['number'],row['san'],row['comment'])==('black',17,'Kd7','Rei ativo.')
    assert annotation_rows('1. e4 $1 *')[0]['symbol']=='!'
