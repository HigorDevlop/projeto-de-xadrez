"""Questionário e percurso diário de preparo, com material previamente calculado."""
from concurrent.futures import CancelledError, ThreadPoolExecutor
from datetime import date, timedelta
from hashlib import sha256
from threading import Event
import time

import chess
import chess.svg
import streamlit as st

from preparation_repetition import create_session, current_exercise, revision, submit, counts
from design_tokens import palette
from preparation_ui import roadmap, STYLE
from interactive_board import interactive_board
from preparation_data import opening_families, build_training_material, _OPENING_FAMILIES
from preparation_state import (STAGES, STAGE_NAMES, STAGE_SECONDS, today, new_plan,
    load_plan, save_plan, day_progress, available_stage, start_stage, pause_stage,
    tick, complete_stage, tactic_limit, finish_plan, plan_path)


@st.cache_resource
def _executor():
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix='preparo')


def _save(plan):
    try:
        save_plan(plan)
        st.session_state.prep_saved_at = time.time()
        st.session_state.pop('prep_save_error', None)
    except OSError:
        st.session_state.prep_save_error = 'O progresso está nesta sessão, mas não foi possível salvá-lo neste computador.'


def pause_preparation():
    plan = st.session_state.get('prep_plan')
    if plan and plan.get('active'):
        pause_stage(plan)
        _save(plan)


def _owner(username):
    state = st.session_state
    if state.get('prep_owner') == username:
        return
    pause_preparation()
    job = state.get('prep_job')
    if job:
        job['cancel'].set()
    for key in list(state):
        if key.startswith('prep_'):
            del state[key]
    state.prep_owner = username
    state.prep_plan = load_plan(username or '')
    state.prep_revision = 0


def _queue(history, username, openings, engine, draft=None):
    state = st.session_state
    if state.get('prep_job'):
        state.prep_job['cancel'].set()
    cancel, status = Event(), {'text': 'Preparando a análise das suas partidas…'}
    future = _executor().submit(build_training_material, list(history), username,
        openings, engine, cancel, lambda message: status.update(text=message))
    state.prep_job = {'future': future, 'cancel': cancel, 'status': status, 'draft': draft}
    state.pop('prep_error', None)
    state.pop('prep_retry_draft', None)


@st.fragment(run_every=1)
def _poll(history, username, engine_path, stats):
    state = st.session_state
    job = state.get('prep_job')
    if job and not job['future'].done():
        st.info(job['status']['text'], icon='⏳')
        return
    if job:
        state.prep_job = None
        created = False
        try:
            material = job['future'].result()
            state.prep_profile = material
            if job['draft'] is not None:
                if not material.get('opening_lines'):
                    state.prep_error = 'Não foi possível criar aulas com as partidas dessas aberturas. Confira o motor e escolha uma abertura presente no histórico.'
                    state.prep_retry_draft = job['draft']
                else:
                    pause_preparation()
                    plan = job['draft']
                    plan['material'] = material
                    state.prep_plan = plan
                    state.prep_revision += 1
                    _save(plan)
                    created = True
        except CancelledError:
            pass
        except Exception as error:
            state.prep_error = f'Não foi possível preparar as aulas: {error}'
            state.prep_retry_draft = job['draft']
        # A análise prévia atualiza só este painel, preservando o questionário
        # enquanto o jogador seleciona aberturas ou edita as datas.
        if created:
            st.rerun()
    if state.get('prep_error'):
        st.error(state.prep_error)
        if st.button('Tentar preparar novamente'):
            draft = state.get('prep_retry_draft')
            _queue(history, username, draft['openings'] if draft else stats, engine_path, draft)
            st.info('Retomando a preparação das suas aulas…')
    material = state.get('prep_profile') or (state.get('prep_plan') or {}).get('material')
    if material:
        weaknesses = material.get('weaknesses', [])
        if weaknesses:
            with st.expander('Pontos para melhorar'):
                for weakness in weaknesses[:3]:
                    st.write('• ' + weakness['description'])


def _start(stage):
    state = st.session_state
    start_stage(state.prep_plan, stage)
    state.prep_revision += 1
    state.prep_review = False
    _save(state.prep_plan)


def _pause():
    pause_preparation()
    st.session_state.prep_return_to_map = True


def _finish(reason):
    complete_stage(st.session_state.prep_plan, reason)
    _save(st.session_state.prep_plan)
    st.session_state.prep_return_to_map = True


def _line(plan):
    lines = plan['material'].get('opening_lines', [])
    return lines[plan['course']['line'] % len(lines)] if lines else None


