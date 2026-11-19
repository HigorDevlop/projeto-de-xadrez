from threading import Event
import json
import pytest
import dashboard_auto_analysis as auto
from performance_dashboard import quality_key,quality_counts,save_game_quality
from game_phase_diagnostics import window,load as load_diagnostics
from test_performance_dashboard import archived
from test_analysis_summary import review


def test_complete_engine_classification_is_atomic_cached_and_covers_own_moves(tmp_path,monkeypatch):
    from stockfish_analysis import find_engine
    engine=find_engine()
    if not engine:pytest.skip('Stockfish unavailable')
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR',str(tmp_path))
    record=window([archived(1)],'player')[0];key=quality_key(record['game']);updates=[]
    def progress(done,total):
        assert auto.load(key,'white') is None
        updates.append((done,total))
    auto.analyze(record,engine,progress=progress)
    result=auto.load(key,'white')
    assert result['moves']==2 and sum(result['counts'].values())==2
    assert updates==[(1,2),(2,2)]
    assert len(load_diagnostics(key,'white')['rows'])==2
    assert auto.load(key,'black') is None
    auto.analyze(record,'missing-engine')
    assert auto.load(key,'white')==result


def test_complete_automatic_report_replaces_partial_counts_but_preserves_full_manual(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR',str(tmp_path))
    record=window([archived(1)],'player')[0];game=record['game'];key=quality_key(game)
    save_game_quality(game,[review(1,'Brancas','good')])
    path=auto._path(key,'white');path.parent.mkdir(parents=True)
    counts={name:0 for name in auto.individual_counts(key,'white')};counts['best']=2
    path.write_text(json.dumps(dict(version=1,complete=True,moves=2,counts=counts)))
    games=[dict(quality_key=key,side='white')]
    assert quality_counts(games)[0]['best']==2
    save_game_quality(game,[review(1,'Brancas','good'),review(2,'Pretas','good'),review(3,'Brancas','good'),review(4,'Pretas','good')])
    assert quality_counts(games)[0]['good']==2


def test_queue_prioritizes_new_arrivals_and_does_not_duplicate_running_work(monkeypatch,tmp_path):
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR',str(tmp_path))
    monkeypatch.setattr(auto,'ready',lambda record:False)
    records=window([archived(i,opening=f'Opening {i}') for i in (1,2,3)],'player')
    assert len(records)==3
    for i,record in enumerate(records):record['timestamp']=i+1
    started=Event();release=Event();finished=Event();calls=[]
    def analyzer(record,engine,progress):
        calls.append(record['timestamp']);progress(1,2)
        if len(calls)==1:started.set();assert release.wait(5)
        if len(calls)==3:finished.set()
    queue=auto.AnalysisQueue(analyzer=analyzer)
    try:
        queue.submit(records[:1],'engine');assert started.wait(5)
        queue.submit(records[:2],'engine');queue.submit(records[2:],'engine')
        assert queue.status(records)['queued']==2
        release.set();assert finished.wait(5)
        assert calls==[1,3,2]
    finally:release.set();queue.executor.shutdown(wait=True)
