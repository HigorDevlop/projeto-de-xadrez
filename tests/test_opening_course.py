from copy import deepcopy
from datetime import timedelta
import chess

from opening_course_state import (select_course, course_lines, begin_line, settle,
    next_phase, course_summary, ensure_course, record_completion)
from opening_training_state import board_for, expected_move, submit_move
from preparation_state import today, save_plan, load_plan


def new_course():
    return select_course(None, 'course-test', 'italian')


def solve(plan, session):
    for i in range(200):
        if session['phase'] == 'complete':
            return
        if session['phase'] == 'line_end':
            next_phase(plan,session)
        elif session['phase'] == 'answer':
            uci = expected_move(plan,session)
            event = dict(uci=uci,fen=board_for(session).fen(),revision=f"{session['token']}:{session['revision']}")
            assert submit_move(plan,session,event,i)
        else:
            settle(plan,session,session['next_at']+1)
    raise AssertionError('Lesson did not finish')


def test_learn_recall_quiz_unlocks_next_line_and_schedules_review():
    plan = new_course()
    lines = course_lines(plan)
    assert lines[0]['unlocked'] and not lines[1]['unlocked']
    assert begin_line(plan,lines[1]['id']) is None
    session = begin_line(plan,lines[0]['id'])
    assert session['mode']=='learn'
    solve(plan,session)
    items = course_lines(plan)
    assert items[0]['learned'] and items[0]['mastery']==1
    assert items[1]['unlocked']
    assert items[0]['due']==str(today()+timedelta(days=1))
    assert course_summary(plan)['learned']==1
    review = begin_line(plan,items[0]['id'],'master')
    assert review['mode']=='recall' and not review['hint']
    solve(plan,review)
    assert course_lines(plan)[0]['mastery']==1  # No same-day score farming.


def test_train_teaches_each_new_line_and_reviews_only_learned_lines():
    plan = new_course()
    first = course_lines(plan)[0]['id']
    session = begin_line(plan, first, 'train')
    assert session['mode'] == 'learn'
    solve(plan, session)
    second = course_lines(plan)[1]['id']
    assert begin_line(plan, second, 'train')['mode'] == 'learn'
    assert begin_line(plan, first, 'train')['mode'] == 'learn'


def test_expanded_courses_preserve_old_progress_and_unlock_new_material():
    plan = new_course()
    from opening_repertoires import _COURSES, catalog
    old_count = len(next(row for row in _COURSES if row[0] == 'italian')[4])
    assert len(course_lines(plan)) >= 5
    for row in course_lines(plan)[:4]:
        plan['practice_progress'][row['id']]['learned'] = True
        plan['course_cycle']['completed'].append(row['branch'])
    restored = select_course(plan, 'course-test', 'italian')
    next_line = next(row for row in course_lines(restored) if not row['learned'])
    assert next_line['unlocked']
    assert begin_line(restored, next_line['id'], 'train')['mode'] == 'learn'
    assert all(line.get('lesson_moves',5) in range(5,99,2) for course in catalog() for line in course['lines'])
    assert len(next(course for course in catalog() if course['id']=='london')['lines']) > 10


