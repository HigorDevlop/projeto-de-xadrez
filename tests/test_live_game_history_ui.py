from pathlib import Path
import json
import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def game(url,move,when):
    return dict(url=url,end_time=when,time_class='blitz',rules='chess',
        white=dict(username='fixture',result='agreed'),black=dict(username='opponent',result='agreed'),
        pgn=f'[White "fixture"]\n[Black "opponent"]\n[Result "1/2-1/2"]\n\n1. {move} 1/2-1/2')


@pytest.fixture
def live_server(tmp_path,monkeypatch,request):
    import test_coach_chess_ui as desktop
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    first=game('https://www.chess.com/game/live/111','e4 e5',1780000000)
    feed=tmp_path/'games.json';feed.write_text(json.dumps([first]),encoding='utf-8')
    (tmp_path/'app.py').write_text(f'''
import sys,json,ast
from pathlib import Path
sys.path.insert(0,{str(root)!r})
import streamlit as st
from datetime import datetime,timezone
from time import perf_counter
from concurrent.futures import Future
from chess_review import read_games
from interactive_board import interactive_board
import dashboard_auto_analysis
dashboard_auto_analysis.ensure=lambda *args:[]
st.set_page_config(layout='wide')
state=st.session_state
if 'history_games' not in state:
    state.update(archive_user='fixture',history_loaded_user='fixture',active_tab='Análise',
        history_games=[{first!r}],history_choice=None,history_live_next=0,jobs={{}},job_errors={{}},
        game='*',ply=0,reviews={{}})
def latest(*a,**k):return json.loads(Path({str(feed)!r}).read_text(encoding='utf-8'))
cached_live_history=latest
def queue_job(slot,key,function,*args):
    future=Future();future.set_result(function(*args));state.jobs[slot]=(key,future)
def reset_game(game,accuracies=None):state.game=str(game);state.ply=0
tree=ast.parse(Path({str(root/'app.py')!r}).read_text(encoding='utf-8'))
selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['poll_jobs','render_history','select_history_game']]
exec(compile(ast.Module(body=selected,type_ignores=[]),'live_history_fixture','exec'),globals())
render_history()
game=read_games(state.game)[0]
board=game.board();moves=list(game.mainline_moves())
for move in moves[:state.ply]:board.push(move)
with st.container(key='analysis_board_focus'):
    interactive_board(board,key='live_history_board',on_move=lambda:None,on_navigate=lambda:None,
        disabled=True,ply=state.ply,total=len(moves),pgn=state.game,revision=0,table=False)
poll_jobs()
''',encoding='utf-8')
    return request.getfixturevalue('coach_server')


def test_new_finished_game_appears_automatically_without_changing_review(browser_page,live_server,tmp_path):
    page=browser_page;page.set_default_timeout(45000);expect.set_options(timeout=45000)
    page.goto(live_server)
    selector=page.get_by_role('combobox',name='Escolher partida no histórico')
    expect(selector).to_be_enabled()
    selector.click();page.get_by_role('option').first.click()
    board=page.locator('.st-key-analysis_board_focus .board')
    expect(page.locator('.move-counter')).to_contain_text('Lance 2 de 2')
    before=board.get_attribute('data-fen')
    selected_label=selector.input_value()
    first=game('https://www.chess.com/game/live/111','e4 e5',1780000000)
    newer=game('https://www.chess.com/game/live/222','d4 d5',1780000100)
    (tmp_path/'games.json').write_text(json.dumps([newer,first]),encoding='utf-8')
    # The regular background timer detects this without clicking Atualizar.
    page.wait_for_timeout(35000)
    expect(selector).to_have_value(selected_label)
    assert board.get_attribute('data-fen')==before
    selector.click();expect(page.get_by_role('option')).to_have_count(2)
    page.keyboard.press('Escape')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path='tests/artifacts/history-live-update.png',full_page=True)
