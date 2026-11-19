"""Account-scoped evidence, read locally; no engine jobs or inferred weaknesses."""
from collections import defaultdict
from datetime import date, timedelta
from io import StringIO

import chess.pgn

import analysis_archive
import classroom as rooms
import tactics_progress
from game_phase_diagnostics import phase
from preparation_state import load_plan, today

SOURCES = ('Partidas', 'Aberturas', 'Táticos', 'Preparos')
ERRORS = {'inaccuracy', 'mistake', 'blunder'}
# Descriptive guardrails, not significance tests or skill ratings.
MIN_SAMPLES = {'Partidas': 3, 'Aberturas': 3, 'Táticos': 5, 'Preparos': 3}
UNITS = {'Partidas': 'partidas', 'Aberturas': 'fases', 'Táticos': 'problemas distintos', 'Preparos': 'dias ativos'}
METRICS = {'Partidas': 'Lances classificados como imprecisão/erro (%)',
           'Aberturas': 'Média do acerto inicial das fases (%)',
           'Táticos': 'Acerto nos lances tentados (%)',
           'Preparos': 'Minutos de atividade registrados'}


def _day(value):
    try:
        return date.fromisoformat(str(value).replace('.', '-'))
    except ValueError:
        return None


def _row(source, theme, day, key, sample, value, total, detail, action):
    return dict(source=source, theme=theme, day=str(day), id=key, sample=sample,
                value=value, total=total, detail=detail, action=action)


def collect(token, *, end=None, days=7):
    """Only the authenticated training identity is accepted, never a public username."""
    if days not in (7, 30):
        raise ValueError('Escolha 7 ou 30 dias.')
    end = end or today()
    start = end - timedelta(days=2*days-1)
    with rooms.database() as db:
        actor = rooms._identity(db, token)
    owner = actor['id']
    rows, notes = [], []
    skipped = 0
    account = actor.get('chesscom', '').strip().casefold()
    for item in analysis_archive.listing(token):
        saved = analysis_archive.load(token, item['game'])
        if not saved:
            skipped += 1
            continue
        game = chess.pgn.read_game(StringIO(saved['pgn']))
        day = _day(game.headers.get('Date')) if game else None
        sides = [color for color, header in ((chess.WHITE, 'White'), (chess.BLACK, 'Black'))
                 if game and account and game.headers.get(header, '').strip().casefold() == account]
        if not game or game.errors or day is None or len(sides) != 1:
            skipped += 1
            continue
        if not start <= day <= end:
            continue
        board = game.board()
        for ply, move in enumerate(game.mainline_moves(), 1):
            review = saved['reviews'].get(ply)
            if board.turn == sides[0] and review and review.uci == move.uci():
                key = f"{saved['id']}:{ply}"
                rows.append(_row('Partidas', phase(board) + ' · ' + review.engine_name, day,
                    key, saved['id'], int(review.category in ERRORS), 1,
                    f"{game.headers.get('White')} × {game.headers.get('Black')} · lance {ply}: "
                    f'{review.san} · {review.category}',
                    dict(kind='game', game=saved['id'], ply=ply, train=review.category in ERRORS)))
            board.push(move)
    if skipped:
        notes.append(f'Partidas: {skipped} análise(s) sem data válida, legibilidade ou lado identificado pelo Chess.com desta conta foram excluídas.')
    if not account:
        notes.append('Partidas: vincule seu nome Chess.com para identificar seu lado nas análises salvas; nenhuma identidade foi presumida.')

    with tactics_progress.database() as db:
        attempts = db.execute('''SELECT event,puzzle,theme,day,correct,solved FROM attempts
            WHERE owner=? AND day BETWEEN ? AND ? ORDER BY day,event''', (owner, str(start), str(end))).fetchall()
    for event, puzzle, theme, day, correct, solved in attempts:
        rows.append(_row('Táticos', theme, day, event, puzzle, int(correct), 1,
                        f'Problema {puzzle} · lance {"correto" if correct else "incorreto"} · '
                        f'{"concluído" if solved else "não concluído neste evento"}', dict(kind='tactic', theme=theme)))

    # Teacher/admin legacy files are keyed by a public Chess.com name, not an account.
    # Do not import them into a private map without a verified ownership migration.
    plan_key = {'user': 'user:', 'student': 'classroom:'}.get(actor['role'])
    plan = load_plan(plan_key + owner, namespace='openings') if plan_key else None
    if not plan_key:
        notes.append('Aberturas: arquivos antigos de professor/administrador usam nome público, sem vínculo exclusivo verificável; não foram incluídos.')
    if plan:
        library = dict(plan.get('practice_library', {}))
        library['+'.join(plan.get('repertoire_ids', []))] = plan
        for course, saved in library.items():
            for number, result in saved.get('phase_results', {}).items():
                day = _day(result.get('day'))
                accuracy = result.get('accuracy')
                if (not result.get('completed') or day is None or not start <= day <= end
                        or not isinstance(accuracy, (int, float)) or not 0 <= accuracy <= 100):
                    continue
                key = f'{course}:phase:{number}'
                rows.append(_row('Aberturas', course, day, key, key, accuracy, 100,
                    f"Fase {number} · linha {result.get('line_id', '?')} · acerto inicial salvo {accuracy:g}% · "
                    f"{result.get('questions', '?')} perguntas", dict(kind='opening', course=course)))
    notes.append('Aberturas: só fases concluídas com data e acerto inicial salvo; sessões incompletas e progresso sem histórico datado não entram na tendência. Cada fase tem o mesmo peso.')

    if actor['role'] == 'student':
        with rooms.database() as db:
            rooms._identity(db, token, 'student')
            # Reuse the safe daily summary. Never expose visits, exit reasons or warnings.
            dates = db.execute('''SELECT day FROM events WHERE student=? AND day BETWEEN ? AND ?
                UNION SELECT day FROM training_time WHERE student=? AND day BETWEEN ? AND ?
                UNION SELECT day FROM training_visits WHERE student=? AND day BETWEEN ? AND ?''',
                (owner, str(start), str(end))*3).fetchall()
            for entry in dates:
                day = entry['day']
                summary = rooms._summary(db, owner, day)
                if summary['seconds'] <= 0:
                    continue
                rows.append(_row('Preparos', 'Atividade no preparo', day, day, day,
                    summary['seconds']/60, 1,
                    f"{summary['seconds']/60:.1f} min · {summary['lines']} linhas e {summary['tactics']} táticos concluídos",
                    dict(kind='preparation')))
    else:
        notes.append('Preparos: o histórico seguro disponível é o da própria conta de aluno na sala. Planos antigos vinculados só ao nome Chess.com não foram incluídos.')
    notes.append('Partidas: a data é a do PGN, não a data da análise. Classificações antigas podem usar versões diferentes do método; motores são separados. Táticos contam lances, incluindo novas tentativas. Tempo de preparo mede atividade, não habilidade.')
    return dict(owner=owner, name=actor.get('name', ''), rows=rows, notes=notes, days=days, end=end)


