import pytest
import classroom as rooms
import classroom_materials as materials
import classroom_trails as trails
import classroom_community as community


@pytest.fixture
def room(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'trails.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    teacher=rooms.enter_professor('teacher','password-teacher-123',rooms.issue_professor_key(owner,'teacher'))
    other=rooms.enter_professor('other','password-other-123',rooms.issue_professor_key(owner,'other'))
    seat=rooms.students(teacher)[0];pupil=rooms.login_student(seat['access_key'])
    return teacher,seat['id'],pupil,other


def candidate(kind='line',title='Italiana'):
    payload={'pgn':'1. e4 e5 2. Nf3 *','side':'white'}
    if kind=='tactic':payload=dict(fen='6rk/6pp/8/4N3/8/8/8/6K1 w - - 0 1',solution=['e5f7'])
    if kind=='exam':payload=dict(questions=[dict(kind='closed',prompt='Quem joga em L?',options=['Bispo','Cavalo'],answer=1,weight=1)])
    return dict(title=title,kind=kind,payload=payload,reviewed=True)


def add(token,student,draft,items,step=None):
    return trails.edit_draft(token,student,draft['revision'],dict(action='add',step=step),items)


def test_draft_survives_reload_can_rename_order_and_attach_mixed_activities(room):
    teacher,student,pupil,other=room
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate()])
    identifier=draft['steps'][0]['id']
    draft=add(teacher,student,draft,[candidate('tactic'),candidate('exam')],identifier)
    assert materials.list_materials(pupil)==[]
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='rename',step=identifier,title='Centro e iniciativa'))
    draft=add(teacher,student,draft,[candidate(title='Segunda linha')])
    ids=[s['id'] for s in draft['steps']][::-1]
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='order',order=ids))
    assert trails.load_draft(teacher,student)==draft
    assert draft['steps'][1]['title']=='Centro e iniciativa'
    assert [item['kind'] for item in draft['steps'][1]['items']]==['line','tactic','exam']
    assert trails.publish(teacher,student,draft['revision'])==4
    visible=materials.list_materials(pupil)
    assert len(visible)==4
    assert 'answer' not in next(item for item in visible if item['kind']=='exam')['payload']['questions'][0]
    with pytest.raises(PermissionError):trails.load_draft(other,student)


def test_lock_blocks_current_and_all_following_and_is_immediate(room):
    teacher,student,pupil,_=room
    draft=trails.load_draft(teacher,student)
    for kind in ('line','tactic','exam'):draft=add(teacher,student,draft,[candidate(kind)])
    trails.publish(teacher,student,draft['revision'])
    step=draft['steps'][1];tactic=step['items'][0]['id'];exam=draft['steps'][2]['items'][0]['id']
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=step['id']))
    assert len(materials.list_materials(pupil))==1
    assert [s['blocked'] for s in trails.student_trail(pupil)]==[False,True,True]
    assert trails.student_trail(pupil)[1]['materials']==[]
    with pytest.raises(PermissionError):materials.check_training(pupil,tactic,0,'e5f7',candidate('tactic')['payload']['fen'])
    with pytest.raises(PermissionError):materials.restart_training(pupil,tactic)
    with pytest.raises(PermissionError):materials.submit_exam(pupil,exam,[1])
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=step['id']))
    assert len(materials.list_materials(pupil))==3
    materials.check_training(pupil,tactic,0,'e5f7',candidate('tactic')['payload']['fen'])
    materials.submit_exam(pupil,exam,[1])
    trails.publish(teacher,student,draft['revision'])
    assert next(item for item in materials.list_materials(pupil) if item['id']==exam)['result']['score']==1
    assert next(item for item in materials.list_materials(pupil) if item['id']==tactic)['progress']['completed']==1


def test_unreviewed_and_stale_drops_are_rejected_without_duplicates(room):
    teacher,student,_,_=room;draft=trails.load_draft(teacher,student)
    with pytest.raises(ValueError):add(teacher,student,draft,[dict(candidate(),reviewed=False)])
    changed=add(teacher,student,draft,[candidate()])
    with pytest.raises(ValueError):add(teacher,student,draft,[candidate()])
    assert len(trails.load_draft(teacher,student)['steps'])==1
    with pytest.raises(ValueError):trails.publish(teacher,student,0)


