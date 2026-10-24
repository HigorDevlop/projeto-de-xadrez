from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest

import classroom as rooms
from preparation_state import today
from test_browser_components import browser_page


def register_teacher(name,password):
    owner=rooms.login_owner('creator','creator-password-123')
    return rooms.register_professor(name,password,rooms.issue_professor_key(owner,name))


@pytest.fixture
def room(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    teacher_key=rooms.issue_professor_key(owner,'mestre')
    teacher=rooms.register_professor('mestre','senha-segura-123',teacher_key)
    student=rooms.students(teacher)[0]
    student['teacher_key']=teacher_key
    token=rooms.login_student(student['access_key'])
    return teacher,student,token


def task(teacher,student,**changes):
    data=dict(openings=['italian'],lines=1,positions=1,tactics=1,minutes=1,weekdays=list(range(7)),start=today())
    data.update(changes)
    return rooms.save_routine(teacher,student['id'],**data)


def test_four_unique_seats_login_and_exclusive_permissions(room):
    teacher,student,token=room
    seats=rooms.students(teacher)
    assert len(seats)==4 and len({s['access_key'] for s in seats})==4
    assert rooms.identity(token)['id']==student['id']
    assert rooms.identity(rooms.login_professor('MESTRE','senha-segura-123',student['teacher_key']))['role']=='professor'
    with pytest.raises(ValueError):rooms.login_professor('mestre','wrong',student['teacher_key'])
    with pytest.raises(ValueError):rooms.register_professor('mestre','senha-segura-123')
    with pytest.raises(PermissionError):rooms.students(token)
    with pytest.raises(PermissionError):task(token,student)
    with pytest.raises(PermissionError):rooms.warn(token,student['id'],'fraude')
    other=register_teacher('outra-sala','outra-senha-123')
    with pytest.raises(PermissionError):rooms.dashboard(other,student['id'])
    with pytest.raises(PermissionError):task(other,student)
    with pytest.raises(PermissionError):rooms.dashboard(token,seats[1]['id'])


def test_third_warning_revokes_key_and_every_existing_session(room):
    teacher,student,token=room
    second=rooms.login_student(student['access_key'])
    assert rooms.warn(teacher,student['id'],'Primeira falta')==1
    assert rooms.identity(token)
    assert rooms.warn(teacher,student['id'],'Segunda falta')==2
    assert rooms.warn(teacher,student['id'],'Terceira falta')==3
    assert rooms.identity(token) is None and rooms.identity(second) is None
    with pytest.raises(ValueError):rooms.login_student(student['access_key'])
    with pytest.raises(PermissionError):rooms.record(token,'after-ban','tactics',True,True,line='x')
    with pytest.raises(PermissionError):rooms.pulse(token,True)
    banned=rooms.students(teacher)[0]
    assert banned['banned'] and banned['access_key'] is None
    assert len(rooms.dashboard(teacher,student['id'])['warnings'])==3
    assert rooms.students(teacher)[1]['access_key']  # Other students retain access.


def test_concurrent_warnings_are_atomic(room):
    teacher,student,token=room
    def warning(i):
        try:return rooms.warn(teacher,student['id'],f'Falta {i}')
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=4) as executor:
        result=list(executor.map(warning,range(4)))
    assert sorted(x for x in result if x is not None)==[1,2,3]
    assert rooms.students(teacher)[0]['warnings']==3


def test_actual_metrics_deduplicate_recovery_and_daily_time(room):
    teacher,student,token=room
    config=task(teacher,student)
    line=config['line_ids'][0]
    rooms.record(token,'attempt-1','opening',False,line=line,states={'0':'wrong'})
    rooms.record(token,'attempt-1','opening',False,line=line,states={'0':'wrong'})
    rooms.record(token,'attempt-2','opening',True,line=line,states={'0':'unknown'})
    assert rooms.dashboard(teacher,student['id'])['states']['unknown']==1
    rooms.record(token,'attempt-3','opening',True,line=line,states={'0':'correct'})
    rooms.record(token,'complete','line',line=line)
    rooms.record(token,'t-1','tactics',False,line='puzzle-1')
    rooms.record(token,'t-2','tactics',True,True,line='puzzle-1')
    rooms.record(token,'t-3','tactics',True,True,line='puzzle-1')
    now=__import__('time').time()
    rooms.pulse(token,True,now)
    # A second logged-in tab may not double-count the same interval.
    second=rooms.login_student(student['access_key'])
    for step in range(1,7):
        rooms.pulse(token,True,now+10*step)
        rooms.pulse(second,True,now+10*step)
    summary=rooms.dashboard(teacher,student['id'])
    assert summary['seconds']==60 and summary['fulfilled']
    assert summary['tactics']==1 and summary['lines']==1
    assert summary['accuracy']['opening']==pytest.approx(200/3)
    assert summary['accuracy']['tactics']==pytest.approx(200/3)
    assert summary['states']['correct']==1
    rooms.pulse(token,False,now+70)
    rooms.pulse(token,True,now+3600)
    assert rooms.dashboard(token)['seconds']==60  # Offline time is not credited.
    rooms.pulse(token,True,now+7200)
    assert rooms.dashboard(token)['seconds']==60  # Closing without a final pulse also cannot credit offline time.


