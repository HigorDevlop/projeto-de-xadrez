from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from io import StringIO
from pathlib import Path
from threading import Event
import base64
import json
import os

import chess
import chess.pgn
import streamlit as st

from chess_review import (BookIndex, CATEGORIES, decode_text,
                          export_review, read_games, player_accuracy)
from chesscom import fetch_recent_games, normalize_username, fetch_rating
from game_play import play_move
from interactive_board import interactive_board
from profile_avatar import profile_avatar
from stockfish_analysis import find_engine, analyse_with_books
from book_study import BookStudy
from tactic_art import theme_art
from tactics import THEMES, fetch_puzzle_range, solve_move
from tutor import load_passages, tutor_mood

ROOT = Path(__file__).resolve().parent
USER_PREFERENCE = Path(os.environ.get("ACERVO_USER_PREFERENCE", ROOT / ".streamlit/last_chesscom_user.json"))
APPEARANCE_PREFERENCE = Path(os.environ.get("ACERVO_APPEARANCE_PREFERENCE", ROOT / ".streamlit/appearance.json"))
st.set_page_config(page_title="Acervo • análise de xadrez", page_icon="♞", layout="wide", initial_sidebar_state="collapsed")


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


def save_theme(theme):
    APPEARANCE_PREFERENCE.parent.mkdir(parents=True, exist_ok=True)
    APPEARANCE_PREFERENCE.write_text(json.dumps({"theme": theme}), encoding="utf-8")


def choose_theme(theme):
    state = st.session_state
    state.theme_mode = theme
    try:
        save_theme(theme)
    except OSError:
        state.theme_save_error = "Tema aplicado nesta sessão; não foi possível salvá-lo neste computador."


def theme_selector_changed():
    choice = st.session_state.theme_selector
    if choice in {"☾ Escuro", "Escuro"}:
        choose_theme("Escuro")
    elif choice in {"☀ Claro", "Claro"}:
        choose_theme("Claro")


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


def background_css(mode, image, dark_theme=False):
    image_url = background_data(image)
    if mode == "Imagem personalizada" and image_url:
        overlay = "#1119232e" if dark_theme else "#0000001f"
        return f"background-image:linear-gradient({overlay},{overlay}),url('{image_url}');background-size:cover;background-position:center;"
    dark = mode == "Escuro"
    fill = "#18212b" if dark else "#efe9dc"
    pieces = "#f1d7a3" if dark else "#5b5145"
    pattern = base64.b64encode(f'''<svg xmlns="http://www.w3.org/2000/svg" width="260" height="220" viewBox="0 0 260 220">
<rect width="260" height="220" fill="{fill}"/>
<g fill="{pieces}" opacity=".2" font-family="serif" font-size="62" text-anchor="middle">
<text x="45" y="72">♞</text><text x="175" y="72">♜</text>
<text x="110" y="175">♛</text><text x="240" y="175">♟</text>
</g></svg>'''.encode()).decode()
    return f"background-image:url('data:image/svg+xml;base64,{pattern}');background-size:260px 220px;"


def show_portrait(category):
    path = ROOT / "assets/bobby-qualities.png"
    if not path.is_file():
        return
    keys = list(CATEGORIES)
    index = keys.index(category) if category in keys else 0
    label = CATEGORIES[keys[index]].label
    data = portrait_data(str(path), path.stat().st_mtime)
    st.html(f'<div role="img" aria-label="Bobby Fischer: {label}" style="width:100%;max-width:140px;'
            f'aspect-ratio:1;border-radius:8px;background-image:url(data:image/png;base64,{data});'
            f'background-size:500% 200%;background-position:{index % 5 * 25}% {index // 5 * 100}%"></div>')


@st.cache_resource
def workers():
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="chess-review")


cached_history = st.cache_data(ttl=900, max_entries=32, show_spinner=False)(fetch_recent_games)


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
    state.board_revision += 1
    try:
        pgn, ply = play_move(state.game, state.ply, event["uci"], event["fen"])
        if pgn != state.game:
            cancel_analysis()
            state.official_accuracies = {}
            state.explanations, state.reviews = {}, {}
            state.book_references = {}
            state.loaded_analysis = None
            state.analysis_generation += 1
        state.game, state.ply = pgn, ply
    except (KeyError, ValueError) as error:
        state.move_error = str(error)


