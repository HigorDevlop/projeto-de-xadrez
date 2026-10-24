"""Keep older full-app unit tests authenticated and isolated from local data."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def authenticated_legacy_app(request, tmp_path, monkeypatch):
    if request.module.__name__ not in {'test_workflows', 'test_stockfish_books', 'test_home_startup'}:
        return
    import classroom
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'accounts.sqlite3'))
    monkeypatch.setenv('COACH_BOOK_LIBRARY', str(tmp_path/'books.sqlite3'))
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR', str(tmp_path/'performance'))
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path/'progress'))
    token = classroom.bootstrap_owner('test-admin', 'test-admin-password-123')
    original = AppTest.from_file
    components = [path.stem for path in ROOT.glob('*.py')
                  if 'st.components.v2.component(' in path.read_text(encoding='utf-8')]

    def create(path, *args, **kwargs):
        if Path(path).resolve() == ROOT/'app.py':
            # Each AppTest owns a fresh CCv2 registry, unlike a running server.
            for name in [*components, 'study_workspace', 'analysis_editor', 'opening_practice']:
                sys.modules.pop(name, None)
            app = original(path, *args, **kwargs)
            app.session_state.classroom_token = token
            app.session_state.welcome_entered = True
            return app
        return original(path, *args, **kwargs)

    monkeypatch.setattr(AppTest, 'from_file', staticmethod(create))
