import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
import classroom as rooms


@pytest.fixture
def owner(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'auth.sqlite3'))
    return rooms.bootstrap_owner('criador','password-criador-123')


def test_only_creator_can_issue_single_use_teacher_keys(owner):
    with pytest.raises(ValueError):rooms.register_professor('intruso','password-intruso')
    with pytest.raises(ValueError):rooms.bootstrap_owner('outro','password-outro-123')
    assert rooms.identity(rooms.login_owner('criador','password-criador-123'))['role']=='admin'
    key=rooms.issue_professor_key(owner,'Professor convidado')
    professor=rooms.register_professor('professor','password-professor',key)
    with pytest.raises(ValueError):rooms.register_professor('professor2','password-professor',key)
    with pytest.raises(PermissionError):rooms.issue_professor_key(professor,'ilegal')
    student=rooms.students(professor)[0]
    pupil=rooms.login_student(student['access_key'])
    with pytest.raises(PermissionError):rooms.issue_professor_key(pupil,'ilegal')
    assert len(rooms.students(owner))==4
    rooms.update_student(owner,student['id'],'Nome escolhido pelo criador')
    assert rooms.students(owner)[0]['name']=='Nome escolhido pelo criador'
    unused=rooms.issue_professor_key(owner,'Revogar antes do uso')
    invitation=rooms.admin_overview(owner)['invitations'][0]
    rooms.revoke_professor_key(owner,invitation['id'])
    with pytest.raises(ValueError):rooms.register_professor('revogado','password-professor',unused)


def test_remembered_logins_validate_suspension_bans_and_logout(owner):
    key=rooms.issue_professor_key(owner,'P')
    professor=rooms.register_professor('professor','password-professor',key)
    row=rooms.students(professor)[0]
    pupil=rooms.login_student(row['access_key'])
    device=rooms.remember_device(pupil)
    resumed=rooms.restore_device(device)
    assert rooms.identity(resumed)['id']==row['id']
    with rooms.database() as db:
        assert not db.execute('SELECT token FROM devices WHERE token=?',(device,)).fetchone()
    rooms.forget_device(device)
    assert rooms.restore_device(device) is None
    device=rooms.remember_device(pupil)
    rooms.warn(owner,row['id'],'1');rooms.warn(owner,row['id'],'2');rooms.warn(owner,row['id'],'3')
    assert rooms.restore_device(device) is None and rooms.identity(resumed) is None
    teacher_device=rooms.remember_device(professor)
    professor_id=rooms.identity(professor)['id']
    rooms.set_professor_access(owner,professor_id,False)
    assert rooms.identity(professor) is None and rooms.restore_device(teacher_device) is None
    with pytest.raises(ValueError):rooms.login_professor('professor','password-professor',key)
    with pytest.raises(ValueError):rooms.login_student(rooms.students(owner)[1]['access_key'])
    rooms.set_professor_access(owner,professor_id,True)
    assert rooms.identity(rooms.login_professor('professor','password-professor',key))
    assert rooms.restore_device(teacher_device) is None
    admin_device=rooms.remember_device(owner)
    rooms.revoke_remembered_access(owner)
    assert rooms.restore_device(admin_device) is None


def test_public_signup_accounts_are_quarantined_on_migration(tmp_path,monkeypatch):
    path=tmp_path/'old.sqlite3'
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(path))
    salt='00'*16
    encoded=rooms.pbkdf2_hmac('sha256',b'old-password',bytes.fromhex(salt),260000).hex()
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE professors(id TEXT PRIMARY KEY,name TEXT UNIQUE,salt TEXT,password TEXT)')
        db.execute('INSERT INTO professors VALUES(?,?,?,?)',('old','antigo',salt,encoded))
        db.execute('CREATE TABLE sessions(token TEXT PRIMARY KEY,role TEXT,owner TEXT,expires REAL,last_tick REAL)')
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(rooms._digest('old-session'),'professor','old',time.time()+3600,None))
    assert rooms.identity('old-session') is None
    with pytest.raises(ValueError):rooms.login_professor('antigo','old-password')
    owner=rooms.bootstrap_owner('criador','password-criador-123')
    assert rooms.admin_overview(owner)['professors'][0]['approved']==0
    rooms.set_professor_access(owner,'old',True)
    key=rooms.issue_professor_key(owner,'Professor antigo','old')
    assert rooms.identity(rooms.login_professor('antigo','old-password',key))['role']=='professor'
    assert rooms.identity('old-session') is None


def test_same_creator_key_cannot_activate_two_accounts_concurrently(owner):
    key=rooms.issue_professor_key(owner,'Uma única pessoa')
    def activate(name):
        try:return rooms.register_professor(name,'password-professor',key)
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        tokens=list(executor.map(activate,['professor-a','professor-b']))
    assert sum(token is not None for token in tokens)==1
    assert len(rooms.admin_overview(owner)['professors'])==1


