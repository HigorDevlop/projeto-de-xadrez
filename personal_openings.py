"""Rank a player's archived opening decisions and calculate local UCI lines."""
from hashlib import sha256
from functools import lru_cache
from pathlib import Path
import csv
import io
import os
import subprocess
import chess
import chess.engine
import chess.pgn
from preparation_state import new_plan, today, save_plan, load_plan
from stockfish_analysis import find_engine, _ENGINE_LOCK
from opening_initiative import analyse_options,score_cp


def storage_key(owner, account):
    return owner + '|chesscom:' + account.strip().lower()


def latest_history(games, account):
    user=account.strip().lower();unique={}
    for game in games:
        if not isinstance(game,dict) or not isinstance(game.get('pgn'),str):continue
        if user not in [str(game.get(side,{}).get('username','')).lower() for side in ('white','black')]:continue
        unique[game.get('url') or game['pgn']]=game
    return sorted(unique.values(),key=lambda game:game.get('end_time',0),reverse=True)[:200]


def remember_history(owner, account, games):
    key = storage_key(owner, account) + '|history'
    saved = load_plan(key, namespace='openings') or {}
    merged = {g.get('url') or g['pgn']: g for g in saved.get('games', [])}
    user = account.strip().lower()
    for item in games:
        if not isinstance(item, dict) or not isinstance(item.get('pgn'), str):
            continue
        if user not in [str(item.get(side, {}).get('username', '')).lower() for side in ('white', 'black')]:
            continue
        merged[item.get('url') or item['pgn']] = item
    records = latest_history(merged.values(),account)
    if records != saved.get('games', []):
        save_plan(dict(version=1, username=key, games=records), namespace='openings')
    return records


def positions(games, account, max_ply=20):
    """Count distinct games per decision, including transpositions, by colour."""
    rows, seen = {}, set()
    user = account.strip().lower()
    for item in games:
        identity = item.get('url') or item.get('pgn')
        if not identity or identity in seen:
            continue
        seen.add(identity)
        try:
            game = chess.pgn.read_game(io.StringIO(item['pgn']))
            if not game or game.errors or game.board().fen() != chess.STARTING_FEN:
                continue
            white = str(item.get('white', {}).get('username') or game.headers.get('White', '')).lower()
            black = str(item.get('black', {}).get('username') or game.headers.get('Black', '')).lower()
            if user not in (white, black):
                continue
            color = user == white
            board, path, counted = game.board(), [], set()
            for move in list(game.mainline_moves())[:max_ply]:
                if board.turn == color and len(path) >= (2 if color else 1):
                    key = ('white' if color else 'black', board.epd())
                    if key not in counted:
                        row = rows.setdefault(key, dict(side=key[0], fen=board.fen(), prefix=list(path),
                            opening=game.headers.get('Opening') or game.headers.get('ECO') or 'Abertura do seu histórico', count=0,played={}))
                        row['count'] += 1
                        row['played'][move.uci()]=row['played'].get(move.uci(),0)+1
                        counted.add(key)
                board.push(move)
                path.append(move.uci())
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
    return sorted(rows.values(), key=lambda row: (-row['count'], len(row['prefix']), row['fen']))


