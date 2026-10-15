"""Opening points in half-point units, with protected rank floors."""
from datetime import date, timedelta

from preparation_state import today

RANKS = ('Bronze', 'Prata', 'Ferro', 'Ouro', 'Platina', 'Diamante',
         'Candidato a Mestre', 'Mestre Nacional', 'Mestre', 'Mestre FIDE',
         'Mestre Internacional', 'Grande Mestre')
LEVEL_UNITS = 200
RANK_UNITS = 5 * LEVEL_UNITS
MAX_UNITS = len(RANKS) * RANK_UNITS
GRACE_DAYS = 7
DECAY_UNITS_PER_DAY = 2


def ranking_state(plan):
    # Older progress remains learned; no points are invented for unrecorded runs.
    score = plan.setdefault('practice_ranking', dict(units=0, floor=0,
        last_active=str(today()), last_decay=str(today()), completed=0,
        rank_units=RANK_UNITS))
    if score.get('rank_units') != RANK_UNITS:
        # Preserve earned points while recalculating the protected rank floor
        # under the corrected thresholds (100 per level, 500 per rank).
        score['floor'] = min(len(RANKS) - 1, score['units'] // RANK_UNITS) * RANK_UNITS
        score['rank_units'] = RANK_UNITS
    return score


def apply_decay(plan, day=None):
    day = day or today()
    old = dict(plan.get('practice_ranking', {}))
    score = ranking_state(plan)
    grace_end = date.fromisoformat(score['last_active']) + timedelta(days=GRACE_DAYS)
    since = max(grace_end, date.fromisoformat(score['last_decay']))
    days = max(0, (day - since).days)
    score['units'] = max(score['floor'], score['units'] - days * DECAY_UNITS_PER_DAY)
    score['last_decay'] = str(max(day, date.fromisoformat(score['last_decay'])))
    return old != score


def rank_summary(plan=None):
    score = ranking_state(plan) if plan is not None else dict(units=0)
    units = score['units']
    index = min(len(RANKS) - 1, units // RANK_UNITS)
    within = units - index * RANK_UNITS
    level = min(5, within // LEVEL_UNITS + 1)
    level_units = within - (level - 1) * LEVEL_UNITS
    next_rank = RANKS[min(index + 1, len(RANKS) - 1)]
    return dict(points=units / 2, rank_points=within / 2, rank=RANKS[index],
        level=level, level_points=level_units / 2, level_ratio=level_units / LEVEL_UNITS,
        next_rank=next_rank, ratio=within / RANK_UNITS,
        rank_index=index, remaining=max(0, (RANK_UNITS - within) / 2))


def award_completion(plan, session):
    if session.get('points_recorded') or session.get('practice_intent') == 'explore':
        return 0
    apply_decay(plan)
    score = ranking_state(plan)
    units = (1 if session.get('requested_hint') else
             2 if session.get('had_error') or session['line_id'] in session.get('failed', []) else 4)
    score['units'] = min(MAX_UNITS, score['units'] + units)
    index = min(len(RANKS) - 1, score['units'] // RANK_UNITS)
    score['floor'] = max(score['floor'], index * RANK_UNITS)
    score.update(last_active=str(today()), last_decay=str(today()), completed=score['completed'] + 1)
    session.update(points_recorded=True, earned_points=units / 2)
    return units / 2


def decay_library(plan):
    if not plan:
        return False
    changed = apply_decay(plan)
    for saved in plan.get('practice_library', {}).values():
        changed = apply_decay(saved) or changed
    return changed
