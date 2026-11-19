"""Reusable trail drafts, separate training sessions and teacher progress views."""
import copy
import json
import secrets
import time

import classroom as rooms
import classroom_trails as trails


def tables(db):
    trails.tables(db)
    db.execute('CREATE TABLE IF NOT EXISTS training_trail_library(id TEXT PRIMARY KEY,owner TEXT,room TEXT,title TEXT,payload TEXT,created REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS training_session_history(id TEXT PRIMARY KEY,student TEXT,room TEXT,title TEXT,payload TEXT,created REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS training_session_pending(student TEXT PRIMARY KEY)')


def _current(db,token,student,revision):
    seat,draft,current=trails._draft(db,token,student)
    if revision!=current:raise ValueError('A trilha mudou. Atualize a tela antes de continuar.')
    return seat,draft,current


def _save(db,token,seat,draft,title):
    actor=rooms._identity(db,token)
    identifier=secrets.token_hex(16)
    db.execute('INSERT INTO training_trail_library VALUES(?,?,?,?,?,?)',
               (identifier,actor['id'],seat['room'],trails._title(title),json.dumps(draft),time.time()))
    return identifier


def save_template(token,student,revision,title):
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        seat,draft,_=_current(db,token,student,revision)
        if not draft['steps']:raise ValueError('Adicione linhas e atividades antes de salvar a trilha.')
        return _save(db,token,seat,draft,title)


def library(token):
    with rooms.database() as db:
        tables(db);actor=rooms._identity(db,token)
        if actor['role'] not in ('admin','professor'):raise PermissionError('A biblioteca é exclusiva do Professor.')
        rows=db.execute('SELECT * FROM training_trail_library WHERE owner=? ORDER BY created DESC',(actor['id'],))
        return [dict(dict(row),payload=json.loads(row['payload'])) for row in rows]


def _write_draft(db,student,room,draft,revision):
    db.execute('INSERT INTO lesson_trail_drafts VALUES(?,?,?,?) ON CONFLICT(student) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',
               (student,room,json.dumps(draft),revision))


def new_draft(token,student,revision,title='Nova trilha',save_title=None,template=None):
    """Start a new private draft; the student's published trail stays available."""
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        seat,old,current=_current(db,token,student,revision)
        if save_title:
            if not old['steps']:raise ValueError('A trilha atual está vazia.')
            _save(db,token,seat,old,save_title)
        draft=dict(title=trails._title(title),steps=[])
        if template:
            actor=rooms._identity(db,token)
            row=db.execute('SELECT * FROM training_trail_library WHERE id=? AND owner=?',(template,actor['id'])).fetchone()
            if not row:raise PermissionError('Trilha não disponível na sua biblioteca.')
            draft=copy.deepcopy(json.loads(row['payload']));draft['title']=trails._title(title)
            for step in draft['steps']:
                step['id']=secrets.token_hex(16);step.pop('release_at',None)
                for item in step['items']:
                    item['id']=secrets.token_hex(16)
                    if item['kind']=='video':trails._check_video(db,item['payload'],seat['room'])
        _write_draft(db,student,seat['room'],draft,current+1)
        db.execute('INSERT OR IGNORE INTO training_session_pending VALUES(?)',(student,))
        return dict(draft,revision=current+1)


def archive_before_publish(db,student):
    """Called after publication validation, inside the publishing transaction."""
    db.execute('CREATE TABLE IF NOT EXISTS training_session_pending(student TEXT PRIMARY KEY)')
    if not db.execute('SELECT 1 FROM training_session_pending WHERE student=?',(student,)).fetchone():return
    _archive(db,student)
    db.execute('DELETE FROM training_session_pending WHERE student=?',(student,))


