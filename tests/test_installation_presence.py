from uuid import uuid4
import secrets
import time

import pytest
from fastapi.testclient import TestClient
import classroom as rooms
import installation_presence as presence
import desktop_presence
from mobile_api import create_app


@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'central.sqlite3'))
    owner=rooms.bootstrap_owner('superadmin','testpass')
    user=rooms.register_user('amigo','test-password-user')
    return owner,user


def test_only_owner_sees_inventory_and_blocks_require_explicit_action(accounts):
    owner,user=accounts;device=str(uuid4());secret=secrets.token_urlsafe(40)
    assert presence.heartbeat(device,secret,'amigo','windows','0.2.2')['allowed']
    rows=presence.inventory(owner)
    assert rows[0]['online'] and not rows[0]['blocked']
    assert not {'credential','secret','password'} & rows[0].keys()
    with pytest.raises(PermissionError):presence.inventory(user)
    with pytest.raises(PermissionError):presence.set_access(user,device,False)
    with pytest.raises(PermissionError):presence.heartbeat(device,secrets.token_urlsafe(40),'impostor','windows','0.2.2')
    presence.set_access(owner,device,False)
    assert not presence.heartbeat(device,secret,'amigo','windows','0.2.2')['allowed']
    presence.set_access(owner,device,True)
    assert presence.heartbeat(device,secret,'amigo','windows','0.2.2')['allowed']
    with rooms.database() as db:db.execute('UPDATE app_installations SET last_seen=?',(time.time()-95,))
    assert not presence.inventory(owner)[0]['online']


def test_http_inventory_is_private_and_installation_cannot_promote_itself(accounts):
    owner,user=accounts;client=TestClient(create_app());device=str(uuid4())
    body={'device':device,'name':'amigo','version':'0.2.2','platform':'windows'}
    credential='Installation '+secrets.token_urlsafe(40)
    assert client.post('/v1/installations/heartbeat',json=body,headers={'Authorization':credential}).status_code==200
    assert client.get('/v1/admin/installations').status_code==401
    assert client.get('/v1/admin/installations',headers={'Authorization':'Bearer '+user}).status_code==403
    assert client.get('/v1/admin/installations',headers={'Authorization':credential}).status_code==401
    headers={'Authorization':'Bearer '+owner}
    assert client.get('/v1/admin/installations',headers=headers).json()['installations'][0]['name']=='amigo'
    assert client.post(f'/v1/admin/installations/{device}/access',json={'allowed':False},headers=headers).status_code==200
    assert client.post('/v1/installations/heartbeat',json=body,headers={'Authorization':credential}).json()['allowed'] is False


def test_connection_failure_never_blocks_and_explicit_block_survives_reopen(tmp_path,monkeypatch):
    allowed={'value':True}
    def api(*args,**kwargs):
        if allowed['value']=='offline':raise OSError('offline')
        return {'allowed':allowed['value']}
    monkeypatch.setattr(desktop_presence,'api',api)
    path=tmp_path/'installation.json'
    client=desktop_presence.PresenceClient('https://example.com',path)
    def update():
        client.checked=0;client.poll('amigo','0.2.2');client.future.result(timeout=2)
        return client.poll('amigo','0.2.2')
    try:
        assert update()['blocked'] is False
        allowed['value']=False
        assert update()['blocked'] is True
        allowed['value']='offline';client.checked=0;client.poll('amigo','0.2.2')
        with pytest.raises(OSError):client.future.result(timeout=2)
        assert client.poll('amigo','0.2.2')['blocked'] is True
    finally:client.executor.shutdown(wait=True)
    restored=desktop_presence.PresenceClient('https://example.com',path)
    try:assert restored.saved['blocked'] is True
    finally:restored.executor.shutdown(wait=True)


@pytest.mark.parametrize('url',['http://example.com','file:///tmp/config','https://admin:secret@example.com','https://example.com?secret=1'])
def test_control_connection_requires_https_and_does_not_accept_credentials_in_url(url):
    with pytest.raises(ValueError):desktop_presence.valid_url(url)
