import pytest
import classroom as rooms
import classroom_sessions as visits
from preparation_state import today


@pytest.fixture
def training(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'visits.sqlite3'))
    clock=[rooms.time.time()]
    monkeypatch.setattr(rooms.time,'time',lambda:clock[0])
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    teacher=rooms.register_professor('teacher','teacher-password-123',rooms.issue_professor_key(owner))
    student=rooms.students(teacher)[0]
    pupil=rooms.login_student(student['access_key'])
    task=rooms.save_routine(teacher,student['id'],['italian'],1,1,0,1,list(range(7)),today())
    return teacher,student,pupil,task,clock,owner


def test_entry_records_presence_timer_and_private_early_exit(training):
    teacher,student,pupil,task,clock,owner=training
    first=visits.begin(pupil)
    assert first and visits.begin(pupil)==first
    assert rooms.dashboard(pupil)['present']
    assert visits.current(pupil)['remaining']==60
    clock[0]+=10;visits.heartbeat(pupil)
    clock[0]+=5;visits.leave(pupil)
    audit=visits.history(teacher,student['id'])
    assert audit[0]['seconds']==15 and audit[0]['early_exit'] and audit[0]['color']=='red'
    assert visits.history(owner,student['id'])[0]['status']=='Saída antecipada'
    assert not visits.current(pupil)['running']
    assert 'reason' not in visits.current(pupil) and 'early_exit' not in visits.current(pupil)
    with pytest.raises(PermissionError):visits.history(pupil,student['id'])
    with pytest.raises(PermissionError):visits.begin(teacher)
    clock[0]+=100
    assert visits.begin(pupil)!=first
    assert len(visits.history(teacher,student['id']))==2


def test_completion_stops_clock_green_even_before_target(training):
    teacher,student,pupil,task,clock,_=training
    visits.begin(pupil)
    clock[0]+=12;visits.heartbeat(pupil)
    rooms.record(pupil,'position','opening',True,line=task['line_ids'][0],states={'0':'correct'})
    clock[0]+=3
    rooms.record(pupil,'line','line',line=task['line_ids'][0])
    report=visits.history(teacher,student['id'])[0]
    assert report['completed'] and report['color']=='green' and report['seconds']==15
    assert report['status']=='Trilha concluída' and not report['early_exit']
    clock[0]+=500
    visits.leave(pupil)
    assert visits.current(pupil)['seconds']==15
    assert visits.begin(pupil) is None
    assert len(visits.history(teacher,student['id']))==1


def test_disconnection_stops_at_last_confirmed_heartbeat(training):
    teacher,student,pupil,task,clock,_=training
    visits.begin(pupil)
    clock[0]+=10;visits.heartbeat(pupil)
    clock[0]+=100
    row=visits.history(teacher,student['id'])[0]
    assert row['seconds']==10 and row['color']=='red' and row['reason']=='Conexão encerrada'
    assert not visits.current(pupil)['running']
    visits.heartbeat(pupil)
    assert visits.history(teacher,student['id'])[0]['seconds']==10


def test_time_expired_without_trail_is_not_success_and_rooms_are_isolated(training):
    teacher,student,pupil,task,clock,owner=training
    visits.begin(pupil)
    for _i in range(7):clock[0]+=10;visits.heartbeat(pupil)
    assert visits.current(pupil)['remaining']==0
    visits.leave(pupil)
    row=visits.history(teacher,student['id'])[0]
    assert row['status']=='Trilha incompleta' and row['color']=='orange' and not row['completed']
    other=rooms.register_professor('other','other-password-123',rooms.issue_professor_key(owner))
    with pytest.raises(PermissionError):visits.history(other,student['id'])