def keyboard_navigate():
    event = st.session_state.interactive_board.navigate
    total = len(list(current_game(st.session_state.game).mainline_moves()))
    if isinstance(event, dict) and isinstance(event.get("to"), int):
        st.session_state.ply = max(0, min(total, event["to"]))


def select_history_game():
    state = st.session_state
    index = state.history_choice
    if isinstance(index, int) and 0 <= index < len(state.history_games):
        item = state.history_games[index]
        try:
            game = read_games(item["pgn"])[0]
            reset_game(game, item.get("accuracies"))
            state.ply = len(list(game.mainline_moves()))
            go_tab("Análise")
        except ValueError as error:
            state.history_error = str(error)


def render_review():
    state = st.session_state
    reviews = list(state.reviews.values())
    rows = ['<div class="review-row review-heading"><span></span><span>Brancas</span><span>Pretas</span></div>']
    for key, category in CATEGORIES.items():
        white = sum(r.category == key and r.side == 'Brancas' for r in reviews)
        black = sum(r.category == key and r.side == 'Pretas' for r in reviews)
        rows.append(f'<div class="review-row" aria-label="{category.label}: Brancas {white}, Pretas {black}" title="{category.label}">'
                    f'<span class="review-symbol" style="background:{category.color};color:{category.ink}">{category.symbol}</span>'
                    f'<span>{white}</span><span>{black}</span></div>')
    st.html('<div class="book-page review-page" aria-label="Revisão completa">' + ''.join(rows) + '</div>')
    columns = st.columns(2)
    for col, label, api_side in zip(columns, ["Brancas", "Pretas"], ["white", "black"]):
        official = state.official_accuracies.get(api_side)
        accuracy = official if official is not None else player_accuracy(reviews, label)
        col.metric(f"Precisão · {label}", f"{accuracy:.1f}%" if accuracy is not None else "—",
                   help="Chess.com" if official is not None else "Estimativa baseada na perda de pontos esperados.")
    if len(reviews) < len(list(current_game(state.game).mainline_moves())):
        st.caption(f"{len(reviews)} lances avaliados · precisão estimada quando não há precisão do Chess.com.")


def queue_job(slot, key, function, *args):
    record = st.session_state.jobs.get(slot)
    if record and record[0] == key:
        return
    if record:
        record[1].cancel()
    if slot == "full":
        if st.session_state.analysis_cancel:
            st.session_state.analysis_cancel.set()
        st.session_state.analysis_cancel = Event()
        args = (*args, st.session_state.analysis_cancel)
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
            elif slot == "puzzle" and key == state.puzzle_request:
                state.puzzle = result
                reset_puzzle()
            elif slot == "rating" and key == state.archive_user:
                state.player_rating, state.rating_label = result
                state.rating_user = key
            state.job_errors.pop((slot, key), None)
        except Exception as error:
            state.job_errors[(slot, key)] = str(error)
            if slot == "rating" and key == state.archive_user:
                state.rating_user = key
            while len(state.job_errors) > 32:
                state.job_errors.pop(next(iter(state.job_errors)))
    if changed:
        st.rerun()


def analysis_key():
    state = st.session_state
    return state.game, state.analysis_signature, state.analysis_generation


def ensure_analysis():
    state = st.session_state
    if not engine_path or (state.archive_user and state.rating_user != state.archive_user):
        return
    key = analysis_key()
    if state.loaded_analysis == key or ("full", key) in state.job_errors:
        return
    queue_job("full", key, analyse_with_books, current_game(state.game), engine_path,
              state.player_rating or 1500, book, study, state.quality)


def jump_to_ply(ply):
    st.session_state.ply = ply
    st.session_state.board_revision += 1


