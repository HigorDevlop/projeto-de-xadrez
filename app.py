from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from html import escape
from io import StringIO
from pathlib import Path
from threading import Event
from time import perf_counter
import base64
import json
import os

import chess
import chess.pgn
import streamlit as st

from chess_review import (BookIndex, CATEGORIES, decode_text, canonical_category, canonical_explanation,
                          export_review, read_games)
from chesscom import fetch_recent_games, fetch_dashboard_games, normalize_username, fetch_rating
from game_play import play_move
from interactive_board import interactive_board
from profile_avatar import profile_avatar
from stockfish_analysis import find_engine, analyse_with_books
from book_study import BookStudy, prepare_explanations
from quick_question import answer_question
from pgn_clipboard import pgn_clipboard
from presentation import apply_theme, classification_legend, brand, page_heading
from design_tokens import palette
from analysis_summary import render_analysis_summary
from tactic_art import theme_art
from tactics import THEMES, fetch_puzzle_range, fetch_puzzle_pair, solve_move
from tactic_demo import tactic_demo
from page_chrome import page_chrome
from tactics_forge import tactics_forge
from tutor import load_passages, tutor_mood
from book_reader import merge_books
from study_workspace import render_study, study_board as current_study_board
from preparation_workspace import render_preparation, pause_preparation
from preparation_state import load_plan, today as local_today
from performance import render_comparative_chart
from performance_dashboard import render_dashboard, save_game_quality
from recent_games import recent_games, recent_eight, history_revision, game_id

ROOT = Path(__file__).resolve().parent
USER_PREFERENCE = Path(os.environ.get("ACERVO_USER_PREFERENCE", ROOT / ".streamlit/last_chesscom_user.json"))
APPEARANCE_PREFERENCE = Path(os.environ.get("ACERVO_APPEARANCE_PREFERENCE", ROOT / ".streamlit/appearance.json"))
st.set_page_config(page_title="Acervo · Estudo de xadrez", page_icon="♞", layout="wide", initial_sidebar_state="expanded")


def load_saved_user():
    try:
        user = normalize_username(json.loads(USER_PREFERENCE.read_text(encoding="utf-8")).get("username", ""))
        # Migrate a fixture accidentally persisted by older versions of the tests.
        return "" if user == "demo_import_test" and not os.environ.get("ACERVO_USER_PREFERENCE") else user
    except (OSError, TypeError, ValueError, AttributeError):
        return ""


def save_user(username):
    USER_PREFERENCE.parent.mkdir(parents=True, exist_ok=True)
    USER_PREFERENCE.write_text(json.dumps({"username": username}), encoding="utf-8")


def load_saved_theme():
    try:
        theme = json.loads(APPEARANCE_PREFERENCE.read_text(encoding="utf-8")).get("theme")
        return theme if theme in {"Claro", "Escuro"} else "Claro"
    except (OSError, TypeError, ValueError, AttributeError):
        return "Claro"


def load_saved_background(preferences=None):
    image = (load_appearance() if preferences is None else preferences).get("background_image")
    if not isinstance(image, dict) or image.get("mime") not in {
            "image/png", "image/jpeg", "image/webp"}:
        return None
    try:
        data = base64.b64decode(image["data"], validate=True)
    except (KeyError, TypeError, ValueError):
        return None
    return (image["mime"], data) if data else None


def save_theme(theme):
    save_appearance(theme=theme)


def load_appearance():
    try:
        value = json.loads(APPEARANCE_PREFERENCE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_appearance(**changes):
    preferences = load_appearance()
    preferences.update(changes)
    APPEARANCE_PREFERENCE.parent.mkdir(parents=True, exist_ok=True)
    APPEARANCE_PREFERENCE.write_text(json.dumps(preferences), encoding="utf-8")


def table_preference_changed():
    try:
        save_appearance(show_table=st.session_state.show_table)
    except OSError:
        st.session_state.theme_save_error = 'Mesa ajustada nesta sessão; não foi possível salvar a preferência.'


def choose_appearance(theme):
    state = st.session_state
    state.theme_mode = theme
    state.background_mode = theme
    try:
        save_appearance(theme=theme, background_mode=theme)
    except OSError:
        state.theme_save_error = "Tema aplicado nesta sessão; não foi possível salvá-lo neste computador."


def theme_selector_changed():
    choice = st.session_state.theme_selector
    if choice in {"☾ Escuro", "Escuro"}:
        choose_appearance("Escuro")
    elif choice in {"☀ Claro", "Claro"}:
        choose_appearance("Claro")


@st.cache_data(max_entries=1, show_spinner=False)
def load_openings():
    index = BookIndex()
    index.add_opening_catalog(ROOT / "data/openings")
    return index


@st.cache_data(max_entries=2, show_spinner=False)
def load_library(files, max_plies):
    index, errors = load_openings(), []
    for name, data in files:
        try:
            if name.lower().endswith(".bin"):
                index.add_polyglot(data, name)
            elif name.lower().endswith(".pgn"):
                index.add_pgn(decode_text(data), name, max_plies)
        except (ValueError, UnicodeError) as error:
            errors.append(f"{name}: {error}")
    passages, text_errors = load_passages(files)
    return index, BookStudy(passages), errors + text_errors


@st.cache_data(max_entries=2, show_spinner=False)
def portrait_data(path, modified):
    return base64.b64encode(Path(path).read_bytes()).decode()


def background_data(image):
    if not image:
        return ""
    mime, data = image
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def background_mode_changed(widget_key):
    st.session_state.background_mode = st.session_state[widget_key]
    if st.session_state.background_mode in {'Claro', 'Escuro'}:
        choose_appearance(st.session_state.background_mode)
        st.session_state.theme_selector = '☾ Escuro' if st.session_state.theme_mode == 'Escuro' else '☀ Claro'


def background_settings():
    state = st.session_state
    st.markdown('**Fundo de tela**')
    options = ['Claro', 'Escuro', 'Imagem personalizada']
    widget_key = f'background_mode_widget_{state.appearance_revision}'
    st.selectbox('Estilo do fundo', options, index=options.index(state.background_mode), key=widget_key,
                 on_change=background_mode_changed, args=(widget_key,))
    def background_changed():
        upload = state.get(f'page_background_upload_{state.background_upload_revision}')
        if upload:
            state.background_image = (upload.type, upload.getvalue())
            state.background_mode = 'Imagem personalizada'
            state[widget_key] = 'Imagem personalizada'
            try:
                save_appearance(background_mode='Imagem personalizada', background_image={
                    'mime': upload.type,
                    'data': base64.b64encode(state.background_image[1]).decode('ascii'),
                })
            except OSError:
                state.theme_save_error = 'Fundo aplicado nesta sessão; não foi possível salvá-lo neste computador.'
    st.file_uploader('Escolha uma imagem', type=['png', 'jpg', 'jpeg', 'webp'],
                     key=f'page_background_upload_{state.background_upload_revision}',
                     on_change=background_changed, max_upload_size=8)
    if state.background_image and st.button('Restaurar fundo do tema', icon=':material/refresh:'):
        state.background_image = None
        state.background_mode = state.theme_mode
        try:
            save_appearance(background_mode=state.theme_mode, background_image=None)
        except OSError:
            state.theme_save_error = 'Fundo restaurado nesta sessão; não foi possível salvar a preferência.'
        state.appearance_revision += 1
        state.background_upload_revision += 1
        st.rerun()


def background_css(mode, image, dark_theme=False):
    image_url = background_data(image)
    if mode == "Imagem personalizada" and image_url:
        overlay = "#111A16d9" if dark_theme else "#F5F3EDe6"
        return f"background-image:linear-gradient({overlay},{overlay}),url('{image_url}');background-size:cover;background-position:center;"
    return f"background-color:{palette(dark_theme)['background']};background-image:none;"


def show_portrait(category):
    path = ROOT / "assets/bobby-qualities.png"
    if not path.is_file():
        return
    category = canonical_category(category)
    portraits = {'brilliant': 1, 'best': 2, 'excellent': 4,
                 'good': 5, 'inaccuracy': 6, 'mistake': 7, 'blunder': 9}
    index = portraits.get(category, 0)
    label = CATEGORIES[category].label if category in CATEGORIES else 'Aguardando avaliação'
    data = portrait_data(str(path), path.stat().st_mtime)
    st.html(f'<div role="img" aria-label="Bobby Fischer: {label}" style="width:100%;max-width:140px;'
            f'aspect-ratio:1;border-radius:8px;background-image:url(data:image/png;base64,{data});'
            f'background-size:500% 200%;background-position:{index % 5 * 25}% {index // 5 * 100}%"></div>')


@st.cache_resource
def workers():
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="chess-review")


