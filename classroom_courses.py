"""Reusable course templates; publishing copies content, never learner answers."""
import json
import secrets
import time
import classroom as rooms
import classroom_materials as materials


def _table(db):
    db.execute('CREATE TABLE IF NOT EXISTS classroom_courses(id TEXT PRIMARY KEY,owner TEXT,title TEXT,payload TEXT,created REAL)')


def save_course(token,student,title):
    if not title.strip() or len(title)>150:raise ValueError('Informe um título de até 150 caracteres.')
    with rooms.database() as db:
        _table(db);materials.tables(db);db.execute('BEGIN IMMEDIATE')
        actor=rooms._identity(db,token);rooms._owned_student(db,token,student)
        rows=db.execute('SELECT id,title,kind,payload FROM lesson_materials m WHERE student=? AND NOT EXISTS (SELECT 1 FROM lesson_trail_history h WHERE h.material=m.id AND NOT EXISTS (SELECT 1 FROM lesson_trail_items i WHERE i.material=h.material)) ORDER BY created',(student,)).fetchall()
        if not rows:raise ValueError('Prepare ao menos um material antes de salvar o curso.')
        items=[]
        for row in rows:
            item=dict(title=row['title'],kind=row['kind'],payload=json.loads(row['payload']))
            step=db.execute("SELECT s.id,s.title,s.position,s.locked,i.position AS item_position,COALESCE(n.notes,'') AS notes FROM lesson_trail_items i JOIN lesson_trail_steps s ON s.id=i.step LEFT JOIN lesson_trail_notes n ON n.step=s.id WHERE i.material=?",(row['id'],)).fetchone()
            if step:item['trail_step']=dict(step)
            items.append(item)
        identifier=secrets.token_hex(16)
        db.execute('INSERT INTO classroom_courses VALUES(?,?,?,?,?)',(identifier,actor['id'],title.strip(),json.dumps(items),time.time()))
        return identifier


def list_courses(token):
    with rooms.database() as db:
        _table(db);actor=rooms._identity(db,token)
        if actor['role'] not in ('admin','professor'):raise PermissionError('Cursos são gerenciados pelo Professor e pelo administrador.')
        rows=db.execute('SELECT * FROM classroom_courses ORDER BY created DESC').fetchall() if actor['role']=='admin' else db.execute('SELECT * FROM classroom_courses WHERE owner=? ORDER BY created DESC',(actor['id'],)).fetchall()
        return [dict(dict(row),payload=json.loads(row['payload'])) for row in rows]


def assign_course(token,identifier,student,published=True):
    with rooms.database() as db:
        _table(db);materials.tables(db);db.execute('BEGIN IMMEDIATE')
        actor=rooms._identity(db,token);seat=rooms._owned_student(db,token,student)
        row=db.execute('SELECT * FROM classroom_courses WHERE id=?',(identifier,)).fetchone()
        if not row or actor['role']!='admin' and row['owner']!=actor['id']:raise PermissionError('Curso não disponível para seu perfil.')
        if seat['banned']:raise ValueError('Reative a vaga antes de atribuir um curso.')
        identifiers=[]
        steps={};new_steps=[]
        base=db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM lesson_trail_steps WHERE student=?',(student,)).fetchone()[0]
        for item in json.loads(row['payload']):
            payload=materials.validate(item['kind'],item['payload']);new=secrets.token_hex(16)
            if item['kind']=='video':
                from classroom_trails import _check_video
                _check_video(db,payload,seat['room'])
            db.execute('INSERT INTO lesson_materials VALUES(?,?,?,?,?,?,?,?)',(new,student,seat['room'],item['title'],item['kind'],json.dumps(payload),int(bool(published)),time.time()))
            if metadata:=item.get('trail_step'):
                if metadata['id'] not in steps:
                    step=dict(id=secrets.token_hex(16),title=metadata['title'],locked=bool(metadata['locked']),notes=metadata.get('notes',''),items=[],_course_position=metadata['position'])
                    steps[metadata['id']]=step;new_steps.append(step)
                    db.execute('INSERT INTO lesson_trail_steps VALUES(?,?,?,?,?,?)',(step['id'],student,seat['room'],step['title'],base+metadata['position'],int(step['locked'])))
                    db.execute('INSERT INTO lesson_trail_notes VALUES(?,?)',(step['id'],step['notes']))
                step=steps[metadata['id']]
                step['items'].append(dict(id=new,title=item['title'],kind=item['kind'],payload=payload,reviewed=True))
                db.execute('INSERT INTO lesson_trail_items VALUES(?,?,?)',(new,step['id'],metadata['item_position']))
                db.execute('INSERT INTO lesson_trail_history VALUES(?,?)',(new,student))
            identifiers.append(new)
        new_steps.sort(key=lambda step:step['_course_position'])
        for step in new_steps:step.pop('_course_position',None)
        draft_table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lesson_trail_drafts'").fetchone()
        if new_steps and draft_table:
            draft=db.execute('SELECT payload FROM lesson_trail_drafts WHERE student=?',(student,)).fetchone()
            if draft:
                content=json.loads(draft['payload']);content['steps'].extend(new_steps)
                db.execute('UPDATE lesson_trail_drafts SET payload=?,revision=revision+1 WHERE student=?',(json.dumps(content),student))
        return identifiers


def delete_course(token,identifier):
    with rooms.database() as db:
        _table(db);actor=rooms._identity(db,token)
        if actor['role'] not in ('professor','admin'):raise PermissionError('Acesso restrito ao Professor ou administrador.')
        row=db.execute('SELECT owner FROM classroom_courses WHERE id=?',(identifier,)).fetchone()
        if not row or actor['role']!='admin' and row['owner']!=actor['id']:raise PermissionError('Curso não disponível para seu perfil.')
        db.execute('DELETE FROM classroom_courses WHERE id=?',(identifier,))
