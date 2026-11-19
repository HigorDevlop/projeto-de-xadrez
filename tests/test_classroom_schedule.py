import pytest
import classroom_trails as trails
import classroom_materials as materials
from test_classroom_trails import room, candidate, add


def test_schedule_blocks_all_access_until_release_and_survives_publish(room,monkeypatch):
    import classroom_schedule as schedule
    teacher,student,pupil,_=room
    monkeypatch.setattr(schedule.time,'time',lambda:1000.)
    draft=trails.load_draft(teacher,student)
    draft=add(teacher,student,draft,[candidate()])
    step=draft['steps'][0]
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=step['id'],locked=True,release_at=2000.))
    trails.publish(teacher,student,draft['revision'])
    assert not materials.list_materials(pupil)
    assert trails.student_trail(pupil)[0]['blocked']
    item=step['items'][0]
    board,moves=materials.training_moves(item['payload'],'line')
    with pytest.raises(PermissionError):materials.check_training(pupil,item['id'],0,moves[0],board.fen())
    monkeypatch.setattr(schedule.time,'time',lambda:2000.)
    assert not trails.student_trail(pupil)[0]['blocked']
    assert len(materials.list_materials(pupil))==1
    assert materials.check_training(pupil,item['id'],0,moves[0],board.fen())['correct']


def test_invalid_dates_and_manual_lock(room,monkeypatch):
    import classroom_schedule as schedule
    teacher,student,pupil,_=room
    monkeypatch.setattr(schedule.time,'time',lambda:1000.)
    draft=add(teacher,student,trails.load_draft(teacher,student),[candidate()])
    step=draft['steps'][0]
    for invalid in (999.,float('nan'),True,'tomorrow'):
        with pytest.raises(ValueError):trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=step['id'],locked=True,release_at=invalid))
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=step['id'],locked=True))
    trails.publish(teacher,student,draft['revision'])
    monkeypatch.setattr(schedule.time,'time',lambda:999999.)
    assert trails.student_trail(pupil)[0]['blocked']
    trails.edit_draft(teacher,student,draft['revision'],dict(action='lock',step=step['id'],locked=False))
    assert not trails.student_trail(pupil)[0]['blocked']
