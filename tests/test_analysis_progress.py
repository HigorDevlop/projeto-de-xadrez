"""Real move completion drives progress; the UI never invents percentages."""
from io import StringIO
from threading import Event
from concurrent.futures import CancelledError, ThreadPoolExecutor
import chess.pgn
import pytest
from analysis_progress import AnalysisProgress
from stockfish_analysis import analyse_with_books, find_engine


def test_snapshots_are_immutable_bounded_and_safe_for_concurrent_reads():
    progress=AnalysisProgress('Stockfish')
    original=progress.snapshot()
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=pool.submit(lambda:[progress.update(i,100,'Avaliando') for i in range(101)])
        snapshots=[progress.snapshot() for _ in range(100)]
        future.result()
    assert original.completed==0
    assert all(0<=s.fraction<=1 for s in snapshots)
    assert progress.snapshot().fraction==1
    assert original.engine=='Stockfish'


@pytest.mark.skipif(not find_engine(),reason='Stockfish not installed')
def test_real_engine_reports_completed_moves_in_order():
    snapshots=[]
    progress=AnalysisProgress()
    def report(*args):
        progress.update(*args);snapshots.append(progress.snapshot())
    game=chess.pgn.read_game(StringIO('1. e4 e5 2. Nf3 *'))
    result=analyse_with_books(game,find_engine(),quality='Rápida',progress=report)
    counts=[s.completed for s in snapshots]
    assert counts==sorted(counts)
    assert counts[0]==0 and counts[-1]==len(result['reviews'])==3
    assert {1,2,3}<=set(counts)
    assert snapshots[-1].phase=='Análise concluída'
    assert snapshots[-1].engine==result['engine_name']


@pytest.mark.skipif(not find_engine(),reason='Stockfish not installed')
def test_cancelled_analysis_does_not_report_a_finished_percentage():
    snapshots=[];cancel=Event()
    def report(done,total,phase,*name):
        snapshots.append((done,total))
        if done==1:cancel.set()
    game=chess.pgn.read_game(StringIO('1. e4 e5 2. Nf3 *'))
    with pytest.raises(CancelledError):
        analyse_with_books(game,find_engine(),quality='Rápida',progress=report,cancel=cancel)
    assert snapshots[-1]==(1,3)


def test_old_worker_cannot_change_progress_for_a_new_analysis():
    old=AnalysisProgress('Stockfish')
    current=AnalysisProgress('Berserk')
    current.update(0,5,'Iniciando')
    old.update(100,100,'Análise concluída')
    assert current.snapshot().completed==0
    assert current.snapshot().engine=='Berserk'