def prepare(owner, account, games, count=12, depth=20, seconds=1.0, engine_factory=None, *, candidates=None):
    games=latest_history(games,account)
    candidates = (positions(games, account) if candidates is None else candidates)[:count]
    if not candidates:
        raise ValueError('Importe partidas padrão desse usuário do Chess.com antes de preparar o repertório.')
    path = find_engine()
    if not path:
        raise ValueError('Stockfish local indisponível. Nenhuma recomendação foi gerada.')
    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    factory = engine_factory or chess.engine.SimpleEngine.popen_uci
    lines = []
    with _ENGINE_LOCK, factory(path, **kwargs) as engine:
        engine.configure({'Threads': 1, 'Hash': 64})
        name = engine.id.get('name', 'Stockfish')
        for row in candidates:
            origin=chess.Board(row['fen'])
            played=max(row['played'],key=row['played'].get)
            options,history=analyse_options(engine,origin,chess.engine.Limit(depth=depth,time=seconds),played)
            history_cp=score_cp(history,origin.turn) if history else None
            best_cp=max((item['cp'] for item in options if item['cp'] is not None),default=None)
            for option in options:
                board=origin.copy();info=option['info'];pv=[]
                for move in info.get('pv',[])[:10]:
                    if move not in board.legal_moves: break
                    pv.append(move.uci());board.push(move)
                if not pv: continue
                moves=row['prefix']+pv
                if len(moves)%2==(0 if row['side']=='white' else 1): moves.pop()
                identifier='personal-'+sha256((row['side']+' '.join(moves)).encode()).hexdigest()[:20]
                lines.append(dict(id=identifier,moves=moves,side=row['side'],opening=row['opening'],
                    frequency=row['count'],context_plies=len(row['prefix']),engine=name,depth=info.get('depth'),searched_seconds=info.get('time'),
                    recommendation=option['kind'],reasons=option['reasons'],candidate_cp=option['cp'],style_loss_cp=option['loss_cp'],
                    played_uci=played,played_san=origin.san(chess.Move.from_uci(played)),played_count=row['played'][played],
                    played_cp=history_cp,played_loss_cp=max(0,best_cp-history_cp) if best_cp is not None and history_cp is not None else None,
                    candidate_mate=info['score'].pov(origin.turn).mate() if info.get('score') is not None else None,
                    played_mate=history['score'].pov(origin.turn).mate() if history and history.get('score') is not None else None,
                    suggested_san=origin.san(chess.Move.from_uci(pv[0])),is_alternative=pv[0]!=played,
                    variation=f"{row['opening']} · {option['kind']} · "+('Brancas' if row['side']=='white' else 'Pretas')))
    if not lines:
        raise ValueError('O motor não retornou continuações legais. O repertório anterior foi preservado.')
    plan = new_plan(storage_key(owner, account), today(), today(), [{'id':'personal','opening':'Seu repertório','side':'both'}])
    plan.update(repertoire_mode=True, repertoire_ids=[], personal_lines=lines, chesscom_account=account,
                training_days={}, retention={}, source_games=len(games), engine=name,recommendation_version=2)
    return plan


@lru_cache(maxsize=1)
def family_anchors():
    """Only defining opening moves; do not generate the full static curriculum."""
    shortest={}
    for path in (Path(__file__).parent/'data/openings').glob('*.tsv'):
        with path.open(encoding='utf-8-sig') as source:
            for row in csv.DictReader(source,delimiter='\t'):
                name=row['name'].split(':')[0]
                tokens=[word for word in row['pgn'].split() if not word.endswith('.')]
                old=shortest.get(name)
                if old is None or len(tokens)<len(old):shortest[name]=tokens
    result=[]
    for name,tokens in shortest.items():
        board=chess.Board();moves=[]
        for token in tokens:
            move=board.parse_san(token);moves.append(move.uci());board.push(move)
        if len(moves)<=12:result.append((tuple(moves),name))
    return sorted(result,key=lambda item:len(item[0]),reverse=True)


def trail_positions(games,account,count=12):
    groups={};anchors=family_anchors()
    for item in latest_history(games,account):
        game=chess.pgn.read_game(io.StringIO(item['pgn']))
        if not game or game.errors or game.board().fen()!=chess.STARTING_FEN:continue
        moves=tuple(move.uci() for move in game.mainline_moves())
        matched=next(((prefix,name) for prefix,name in anchors if moves[:len(prefix)]==prefix),None)
        if not matched:continue
        prefix,name=matched
        side='white' if str(item['white']['username']).lower()==account.lower() else 'black'
        group=groups.setdefault((name,side),dict(games=[],prefix=prefix))
        group['games'].append(item)
    ranked=sorted(groups.items(),key=lambda item:-len(item[1]['games']))
    result=[]
    # Round-robin across frequent openings: one early position cannot consume all slots.
    queues=[]
    for (name,side),group in ranked:
        rows=[row for row in positions(group['games'],account) if row['side']==side and
              tuple(row['prefix'][:len(group['prefix'])])==group['prefix']]
        for row in rows:
            row.update(opening=name,opening_frequency=len(group['games']))
        queues.append(rows[:4])
    for index in range(4):
        for rows in queues:
            if index<len(rows):result.append(rows[index])
            if len(result)>=count:return result
    return result


def prepare_history_trails(owner,account,games,**kwargs):
    games=latest_history(games,account)
    rows=trail_positions(games,account)
    plan=prepare(owner,account,games,candidates=rows,**kwargs)
    for line in plan['personal_lines']:
        row=next(row for row in rows if row['prefix']==line['moves'][:line['context_plies']] and row['side']==line['side'])
        line['opening_frequency']=row['opening_frequency']
    plan['recommendation_version']=3
    return plan
