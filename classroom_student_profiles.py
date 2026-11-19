"""Persistent, teacher-authorized snapshots of students' public chess profiles."""
import json
import time

import classroom as rooms


def _table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS student_chess_profiles(
        student TEXT PRIMARY KEY, username TEXT NOT NULL, payload TEXT NOT NULL, updated REAL NOT NULL)''')


def load(token, student, username):
    with rooms.database() as db:
        rooms._owned_student(db, token, student)
        _table(db)
        row=db.execute('SELECT * FROM student_chess_profiles WHERE student=? AND username=?',
                       (student,username)).fetchone()
        return dict(data=json.loads(row['payload']),updated=row['updated']) if row else None


def save(token, student, username, data):
    from chesscom import normalize_username
    username=normalize_username(username)
    with rooms.database() as db:
        rooms._owned_student(db, token, student)
        _table(db)
        db.execute('''INSERT INTO student_chess_profiles VALUES(?,?,?,?)
            ON CONFLICT(student) DO UPDATE SET username=excluded.username,
            payload=excluded.payload,updated=excluded.updated''',
            (student,username,json.dumps(data,ensure_ascii=False),time.time()))
