"""Run the current browser smoke tests against isolated local data."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SMOKE_TESTS = (
    'tests/test_login_ui.py',
    'tests/test_analysis_workspace.py',
    'tests/test_book_positions_ui.py',
    'tests/test_coach_chess_ui.py',
    'tests/test_profile_persistence.py',
    'tests/test_opening_reference_ui.py',
)


def main():
    return subprocess.run(
        [sys.executable, '-m', 'pytest', *SMOKE_TESTS, '-q', *sys.argv[1:]],
        cwd=ROOT, check=False,
    ).returncode


if __name__ == '__main__':
    raise SystemExit(main())
