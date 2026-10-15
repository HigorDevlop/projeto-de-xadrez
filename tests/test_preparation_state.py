"""Calendar, active training time and lesson progression with explicit clocks."""
from copy import deepcopy
from datetime import datetime
import json

import pytest

from preparation_state import (
    LOCAL_ZONE, STAGES, STAGE_SECONDS, advance_lesson, available_stage,
    day_progress, lesson_step, load_plan, new_plan, pause_stage, plan_path,
    record_lesson_answer, save_plan, start_stage, tactic_limit, tick, today,
)


def clock(day='2026-09-24', at='12:00:00'):
    return datetime.fromisoformat(f'{day}T{at}').replace(tzinfo=LOCAL_ZONE).timestamp()


def make_plan():
    return new_plan('Jogador', '2026-09-24', '2026-09-26', ['Italiana'],
                    {'source': 'Livro de São Paulo', 'tactics': []})


@pytest.mark.parametrize('start,end', [
    ('2026-09-26', '2026-09-24'),
    ('2026-02-30', '2026-09-24'),
    ('not-a-date', '2026-09-24'),
    ('2026-09-24', '2027-09-26'),
])
def test_invalid_calendar_is_rejected(start, end):
    with pytest.raises(ValueError):
        new_plan('Jogador', start, end, ['Italiana'])


def test_plan_requires_an_opening_and_accepts_a_single_day():
    with pytest.raises(ValueError, match='abertura'):
        new_plan('Jogador', '2026-09-24', '2026-09-24', [])
    plan = new_plan('Jogador', '2026-09-24', '2026-09-24', ['Siciliana'])
    assert plan['start'] == plan['end'] == '2026-09-24'
    assert plan['openings'] == ['Siciliana']
    assert plan['days'] == {} and plan['active'] is None


def test_selection_limit_is_enforced_by_plan_not_only_interface():
    with pytest.raises(ValueError, match='máximo 4'):
        new_plan('Jogador', '2026-09-24', '2026-09-24', list('ABCDE'))
    assert len(new_plan('Jogador', '2026-09-24', '2026-09-24', list('ABCD'))['openings']) == 4


def test_real_metrics_do_not_invent_accuracy_or_double_count_learned_lines():
    from preparation_state import record_attempt, record_learned_line, training_metrics, finish_plan
    plan = make_plan()
    assert training_metrics(plan)['accuracy'] is None
    for correct in (False, True, True, True):
        record_attempt(plan, correct)
    record_learned_line(plan, 'italiana-1')
    record_learned_line(plan, 'italiana-1')
    assert training_metrics(plan) == {'accuracy': 75.0, 'attempts': 4, 'correct': 3, 'lines': 1}
    start_stage(plan, 'opening', clock())
    finish_plan(plan, clock(at='12:03:00'))
    assert plan['active'] is None
    assert not available_stage(plan, 'opening', now=clock(at='12:04:00'))
    assert day_progress(plan, '2026-09-24')['opening']['seconds'] == 180
    assert not day_progress(plan, '2026-09-24')['opening']['done']


def test_phase_order_and_future_dates_cannot_be_bypassed():
    plan, now = make_plan(), clock()
    assert STAGES == ('opening', 'middlegame', 'tactics')
    assert available_stage(plan, 'opening', now=now)
    assert not available_stage(plan, 'middlegame', now=now)
    assert not available_stage(plan, 'tactics', now=now)
    for stage in ('middlegame', 'tactics'):
        with pytest.raises(ValueError):
            start_stage(plan, stage, now=now)
    for day in ('2026-09-23', '2026-09-25'):
        assert not available_stage(plan, 'opening', day=day, now=now)
    with pytest.raises(ValueError):
        start_stage(plan, 'opening', now=clock('2026-09-23'))
    with pytest.raises(ValueError):
        start_stage(plan, 'opening', now=clock('2026-09-27'))


