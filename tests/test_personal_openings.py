import chess
import chess.engine
import pytest

import personal_openings as personal
from opening_course_state import begin_line, active_session
from opening_training_state import lines_for, board_for
from preparation_state import save_plan, load_plan


def game(path='e4 e5 Nf3 Nc6 Bc4 Bc5', white='alice', black='bob', url='one'):
    import chess.pgn
    item = chess.pgn.Game()
    item.headers.update(White=white, Black=black, ECO='C50')
    board, node = chess.Board(), item
    for san in path.split():
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)
    return dict(url=url, pgn=str(item), white={'username':white}, black={'username':black})


def test_frequency_is_per_game_and_separates_players_and_colours():
    first = game()
    games = [first, first, game(url='two'), game('d4 d5 c4 e6', url='three'), game(white='other',url='foreign')]
    rows = personal.positions(games, 'ALICE')
    assert rows[0]['count'] == 2
    assert rows[0]['prefix'] == ['e2e4','e7e5']
    assert all(row['side']=='white' for row in rows)
    assert personal.positions(games,'absent') == []
    assert personal.positions([game(white='bob', black='alice')],'alice')[0]['side']=='black'


def test_history_is_durable_offline_and_isolated_by_local_owner(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    records = personal.remember_history('user:1','alice',[game(),game(white='other',url='other')])
    assert len(records)==1
    assert personal.remember_history('user:1','alice',[]) == records
    assert personal.remember_history('user:2','alice',[]) == []
    assert personal.remember_history('user:1','bob',[]) == []


def test_only_latest_200_distinct_account_games_are_used(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    games=[dict(game(url=str(i)),end_time=i) for i in range(215)]
    games += [games[-1],dict(game(white='foreign',url='foreign'),end_time=1000)]
    recent=personal.remember_history('owner','alice',games)
    assert len(recent)==200
    assert [item['end_time'] for item in recent]==list(range(214,14,-1))
    assert personal.remember_history('owner','alice',[])==recent


def test_default_import_fills_200_games_even_beyond_twelve_months(monkeypatch):
    import chesscom
    calls=[]
    monkeypatch.setattr(chesscom,'fetch_archives',lambda user:list(range(18)))
    def month_games(user,month):
        calls.append(month)
        return [dict(url=str(month)+'-'+str(i),pgn='1. e4 *',end_time=10000-month*15-i) for i in range(15)]
    monkeypatch.setattr(chesscom,'fetch_games',month_games)
    result=chesscom.fetch_recent_games('alice')
    assert len(result)==200 and len(calls)==14
    assert result[0]['end_time']>result[-1]['end_time']


def test_historical_trails_keep_defining_opening_moves_and_rank_frequency():
    caro='e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5'
    italian='e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6'
    games=[game(caro,white='bob',black='alice',url=str(i)) for i in range(3)]
    games.append(game(italian,url='italian'))
    rows=personal.trail_positions(games,'alice')
    assert rows and rows[0]['opening']=='Caro-Kann Defense'
    assert rows[0]['opening_frequency']==3
    for row in rows:
        if row['opening']=='Caro-Kann Defense':
            assert row['prefix'][:2]==['e2e4','c7c6']
        if row['opening']=='Italian Game':
            assert row['prefix'][:5]==['e2e4','e7e5','g1f3','b8c6','f1c4']


def test_transpositions_share_frequency():
    games = [game('Nf3 d5 d4 Nf6 c4 e6',url='one'), game('d4 d5 Nf3 Nf6 c4 e6',url='two')]
    board = chess.Board()
    for san in 'd4 d5 Nf3 Nf6'.split(): board.push_san(san)
    row = next(row for row in personal.positions(games,'alice') if chess.Board(row['fen']).epd()==board.epd())
    assert row['count']==2


def test_real_local_engine_prepares_legal_continuation(monkeypatch):
    if not personal.find_engine(): pytest.skip('Stockfish local não disponível')
    plan = personal.prepare('smoke-test','alice',[game()],count=1,depth=12,seconds=.15)
    line = plan['personal_lines'][0]
    assert 'Stockfish' in line['engine']
    assert line['depth'] > 0
    assert len(line['moves']) > line['context_plies']


class Engine:
    id = {'name':'Test UCI'}
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def configure(self, options): pass
    def analyse(self, board, limit, multipv=None, root_moves=None):
        assert limit.depth == 20
        board = board.copy()
        path = []
        for index in range(5):
            if board.is_game_over(): break
            move = list(root_moves)[0] if index==0 and root_moves else next(iter(board.legal_moves))
            path.append(move)
            board.push(move)
        info=dict(pv=path,depth=17,score=chess.engine.PovScore(chess.engine.Cp(15),not board.turn))
        return [info] if multipv is not None else info


def test_history_preparation_builds_trails_without_changing_the_opening(monkeypatch):
    monkeypatch.setattr(personal,'find_engine',lambda:'local-engine')
    games=[game('e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5',white='bob',black='alice')]
    plan=personal.prepare_history_trails('owner','alice',games,engine_factory=lambda *a,**k:Engine())
    assert plan['recommendation_version']==3 and plan['source_games']==1
    assert plan['personal_lines']
    for line in plan['personal_lines']:
        assert line['moves'][:2]==['e2e4','c7c6']
        assert line['opening_frequency']==1 and line['context_plies']>=2


def test_engine_lines_train_and_persist_without_using_static_courses(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    monkeypatch.setattr(personal,'find_engine',lambda:'local-engine')
    plan = personal.prepare('user:1','alice',[game()],count=2,engine_factory=lambda *a,**k:Engine())
    assert len(lines_for(plan))==2
    assert plan['engine']=='Test UCI'
    line = plan['personal_lines'][0]
    assert line['moves'][:line['context_plies']] == ['e2e4','e7e5']
    board = chess.Board()
    for uci in line['moves']:
        assert chess.Move.from_uci(uci) in board.legal_moves
        board.push_uci(uci)
    session = begin_line(plan,line['id'],'train')
    assert active_session(plan) is session
    assert board_for(session).is_valid()
    assert session['ply'] == line['context_plies']
    assert session['history'] == line['moves'][:line['context_plies']]
    from opening_training_state import _start_quiz, _restart_recall
    _restart_recall(plan,session)
    assert session['ply'] == line['context_plies']
    _start_quiz(plan,session)
    assert min(session['quiz_queue']) >= line['context_plies']
    save_plan(plan,namespace='openings')
    restored = load_plan(plan['username'],namespace='openings')
    assert restored['personal_lines']==plan['personal_lines']
    assert active_session(restored)['line_id']==line['id']


def test_missing_engine_never_calls_historical_moves_recommendations(monkeypatch):
    monkeypatch.setattr(personal,'find_engine',lambda:'')
    with pytest.raises(ValueError, match='Stockfish local indisponível'):
        personal.prepare('owner','alice',[game()])


def test_personal_lesson_renders_with_no_catalogue_course(tmp_path, monkeypatch):
    import json
    import classroom
    import classroom_ui
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    monkeypatch.setattr(personal,'find_engine',lambda:'test-engine')
    monkeypatch.setattr(classroom_ui,'training_token',lambda:None)
    monkeypatch.setattr(classroom,'identity',lambda token:None)
    plan = personal.prepare('alice','alice',[game()],count=1,engine_factory=lambda *a,**k:Engine())
    begin_line(plan,plan['personal_lines'][0]['id'],'train')
    source = '''import json
import importlib, interactive_board
importlib.reload(interactive_board)
import streamlit as st
from opening_practice import render_opening_practice
st.session_state.openings_owner = 'alice'
st.session_state.openings_plan = json.loads(PAYLOAD)
st.session_state.openings_active = True
st.session_state.openings_catalog = False
render_opening_practice('alice')
'''.replace('PAYLOAD', repr(json.dumps(plan)))
    app = AppTest.from_string(source).run(timeout=30)
    assert not app.exception
    assert any('Seu histórico do Chess.com' in item.value for item in app.caption)
