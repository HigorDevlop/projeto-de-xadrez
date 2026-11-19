"""Four-state recovery and reproducible random queue insertion.

The session token supplies randomness; the revision makes each retry different.
The same small hash is used by the board's optimistic browser reconciliation.
"""
STATES = ('pending', 'wrong', 'unknown', 'correct')


def learner_plies(line):
    first = line.get('context_plies', 0 if line['side'] == 'white' else 1)
    return range(first, len(line['moves']), 2)


def quiz_state_key(session):
    return str(session['quiz_key'] if session.get('quiz_bank') else session['ply'])


def next_status(previous, correct, assisted=False):
    if not correct:
        return 'wrong'
    if assisted:
        return 'wrong' if previous == 'wrong' else 'unknown'
    return 'unknown' if previous == 'wrong' else 'correct'


def reinsert_index(token, revision, ply, remaining):
    if remaining == 0:
        return 0
    value = 2166136261
    for byte in f'{token}|{revision}|{ply}'.encode():
        value = ((value ^ byte) * 16777619) & 0xffffffff
    # When another position exists, it is always shown before this retry.
    return 1 + value % remaining


def ensure_quiz_states(plan, session):
    """Migrate an interrupted older quiz without losing outstanding recovery."""
    if session.get('mode') != 'quiz' or session.get('quiz_schema') == 2 or session['phase'] == 'complete':
        return
    from opening_training_state import current_line
    line = current_line(plan, session)
    plies = list(learner_plies(line))
    marks = session.get('marks', {})
    shown = session.get('display_marks', {})
    states = {str(ply): marks.get(str(ply), shown.get(str(ply), 'pending')) for ply in plies}
    pending = [ply for ply in plies if states[str(ply)] != 'correct']
    queue = [ply for ply in session.get('quiz_queue', []) if ply in pending]
    queue = list(dict.fromkeys(queue + pending))
    session.update(quiz_schema=2, quiz_states=states, display_marks=dict(states), quiz_queue=queue,
                   quiz_retry=[])
    checkpoint = session.get('ui_checkpoint')
    if checkpoint and checkpoint['kind'] == 'error':
        session.pop('ui_checkpoint')

