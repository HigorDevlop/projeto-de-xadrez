"""Bundled, read-only puzzle bank. Runtime selection never contacts a server."""
from functools import lru_cache
import gzip
import json
import os
from pathlib import Path
import secrets


class LocalBankExhausted(ValueError):
    def __init__(self,available):
        self.available=available
        super().__init__('Nenhum outro tático local dessa faixa está disponível. Amplie a faixa ou escolha outro tema.')


def bank_path():
    return Path(os.environ.get('COACH_TACTICS_BANK',Path(__file__).parent/'data/tactics/puzzles.jsonl.gz'))


@lru_cache(maxsize=2)
def _bank(path,modified):
    from tactics import Puzzle,THEMES
    puzzles=[];index={theme:[] for theme in THEMES.values()}
    with gzip.open(path,'rt',encoding='utf8') as source:
        for line in source:
            row=json.loads(line)
            puzzle=Puzzle(row['id'],row['fen'],tuple(row['solution']),int(row['rating']),tuple(row['themes']),row['last_move'])
            position=len(puzzles);puzzles.append(puzzle);index['mix'].append(position)
            for theme in puzzle.themes:
                if theme in index and theme!='mix':index[theme].append(position)
    if not puzzles:raise ValueError('O banco local de táticos está vazio.')
    return tuple(puzzles),index


def select_puzzle(theme,minimum,maximum,exclude_id=None):
    from tactics import THEMES
    if theme not in THEMES.values():raise ValueError('Tema inválido.')
    if type(minimum) is not int or type(maximum) is not int or not 0<=minimum<=maximum<=4000:
        raise ValueError('Selecione uma faixa de rating válida, com início menor ou igual ao final.')
    path=bank_path()
    try:puzzles,index=_bank(str(path),path.stat().st_mtime_ns)
    except OSError as error:raise ValueError('O banco local de táticos não foi instalado. Repare os arquivos do aplicativo.') from error
    excluded={exclude_id} if isinstance(exclude_id,str) else set(exclude_id or ())
    matches=[puzzles[i] for i in index[theme] if minimum<=puzzles[i].rating<=maximum]
    candidates=[p for p in matches if p.id not in excluded]
    if not candidates:
        raise LocalBankExhausted(len(matches))
    return secrets.choice(candidates)


def bank_count():
    path=bank_path()
    return len(_bank(str(path),path.stat().st_mtime_ns)[0])
