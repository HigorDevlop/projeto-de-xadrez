from datetime import date, timedelta
from io import StringIO

import chess.engine
import chess.pgn
import pytest

import analysis_archive
import classroom as rooms
import evolution_map as evolution
import tactics_progress
from chess_review import MoveReview
from preparation_state import save_plan

END = date(2026, 11, 10)


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'accounts.sqlite3'))
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path/'preparation'))
    monkeypatch.setattr(evolution, 'today', lambda: END)
    monkeypatch.setattr(tactics_progress, 'today', lambda: END)
    def forbidden(*args, **kwargs):
        raise AssertionError('O mapa não pode iniciar o motor.')
    monkeypatch.setattr(chess.engine.SimpleEngine, 'popen_uci', forbidden)
    owner = rooms.bootstrap_owner('owner', 'owner-password-123')
    user = rooms.register_user('player', 'player-password-123')
    other = rooms.register_user('other', 'other-password-123')
    for token in (user, other):
        rooms.save_chesscom_user(token, 'ChessPlayer')
    return owner, user, other


def opening_plan(token):
    return dict(version=1, username='user:'+rooms.identity(token)['id'], repertoire_ids=['london'],
        phase_results={'1': dict(completed=True, day=str(END), accuracy=80, questions=5,
                                 first_correct=4, line_id='london-line')})


def saved_game(token, day='2026.11.10', white='ChessPlayer'):
    game = chess.pgn.read_game(StringIO(f'[White "{white}"]\n[Black "Rival"]\n[Date "{day}"]\n\n1. e4 *'))
    review = MoveReview(1, '1', 'Brancas', 'e4', 'e2e4', 'mistake', 80, 0, None,
                        'd4', '', [], 'Texto salvo.', best_line='1. d4 d5')
    return analysis_archive.save(token, str(game), dict(reviews={1: review}, explanations={}, references={}))


def test_sources_account_isolation_same_public_name_and_no_engine(accounts):
    owner, user, other = accounts
    key = saved_game(user)
    tactics_progress.record(rooms.identity(user)['id'], 'attempt-1', 'puzzle-1', 'fork', True, True)
    plan = opening_plan(user)
    # A stale library copy must not double-count the active course.
    plan['practice_library'] = {'london': dict(plan, phase_results={})}
    save_plan(plan, namespace='openings')
    data = evolution.collect(user)
    assert {r['source'] for r in data['rows']} == {'Partidas', 'Táticos', 'Aberturas'}
    assert len(data['rows']) == 3
    assert next(r for r in data['rows'] if r['source']=='Partidas')['id'] == key+':1'
    assert evolution.collect(other)['rows'] == []
    legacy = dict(opening_plan(user), username='ChessPlayer')
    save_plan(legacy, namespace='openings')
    rooms.save_chesscom_user(owner, 'ChessPlayer')
    assert evolution.collect(owner)['rows'] == []
    rooms.logout(user)
    with pytest.raises(PermissionError): evolution.collect(user)


def test_missing_dates_and_unidentified_side_are_not_weaknesses(accounts):
    _, user, _ = accounts
    saved_game(user, day='????.??.??')
    data = evolution.collect(user)
    assert not data['rows'] and any('excluídas' in n for n in data['notes'])
    saved_game(user, white='SomeoneElse')
    assert not evolution.collect(user)['rows']
    plan = opening_plan(user)
    plan['phase_results']['1']['accuracy'] = None
    save_plan(plan, namespace='openings')
    assert not evolution.collect(user)['rows']


def test_aggregation_equal_periods_dedup_and_minimum_samples():
    rows = []
    for bucket, offset in [('current', 0), ('previous', 7)]:
        for i in range(5):
            rows.append(evolution._row('Táticos', 'fork', END-timedelta(days=offset),
                bucket+str(i), str(i), int(bucket=='current'), 1, 'evidence', {}))
    rows += [rows[0], evolution._row('Táticos', 'fork', END-timedelta(days=14), 'too-old', 'old', 0, 1, '', {})]
    group, = evolution.aggregate(rows, end=END, days=7)
    assert group['current'] == dict(samples=5, records=5, value=100)
    assert group['previous']['value'] == 0 and group['delta'] == 100
    assert len(group['evidence']) == 10
    group, = evolution.aggregate(rows[:4], end=END, days=7)
    assert not group['sufficient'] and group['delta'] is None
    # Repeated attempts on one puzzle cannot satisfy distinct-puzzle evidence.
    for row in rows: row['sample'] = 'same'
    group, = evolution.aggregate(rows, end=END, days=7)
    assert not group['sufficient']
    assert evolution.aggregate([], end=END, days=30) == []


