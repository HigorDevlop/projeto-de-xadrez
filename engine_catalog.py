"""Discover installed review engines without launching them on page navigation."""
import os
from pathlib import Path
import shutil


def find_berserk():
    configured = os.environ.get('BERSERK_PATH')
    if configured is not None:
        return configured if Path(configured).is_file() else ''
    folder = Path(__file__).resolve().parent / 'engines'
    names = ('berserk/berserk.exe', 'berserk.exe') if os.name == 'nt' else ('berserk/berserk', 'berserk')
    for name in names:
        if (folder / name).is_file():
            return str(folder / name)
    return shutil.which('berserk') or ''


def review_engines(stockfish_path):
    # Keep unavailable choices visible: a missing chosen binary must never
    # silently switch an analysis to a different engine.
    return {'Stockfish': stockfish_path, 'Berserk': find_berserk()}