def test_validation_no_data_and_absence_audit(room,monkeypatch):
    teacher,student,token=room
    assert rooms.dashboard(token)['accuracy']['opening'] is None
    with pytest.raises(ValueError):task(teacher,student,positions=10000)
    with pytest.raises(ValueError):task(teacher,student,weekdays=[])
    with pytest.raises(ValueError):task(teacher,student,openings=['italian','caro'],lines=1)
    task(teacher,student)
    next_day=today()+timedelta(days=1)
    monkeypatch.setattr(rooms,'today',lambda *args:next_day)
    yesterday=rooms.attendance(teacher,student['id'])[1]
    assert yesterday['status']=='Falta / incompleta'
    assert yesterday['accuracy']['opening'] is None


def test_opening_attempts_are_authoritative_and_assignment_limits_lines(room):
    from opening_course_state import select_course,course_lines,begin_line,receive_move
    from opening_training_state import expected_move,board_for
    teacher,student,token=room
    config=task(teacher,student)
    plan=select_course(None,'classroom:'+student['id'],'italian')
    plan['classroom_line_ids']=config['line_ids']
    assert len(course_lines(plan))==1
    session=begin_line(plan,config['line_ids'][0],'practice')
    event=dict(uci=expected_move(plan,session),fen=board_for(session).fen(),revision=f"{session['token']}:{session['revision']}")
    assert receive_move(plan,event,100,token)
    assert rooms.dashboard(token)['accuracy']['opening']==100
    receive_move(plan,event,100,token)
    assert rooms.dashboard(token)['accuracy']['opening']==100
    rooms.warn(teacher,student['id'],'1');rooms.warn(teacher,student['id'],'2');rooms.warn(teacher,student['id'],'3')
    with pytest.raises(PermissionError):receive_move(plan,event,100,token)


def test_last_twenty_games_are_real_rows_with_opening_names(monkeypatch):
    import chesscom
    from classroom_ui import last_games
    pgn='[White "student"]\n[Black "other"]\n[Result "1-0"]\n[Opening "Italian Game"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 1-0'
    games=[dict(pgn=pgn,end_time=1000+i,white={'username':'student'},black={'username':'other'},url=f'https://example.test/{i}') for i in range(25)]
    monkeypatch.setattr(chesscom,'fetch_recent_games',lambda username,limit,max_months:games)
    last_games.clear()
    rows=last_games('student')
    assert len(rows)==20
    assert all(row['Abertura']!='Abertura não identificada' and row['Brancas']=='student' for row in rows)
    assert rows[0]['Partida']=='https://example.test/0'
    last_games.clear()


def test_activity_clock_survives_move_renders_and_stops_on_pause(browser_page):
    from test_browser_components import mount
    page=browser_page
    page.add_init_script('window.classroomTimers=[]')
    page.evaluate('''()=>{
      window.classroomTimers=[];window.classroomNow=100000;
      Date.now=()=>window.classroomNow;
      window.setInterval=fn=>{window.classroomTimers.push(fn);return window.classroomTimers.length;};
      document.hasFocus=()=>true;
    }''')
    mount(page,'classroom_ui.py',{'paused':False})
    page.evaluate("document.dispatchEvent(new PointerEvent('pointerdown'))")
    page.evaluate("window.render({paused:false});window.classroomNow+=10000;window.classroomTimers[0]()")
    assert page.evaluate('window.classroomTimers.length')==1
    assert page.evaluate('window.events.at(-1).value.active')
    page.evaluate("window.render({paused:true});window.classroomTimers[0]()")
    assert not page.evaluate('window.events.at(-1).value.active')
    page.evaluate("window.render({paused:false});window.classroomNow+=61000;window.classroomTimers[0]()")
    assert not page.evaluate('window.events.at(-1).value.active')
