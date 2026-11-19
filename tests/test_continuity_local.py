from copy import deepcopy
from uuid import uuid4
import pytest
import classroom as rooms
import continuity_local as continuity
import mobile_sync
from preparation_state import save_plan


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    import socket
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'accounts.sqlite3'))
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path/'plans'))
    def offline(*args, **kwargs):
        raise AssertionError('No network in local continuity')
    monkeypatch.setattr(socket, 'create_connection', offline)
    rooms.bootstrap_owner('owner', 'password-owner-123')
    return [rooms.register_user(name, 'password-user-123') for name in ('alice', 'bob')]


def test_capture_existing_stores_without_credentials_or_cross_account_data(accounts):
    import analysis_training
    token, other = accounts
    owner = rooms.identity(token)['id']
    # Exercise storage is the existing adapter, not a new continuity database.
    analysis_training._save_exercise(token, 'one', dict(fen='local', uci='e2e4'))
    analysis_training._save_exercise(other, 'private', dict(fen='secret'))
    save_plan(dict(version=1, username='user:'+owner, practice_progress={'lesson':{'learned':True}},
                   material={'private_book':'do not export'}, password='do not export'), namespace='openings')
    before = analysis_training.listing(token)
    draft = continuity.capture(token)
    assert {r['kind'] for r in draft['records']} == {'review', 'progress'}
    assert 'private' not in str(draft) and 'password' not in str(draft) and token not in str(draft)
    assert continuity.capture(token) == draft
    assert analysis_training.listing(token) == before
    assert all(r['id'] != 'one' for r in continuity.capture(other)['records'])
    rooms.logout(token)
    with pytest.raises(PermissionError): continuity.capture(token)


def test_three_way_conflicts_are_reported_without_mutation(accounts):
    token, other = accounts
    base = dict(version=1, account=rooms.identity(token)['id'], records=[
        dict(kind='progress', id='course', value={'revision':1}),
        dict(kind='game', id='game', value={'pgn':'1. e4 *'})])
    left, right = deepcopy(base), deepcopy(base)
    left['records'][0]['value']['revision'] = 2
    right['records'][0]['value']['revision'] = 3
    right['records'].append(dict(kind='attempt', id='new', value={'uci':'d2d4'}))
    original = deepcopy((left, right, base))
    rows = continuity.compare(token, left, right, base)
    assert {r['id']:r['status'] for r in rows} == {'course':'conflict', 'game':'identical','new':'incoming_only'}
    assert (left, right, base) == original
    assert continuity.compare(token, base, left, base)[1]['status'] == 'incoming_changed'
    assert continuity.compare(token, left, base, base)[1]['status'] == 'local_changed'
    with pytest.raises(PermissionError): continuity.compare(other, left, right)
    right['records'].append(right['records'][0])
    with pytest.raises(ValueError): continuity.compare(token, left, right)


def test_capture_archived_game_attempt_and_review_without_rescheduling(accounts):
    import analysis_archive
    import analysis_training
    from chess_review import MoveReview
    token, other = accounts
    pgn = '[White "alice"]\n[Black "opponent"]\n\n1. e4 *'
    review = MoveReview(1, '1', 'Brancas', 'e4', 'e2e4', 'mistake', 100, 20, None,
                        'd4', '', [], 'Explicação já salva.')
    game = analysis_archive.save(token, pgn, dict(reviews={1:review}, explanations={}, references={}))
    exercise = analysis_training.create(token, game, 1)
    analysis_training.submit(token, exercise, 'd2d4', 0)
    before = analysis_training.listing(token)
    captured = continuity.capture(token)
    assert {r['kind'] for r in captured['records']} == {'game','review','attempt'}
    by_kind = {r['kind']: r['value'] for r in captured['records']}
    assert by_kind['game']['pgn'] == pgn
    assert by_kind['attempt']['uci'] == 'd2d4'
    assert by_kind['review']['revision'] == 1
    assert by_kind['review']['due'] == before[0]['due']
    assert analysis_training.listing(token) == before
    assert continuity.capture(other)['records'] == []


def test_own_device_heads_retry_isolation_and_revocation(accounts):
    token, other = accounts
    devices = [str(uuid4()), str(uuid4())]
    for device in devices:
        event = dict(id=str(uuid4()), sequence=1, payload={'checkpoint':{'progress':device}})
        mobile_sync.sync(token, device, [event])
        mobile_sync.sync(token, device, [event])
    mobile_sync.sync(other, devices[0], [dict(id=str(uuid4()), sequence=1, payload={'checkpoint':{'private':True}})])
    rows = mobile_sync.checkpoints(token)
    assert len(rows) == 2 and all(r['sequence']==1 for r in rows)
    assert all('private' not in r['checkpoint'] for r in rows)
    assert mobile_sync.checkpoints(other)[0]['checkpoint'] == {'private':True}
    rooms.logout(token)
    with pytest.raises(PermissionError): mobile_sync.checkpoints(token)


