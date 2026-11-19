"""Offline, course-local review of positions the learner actually missed."""
from copy import deepcopy
from hashlib import sha256
import chess

POLICY = 3


def identity(line, ply):
    board = chess.Board()
    for move in line['moves'][:ply]:
        board.push_uci(move)
    return sha256((line['side'] + ' ' + board.epd() + ' ' + line['moves'][ply]).encode()).hexdigest()


def record(plan, session, line, ply, *, hint=False):
    if session.get('practice_intent') == 'explore':
        return
    key = identity(line, ply)
    entry = plan.setdefault('opening_errors', {}).setdefault(key, dict(
        line=deepcopy(line), ply=ply, mistakes=0, hints=0))
    entry['hints' if hint else 'mistakes'] += 1


def candidates(plan, session, line):
    """Match exact taught paths; never import another opening or unseen depth."""
    from opening_training_state import lines_for
    from opening_repetition import learner_plies
    progress = plan.get('practice_progress', {})
    lines = [item for item in lines_for(plan).values()
             if item['id'] == line['id'] or progress.get(item['id'], {}).get('learned')]
    if session.get('custom_line'):
        lines = [line]
    pool = {}
    for item in lines:
        for ply in learner_plies(item):
            key = identity(item, ply)
            pool.setdefault(key, dict(line=item, ply=ply))
    errors = plan.get('opening_errors', {})
    missed = [dict(item, mistakes=errors[key].get('mistakes', 0), hints=errors[key].get('hints', 0))
              for key, item in pool.items() if key in errors]
    missed.sort(key=lambda item: (item['mistakes'], item['hints']), reverse=True)
    return missed


def recover_saved_errors(plan, session):
    from opening_training_state import lines_for
    from opening_repetition import learner_plies
    available = lines_for(plan)
    for saved in list(plan.get('practice_sessions', {}).values()) + [session]:
        base = saved.get('custom_line') or available.get(saved.get('line_id'))
        if not base or saved.get('practice_intent') == 'explore':
            continue
        marks = saved.get('quiz_states', {}) if saved.get('mode') == 'quiz' else saved.get('display_marks', saved.get('marks', {}))
        first = saved.get('quiz_first_answers', {}) if saved.get('mode') == 'quiz' else {}
        for key in set(marks) | set(first):
            item = (saved.get('quiz_bank') or {}).get(str(key), dict(line=base, ply=int(key)))
            if item['ply'] not in learner_plies(item['line']):
                continue
            if marks.get(key) in ('wrong', 'unknown') or first.get(key) is False:
                error_key = identity(item['line'], item['ply'])
                if error_key not in plan.get('opening_errors', {}):
                    record(plan, saved, item['line'], item['ply'], hint=marks.get(key) == 'unknown')


def apply(plan, session, line, limit):
    missed = candidates(plan, session, line) if session.get('practice_intent') != 'explore' else []
    if missed:
        # Every error is represented before revisiting any one of them.
        session['quiz_bank'] = {str(i): deepcopy(missed[i % len(missed)]) for i in range(limit)}
        session['quiz_scope'] = sorted({item['line']['id'] for item in missed})
        session['quiz_pool_size'] = len(missed)
    session['quiz_error_based'] = bool(missed)
    session['quiz_policy'] = POLICY


def migrate(plan, session):
    """Preserve answered/recovery slots in an interrupted legacy quiz."""
    if session.get('mode') != 'quiz' or session.get('phase') == 'complete' or session.get('quiz_policy') == POLICY:
        return
    from opening_training_state import lines_for, current_line
    line = session.get('custom_line') or lines_for(plan).get(session['line_id'])
    if not line:
        return
    bank = session.get('quiz_bank') or {
        str(ply): dict(line=current_line(plan, session), ply=ply) for ply in session.get('quiz_queue', [])}
    recover_saved_errors(plan, session)
    missed = candidates(plan, session, line)
    if missed:
        index = 0
        for key in session.get('quiz_queue', []):
            if session.get('quiz_states', {}).get(str(key)) == 'pending':
                bank[str(key)] = deepcopy(missed[index % len(missed)])
                index += 1
        session['quiz_bank'] = bank
        session['quiz_pool_size'] = len(missed)
        if session.get('phase') == 'answer' and session.get('quiz_queue'):
            key = str(session['quiz_queue'][0])
            item = bank[key]
            session.update(quiz_key=int(key), ply=item['ply'], history=list(item['line']['moves'][:item['ply']]))
        session['revision'] += 1
    session.update(quiz_policy=POLICY, quiz_error_based=bool(missed))