def render_moves(prefix):
    state = st.session_state
    board = current_game(state.game).board()
    st.button("Posição inicial", key=f"{prefix}_start", on_click=jump_to_ply, args=(0,))
    with st.container(height=320):
        for ply, move in enumerate(current_game(state.game).mainline_moves(), 1):
            review = state.reviews.get(ply)
            symbol = CATEGORIES[review.category].symbol if review else ""
            label = f"{board.fullmove_number}{'.' if board.turn else '...'} {board.san(move)} {symbol}"
            st.button(label, key=f"{prefix}_{ply}", type="primary" if state.ply == ply else "secondary",
                      on_click=jump_to_ply, args=(ply,), width="stretch")
            board.push(move)


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
    before = board.copy()
    if last:
        before.pop()
    review = state.reviews.get(state.ply)
    category = review.category if review else "book" if last and book.sources(before, last) else None
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        with st.container(horizontal=True):
            with st.popover("", icon=":material/settings:", help="Configurar tabuleiro"):
                st.toggle("Mostrar qualidade do lance", key="show_quality")
                st.toggle("Pretas na parte inferior", key="flip")
                st.selectbox("Qualidade", ["Rápida", "Equilibrada", "Profunda"], key="quality")
                st.caption("Stockfish · 1 thread · 64 MB de hash" if engine_path else "Stockfish não encontrado.")
            with st.popover("", icon=":material/description:", help="Anotações e lances PGN"):
                render_moves("panel")
        interactive_board(board, flip=state.flip, last_move=last,
                          category=CATEGORIES[category] if category and state.show_quality else None,
                          on_move=board_changed, ply=state.ply, total=len(moves), on_navigate=keyboard_navigate,
                          revision=state.board_revision)
        if error := state.pop("move_error", None):
            st.error(error)
        render_review()
    with right:
        answer = state.explanations.get(state.ply)
        if answer and last:
            answer = f"{CATEGORIES[category].symbol if category else '◌'} {before.san(last)} — {answer}"
        state.last_explanation = answer or ""
        with st.container(border=True, key="bobby_explanation"):
            heading, portrait = st.columns([3, 1])
            heading.markdown("### Bobby Fischer")
            with portrait:
                show_portrait(tutor_mood(category)[0])
            if answer:
                st.html(f'<div class="book-page lesson-text">{escape(answer)}</div>')
                st.caption("Stockfish + livros carregados · explicação pré-carregada")
                refs = state.book_references.get(state.ply, [])
                if refs:
                    with st.expander("Trechos dos livros usados nesta posição", expanded=True):
                        for i, ref in enumerate(refs, 1):
                            st.caption(f"[{i}] {ref.source} · {ref.match}")
                            st.text(ref.quote)
                if review and review.played_expected is not None:
                    st.caption(f"Pontos esperados: {review.played_expected:.0%} · perda: {review.expected_loss:.1%}")
            elif "full" in state.jobs:
                st.info("Preparando a análise e todas as explicações da partida…")
            elif not engine_path:
                st.info("Stockfish não encontrado. Instale em engines/ ou configure STOCKFISH_PATH.")
            if error := state.job_errors.get(("full", analysis_key())):
                st.error(error)
                if st.button("Tentar análise novamente"):
                    state.analysis_generation += 1
                    st.rerun()


def reset_puzzle():
    state = st.session_state
    state.puzzle_progress, state.puzzle_message = 0, ""
    state.puzzle_revision += 1


def puzzle_changed():
    state = st.session_state
    event = state.puzzle_board.move
    if not isinstance(event, dict) or not state.puzzle or event.get("revision") != state.puzzle_revision:
        return
    try:
        state.puzzle_progress, state.puzzle_message = solve_move(state.puzzle, state.puzzle_progress,
                                                               event["uci"], event["fen"])
    except (KeyError, ValueError) as error:
        state.puzzle_message = str(error)
    finally:
        state.puzzle_revision += 1


def choose_theme(theme):
    state = st.session_state
    state.tactic_theme = theme
    state.puzzle = None
    state.puzzle_request = None
    state.puzzle_nonce += 1
    reset_puzzle()
    for key in ("rating_min", "rating_max"):
        state.pop(key, None)
    if record := state.jobs.pop("puzzle", None):
        record[1].cancel()


