from concurrent.futures import ThreadPoolExecutor

import pytest

from book_library import BookLibrary


def test_books_survive_reopening_and_are_private_to_each_account(tmp_path):
    path = tmp_path / 'books.sqlite3'
    first = BookLibrary(path, limit=10)
    assert first.add('reader', [('Manual.txt', b'abc')]) == (('Manual.txt', b'abc'),)
    reopened = BookLibrary(path, limit=10)
    assert reopened.load('reader') == (('Manual.txt', b'abc'),)
    assert reopened.load('other') == ()
    reopened.add('reader', [('Manual.txt', b'abc')])
    assert reopened.used() == 3


def test_quota_is_total_atomic_and_space_can_be_reused(tmp_path):
    library = BookLibrary(tmp_path / 'books.sqlite3', limit=10)
    library.add('reader', [('A', b'123456')])
    with pytest.raises(ValueError, match='500 MB'):
        library.add('other', [('B', b'123'), ('C', b'12')])
    assert library.load('other') == () and library.used() == 6
    library.add('other', [('B', b'1234')])
    assert library.used() == 10
    library.remove_all('reader')
    assert library.load('other') == (('B', b'1234'),)
    library.add('reader', [('C', b'123456')])
    assert library.used() == 10


def test_two_simultaneous_uploads_cannot_exceed_quota(tmp_path):
    library = BookLibrary(tmp_path / 'books.sqlite3', limit=10)
    def save(owner):
        try:
            library.add(owner, [('Book', b'12345678')])
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(save, ['reader', 'other']))
    assert sum(results) == 1 and library.used() == 8
