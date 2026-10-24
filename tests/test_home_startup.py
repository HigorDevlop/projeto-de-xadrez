"""The home must remain usable while its remote history is unavailable."""
import json
import sys
from pathlib import Path
from threading import Event
from time import perf_counter

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('fails', [False, True])
def test_home_does_not_wait_for_history_or_build_analysis_catalog(tmp_path, monkeypatch, fails):
    import chesscom
    from chess_review import BookIndex
    user = 'slow_failure' if fails else 'slow_success'
    preference = tmp_path / 'user.json'
    preference.write_text(json.dumps({'username': user}), encoding='utf8')
    monkeypatch.setenv('ACERVO_USER_PREFERENCE', str(preference))
    monkeypatch.setenv('ACERVO_APPEARANCE_PREFERENCE', str(tmp_path/'appearance.json'))
    started, release = Event(), Event()
    records = [{'pgn': '[White "slow_success"]\n[Black "Other"]\n\n1. e4 e5 *',
                'white': {'username': user}, 'black': {'username': 'Other'},
                'end_time': 1, 'url': 'example-game'}]

    def history(username):
        started.set()
        if not release.wait(30):
            raise AssertionError('The home waited for the network')
        if fails:
            raise ValueError('Serviço temporariamente indisponível')
        return records

    def forbidden_catalog(*args):
        raise AssertionError('The home must not index analysis books')

    monkeypatch.setattr(chesscom, 'fetch_recent_games', history)
    monkeypatch.setattr(chesscom, 'fetch_dashboard_games', lambda *args: records)
    monkeypatch.setattr(chesscom, 'fetch_rating', lambda user: (1500, 'Rápidas'))
    monkeypatch.setattr(BookIndex, 'add_opening_catalog', forbidden_catalog)
    # Register CCv2 components against this AppTest runtime.
    for module in ('interactive_board', 'recent_games', 'study_workspace', 'study_entrance',
                   'profile_avatar', 'page_chrome', 'cat_mascot', 'tactics_forge',
                   'tactic_demo', 'pgn_clipboard'):
        sys.modules.pop(module, None)
    at = AppTest.from_file(str(ROOT/'app.py'))
    at.session_state.main_view = at.session_state.active_tab = 'Partida'
    try:
        start = perf_counter()
        at.run(timeout=15)
        elapsed = perf_counter() - start
        assert not at.exception
        assert started.is_set() and not release.is_set()
        assert any(item.value == 'Últimas 8 partidas' for item in at.subheader)
        assert not at.main.title
        assert not at.main.get('page_link')
        assert not any(item.label in {'Desempenho', 'Atualizar partidas', 'Nova partida'} for item in at.main.button)
        assert at.session_state.active_tab == 'Partida'
        assert 'full' not in at.session_state.jobs
        assert any('segundo plano' in item.value for item in at.caption)
        assert not any('Nenhuma partida' in item.value for item in at.info)
        future = at.session_state.jobs['history'][1]
        assert not future.done()
        print(f'Home ready with blocked network: {elapsed:.3f}s')
    finally:
        release.set()
    try:
        future.result(timeout=5)
    except ValueError:
        assert fails
    at.run(timeout=15)
    assert not at.exception
    assert at.session_state.history_loaded_user == user
    if fails:
        assert 'temporariamente' in at.session_state.history_error
        assert at.session_state.history_games == []
    else:
        assert at.session_state.history_games == records
    at.session_state.requested_page = 'Desempenho'
    at.run(timeout=15)
    assert not at.exception
    assert at.session_state.active_tab == 'Desempenho'
    assert 'full' not in at.session_state.jobs