def render_tactics():
    state = st.session_state
    if state.tactic_theme is None:
        st.subheader("Escolha um tema tático")
        columns = st.columns(3)
        for index, (label, theme) in enumerate(THEMES.items()):
            with columns[index % 3], st.container(border=True):
                st.html(theme_art(theme))
                st.button(label, key=f"theme_{theme}", width="stretch", on_click=choose_theme, args=(theme,))
        return
    st.button("Escolher outro tema", icon=":material/arrow_back:", on_click=choose_theme, args=(None,))
    st.subheader(next(label for label, value in THEMES.items() if value == state.tactic_theme))
    start, end = st.columns(2)
    minimum = start.selectbox("Rating inicial", range(0, 4001, 100), index=None, key="rating_min", persist_state="session")
    maximum = end.selectbox("Rating final", range(0, 4001, 100), index=None, key="rating_max", persist_state="session")
    if minimum is None or maximum is None:
        st.info("Selecione o rating inicial e final para carregar automaticamente.")
        return
    if minimum > maximum:
        state.puzzle_request = None
        st.error("O rating inicial deve ser menor ou igual ao final.")
        return
    st.caption(f"Faixa: {minimum}–{maximum} · média: {(minimum + maximum) / 2:.0f}")
    request_key = state.tactic_theme, minimum, maximum, state.puzzle_nonce
    if request_key != state.puzzle_request:
        exclude = state.puzzle.id if state.puzzle else None
        state.puzzle_request, state.puzzle = request_key, None
        reset_puzzle()
        queue_job("puzzle", request_key, fetch_puzzle_range, state.tactic_theme, minimum, maximum, exclude)
    if "puzzle" in state.jobs:
        st.info("Buscando um tático na faixa selecionada…")
    if error := state.job_errors.get(("puzzle", request_key)):
        st.error(error)
        if st.button("Tentar busca novamente"):
            state.puzzle_nonce += 1
            st.rerun()
    if not state.puzzle:
        return
    puzzle = state.puzzle
    board = chess.Board(puzzle.fen)
    player = board.turn
    for move in puzzle.solution[:state.puzzle_progress]:
        board.push_uci(move)
    done = state.puzzle_progress == len(puzzle.solution)
    left, right = st.columns([1.15, 1])
    with left:
        interactive_board(board, flip=not player, on_move=puzzle_changed, key="puzzle_board", disabled=done,
                          revision=state.puzzle_revision,
                          last_move=board.peek() if board.move_stack else chess.Move.from_uci(puzzle.last_move) if puzzle.last_move else None)
    with right:
        st.subheader("Tático resolvido!" if done else f"Jogam as {'brancas' if player else 'pretas'}")
        st.caption(f"Rating Lichess: {puzzle.rating}")
        if state.puzzle_message:
            st.write(state.puzzle_message)
        if not done and st.button("Dica"):
            st.info(f"Observe a peça em {puzzle.solution[state.puzzle_progress][:2]}.")
        st.button("Recomeçar tático", on_click=reset_puzzle)
        if st.button("Próximo tático"):
            state.puzzle_nonce += 1
            st.rerun()
        st.link_button("Ver tático no Lichess", f"https://lichess.org/training/{puzzle.id}")
        st.caption("Fonte: banco público de táticos Lichess · CC0.")


defaults = {"game": (ROOT / "examples/partida.pgn").read_text(encoding="utf-8"), "ply": 0,
            "reviews": {}, "archive_user": load_saved_user(), "history_loaded_user": None,
            "history_games": [], "official_accuracies": {},
            "show_quality": True, "flip": False, "quality": "Equilibrada",
            "analysis_generation": 0, "board_revision": 0, "explanations": {}, "loaded_analysis": None, "analysis_signature": None,
            "analysis_cancel": None, "book_references": {}, "study_files": (), "study_upload_revision": 0,
            "jobs": {}, "job_errors": {},
            "last_explanation": "", "active_tab": "Partida", "tab_history": [], "main_view": "Partida",
            "analysis_workspace_open": False, "puzzle": None, "puzzle_progress": 0,
            "puzzle_message": "", "profile_bytes": None,
            "puzzle_revision": 0, "puzzle_request": None, "puzzle_nonce": 0, "tactic_theme": None,
            "player_rating": None, "rating_label": "", "rating_user": None,
            "background_image": None, "background_mode": "Claro", "theme_mode": load_saved_theme(),
            "background_upload_revision": 0, "appearance_revision": 0}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
