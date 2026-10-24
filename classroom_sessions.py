"""Server-owned preparation attendance; audit details are teacher-only."""
import secrets
import time
import classroom as rooms
from preparation_state import today

HEARTBEAT_TIMEOUT=25


def _expire(db,student,now):
    # A disconnected browser cannot send a reliable final event. Stop at the
    # last confirmed heartbeat, never credit the time spent offline.
    db.execute("UPDATE training_visits SET ended=last_seen,reason='Conexão encerrada' WHERE student=? AND ended IS NULL AND (last_seen<? OR day<>?)",
        (student,now-HEARTBEAT_TIMEOUT,str(today(now))))


def _credit(db,row,now):
    delta=max(0,min(now-row['last_seen'],HEARTBEAT_TIMEOUT))
    db.execute('UPDATE training_visits SET seconds=seconds+?,last_seen=? WHERE id=?',(delta,now,row['id']))
    return row['seconds']+delta


def synchronize(db,student,now):
    _expire(db,student,now)
    row=db.execute('SELECT * FROM training_visits WHERE student=? AND ended IS NULL',(student,)).fetchone()
    if row and rooms._summary(db,student,row['day'])['trail_complete']:
        _credit(db,row,now)
        db.execute("UPDATE training_visits SET completed=1,ended=?,reason='Trilha concluída' WHERE id=?",(now,row['id']))


def begin(token,now=None,new_entry=False):
    now=time.time() if now is None else now
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        student=rooms._identity(db,token,'student')['id']
        _expire(db,student,now)
        summary=rooms._summary(db,student,str(today(now)))
        task=summary['routine']
        if not task:return None
        active=db.execute('SELECT id FROM training_visits WHERE student=? AND ended IS NULL',(student,)).fetchone()
        if active:return active['id']
        if summary['trail_complete'] and not new_entry:return None
        identifier=secrets.token_hex(16)
        db.execute('INSERT INTO training_visits(id,student,day,started,last_seen,target) VALUES(?,?,?,?,?,?)',
            (identifier,student,str(today(now)),now,now,task['minutes']*60))
        if summary['trail_complete']:
            db.execute("UPDATE training_visits SET completed=1,ended=?,reason='Trilha concluída' WHERE id=?",(now,identifier))
        return identifier


def heartbeat(token,active=True,now=None):
    now=time.time() if now is None else now
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        student=rooms._identity(db,token,'student')['id']
        synchronize(db,student,now)
        row=db.execute('SELECT * FROM training_visits WHERE student=? AND ended IS NULL',(student,)).fetchone()
        if not row:return
        _credit(db,row,now)
        if not active:
            db.execute("UPDATE training_visits SET ended=?,reason='Saiu do preparo' WHERE id=?",(now,row['id']))


def leave(token,now=None):
    heartbeat(token,False,now)


def current(token,now=None):
    """Safe student view: clock and completion only, never the private audit."""
    now=time.time() if now is None else now
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        student=rooms._identity(db,token,'student')['id']
        synchronize(db,student,now)
        row=db.execute('SELECT * FROM training_visits WHERE student=? AND day=? ORDER BY started DESC LIMIT 1',
            (student,str(today(now)))).fetchone()
        if not row:return None
        elapsed=row['seconds']+(max(0,now-row['last_seen']) if row['ended'] is None else 0)
        return dict(seconds=elapsed,target=row['target'],remaining=max(0,row['target']-elapsed),
            running=row['ended'] is None,completed=bool(row['completed']))


def history(token,student,days=30,now=None):
    now=time.time() if now is None else now
    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        rooms._owned_student(db,token,student)
        synchronize(db,student,now)
        rows=db.execute('SELECT * FROM training_visits WHERE student=? ORDER BY started DESC',(student,)).fetchall()
        result=[]
        for row in rows:
            if (today(now)-today(row['started'])).days>=days:continue
            entry=dict(row)
            entry['seconds']+=max(0,now-row['last_seen']) if row['ended'] is None else 0
            entry['early_exit']=bool(row['ended'] is not None and not row['completed'] and row['seconds']<row['target'])
            entry['status']='Trilha concluída' if row['completed'] else 'Saída antecipada' if entry['early_exit'] else 'Em treino' if row['ended'] is None else 'Trilha incompleta'
            entry['color']='green' if row['completed'] else 'red' if entry['early_exit'] else 'orange'
            result.append(entry)
        return result