cached_history = st.cache_data(ttl=900, max_entries=32, show_spinner=False)(fetch_recent_games)
cached_dashboard_history = st.cache_data(ttl=900, max_entries=16, show_spinner=False)(fetch_dashboard_games)


def current_game(pgn):
    """Session games may be empty or start from a FEN."""
    return chess.pgn.read_game(StringIO(pgn)) or chess.pgn.Game()


def cancel_analysis():
    state = st.session_state
    if state.analysis_cancel:
        state.analysis_cancel.set()
    if record := state.jobs.pop("full", None):
        record[1].cancel()


def reset_game(game, accuracies=None):
    state = st.session_state
    cancel_analysis()
    state.job_errors = {}
    state.analysis_generation += 1
    state.board_revision += 1
    state.explanations = {}
    state.book_references = {}
    state.loaded_analysis = None
    state.study_open = state.analysis_requested = False
    state.analysis_options_open = False
    state.quick_answer = None
    state.navigation_ack = 0
    state.game, state.ply, state.reviews = str(game), 0, {}
    state.official_accuracies = {side: float(value) for side, value in (accuracies or {}).items()
                               if side in {"white", "black"} and isinstance(value, (int, float))
                               and not isinstance(value, bool) and 0 <= value <= 100}


def go_tab(name):
    state = st.session_state
    state.requested_page = name


def tab_changed():
    state = st.session_state
    name = state.main_view
    if name != state.active_tab:
        state.tab_history.append(state.active_tab)
    state.active_tab = name
    state.analysis_workspace_open = name == "Análise"


def go_back():
    state = st.session_state
    if state.tab_history:
        state.requested_page = state.tab_history[-1]
        state.going_back = True


def board_changed():
    event = st.session_state.interactive_board.move
    if not isinstance(event, dict):
        return
    state = st.session_state
    if event.get("revision") != state.board_revision:
        return
    state.board_needs_app_rerun = True
    state.board_revision += 1
    try:
        state.navigation_ack = 0
        pgn, ply = play_move(state.game, event.get('ply', state.ply), event["uci"], event["fen"])
        if pgn != state.game:
            cancel_analysis()
            state.analysis_requested = False
            state.official_accuracies = {}
            state.explanations, state.reviews = {}, {}
            state.book_references = {}
            state.loaded_analysis = None
            state.analysis_generation += 1
        state.game, state.ply = pgn, ply
    except (KeyError, ValueError) as error:
        state.move_error = str(error)


def keyboard_navigate():
    state = st.session_state
    event = state.interactive_board.navigate
    total = len(list(current_game(state.game).mainline_moves()))
    if (isinstance(event, dict) and type(event.get('to')) is int
            and event.get('epoch') == navigation_epoch()
            and type(event.get('sequence')) is int and event['sequence'] > state.navigation_ack):
        state.ply = max(0, min(total, event['to']))
        state.navigation_ack = event['sequence']


def navigation_epoch():
    return sha256(st.session_state.game.encode()).hexdigest() + ':' + str(st.session_state.board_revision)


def select_history_game():
    state = st.session_state
    index = state.history_choice
    if isinstance(index, int) and 0 <= index < len(state.history_games):
        item = state.history_games[index]
        try:
            game = read_games(item["pgn"])[0]
            reset_game(game, item.get("accuracies"))
            state.ply = len(list(game.mainline_moves()))
        except ValueError as error:
            state.history_error = str(error)


