"""Regression cases found during the application review."""
from io import StringIO
from types import SimpleNamespace
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event

import chess
import chess.pgn
import pytest

import analysis_editor
import study_workspace
from book_reader import book_info
from preparation_state import load_plan, plan_path, new_plan, save_plan


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def test_invalid_pdf_is_a_recoverable_upload_error():
    with pytest.raises(ValueError, match='PDF'):
        book_info('Danificado.pdf', b'arquivo incompleto')


def test_book_editor_clears_impossible_castling_after_moving_rook(monkeypatch):
    board = chess.Board('4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1')
    game = chess.pgn.Game()
    game.setup(board)
    state = State(book_game=str(game), book_editing=False, book_ply=0, book_revision=0)
    monkeypatch.setattr(study_workspace, 'st', SimpleNamespace(session_state=state))
    study_workspace.start_edit()
    state.book_board = SimpleNamespace(edit=dict(
        fen=state.book_draft, revision=state.book_revision, **{'from':'h1', 'to':'h2'}))
    study_workspace.edit_changed()
    assert state.book_castling == ['Q']
    study_workspace.finish_edit()
    assert not state.book_editing and not state.get('book_error')
    assert study_workspace.study_board().piece_at(chess.H2) == chess.Piece(chess.ROOK, chess.WHITE)


@pytest.mark.parametrize('editor', ['analysis', 'book'])
def test_changing_turn_in_editor_clears_en_passant_from_original_turn(monkeypatch, editor):
    board = chess.Board('4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1')
    assert board.is_valid() and board.has_legal_en_passant()
    if editor == 'analysis':
        state = State(board_revision=0)
        monkeypatch.setattr(analysis_editor, 'st', SimpleNamespace(session_state=state))
        analysis_editor.begin(board)
        state.analysis_edit_turn = 'Brancas'
        saved = []
        analysis_editor.save(saved.append)
        assert saved and not state.analysis_editing
        result = saved[0].board()
    else:
        game = chess.pgn.Game()
        game.setup(board)
        state = State(book_game=str(game), book_editing=False, book_ply=0, book_revision=0)
        monkeypatch.setattr(study_workspace, 'st', SimpleNamespace(session_state=state))
        study_workspace.start_edit()
        state.book_turn = 'Brancas'
        study_workspace.finish_edit()
        assert not state.book_editing
        result = chess.pgn.read_game(StringIO(state.book_game)).board()
    assert result.turn == chess.WHITE and result.ep_square is None and result.is_valid()


@pytest.mark.parametrize('contents', ['[]', 'null', '42', '{"version":1,"username":null}'])
def test_malformed_saved_plan_does_not_crash_loading(tmp_path, monkeypatch, contents):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    plan_path('reader').write_text(contents, encoding='utf-8')
    assert load_plan('reader') is None


def test_simultaneous_progress_saves_do_not_share_a_temporary_file(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    def save(index):
        plan = new_plan('reader', '2026-10-21', '2026-10-22', ['Italiana'])
        plan['middle_cursor'] = index
        save_plan(plan)
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(save, range(24)))
    assert load_plan('reader')['middle_cursor'] in range(24)
    assert not list(tmp_path.glob('*.tmp'))


def test_switching_accounts_drops_previous_game_and_background_jobs(monkeypatch):
    import classroom_ui
    game = chess.pgn.Game()
    game.headers['White'] = 'Conta anterior'
    job = Future()
    cancel = Event()
    state = State(game=str(game), ply=1, reviews={1:'análise anterior'},
                  jobs={'history':('old', job)}, analysis_cancel=cancel,
                  dashboard_history_games=[{'pgn':'old'}], prep_plan={'username':'old'},
                  study_files=(('Privado.txt', b'old'),), library_uploads=(),
                  _analysis_files=(('Privado.txt',b'old'),),_analysis_library_id='old',_book_sources_cache=('old',),
                  study_book_upload_3=['old upload'], study_upload_revision=3,
                  tab_history=['Usuários'], board_revision=3, analysis_generation=2,
                  book_revision=4, puzzle_revision=6)
    monkeypatch.setattr(classroom_ui, 'st', SimpleNamespace(session_state=state))
    monkeypatch.setattr(classroom_ui, 'rooms', SimpleNamespace(
        identity=lambda token:{'id':'new', 'name':'Novo', 'role':'user'},
        load_profile_photo=lambda token:None, logout=lambda token:None))
    classroom_ui._switch('new-token')
    assert 'Conta anterior' not in state.game and state.ply == 0 and state.reviews == {}
    assert state.jobs == {} and job.cancelled() and cancel.is_set()
    assert state.dashboard_history_games == [] and not state.get('prep_plan')
    assert state.study_files == () and not state.tab_history
    assert all(key not in state for key in ('_analysis_files','_analysis_library_id','_book_sources_cache'))
    assert 'study_book_upload_3' not in state and state.study_upload_revision > 3
    assert state.book_revision > 4 and state.puzzle_revision > 6


def test_restart_board_cancels_pending_diagram_and_preserves_reading(monkeypatch):
    state = State(book_game='1. e4 e5 *', book_ply=2, book_revision=4,
                  book_editing=True, reader_book='book', reader_page=23,
                  book_flip=True, book_load_requested=('book',23), book_error='old')
    monkeypatch.setattr(study_workspace, 'st', SimpleNamespace(session_state=state))
    study_workspace.restart_study_board()
    assert study_workspace.study_board().fen() == chess.STARTING_FEN
    assert state.book_ply == 0 and state.book_revision == 5 and not state.book_editing
    assert state.reader_page == 23 and state.reader_book == 'book' and state.book_flip
    assert 'book_load_requested' not in state and 'book_error' not in state


def test_reader_navigation_rejects_old_book_and_out_of_order_events(monkeypatch):
    import book_reader
    state = State(reader_book='book', reader_epoch=2, reader_page=0, reader_navigation_ack=0)
    monkeypatch.setattr(book_reader, 'st', SimpleNamespace(session_state=state))
    def send(**changes):
        event = dict(book='book',epoch=2,page=8,sequence=5)
        state.study_focus_control = SimpleNamespace(navigate=event | changes)
        book_reader.navigate_reader(10)
    send()
    assert state.reader_page == 8 and state.reader_page_input == 9
    for changes in [dict(sequence=4,page=2),dict(book='old'),dict(epoch=1),dict(page=True)]:
        send(**changes)
        assert state.reader_page == 8
    send(sequence=6,page=100)
    assert state.reader_page == 9