state = st.session_state
if state.archive_user == 'demo_import_test' and not os.environ.get('ACERVO_USER_PREFERENCE'):
    state.archive_user, state.history_games, state.history_loaded_user = '', [], None
    state.pop('history_error', None)
# Preserve settings while their widgets are hidden on another tab.
for key in ("quality", "flip", "show_quality", "review_side"):
    if key in state:
        state[key] = state[key]
if isinstance(state.reviews, list):
    state.reviews = {r.ply: r for r in state.reviews}

theme_choice = st.segmented_control("Tema", ["☀ Claro", "☾ Escuro"],
                                    default="☾ Escuro" if state.theme_mode == "Escuro" else "☀ Claro",
                                    key="theme_selector", label_visibility="collapsed",
                                    on_change=theme_selector_changed)

dark_theme = state.theme_mode == "Escuro"
theme_styles = '''
.stApp, .stApp label, .stApp .stMarkdown, .stApp .stCaption, .stApp [data-testid="stMetricLabel"],
.stApp [data-testid="stSidebar"] nav *, .stApp [data-testid="stSidebar"] p,
.stApp [data-testid="stSidebar"] [data-testid="stExpander"] summary { color:#f4f1e8 !important; }
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div { color:#f4f1e8; background-color:#202b38; }
.stApp [data-baseweb="select"] * { color:#f4f1e8 !important; }
''' if dark_theme else '''
.stApp, .stApp label, .stApp .stMarkdown, .stApp .stCaption, .stApp [data-testid="stMetricLabel"],
.stApp [data-testid="stSidebar"] nav *, .stApp [data-testid="stSidebar"] p,
.stApp [data-testid="stSidebar"] [data-testid="stExpander"] summary { color:#000000 !important; }
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div { color:#000000; background-color:#ffffff; }
.stApp [data-baseweb="select"] * { color:#000000 !important; }
.stApp [data-testid="stSidebar"] button[kind="primary"] { color:#ffffff !important; }
'''
st.markdown(f'''<style>
body, .stApp {{ {background_css(state.background_mode, state.background_image, dark_theme)} background-attachment:fixed; }}
.stApp > header {{ background:transparent; }}
.main .block-container {{ position:relative; z-index:1; }}
.stSidebar {{ background:{"#111923ee" if dark_theme else "#f7f4edf2"}; }}
{theme_styles}
.book-page {{background:linear-gradient(90deg,#e5d4ae 0,#faf2df 15px,#fff9ed 48%,#f6ecd6 100%);
color:#342a20;border:1px solid #d9c7a5;border-left:5px solid #c6aa78;border-radius:3px;
box-shadow:3px 3px 0 #e9dcc1,5px 5px 0 #cebb97,0 8px 20px #20170d15}}
.lesson-text {{padding:24px 28px;font:17px/1.8 Georgia,serif;overflow-wrap:anywhere}}
.review-page {{padding:10px 22px;max-width:380px;margin:3px 0 16px}}
.review-row {{display:grid;grid-template-columns:32px 1fr 1fr;gap:16px;align-items:center;padding:3px 0;font:600 15px Georgia,serif;
border-bottom:1px solid #baa48033}}.review-row:last-child {{border-bottom:0}}
.review-row>span:not(:first-child) {{text-align:center}}.review-heading {{font-size:13px;padding-bottom:8px}}
.review-symbol {{display:inline-flex;justify-content:center;align-items:center;width:26px;height:26px;
border-radius:50%;font:bold 13px sans-serif}}
</style>''', unsafe_allow_html=True)
profile, title = st.columns([1, 5])
with profile:
    profile_avatar(state.profile_bytes)
    st.markdown(f"**{state.archive_user or 'Jogador'}**")
    st.caption(f"Rating: {state.player_rating} · {state.rating_label}" if state.player_rating else "Rating: —")
    if state.get("photo_error"):
        st.error(state.photo_error)
    if state.archive_user and state.rating_user != state.archive_user:
        st.caption("Atualizando rating…")
    if state.archive_user and ("rating", state.archive_user) in state.job_errors:
        st.caption("Rating indisponível no momento.")
        if st.button("Atualizar rating"):
            state.rating_user = None
