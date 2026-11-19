"""Teacher release times, stored as UTC and enforced by all material gates."""
from datetime import datetime
import math
import time


def tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS lesson_trail_schedule(step TEXT PRIMARY KEY,release_at REAL NOT NULL)')


def release_time(value):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Confira a data e a hora de liberação.')
    if value<=time.time():raise ValueError('Escolha uma data e hora futuras.')
    return float(value)


def releases(db):
    tables(db)
    return {row['step']:row['release_at'] for row in db.execute('SELECT step,release_at FROM lesson_trail_schedule')}


def is_locked(locked, release_at, now=None):
    return bool(locked) and (release_at is None or (time.time() if now is None else now)<release_at)


def display_time(timestamp):
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(timestamp,ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M')