def test_professor_key_is_mandatory_for_every_login_and_can_be_replaced(owner):
    key=rooms.issue_professor_key(owner,'Professor')
    with pytest.raises(ValueError):rooms.enter_professor('professor','password-professor','')
    assert not rooms.admin_overview(owner)['professors']
    first=rooms.enter_professor('professor','password-professor',key)
    professor=rooms.identity(first)
    pupil=rooms.students(first)[0]
    with pytest.raises(ValueError):rooms.login_professor('professor','password-professor')
    with pytest.raises(ValueError):rooms.login_professor('professor','password-professor','wrong-key')
    second=rooms.login_professor('professor','password-professor',key)
    assert rooms.identity(second)['id']==professor['id']
    device=rooms.remember_device(second)
    invitation=next(row for row in rooms.admin_overview(owner)['invitations'] if row['used_by']==professor['id'])
    rooms.revoke_professor_key(owner,invitation['id'])
    assert rooms.identity(first) is None and rooms.identity(second) is None
    assert rooms.restore_device(device) is None
    with pytest.raises(ValueError):rooms.login_professor('professor','password-professor',key)
    with pytest.raises(ValueError):rooms.login_student(pupil['access_key'])
    replacement=rooms.issue_professor_key(owner,'Professor',professor['id'])
    renewed=rooms.enter_professor('professor','password-professor',replacement)
    assert rooms.identity(renewed)['id']==professor['id']
    assert rooms.identity(rooms.login_student(pupil['access_key']))
    with pytest.raises(ValueError):rooms.login_professor('professor','password-professor',key)


def test_creator_can_issue_keys_without_labels_at_any_time(owner):
    keys=[rooms.issue_professor_key(owner) for _ in range(3)]
    assert len(set(keys))==3
    overview=rooms.admin_overview(owner)
    assert {row['label'] for row in overview['invitations']}=={'Chave 001','Chave 002','Chave 003'}
    professor=rooms.enter_professor('invited','professor-password-123',keys[0])
    assert rooms.identity(professor)['role']=='professor'
    with pytest.raises(PermissionError):rooms.issue_professor_key(professor)
    with pytest.raises(PermissionError):rooms.issue_professor_key('invalid')
    assert rooms.issue_professor_key(owner) not in keys


def test_creator_can_delete_unused_and_bound_keys(owner):
    unused=rooms.issue_professor_key(owner)
    identifier=rooms.admin_overview(owner)['invitations'][0]['id']
    rooms.delete_professor_key(owner,identifier)
    assert not rooms.admin_overview(owner)['invitations']
    with pytest.raises(ValueError):rooms.register_professor('expired','professor-password-123',unused)
    key=rooms.issue_professor_key(owner)
    professor=rooms.register_professor('bound','professor-password-123',key)
    device=rooms.remember_device(professor)
    identifier=rooms.admin_overview(owner)['invitations'][0]['id']
    with pytest.raises(PermissionError):rooms.delete_professor_key(professor,identifier)
    rooms.delete_professor_key(owner,identifier)
    assert rooms.identity(professor) is None and rooms.restore_device(device) is None
    assert not rooms.admin_overview(owner)['invitations']
    with rooms.database() as db:
        assert db.execute('SELECT COUNT(*) FROM professor_invites WHERE deleted=1 AND revoked=1').fetchone()[0]==2


def test_unused_key_expires_at_fifteen_minutes_and_record_survives(owner,monkeypatch):
    moment=rooms.time.time()
    monkeypatch.setattr(rooms.time,'time',lambda:moment)
    key=rooms.issue_professor_key(owner)
    row=rooms.admin_overview(owner)['invitations'][0]
    assert row['expires_at']==moment+900 and not row['expired']
    monkeypatch.setattr(rooms.time,'time',lambda:moment+900)
    assert rooms.admin_overview(owner)['invitations'][0]['expired']
    with pytest.raises(ValueError):rooms.enter_professor('late','professor-password-123',key)
    with rooms.database() as db:assert db.execute('SELECT COUNT(*) FROM professors').fetchone()[0]==0
    rooms.delete_professor_key(owner,row['id'])
    assert not rooms.admin_overview(owner)['invitations']


def test_key_used_before_expiry_keeps_professor_and_room_access(owner,monkeypatch):
    moment=rooms.time.time()
    monkeypatch.setattr(rooms.time,'time',lambda:moment)
    key=rooms.issue_professor_key(owner)
    monkeypatch.setattr(rooms.time,'time',lambda:moment+899)
    professor=rooms.enter_professor('ontime','professor-password-123',key)
    device=rooms.remember_device(professor)
    monkeypatch.setattr(rooms.time,'time',lambda:moment+901)
    assert not rooms.admin_overview(owner)['invitations'][0]['expired']
    assert rooms.identity(professor) and rooms.restore_device(device)
    assert rooms.login_professor('ontime','professor-password-123',key)
    assert rooms.login_student(rooms.students(professor)[0]['access_key'])
