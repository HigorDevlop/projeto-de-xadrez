"""Read-only continuity drafts. No transport, background job or restore policy.

Drafts remain in memory. They must not be persisted/uploaded until encryption,
account binding and conflict resolution have been configured by the product.
"""
from hashlib import sha256
import json
import math
from uuid import UUID

import classroom as rooms
from preparation_state import load_plan, _PLAN_LOCK

VERSION = 1
KINDS = {'game', 'review', 'attempt', 'progress'}
PROGRESS_FIELDS = ('practice_progress', 'practice_sessions', 'practice_current',
                   'retention', 'practice_library', 'repertoire_ids', 'classroom_line_ids',
                   'training_days', 'course', 'metrics', 'days')


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def capture(token):
    """Allowlisted records from the existing stores, scoped by authenticated ID.

    SQLite records form one read transaction; JSON plans have their own lock.
    This is deliberately not advertised as an atomic cross-store backup.
    """
    records = []
    def add(kind, key, value):
        records.append(dict(kind=kind, id=key, value=value))

    with rooms.database() as db:
        db.execute('BEGIN IMMEDIATE')
        actor = rooms._identity(db, token)
        owner = actor['id']
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'saved_analyses' in tables:
            for row in db.execute('SELECT game,pgn,payload FROM saved_analyses WHERE owner=?', (owner,)):
                add('game', row['game'], dict(pgn=row['pgn'], analysis=json.loads(row['payload'])))
        if 'analysis_exercises' in tables:
            for row in db.execute('SELECT id,payload,due,level,revision FROM analysis_exercises WHERE owner=?', (owner,)):
                add('review', row['id'], dict(exercise=json.loads(row['payload']), due=row['due'],
                                            level=row['level'], revision=row['revision']))
        if 'analysis_attempts' in tables:
            for row in db.execute('SELECT exercise,revision,uci,matched,created FROM analysis_attempts WHERE owner=?', (owner,)):
                add('attempt', row['exercise']+':'+str(row['revision']), dict(row))
    notes = ['Rascunho em memória; não enviado nem aplicado. Não é backup atômico entre arquivos.']
    with _PLAN_LOCK:
        # Only keys whose ownership is unambiguous in the existing desktop UI.
        keys = [('endgames', f"endgames:{actor['role']}:{owner}")]
        if actor['role'] in ('user', 'student'):
            scope = ('classroom:' if actor['role'] == 'student' else 'user:') + owner
            keys.append(('openings', scope))
            if actor.get('chesscom'):
                from personal_openings import storage_key
                keys.append(('personal-openings', storage_key(scope, actor['chesscom'])))
        else:
            notes.append('Cursos legados por nome público excluídos: vínculo de conta ambíguo.')
        for kind, key in keys:
            plan = load_plan(key, namespace='openings')
            if plan:
                # Library contains plans; take only progress, never arbitrary material/files.
                value = {field: plan[field] for field in PROGRESS_FIELDS
                         if field in plan and field != 'practice_library'}
                value['practice_library'] = {
                    course: {field: entry[field] for field in PROGRESS_FIELDS
                             if field in entry and field != 'practice_library'}
                    for course, entry in plan.get('practice_library', {}).items()}
                add('progress', kind, value)
    return dict(version=VERSION, account=owner, records=sorted(records, key=lambda r:(r['kind'], r['id'])), notes=notes)


def _index(snapshot, owner):
    if not isinstance(snapshot, dict) or snapshot.get('version') != VERSION:
        raise ValueError('Formato de continuidade incompatível.')
    if snapshot.get('account') != owner:
        raise PermissionError('Os dados não pertencem à conta autenticada.')
    records = snapshot.get('records')
    if not isinstance(records, list) or len(records) > 100000:
        raise ValueError('Lista de registros inválida.')
    index = {}
    for record in records:
        if (not isinstance(record, dict) or record.get('kind') not in KINDS
                or not isinstance(record.get('id'), str) or not record['id']
                or not isinstance(record.get('value'), dict)):
            raise ValueError('Registro de continuidade inválido.')
        key = (record['kind'], record['id'])
        if key in index:
            raise ValueError('Registro repetido no rascunho.')
        index[key] = _digest(record['value'])
    return index


def compare(token, local, incoming, base=None):
    """Three-way inspection only. Missing entries are NOT inferred deletions.

    No last-write-wins, clock comparison, XP addition or review rescheduling.
    Without a common base, differing versions require manual inspection.
    """
    with rooms.database() as db:
        owner = rooms._identity(db, token)['id']
    left, right = _index(local, owner), _index(incoming, owner)
    previous = _index(base, owner) if base is not None else {}
    rows = []
    for key in sorted(left.keys() | right.keys()):
        a, b, old = left.get(key), right.get(key), previous.get(key)
        if a == b:
            status = 'identical'
        elif a is None:
            status = 'incoming_only'
        elif b is None:
            status = 'local_only'
        elif old is not None and a == old:
            status = 'incoming_changed'
        elif old is not None and b == old:
            status = 'local_changed'
        else:
            status = 'conflict'
        rows.append(dict(kind=key[0], id=key[1], status=status))
    return rows


def last_command(local, incoming, *, observed_at, max_future_skew):
    """Preview the user's device-time priority policy; never apply a write.

    Commands must be captured at action time, not at upload/capture time.
    Caller supplies the trusted observation time and explicit clock tolerance.
    This cannot detect an otherwise plausible but incorrect offline clock.
    """
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    if not number(observed_at) or not number(max_future_skew) or max_future_skew < 0:
        raise ValueError('Informe horário observado e tolerância de relógio válidos.')
    for command in (local, incoming):
        if not isinstance(command, dict):
            return dict(winner=None, reason='missing_command_time')
        stamp = command.get('authored_at')
        if not number(stamp) or stamp < 0:
            return dict(winner=None, reason='missing_command_time')
        try:
            UUID(command['device'])
        except (ValueError, TypeError, KeyError, AttributeError):
            return dict(winner=None, reason='invalid_device')
        if type(command.get('sequence')) is not int or command['sequence'] < 1:
            return dict(winner=None, reason='invalid_sequence')
        if stamp > observed_at + max_future_skew:
            return dict(winner=None, reason='future_clock')
    a, b = local['authored_at'], incoming['authored_at']
    if UUID(local['device']) == UUID(incoming['device']):
        delta = incoming['sequence'] - local['sequence']
        if delta == 0 and a != b or delta * (b-a) < 0:
            return dict(winner=None, reason='sequence_clock_mismatch')
        if delta == 0:
            return dict(winner=None, reason='same_command_requires_content_check')
    if a == b:
        return dict(winner=None, reason='tied_clock')
    return dict(winner='incoming' if b > a else 'local', reason='latest_device_action')
