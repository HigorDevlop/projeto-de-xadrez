"""Central, creator-only inventory of authenticated application installations."""
import hmac
import time
from uuid import UUID

import classroom as rooms

ONLINE_SECONDS = 90


def tables(db):
    db.execute('''CREATE TABLE IF NOT EXISTS app_installations(
        device TEXT PRIMARY KEY, credential TEXT NOT NULL, name TEXT NOT NULL,
        platform TEXT NOT NULL, version TEXT NOT NULL, created REAL NOT NULL,
        last_seen REAL NOT NULL, blocked INTEGER NOT NULL DEFAULT 0)''')


def heartbeat(device, secret, name, platform, version):
    device = str(UUID(device))
    if not 32 <= len(secret) <= 128 or not 1 <= len(name) <= 50:
        raise ValueError('Identificação inválida.')
    if platform not in {'windows','android','ios','web','unknown'} or len(version)>50:
        raise ValueError('Versão ou plataforma inválida.')
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE');tables(db)
        row=db.execute('SELECT credential,blocked FROM app_installations WHERE device=?',(device,)).fetchone()
        if row and not hmac.compare_digest(row['credential'],rooms._digest(secret)):
            raise PermissionError('Credencial do dispositivo inválida.')
        now=time.time()
        if not row:
            db.execute('INSERT INTO app_installations VALUES(?,?,?,?,?,?,?,0)',
                       (device,rooms._digest(secret),name,platform,version,now,now))
        else:
            db.execute('UPDATE app_installations SET name=?,platform=?,version=?,last_seen=? WHERE device=?',
                       (name,platform,version,now,device))
        return {'allowed':not bool(row and row['blocked']), 'received_at':now}


def inventory(token):
    with rooms.database() as db:
        rooms._identity(db,token,'admin');tables(db)
        now=time.time()
        return [dict(row,online=0<=now-row['last_seen']<=ONLINE_SECONDS)
                for row in db.execute('SELECT device,name,platform,version,created,last_seen,blocked FROM app_installations ORDER BY last_seen DESC')]


def set_access(token, device, allowed):
    with rooms.database() as db:
        rooms._identity(db,token,'admin');tables(db)
        result=db.execute('UPDATE app_installations SET blocked=? WHERE device=?',(int(not allowed),str(UUID(device))))
        if not result.rowcount:raise ValueError('Dispositivo não encontrado.')