def test_checkpoint_endpoint_authentication_and_no_cache(accounts):
    from fastapi.testclient import TestClient
    from mobile_api import create_app
    token, other = accounts
    device = str(uuid4())
    mobile_sync.sync(token, device, [dict(id=str(uuid4()), sequence=1, payload={'checkpoint':{'ply':2}})])
    client = TestClient(create_app())
    assert client.get('/v1/sync/checkpoints').status_code == 401
    response = client.get('/v1/sync/checkpoints', headers={'Authorization':'Bearer '+token})
    assert response.json()['devices'][0]['checkpoint'] == {'ply':2}
    assert response.headers['Cache-Control'] == 'no-store'
    assert client.get('/v1/sync/checkpoints', headers={'Authorization':'Bearer '+other}).json() == {'devices':[]}


def test_last_action_policy_and_unreliable_clocks():
    a = dict(device=str(uuid4()), sequence=1, authored_at=100)
    b = dict(device=str(uuid4()), sequence=1, authored_at=150)
    def assess(left, right):
        return continuity.last_command(left, right, observed_at=200, max_future_skew=10)
    assert assess(a, b)['winner'] == 'incoming'
    assert assess(b, a)['winner'] == 'local'  # Later upload is irrelevant.
    assert assess(a, dict(b, authored_at=300))['reason'] == 'future_clock'
    assert assess(a, dict(b, authored_at=100))['reason'] == 'tied_clock'
    assert assess(a, dict(a, sequence=2, authored_at=90))['reason'] == 'sequence_clock_mismatch'
    assert assess(a, None)['winner'] is None
    assert assess(a, dict(b, authored_at=float('nan')))['winner'] is None


@pytest.fixture
def recovery_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


def test_encrypted_drafts_account_binding_integrity_and_no_stored_key(accounts, recovery_key):
    import continuity_crypto as crypto
    token, other = accounts
    snapshot = continuity.capture(token)
    snapshot['records'].append(dict(kind='game', id='test', value={'pgn':'1. e4 e5 *'}))
    key = crypto.new_key()
    envelope = crypto.seal(token, snapshot, key, recovery_public_key=recovery_key.public_key())
    assert crypto.unseal(token, envelope, key) == snapshot
    assert set(envelope) == {'scheme', 'account', 'recovery', 'nonce', 'ciphertext'}
    assert '1. e4 e5 *' not in str(envelope)
    assert crypto.seal(token, snapshot, key, recovery_public_key=recovery_key.public_key()) != envelope
    with pytest.raises(ValueError): crypto.unseal(other, envelope, key)
    with pytest.raises(ValueError): crypto.unseal(token, envelope, crypto.new_key())
    tampered = dict(envelope, ciphertext='AAAA'+envelope['ciphertext'][4:])
    with pytest.raises(ValueError): crypto.unseal(token, tampered, key)
    with pytest.raises(ValueError): crypto.seal(token, snapshot, b'password')
    snapshot['records'][0]['value']['large'] = 'x' * crypto.MAX_PLAINTEXT
    with pytest.raises(ValueError): crypto.seal(token, snapshot, key, recovery_public_key=recovery_key.public_key())


def test_superadmin_recovery_without_user_key_and_audit(accounts, recovery_key):
    import continuity_crypto as crypto
    token, other = accounts
    admin = rooms.login_owner('owner', 'password-owner-123')
    snapshot = continuity.capture(token)
    key = crypto.new_key()
    with pytest.raises(ValueError): crypto.seal(token, snapshot, key)
    envelope = crypto.seal(token, snapshot, key, recovery_public_key=recovery_key.public_key())
    del key
    assert crypto.recover(admin, envelope, recovery_key) == snapshot
    for unauthorized in (token, other, 'expired'):
        with pytest.raises(PermissionError): crypto.recover(unauthorized, envelope, recovery_key)
    corrupt = deepcopy(envelope)
    corrupt['recovery']['wrapped_key'] = 'AAAA' + corrupt['recovery']['wrapped_key'][4:]
    with pytest.raises(ValueError): crypto.recover(admin, corrupt, recovery_key)
    from cryptography.hazmat.primitives.asymmetric import rsa
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    with pytest.raises(ValueError): crypto.recover(admin, envelope, wrong_key)
    with rooms.database() as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM continuity_recoveries')]
    assert [row['success'] for row in rows] == [1, 0, 0]
    assert all(row['actor'] == rooms.identity(admin)['id'] for row in rows)
    assert all(row['owner'] == rooms.identity(token)['id'] for row in rows)
    assert 'ciphertext' not in str(rows) and 'wrapped_key' not in str(rows)
