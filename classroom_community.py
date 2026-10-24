"""Private classroom conversations, lessons and WebRTC signaling."""
import json
import secrets
import time
from urllib.parse import urlparse
import classroom as rooms


def context(db,token,room=None,allow_user=False):
    actor=rooms._identity(db,token)
    if actor['role']=='user' and allow_user:
        membership=db.execute('SELECT student FROM memberships WHERE owner=?',(actor['id'],)).fetchone()
        if not membership:raise PermissionError('Junte-se a uma sala para assistir aos vídeos.')
        identifier=rooms._account(db,'student',membership['student'])['room']
    elif actor['role']=='student':identifier=actor['room']
    elif actor['role']=='professor':identifier=actor['id']
    elif actor['role']=='admin' and room:
        if room!=actor['id']:rooms._account(db,'professor',room)
        identifier=room
    else:raise PermissionError('Entre na sala do Professor.')
    if room and room!=identifier:raise PermissionError('Esta sala não pertence à sua conta.')
    return actor,identifier


def _channel(db,actor,room,channel):
    if channel=='group':return channel
    row=db.execute('SELECT id FROM students WHERE room=? AND id=? AND banned=0',(room,channel)).fetchone()
    if not row or actor['role']=='student' and actor['id']!=channel:raise PermissionError('Conversa privada de outro aluno.')
    return channel


def messages(token,channel='group',room=None):
    with rooms.database() as db:
        actor,room=context(db,token,room);_channel(db,actor,room,channel)
        rows=db.execute('SELECT id,sender,name,body,created FROM room_messages WHERE room=? AND channel=? ORDER BY id DESC LIMIT 100',(room,channel)).fetchall()
        return [dict(row,mine=row['sender']==actor['id']) for row in reversed(rows)]


def send(token,text,channel='group',room=None,nonce=None):
    text=text.strip()
    if not 1<=len(text)<=4000:raise ValueError('Escreva uma mensagem de até 4.000 caracteres.')
    with rooms.database() as db:
        actor,room=context(db,token,room);_channel(db,actor,room,channel)
        db.execute('INSERT OR IGNORE INTO room_messages(room,channel,sender,name,body,created,nonce) VALUES(?,?,?,?,?,?,?)',
            (room,channel,actor['id'],actor['name'],text,time.time(),nonce or secrets.token_hex(16)))


def videos(token,room=None):
    with rooms.database() as db:
        _,room=context(db,token,room,allow_user=True)
        return [dict(row) for row in db.execute('SELECT id,title,url,mime,created FROM room_videos WHERE room=? ORDER BY created DESC',(room,))]


def publish_video(token,title,url='',media=None,mime='',room=None):
    if not title.strip():raise ValueError('Dê um título à aula.')
    if media:
        if len(media)>100*1024*1024 or mime not in ('video/mp4','video/webm','video/quicktime'):raise ValueError('Envie MP4, WebM ou MOV de até 100 MB.')
        url=''
    elif urlparse(url).scheme!='https' or not urlparse(url).hostname:raise ValueError('Informe um link HTTPS ou envie um vídeo.')
    with rooms.database() as db:
        actor,room=context(db,token,room)
        if actor['role']=='student':raise PermissionError('Somente o Professor publica aulas.')
        db.execute('INSERT INTO room_videos VALUES(?,?,?,?,?,?,?)',(secrets.token_hex(16),room,title.strip()[:150],url,media,mime,time.time()))


def video_media(token,identifier,room=None):
    with rooms.database() as db:
        _,room=context(db,token,room,allow_user=True)
        row=db.execute('SELECT media FROM room_videos WHERE id=? AND room=?',(identifier,room)).fetchone()
        if not row:raise PermissionError('Vídeo indisponível.')
        return bytes(row['media']) if row['media'] else None


def recorded_room(token):
    with rooms.database() as db:
        _,room=context(db,token,allow_user=True)
        return room


def delete_video(token,identifier,room=None):
    with rooms.database() as db:
        actor,room=context(db,token,room)
        if actor['role']=='student':raise PermissionError('Somente o Professor remove aulas.')
        db.execute('DELETE FROM room_videos WHERE id=? AND room=?',(identifier,room))