def test_preparation_uses_own_daily_summary_without_teacher_audit(accounts):
    owner, _, other = accounts
    teacher = rooms.register_professor('teacher', 'teacher-password-123', rooms.issue_professor_key(owner, 'teacher'))
    seat = rooms.students(teacher)[0]
    student = rooms.login_student(seat['access_key'])
    with rooms.database() as db:
        db.execute('INSERT INTO training_time VALUES(?,?,?)', (seat['id'], str(END), 600))
        db.execute('INSERT INTO warnings(student,created,reason) VALUES(?,?,?)', (seat['id'], 1, 'PRIVATE AUDIT'))
    data = evolution.collect(student)
    row, = data['rows']
    assert row['source'] == 'Preparos' and row['value'] == 10
    assert 'PRIVATE AUDIT' not in str(data)
    assert not evolution.collect(other)['rows']
    state = {}
    evolution.open_training(student, state, row)
    assert state['requested_page'] == 'Preparo'


@pytest.mark.parametrize('source,values,totals,expected', [
    ('Partidas', [1, 0], [1, 1], 50),
    ('Aberturas', [80, 40], [100, 100], 60),
    ('Preparos', [10, 20], [1, 1], 30),
])
def test_source_formulas_and_thirty_day_boundaries(source, values, totals, expected):
    rows = [evolution._row(source, 'tema', END-timedelta(days=i*29), str(i), str(i),
                           value, totals[i], 'registro', {}) for i, value in enumerate(values)]
    rows.append(evolution._row(source, 'tema', END-timedelta(days=30), 'previous', 'previous',
                               values[0], totals[0], 'anterior', {}))
    rows.append(evolution._row(source, 'tema', END+timedelta(days=1), 'future', 'future',
                               99, 100, 'futuro', {}))
    group, = evolution.aggregate(rows, end=END, days=30)
    assert group['current']['value'] == expected
    assert group['current']['records'] == 2 and group['previous']['records'] == 1
    assert len(group['evidence']) == 3 and group['delta'] is None


def test_navigation_revalidates_evidence_and_discards_stale_account(accounts):
    _, user, other = accounts
    tactics_progress.record(rooms.identity(user)['id'], 'attempt-1', 'puzzle-1', 'fork', True, True)
    row, = evolution.collect(user)['rows']
    state = {}
    with pytest.raises(PermissionError): evolution.open_training(other, state, row)
    assert not state
    evolution.open_training(user, state, row)
    chosen = []
    evolution.apply_training_request(other, state, 'Tático', chosen.append)
    assert not chosen and 'dashboard_evolution_request' not in state
    evolution.open_training(user, state, row)
    evolution.apply_training_request(user, state, 'Tático', chosen.append)
    assert chosen == ['fork']
    save_plan(opening_plan(user), namespace='openings')
    row = next(r for r in evolution.collect(user)['rows'] if r['source']=='Aberturas')
    evolution.open_training(user, state, row)
    evolution.apply_training_request(user, state, 'Aberturas', chosen.append)
    assert state['room_opening_request'] == dict(id='london', intent='master')


def test_game_action_opens_existing_personal_training(accounts):
    import analysis_training
    _, user, other = accounts
    saved_game(user)
    row, = evolution.collect(user)['rows']
    state = dict(classroom_token=user)
    evolution.open_training(user, state, row)
    assert state['requested_page'] == 'Análise' and state['analysis_training_open']
    assert state['dashboard_review_request']['ply'] == 1
    assert len(analysis_training.listing(user)) == 1
    evolution.open_training(user, state, row)
    assert len(analysis_training.listing(user)) == 1
    with pytest.raises(PermissionError): evolution.open_training(user, dict(classroom_token=other), row)


def test_map_ui_empty_evidence_navigation_and_account_switch(accounts, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import evolution_map_ui
    monkeypatch.setattr(evolution_map_ui, 'today', lambda: END)
    _, user, other = accounts
    app = AppTest.from_string('''
import streamlit as st
from evolution_map_ui import render
render(st.session_state.classroom_token)
''')
    app.session_state.classroom_token = user
    app.run()
    app.toggle[0].set_value(True).run()
    assert not app.exception and len(app.info) == 4
    tactics_progress.record(rooms.identity(user)['id'], 'attempt-1', 'puzzle-1', 'fork', True, True)
    app.run()
    assert not app.exception and any('Dados insuficientes para comparar' in i.value for i in app.info)
    assert len(app.dataframe) == 1
    app.button[0].click().run()
    assert app.session_state.requested_page == 'Tático'
    app.session_state.classroom_token = other
    app.run()
    assert not app.exception and not app.dataframe and not app.button
