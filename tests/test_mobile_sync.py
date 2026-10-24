from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
import classroom as rooms
import mobile_sync


@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'mobile.sqlite3'))
    admin=rooms.bootstrap_owner('criador','password-criador-123')
    user=rooms.register_user('amigo','password-amigo-123')
    return admin,user,rooms.identity(user)['id']


def event(sequence,pgn='1. e4 *'):
    return dict(id=str(uuid4()),sequence=sequence,payload={'checkpoint':{'pgn':pgn,'ply':sequence},'activity':{'kind':'move'}})


def test_sync_keeps_history_once_and_current_checkpoint(accounts):
    admin,user,_=accounts;device=str(uuid4());batch=[event(1),event(2,'1. e4 e5 *')]
    result=mobile_sync.sync(user,device,batch,'android','0.1.0')
    assert result['acknowledged']==2 and result['checkpoint']['ply']==2
    assert mobile_sync.sync(user,device,batch,'android','0.1.0')['acknowledged']==2
    with rooms.database() as db:
        assert db.execute('SELECT COUNT(*) FROM mobile_history').fetchone()[0]==2
    rows=mobile_sync.devices_for_owner(admin)
    assert rows[0]['name']=='amigo' and rows[0]['sequence']==2


def test_gap_or_changed_duplicate_is_rejected_without_losing_current_state(accounts):
    _,user,_=accounts;device=str(uuid4());first=event(1)
    mobile_sync.sync(user,device,[first])
    with pytest.raises(ValueError):mobile_sync.sync(user,device,[event(3)])
    with pytest.raises(ValueError):mobile_sync.sync(user,device,[first|{'payload':{'checkpoint':{'ply':999}}}])
    assert mobile_sync.sync(user,device,[])['checkpoint']['ply']==1


def test_devices_and_accounts_do_not_overwrite_each_other(accounts):
    admin,user,_=accounts;device=str(uuid4());other_device=str(uuid4())
    other=rooms.register_user('outro','password-outro-123')
    mobile_sync.sync(user,device,[event(1,'user')])
    mobile_sync.sync(other,device,[event(1,'other')])
    mobile_sync.sync(user,other_device,[event(1,'second-device')])
    assert mobile_sync.sync(user,device,[])['checkpoint']['pgn']=='user'
    assert mobile_sync.sync(other,device,[])['checkpoint']['pgn']=='other'
    assert len(mobile_sync.devices_for_owner(admin))==3
    with pytest.raises(PermissionError):mobile_sync.devices_for_owner(user)


def test_creator_can_approve_and_block_reconnections_without_deleting_history(accounts):
    admin,user,identifier=accounts;device=str(uuid4())
    mobile_sync.sync(user,device,[event(1)])
    refresh=rooms.remember_device(user)
    rooms.set_user_access(admin,identifier,False)
    assert rooms.identity(user) is None and rooms.restore_device(refresh) is None
    with pytest.raises(PermissionError):mobile_sync.sync(user,device,[])
    with pytest.raises(PermissionError):rooms.login_user('amigo','password-amigo-123')
    rooms.set_user_access(admin,identifier,True)
    resumed=rooms.login_user('amigo','password-amigo-123')
    assert mobile_sync.sync(resumed,device,[])['checkpoint']['ply']==1
    rows=rooms.admin_overview(admin)['users']
    assert rows[0]['last_login'] and rows[0]['last_seen'] and rows[0]['created']


def test_registration_is_free_unless_creator_blocks_it(accounts,monkeypatch):
    admin,_,_=accounts
    monkeypatch.setenv('COACH_REQUIRE_USER_APPROVAL','1')
    token=rooms.register_user('livre','password-livre',require_approval=True)
    row=next(row for row in rooms.admin_overview(admin)['users'] if row['name']=='livre')
    assert row['status']=='active' and rooms.identity(token)
    rooms.set_user_access(admin,row['id'],False)
    assert rooms.identity(token) is None
    with pytest.raises(PermissionError):rooms.login_user('livre','password-livre')


def test_concurrent_retry_deduplicates_and_invalid_batch_is_atomic(accounts):
    _,user,_=accounts;device=str(uuid4());first=event(1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:mobile_sync.sync(user,device,[first]),range(2)))
    assert all(row['acknowledged']==1 for row in results)
    with pytest.raises(ValueError):mobile_sync.sync(user,device,[event(2),event(4)])
    assert mobile_sync.sync(user,device,[])['acknowledged']==1


def test_http_registration_is_free_and_sync_is_authenticated(accounts):
    from fastapi.testclient import TestClient
    from mobile_api import create_app
    admin,_,_=accounts;client=TestClient(create_app())
    response=client.post('/v1/register',json={'name':'mobile','password':'password-mobile'})
    assert response.status_code==201
    assert response.json()['token']
    row=next(row for row in rooms.admin_overview(admin)['users'] if row['name']=='mobile')
    response=client.post('/v1/login',json={'name':'mobile','password':'password-mobile'})
    assert response.status_code==200
    headers={'Authorization':'Bearer '+response.json()['token']}
    batch={'device':str(uuid4()),'events':[event(1)],'platform':'ios','version':'0.1.0'}
    assert client.post('/v1/sync',json=batch).status_code==401
    assert client.post('/v1/sync',headers=headers,json=batch).json()['acknowledged']==1
    rooms.set_user_access(admin,row['id'],False)
    assert client.post('/v1/sync',headers=headers,json=batch).status_code==401