def select_recent_game():
    state = st.session_state
    event = state.recent_games.select
    history = recent_eight(state.history_games)
    if (not isinstance(event, dict) or event.get('revision') != history_revision(state.history_games)
            or type(event.get('index')) is not int or not 0 <= event['index'] < len(history)):
        return
    item = history[event['index']]
    try:
        game = read_games(item['pgn'])[0]
        reset_game(game, item.get('accuracies'))
        state.ply = len(list(game.mainline_moves()))
        state.analysis_options_open = event.get('action') == 'analyse'
        go_tab('Análise')
    except ValueError as error:
        state.history_error = str(error)


def free_board():
    reset_game(chess.pgn.Game())
    go_tab('Análise')


def render_home():
    state = st.session_state
    st.subheader('Últimas 8 partidas', width='stretch')
    if not state.archive_user:
        st.info('Entre com seu usuário do Chess.com no menu lateral para carregar suas últimas partidas.')
    elif not state.history_games:
        if state.history_loaded_user != state.archive_user:
            st.caption('Carregando suas partidas em segundo plano…')
        elif not state.get('history_error'):
            st.info('Nenhuma partida de xadrez encontrada no histórico carregado.')
    recent_games(state.history_games, state.archive_user, state.recent_accuracies, dark_theme, select_recent_game)


def render_performance(history, username, dark=False, *, context='painel', compact=False):
    render_comparative_chart(history, username, dark, context=context, compact=compact,
                             plan=state.get('prep_plan'))


def queue_job(slot, key, function, *args):
    record = st.session_state.jobs.get(slot)
    if record and record[0] == key:
        return
    if record:
        record[1].cancel()
    if slot in {'full', 'accuracy'}:
        cancel_key = 'analysis_cancel' if slot == 'full' else 'accuracy_cancel'
        if st.session_state[cancel_key]:
            st.session_state[cancel_key].set()
        st.session_state[cancel_key] = Event()
        args = (*args, st.session_state[cancel_key])
    st.session_state.jobs[slot] = (key, workers().submit(function, *args))


@st.fragment(run_every=0.5)
def poll_jobs():
    state = st.session_state
    changed = False
    for slot, (key, future) in list(state.jobs.items()):
        if not future.done():
            continue
        del state.jobs[slot]
        changed = True
        try:
            result = future.result()
            if slot == "full" and key == analysis_key():
                state.reviews = result["reviews"]
                state.explanations = result["explanations"]
                state.book_references = result["references"]
                state.loaded_analysis = key
                try:
                    save_game_quality(current_game(state.game), state.reviews)
                except OSError:
                    state.quality_save_error = 'A análise está pronta, mas não foi possível salvar o resumo de desempenho.'
            elif slot == "puzzle" and key == state.puzzle_request:
                state.puzzle, *state.puzzle_buffer = result
                reset_puzzle()
            elif slot == "puzzle_next" and key == state.puzzle_request:
                occupied = {p.id for p in state.puzzle_buffer} | set(state.puzzle_seen)
                if state.puzzle:
                    occupied.add(state.puzzle.id)
                if result.id in occupied:
                    raise ValueError("O serviço repetiu um exercício. Tente preparar outro.")
                state.puzzle_buffer.append(result)
                if state.puzzle_waiting:
                    advance_puzzle()
            elif slot == "rating" and key == state.archive_user:
                state.player_rating, state.rating_label = result
                state.rating_user = key
            elif slot == 'history' and key == state.archive_user:
                state.history_games = result
                state.history_loaded_user = key
                state.pop('history_error', None)
                if state.get('history_save_user') == key:
                    state.pop('history_save_user', None)
                    try:
                        save_user(key)
                    except OSError:
                        state.login_notice = 'Usuário carregado nesta sessão; não foi possível salvar a preferência.'
            elif slot == 'accuracy':
                state.recent_accuracies[key[0]] = result
            elif slot == 'dashboard_history' and key[0] == state.archive_user:
                state.dashboard_history_games = result
                state.dashboard_history_key = key
            state.job_errors.pop((slot, key), None)
        except Exception as error:
            state.job_errors[(slot, key)] = str(error)
            if slot == "rating" and key == state.archive_user:
                state.rating_user = key
            elif slot == 'history' and key == state.archive_user:
                state.history_loaded_user = key
                state.history_error = str(error)
            while len(state.job_errors) > 32:
                state.job_errors.pop(next(iter(state.job_errors)))
    if changed:
        st.rerun()


def analysis_key():
    state = st.session_state
    return state.game, state.analysis_signature, state.analysis_generation


def ensure_analysis():
    state = st.session_state
    if not (state.study_open or state.analysis_requested):
        return
    key = analysis_key()
    if state.loaded_analysis == key or ("full", key) in state.job_errors:
        return
    record = state.jobs.get('full')
    if record and record[0] == key:
        return
    # Indexing the opening catalogue and uploaded books belongs to analysis,
    # not to opening the home page or navigating between unrelated sections.
    book, study, book_errors = load_library(files, book_plies)
    for error in book_errors:
        st.warning(error)
    if engine_path and state.analysis_requested:
        queue_job("full", key, analyse_with_books, current_game(state.game), engine_path,
                  state.player_rating or 1500, book, study, state.quality)
    elif state.study_open:
        queue_job("full", key, prepare_explanations, current_game(state.game), study)


def jump_to_ply(ply):
    total = len(list(current_game(st.session_state.game).mainline_moves()))
    st.session_state.ply = max(0, min(total, ply))
    st.session_state.board_revision += 1
    st.session_state.navigation_ack = 0


