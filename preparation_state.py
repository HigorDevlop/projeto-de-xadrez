"""Persistent preparation calendar and deterministic learning state machines."""
from datetime import date, datetime, time as day_time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from tempfile import NamedTemporaryFile
from threading import RLock
import json
import os
import random
import time

try:
    LOCAL_ZONE = ZoneInfo('America/Sao_Paulo')
except ZoneInfoNotFoundError:
    LOCAL_ZONE = timezone(timedelta(hours=-3))

STAGES = ('opening', 'middlegame', 'tactics')
STAGE_NAMES = {'opening': 'Aberturas', 'middlegame': 'Meio-jogo', 'tactics': 'Táticos'}
STAGE_SECONDS = 30 * 60
_PLAN_LOCK = RLock()


def today(now=None):
    return datetime.fromtimestamp(time.time() if now is None else now, LOCAL_ZONE).date()


def new_plan(username, start, end, openings, material=None):
    start, end = date.fromisoformat(str(start)), date.fromisoformat(str(end))
    if end < start:
        raise ValueError('A data de término deve ser igual ou posterior à data de início.')
    if (end - start).days > 365:
        raise ValueError('Organize até um ano de preparo por plano.')
    if not openings:
        raise ValueError('Selecione pelo menos uma abertura.')
    if len(openings) > 4:
        raise ValueError('Selecione no máximo 4 aberturas.')
    return {'version': 1, 'username': username, 'start': start.isoformat(), 'end': end.isoformat(),
            'openings': list(openings), 'created': time.time(), 'material': material or {},
            'days': {}, 'active': None,
            'course': {'line': 0, 'mode': 'guide', 'step': 0, 'marks': {}, 'queue': [], 'retry': [],
                       'answered': False, 'correct': False, 'help': False},
            'middle_cursor': 0, 'tactic_cursor': 0,
            'metrics': {'attempts': 0, 'correct': 0, 'learned_lines': []}}


def plan_path(username, namespace=None):
    folder = Path(os.environ.get('ACERVO_PREPARATION_DIR', Path(__file__).parent / 'data' / 'preparation'))
    if namespace == 'openings':
        folder = folder / 'openings'
    return folder / (sha256(username.strip().lower().encode()).hexdigest() + '.json')


def save_plan(plan, namespace=None):
    path = plan_path(plan['username'], namespace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(plan, ensure_ascii=False)
    # Separate browser sessions may save the same player's progress together.
    with _PLAN_LOCK:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                suffix='.tmp', delete=False) as file:
            temporary = Path(file.name)
            file.write(payload)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def load_plan(username, namespace=None):
    try:
        with _PLAN_LOCK:
            plan = json.loads(plan_path(username, namespace).read_text(encoding='utf-8'))
        if (not isinstance(plan, dict) or plan.get('version') != 1
                or not isinstance(plan.get('username'), str)
                or plan['username'].strip().lower() != username.strip().lower()):
            return None
        # Offline time is never charged to a training session.
        plan['active'] = None
        return plan
    except (OSError, ValueError, TypeError):
        return None


def day_progress(plan, day):
    return plan['days'].setdefault(str(day), {
        stage: {'seconds': 0.0, 'done': False, 'solved': 0, 'attempts': 0,
                'cursor': 0, 'answered': False, 'correct': False, 'help': False}
        for stage in STAGES})


def available_stage(plan, stage, day=None, now=None):
    if plan.get('finished'):
        return False
    day = str(day or today(now))
    if day != str(today(now)) or not plan['start'] <= day <= plan['end']:
        return False
    progress = day_progress(plan, day)
    index = STAGES.index(stage)
    return not progress[stage]['done'] and all(progress[previous]['done'] for previous in STAGES[:index])


def start_stage(plan, stage, now=None):
    now = time.time() if now is None else now
    day = str(today(now))
    if not available_stage(plan, stage, day, now):
        raise ValueError('Conclua a fase anterior e abra o treino na data correspondente.')
    pause_stage(plan, now)
    plan['active'] = {'day': day, 'stage': stage, 'last_tick': now}


