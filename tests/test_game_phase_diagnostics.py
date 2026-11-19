from datetime import datetime
from io import StringIO
import chess
import chess.pgn
import pytest

import game_phase_diagnostics as diag
from performance_dashboard import quality_key
from preparation_state import today,LOCAL_ZONE
from test_performance_dashboard import archived
from test_analysis_summary import review


def test_phase_uses_position_and_real_move_number():
    board=chess.Board();assert diag.phase(board)=='Abertura'
    board.fullmove_number=11;assert diag.phase(board)=='Meio-jogo'
    assert diag.phase(chess.Board('8/8/5k2/8/5P2/8/5K2/8 w - - 0 40'))=='Final'
    assert diag.phase(chess.Board('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 9'))=='Final'


def test_only_players_moves_and_error_rates_not_raw_counts(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR',str(tmp_path))
    record=diag.window([archived(1)],'player')[0]
    rows=[dict(ply=i+1,number=i+1,san='e4',phase='Meio-jogo',category='mistake' if i<4 else 'good',loss_cp=40,loss_chances=.1,best_san='d4',fen=chess.STARTING_FEN) for i in range(20)]
    rows.extend(dict(ply=i+21,number=i+21,san='Kf3',phase='Final',category='mistake' if i<3 else 'good',loss_cp=40,loss_chances=.1,best_san='Ke3',fen=chess.STARTING_FEN) for i in range(10))
    key=quality_key(record['game'])
    diag.save(key,'white',dict(complete=True,rows=rows))
    diag.save(key,'black',dict(complete=True,rows=[dict(rows[0],phase='Abertura',category='blunder')]))
    result=diag.aggregate([record])
    assert result['worst']['phase']=='Final' and result['worst']['rate']==30
    assert result['phases'][0]['moves']==0
    assert result['phases'][1]['errors']==4
    assert result['analyzed']==1 and len(result['critical'])==7


def test_completed_reviews_produce_phase_data_and_partial_reviews_do_not(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR',str(tmp_path))
    game=chess.pgn.read_game(StringIO(archived(1)['pgn']));key=quality_key(game)
    diag.from_reviews(game,[review()]);assert diag.load(key,'white') is None
    diag.from_reviews(game,[review(1,'Brancas','good'),review(2,'Pretas','blunder'),
                            review(3,'Brancas','mistake'),review(4,'Pretas','good')])
    assert [row['number'] for row in diag.load(key,'white')['rows']]==[1,2]
    assert diag.load(key,'white')['rows'][1]['category']=='mistake'


def test_engine_diagnostic_is_saved_and_reused(tmp_path,monkeypatch):
    from stockfish_analysis import find_engine
    engine=find_engine()
    if not engine:pytest.skip('Stockfish not installed')
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR',str(tmp_path))
    record=diag.window([archived(1)],'player')[0]
    report=diag.analyze_record(record,engine)
    assert report['complete'] and len(report['rows'])==2
    assert all(row['phase']=='Abertura' for row in report['rows'])
    assert diag.analyze_record(record,'missing-engine')==report