def live(token,room=None):
    with rooms.database() as db:
        _,room=context(db,token,room)
        row=db.execute('SELECT id,title,created FROM live_classes WHERE room=? AND ended IS NULL ORDER BY created DESC LIMIT 1',(room,)).fetchone()
        return dict(row) if row else None


def start_live(token,title='Aula ao vivo',room=None):
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        actor,room=context(db,token,room)
        if actor['role']=='student':raise PermissionError('Somente o Professor inicia aulas.')
        current=db.execute('SELECT id FROM live_classes WHERE room=? AND ended IS NULL',(room,)).fetchone()
        if current:return current['id']
        identifier=secrets.token_hex(24)
        db.execute('INSERT INTO live_classes VALUES(?,?,?,?,NULL)',(identifier,room,title.strip()[:150] or 'Aula ao vivo',time.time()))
        return identifier


def end_live(token,room=None):
    with rooms.database() as db:
        actor,room=context(db,token,room)
        if actor['role']=='student':raise PermissionError('Somente o Professor encerra aulas.')
        db.execute('UPDATE live_classes SET ended=? WHERE room=? AND ended IS NULL',(time.time(),room))


def join_live(token,room=None):
    with rooms.database() as db:
        actor,room=context(db,token,room)
        call=db.execute('SELECT id FROM live_classes WHERE room=? AND ended IS NULL',(room,)).fetchone()
        if not call:raise ValueError('O Professor ainda não iniciou a aula.')
        peer=secrets.token_hex(24)
        db.execute('INSERT INTO live_peers VALUES(?,?,?,?,?,?)',(peer,call['id'],actor['id'],actor['name'],int(actor['role']!='student'),time.time()))
        return peer


def _peer(db,token,peer,room):
    actor,room=context(db,token,room)
    row=db.execute('SELECT p.* FROM live_peers p JOIN live_classes c ON c.id=p.class_id WHERE p.id=? AND p.actor=? AND c.room=? AND c.ended IS NULL',
        (peer,actor['id'],room)).fetchone()
    if not row:raise PermissionError('Aula encerrada ou acesso revogado.')
    return row


def exchange(token,peer,outbox=(),after=0,room=None):
    if len(outbox)>100:raise ValueError('Sinalização inválida.')
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        actor=_peer(db,token,peer,room)
        db.execute('UPDATE live_peers SET seen=? WHERE id=?',(time.time(),peer))
        for event in outbox:
            if event.get('kind') not in ('offer','answer','ice'):raise ValueError('Sinalização inválida.')
            target=db.execute('SELECT * FROM live_peers WHERE id=? AND class_id=?',(event.get('target'),actor['class_id'])).fetchone()
            if not target or not (actor['teacher'] or target['teacher']):raise PermissionError('Destino não autorizado.')
            payload=json.dumps(event.get('payload'))
            if len(payload)>100000:raise ValueError('Sinalização muito grande.')
            db.execute('INSERT OR IGNORE INTO live_signals(class_id,sender,target,kind,payload,created,nonce) VALUES(?,?,?,?,?,?,?)',
                (actor['class_id'],peer,target['id'],event['kind'],payload,time.time(),str(event.get('nonce',''))[:100]))
        signals=[dict(row,payload=json.loads(row['payload'])) for row in db.execute('SELECT id,sender,kind,payload FROM live_signals WHERE target=? AND id>? ORDER BY id LIMIT 200',(peer,int(after)))]
        peers=[dict(row) for row in db.execute('SELECT id,name,teacher FROM live_peers WHERE class_id=? AND id<>? AND seen>?',(actor['class_id'],peer,time.time()-25))]
        return dict(signals=signals,peers=peers,teacher=bool(actor['teacher']),id=peer)


def leave_live(token,peer,room=None):
    with rooms.database() as db:
        _peer(db,token,peer,room)
        db.execute('UPDATE live_peers SET seen=0 WHERE id=?',(peer,))
