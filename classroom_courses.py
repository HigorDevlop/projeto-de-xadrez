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
        rows=db.execute('SELECT title,kind,payload FROM lesson_materials WHERE student=? ORDER BY created',(student,)).fetchall()
        if not rows:raise ValueError('Prepare ao menos um material antes de salvar o curso.')
        items=[dict(title=r['title'],kind=r['kind'],payload=json.loads(r['payload'])) for r in rows]
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
        for item in json.loads(row['payload']):
            payload=materials.validate(item['kind'],item['payload']);new=secrets.token_hex(16)
            db.execute('INSERT INTO lesson_materials VALUES(?,?,?,?,?,?,?,?)',(new,student,seat['room'],item['title'],item['kind'],json.dumps(payload),int(bool(published)),time.time()))
            identifiers.append(new)
        return identifiers


def delete_course(token,identifier):
    with rooms.database() as db:
        _table(db);actor=rooms._identity(db,token)
        if actor['role'] not in ('professor','admin'):raise PermissionError('Acesso restrito ao Professor ou administrador.')
        row=db.execute('SELECT owner FROM classroom_courses WHERE id=?',(identifier,)).fetchone()
        if not row or actor['role']!='admin' and row['owner']!=actor['id']:raise PermissionError('Curso não disponível para seu perfil.')
        db.execute('DELETE FROM classroom_courses WHERE id=?',(identifier,))
