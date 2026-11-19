"""Local authenticated envelopes; no key persistence, transport or database migration."""
import base64
import binascii
import json
import os
import time
from hashlib import sha256

import classroom as rooms
from continuity_local import _index

MAX_PLAINTEXT = 512 * 1024
SCHEME = 'coach-continuity-aes256gcm-recovery-v2'


def new_key():
    """Return a random key in memory; caller must use a secure platform key vault."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM.generate_key(bit_length=256)


def _context(token, key):
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError('Forneça uma chave aleatória de 256 bits; não use uma senha.')
    with rooms.database() as db:
        owner = rooms._identity(db, token)['id']
    return owner, (SCHEME + '|' + owner).encode()


def _padding():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=SCHEME.encode())


def _key_id(public_key):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 3072:
        raise ValueError('Configure a chave pública RSA de recuperação do Superadmin (mínimo 3072 bits).')
    return sha256(public_key.public_bytes(serialization.Encoding.DER,
                  serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()


def _aad(owner, recovery):
    return json.dumps([SCHEME, owner, recovery], sort_keys=True, separators=(',', ':')).encode()


def seal(token, snapshot, key, *, recovery_public_key=None):
    """Produce an encrypted artifact in memory, bound to the authenticated account."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    owner, _ = _context(token, key)
    key_id = _key_id(recovery_public_key)  # Fail closed: no new package without recovery.
    _index(snapshot, owner)
    body = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(',', ':')).encode()
    if len(body) > MAX_PLAINTEXT:
        raise ValueError('Rascunho excede 512 KB; nenhuma informação foi descartada.')
    nonce = os.urandom(12)
    recovery = dict(key_id=key_id, wrapped_key=base64.b64encode(
        recovery_public_key.encrypt(key, _padding())).decode())
    ciphertext = AESGCM(key).encrypt(nonce, body, _aad(owner, recovery))
    return dict(scheme=SCHEME, account=owner, recovery=recovery, nonce=base64.b64encode(nonce).decode(),
                ciphertext=base64.b64encode(ciphertext).decode())


def unseal(token, envelope, key):
    """Verify before exposing a draft. This never restores or overwrites progress."""
    owner, _ = _context(token, key)
    return _decrypt(owner, envelope, key)


def _decrypt(owner, envelope, key):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        if (not isinstance(envelope, dict) or envelope.get('scheme') != SCHEME
                or envelope.get('account') != owner):
            raise ValueError()
        encoded = envelope['ciphertext']
        nonce_text = envelope['nonce']
        if (not isinstance(encoded, str) or len(encoded) > (MAX_PLAINTEXT+16)*4//3+4
                or not isinstance(nonce_text, str) or len(nonce_text) != 16):
            raise ValueError()
        nonce = base64.b64decode(nonce_text, validate=True)
        ciphertext = base64.b64decode(encoded, validate=True)
        body = AESGCM(key).decrypt(nonce, ciphertext, _aad(owner, envelope['recovery']))
        snapshot = json.loads(body)
        _index(snapshot, owner)
        return snapshot
    except (ValueError, TypeError, KeyError, binascii.Error, InvalidTag, PermissionError):
        raise ValueError('Pacote inválido, alterado ou incompatível com esta conta/chave.') from None


def recover(admin_token, envelope, recovery_private_key):
    """Superadmin-only, audited local recovery; never restore over live progress."""
    with rooms.database() as db:
        actor = rooms._identity(db, admin_token, 'admin')
        db.execute('''CREATE TABLE IF NOT EXISTS continuity_recoveries(
            id INTEGER PRIMARY KEY, actor TEXT NOT NULL, owner TEXT NOT NULL,
            key_id TEXT NOT NULL, created REAL NOT NULL, success INTEGER NOT NULL)''')
        owner, key_id, result, error = '', '', None, None
        try:
            key_id = _key_id(recovery_private_key.public_key())
            if not isinstance(envelope, dict) or envelope.get('scheme') != SCHEME:
                raise ValueError()
            owner = envelope['account']
            if not isinstance(owner, str) or len(owner) > 128:
                raise ValueError()
            recovery = envelope['recovery']
            if recovery['key_id'] != key_id or len(recovery['wrapped_key']) > 2048:
                raise ValueError()
            key = recovery_private_key.decrypt(base64.b64decode(recovery['wrapped_key'], validate=True), _padding())
            result = _decrypt(owner, envelope, key)
        except (ValueError, TypeError, KeyError, AttributeError, binascii.Error):
            error = ValueError('Recuperação recusada: chave ou pacote inválido.')
        db.execute('INSERT INTO continuity_recoveries(actor,owner,key_id,created,success) VALUES(?,?,?,?,?)',
                   (actor['id'], owner if isinstance(owner, str) else '', key_id, time.time(), int(error is None)))
    # Commit even failed authorized attempts before returning; never log plaintext or keys.
    if error:
        raise error
    return result
