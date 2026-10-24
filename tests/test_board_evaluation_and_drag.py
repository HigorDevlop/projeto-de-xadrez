from types import SimpleNamespace
import chess
from playwright.sync_api import expect
from interactive_board import annotation_rows,game_frames,piece_images,position_data,interactive_board
from test_browser_components import browser_page,mount,drag


def test_tactics_drag_uses_actual_squares_with_no_border_and_zoom(browser_page):
    page=browser_page
    board=chess.Board('6k1/ppp2ppp/8/3r4/3P4/1P3P2/PP2b1PP/R5K1 b - - 0 1')
    data={**position_data(board,True),'revision':1,'trainingMode':True,'stableBoard':True,
          'trainingExpected':'e2f3','pieces':piece_images(),'ply':0,'total':0,'navigation':False}
    mount(page,'interactive_board.py',data)
    page.add_style_tag(content='.workspace{zoom:1.35}.board{border:0}.board-stage{width:420px}')
    drag(page,'e2','f3')
    page.wait_for_function('window.events.some(e=>e.key==="move")')
    assert page.evaluate('window.events.find(e=>e.key==="move").value.uci')=='e2f3'
    board.push_uci('e2f3')
    page.evaluate('(data)=>window.render(data)',{**data,**position_data(board,True),'revision':2})
    expect(page.locator('.drag-ghost')).to_have_count(0)


def test_evaluation_follows_moves_and_flip_without_an_engine(browser_page):
    page=browser_page
    frames=game_frames('1. e4 e5 *')
    for frame,score in zip(frames,[None,{'cp':75,'mate':None},{'cp':None,'mate':-3}]):frame['evaluation']=score
    data={**position_data(chess.Board()),'revision':0,'ply':0,'total':2,'navigation':True,
          'expanded':True,'epoch':'eval-test','frames':frames,'pieces':piece_images(),
          'evaluationBar':True,'evaluation':None,'analysisNotes':annotation_rows('1. e4 e5 *')}
    mount(page,'interactive_board.py',data)
    bar=page.locator('.evaluation-bar')
    expect(bar).to_have_attribute('aria-valuetext','Sem avaliação. Clique em Analisar Partida.')
    assert abs(bar.bounding_box()['height']-page.locator('.board').bounding_box()['height'])<1
    page.get_by_role('button',name='Próximo lance',exact=True).click()
    expect(bar.locator('.evaluation-label')).to_have_text('+0,75')
    page.wait_for_function('document.getAnimations().every(animation=>animation.playState!=="running")')
    from pathlib import Path
    folder=Path(__file__).resolve().parent/'artifacts';folder.mkdir(exist_ok=True)
    page.screenshot(path=str(folder/'analysis-evaluation.png'),full_page=True)
    page.get_by_role('button',name='Próximo lance',exact=True).click()
    expect(bar.locator('.evaluation-label')).to_have_text('M3')
    assert 'pretas' in bar.get_attribute('aria-valuetext')
    page.evaluate('(data)=>window.render({...data,flip:true})',{**data,'ply':2,'evaluation':frames[2]['evaluation'],'navigation_ack':2})
    expect(bar).to_have_class('evaluation-bar negative flipped')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


def test_clock_metadata_is_readable_and_commands_are_hidden():
    row=annotation_rows('1. e4 {[%clk 0:03:01.4] [%eval 0.2] Controle do centro.} *')[0]
    assert row['clock']=='3:01'
    assert row['comment']=='Controle do centro.'


def test_evaluation_is_independent_of_quality_badges(monkeypatch):
    captured={}
    monkeypatch.setattr('interactive_board._BOARD',lambda **kwargs:captured.update(kwargs))
    review=SimpleNamespace(white_cp=-40,white_mate=None)
    interactive_board(chess.Board(),on_move=lambda:None,evaluation_bar=True,
                      evaluation_reviews={0:review},reviews={})
    assert captured['data']['evaluation']=={'cp':-40,'mate':None}