def test_each_phase_has_thirty_minutes_and_overrun_never_charges_the_next():
    plan, now = make_plan(), clock()
    assert STAGE_SECONDS == 30 * 60
    for index, stage in enumerate(STAGES):
        start_stage(plan, stage, now=now)
        assert not tick(plan, now=now + 1799)
        progress = day_progress(plan, '2026-09-24')
        assert progress[stage]['seconds'] == 1799
        assert not progress[stage]['done']
        assert tick(plan, now=now + 2100)
        assert progress[stage]['seconds'] == 1800
        assert progress[stage]['done']
        assert plan['active'] is None
        assert not available_stage(plan, stage, now=now + 2100)
        for remaining in STAGES[index + 1:]:
            assert progress[remaining]['seconds'] == 0
            assert not progress[remaining]['done']
        if index + 1 < len(STAGES):
            assert available_stage(plan, STAGES[index + 1], now=now + 2100)
        now += 2100


def test_pause_and_resume_do_not_count_time_away():
    plan, now = make_plan(), clock()
    start_stage(plan, 'opening', now=now)
    tick(plan, now=now + 120)
    pause_stage(plan, now=now + 180)
    assert day_progress(plan, '2026-09-24')['opening']['seconds'] == 180
    assert not tick(plan, now=now + 4 * 3600)
    assert day_progress(plan, '2026-09-24')['opening']['seconds'] == 180
    start_stage(plan, 'opening', now=now + 4 * 3600)
    tick(plan, now=now + 4 * 3600 + 60)
    assert day_progress(plan, '2026-09-24')['opening']['seconds'] == 240
    assert not day_progress(plan, '2026-09-24')['opening']['done']


def test_midnight_stops_old_day_and_new_day_starts_with_opening():
    plan = make_plan()
    start = clock(at='23:50:00')
    midnight = clock('2026-09-25', '00:00:00')
    after = clock('2026-09-25', '00:20:00')
    assert str(today(midnight - 1)) == '2026-09-24'
    assert str(today(midnight)) == '2026-09-25'
    start_stage(plan, 'opening', now=start)
    assert tick(plan, now=after)
    assert plan['active'] is None
    assert plan['days']['2026-09-24']['opening']['seconds'] == 600
    assert not plan['days']['2026-09-24']['opening']['done']
    assert '2026-09-25' not in plan['days']
    assert available_stage(plan, 'opening', now=after)
    assert not available_stage(plan, 'middlegame', now=after)
    assert not available_stage(plan, 'tactics', now=after)
    start_stage(plan, 'opening', now=after)
    tick(plan, now=after + 60)
    assert plan['active']['day'] == '2026-09-25'
    assert plan['days']['2026-09-25']['opening']['seconds'] == 60
    assert plan['days']['2026-09-24']['opening']['seconds'] == 600


def test_completed_previous_day_does_not_unlock_later_phases_on_new_day():
    plan, now = make_plan(), clock()
    for stage in STAGES:
        start_stage(plan, stage, now=now)
        tick(plan, now=now + STAGE_SECONDS)
        now += STAGE_SECONDS
    next_day = clock('2026-09-25')
    assert available_stage(plan, 'opening', now=next_day)
    assert not available_stage(plan, 'middlegame', now=next_day)
    assert not available_stage(plan, 'tactics', now=next_day)