def aggregate(rows, *, end, days):
    start = end - timedelta(days=days-1)
    previous = start - timedelta(days=days)
    grouped = defaultdict(dict)
    for row in rows:
        day = _day(row['day'])
        if day and previous <= day <= end:
            grouped[(row['source'], row['theme'])][row['id']] = row
    result = []
    for (source, theme), unique in sorted(grouped.items()):
        evidence = sorted(unique.values(), key=lambda r: (r['day'], r['id']), reverse=True)
        buckets = ([r for r in evidence if _day(r['day']) >= start],
                   [r for r in evidence if _day(r['day']) < start])
        summaries = []
        for bucket in buckets:
            n = len({r['sample'] for r in bucket})
            total = sum(r['total'] for r in bucket)
            value = sum(r['value'] for r in bucket)
            metric = (value if source == 'Preparos' else 100*value/total) if total else None
            summaries.append(dict(samples=n, records=len(bucket), value=metric))
        current, before = summaries
        sufficient = min(current['samples'], before['samples']) >= MIN_SAMPLES[source]
        delta = current['value']-before['value'] if sufficient else None
        result.append(dict(source=source, theme=theme, current=current, previous=before,
                           delta=delta, evidence=evidence, sufficient=sufficient))
    return result


def open_training(token, state, evidence):
    """Resolve navigation against fresh, authorized evidence, not a supplied owner/PGN."""
    data = collect(token, days=30)
    row = next((r for r in data['rows'] if r['source'] == evidence['source'] and r['id'] == evidence['id']), None)
    if row is None:
        raise PermissionError('Esta evidência não está disponível nesta conta ou período.')
    action = row['action']
    kind = action['kind']
    if kind == 'game':
        primary = rooms.identity(state.get('classroom_token'))
        if not primary or primary['id'] != data['owner']:
            raise PermissionError('Volte ao perfil proprietário da análise para abrir seu treino de partidas.')
        saved = analysis_archive.load(token, action['game'])
        if action['train']:
            from analysis_training import create
            key = create(token, action['game'], action['ply'])
            state['analysis_training_' + data['owner'] + '_choice'] = key
            state['analysis_training_open'] = True
        state['dashboard_review_request'] = dict(pgn=saved['pgn'], ply=action['ply'])
        state['requested_page'] = 'Análise'
    else:
        target = {'tactic': 'Tático', 'opening': 'Aberturas', 'preparation': 'Preparo'}[kind]
        state['dashboard_evolution_request'] = dict(owner=data['owner'], target=target, action=action)
        state['requested_page'] = target


def apply_training_request(token, state, page, choose_theme):
    request = state.pop('dashboard_evolution_request', None)
    if not request:
        return
    actor = rooms.identity(token)
    if not actor or actor['id'] != request['owner'] or page != request['target']:
        return
    action = request['action']
    if page == 'Tático':
        from tactics import THEMES
        choose_theme(action['theme'] if action['theme'] in THEMES.values() else 'mix')
    elif page == 'Aberturas':
        state['room_opening_request'] = dict(id=action['course'], intent='master')
