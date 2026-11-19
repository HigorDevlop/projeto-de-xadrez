"""Offline, per-account tactics history and earned experience points."""
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3
import time
from preparation_state import today

RANK_TIERS=((0,'Bronze'),(200,'Prata'),(600,'Ouro'),(1500,'Platina'),(3000,'Diamante'),(6000,'Mestre'))
# Preserve existing XP and tier thresholds; each tier now has five divisions.
RANKS=tuple((floor+(level-1)*(ceiling-floor)//5,f'{title} {level}')
    for index,(floor,title) in enumerate(RANK_TIERS)
    for ceiling in [RANK_TIERS[index+1][0] if index+1<len(RANK_TIERS) else 12000]
    for level in range(1,6))
NEW_CLEAN_XP=5
NEW_ASSISTED_XP=1


@contextmanager
def database():
    root=Path(os.environ.get('ACERVO_PREPARATION_DIR',Path(__file__).parent/'data/preparation'))
    root.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(root/'tactics.sqlite3',timeout=10)
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS attempts(owner TEXT,event TEXT,puzzle TEXT,theme TEXT,
            day TEXT,correct INTEGER,solved INTEGER,seconds REAL,points INTEGER,PRIMARY KEY(owner,event))''')
        db.execute('CREATE INDEX IF NOT EXISTS tactics_completed ON attempts(owner,puzzle,solved)')
        db.execute('''CREATE TABLE IF NOT EXISTS rank_resets(owner TEXT,request TEXT,created REAL,
            previous_points INTEGER,PRIMARY KEY(owner,request))''')
        yield db
        db.commit()
    finally: db.close()


def record(owner,event,puzzle,theme,correct,solved,seconds=0,clean=True):
    if not owner: return 0
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM attempts WHERE owner=? AND event=?',(owner,event)).fetchone(): return 0
        previous=db.execute('SELECT 1 FROM attempts WHERE owner=? AND puzzle=? AND solved=1 LIMIT 1',(owner,puzzle)).fetchone()
        points=(NEW_CLEAN_XP if clean else NEW_ASSISTED_XP) if solved and not previous else 0
        db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)',(owner,event,puzzle,theme,str(today()),int(correct),int(solved),max(0,seconds) if solved else 0,points))
        return points


def reset_rank(owner,request):
    """Explicit local maintenance: reset XP only, keeping all training history."""
    if not owner or not request:raise ValueError('Conta e identificação da solicitação são obrigatórias.')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM rank_resets WHERE owner=? AND request=?',(owner,request)).fetchone():return False
        previous=db.execute('SELECT COALESCE(SUM(points),0) FROM attempts WHERE owner=?',(owner,)).fetchone()[0]
        db.execute('UPDATE attempts SET points=0 WHERE owner=?',(owner,))
        db.execute('INSERT INTO rank_resets VALUES(?,?,?,?)',(owner,request,time.time(),previous))
        return True


def summary(owner,theme='mix',session=None):
    where='owner=?'+(' AND event LIKE ?' if session is not None else '')
    params=(owner,session+':%') if session is not None else (owner,)
    with database() as db:
        attempts,hits,solved,seconds=db.execute('''SELECT COUNT(*),COALESCE(SUM(correct),0),COALESCE(SUM(solved),0),
            COALESCE(SUM(seconds),0) FROM attempts WHERE '''+where,params).fetchone()
        points=db.execute('SELECT COALESCE(SUM(points),0) FROM attempts WHERE owner=?',(owner,)).fetchone()[0]
        if theme=='mix':
            known=db.execute('SELECT COUNT(DISTINCT puzzle) FROM attempts WHERE '+where+' AND solved=1',params).fetchone()[0]
        else:
            known=db.execute('SELECT COUNT(DISTINCT puzzle) FROM attempts WHERE '+where+' AND theme=? AND solved=1',params+(theme,)).fetchone()[0]
        recent=[dict(id=event,seconds=duration) for event,duration in db.execute(
            'SELECT event,seconds FROM attempts WHERE '+where+' AND solved=1 ORDER BY rowid DESC LIMIT 5',params)]
    goal=50 if theme=='mix' else 20
    index=max(i for i,(threshold,_) in enumerate(RANKS) if points>=threshold)
    floor,title=RANKS[index]
    ceiling=RANKS[index+1][0] if index+1<len(RANKS) else None
    return dict(attempts=attempts,hits=hits,errors=attempts-hits,solved=solved,
        average=round(seconds/solved,1) if solved else None,xp=points,rank=title,
        rank_progress=(points-floor)/(ceiling-floor) if ceiling else 1,next_xp=ceiling,
        preparation=round(100*min(known,goal)/goal),known=known,goal=goal,recent=recent)


def owner_for(state):
    import classroom
    from classroom_ui import training_token
    actor=classroom.identity(training_token() or state.get('classroom_token'))
    return str(actor['id']) if actor else ''