def test_saved_plan_is_isolated_per_user_and_load_never_charges_offline_time(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    plan, now = make_plan(), clock()
    start_stage(plan, 'opening', now=now)
    tick(plan, now=now + 90)
    plan['course']['step'] = 3
    save_plan(plan)
    assert plan_path('Jogador').parent == tmp_path
    assert plan_path('Jogador') == plan_path('jogador')
    assert len(list(tmp_path.glob('*.json'))) == 1
    assert not list(tmp_path.glob('*.tmp'))
    saved = json.loads(plan_path('Jogador').read_text(encoding='utf-8'))
    assert saved['active'] is not None
    restored = load_plan('jogador')
    assert restored['active'] is None
    assert restored['course']['step'] == 3
    assert restored['material']['source'] == 'Livro de São Paulo'
    assert not tick(restored, now=now + 4 * 3600)
    assert restored['days']['2026-09-24']['opening']['seconds'] == 90
    start_stage(restored, 'opening', now=now + 4 * 3600)
    tick(restored, now=now + 4 * 3600 + 30)
    assert restored['days']['2026-09-24']['opening']['seconds'] == 120
    assert plan['days']['2026-09-24']['opening']['seconds'] == 90
    assert load_plan('Outro jogador') is None


def test_missing_corrupt_and_unsupported_saved_plans_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    assert load_plan('Jogador') is None
    path = plan_path('Jogador')
    path.write_text('{invalid json', encoding='utf-8')
    assert load_plan('Jogador') is None
    plan = make_plan()
    plan['version'] = 999
    path.write_text(json.dumps(plan), encoding='utf-8')
    assert load_plan('Jogador') is None


@pytest.fixture
def lesson_steps():
    return [{'uci': uci} for uci in ('e2e4', 'g1f3', 'f1c4', 'd2d3', 'c1e3')]


def test_guide_and_recall_require_five_correct_moves_before_a_shuffled_quiz(lesson_steps):
    course = make_plan()['course']
    for mode in ('guide', 'recall'):
        assert course['mode'] == mode
        for index, step in enumerate(lesson_steps):
            assert course['step'] == index
            assert lesson_step(course, lesson_steps) == step
            assert not record_lesson_answer(course, lesson_steps, 'a2a3')
            assert course['help'] and not course['answered']
            assert not advance_lesson(course, lesson_steps, seed='Jogador')
            assert course['step'] == index
            assert record_lesson_answer(course, lesson_steps, step['uci'])
            snapshot = deepcopy(course)
            assert not record_lesson_answer(course, lesson_steps, 'a2a3')
            assert course == snapshot
            assert not advance_lesson(course, lesson_steps, seed='Jogador')
    assert course['mode'] == 'quiz'
    assert sorted(course['queue']) == list(range(5))
    assert course['queue'] != list(range(5))
    assert course['line'] == 0


def test_quiz_repeats_every_error_until_correct_before_advancing_line(lesson_steps):
    course = make_plan()['course']
    for _ in range(10):
        assert record_lesson_answer(course, lesson_steps, lesson_step(course, lesson_steps)['uci'])
        advance_lesson(course, lesson_steps, seed='Jogador')
    order = list(course['queue'])
    missed = {order[1], order[3]}
    for index in order:
        answer = 'a2a3' if index in missed else lesson_steps[index]['uci']
        assert record_lesson_answer(course, lesson_steps, answer) is (index not in missed)
        assert course['answered']
        assert not advance_lesson(course, lesson_steps)
        assert course['line'] == 0
    assert set(course['queue']) == missed
    assert course['mode'] == 'quiz'
    first_retry = course['queue'][0]
    assert not record_lesson_answer(course, lesson_steps, 'a2a3')
    assert not advance_lesson(course, lesson_steps)
    assert record_lesson_answer(course, lesson_steps, lesson_step(course, lesson_steps)['uci'])
    assert not advance_lesson(course, lesson_steps)
    assert course['queue'] == [first_retry]
    assert course['line'] == 0
    assert record_lesson_answer(course, lesson_steps, lesson_step(course, lesson_steps)['uci'])
    assert advance_lesson(course, lesson_steps)
    assert course['line'] == 1
    assert course['mode'] == 'guide' and course['step'] == 0
    assert not course['queue'] and not course['retry'] and not course['marks']
    assert not course['answered'] and not course['help']


@pytest.mark.parametrize('count,expected', [(0, 0), (4, 4), (10, 10), (25, 10)])
def test_tactics_are_limited_to_ten_without_fabricating_missing_positions(count, expected):
    assert tactic_limit({'tactics': list(range(count))}) == expected
    assert tactic_limit({}) == 0