def render_moves(prefix):
    state = st.session_state
    game = current_game(state.game)
    moves_tab, pgn_tab = st.tabs(["Lances", "PGN"])
    with moves_tab:
        st.button("Posição inicial", key=f"{prefix}_start", on_click=jump_to_ply, args=(0,))
        with st.container(height=320, key=f"{prefix}_moves"):
            white, black = st.columns(2)
            white.markdown("**Brancas**")
            black.markdown("**Pretas**")
            board = game.board()
            rows = {}
            for ply, move in enumerate(game.mainline_moves(), 1):
                number, side = board.fullmove_number, board.turn
                review = state.reviews.get(ply)
                category = CATEGORIES.get(review.category) if review else None
                quality = f" {category.symbol} {category.label}" if category else ""
                label = f"{number}{'.' if side else '...'} {board.san(move)}{quality}"
                rows.setdefault(number, {})[side] = (ply, label, review.category if category else None)
                board.push(move)
            for pair in rows.values():
                for col, side in zip(st.columns(2), (chess.WHITE, chess.BLACK)):
                    if side in pair:
                        ply, label, category_key = pair[side]
                        with col.container(key=f"move_quality_{category_key or 'pending'}_{prefix}_{ply}"):
                            col_help = CATEGORIES[category_key].description if category_key else "Lance ainda não avaliado."
                            st.button(label, key=f"{prefix}_{ply}", type="primary" if state.ply == ply else "secondary",
                                      on_click=jump_to_ply, args=(ply,), width="stretch", help=col_help)
                    else:
                        col.write("—")
        classification_legend()
    with pgn_tab:
        pgn_clipboard(export_review(game, list(state.reviews.values())) if state.reviews else str(game),
                      key=f"{prefix}_copy", dark=state.theme_mode == "Escuro")


def toggle_study(opened):
    st.session_state.study_open = opened


def request_analysis():
    st.session_state.analysis_options_open = True


def start_analysis():
    state = st.session_state
    cancel_analysis()
    state.analysis_generation += 1
    state.loaded_analysis = None
    state.reviews, state.explanations, state.book_references = {}, {}, {}
    state.quality = state.analysis_depth
    state.analysis_requested = True
    state.analysis_request_pending = True
    state.analysis_options_open = False


def change_tactic_menu():
    choose_theme(st.session_state.tactic_menu, preserve_range=True)


