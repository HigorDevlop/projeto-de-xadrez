from copy import deepcopy
from datetime import timedelta
import random

import chess
import pytest

from preparation_repetition import (create_session, current_exercise, revision, submit,
    counts, repertoire_session, submit_repertoire)
from preparation_state import save_plan, load_plan, today
from opening_training_state import create_repertoire_plan


def pool(size=5):
    return [dict(id=str(i), fen=chess.STARTING_FEN, uci='e2e4', side='white') for i in range(size)]


def event(session, correct=True):
    exercise = current_exercise(session)
    board = chess.Board(exercise['fen'])
    uci = exercise['uci'] if correct else next(m.uci() for m in board.legal_moves if m.uci() != exercise['uci'])
    return dict(uci=uci, fen=exercise['fen'], revision=revision(session))


def test_error_learning_correct_and_learning_error():
    s = create_session(pool(1))
    for correct, expected in [(False,'error'), (True,'learning'), (False,'error'),
                              (False,'error'), (True,'learning'), (True,'correct')]:
        assert submit(s,event(s,correct),123)
        assert s['positions']['0']['status'] == expected
    item = s['positions']['0']
    assert (item['attempts'],item['correct_attempts'],item['wrong_attempts']) == (6,3,3)
    assert item['last_seen'] == 123
    assert s['phase'] == 'complete'
    assert counts(s)['correct'] == 1


def test_first_success_requires_second_appearance():
    s = create_session(pool(1))
    submit(s,event(s),1)
    assert counts(s)['learning'] == 1 and counts(s)['correct'] == 0
    submit(s,event(s),2)
    assert s['phase'] == 'complete'


def test_random_rounds_no_adjacent_repeat_and_no_starvation():
    rng = random.Random(10)
    s = create_session(pool())
    seen = []
    for i in range(100):
        previous = s['current']
        seen.append(previous)
        assert submit(s,event(s,False),i,rng)
        assert s['current'] != previous
    assert set(seen) == set(s['positions'])
    assert min(p['attempts'] for p in s['positions'].values()) >= 19
    assert all(p['status'] == 'error' for p in s['positions'].values())
    for i in range(10):
        assert submit(s,event(s),i,rng)
    assert s['phase'] == 'complete' and counts(s)['correct'] == 5


def test_invalid_stale_and_duplicate_events_cannot_change_progress():
    s = create_session(pool())
    old = event(s)
    assert submit(s,old,1)
    snapshot = deepcopy(s)
    for bad in [old,None,{},dict(event(s),uci='bad'),dict(event(s),uci='e2e5'),dict(event(s),fen='stale')]:
        assert not submit(s,bad,2)
        assert s == snapshot


def test_save_reload_preserves_queue_counters_and_current(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan = create_repertoire_plan('recall',['italian'],today(),today()+timedelta(days=2))
    s = repertoire_session(plan)
    for i in range(20):
        assert submit_repertoire(plan,s,event(s,i%3 != 0),i)
    save_plan(plan)
    loaded = load_plan('recall')
    restored = repertoire_session(loaded)
    assert restored == s
    while restored['phase'] != 'complete':
        submit_repertoire(loaded,restored,event(restored),21)
    save_plan(loaded)
    assert repertoire_session(load_plan('recall'))['phase'] == 'complete'
    assert counts(restored)['correct'] == counts(restored)['total']


def test_migrate_completed_lines_without_resetting_them():
    from opening_training_state import session_for
    plan = create_repertoire_plan('migrate',['italian'],today(),today())
    old = session_for(plan)
    key = old['queue'].pop(0)
    old['mastered'].append(key)
    s = repertoire_session(plan)
    assert all(p['status'] == 'correct' for p in s['positions'].values() if p['exercise']['line_id'] == key)


def test_unfinished_progress_survives_next_day():
    day = today()
    plan = create_repertoire_plan('overnight',['italian'],day,day+timedelta(days=2))
    session = repertoire_session(plan,day)
    key = session['current']
    submit_repertoire(plan,session,event(session),1)
    next_day = repertoire_session(plan,day+timedelta(days=1))
    assert next_day['positions'][key] == session['positions'][key]
    assert next_day['positions'][key]['status'] == 'learning'


def test_mastered_position_in_unfinished_line_is_preserved_next_day():
    day = today()
    plan = create_repertoire_plan('partial',['italian'],day,day+timedelta(days=2))
    session = repertoire_session(plan,day)
    key = session['current']
    while session['positions'][key]['status'] != 'correct':
        submit_repertoire(plan,session,event(session, session['current'] == key),1)
    restored = repertoire_session(plan,day+timedelta(days=1))
    assert restored['positions'][key] == session['positions'][key]
    assert restored['current'] != key
