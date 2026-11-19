"""Position-based phase diagnostics from played games and local engine searches."""
from collections import Counter
from datetime import datetime,timedelta
from hashlib import sha256
from math import ceil
import json
import os
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
from threading import Event
import time

import chess
import chess.engine

from preparation_data import _records
from preparation_state import LOCAL_ZONE,today

VERSION=1
PHASES=('Abertura','Meio-jogo','Final')


def phase(board):
    values={chess.KNIGHT:3,chess.BISHOP:3,chess.ROOK:5,chess.QUEEN:9}
    material=sum(value*len(board.pieces(piece,color)) for piece,value in values.items() for color in chess.COLORS)
    queens=bool(board.queens)
    if material<=13 or not queens and material<=20:return 'Final'
    return 'Abertura' if board.fullmove_number<=10 else 'Meio-jogo'


def window(history,username,end=None,days=7):
    end=end or today();start=end-timedelta(days=days-1)
    return [row for row in _records(history,username) if row['outcome'] and row['timestamp']
            and start<=datetime.fromtimestamp(row['timestamp'],LOCAL_ZONE).date()<=end]


def _path(game_key,side):
    from performance_dashboard import _quality_path
    return _quality_path(game_key).parent/'diagnostics'/f'{game_key}-{side}.json'


def load(game_key,side):
    try:
        data=json.loads(_path(game_key,side).read_text(encoding='utf-8'))
        if data.get('version')==VERSION and data.get('complete') is True:return data
    except (OSError,ValueError,TypeError):pass
    return None


def save(game_key,side,data):
    path=_path(game_key,side);path.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as out:
        temporary=Path(out.name);json.dump(dict(data,version=VERSION),out,ensure_ascii=False)
    try:temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)


def from_reviews(game,reviews):
    """Reuse completed individual reviews instead of recomputing their positions."""
    from performance_dashboard import quality_key
    reviews={review.ply:review for review in reviews}
    moves=list(game.mainline_moves())
    if len(reviews)!=len(moves):return
    board=game.board();rows={'white':[],'black':[]}
    for ply,move in enumerate(moves,1):
        review=reviews.get(ply)
        if review is None:return
        side='white' if board.turn else 'black'
        rows[side].append(dict(ply=ply,number=board.fullmove_number,san=board.san(move),
            phase=phase(board),category=review.category,loss_cp=review.loss,
            loss_chances=review.expected_loss,best_san=review.best_san,fen=board.fen()))
        board.push(move)
    for side,items in rows.items():
        save(quality_key(game),side,dict(complete=True,rows=items,engine=next(iter(reviews.values())).engine_name,
            method='Análise individual completa',created=time.time()))


def analyze_record(record,engine_path,cancel=None,progress=None):
    from stockfish_analysis import _ENGINE_LOCK,check_cancelled,review_chances
    from performance_dashboard import quality_key
    cancel=cancel or Event();progress=progress or (lambda *_:None)
    key=quality_key(record['game']);cached=load(key,record['side'])
    if cached:return cached
    board=record['game'].board();moves=list(record['game'].mainline_moves());rows=[]
    limit=chess.engine.Limit(time=.08,depth=16)
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    while not _ENGINE_LOCK.acquire(timeout=.1):check_cancelled(cancel)
    try:
        with chess.engine.SimpleEngine.popen_uci(engine_path,**kwargs) as engine:
            engine.configure({k:v for k,v in {'Threads':1,'Hash':64}.items() if k in engine.options})
            before=engine.analyse(board,limit)
            for ply,move in enumerate(moves,1):
                check_cancelled(cancel)
                color=board.turn;original=board.copy(stack=False)
                number=board.fullmove_number;san=board.san(move)
                best=before.get('pv',[move])[0]
                best_san=board.san(best) if best in board.legal_moves else ''
                board.push(move)
                if board.is_game_over():
                    outcome=board.outcome()
                    terminal=chess.engine.Cp(0) if outcome.winner is None else chess.engine.MateGiven
                    after={'score':chess.engine.PovScore(terminal,outcome.winner if outcome.winner is not None else chess.WHITE)}
                else:after=engine.analyse(board,limit)
                if color==(record['side']=='white'):
                    played=after
                    loss=max(0,review_chances(before,color)-review_chances(after,color))
                    if loss>=.05:
                        # Check consequential losses at the same root position.
                        played=engine.analyse(original,chess.engine.Limit(time=.16,depth=18),root_moves=[move])
                        loss=max(0,review_chances(before,color)-review_chances(played,color))
                    cp=max(0,before['score'].pov(color).score(mate_score=100000)-played['score'].pov(color).score(mate_score=100000))
                    category='blunder' if loss>.20 else 'mistake' if loss>=.10 else 'inaccuracy' if loss>=.05 else 'good'
                    rows.append(dict(ply=ply,number=number,san=san,phase=phase(original),category=category,
                        loss_cp=cp,loss_chances=loss,best_san=best_san,fen=original.fen()))
                before=after
                progress(ply,len(moves))
            data=dict(version=VERSION,complete=True,rows=rows,engine=engine.id.get('name','Stockfish'),
                      method='Triagem local · até profundidade 16, com verificação dos lances críticos',created=time.time())
            save(key,record['side'],data)
            return data
    finally:_ENGINE_LOCK.release()


def aggregate(records):
    from performance_dashboard import quality_key
    phases={name:dict(phase=name,moves=0,errors=0,inaccuracies=0,loss_cp=0) for name in PHASES}
    numbers={};critical=[];analyzed=0
    for record in records:
        report=load(quality_key(record['game']),record['side'])
        if not report:continue
        analyzed+=1
        for row in report['rows']:
            bucket=phases[row['phase']];bucket['moves']+=1;bucket['loss_cp']+=row['loss_cp']
            error=row['category'] in ('mistake','blunder');bucket['errors']+=error
            bucket['inaccuracies']+=row['category']=='inaccuracy'
            move=numbers.setdefault(row['number'],dict(number=row['number'],moves=0,errors=0))
            move['moves']+=1;move['errors']+=error
            if error or row['category']=='inaccuracy':critical.append(dict(row,game_id=record['id'],url=record['id'] if str(record['id']).startswith('https://www.chess.com/') else '',side=record['side']))
    for row in phases.values():
        row['rate']=100*row['errors']/row['moves'] if row['moves'] else 0
        row['average_loss']=row['loss_cp']/row['moves'] if row['moves'] else 0
    eligible=[row for row in phases.values() if row['moves']>=10] or [row for row in phases.values() if row['moves']]
    if not any(row['errors'] for row in eligible):eligible=[row for row in phases.values() if row['moves']]
    worst=max(eligible,key=lambda row:(row['rate'],row['errors'])) if eligible and any(row['errors'] for row in eligible) else None
    minimum=max(3,min(10,ceil(analyzed*.2)))
    sampled=[row for row in numbers.values() if row['moves']>=minimum and row['errors']]
    hotspot=max(sampled,key=lambda row:(row['errors']/row['moves'],row['errors'])) if sampled else None
    peers=[row['phase'] for row in eligible if worst and row['phase']!=worst['phase'] and abs(row['rate']-worst['rate'])<2]
    return dict(total=len(records),analyzed=analyzed,phases=list(phases.values()),worst=worst,hotspot=hotspot,minimum_samples=minimum,close_phases=peers,
        numbers=sorted(numbers.values(),key=lambda row:row['number']),
        critical=sorted(critical,key=lambda row:row['loss_chances'],reverse=True))