def _recall(plan, stage, progress):
    sessions = plan.setdefault('position_sessions', {})
    if stage not in sessions:
        exercises, mastered = [], []
        if stage == 'opening':
            for index, line in enumerate(plan['material'].get('opening_lines', [])):
                for ply, step in enumerate(line['steps']):
                    key = f"opening:{line['id']}:{ply}"
                    exercises.append(dict(step, id=key, side=line['side'], opening=line['label']))
                    if index < plan['course']['line']:
                        mastered.append(key)
        else:
            pool = plan['material'].get(stage, [])
            limit = tactic_limit(plan['material']) if stage == 'tactics' else len(pool)
            offset = progress.get('offset', plan.get('tactic_cursor' if stage == 'tactics' else 'middle_cursor', 0))
            for index in range(limit):
                exercise = pool[(offset + index) % len(pool)]
                key = f"{stage}:{exercise['id']}"
                exercises.append(dict(exercise, id=key))
                if index < progress['cursor']:
                    mastered.append(key)
        sessions[stage] = create_session(exercises, mastered=mastered)
    return sessions[stage]


def _answer():
    state, plan = st.session_state, st.session_state.prep_plan
    if not plan.get('active') or tick(plan):
        _save(plan)
        state.prep_return_to_map = True
        return
    active = plan['active']
    progress = day_progress(plan, active['day'])[active['stage']]
    session = _recall(plan, active['stage'], progress)
    if submit(session, state.prep_board.move, time.time()):
        progress['attempts'] += 1
        progress['solved'] = counts(session)['correct']
        if session['phase'] == 'complete':
            complete_stage(plan, 'Todas as posições desta fase foram dominadas.')
            state.prep_return_to_map = True
        _save(plan)


def _lesson(plan, dark, table):
    active = plan['active']
    _practice(plan, 'opening', day_progress(plan, active['day'])['opening'], dark, table)


def _practice(plan, stage, progress, dark, table):
    from opening_preparation_training import render_feedback, render_progress
    new_session = stage not in plan.get('position_sessions', {})
    session = _recall(plan, stage, progress)
    if new_session:
        _save(plan)
    exercise = current_exercise(session)
    if exercise is None:
        complete_stage(plan, 'Todas as posições disponíveis foram dominadas.')
        _save(plan)
        st.rerun()
    st.subheader(exercise.get('opening', STAGE_NAMES[stage]))
    with st.container(key='prep_repetition_board'):
        interactive_board(chess.Board(exercise['fen']), key='prep_board', on_move=_answer,
            revision=revision(session), flip=exercise['side'] == 'black', dark=dark,
            table=False, training_mode=True, show_coordinates=True)
    st.write('Jogue com as brancas.' if exercise['side'] == 'white' else 'Jogue com as pretas.')
    render_feedback(session)
    render_progress(session)


def _end_preparation():
    finish_plan(st.session_state.prep_plan)
    _save(st.session_state.prep_plan)
    st.session_state.prep_return_to_map = True


def _reset_preparation():
    state = st.session_state
    try:
        plan_path(state.prep_owner).unlink(missing_ok=True)
    except OSError:
        st.error('Não foi possível reiniciar. Tente novamente.')
        return False
    job = state.get('prep_job')
    if job:
        job['cancel'].set()
    for key in list(state):
        if key.startswith('prep_') and key != 'prep_owner':
            del state[key]
    state.prep_plan, state.prep_revision = None, 0
    return True


@st.dialog('Treino concluído', width='small', dismissible=False)
def _result_dialog(plan):
    sessions = plan.get('position_sessions', {}).values()
    results = [counts(session) for session in sessions]
    solved = sum(result['correct'] for result in results)
    total = sum(result['total'] for result in results)
    st.metric('Posições dominadas', f'{solved} / {total}')
    if not any(item['attempts'] for session in plan.get('position_sessions', {}).values()
               for item in session['positions'].values()):
        st.caption('Nenhuma tentativa registrada.')
    if st.button('Iniciar Novo Preparo', type='primary', width='stretch'):
        if _reset_preparation():
            st.rerun()


@st.fragment(run_every=1)
def _training(dark=False, table=False):
    state, plan = st.session_state, st.session_state.prep_plan
    if state.pop('prep_return_to_map', False):
        st.rerun()
    if tick(plan):
        _save(plan)
        st.rerun()
    active = plan.get('active')
    if not active:
        return
    progress = day_progress(plan, active['day'])[active['stage']]
    remaining = max(0, STAGE_SECONDS - int(progress['seconds']))
    with st.container(horizontal=True, vertical_alignment='center', key='prep_clock'):
        with st.container(width='stretch'):
            st.html(f'<div class="prep-clock" role="timer" aria-label="Tempo restante"><small>{STAGE_NAMES[active["stage"]]} · DIA {date.fromisoformat(active["day"]).day}</small>{remaining//60:02d}:{remaining%60:02d}</div>')
        st.button('Concluir Treino', on_click=_end_preparation, type='primary', width='content')
    if time.time() - state.get('prep_saved_at', 0) >= 10:
        _save(plan)
    if active['stage'] == 'opening':
        _lesson(plan, dark, False)
    else:
        _practice(plan, active['stage'], progress, dark, False)
    if state.get('prep_save_error'):
        st.warning(state.prep_save_error)


