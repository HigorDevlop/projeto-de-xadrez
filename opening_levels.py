"""Extend a chosen branch locally with Stockfish, two learner moves at a time."""
from hashlib import sha256
import os
import subprocess
import io
import chess
import chess.engine
from opening_training_state import lines_for
from stockfish_analysis import find_engine,_ENGINE_LOCK
from opening_initiative import analyse_options


def historical_replies(games,account,source):
    """Opponent replies actually faced, inside this exact opening and learner side."""
    from personal_openings import latest_history
    prefix=source.get('family_prefix',[])
    replies={}
    if not account or not prefix:return replies
    for item in latest_history(games,account):
        game=chess.pgn.read_game(io.StringIO(item['pgn']))
        if not game or game.errors or game.board().fen()!=chess.STARTING_FEN:continue
        learner='white' if item['white']['username'].lower()==account.lower() else 'black'
        if learner!=source['side']:continue
        moves=list(game.mainline_moves())
        if [move.uci() for move in moves[:len(prefix)]]!=prefix:continue
        board=game.board()
        for ply,move in enumerate(moves[:40]):
            if ply>=len(prefix) and board.turn!=(source['side']=='white'):
                choices=replies.setdefault(board.epd(),{})
                choices[move.uci()]=choices.get(move.uci(),0)+1
            board.push(move)
    return replies


def prepare_level(plan, source, target, engine_factory=None, *, history_games=(), account=''):
    if target<5 or target%2!=1:
        raise ValueError('Os níveis são 5, 7, 9, 11, 13 lances e assim por diante.')
    expected=5 if source.get('needs_preparation') else source.get('lesson_moves',5)+2
    if target!=expected:
        raise ValueError('Prepare o próximo nível, avançando dois lances por vez.')
    path=find_engine()
    if not path: raise ValueError('Stockfish local indisponível para preparar a continuação.')
    moves=list(source['moves'])
    end=2*target-(1 if source['side']=='white' else 0)
    board=chess.Board()
    for uci in moves: board.push_uci(uci)
    choices={}
    replies=historical_replies(history_games,account,source)
    historical_moves=0
    for line in lines_for(plan).values():
        position=chess.Board()
        for uci in line['moves']:
            if position.turn==(source['side']=='white'): choices.setdefault(position.epd(),uci)
            position.push_uci(uci)
    factory=engine_factory or chess.engine.SimpleEngine.popen_uci
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    with _ENGINE_LOCK,factory(path,**kwargs) as engine:
        engine.configure({'Threads':1,'Hash':64})
        name=engine.id.get('name','Stockfish')
        while len(moves)<end:
            if board.is_game_over():
                raise ValueError('Esta linha termina antes do próximo nível. Continue por outra linha da abertura.')
            known=choices.get(board.epd()) if board.turn==(source['side']=='white') else None
            faced=replies.get(board.epd(),{}) if board.turn!=(source['side']=='white') else {}
            if known:
                move=chess.Move.from_uci(known)
            elif faced:
                move=chess.Move.from_uci(max(faced,key=lambda uci:(faced[uci],uci)))
                historical_moves+=1
            else:
                if board.turn==(source['side']=='white'):
                    options,_=analyse_options(engine,board,chess.engine.Limit(depth=20,time=.35))
                    pv=options[0]['info'].get('pv',[]) if options else []
                else:
                    info=engine.analyse(board,chess.engine.Limit(depth=20,time=.35))
                    pv=info.get('pv',[])
                if not pv: raise ValueError('O motor não retornou uma continuação válida.')
                move=pv[0]
            if move not in board.legal_moves: raise ValueError('Continuação inválida; a linha anterior foi preservada.')
            moves.append(move.uci());board.push(move)
    course_id=source.get('course_id') or plan['repertoire_ids'][0]
    result=dict(source,id=course_id+'-'+sha256(' '.join(moves).encode()).hexdigest()[:12],
                moves=moves,course_id=course_id,lesson_moves=target,needs_preparation=False,
                stage='foundation' if target==5 else 'depth',engine=name,
                history_reply_count=historical_moves,
                variation=f"Linha {source['branch']} · {target} lances")
    result.pop('context_plies',None)
    return result
