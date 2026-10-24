"""Rank a player's archived opening decisions and calculate local UCI lines."""
from hashlib import sha256
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
    records = sorted(merged.values(), key=lambda g: g.get('end_time', 0), reverse=True)
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


def prepare(owner, account, games, count=12, depth=20, seconds=1.0, engine_factory=None):
    candidates = positions(games, account)[:count]
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