def _open_day():
    state = st.session_state
    event, plan = state.prep_roadmap.select, state.prep_plan
    if not isinstance(event, dict) or event.get('plan') != plan['created'] or event.get('day') != str(today()):
        return
    for stage in STAGES:
        if available_stage(plan, stage):
            _start(stage)
            return


@st.fragment(run_every=5)
def _map(dark=False):
    plan = st.session_state.prep_plan
    current = today()
    if plan.get('active') or plan.get('finished'):
        st.rerun()
    start, end = date.fromisoformat(plan['start']), date.fromisoformat(plan['end'])
    progress = day_progress(plan, current) if start <= current <= end else {}
    if current > end or (current == end and all(progress.get(stage, {}).get('done') for stage in STAGES)):
        finish_plan(plan)
        _save(plan)
        st.rerun()
    roadmap(plan, _open_day, dark)
    stage = next((stage for stage in STAGES if available_stage(plan, stage)), None)
    line = _line(plan)
    with st.container(key='prep_day_card'):
        picture, content = st.columns([1, 2], vertical_alignment='center')
        with picture:
            board = chess.Board(line['steps'][0]['fen']) if line else chess.Board()
            svg = chess.svg.board(board, coordinates=False, size=220, colors={'square light':'#ECEFE8','square dark':'#6A9173'})
            st.image(svg, width=220, caption='Posição da abertura')
        with content:
            view = min(max(current, start), end)
            st.subheader(f'Dia {view.day} · {view:%d/%m}')
            st.write(line['opening'] if line else 'Seu treino')
            status = STAGE_NAMES[stage] + ' disponível' if stage else 'Dia concluído' if current >= start else f'Começa em {start:%d/%m}'
            st.caption(status)
            chips = ''.join(f'<span class="{"done" if progress.get(item, {}).get("done") else ""}">{"✓ " if progress.get(item, {}).get("done") else ""}{STAGE_NAMES[item]}</span>' for item in STAGES)
            st.html('<div class="prep-status">'+chips+'</div>')
            st.button('Encerrar Preparo', on_click=_end_preparation, type='tertiary')


def _performance(history, username, dark=False):
    from performance import render_comparative_chart
    render_comparative_chart(history, username, dark, context='preparo', compact=True,
                             plan=st.session_state.get('prep_plan'))


def _toggle_opening(key):
    selected = list(st.session_state.get('prep_selected_openings', []))
    if key in selected:
        selected.remove(key)
    elif len(selected) < 4:
        selected.append(key)
    st.session_state.prep_selected_openings = selected


def render_preparation(history, username, engine_path, dark=False, table=False):
    username = username or ''
    _owner(username)
    state = st.session_state
    colors = palette(dark)
    variables = ';'.join(f'--chess-{key.replace("_", "-")}:{value}' for key, value in colors.items())
    st.html('<style>:root{' + variables + '}' + STYLE + '''
    [class*="st-key-prep_opening_card_"]{padding:1rem;border:1px solid var(--chess-border);border-radius:12px;background:var(--chess-surface)}
    [class*="st-key-prep_opening_card_"] img{display:block;width:min(100%,160px);margin:auto;border-radius:6px}
    [class*="st-key-prep_opening_card_"] button:disabled{opacity:.38;cursor:not-allowed}
    </style>''')
    plan = state.get('prep_plan')
    if not plan or plan.get('repertoire_mode'):
        from opening_training_ui import render_repertoire_preparation
        render_repertoire_preparation(username, _save, _reset_preparation, dark)
        return
    if plan:
        mode = 'prep-plan-mode'
        if plan.get('active') or plan.get('finished'):
            mode += ' prep-focus-mode'
        if plan.get('finished'):
            mode += ' prep-finished-mode'
        st.html(f'<span class="{mode}"></span>')
        if plan.get('finished'):
            # The static trail remains behind the blurred, non-dismissible result.
            roadmap(plan, _open_day, dark)
            _result_dialog(plan)
        elif plan.get('active'):
            _training(dark, table)
        else:
            _map(dark)
            st.button('Criar novo preparo com repertórios prontos', on_click=_reset_preparation)
        return
