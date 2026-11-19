from datetime import datetime,timezone, UTC
import chesscom
from live_game_history import merge


def test_live_arrival_keeps_selected_game_and_has_no_duplicates():
    old=[dict(url='old',pgn='1. e4 *',end_time=10)]
    new=[dict(url='new',pgn='1. d4 *',end_time=20),old[0]]
    games,index=merge(old,new,0)
    assert [row['url'] for row in games]==['new','old'] and index==1
    assert merge(games,new,index)==(games,index)
    assert old==[dict(url='old',pgn='1. e4 *',end_time=10)]


def test_refresh_queries_recent_months_without_the_archive_index(monkeypatch):
    calls=[]
    def games(user,month):
        calls.append((user,month))
        return [dict(url=month,pgn='1. e4 *',end_time=1),dict(pgn='*')]
    monkeypatch.setattr(chesscom,'fetch_games',games)
    monkeypatch.setattr(chesscom,'fetch_archives',lambda *_: (_ for _ in ()).throw(AssertionError('stale archive index')))
    result=chesscom.fetch_latest_finished_games('fixture')
    assert len(result)==2 and len(calls)==2
    assert calls[0][1]==datetime.now(UTC).strftime('%Y/%m')


def test_background_refresh_adds_game_without_changing_board_or_rerunning_when_unchanged(monkeypatch):
    import dashboard_auto_analysis
    requests=[]
    monkeypatch.setattr(dashboard_auto_analysis,"ensure",lambda *args:requests.append(args))
    import ast
    from pathlib import Path
    from concurrent.futures import Future
    from types import SimpleNamespace
    tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8'))
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='poll_jobs')
    function.decorator_list=[]
    class State(dict):
        __getattr__=dict.__getitem__
        __setattr__=dict.__setitem__
    initial=dict(url='old',pgn='1. e4 *',end_time=10)
    latest=dict(url='new',pgn='1. d4 *',end_time=20)
    future=Future();future.set_result([latest,initial])
    state=State(archive_user='fixture',history_loaded_user='fixture',active_tab='Análise',
        history_games=[initial],history_choice=0,game='1. e4 *',ply=1,reviews={'saved':True},
        jobs={'history_live':('fixture',future)},job_errors={})
    reruns=[]
    namespace=dict(st=SimpleNamespace(session_state=state,rerun=lambda:reruns.append(True)),perf_counter=lambda:100,
        queue_job=lambda *_:None,cached_live_history=lambda *_:None)
    exec(compile(ast.Module(body=[function],type_ignores=[]),'poll_jobs_test','exec'),namespace)
    namespace['poll_jobs']()
    assert state.history_games==[latest,initial] and state.history_choice==1
    assert state.game=='1. e4 *' and state.ply==1 and state.reviews=={'saved':True}
    assert len(reruns)==1
    assert requests and requests[0][0]==[latest,initial]
    future=Future();future.set_result([latest,initial])
    state.jobs['history_live']=('fixture',future)
    namespace['poll_jobs']()
    assert len(reruns)==1

    # Accuracy jobs from the home page must not reload the dashboard, even in a batch.
    state.active_tab='Desempenho';state.recent_accuracies={}
    for index in range(4):
        future=Future();future.set_result(85+index)
        state.jobs['accuracy']=((str(index),'signature'),future)
        namespace['poll_jobs']()
    assert len(reruns)==1 and len(state.recent_accuracies)==4
    # An obsolete full-analysis result must also stay silent after changing games.
    future=Future();future.set_result({'obsolete':True})
    state.jobs['full']=('old-game',future)
    namespace['analysis_key']=lambda:'current-game'
    namespace['poll_jobs']()
    assert len(reruns)==1
