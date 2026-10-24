import chess
from playwright.sync_api import expect
from tactics_preview import answer_preview
from interactive_board import position_data,piece_images
from test_browser_components import browser_page,mount,drag

SOLUTION=('e2e4','e7e5','g1f3','b8c6','f1c4')


def data_for(progress,revision):
    board=chess.Board()
    for move in SOLUTION[:progress]:board.push_uci(move)
    return {**position_data(board),'revision':revision,'ply':0,'total':0,'navigation':False,
        'pieces':piece_images(),'stableBoard':True,'trainingMode':True,
        'trainingExpected':SOLUTION[progress],'trainingPreview':answer_preview(chess.STARTING_FEN,SOLUTION,progress)}


def test_preloaded_transition_matches_authoritative_solver_including_last_move():
    from tactics import Puzzle,solve_move
    puzzle=Puzzle('preview',chess.STARTING_FEN,SOLUTION,1200,('mix',))
    for progress in (0,2,4):
        preview=answer_preview(puzzle.fen,SOLUTION,progress)
        next_progress,_=solve_move(puzzle,progress,SOLUTION[progress],preview['sourceFen'])
        board=chess.Board()
        for move in SOLUTION[:next_progress]:board.push_uci(move)
        assert preview['position']['fen']==board.fen()
    assert answer_preview(puzzle.fen,SOLUTION,len(SOLUTION)) is None


def test_player_and_reply_show_immediately_while_python_is_delayed(browser_page):
    page=browser_page;data=data_for(0,1)
    mount(page,'interactive_board.py',data)
    result=page.evaluate('''()=>{
      const board=document.querySelector('.board'),squares=[...board.children];
      document.querySelector('[data-square=e2]').click();document.querySelector('[data-square=e4]').click();
      return {same:squares.every((node,i)=>node===board.children[i]),
        white:document.querySelector('[data-square=e4]').getAttribute('aria-label'),
        black:document.querySelector('[data-square=e5]').getAttribute('aria-label'),
        event:window.events[0].value};
    }''')
    assert result['same'] and result['white']=='e4: peão branco' and result['black']=='e5: peão preto'
    assert result['event']['fen']==chess.STARTING_FEN and result['event']['revision']==1
    # Preview does not count another attempt or bypass authoritative validation.
    page.locator('[data-square=g1]').click();page.locator('[data-square=f3]').click()
    assert page.evaluate('window.events.length')==1
    page.evaluate('(data)=>window.render(data)',data_for(2,2))
    drag(page,'g1','f3')
    expect(page.locator('[data-square=f3]')).to_have_attribute('aria-label','f3: cavalo branco')
    expect(page.locator('[data-square=c6]')).to_have_attribute('aria-label','c6: cavalo preto')
    assert page.evaluate('window.events.at(-1).value.revision')==2


def test_wrong_answer_never_previews_the_solution(browser_page):
    page=browser_page;mount(page,'interactive_board.py',data_for(0,1))
    drag(page,'d2','d4')
    expect(page.locator('[data-square=d2]')).to_have_attribute('aria-label','d2: peão branco')
    expect(page.locator('[data-square=e5]')).to_have_attribute('aria-label','e5: vazia')
    assert page.evaluate('window.events[0].value.uci')=='d2d4'


def test_black_drag_also_preloads_white_reply(browser_page):
    page=browser_page;board=chess.Board();board.push_uci('e2e4')
    moves=('e7e5','g1f3','b8c6')
    data={**position_data(board,True),'revision':1,'ply':0,'total':0,'navigation':False,
        'pieces':piece_images(),'stableBoard':True,'trainingMode':True,'trainingExpected':moves[0],
        'trainingPreview':answer_preview(board.fen(),moves,0)}
    mount(page,'interactive_board.py',data)
    drag(page,'e7','e5')
    expect(page.locator('[data-square=e5]')).to_have_attribute('aria-label','e5: peão preto')
    expect(page.locator('[data-square=f3]')).to_have_attribute('aria-label','f3: cavalo branco')
    assert page.evaluate('window.events[0].value.fen')==board.fen()
