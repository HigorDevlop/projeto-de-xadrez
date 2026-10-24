import pytest
import classroom as rooms


def test_only_creator_deletes_player_and_revokes_linked_sessions(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'accounts.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    player=rooms.register_user('player','password-player-123')
    other=rooms.register_user('other','password-other-123')
    identifier=rooms.identity(player)['id']
    teacher=rooms.enter_professor('teacher','password-teacher-123',rooms.issue_professor_key(owner,'teacher'))
    seat=rooms.students(teacher)[0]
    linked=rooms.join_room(player,seat['access_key'])
    device=rooms.remember_device(player)
    linked_device=rooms.remember_device(linked)
    rooms.save_chesscom_user(player,'saved-player')
    with pytest.raises(PermissionError):rooms.delete_user(other,identifier)
    with pytest.raises(PermissionError):rooms.delete_user(None,identifier)
    assert rooms.identity(player)
    rooms.delete_user(owner,identifier)
    assert rooms.identity(player) is None and rooms.identity(linked) is None
    assert rooms.restore_device(device) is None and rooms.restore_device(linked_device) is None
    with pytest.raises(ValueError):rooms.login_user('player','password-player-123')
    assert rooms.identity(other) and rooms.identity(teacher) and rooms.identity(owner)
    assert len(rooms.students(teacher))==4
    assert rooms.students(teacher)[0]['access_key']!=seat['access_key']
    assert not rooms.admin_overview(owner)['users'][0]['id']==identifier
    with pytest.raises(ValueError):rooms.delete_user(owner,rooms.identity(owner)['id'])
    assert rooms.identity(owner)


def test_deletion_keeps_training_records_and_does_not_leak_to_new_account(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'accounts.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    player=rooms.register_user('player','password-player-123')
    identifier=rooms.identity(player)['id']
    with rooms.database() as db:
        db.execute('INSERT INTO events(student,day,event_key,kind,correct,solved) VALUES(?,?,?,?,?,?)',
                   (identifier,'2026-10-24','progress','tactics',1,1))
    rooms.delete_user(owner,identifier)
    with rooms.database() as db:
        assert db.execute('SELECT COUNT(*) FROM events WHERE student=?',(identifier,)).fetchone()[0]==1
    replacement=rooms.register_user('player','password-player-new')
    assert rooms.identity(replacement)['id']!=identifier
