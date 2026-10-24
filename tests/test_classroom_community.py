import pytest
import classroom as rooms
import classroom_community as community
from streak_style import login_streak,flame
from preparation_state import today
from datetime import timedelta


@pytest.fixture
def school(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'community.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    teacher=rooms.register_professor('teacher','teacher-password-123',rooms.issue_professor_key(owner))
    seats=rooms.students(teacher)
    pupils=[rooms.login_student(row['access_key']) for row in seats[:2]]
    other=rooms.register_professor('outsider','outsider-password-123',rooms.issue_professor_key(owner))
    return teacher,seats,pupils,other


def test_group_and_private_messages_persist_and_isolate_members(school):
    teacher,seats,pupils,other=school
    room=seats[0]['room']
    community.send(teacher,'Olá turma',nonce='same')
    community.send(teacher,'Olá turma',nonce='same')
    community.send(pupils[0],'<script>text</script>')
    assert len(community.messages(pupils[1]))==2
    community.send(teacher,'Mensagem privada',seats[0]['id'])
    assert community.messages(pupils[0],seats[0]['id'])[0]['body']=='Mensagem privada'
    with pytest.raises(PermissionError):community.messages(pupils[1],seats[0]['id'])
    with pytest.raises(PermissionError):community.messages(other,room=room)
    with pytest.raises(PermissionError):community.send(pupils[0],'forjado',seats[1]['id'])
    with pytest.raises(ValueError):community.send(teacher,' ')


def test_videos_and_live_are_teacher_managed_with_authorized_signaling(school):
    teacher,seats,pupils,other=school
    room=seats[0]['room']
    community.publish_video(teacher,'Aula 1','https://example.com/aula.mp4')
    video=community.videos(pupils[0])[0]
    assert video['title']=='Aula 1'
    with pytest.raises(PermissionError):community.publish_video(pupils[0],'Aula','https://example.com/aula.mp4')
    with pytest.raises(PermissionError):community.video_media(other,video['id'],room)
    with pytest.raises(PermissionError):community.delete_video(pupils[0],video['id'])
    with pytest.raises(ValueError):community.publish_video(teacher,'Aula','http://localhost/secret')
    with pytest.raises(PermissionError):community.start_live(pupils[0])
    call=community.start_live(teacher)
    assert community.live(pupils[0])['id']==call
    host=community.join_live(teacher);viewer=community.join_live(pupils[0])
    second=community.join_live(pupils[1])
    packet=dict(target=viewer,kind='offer',payload={'type':'offer','sdp':'test'},nonce='offer')
    community.exchange(teacher,host,[packet])
    signals=community.exchange(pupils[0],viewer)['signals']
    assert len(signals)==1 and signals[0]['sender']==host
    community.exchange(teacher,host,[packet])
    assert len(community.exchange(pupils[0],viewer)['signals'])==1
    with pytest.raises(PermissionError):community.exchange(pupils[1],viewer)
    with pytest.raises(PermissionError):community.exchange(pupils[0],viewer,[dict(packet,target=second)])
    community.end_live(teacher)
    assert community.live(pupils[0]) is None
    with pytest.raises(PermissionError):community.exchange(pupils[0],viewer)
    community.delete_video(teacher,video['id'])
    assert community.videos(pupils[0])==[]


def test_streak_counts_real_days_not_repeated_logins_and_evolves_every_ten(school):
    teacher,_,pupils,_=school
    start=today()-timedelta(days=49)
    for i in range(50):
        assert login_streak(teacher,True,start+timedelta(days=i))==i+1
        assert login_streak(teacher,True,start+timedelta(days=i))==i+1
    assert login_streak(pupils[0])==0
    assert login_streak(teacher,True,today()+timedelta(days=2))==1
    designs=[flame(day) for day in (0,10,20,30,40,50)]
    assert len(set(designs))==6 and 'nível 5' in flame(80)


def test_recorded_videos_are_available_without_entering_training(school):
    teacher,seats,pupils,other=school
    user=rooms.register_user('viewer','viewer-password-123')
    rooms.join_room(user,seats[2]['access_key'])
    community.publish_video(teacher,'Aula permanente','https://example.com/lesson.mp4')
    assert community.recorded_room(user)==seats[2]['room']
    assert community.videos(user)[0]['title']=='Aula permanente'
    restored=rooms.restore_device(rooms.remember_device(user))
    assert community.videos(restored)[0]['title']=='Aula permanente'
    with rooms.database() as db:assert db.execute('SELECT COUNT(*) FROM training_visits').fetchone()[0]==0
    with pytest.raises(PermissionError):community.messages(user)
    with pytest.raises(PermissionError):community.start_live(user)
    with pytest.raises(PermissionError):community.videos(user,rooms.identity(other)['id'])
    for i in range(3):rooms.warn(teacher,seats[2]['id'],f'Falta {i}')
    assert rooms.identity(user)
    with pytest.raises(PermissionError):community.videos(user)
