"""Persistent local books with one transactional storage quota."""
import os
from pathlib import Path
import sqlite3

from book_reader import book_id

MAX_BOOK_BYTES = 500 * 1024 * 1024


class BookLibrary:
    def __init__(self, path=None, limit=MAX_BOOK_BYTES):
        configured = os.environ.get('COACH_BOOK_LIBRARY')
        classroom_db = os.environ.get('COACH_CLASSROOM_DB')
        self.path = Path(path or configured or (
            Path(classroom_db).parent / 'book_library.sqlite3' if classroom_db else
            Path(__file__).parent / 'data/book_library.sqlite3'))
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS books (owner TEXT NOT NULL, identity TEXT NOT NULL, '
                       'name TEXT NOT NULL, data BLOB NOT NULL, PRIMARY KEY(owner, identity))')

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def load(self, owner):
        with self.connect() as db:
            return tuple(db.execute('SELECT name,data FROM books WHERE owner=? ORDER BY rowid', (str(owner),)))

    def used(self):
        with self.connect() as db:
            return db.execute('SELECT COALESCE(SUM(length(data)),0) FROM books').fetchone()[0]

    def add(self, owner, files):
        incoming = {book_id(name, data): (name, data) for name, data in files}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = {row[0] for row in db.execute('SELECT identity FROM books WHERE owner=?', (str(owner),))}
            additions = [(str(owner), identity, name, data) for identity, (name, data) in incoming.items()
                         if identity not in existing]
            used = db.execute('SELECT COALESCE(SUM(length(data)),0) FROM books').fetchone()[0]
            if used + sum(len(row[3]) for row in additions) > self.limit:
                raise ValueError('A biblioteca tem limite total de 500 MB. Remova livros para liberar espaço; '
                                 'nenhum arquivo deste envio foi salvo.')
            db.executemany('INSERT INTO books(owner,identity,name,data) VALUES(?,?,?,?)', additions)
        return self.load(owner)

    def remove_all(self, owner):
        with self.connect() as db:
            db.execute('DELETE FROM books WHERE owner=?', (str(owner),))
        with self.connect() as db:
            db.execute('VACUUM')


def hydrate_library(state, owner):
    library = BookLibrary()
    identity = str(library.path.resolve()), str(owner)
    if state.get('_book_library_owner') != identity:
        changed_user = '_book_library_owner' in state
        # Preserve uploads already held by this session before local storage existed.
        if '_book_library_owner' not in state:
            legacy = (*state.get('study_files', ()), *state.get('library_uploads', ()))
            if legacy:
                library.add(owner, legacy)
        state.study_files = library.load(owner)
        state.library_uploads = ()
        state._book_library_owner = identity
        state.reader_book = None
        state.pop('book_page_sync', None)
        if changed_user:
            import chess.pgn
            state.book_game = str(chess.pgn.Game())
            state.book_ply = 0
            state.book_editing = False
            state.book_revision = state.get('book_revision', 0) + 1
            if images := state.pop('_reader_page_cache', None):
                images.executor.shutdown(wait=False, cancel_futures=True)
            if service := state.pop('_book_position_service', None):
                service.cancel_preloads()
                service.preload_executor.shutdown(wait=False, cancel_futures=True)
                service.executor.shutdown(wait=False, cancel_futures=True)
        state.study_upload_revision = state.get('study_upload_revision', 0) + int(changed_user)
        state.pop('books', None)
    return library