def render_history():
    state = st.session_state
    def label(index, history=state.history_games):
        item = history[index]
        date = datetime.fromtimestamp(item.get("end_time", 0), timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        return f"{date} · {item.get('white', {}).get('username', '?')} × {item.get('black', {}).get('username', '?')}"
    st.selectbox("Escolher partida no histórico", range(len(state.history_games)), index=None,
                 format_func=label, placeholder="Escolha uma partida" if state.history_games else "Entre com seu usuário do Chess.com",
                 key="history_choice", on_change=select_history_game, disabled=not state.history_games)


@st.fragment
def render_main_board():
    state = st.session_state
    if state.pop('board_needs_app_rerun', False):
        st.rerun()
    game = current_game(state.game)
    moves = list(game.mainline_moves())
    board = game.board()
    state.ply = max(0, min(state.ply, len(moves)))
    for move in moves[:state.ply]:
        board.push(move)
    last = board.peek() if board.move_stack else None
    review = state.reviews.get(state.ply)
    category = CATEGORIES.get(canonical_category(review.category)) if review else None
    ready = state.loaded_analysis == analysis_key()
    state.last_explanation = state.explanations.get(state.ply, '') if ready and state.study_open else ''
    interactive_board(board, flip=state.flip, last_move=last,
                      category=category if state.show_quality else None,
                      on_move=board_changed, ply=state.ply, total=len(moves), on_navigate=keyboard_navigate,
                      revision=state.board_revision, pgn=state.game, epoch=navigation_epoch(), navigation_ack=state.navigation_ack,
                      study=state.study_open, explanations=state.explanations if ready else None,
                      reviews=state.reviews if state.show_quality else {}, dark=state.theme_mode == 'Escuro',
                      table=state.show_table,
                      expanded=state.active_tab == 'Análise',
                      analysis_effects=state.active_tab == 'Análise' and state.analysis_requested and ready)


def render_board():
    state = st.session_state
    ensure_analysis()
    game = current_game(state.game)
    moves = list(game.mainline_moves())
    state.ply = max(0, min(state.ply, len(moves)))
    board = game.board()
    for move in moves[:state.ply]:
        board.push(move)
    last = board.peek() if board.move_stack else None
    review = state.reviews.get(state.ply)
    category = review.category if review else None
    ready = state.loaded_analysis == analysis_key()
    with st.container(horizontal=True, vertical_alignment='center', key='analysis_toolbar'):
        st.button("Analisar Partida", on_click=request_analysis, icon=":material/analytics:", type='primary')
        st.button("Fechar estudo" if state.study_open else "Estudar", on_click=toggle_study,
                  args=(not state.study_open,), icon=":material/menu_book:", key="study_toggle", width="content")
        with st.popover("Anotações", icon=":material/description:"):
            render_moves("panel")
    if state.analysis_options_open:
        with st.form("analysis_depth_form"):
            labels = {"Rápida": "Análise Rápida", "Equilibrada": "Análise Mediana", "Profunda": "Análise Profunda"}
            st.radio("Profundidade da análise", list(labels), format_func=labels.get,
                     index=list(labels).index(state.quality), key="analysis_depth")
            st.caption("Rápida: menor tempo de cálculo. Mediana: equilíbrio entre tempo e profundidade. Profunda: busca mais detalhada.")
            st.form_submit_button("Iniciar análise", on_click=start_analysis, type='primary')
    if state.analysis_requested:
        if ready and engine_path:
            st.success("Análise concluída. As avaliações estão disponíveis nos lances e no PGN.")
        else:
            with st.container(border=True, key='analysis_summary_pending'):
                st.subheader('Resumo da qualidade dos lances')
                if not engine_path:
                    st.info("Stockfish não encontrado. Instale em engines/ ou configure STOCKFISH_PATH para avaliar a partida.")
                elif ('full', analysis_key()) in state.job_errors:
                    st.caption('A análise não foi concluída. Tente novamente para preencher o resumo.')
                else:
                    st.caption('Analisando a partida… O resumo será preenchido quando o cálculo terminar.')
    render_history()
    state.last_explanation = state.explanations.get(state.ply, '') if ready and state.study_open else ''
    split_analysis = state.active_tab == 'Análise' and state.analysis_requested and ready and engine_path
    board_column, summary_column = st.columns([1.35, .85], gap='large') if split_analysis else (st.container(), None)
    with board_column:
        with st.container(key="centered_board"):
            render_main_board()
    if summary_column is not None:
        with summary_column:
            render_analysis_summary(state.reviews, state.official_accuracies, dark=state.theme_mode == 'Escuro')
    if error := state.pop("move_error", None):
        st.error(error)
    if "full" in state.jobs:
        st.info("Preparando todas as explicações da partida. Você já pode navegar pelo tabuleiro…")
    if error := state.job_errors.get(("full", analysis_key())):
        st.error(error)
        if st.button("Tentar análise novamente"):
            state.analysis_generation += 1
            st.rerun()
    if state.show_quality:
        classification_legend()


def render_question_box():
    state = st.session_state
    if state.active_tab == "Tático" and state.puzzle:
        board = chess.Board(state.puzzle.fen)
        for move in state.puzzle.solution[:state.puzzle_progress]:
            board.push_uci(move)
    elif state.active_tab == "Estudo com livros":
        board = current_study_board()
    else:
        board = current_game(state.game).board()
        for move in list(current_game(state.game).mainline_moves())[:state.ply]:
            board.push(move)
    with st.container(key="question_launcher"):
        with st.popover("Pergunta rápida", icon=":material/search:", key="question_popover", width=48):
            st.markdown("**Pergunte sobre a posição atual**")
            with st.form("quick_question_form"):
                question = st.text_input("Pergunta rápida", placeholder="Ex.: Posso jogar Nf3?", max_chars=1000)
                submitted = st.form_submit_button("Perguntar")
            if submitted:
                started = perf_counter()
                state.quick_answer = {'fen': board.fen(), 'text': answer_question(question, board),
                                      'seconds': perf_counter()-started}
            if state.quick_answer and state.quick_answer['fen'] == board.fen():
                st.write(state.quick_answer['text'])
                st.caption(f"Posição conferida · resposta local em {state.quick_answer['seconds']:.2f} s")


def reset_puzzle():
    state = st.session_state
    state.puzzle_progress, state.puzzle_message = 0, ""
    state.puzzle_waiting, state.puzzle_notice = False, ""
    state.puzzle_revision += 1


def puzzle_changed():
    state = st.session_state
    event = state.puzzle_board.move
    if not isinstance(event, dict) or not state.puzzle or event.get("revision") != state.puzzle_revision:
        return
    try:
        previous = state.puzzle_progress
        state.puzzle_progress, state.puzzle_message = solve_move(state.puzzle, state.puzzle_progress,
                                                               event["uci"], event["fen"])
        state.forge_event += 1
        if state.puzzle_progress == len(state.puzzle.solution):
            identifier = state.puzzle.id
            if identifier not in state.puzzle_failed_ids and identifier not in state.puzzle_rewarded_ids:
                state.forge_result = "correct"
                state.forge_sharpness = min(100, state.forge_sharpness + 12)
                state.puzzle_rewarded_ids.add(identifier)
            else:
                state.forge_result = "recovered"
        elif state.puzzle_progress > previous:
            state.forge_result = "progress"
        else:
            state.forge_result = "wrong"
            state.puzzle_failed_ids.add(state.puzzle.id)
        if state.puzzle_progress == len(state.puzzle.solution):
            advance_puzzle()
    except (KeyError, ValueError) as error:
        state.puzzle_message = str(error)
    finally:
        state.puzzle_revision += 1


def advance_puzzle():
    state = st.session_state
    if state.puzzle_buffer:
        state.puzzle_seen = (state.puzzle_seen + [state.puzzle.id])[-100:]
        state.puzzle = state.puzzle_buffer.pop(0)
        state.puzzle_waiting = False
        reset_puzzle()
        state.puzzle_notice = "Tático resolvido! Novo exercício carregado."
    else:
        state.puzzle_waiting = True
        state.puzzle_notice = "Tático resolvido! Aguardando a conexão para preparar outro exercício."


def choose_theme(theme, preserve_range=True):
    state = st.session_state
    state.tactic_theme = theme
    if theme is not None:
        state.tactic_menu = theme
    state.puzzle = None
    state.puzzle_request = None
    state.puzzle_nonce += 1
    state.puzzle_notice = ""
    state.puzzle_buffer, state.puzzle_seen, state.puzzle_waiting = [], [], False
    reset_puzzle()
    if not preserve_range:
        for key in ("rating_min", "rating_max"):
            state.pop(key, None)
    for slot in ("puzzle", "puzzle_next"):
        if record := state.jobs.pop(slot, None):
            record[1].cancel()


@st.fragment
def render_tactics():
    state = st.session_state
    if state.tactic_theme is None:
        with st.container(border=True, key="tactic_showcase"):
            tactic_demo(dark=state.theme_mode == "Escuro")
        st.subheader("Escolha um tema tático")
        with st.container(key="tactic_cards"):
            columns = st.columns(3)
            for index, (label, theme) in enumerate(THEMES.items()):
                with columns[index % 3], st.container(border=True, key=f"tactic_card_{theme}"):
                    st.image(theme_art(theme), width="stretch")
                    st.button(label, key=f"theme_{theme}", width="stretch", on_click=choose_theme, args=(theme,))
        return
    st.button("Escolher outro tema", icon=":material/arrow_back:", on_click=choose_theme, args=(None,))
    theme_names = {theme: label for label, theme in THEMES.items()}
    st.selectbox("Tema tático", list(theme_names), index=list(theme_names).index(state.tactic_theme),
                 format_func=theme_names.get, key="tactic_menu", on_change=change_tactic_menu)
    if state.puzzle_notice:
        st.success(state.puzzle_notice)
    with st.expander("Faixa de rating · opcional"):
        start, end = st.columns(2)
        minimum = start.selectbox("Rating inicial", range(0, 4001, 100), index=None, key="rating_min", persist_state="session")
        maximum = end.selectbox("Rating final", range(0, 4001, 100), index=None, key="rating_max", persist_state="session")
        st.caption("Deixe os campos vazios para praticar sem filtro de rating.")
    minimum = 0 if minimum is None else minimum
    maximum = 4000 if maximum is None else maximum
    if minimum > maximum:
        state.puzzle_request = None
        st.error("O rating inicial deve ser menor ou igual ao final.")
        return
    st.caption("Sem filtro de rating" if (minimum, maximum) == (0, 4000) else f"Faixa: {minimum}–{maximum}")
    request_key = state.tactic_theme, minimum, maximum, state.puzzle_nonce
    if request_key != state.puzzle_request:
        for slot in ("puzzle", "puzzle_next"):
            if record := state.jobs.pop(slot, None):
                record[1].cancel()
        state.puzzle_request, state.puzzle = request_key, None
        state.puzzle_buffer, state.puzzle_seen, state.puzzle_waiting = [], [], False
        state.puzzle_notice = ""
        reset_puzzle()
        queue_job("puzzle", request_key, fetch_puzzle_pair, state.tactic_theme, minimum, maximum)
    if "puzzle" in state.jobs:
        st.info("Preparando os primeiros táticos…")
    if error := state.job_errors.get(("puzzle", request_key)):
        st.error(error)
        if st.button("Tentar busca novamente"):
            state.puzzle_nonce += 1
            st.rerun()
    if not state.puzzle:
        return
    prefetch_error = state.job_errors.get(("puzzle_next", request_key))
    if len(state.puzzle_buffer) < 2 and not prefetch_error:
        excluded = {state.puzzle.id} | {p.id for p in state.puzzle_buffer} | set(state.puzzle_seen)
        queue_job("puzzle_next", request_key, fetch_puzzle_range, state.tactic_theme, minimum, maximum, excluded)
    if prefetch_error:
        st.warning(f"Não foi possível preparar outro exercício: {prefetch_error}")
        if st.button("Preparar próximo novamente"):
            state.job_errors.pop(("puzzle_next", request_key), None)
            st.rerun()
    puzzle = state.puzzle
    board = chess.Board(puzzle.fen)
    player = board.turn
    for move in puzzle.solution[:state.puzzle_progress]:
        board.push_uci(move)
    done = state.puzzle_progress == len(puzzle.solution)
    left, right = st.columns([1.15, 1])
    with left:
        interactive_board(board, flip=not player, on_move=puzzle_changed, key="puzzle_board", disabled=done,
                          revision=state.puzzle_revision, dark=state.theme_mode == "Escuro", table=state.show_table,
                          last_move=board.peek() if board.move_stack else chess.Move.from_uci(puzzle.last_move) if puzzle.last_move else None)
    with right:
        tactics_forge(state.forge_event, state.forge_result, state.forge_sharpness,
                     dark=state.theme_mode == "Escuro", speak=state.forge_voice)
        st.subheader("Tático resolvido!" if done else f"Jogam as {'brancas' if player else 'pretas'}")
        st.caption(f"Rating Lichess: {puzzle.rating}")
        if state.puzzle_message:
            st.write(state.puzzle_message)
        if not done and st.button("Dica"):
            st.info(f"Observe a peça em {puzzle.solution[state.puzzle_progress][:2]}.")
        st.button("Recomeçar tático", on_click=reset_puzzle)
        st.caption("Próximo exercício pronto · avanço automático ao resolver." if state.puzzle_buffer
                   else "Preparando o próximo exercício em segundo plano…")
        st.caption("Arraste com o botão direito para desenhar setas. Repita a seta para apagá-la.")
        st.caption("Fonte: banco público de táticos Lichess · CC0.")


if '_initial_appearance' not in st.session_state:
    st.session_state._initial_appearance = load_appearance()
    st.session_state._initial_background = load_saved_background(st.session_state._initial_appearance)
appearance = st.session_state._initial_appearance
saved_background = st.session_state._initial_background
saved_theme = appearance.get('theme') if appearance.get('theme') in {'Claro', 'Escuro'} else 'Claro'
saved_background_mode = appearance.get('background_mode')
if saved_background_mode not in {'Claro', 'Escuro', 'Imagem personalizada'}:
    saved_background_mode = 'Imagem personalizada' if saved_background else saved_theme

defaults = {"game": st.session_state.get('game') or (ROOT / "examples/partida.pgn").read_text(encoding="utf-8"), "ply": 0,
            "reviews": {}, "archive_user": st.session_state.archive_user if 'archive_user' in st.session_state else load_saved_user(), "history_loaded_user": None,
            "history_games": [], "official_accuracies": {},
            "dashboard_history_games": [], "dashboard_history_key": None,
            "recent_accuracies": {}, "accuracy_cancel": None,
            "show_quality": True, "flip": False, "quality": "Equilibrada",
            "analysis_generation": 0, "board_revision": 0, "explanations": {}, "loaded_analysis": None, "analysis_signature": None,
            "analysis_cancel": None, "book_references": {}, "study_files": (), "study_upload_revision": 0,
            "jobs": {}, "job_errors": {},
            "last_explanation": "", "active_tab": "Partida", "tab_history": [], "main_view": "Partida",
            "analysis_workspace_open": False, "puzzle": None, "puzzle_progress": 0,
            "puzzle_message": "", "profile_bytes": None,
            "puzzle_revision": 0, "puzzle_request": None, "puzzle_nonce": 0, "tactic_theme": None,
            "player_rating": None, "rating_label": "", "rating_user": None,
            "background_image": saved_background, "background_mode": saved_background_mode,
            "theme_mode": saved_theme,
            "background_upload_revision": 0, "appearance_revision": 0,
            "study_open": False, "analysis_requested": False, "quick_answer": None, "navigation_ack": 0,
            "analysis_options_open": False, "puzzle_notice": "", "study_entry": 0,
            "show_table": appearance.get('show_table', True) is not False,
            "forge_voice": True,
            "puzzle_failed_ids": set(), "puzzle_rewarded_ids": set(),
            "puzzle_buffer": [], "puzzle_seen": [], "puzzle_waiting": False,
            "forge_event": 0, "forge_result": "idle", "forge_sharpness": 0}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
state = st.session_state
if not state.get('_desktop_entry_handled'):
    state._desktop_entry_handled = True
    if st.query_params.get('view') == 'aberturas':
        state.active_tab = state.main_view = 'Aberturas'
if state.archive_user == 'demo_import_test' and not os.environ.get('ACERVO_USER_PREFERENCE'):
    state.archive_user, state.history_games, state.history_loaded_user = '', [], None
    state.pop('history_error', None)
# Preserve settings while their widgets are hidden on another tab.
for key in ("quality", "flip", "show_quality", "review_side", "show_table", "book_tool", "book_flip", "reader_page_input"):
    if key in state:
        state[key] = state[key]
if isinstance(state.reviews, list):
    state.reviews = {r.ply: r for r in state.reviews}
for review in state.reviews.values():
    review.category = canonical_category(review.category)
    review.explanation = canonical_explanation(review.explanation)
state.explanations = {ply: canonical_explanation(text) for ply, text in state.explanations.items()}

dark_theme = state.theme_mode == "Escuro"
apply_theme(dark_theme)
st.html(f"<style>.stApp {{{background_css(state.background_mode, state.background_image, dark_theme)}background-attachment:fixed}}</style>")
if state.get("theme_save_error"):
    st.caption(state.pop("theme_save_error"))
game = current_game(state.game)

def change_user():
    for slot in ('history', 'rating', 'dashboard_history'):
        previous = state.jobs.pop(slot, None)
        if previous:
            previous[1].cancel()
    state.pop('history_save_user', None)
    try:
        USER_PREFERENCE.unlink(missing_ok=True)
    except OSError:
        pass
    state.archive_user, state.history_loaded_user, state.history_games = "", None, []
    state.dashboard_history_games, state.dashboard_history_key = [], None
    state.player_rating, state.rating_user, state.rating_label = None, None, ""
    state.profile_bytes = None
    state.pop('history_error', None)
    state.pop('chesscom_login_username', None)
    state.history_choice = None
    state.prep_selected_openings = []


with st.sidebar:
    brand()
    with st.container(horizontal=True, vertical_alignment='center', key='sidebar_profile'):
        with st.container(width=72):
            profile_avatar(state.profile_bytes, dark=dark_theme)
        with st.container(width='stretch'):
            st.markdown(f"**{state.archive_user or 'Jogador'}**")
            st.caption(f"{state.player_rating} · {state.rating_label}" if state.player_rating else 'Chess.com · conta local')
    with st.popover('Minha conta', icon=':material/account_circle:', width='stretch'):
        if state.archive_user:
            st.markdown(f"**{state.archive_user}**")
            st.caption(f"Rating {state.player_rating} · {state.rating_label}" if state.player_rating else 'Rating não publicado')
            st.link_button('Abrir perfil Chess.com', f'https://www.chess.com/member/{state.archive_user}',
                           icon=':material/open_in_new:', width='stretch')
            st.button('Trocar usuário', key='change_user', icon=':material/switch_account:',
                      width='stretch', on_click=change_user)
        else:
            st.caption('Entre para carregar seu histórico e suas partidas.')
            with st.form('chesscom_user'):
                username = st.text_input('Usuário do Chess.com', placeholder='Seu usuário', key='chesscom_login_username')
                fetch = st.form_submit_button('Entrar', type='primary', width='stretch')
            if fetch:
                try:
                    user = normalize_username(username)
                    state.archive_user, state.history_games, state.history_loaded_user = user, [], None
                    state.history_save_user = user
                    state.pop('history_error', None)
                    state.history_choice = None
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    if state.archive_user and state.history_loaded_user != state.archive_user:
        queue_job('history', state.archive_user, cached_history, state.archive_user)
    if notice := state.pop('login_notice', None):
        st.caption(notice)
    if state.get('history_error'):
        st.error(f'Histórico Chess.com: {state.history_error}')
        if st.button('Tentar novamente', key='retry_history'):
            state.history_loaded_user = None
            state.pop('history_error', None)
            st.rerun()
    sidebar_navigation = st.container(key='sidebar_navigation')
    st.divider()
    with st.expander('Configurações', icon=':material/settings:'):
        st.segmented_control('Tema', ['☀ Claro', '☾ Escuro'],
                             default='☾ Escuro' if dark_theme else '☀ Claro', key='theme_selector',
                             on_change=theme_selector_changed)
        background_settings()
        with st.popover('Livros', icon=':material/library_books:', width='stretch'):
            uploads = st.file_uploader('Adicionar livros', type=['pgn', 'bin', 'pdf', 'txt', 'md'],
                                       accept_multiple_files=True, key='books', max_upload_size=200)
            book_plies = st.slider('Profundidade do livro', 4, 80, 40, step=2)
            st.caption('Livros e fontes para estudo e análise.')
        st.markdown('**Tabuleiro e treino**')
        st.toggle('Mostrar qualidade do lance', key='show_quality')
        st.toggle('Pretas na parte inferior', key='flip')
        st.toggle('Mostrar mesa sob o tabuleiro', key='show_table', on_change=table_preference_changed)
        st.toggle('Voz do ferreiro', key='forge_voice')
        st.download_button('Baixar partida PGN', export_review(game, list(state.reviews.values())) if state.reviews else str(game),
                           file_name='partida.pgn', mime='application/x-chess-pgn', icon=':material/download:')

    if state.archive_user and state.rating_user != state.archive_user:
        queue_job('rating', state.archive_user, fetch_rating, state.archive_user)
files = merge_books(tuple((item.name, item.getvalue()) for item in uploads), state.study_files)
library_digest = sha256()
for name, data in files:
    library_digest.update(name.encode())
    library_digest.update(sha256(data).digest())
library_id = library_digest.hexdigest()
engine_path = find_engine()
signature = (library_id, book_plies, engine_path, state.quality, state.player_rating or 1500)
if state.analysis_signature != signature:
    cancel_analysis()
    state.reviews = {}
    state.analysis_signature = signature
    state.explanations = {}
    state.book_references = {}
    state.loaded_analysis = None
    # Changing books, rating or engine does not authorize another engine run.
    # start_analysis sets quality before this signature is recomputed.
    if not state.get('analysis_request_pending'):
        state.analysis_requested = False
state.pop('analysis_request_pending', None)
game = current_game(state.game)

def render_workspace(name):
    if name not in {'Partida', 'Desempenho'} and (name != 'Preparo' or not state.get('prep_plan')):
        page_heading(name)
    if name == 'Partida':
        render_home()
    elif name == 'Desempenho':
        day = local_today()
        dashboard_key = (state.archive_user, day.isoformat())
        complete = state.dashboard_history_key == dashboard_key
        if state.archive_user and not complete:
            error = state.job_errors.get(('dashboard_history', dashboard_key))
            if error:
                st.warning(f'Não foi possível carregar o período completo: {error}')
            else:
                queue_job('dashboard_history', dashboard_key, cached_dashboard_history,
                          state.archive_user, (day - timedelta(days=29)).strftime('%Y/%m'), day.strftime('%Y/%m'))
                st.caption('Carregando o histórico completo dos últimos 30 dias em segundo plano…')
        if state.loaded_analysis and state.reviews:
            try:
                save_game_quality(current_game(state.game), state.reviews)
            except OSError:
                state.quality_save_error = 'Não foi possível salvar o resumo desta análise.'
        render_dashboard(state.dashboard_history_games if complete else state.history_games,
                         state.archive_user, dark_theme, complete=complete)
        if state.get('quality_save_error'):
            st.caption(state.quality_save_error)
    elif name == "Análise":
        st.button('Nova partida · jogar livremente', on_click=free_board, icon=':material/add:')
        with st.expander("Carregar PGN ou FEN"):
            upload = st.file_uploader("Arquivo PGN", type="pgn", key="analysis_game_upload")
            text = st.text_area("Cole o PGN", key="analysis_game_text")
            if st.button("Carregar PGN e analisar"):
                try:
                    source = decode_text(upload.getvalue()) if upload else text
                    imported = read_games(source)[0]
                    reset_game(imported)
                    state.ply = len(list(imported.mainline_moves()))
                    state.analysis_options_open = True
                    st.rerun()
                except (ValueError, IndexError, UnicodeError) as error:
                    st.error(f"PGN inválido: {error}")
            fen = st.text_input("Posição FEN", placeholder=chess.STARTING_FEN)
            if st.button("Carregar FEN e analisar"):
                try:
                    position = chess.Board(fen.strip() or chess.STARTING_FEN)
                    if not position.is_valid():
                        raise ValueError("Posição ilegal")
                    imported = chess.pgn.Game()
                    imported.setup(position)
                    reset_game(imported)
                    state.analysis_options_open = True
                    st.rerun()
                except ValueError:
                    st.error("FEN inválida: confira a disposição das peças, o lado a jogar e os direitos de roque.")
        render_board()
    elif name == "Anotações":
        render_moves("notes")
        render_board()
    elif name == "Estudo com livros":
        render_study(files, dark_theme, state.show_table)
    elif name == "Preparo":
        render_preparation(state.history_games, state.archive_user, engine_path, dark_theme, state.show_table)
    elif name == "Aberturas":
        from opening_practice import render_opening_practice
        render_opening_practice(state.archive_user, dark_theme)
    else:
        render_tactics()

from functools import partial

page_icons = {"Partida": "grid_on", "Desempenho": "monitoring", "Análise": "analytics", "Anotações": "notes",
              "Estudo com livros": "menu_book", "Tático": "psychology", "Preparo": "edit_note", "Aberturas": "school"}
page_paths = {"Partida": "partida", "Desempenho": "desempenho", "Análise": "analise", "Anotações": "anotacoes",
              "Estudo com livros": "estudo", "Tático": "tatico", "Preparo": "preparo", "Aberturas": "aberturas"}
pages = {name: st.Page(partial(render_workspace, name), title=name,
                       icon=f":material/{icon}:", url_path=page_paths[name], default=name == "Partida")
         for name, icon in page_icons.items()}
selected_page = st.navigation(list(pages.values()), position="hidden")
with sidebar_navigation:
    for name, page in pages.items():
        if name != 'Anotações':
            st.page_link(page, label='Biblioteca' if name == 'Estudo com livros' else name,
                         icon=f":material/{page_icons[name]}:")
    st.divider()
    if state.archive_user and st.button('Atualizar partidas', icon=':material/refresh:', width='stretch'):
        cached_history.clear()
        cached_dashboard_history.clear()
        state.dashboard_history_key = None
        state.job_errors = {key: value for key, value in state.job_errors.items() if key[0] != 'dashboard_history'}
        previous_dashboard = state.jobs.pop('dashboard_history', None)
        if previous_dashboard:
            previous_dashboard[1].cancel()
        previous = state.jobs.pop('history', None)
        if previous:
            previous[1].cancel()
        state.history_loaded_user = None
        st.rerun()
    st.button('Nova partida', on_click=free_board, icon=':material/add:', width='stretch')
if not state.get('navigation_migrated'):
    state.navigation_migrated = True
    if state.main_view != 'Partida':
        state.requested_page = state.main_view
requested = state.pop('requested_page', None)
if requested in pages and requested != selected_page.title:
    st.switch_page(pages[requested])
if selected_page.title != state.active_tab:
    going_back = state.pop('going_back', False)
    if going_back:
        if state.tab_history and state.tab_history[-1] == selected_page.title:
            state.tab_history.pop()
    else:
        state.tab_history.append(state.active_tab)
state.active_tab = state.main_view = selected_page.title
state.analysis_workspace_open = selected_page.title == 'Análise'
if selected_page.title != 'Preparo':
    pause_preparation()
if 'accuracy' in state.jobs:
    if state.accuracy_cancel:
        state.accuracy_cancel.set()
    state.jobs.pop('accuracy')[1].cancel()
if state.tab_history:
    with st.sidebar:
        st.button("Voltar", icon=":material/arrow_back:", on_click=go_back, key="navigation_back")
page_chrome()
selected_page.run()
render_question_box()

poll_jobs()