def tick(plan, now=None):
    """Charge only this day's phase; stop exactly at the budget or at midnight."""
    active = plan.get('active')
    if not active:
        return False
    now = time.time() if now is None else now
    day = date.fromisoformat(active['day'])
    midnight = datetime.combine(day + timedelta(days=1), day_time(), LOCAL_ZONE).timestamp()
    elapsed = max(0, min(now, midnight) - active['last_tick'])
    progress = day_progress(plan, active['day'])[active['stage']]
    progress['seconds'] = min(STAGE_SECONDS, progress['seconds'] + elapsed)
    active['last_tick'] = now
    if progress['seconds'] >= STAGE_SECONDS:
        progress['done'] = True
        progress['reason'] = 'Tempo de treino concluído; posição salva para a próxima sessão.'
        plan['active'] = None
        return True
    if str(today(now)) != active['day']:
        plan['active'] = None
        return True
    return False


def pause_stage(plan, now=None):
    tick(plan, now)
    plan['active'] = None


def complete_stage(plan, reason='', now=None):
    if not plan.get('active'):
        return
    day, stage = plan['active']['day'], plan['active']['stage']
    tick(plan, now)
    progress = day_progress(plan, day)[stage]
    progress['done'], progress['reason'] = True, reason
    plan['active'] = None


def lesson_step(course, steps):
    if not steps:
        return None
    index = course['queue'][0] if course['mode'] == 'quiz' and course['queue'] else course['step']
    return steps[min(index, len(steps) - 1)]


def record_lesson_answer(course, steps, uci):
    if course['answered']:
        return False
    step = lesson_step(course, steps)
    if not step:
        return False
    correct = uci == step['uci']
    index = course['queue'][0] if course['mode'] == 'quiz' else course['step']
    course['marks'][str(index)] = 'correct' if correct else 'wrong'
    course['correct'], course['help'] = correct, not correct
    # In the quiz, errors move to a retry round. In practice, repeat immediately.
    course['answered'] = correct or course['mode'] == 'quiz'
    if course['mode'] == 'quiz' and not correct and index not in course['retry']:
        course['retry'].append(index)
    return correct


def advance_lesson(course, steps, seed=''):
    if not course['answered']:
        return False
    count = len(steps)
    course.update(answered=False, correct=False, help=False)
    if course['mode'] == 'quiz':
        course['queue'].pop(0)
        if not course['queue']:
            if course['retry']:
                course['queue'], course['retry'] = course['retry'], []
            else:
                course.update(line=course['line'] + 1, mode='guide', step=0, marks={}, queue=[], retry=[])
                return True
    else:
        course['step'] += 1
        if course['step'] >= count:
            course['step'], course['marks'] = 0, {}
            if course['mode'] == 'guide':
                course['mode'] = 'recall'
            else:
                course['mode'], course['queue'] = 'quiz', list(range(count))
                random.Random(f'{seed}:{course["line"]}').shuffle(course['queue'])
    return False


def tactic_limit(material):
    return min(10, len(material.get('tactics', [])))


def record_attempt(plan, correct):
    metrics = plan.setdefault('metrics', {'attempts': 0, 'correct': 0, 'learned_lines': []})
    metrics['attempts'] += 1
    metrics['correct'] += int(bool(correct))


def record_learned_line(plan, identifier):
    metrics = plan.setdefault('metrics', {'attempts': 0, 'correct': 0, 'learned_lines': []})
    if identifier not in metrics['learned_lines']:
        metrics['learned_lines'].append(identifier)


def training_metrics(plan):
    metrics = plan.get('metrics', {})
    attempts, correct = metrics.get('attempts', 0), metrics.get('correct', 0)
    return {'accuracy': round(100 * correct / attempts, 1) if attempts else None,
            'attempts': attempts, 'correct': correct,
            'lines': len(metrics.get('learned_lines', []))}


def finish_plan(plan, now=None):
    if plan.get('finished'):
        return
    pause_stage(plan, now)
    plan['finished'] = time.time() if now is None else now