def _archive(db,student):
    from classroom_tactic_blocks import tables as tactic_tables
    tactic_tables(db)
    db.execute('CREATE TABLE IF NOT EXISTS training_session_history(id TEXT PRIMARY KEY,student TEXT,room TEXT,title TEXT,payload TEXT,created REAL)')
    seat=db.execute('SELECT * FROM students WHERE id=?',(student,)).fetchone()
    items=[dict(row) for row in db.execute('SELECT * FROM lesson_materials WHERE student=? AND published=1',(student,))]
    if not items:return
    steps=[dict(row) for row in db.execute('SELECT * FROM lesson_trail_steps WHERE student=? ORDER BY position',(student,))]
    data=dict(items=items,steps=steps)
    for name,table in [('training','lesson_training'),('results','lesson_results'),('tactics','lesson_tactic_blocks')]:
        data[name]=[dict(row) for row in db.execute(f'SELECT * FROM {table} WHERE student=? AND material IN (SELECT id FROM lesson_materials WHERE student=? AND published=1)',(student,student))]
    title_row=db.execute('SELECT title FROM lesson_trail_titles WHERE student=?',(student,)).fetchone()
    title=title_row['title'] if title_row else ' / '.join(step['title'] for step in steps[:2]) or 'Sessão de treino'
    db.execute('INSERT INTO training_session_history VALUES(?,?,?,?,?,?)',
               (secrets.token_hex(16),student,seat['room'],title,json.dumps(data),time.time()))


def reset(token,student,revision):
    """Explicitly clear this student's current training, retaining an audit snapshot."""
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        seat,_,current=_current(db,token,student,revision)
        _archive(db,student)
        for table in ['lesson_trail_notes','lesson_trail_items','lesson_trail_schedule']:
            db.execute(f'DELETE FROM {table} WHERE step IN (SELECT id FROM lesson_trail_steps WHERE student=?)',(student,))
        for table in ['lesson_trail_steps','lesson_trail_history','lesson_results','lesson_training','lesson_tactic_blocks','lesson_materials','training_session_pending']:
            db.execute(f'DELETE FROM {table} WHERE student=?',(student,))
        _write_draft(db,student,seat['room'],dict(title='Nova trilha',steps=[]),current+1)
        db.execute('DELETE FROM lesson_trail_titles WHERE student=?',(student,))


def history(token,student):
    with rooms.database() as db:
        tables(db);rooms._owned_student(db,token,student)
        return [dict(dict(row),payload=json.loads(row['payload'])) for row in db.execute('SELECT * FROM training_session_history WHERE student=? ORDER BY created DESC',(student,))]


def progress(token,student):
    with rooms.database() as db:
        tables(db);rooms._owned_student(db,token,student)
        from classroom_tactic_blocks import tables as tactic_tables,activity_blocks
        tactic_tables(db)
        access=activity_blocks(db,student)
        rows=db.execute('''SELECT m.id,m.title,m.kind,s.title AS step,s.id AS step_id,s.locked,
            COALESCE(t.completed,0) AS completed,COALESCE(t.errors,0) AS errors,
            COALESCE(t.progress,0) AS progress,COALESCE(t.updated,b.updated) AS updated,
            r.payload AS result,b.payload AS tactics
            FROM lesson_trail_steps s JOIN lesson_trail_items i ON i.step=s.id
            JOIN lesson_materials m ON m.id=i.material
            LEFT JOIN lesson_training t ON t.material=m.id AND t.student=s.student
            LEFT JOIN lesson_results r ON r.material=m.id AND r.student=s.student
            LEFT JOIN lesson_tactic_blocks b ON b.material=m.id AND b.student=s.student
            WHERE s.student=? AND m.published=1 ORDER BY s.position,i.position''',(student,)).fetchall()
        result=[]
        for row in rows:
            item=dict(row);raw=item.pop('result');exam=json.loads(raw) if raw else None
            raw=item.pop('tactics');tactics=json.loads(raw) if raw else None
            item['completed']=bool(item['completed'] or exam or tactics and tactics['passed'])
            item['blocked']=bool(access.get(item['id']))
            item['accuracy']=None
            if tactics:
                item['errors']=tactics['errors'];item['progress']=tactics['index']
                if tactics['results']:item['accuracy']=100*sum(tactics['results'])/len(tactics['results'])
            item['score']=exam['score'] if exam else None
            item['maximum']=exam['maximum'] if exam else None
            result.append(item)
        return result
