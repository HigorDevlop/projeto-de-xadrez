"""Preloaded positions and ordered reconciliation for continuous quiz input."""
from functools import lru_cache

import chess

from interactive_board import position_data


@lru_cache(maxsize=128)
def prepared_positions(moves, flip):
    """Build every position once, before the first quiz answer."""
    board = chess.Board()
    positions = {}
    for ply, uci in enumerate(moves):
        if board.turn == (not flip):
            positions[str(ply)] = dict(position_data(board, flip), trainingExpected=uci)
            played = board.copy()
            played.push_uci(uci)
            positions[str(ply)]['played'] = position_data(played, flip)
        board.push_uci(uci)
    return positions


def quiz_data(line, session):
    if session['mode'] != 'quiz' or session['phase'] != 'answer':
        return None
    positions=prepared_positions(tuple(line['moves']), line['side'] == 'black')
    if session.get('quiz_bank'):
        positions={key:prepared_positions(tuple(item['line']['moves']),item['line']['side']=='black')[str(item['ply'])]
                   for key,item in session['quiz_bank'].items()}
    return dict(positions=positions,
                queue=list(session['quiz_queue']), retry=list(session['quiz_retry']),
                states=dict(session.get('quiz_states', {})),
                assisted=session['hint'])


def line_data(line, session):
    if session['mode'] == 'quiz' or session['phase'] != 'answer' or session.get('paused'):
        return None
    return dict(positions=prepared_positions(tuple(line['moves']), line['side'] == 'black'),
                current=session['ply'], mode=session['mode'])
