"""Offline recall from the authenticated user's saved analysis."""
from hashlib import sha256
from io import StringIO
import json
import time

import chess
import chess.pgn

import analysis_archive
import classroom as rooms
from opening_training_state import schedule_review
from preparation_state import today

CATEGORIES = {'inaccuracy', 'mistake', 'blunder'}


def _table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS analysis_exercises(
        owner TEXT, id TEXT, payload TEXT NOT NULL, due TEXT NOT NULL,
        level INTEGER NOT NULL DEFAULT -1, revision INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(owner,id))''')
    db.execute('''CREATE TABLE IF NOT EXISTS analysis_attempts(
        owner TEXT, exercise TEXT, revision INTEGER, uci TEXT, matched INTEGER,
        created REAL, PRIMARY KEY(owner,exercise,revision))''')


def create(token, game_id, ply):
    saved = analysis_archive.load(token, game_id)
    if not saved:
        raise ValueError('Análise salva não encontrada nesta conta.')
    review = saved['reviews'].get(ply)
    if not review or review.category not in CATEGORIES:
        raise ValueError('Escolha uma imprecisão ou um erro analisado.')
    game = chess.pgn.read_game(StringIO(saved['pgn']))
    moves = list(game.mainline_moves())
    if not 1 <= ply <= len(moves):
        raise ValueError('Posição fora da partida.')
    board = game.board()
    for move in moves[:ply-1]:
        if move not in board.legal_moves:
            raise ValueError('Partida contém lance ilegal.')
        board.push(move)
    if not board.is_valid() or moves[ply-1] not in board.legal_moves or review.uci != moves[ply-1].uci():
        raise ValueError('Análise não corresponde à posição legal da partida.')
    best = board.parse_san(review.best_san)
    if not best or best not in board.legal_moves:
        raise ValueError('Recomendação não contém um lance legal.')
    line = review.best_line
    if line:
        continuation = chess.pgn.read_game(StringIO(
            f'[SetUp "1"]\n[FEN "{board.fen()}"]\n\n{line} *'))
        pv = list(continuation.mainline_moves()) if continuation else []
        if not pv or continuation.errors or pv[0] != best:
            raise ValueError('Continuação recomendada inválida.')
    # Position identity ignores move clocks: transpositions do not create duplicates.
    key = sha256(board.epd().encode()).hexdigest()
    data = dict(fen=board.fen(), uci=best.uci(), best_san=review.best_san,
                best_line=line, explanation=review.explanation, engine=review.engine_name,
                played=review.san, category=review.category, game=game_id, ply=ply)
    return _save_exercise(token, key, data)


def _save_exercise(token, key, data):
    """Shared persistence for validated analysis and repertoire recall sources."""
    with rooms.database() as db:
        _table(db)
        owner = rooms._identity(db, token)['id']
        db.execute('INSERT OR IGNORE INTO analysis_exercises(owner,id,payload,due) VALUES(?,?,?,?)',
                   (owner, key, json.dumps(data, ensure_ascii=False), str(today())))
    return key


def listing(token):
    with rooms.database() as db:
        _table(db)
        owner = rooms._identity(db, token)['id']
        return [dict(json.loads(row['payload']), id=row['id'], due=row['due'],
                     level=row['level'], revision=row['revision'])
                for row in db.execute('SELECT * FROM analysis_exercises WHERE owner=? ORDER BY due,id', (owner,))]


def submit(token, key, uci, revision):
    """Persist one legal attempt and its schedule atomically; reject stale UI events."""
    with rooms.database() as db:
        _table(db)
        db.execute('BEGIN IMMEDIATE')
        owner = rooms._identity(db, token)['id']
        row = db.execute('SELECT * FROM analysis_exercises WHERE owner=? AND id=?', (owner, key)).fetchone()
        if not row:
            raise ValueError('Exercício não encontrado nesta conta.')
        if row['revision'] != revision:
            raise ValueError('Tentativa já registrada. Reabra o exercício.')
        if row['due'] > str(today()):
            raise ValueError('Este exercício já foi revisado; aguarde a próxima revisão.')
        data = json.loads(row['payload'])
        board = chess.Board(data['fen'])
        move = board.parse_uci(uci)
        if not move or move not in board.legal_moves:
            raise ValueError('Escolha um lance legal.')
        matched = move.uci() == data['uci']
        retention = schedule_review(dict(level=row['level']), today(), failed=not matched)
        db.execute('INSERT INTO analysis_attempts VALUES(?,?,?,?,?,?)',
                   (owner, key, revision, move.uci(), int(matched), time.time()))
        db.execute('UPDATE analysis_exercises SET due=?,level=?,revision=revision+1 WHERE owner=? AND id=?',
                   (retention['due'], retention['level'], owner, key))
    return dict(data, matched=matched, attempt=board.san(move), due=retention['due'])