def test_video_attachments_are_private_and_locked_on_the_server(room):
    teacher,student,pupil,other=room
    video=community.publish_video(teacher,'Vídeo',url='https://example.com/lesson.mp4')
    foreign=community.publish_video(other,'Outro',url='https://example.com/other.mp4')
    draft=trails.load_draft(teacher,student)
    item=dict(title='Vídeo da linha',kind='video',payload=dict(video_id=video),reviewed=True)
    with pytest.raises(PermissionError):add(teacher,student,draft,[dict(item,payload=dict(video_id=foreign))])
    draft=add(teacher,student,draft,[item]);trails.publish(teacher,student,draft['revision'])
    identifier=draft['steps'][0]['items'][0]['id']
    assert materials.authorized_video(pupil,identifier)['video_id']==video
    trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=draft['steps'][0]['id']))
    with pytest.raises(PermissionError):materials.authorized_video(pupil,identifier)


def test_course_reuse_preserves_steps_locks_and_reopens_as_a_draft(room):
    import classroom_courses as courses
    teacher,student,pupil,_=room
    draft=trails.load_draft(teacher,student)
    for title in ('Linha A','Linha B'):draft=add(teacher,student,draft,[candidate(title=title)])
    ids=[step['id'] for step in draft['steps']][::-1]
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='order',order=ids))
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=ids[1]))
    trails.publish(teacher,student,draft['revision'])
    course=courses.save_course(teacher,student,'Reutilizável')
    target=rooms.students(teacher)[1];learner=rooms.login_student(target['access_key'])
    courses.assign_course(teacher,course,target['id'])
    assert [step['title'] for step in trails.student_trail(learner)]==['Linha B','Linha A']
    assert [step['blocked'] for step in trails.student_trail(learner)]==[False,True]
    copied=trails.load_draft(teacher,target['id'])
    assert len(copied['steps'])==2
    assert all(new['id']!=old['id'] for new,old in zip(copied['steps'],draft['steps']))
    trails.publish(teacher,target['id'],copied['revision'])
    assert len(materials.list_materials(learner))==1


def test_removing_a_published_step_hides_content_without_deleting_results(room):
    import classroom_courses as courses
    teacher,student,pupil,_=room
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate('exam')])
    draft=add(teacher,student,draft,[candidate('line')])
    trails.publish(teacher,student,draft['revision'])
    exam_id=draft['steps'][0]['items'][0]['id']
    materials.submit_exam(pupil,exam_id,[1])
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='remove',step=draft['steps'][0]['id']))
    trails.publish(teacher,student,draft['revision'])
    assert all(item['id']!=exam_id for item in materials.list_materials(teacher,student))
    with rooms.database() as db:assert db.execute('SELECT 1 FROM lesson_results WHERE material=?',(exam_id,)).fetchone()
    course=courses.save_course(teacher,student,'Sem arquivo removido')
    assert len(next(item for item in courses.list_courses(teacher) if item['id']==course)['payload'])==1


def test_generic_palette_drafts_need_review_and_teacher_orders_events(room):
    teacher,student,pupil,_=room
    draft=trails.load_draft(teacher,student)
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='add_event',kind='note'))
    step=draft['steps'][0]
    assert not step['items'][0]['reviewed']
    with pytest.raises(ValueError):trails.publish(teacher,student,draft['revision'])
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='save_item',step=step['id'],item=step['items'][0]['id'],title='Plano',payload=dict(text='Desenvolver primeiro'),reviewed=True))
    draft=add(teacher,student,draft,[candidate()],step['id'])
    item_ids=[item['id'] for item in draft['steps'][0]['items']][::-1]
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='item_order',step=step['id'],order=item_ids))
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='update_step',step=step['id'],title='Linha livre',notes='Vídeo e explicação antes de praticar.'))
    trails.publish(teacher,student,draft['revision'])
    visible=trails.student_trail(pupil)[0]
    assert visible['materials']==item_ids
    assert visible['notes']=='Vídeo e explicação antes de praticar.'
    assert next(item for item in materials.list_materials(pupil) if item['kind']=='note')['payload']['text']=='Desenvolver primeiro'


def test_editing_published_content_keeps_old_answers_in_a_separate_version(room):
    teacher,student,pupil,_=room
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate('exam')])
    trails.publish(teacher,student,draft['revision'])
    step=draft['steps'][0];item=step['items'][0]
    materials.submit_exam(pupil,item['id'],[1])
    replacement=dict(item['payload']);replacement['questions']=[dict(replacement['questions'][0],prompt='Nova pergunta')]
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='save_item',step=step['id'],item=item['id'],title='Prova revisada',payload=replacement,reviewed=True))
    new_id=draft['steps'][0]['items'][0]['id']
    assert new_id!=item['id']
    trails.publish(teacher,student,draft['revision'])
    assert materials.list_materials(pupil)[0]['result'] is None
    with rooms.database() as db:assert db.execute('SELECT 1 FROM lesson_results WHERE material=?',(item['id'],)).fetchone()
