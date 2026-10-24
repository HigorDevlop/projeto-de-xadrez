import pytest
from concurrent.futures import ThreadPoolExecutor
import classroom as rooms


@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'rooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    teacher=rooms.register_professor('teacher','teacher-password-123',rooms.issue_professor_key(owner,'teacher'))
    return owner,teacher,rooms.students(teacher)[0]


def test_personal_account_membership_and_ban_are_separate(accounts):
    owner,teacher,seat=accounts
    user=rooms.register_user('ordinary','ordinary-password-123')
    assert rooms.identity(user)['role']=='user'
    assert rooms.membership(user) is None
    assert rooms.identity(rooms.login_user('CREATOR','creator-password-123'))['role']=='admin'
    with pytest.raises(ValueError):rooms.register_user('creator','ordinary-password-123')
    with pytest.raises(ValueError):rooms.register_user('SuperAdmin','ordinary-password-123')
    with pytest.raises(ValueError):rooms.login_user('ordinary','wrong')
    with pytest.raises(PermissionError):rooms.issue_professor_key(user,'attacker')
    with pytest.raises(PermissionError):rooms.join_room(teacher,seat['access_key'])
    legacy=rooms.login_student(seat['access_key'])
    room=rooms.join_room(user,seat['access_key'])
    assert rooms.identity(room)['id']==seat['id']
    assert rooms.identity(legacy) is None
    assert rooms.membership(user)['professor']=='teacher'
    assert rooms.identity(user)['role']=='user'
    with pytest.raises(ValueError):rooms.login_student(seat['access_key'])
    other=rooms.register_user('other','other-password-123')
    with pytest.raises(ValueError):rooms.join_room(other,seat['access_key'])
    with pytest.raises(PermissionError):rooms.record(user,'event','tactics',True,True)
    renewed=rooms.room_session(rooms.login_user('ordinary','ordinary-password-123'))
    assert rooms.identity(renewed)['id']==seat['id']
    device=rooms.remember_device(user)
    for number in range(3):rooms.warn(teacher,seat['id'],f'Falta {number}')
    assert rooms.identity(room) is None and rooms.identity(renewed) is None
    with pytest.raises(PermissionError):rooms.room_session(user)
    assert rooms.identity(user)['role']=='user'
    assert rooms.identity(rooms.restore_device(device))['role']=='user'
    assert {row['name'] for row in rooms.admin_overview(owner)['users']}=={'ordinary','other'}


def test_only_one_account_can_claim_each_code(accounts):
    _,_,seat=accounts
    users=[rooms.register_user(name,'ordinary-password-123') for name in ('first','second')]
    def claim(token):
        try:return rooms.join_room(token,seat['access_key'])
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,users))
    assert sum(bool(result) for result in results)==1
