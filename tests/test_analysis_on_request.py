"""Exercise app callbacks without starting its network-backed page shell."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'app.py'


def callbacks(state, engine='stockfish'):
    state.jobs = {}
    state.analysis_engine = getattr(state, 'analysis_engine', 'Stockfish')
    state.review_engine = state.analysis_engine
    tree = ast.parse(SOURCE.read_text(encoding='utf8'))
    names = {'ensure_analysis', 'start_analysis', 'analysis_key'}
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    calls = []
    engine_job, study_job = object(), object()
    from analysis_progress import AnalysisProgress
    namespace = dict(st=SimpleNamespace(session_state=state), engine_path=engine,
        AnalysisProgress=AnalysisProgress,
        engine_choices={'Stockfish': engine, 'Berserk': 'berserk-test'},
        analysis_settings_signature=lambda: state.analysis_signature,
        queue_job=lambda *args: calls.append(args), analyse_with_books=engine_job,
        prepare_explanations=study_job, current_game=lambda pgn: pgn, book=None, study=None,
        cancel_analysis=lambda: None, files=(), book_plies=40,
        load_library=lambda *args: (None, None, []))
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace, calls, engine_job, study_job


@pytest.mark.parametrize('study_open', [False, True])
@pytest.mark.parametrize('active_tab', ['Análise', 'Partida', 'Estudo com livros'])
def test_opening_board_or_study_never_starts_stockfish(study_open, active_tab):
    state = SimpleNamespace(active_tab=active_tab, study_open=study_open, analysis_requested=False, game='PGN',
        analysis_signature='settings', analysis_generation=0, loaded_analysis=None,
        job_errors={}, player_rating=1500, quality='Rápida')
    functions, calls, engine_job, study_job = callbacks(state)
    functions['ensure_analysis']()
    assert not any(call[2] is engine_job for call in calls)
    assert bool(calls) == (study_open and active_tab == 'Estudo com livros')
    if calls:
        assert calls[0][2] is study_job


def test_explicit_request_starts_engine_even_after_text_only_study():
    state = SimpleNamespace(active_tab='Análise', study_open=True, analysis_requested=False, game='PGN',
        analysis_signature='settings', analysis_generation=0,
        loaded_analysis=('PGN', 'settings', 0), job_errors={}, player_rating=1500,
        quality='Rápida', analysis_depth='Profunda')
    functions, calls, engine_job, _ = callbacks(state)
    functions['start_analysis']()
    functions['ensure_analysis']()
    assert state.analysis_requested and state.analysis_generation == 1
    assert calls[0][2] is engine_job
    assert calls[0][-1] == 'Profunda'
    state.loaded_analysis = functions['analysis_key']()
    functions['ensure_analysis']()
    assert len(calls) == 1


def test_no_page_schedules_background_accuracy_estimation():
    tree = ast.parse(SOURCE.read_text(encoding='utf8'))
    jobs = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == 'queue_job']
    assert all(not (node.args and isinstance(node.args[0], ast.Constant)
                   and node.args[0].value == 'accuracy') for node in jobs)


def test_explicit_choice_routes_to_berserk_instead_of_previous_stockfish():
    state=SimpleNamespace(active_tab='Análise',study_open=False,analysis_requested=False,game='PGN',
        analysis_signature='settings',analysis_generation=0,loaded_analysis=None,job_errors={},
        player_rating=1500,quality='Rápida',analysis_depth='Rápida',analysis_engine='Berserk')
    functions,calls,engine_job,_=callbacks(state)
    functions['start_analysis']();functions['ensure_analysis']()
    assert calls[0][2] is engine_job and calls[0][4]=='berserk-test'
