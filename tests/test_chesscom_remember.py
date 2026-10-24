"""The public archive name survives login/relaunch without a network request."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
import classroom as rooms


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'accounts.sqlite3'))
    return (rooms.register_user('player-one', 'password-player-one'),
            rooms.register_user('player-two', 'password-player-two'))


def test_name_survives_logout_and_remembered_device_offline(accounts, monkeypatch):
    import chesscom
    monkeypatch.setattr(chesscom, 'get_json', lambda *a: pytest.fail('Must not need internet'))
    first, second = accounts
    device = rooms.remember_device(first)
    rooms.save_chesscom_user(first, '  My-Chess_Name  ')
    rooms.logout(first)
    restored = rooms.restore_device(device)
    assert rooms.identity(restored)['chesscom'] == 'my-chess_name'
    assert not rooms.identity(second).get('chesscom')
    rooms.save_chesscom_user(second, 'another-player')
    assert rooms.identity(restored)['chesscom'] == 'my-chess_name'
    rooms.save_chesscom_user(restored, '')
    assert rooms.identity(rooms.login_user('player-one', 'password-player-one'))['chesscom'] == ''
    assert rooms.identity(second)['chesscom'] == 'another-player'


def test_invalid_or_expired_identity_cannot_change_preference(accounts):
    first, _ = accounts
    rooms.save_chesscom_user(first, 'valid-name')
    with pytest.raises(ValueError):
        rooms.save_chesscom_user(first, 'https://chess.com/invalid')
    assert rooms.identity(first)['chesscom'] == 'valid-name'
    rooms.logout(first)
    with pytest.raises(PermissionError):
        rooms.save_chesscom_user(first, 'different-name')


def test_remembered_access_survives_long_offline_period_but_logout_revokes(accounts, monkeypatch):
    first, _ = accounts
    device = rooms.remember_device(first)
    future = rooms.time.time() + 90*86400
    monkeypatch.setattr(rooms.time, 'time', lambda: future)
    restored = rooms.restore_device(device)
    assert rooms.identity(restored)['name'] == 'player-one'
    rooms.forget_device(device)
    assert rooms.restore_device(device) is None


def test_app_saves_to_authenticated_account_without_global_file(accounts, tmp_path):
    first, _ = accounts
    tree = ast.parse(Path('app.py').read_text(encoding='utf-8'))
    save = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'save_user')
    preference = tmp_path/'legacy.json'
    namespace = dict(st=SimpleNamespace(session_state={'classroom_token': first}),
                     USER_PREFERENCE=preference)
    exec(compile(ast.Module(body=[save], type_ignores=[]), 'app.py', 'exec'), namespace)
    namespace['save_user']('my-chess-name')
    assert rooms.identity(first)['chesscom'] == 'my-chess-name'
    assert not preference.exists()


def test_switch_restores_saved_account_name(accounts, monkeypatch):
    import classroom_ui
    class State(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__
    first, second = accounts
    rooms.save_chesscom_user(first, 'remember-me')
    state = State()
    monkeypatch.setattr(classroom_ui, 'st', SimpleNamespace(session_state=state))
    monkeypatch.setattr(classroom_ui, '_clear_workspace', lambda: None)
    classroom_ui._switch(first)
    assert state.archive_user == 'remember-me'
    classroom_ui._switch(second)
    assert state.archive_user == ''
