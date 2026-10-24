"""Engine selection discovers executables without starting processes."""
from io import StringIO
from dataclasses import replace
import chess
import chess.pgn
import pytest

from engine_catalog import find_berserk, review_engines
from stockfish_analysis import analyse_with_books, find_engine
from analysis_summary import summarize_reviews, _summary_html
from test_analysis_summary import review


def test_missing_explicit_engine_path_is_not_silently_replaced(tmp_path,monkeypatch):
    monkeypatch.setenv('BERSERK_PATH',str(tmp_path/'missing.exe'))
    assert find_berserk()==''
    assert review_engines('stockfish-path')=={'Stockfish':'stockfish-path','Berserk':''}


def test_engine_override_is_used_without_launching_it(tmp_path,monkeypatch):
    path=tmp_path/'alternative.exe';path.write_bytes(b'not executed')
    monkeypatch.setenv('BERSERK_PATH',str(path))
    assert review_engines('stockfish')['Berserk']==str(path)


def test_summary_attributes_the_estimate_to_the_engine_that_did_the_work():
    html=_summary_html(summarize_reviews([replace(review(),engine_name='Berserk 14')]))
    assert 'Estimada · Berserk 14' in html and 'Stockfish' not in html


@pytest.mark.parametrize('name,path',[('Stockfish',find_engine()),('Berserk',find_berserk())])
def test_installed_engines_analyse_moves_and_an_empty_custom_position(name,path):
    if not path:pytest.skip(name+' not installed')
    game=chess.pgn.read_game(StringIO('1. e4 e5 2. Nf3 *'))
    result=analyse_with_books(game,path,quality='Rápida')
    assert name in result['engine_name']
    assert len(result['reviews'])==3
    assert all(name in r.engine_name and name in r.explanation for r in result['reviews'].values())
    root=chess.pgn.Game();root.setup(chess.Board('4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'))
    result=analyse_with_books(root,path,quality='Rápida')
    assert not result['reviews'] and name in result['explanations'][0]
    assert result['position']['engine_name']==result['engine_name']
    assert result['position']['cp'] is not None and result['position']['line']
    root.setup(chess.Board('7k/6Q1/5K2/8/8/8/8/8 b - - 0 1'))
    result=analyse_with_books(root,path,quality='Rápida')
    assert result['position']['result']=='1-0'
