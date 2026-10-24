"""Prefer activity only among engine candidates of comparable objective quality."""
import chess
import chess.engine

MAX_STYLE_LOSS_CP = 25
CENTRE=(chess.D4,chess.E4,chess.D5,chess.E5)


def score_cp(info,color):
    score=info.get('score')
    return score.pov(color).score(mate_score=100000) if score is not None else None


def king_pressure(board,color):
    king=board.king(color)
    if king is None: return 99
    return sum(bool(board.attackers(not color,square)) for square in chess.SquareSet(chess.BB_KING_ATTACKS[king]) | {king})


def development(board,color):
    home=0 if color else 7
    return sum(chess.square_rank(square)!=home for piece in (chess.KNIGHT,chess.BISHOP) for square in board.pieces(piece,color))


def activity(board,pv):
    """Explain visible features after the opponent's reply, not an attack guarantee."""
    color=board.turn
    after=board.copy()
    for move in pv[:2]:
        if move not in after.legal_moves: break
        after.push(move)
    centre=sum(len(after.attackers(color,s)) for s in CENTRE)-sum(len(board.attackers(color,s)) for s in CENTRE)
    developed=development(after,color)-development(board,color)
    danger=king_pressure(after,color)
    hanging=sum(piece.piece_type for square,piece in after.piece_map().items()
                if piece.color==color and piece.piece_type!=chess.KING and after.is_attacked_by(not color,square) and not after.is_attacked_by(color,square))
    move=pv[0]
    castle=board.is_castling(move)
    check=board.gives_check(move)
    queen=board.piece_type_at(move.from_square)==chess.QUEEN and board.fullmove_number<8
    forcing=0
    position=board.copy()
    for continuation in pv[:6]:
        if continuation not in position.legal_moves: break
        if position.turn==color: forcing+=int(position.gives_check(continuation))+.5*int(position.is_capture(continuation))
        position.push(continuation)
    initiative=1.8*developed+.3*centre+forcing+.8*int(castle)-.8*max(0,danger-king_pressure(board,color))-.7*int(queen)
    solidity=-danger-.3*hanging+.5*int(castle)+.2*developed
    reasons=[]
    if developed>0: reasons.append('desenvolvimento de peças')
    if centre>0: reasons.append('mais controle central')
    if castle: reasons.append('roque')
    if check: reasons.append('xeque')
    elif forcing: reasons.append('continuação com lances forçantes')
    return dict(initiative=initiative,solidity=solidity,reasons=reasons or ['continuação bem avaliada pelo motor'])


def choose_options(board,infos,played=None):
    if isinstance(infos,dict): infos=[infos]
    candidates=[]
    seen=set()
    for info in infos:
        pv=info.get('pv',[])
        if not pv or pv[0] not in board.legal_moves or pv[0].uci() in seen: continue
        seen.add(pv[0].uci())
        candidates.append(dict(info=info,move=pv[0].uci(),cp=score_cp(info,board.turn),**activity(board,pv)))
    if not candidates: return []
    best=max(candidates,key=lambda item:item['cp'] if item['cp'] is not None else -100001)
    score=best['info'].get('score')
    # Forced mates and unbounded/absent scores do not justify style alternatives.
    if score is None or score.pov(board.turn).is_mate() or best['info'].get('lowerbound') or best['info'].get('upperbound'):
        return [dict(best,kind='Principal do motor',loss_cp=0)]
    safe=[item for item in candidates if item['cp'] is not None and not item['info'].get('lowerbound')
          and not item['info'].get('upperbound') and not item['info']['score'].pov(board.turn).is_mate()
          and best['cp']-item['cp']<=MAX_STYLE_LOSS_CP]
    if len(safe)<2: return [dict(best,kind='Principal do motor',loss_cp=0)]
    alternatives=[item for item in safe if item['move']!=played]
    preferred=max(alternatives or safe,key=lambda item:(item['initiative'],item['cp']))
    result=[dict(preferred,kind='Iniciativa com segurança',loss_cp=best['cp']-preferred['cp'])]
    rest=[item for item in safe if item['move']!=preferred['move']]
    alternatives=[item for item in rest if item['move']!=played]
    if rest:
        solid=max(alternatives or rest,key=lambda item:(item['solidity'],item['cp']))
        result.append(dict(solid,kind='Opção sólida',loss_cp=best['cp']-solid['cp']))
    if best['move'] not in [item['move'] for item in result]:
        result.append(dict(best,kind='Principal do motor',loss_cp=0))
    return result


def analyse_options(engine,board,limit,played=None):
    infos=engine.analyse(board,limit,multipv=min(4,board.legal_moves.count()))
    options=choose_options(board,infos,played)
    history=None
    if played:
        move=chess.Move.from_uci(played)
        if move in board.legal_moves:
            entries=infos if isinstance(infos,list) else [infos]
            history=next((info for info in entries if info.get('pv') and info['pv'][0]==move),None)
            if history is None:
                history=engine.analyse(board,limit,root_moves=[move])
    return options,history
