"""One-move room challenges using existing assignments and immutable results."""
from hashlib import sha256
import json
import re
import time

import chess
import classroom as rooms
import classroom_materials as materials


def _teacher(db, token):
    actor = rooms._identity(db, token)
    if actor['role'] not in ('professor', 'admin'):
        raise PermissionError('Somente o professor pode publicar e consultar os resultados da sala.')
    return actor


def validate(fen, instructions, solution):
    if not isinstance(instructions, str) or not instructions.strip() or len(instructions) > 5000:
        raise ValueError('Escreva uma instrução de até 5000 caracteres.')
    try:
        board = chess.Board(fen)
        if not board.is_valid() or board.is_game_over():
            raise ValueError()
        move = board.parse_uci(solution)
        if not move or move not in board.legal_moves:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Informe uma posição legal, não encerrada, e um lance UCI legal como solução.') from None
    return dict(fen=board.fen(), instructions=instructions.strip(), solution=move.uci())


def publish(token, title, fen, instructions, solution, event):
    """One publication token creates one assignment per active seat, atomically."""
    with rooms.database() as db:
        materials.tables(db)
        db.execute('BEGIN IMMEDIATE')
        actor = _teacher(db, token)
        if not isinstance(title, str) or not title.strip() or len(title) > 150:
            raise ValueError('Informe um título de até 150 caracteres.')
        if not isinstance(event, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}', event):
            raise ValueError('Identificador de publicação inválido.')
        payload = validate(fen, instructions, solution)
        group = sha256((actor['id'] + ':' + event).encode()).hexdigest()
        payload['challenge'] = group
        previous = db.execute("SELECT title,payload FROM lesson_materials WHERE room=? AND kind='challenge' AND json_extract(payload,'$.challenge')=?",
                              (actor['id'], group)).fetchall()
        if previous:
            if any(row['title'] != title.strip() or json.loads(row['payload']) != payload for row in previous):
                raise ValueError('Esta publicação já foi usada com outro conteúdo. Inicie um novo desafio.')
            return group
        students = db.execute('SELECT id FROM students WHERE room=? AND banned=0', (actor['id'],)).fetchall()
        if not students:
            raise ValueError('A sala não tem alunos ativos para receber o desafio.')
        for student in students:
            identifier = sha256((group + ':' + student['id']).encode()).hexdigest()
            db.execute('INSERT INTO lesson_materials VALUES(?,?,?,?,?,?,?,?)',
                (identifier, student['id'], actor['id'], title.strip(), 'challenge',
                 json.dumps(payload), 1, time.time()))
        return group


def student_challenges(token):
    with rooms.database() as db:
        materials.tables(db)
        actor = rooms._identity(db, token, 'student')
        rows = db.execute("SELECT id FROM lesson_materials WHERE student=? AND room=? AND kind='challenge' AND published=1 ORDER BY created DESC",
                          (actor['id'], actor['room'])).fetchall()
        result = []
        for row in rows:
            try:
                material, _ = materials._get(db, token, row['id'])
            except PermissionError:
                continue
            payload = json.loads(material['payload'])
            saved = db.execute('SELECT payload FROM lesson_results WHERE material=? AND student=?',
                               (material['id'], actor['id'])).fetchone()
            # An explicit allowlist: no expected move, variation or teacher payload.
            result.append(dict(id=material['id'], title=material['title'], fen=payload['fen'],
                instructions=payload['instructions'], result=json.loads(saved['payload']) if saved else None))
        return result


def submit(token, identifier, fen, uci):
    with rooms.database() as db:
        materials.tables(db)
        db.execute('BEGIN IMMEDIATE')
        row, actor = materials._get(db, token, identifier)
        if actor['role'] != 'student' or row['kind'] != 'challenge':
            raise PermissionError('Somente o aluno destinatário pode enviar esta tentativa.')
        previous = db.execute('SELECT payload FROM lesson_results WHERE material=? AND student=?',
                              (identifier, actor['id'])).fetchone()
        if previous:
            return json.loads(previous['payload'])
        payload = json.loads(row['payload'])
        if fen != payload['fen']:
            raise ValueError('A posição mudou. Reabra o desafio.')
        board = chess.Board(payload['fen'])
        try:
            move = board.parse_uci(uci)
            if not move or move not in board.legal_moves:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Envie um lance legal para esta posição.') from None
        correct = move.uci() == payload['solution']
        result = dict(uci=move.uci(), san=board.san(move), correct=correct,
                      solution=payload['solution'], solution_san=board.san(chess.Move.from_uci(payload['solution'])),
                      score=int(correct), maximum=1, percent=100*int(correct), submitted=time.time())
        db.execute('INSERT INTO lesson_results VALUES(?,?,?,?)',
                   (identifier, actor['id'], json.dumps(result), time.time()))
        return result


def results(token):
    with rooms.database() as db:
        materials.tables(db)
        actor = _teacher(db, token)
        rows = db.execute("""SELECT m.id,m.title,m.payload,m.published,s.id AS student,s.name,s.banned,
            r.payload AS result FROM lesson_materials m JOIN students s ON s.id=m.student AND s.room=m.room
            LEFT JOIN lesson_results r ON r.material=m.id AND r.student=m.student
            WHERE m.room=? AND m.kind='challenge' ORDER BY m.created DESC,s.name""", (actor['id'],)).fetchall()
        return [dict(id=row['id'], title=row['title'], student=row['student'], name=row['name'],
                     banned=bool(row['banned']), published=bool(row['published']),
                     challenge=json.loads(row['payload'])['challenge'],
                     result=json.loads(row['result']) if row['result'] else None) for row in rows]
