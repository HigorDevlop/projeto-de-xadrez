"""Endgame adapter for the existing plan, per-position recall and review modules."""
import time
import chess
import classroom as rooms
import preparation_repetition as recall
from preparation_state import new_plan, load_plan, save_plan, today, _PLAN_LOCK
from opening_training_state import schedule_review
from endgame_lessons import LESSONS, lesson


def _key(token):
    with rooms.database() as db:
        actor = rooms._identity(db, token)
    return f"endgames:{actor['role']}:{actor['id']}"


def _load(key):
    plan = load_plan(key, namespace='openings')
    if plan is None:
        plan = new_plan(key, today(), today(),
            [dict(id=item['id'], opening=item['title'], side='white') for item in LESSONS])
        plan.update(practice_sessions={}, practice_progress={}, retention={}, practice_current=None)
    return plan


def load(token):
    with _PLAN_LOCK:
        return _load(_key(token))


def unlocked(plan, identifier):
    ids = [item['id'] for item in LESSONS]
    if identifier not in ids:
        return False
    index = ids.index(identifier)
    return index == 0 or bool(plan['practice_progress'].get(ids[index-1], {}).get('learned'))


def act(token, identifier, action, event=None):
    """Reload under the shared plan lock so stale events cannot overwrite progress."""
    key = _key(token)
    with _PLAN_LOCK:
        plan = _load(key)
        if not unlocked(plan, identifier):
            raise ValueError('Conclua a lição anterior para continuar.')
        item = lesson(identifier)
        session = plan['practice_sessions'].get(identifier)
        changed = False
        if action == 'begin':
            if session is None or (session['phase'] == 'complete' and
                                  plan['retention'][identifier]['due'] <= str(today())):
                session = recall.create_session([dict(id=identifier, fen=item['fen'], uci=item['uci'], side='white')])
                session.update(hint_level=0, solution=False, checkpoint=False, had_help=False)
                plan['practice_sessions'][identifier] = session
            plan['practice_current'] = identifier
            changed = True
        elif session and action == 'continue' and session['checkpoint'] and session['phase'] != 'complete':
            session.update(checkpoint=False, hint_level=0, solution=False)
            session['revision'] += 1
            changed = True
        elif session and action in ('hint', 'solution') and session['phase'] != 'complete':
            if action == 'hint':
                session['hint_level'] = min(3, session['hint_level']+1)
            else:
                session['solution'] = True
            session['had_help'] = True
            session['revision'] += 1
            changed = True
        elif session and action == 'move' and not session['checkpoint']:
            assisted = bool(session['hint_level'] or session['solution'])
            if recall.submit(session, event, time.time(), assisted=assisted):
                board = chess.Board(item['fen'])
                move = chess.Move.from_uci(event['uci'])
                san = board.san(move)
                board.push(move)
                session.update(checkpoint=True, result_fen=board.fen(), attempted_san=san,
                               assisted=assisted)
                progress = plan['practice_progress'].setdefault(identifier, dict(learned=False, attempts=0))
                progress['attempts'] += 1
                if session['phase'] == 'complete':
                    missed = session['positions'][identifier]['wrong_attempts'] > 0 or session['had_help']
                    plan['retention'][identifier] = schedule_review(plan['retention'].get(identifier, {}),
                                                                    today(), failed=missed)
                    progress.update(learned=True, last_review=str(today()), **plan['retention'][identifier])
                changed = True
        if changed:
            save_plan(plan, namespace='openings')
        return plan, changed


def feedback(item, session):
    """Describe the actual submitted board without pretending to evaluate alternatives."""
    board = chess.Board(session['result_fen'])
    correct = session['feedback']['correct']
    if correct:
        message = ('Objetivo atingido com ajuda; repita sem dica para concluir.' if session['assisted']
                   else 'Objetivo atingido nesta posição.')
    else:
        message = 'Lance legal, mas diferente do objetivo pedido. Isso não significa que ele perca a partida.'
    status = ('Xeque-mate.' if board.is_checkmate() else 'Afogamento: empate.' if board.is_stalemate()
              else 'O rei preto está em xeque.' if board.is_check() else 'O rei preto não está em xeque.')
    return f"Você jogou {session['attempted_san']}. {message} {status}"
