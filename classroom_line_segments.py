"""Split a prepared PGN into continuous, independently playable lessons."""
import chess.pgn
from classroom_materials import parse_pgn


def previous_line(draft,step_id,item_id):
    previous=None
    for step in draft['steps']:
        for item in step['items']:
            if step['id']==step_id and item['id']==item_id:return previous
            if item['kind']=='line':
                previous=item if item.get('reviewed') else None
    return None


def segment(source_pgn,start,count,side,instructions='',previous=None):
    source=parse_pgn(source_pgn);nodes=list(source.mainline());board=source.board()
    if type(start) is not int or start<0 or start>=len(nodes):raise ValueError('A linha anterior terminou a sequência disponível. Acrescente a continuação no PGN completo.')
    if type(count) is not int or not 1<=count<=100:raise ValueError('Escolha de 1 a 100 lances por bloco.')
    if previous:
        old=parse_pgn(previous.get('source_pgn',previous['pgn']))
        old_start=previous.get('start_ply',0);end=old_start+len(list(parse_pgn(previous['pgn']).mainline_moves()))
        if start!=end or old.board().fen()!=board.fen() or [n.move for n in nodes[:end]]!=list(old.mainline_moves())[:end]:
            raise ValueError('Mantenha os lances anteriores no PGN e acrescente a continuação depois deles.')
    for node in nodes[:start]:board.push(node.move)
    game=chess.pgn.Game();game.headers.update(source.headers);game.setup(board);game.headers['Result']='*'
    target=game
    for node in nodes[start:start+2*count]:
        target=target.add_main_variation(node.move);target.comment=node.comment;target.nags=set(node.nags)
    return dict(pgn=str(game),side=side,instructions=instructions,source_pgn=str(source),start_ply=start,move_count=count)


from functools import lru_cache


@lru_cache(maxsize=128)
def extend_sequence(source_pgn, required_plies):
    """Preserve every authored move and fill only the missing tail offline."""
    import os
    import subprocess
    import chess.engine
    from stockfish_analysis import find_engine, _ENGINE_LOCK
    game=parse_pgn(source_pgn)
    node=game.end();board=node.board();size=len(list(game.mainline_moves()))
    if size>=required_plies:return str(game)
    engine_path=find_engine()
    if not engine_path:raise ValueError('Stockfish local não encontrado para completar a continuação. Acrescente os lances no PGN.')
    if board.is_game_over():raise ValueError('A linha anterior terminou a partida; escolha outra sequência.')
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    try:
        with _ENGINE_LOCK, chess.engine.SimpleEngine.popen_uci(engine_path,**kwargs) as engine:
            engine.configure({key:value for key,value in {'Threads':1,'Hash':64}.items() if key in engine.options})
            for _ in range(required_plies-size):
                if board.is_game_over():break
                move=engine.play(board,chess.engine.Limit(depth=18,time=.3)).move
                if move is None:break
                board.push(move);node=node.add_main_variation(move)
        game.headers['Result']='*'
        return str(game)
    except (OSError,chess.engine.EngineError) as error:
        raise ValueError('Não foi possível calcular a continuação com o Stockfish local.') from error
