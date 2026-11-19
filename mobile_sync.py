"""Account-isolated, idempotent offline history and device checkpoints.

No mobile UI or installer is implied by this module. A device remains usable
offline; authorization is enforced by the service when that device reconnects.
"""
import json
import time
from uuid import UUID

import classroom as rooms


def _tables(db):
    # Execute statements separately: executescript would commit the transaction.
    db.execute('''CREATE TABLE IF NOT EXISTS mobile_devices(
        owner TEXT,device TEXT,platform TEXT,version TEXT,created REAL,last_sync REAL,
        sequence INTEGER NOT NULL DEFAULT 0,checkpoint TEXT,PRIMARY KEY(owner,device))''')
    db.execute('''CREATE TABLE IF NOT EXISTS mobile_history(
        owner TEXT,event TEXT,device TEXT,sequence INTEGER,payload TEXT,received REAL,
        PRIMARY KEY(owner,event),UNIQUE(owner,device,sequence))''')


def _uuid(value):
    try:
        return str(UUID(str(value)))
    except (ValueError,TypeError,AttributeError):
        raise ValueError('Identificador do dispositivo ou evento inválido.') from None


def sync(token,device,events,platform='unknown',version=''):
    """Commit consecutive events and their latest checkpoint in one transaction.

    Lost responses can be retried. Gaps and changed duplicates are rejected;
    one device's checkpoint can never overwrite another device's checkpoint.
    """
    device=_uuid(device)
    if not isinstance(events,list) or len(events)>100:
        raise ValueError('Envie no máximo 100 eventos por sincronização.')
    if platform not in ('android','ios','web','unknown') or not isinstance(version,str) or len(version)>50:
        raise ValueError('Plataforma ou versão inválida.')
    encoded=[]
    for event in events:
        if not isinstance(event,dict) or type(event.get('sequence')) is not int or event['sequence']<1:
            raise ValueError('Sequência de sincronização inválida.')
        payload=event.get('payload')
        if not isinstance(payload,dict) or not isinstance(payload.get('checkpoint'),dict):
            raise ValueError('Informe o ponto atual junto do evento.')
        body=json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))
        if len(body.encode())>1024*1024:
            raise ValueError('Evento excede o limite de 1 MB.')
        encoded.append((_uuid(event.get('id')),event['sequence'],body))
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        actor=rooms._identity(db,token)
        owner=actor['id']
        _tables(db)
        now=time.time()
        db.execute('INSERT OR IGNORE INTO mobile_devices(owner,device,platform,version,created) VALUES(?,?,?,?,?)',
                   (owner,device,platform,version,now))
        current=db.execute('SELECT sequence,checkpoint FROM mobile_devices WHERE owner=? AND device=?',(owner,device)).fetchone()
        sequence=current['sequence']
        checkpoint=current['checkpoint']
        for identifier,next_sequence,body in encoded:
            previous=db.execute('SELECT device,sequence,payload FROM mobile_history WHERE owner=? AND event=?',(owner,identifier)).fetchone()
            if previous:
                if (previous['device'],previous['sequence'],previous['payload'])!=(device,next_sequence,body):
                    raise ValueError('O evento já existe com dados diferentes. Os dados locais devem ser preservados.')
                continue
            if next_sequence!=sequence+1:
                raise ValueError('Faltam eventos anteriores. Reenvie a fila local na ordem original.')
            db.execute('INSERT INTO mobile_history VALUES(?,?,?,?,?,?)',(owner,identifier,device,next_sequence,body,now))
            sequence=next_sequence
            checkpoint=json.dumps(json.loads(body)['checkpoint'],ensure_ascii=False,allow_nan=False)
        db.execute('UPDATE mobile_devices SET platform=?,version=?,last_sync=?,sequence=?,checkpoint=? WHERE owner=? AND device=?',
                   (platform,version,now,sequence,checkpoint,owner,device))
        return {'acknowledged':sequence,'checkpoint':json.loads(checkpoint) if checkpoint else None,
                'received_at':now}


def devices_for_owner(token):
    with rooms.database() as db:
        rooms._identity(db,token,'admin')
        _tables(db)
        return [dict(row) for row in db.execute('''SELECT mobile_devices.owner,device,platform,version,
            mobile_devices.created,last_sync,sequence,COALESCE(users.name,professors.name,administrators.name,'Conta') AS name
            FROM mobile_devices LEFT JOIN users ON users.id=mobile_devices.owner
            LEFT JOIN professors ON professors.id=mobile_devices.owner
            LEFT JOIN administrators ON administrators.id=mobile_devices.owner ORDER BY last_sync DESC''')]


def checkpoints(token):
    """Read only this account's device heads; never select a winning device."""
    with rooms.database() as db:
        owner = rooms._identity(db, token)['id']
        _tables(db)
        return [dict(device=row['device'], sequence=row['sequence'],
                     checkpoint=json.loads(row['checkpoint']) if row['checkpoint'] else None)
                for row in db.execute('SELECT device,sequence,checkpoint FROM mobile_devices WHERE owner=? ORDER BY device',
                                      (owner,))]