with title:
    pass
    if state.get("theme_save_error"):
        st.caption(state.pop("theme_save_error"))

with st.sidebar:
    if not state.archive_user:
        with st.form("chesscom_user"):
            username = st.text_input("Usuário do Chess.com", placeholder="Nome do usuário", key="chesscom_login_username")
            fetch = st.form_submit_button("Entrar")
        if fetch:
            try:
                user = normalize_username(username)
                games = cached_history(user)
                state.archive_user, state.history_games, state.history_loaded_user = user, games, user
                state.pop('history_error', None)
                state.history_choice = None
                try:
                    save_user(user)
                except OSError:
                    state.login_notice = "Usuário carregado nesta sessão; não foi possível salvar a preferência neste computador."
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    else:
        st.caption(f"Usuário: {state.archive_user}")
        if st.button("Trocar usuário"):
            try:
                USER_PREFERENCE.unlink(missing_ok=True)
            except OSError:
                pass
            state.archive_user, state.history_loaded_user, state.history_games = "", None, []
            state.player_rating, state.rating_user, state.rating_label = None, None, ""
            state.profile_bytes = None
            state.pop('history_error', None)
            state.pop('chesscom_login_username', None)
            state.history_choice = None
            st.rerun()
        if state.history_loaded_user != state.archive_user:
            try:
                state.history_games = cached_history(state.archive_user)
                state.pop('history_error', None)
            except ValueError as error:
                state.history_error = str(error)
            state.history_loaded_user = state.archive_user
    if notice := state.pop("login_notice", None):
        st.info(notice)
    if state.get("history_error"):
        st.error(f"Histórico do Chess.com · {state.archive_user}: {state.history_error}")
        if st.button("Tentar carregar histórico novamente"):
            state.history_loaded_user = None
            state.pop("history_error", None)
            st.rerun()
    if state.history_games:
        def history_label(i, history=state.history_games):
            item = history[i]
            date = datetime.fromtimestamp(item.get("end_time", 0), timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
            return f"{date} · {item.get('white', {}).get('username', '?')} × {item.get('black', {}).get('username', '?')}"
        st.selectbox("Histórico", range(len(state.history_games)), index=None, format_func=history_label,
                     placeholder="Escolha uma partida", key="history_choice", on_change=select_history_game)
    with st.expander("Livros"):
        uploads = st.file_uploader("Adicionar livros", type=["pgn", "bin", "pdf", "txt", "md"], accept_multiple_files=True,
                                   key="books", max_upload_size=200)
        book_plies = st.slider("Profundidade do livro", 4, 80, 40, step=2)
    with st.expander("Fundo da página"):
        background_options = ["Claro", "Escuro", "Imagem personalizada"]
        background_key = f"background_mode_widget_{state.appearance_revision}"
        st.selectbox("Estilo do fundo", background_options,
                     index=background_options.index(state.background_mode), key=background_key,
                     on_change=background_mode_changed, args=(background_key,))
        def background_changed():
            upload = st.session_state.get(f"page_background_upload_{state.background_upload_revision}")
            if upload:
                state.background_image = (upload.type, upload.getvalue())
                state.background_mode = "Imagem personalizada"
                state[background_key] = "Imagem personalizada"

        st.file_uploader("Escolha uma imagem", type=["png", "jpg", "jpeg", "webp"],
                         key=f"page_background_upload_{state.background_upload_revision}",
                         on_change=background_changed, max_upload_size=8)
        st.caption("Escolha entre o padrão claro, escuro ou uma imagem personalizada.")
        if state.background_image and st.button("Restaurar fundo com peças", icon=":material/refresh:"):
            state.background_image = None
            state.background_mode = "Claro"
            state.appearance_revision += 1
            state.background_upload_revision += 1
            st.rerun()

if state.archive_user and state.rating_user != state.archive_user:
    queue_job("rating", state.archive_user, fetch_rating, state.archive_user)

files = tuple((item.name, item.getvalue()) for item in uploads) + state.study_files
book, study, book_errors = load_library(files, book_plies)
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
for error in book_errors:
    st.warning(error)
with st.sidebar:
    st.caption(f"Livros preparados: {len(files)} arquivos · {len(study.passages)} trechos indexados.")
    if not files:
        st.caption("Carregue livros para fundamentar as explicações com trechos e fontes.")
game = current_game(state.game)

def render_workspace(name):
    if name in {"Partida", "Análise"}:
        if name == "Partida":
            with st.expander("Nova partida"):
                if st.button("Nova partida · jogar livremente"):
                    reset_game(chess.pgn.Game())
                    st.rerun()
                if st.button("Carregar exemplo"):
                    reset_game(read_games((ROOT / "examples/partida.pgn").read_text(encoding="utf-8"))[0])
                    st.rerun()
        else:
            with st.expander("Carregar PGN ou FEN"):
                upload = st.file_uploader("Arquivo PGN", type="pgn", key="analysis_game_upload")
                text = st.text_area("Cole o PGN", key="analysis_game_text")
                if st.button("Carregar PGN e analisar"):
                    try:
                        source = decode_text(upload.getvalue()) if upload else text
                        imported = read_games(source)[0]
                        reset_game(imported)
                        state.ply = len(list(imported.mainline_moves()))
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
                        st.rerun()
                    except ValueError as error:
                        st.error(f"FEN inválida: {error}")
            if st.button("Executar avaliação", icon=":material/play_arrow:"):
                state.analysis_generation += 1
                state.explanations, state.reviews = {}, {}
                st.rerun()
        render_board()
    elif name == "Anotações":
        render_moves("notes")
        render_board()
    elif name == "Estudo com livros":
        left, right = st.columns([1.15, 1])
        with left:
            interactive_board(chess.Board(), on_move=lambda: None, key="study_board", disabled=True)
        with right:
            def study_books_changed():
                selected = st.session_state[f"study_book_upload_{st.session_state.study_upload_revision}"]
                st.session_state.study_files = tuple((item.name, item.getvalue()) for item in selected)
            st.file_uploader("Carregar livros para análise", type=["pgn", "bin", "pdf", "txt", "md"],
                             accept_multiple_files=True, key=f"study_book_upload_{state.study_upload_revision}",
                             on_change=study_books_changed, max_upload_size=200)
            st.write(f"{len(study.passages)} trechos preparados para analisar suas partidas.")
            st.caption("Os livros desta aba e da barra lateral são consultados antes da avaliação pelo Stockfish.")
            if state.study_files and st.button("Remover livros desta aba"):
                state.study_files = ()
                state.study_upload_revision += 1
                st.rerun()
    else:
        render_tactics()

from functools import partial

page_icons = {"Partida": "grid_on", "Análise": "analytics", "Anotações": "notes",
              "Estudo com livros": "menu_book", "Tático": "psychology"}
page_paths = {"Partida": "partida", "Análise": "analise", "Anotações": "anotacoes",
              "Estudo com livros": "estudo", "Tático": "tatico"}
pages = {name: st.Page(partial(render_workspace, name), title=name,
                       icon=f":material/{icon}:", url_path=page_paths[name], default=name == "Partida")
         for name, icon in page_icons.items()}
selected_page = st.navigation(list(pages.values()), position="sidebar")
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
if state.tab_history:
    st.button("Voltar", icon=":material/arrow_back:", on_click=go_back, key="navigation_back")
selected_page.run()

with st.sidebar:
    reviews = list(state.reviews.values())
    st.download_button("Baixar partida PGN", export_review(game, reviews) if reviews else str(game),
                       file_name="partida.pgn", mime="application/x-chess-pgn")
if state.jobs:
    poll_jobs()
