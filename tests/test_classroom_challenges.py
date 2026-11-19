from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import json

import chess
import pytest
import classroom as rooms
import classroom_materials as materials
import classroom_challenges as challenges


@pytest.fixture
def classroom(tmp_path, monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'challenges.sqlite3'))
    owner = rooms.bootstrap_owner('creator', 'creator-password-123')
    teachers = [rooms.register_professor(name, 'teacher-password-123', rooms.issue_professor_key(owner, name))
                for name in ('teacher-a', 'teacher-b')]
    seats = [rooms.students(token) for token in teachers]
    students = [rooms.login_student(seats[0][i]['access_key']) for i in (0, 1)]
    outsider = rooms.login_student(seats[1][0]['access_key'])
    return owner, teachers, seats, students, outsider


def publish(token, event='publication-001', **kwargs):
    values = dict(title='Centro', fen=chess.STARTING_FEN, instructions='Jogue um lance para ocupar o centro.', solution='e2e4')
    values.update(kwargs)
    return challenges.publish(token, event=event, **values)


def test_permissions_room_isolation_and_hidden_answer(classroom):
    owner, teachers, seats, students, outsider = classroom
    group = publish(teachers[0])
    item, = challenges.student_challenges(students[0])
    assert set(item) == {'id', 'title', 'fen', 'instructions', 'result'}
    assert item['result'] is None and 'e2e4' not in json.dumps(item)
    assert materials.list_materials(students[0]) == []
    assert challenges.student_challenges(outsider) == []
    assert challenges.results(teachers[1]) == []
    assert challenges.results(owner) == []  # Admin's map is its own room, not a global feed.
    assert len(challenges.results(teachers[0])) == 4
    for token in (students[0], outsider):
        with pytest.raises(PermissionError): publish(token)
        with pytest.raises(PermissionError): challenges.results(token)
    for token in (teachers[0], teachers[1], students[1], outsider):
        with pytest.raises(PermissionError): challenges.submit(token, item['id'], item['fen'], 'e2e4')
    assert all(row['challenge'] == group and row['result'] is None for row in challenges.results(teachers[0]))


@pytest.mark.parametrize('changes', [
    {'fen': 'invalid'}, {'fen': '8/8/8/8/8/8/8/8 w - - 0 1'},
    {'fen': '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', 'solution': 'h8h7'},
    {'solution': 'e2e5'}, {'solution': '0000'}, {'instructions': ''}, {'title': ''},
])
def test_invalid_publication_has_no_assignments(classroom, changes):
    _, teachers, _, _, _ = classroom
    with pytest.raises(ValueError): publish(teachers[0], **changes)
    assert challenges.results(teachers[0]) == []


def test_idempotent_publication_and_first_submission(classroom):
    _, teachers, _, students, _ = classroom
    assert publish(teachers[0]) == publish(teachers[0])
    assert len(challenges.results(teachers[0])) == 4
    with pytest.raises(ValueError): publish(teachers[0], solution='d2d4')
    item, = challenges.student_challenges(students[0])
    for fen, move in [(item['fen'], 'e2e5'), (item['fen'], '0000'), ('stale-fen', 'e2e4')]:
        with pytest.raises(ValueError): challenges.submit(students[0], item['id'], fen, move)
    assert challenges.student_challenges(students[0])[0]['result'] is None
    first = challenges.submit(students[0], item['id'], item['fen'], 'd2d4')
    assert not first['correct'] and first['solution_san'] == 'e4'
    assert challenges.submit(students[0], item['id'], item['fen'], 'e2e4') == first
    assert challenges.student_challenges(students[1])[0]['result'] is None
    with rooms.database() as db:
        assert db.execute('SELECT COUNT(*) FROM lesson_results').fetchone()[0] == 1
    results = challenges.results(teachers[0])
    assert sum(row['result'] is not None for row in results) == 1


def test_concurrent_submissions_store_only_one_result(classroom):
    _, teachers, _, students, _ = classroom
    publish(teachers[0])
    item, = challenges.student_challenges(students[0])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: challenges.submit(students[0], item['id'], item['fen'], 'e2e4'), range(6)))
    assert all(result == results[0] and result['correct'] for result in results)
    with rooms.database() as db:
        assert db.execute('SELECT COUNT(*) FROM lesson_results').fetchone()[0] == 1


def test_unpublished_revoked_and_black_promotion(classroom):
    owner, teachers, _, students, _ = classroom
    fen = '7k/8/8/8/8/8/p7/7K b - - 0 40'
    publish(teachers[0], fen=fen, solution='a2a1q')
    item, = challenges.student_challenges(students[0])
    materials.set_published(teachers[0], item['id'], False)
    assert not challenges.student_challenges(students[0])
    with pytest.raises(PermissionError): challenges.submit(students[0], item['id'], fen, 'a2a1q')
    materials.set_published(teachers[0], item['id'], True)
    assert challenges.submit(students[0], item['id'], fen, 'a2a1q')['correct']
    rooms.set_professor_access(owner, rooms.identity(teachers[0])['id'], False)
    with pytest.raises(PermissionError): challenges.student_challenges(students[0])
    with pytest.raises(PermissionError): challenges.submit(students[0], item['id'], fen, 'a2a1q')


def test_ui_publication_and_student_attempt_without_answer_in_board(classroom, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import classroom_challenges_ui as ui
    _, teachers, _, students, outsider = classroom
    teacher = AppTest.from_string('import streamlit as st\nfrom classroom_challenges_ui import teacher\nteacher(st.session_state.token)', default_timeout=15)
    teacher.session_state.token = teachers[0]
    teacher.run()
    teacher.text_input[0].set_value('Centro')
    teacher.text_input[2].set_value('e2e4')
    teacher.text_area[0].set_value('Ocupe o centro.')
    teacher.button[0].click().run()
    assert not teacher.exception and len(challenges.results(teachers[0])) == 4
    pending, calls = [], []
    def board(position, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(move=pending.pop(0) if pending else None)
    monkeypatch.setattr(ui, 'interactive_board', board)
    app = AppTest.from_string('import streamlit as st\nfrom classroom_challenges_ui import student\nstudent(st.session_state.token)', default_timeout=15)
    app.session_state.token = students[0]
    app.run()
    assert not app.exception and 'training_expected' not in calls[-1] and 'hint_move' not in calls[-1]
    assert not any('Lance esperado pelo professor:' in m.value for m in app.markdown)
    item, = challenges.student_challenges(students[0])
    pending.append(dict(revision=item['id'], fen=item['fen'], uci='e2e4'))
    app.run()
    assert not app.exception and calls[-1]['disabled']
    assert any('Lance esperado pelo professor: e4' in m.value for m in app.markdown)
    app.session_state.token = outsider
    app.run()
    assert not app.exception and not app.selectbox