def test_switching_course_and_reload_keeps_each_board(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan = new_course()
    key = course_lines(plan)[0]['id']
    session = begin_line(plan,key)
    original = deepcopy(session)
    other = select_course(plan,'course-test','caro')
    begin_line(other,course_lines(other)[0]['id'])
    save_plan(other,namespace='openings')
    restored = select_course(load_plan('course-test',namespace='openings'),'course-test','italian')
    assert begin_line(restored,key)==original


def test_explore_does_not_unlock_or_award_mastery():
    plan = new_course()
    line = course_lines(plan)[-1]
    session = begin_line(plan,line['id'],'explore')
    solve(plan,session)
    assert not course_lines(plan)[-1]['learned']
    assert course_summary(plan)['ratio']==0


def test_mastery_grows_on_later_days_and_completion_is_idempotent(monkeypatch):
    plan = new_course()
    line = course_lines(plan)[0]
    session = begin_line(plan,line['id'])
    solve(plan,session)
    original = deepcopy(plan['practice_progress'])
    record_completion(plan,session)
    assert plan['practice_progress']==original
    tomorrow = today()+timedelta(days=1)
    monkeypatch.setattr('opening_course_state.today',lambda:tomorrow)
    review = begin_line(plan,line['id'],'master')
    solve(plan,review)
    assert course_lines(plan)[0]['mastery']==2


def test_invalid_selection_does_not_mutate_course():
    plan = new_course()
    original = deepcopy(plan)
    try:
        select_course(plan,'course-test','not-an-opening')
    except ValueError:
        pass
    assert plan==original


def test_legacy_lesson_resumes_with_compatibility_defaults():
    from opening_training_state import session_for
    plan = new_course()
    old = session_for(plan)
    old.update(ply=2, history=['e2e4', 'e7e5'], phase='answer')
    for key in ('mode', 'learned', 'attempted', 'animation', 'marks', 'quiz_queue', 'quiz_retry'):
        old.pop(key, None)
    ensure_course(plan)
    resumed = begin_line(plan, old['line_id'])
    assert resumed['history'] == ['e2e4', 'e7e5']
    assert resumed['token'] == old['token']
    assert resumed['mode'] == 'recall'
    assert resumed['marks'] == {} and resumed['quiz_queue'] == []


def test_guided_lesson_waits_for_player_pause_and_phase_changes():
    plan = new_course()
    session = begin_line(plan, course_lines(plan)[0]['id'])
    # Even an old saved demonstration timer must not play the learner's move.
    session['demo_at'] = 1
    assert not settle(plan, session, 999)
    assert session['history'] == [] and 'demo_at' not in session
    seen = set()
    now = 1000
    for _ in range(200):
        seen.add(session['mode'])
        if session['phase'] == 'complete':
            break
        if session['phase'] == 'answer':
            event = dict(uci=expected_move(plan, session), fen=board_for(session).fen(),
                         revision=f"{session['token']}:{session['revision']}")
            assert submit_move(plan, session, event, now)
        else:
            before = deepcopy(session)
            session['paused'] = True
            assert not settle(plan, session, now + 10)
            session.pop('paused')
            assert session == before
            settle(plan, session, now)
        now += 2
    assert session['phase'] == 'complete'
    assert seen == {'learn', 'recall', 'quiz'}
    assert course_summary(plan)['learned'] == 1


def test_rejected_moves_and_recovery_always_acknowledge_without_replaying():
    from opening_course_state import receive_move, resync_board
    plan = new_course()
    session = begin_line(plan, course_lines(plan)[0]['id'])
    event = dict(uci='e2e4', fen=board_for(session).fen(),
                 revision=f"{session['token']}:{session['revision']}")
    assert receive_move(plan, event, 1)
    assert session['history'] == ['e2e4', 'e7e5']


    for _ in range(5):
        revision = session['revision']
        assert receive_move(plan, event, 2)
        assert session['revision'] == revision
        assert session['history'] == ['e2e4', 'e7e5']
        assert not resync_board(plan, event)
        assert resync_board(plan, dict(revision=f"{session['token']}:{revision}"))
        assert session['revision'] == revision + 1
        assert session['history'] == ['e2e4', 'e7e5']
    assert not resync_board(plan, dict(revision='another-session:1'))
    session['paused'] = True
    before = session['revision']
    assert receive_move(plan, dict(event, revision=f"{session['token']}:{before}"), 3)
    assert session['revision'] == before + 1
    assert session['history'] == ['e2e4', 'e7e5']


def test_recovery_delivers_a_missing_move_exactly_once():
    from opening_course_state import resync_board, receive_move
    plan = new_course()
    session = begin_line(plan, course_lines(plan)[0]['id'])
    event = dict(uci='e2e4', fen=board_for(session).fen(),
                 revision=f"{session['token']}:{session['revision']}")
    assert resync_board(plan, event)
    revision = session['revision']
    assert session['history'] == ['e2e4', 'e7e5'] and session['phase'] == 'answer'
    for _ in range(5):
        assert not resync_board(plan, event)
        assert receive_move(plan, event, 10)
        assert session['revision'] == revision and session['history'] == ['e2e4', 'e7e5']


def test_rankings_use_live_progress_and_preserve_other_courses():
    from opening_course_state import opening_rankings
    plan = new_course()
    solve(plan, begin_line(plan, course_lines(plan)[0]['id']))
    other = select_course(plan, 'course-test', 'caro')
    rows = opening_rankings(other)
    assert rows[0]['id'] == 'italian'
    assert rows[0]['learned'] == 1
    assert rows[0]['position'] == 1
    assert next(row for row in rows if row['id'] == 'caro')['ratio'] == 0
    restored = select_course(other, 'course-test', 'italian')
    for item in ensure_course(restored).values():
        item.update(learned=True, mastery=10)
    rows = opening_rankings(restored)
    assert rows[0]['rank'] == 'Bronze' and rows[0]['points'] == 2
    from opening_repertoires import catalog
    assert len(rows) == len(catalog())
