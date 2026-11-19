import pytest
import classroom as rooms
import classroom_materials as materials
import classroom_trails as trails
import classroom_training_sessions as sessions
from test_classroom_trails import room,add,candidate


def test_saved_draft_reused_without_publishing_or_copying_answers(room):
    teacher,student,pupil,_=room
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate('exam')])
    model=sessions.save_template(teacher,student,draft['revision'],'Primeira sessão')
    assert materials.list_materials(pupil)==[]
    trails.publish(teacher,student,draft['revision'])
    old=draft['steps'][0]['items'][0]['id']
    materials.submit_exam(pupil,old,[1])
    assert sessions.progress(teacher,student)[0]['completed']
    new=sessions.new_draft(teacher,student,draft['revision'],save_title='Cópia salva')
    assert new['steps']==[] and len(sessions.library(teacher))==2
    assert materials.list_materials(pupil)[0]['id']==old
    loaded=sessions.new_draft(teacher,student,new['revision'],title='Segunda sessão',template=model)
    new_id=loaded['steps'][0]['items'][0]['id']
    assert new_id!=old
    assert len(sessions.history(teacher,student))==0
    trails.publish(teacher,student,loaded['revision'])
    assert [item['id'] for item in materials.list_materials(pupil)]==[new_id]
    assert sessions.progress(teacher,student)[0]['completed'] is False
    history=sessions.history(teacher,student)
    assert len(history)==1 and history[0]['payload']['results'][0]['material']==old


def test_reset_only_selected_student_and_stale_revision_is_rejected(room):
    teacher,student,pupil,_=room
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate('exam')])
    trails.publish(teacher,student,draft['revision'])
    materials.submit_exam(pupil,draft['steps'][0]['items'][0]['id'],[1])
    model=sessions.save_template(teacher,student,draft['revision'],'Modelo')
    target=rooms.students(teacher)[1]
    other=sessions.new_draft(teacher,target['id'],0,template=model)
    trails.publish(teacher,target['id'],other['revision'])
    with pytest.raises(ValueError):sessions.reset(teacher,student,0)
    sessions.reset(teacher,student,draft['revision'])
    assert sessions.progress(teacher,student)==[]
    assert trails.student_trail(pupil)==[]
    assert trails.load_draft(teacher,student)['steps']==[]
    assert len(sessions.history(teacher,student))==1
    assert len(sessions.library(teacher))==1
    assert len(sessions.progress(teacher,target['id']))==1


def test_teacher_cannot_read_or_change_another_room_sessions(room):
    teacher,student,pupil,other=room
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate()])
    sessions.save_template(teacher,student,draft['revision'],'Privada')
    assert sessions.library(other)==[]
    for actor in [other,pupil]:
        with pytest.raises(PermissionError):sessions.progress(actor,student)
        with pytest.raises(PermissionError):sessions.history(actor,student)
        with pytest.raises(PermissionError):sessions.reset(actor,student,draft['revision'])


def test_teacher_sees_tactical_block_progress_and_next_activity_unlock(room):
    import classroom_tactic_blocks as blocks
    teacher,student,pupil,_=room
    puzzle=candidate('tactic')['payload']
    pack=dict(title='Bloco de táticos',kind='tactic',payload=dict(puzzles=[puzzle]),reviewed=True)
    draft=add(teacher,student,trails.load_draft(teacher,student),[pack,candidate()])
    trails.publish(teacher,student,draft['revision'])
    rows=sessions.progress(teacher,student)
    assert not rows[0]['completed'] and rows[1]['blocked']
    blocks.act(pupil,rows[0]['id'],0,0,'e5f7',puzzle['fen'])
    rows=sessions.progress(teacher,student)
    assert rows[0]['completed'] and rows[0]['accuracy']==100 and rows[0]['progress']==1
    assert not rows[1]['blocked']
