"""Entry point for the self-contained Windows distribution."""
from pathlib import Path
import os


def configure_data(home=None):
    base=Path(home or os.environ.get('LOCALAPPDATA',Path.home()))/'CoachChess'
    base.mkdir(parents=True,exist_ok=True)
    defaults={
        'COACH_CLASSROOM_DB':base/'classrooms.sqlite3',
        'COACH_BOOK_LIBRARY':base/'book_library.sqlite3',
        'COACH_BOOK_POSITION_DIR':base/'book_positions',
        'COACH_DESKTOP_STATE':base/'desktop',
        'ACERVO_PREPARATION_DIR':base/'preparation',
        'ACERVO_PERFORMANCE_DIR':base/'performance',
        'ACERVO_USER_PREFERENCE':base/'user.json',
        'ACERVO_APPEARANCE_PREFERENCE':base/'appearance.json',
    }
    for key,value in defaults.items():os.environ.setdefault(key,str(value))
    return base


if __name__=='__main__':
    configure_data()
    import desktop_launcher
    desktop_launcher.main()
