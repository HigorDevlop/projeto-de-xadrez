from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from io import StringIO
from pathlib import Path
import base64
import json
import os

import chess
import chess.pgn
import streamlit as st

from chess_review import (BookIndex, CATEGORIES, Thresholds, analyse_game, decode_text,
                          export_review, find_engine, read_games, player_accuracy)
from chesscom import fetch_recent_games, normalize_username
from game_play import play_move
from interactive_board import interactive_board
from profile_photo import normalize_photo
from tactics import THEMES, fetch_puzzle, solve_move
from local_ai import default_model
from tutor import (analyse_position, explain_with_ai, load_passages, move_lesson,
                   ollama_models, retrieve, tutor_mood)

ROOT = Path(__file__).resolve().parent
USER_PREFERENCE = Path(os.environ.get("ACERVO_USER_PREFERENCE", ROOT / ".streamlit/last_chesscom_user.json"))
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


@st.cache_data(max_entries=1, show_spinner=False)
def load_openings():
    index = BookIndex()
    index.add_opening_catalog(ROOT / "data/openings")
    return index


@st.cache_data(max_entries=8, show_spinner=False)
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
    return index, passages, errors + text_errors


@st.cache_data(max_entries=2, show_spinner=False)
def portrait_data(path, modified):
    return base64.b64encode(Path(path).read_bytes()).decode()


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


@st.cache_resource
def language_workers():
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="chess-tutor")


cached_history = st.cache_data(ttl=900, max_entries=32, show_spinner=False)(fetch_recent_games)


def current_game(pgn):
    """Session games may be empty or start from a FEN."""
    return chess.pgn.read_game(StringIO(pgn)) or chess.pgn.Game()


def position_job(pgn, ply, engine, book, depth, seconds):
    game = current_game(pgn)
    board = game.board()
    for move in list(game.mainline_moves())[:ply]:
        board.push(move)
    review = None
    if board.move_stack:
        before = board.copy()
        last = before.pop()
        single = chess.pgn.Game()
        single.setup(before)
        single.add_main_variation(last)
        review = analyse_game(single, engine, book, depth, seconds, Thresholds())[0]
        review.ply = ply
    snapshot = analyse_position(board.fen(), engine, depth, seconds)
    return review, snapshot


def reset_game(game, accuracies=None):
    state = st.session_state
    for _, future in state.jobs.values():
        future.cancel()
    state.jobs, state.job_errors = {}, {}
    state.game, state.ply, state.reviews = str(game), 0, {}
    state.position_results, state.tutor_answers = {}, {}
    state.explanation_nonce = 0
    state.official_accuracies = {side: float(value) for side, value in (accuracies or {}).items()
                               if side in {"white", "black"} and isinstance(value, (int, float))
                               and not isinstance(value, bool) and 0 <= value <= 100}
    state.full_analysis_requested = False


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
        state.requested_page = state.tab_history.pop()
        state.going_back = True


def board_changed():
    event = st.session_state.interactive_board.move
    if not isinstance(event, dict):
        return
    state = st.session_state
    try:
        pgn, ply = play_move(state.game, state.ply, event["uci"], event["fen"])
        if pgn != state.game:
            state.reviews = {p: r for p, r in state.reviews.items() if p <= state.ply}
            state.official_accuracies = {}
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
                   help="Chess.com" if official is not None else "Estimativa local dos lances já avaliados.")
    if len(reviews) < len(list(current_game(state.game).mainline_moves())):
        st.caption(f"{len(reviews)} lances avaliados · precisão local parcial quando não há precisão do Chess.com.")


def queue_job(slot, key, function, *args, language=False):
    record = st.session_state.jobs.get(slot)
    if record and record[0] == key:
        return
    if record:
        record[1].cancel()
    pool = language_workers() if language else workers()
    st.session_state.jobs[slot] = (key, pool.submit(function, *args))


@st.fragment(run_every=0.4)
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
            state.job_errors.pop((slot, key), None)
            if slot == "position":
                state.position_results[key] = result
                if key[:2] == (state.game, state.analysis_signature) and result[0]:
                    state.reviews.setdefault(result[0].ply, result[0])
            elif slot == "full" and key == (state.game, state.analysis_signature):
                state.reviews = {r.ply: r for r in result}
            elif slot == "tutor":
                state.tutor_answers[key] = result
                past_game = current_game(key[0][0])
                past_board = past_game.board()
                for move in list(past_game.mainline_moves())[:key[0][2]]:
                    past_board.push(move)
                state.ai_by_fen[past_board.fen()] = result
            for cache in (state.position_results, state.tutor_answers, state.ai_by_fen):
                while len(cache) > 128:
                    cache.pop(next(iter(cache)))
        except Exception as error:
            state.job_errors[(slot, key)] = str(error)
            while len(state.job_errors) > 128:
                state.job_errors.pop(next(iter(state.job_errors)))
    if changed:
        st.rerun()


def render_board(book, passages, library_id, engine_path, quality):
    state = st.session_state
    game = current_game(state.game)
    moves = list(game.mainline_moves())
    state.ply = min(state.ply, len(moves))
    board = game.board()
    for move in moves[:state.ply]:
        board.push(move)
    last = board.peek() if board.move_stack else None
    before = board.copy()
    if last:
        before.pop()
    position_key = (state.game, state.analysis_signature, state.ply)
    depth, seconds = {"Rápida": (12, .1), "Equilibrada": (18, .4), "Profunda": (24, 1.5)}[quality]
    engine_ready = bool(engine_path and Path(engine_path).is_file())
    result = state.position_results.get(position_key)
    if engine_ready and state.auto_classify and result is None and ("position", position_key) not in state.job_errors:
        queue_job("position", position_key, position_job, state.game, state.ply, engine_path, book, depth, seconds)
    review = state.reviews.get(state.ply)
    snapshot = result[1] if result else None
    category = review.category if review else "book" if last and book.sources(before, last) else None
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        with st.popover("", icon=":material/settings:", help="Configurar tabuleiro e engine"):
            st.toggle("Mostrar qualidade do lance", key="show_quality")
            st.toggle("Pretas na parte inferior", key="flip")
            st.text_input("Executável da engine", key="engine_path")
            st.selectbox("Qualidade", ["Rápida", "Equilibrada", "Profunda"], key="quality")
            st.toggle("Classificar ao mover peças", key="auto_classify")
            if not engine_ready:
                st.info("Configure a engine para obter as classificações e continuações calculadas.")
        interactive_board(board, flip=state.flip, last_move=last,
                          category=CATEGORIES[category] if category and state.show_quality else None,
                          on_move=board_changed, ply=state.ply, total=len(moves), on_navigate=keyboard_navigate)
        if error := state.pop("move_error", None):
            st.error(error)
        render_review()
    with right:
        question = state.get("explanation_question", "")
        model = state.get("tutor_model", "").strip()
        answer_key = (position_key, category, bool(snapshot), library_id, question, model, state.explanation_nonce, 'strategy-v2')
        answer = move_lesson(board, review, snapshot, category, question, state.explanation_nonce)
        matched = retrieve(passages, board, question, before.fen())
        if model and (snapshot is not None or not engine_ready or not state.auto_classify):
            if answer_key not in state.tutor_answers and ("tutor", answer_key) not in state.job_errors:
                queue_job("tutor", answer_key, explain_with_ai, model, board.copy(), review, snapshot,
                          matched, question, state.explanation_nonce,
                          state.ai_by_fen.get(board.fen() if state.explanation_nonce else before.fen(), ''), language=True)
            answer = state.tutor_answers.get(answer_key, answer)
        if last:
            symbol = CATEGORIES[category].symbol if category else "◌"
            answer = f"{symbol} {before.san(last)} — {answer}"
        state.last_explanation, state.last_explanation_key = answer, answer_key
        with st.container(border=True, key="bobby_explanation"):
            heading, portrait = st.columns([3, 1])
            heading.markdown("### Bobby Fischer")
            with portrait:
                show_portrait(tutor_mood(category)[0])
            st.html(f'<div class="book-page lesson-text">{escape(answer)}</div>')
            if model and answer_key not in state.tutor_answers and ('tutor', answer_key) not in state.job_errors:
                st.caption("A IA local está desenvolvendo a explicação estratégica desta posição…")
            elif model and answer_key in state.tutor_answers:
                st.caption(f"Explicação gerada localmente · {model}")
            st.text_input("Pergunta sobre esta posição", key="explanation_question",
                          placeholder="Qual é o plano e a ameaça do adversário?", max_chars=1000)
            if question and not model:
                st.caption("A explicação acima usa os fatos do tabuleiro. Para conversar sobre uma pergunta, selecione uma IA local nas configurações do tutor.")
            if matched:
                with st.expander("Trechos dos livros nesta posição"):
                    for passage in matched:
                        st.caption(passage.source)
                        st.write(passage.text)
            if st.button("Reexplicar lance", icon=":material/refresh:"):
                state.explanation_nonce += 1
                st.rerun()
            for slot, key in [("position", position_key), ("tutor", answer_key)]:
                if error := state.job_errors.get((slot, key)):
                    st.caption(f"{error} A explicação do tabuleiro continua disponível.")


def puzzle_changed():
    state = st.session_state
    event = state.puzzle_board.move
    if not isinstance(event, dict) or not state.puzzle:
        return
    try:
        state.puzzle_progress, state.puzzle_message = solve_move(state.puzzle, state.puzzle_progress,
                                                               event["uci"], event["fen"])
    except (KeyError, ValueError) as error:
        state.puzzle_message = str(error)


def render_tactics():
    state = st.session_state
    random = st.button("Random · tático aleatório", icon=":material/shuffle:", type="primary")
    theme = st.selectbox("Tema do tático", list(THEMES))
    difficulties = dict(zip(["Muito fácil", "Fácil", "Normal", "Difícil", "Muito difícil"],
                            ["easiest", "easier", "normal", "harder", "hardest"]))
    difficulty = st.select_slider("Dificuldade", list(difficulties), value="Normal")
    load = st.button("Carregar tático", icon=":material/refresh:")
    if random or load:
        try:
            with st.spinner("Buscando tático no Lichess…"):
                state.puzzle = fetch_puzzle("mix" if random else THEMES[theme], difficulties[difficulty])
            state.puzzle_progress, state.puzzle_message = 0, ""
        except ValueError as error:
            st.error(str(error))
    if not state.puzzle:
        st.info("Escolha um tema ou Random para começar.")
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
                          last_move=board.peek() if board.move_stack else chess.Move.from_uci(puzzle.last_move) if puzzle.last_move else None)
    with right:
        st.subheader("Tático resolvido!" if done else f"Jogam as {'brancas' if player else 'pretas'}")
        st.caption(f"Dificuldade Lichess: {puzzle.rating}")
        if state.puzzle_message:
            st.write(state.puzzle_message)
        if not done and st.button("Dica"):
            st.info(f"Observe a peça em {puzzle.solution[state.puzzle_progress][:2]}.")
        if st.button("Recomeçar tático"):
            state.puzzle_progress, state.puzzle_message = 0, ""
            st.rerun()
        st.link_button("Ver tático no Lichess", f"https://lichess.org/training/{puzzle.id}")
        st.caption("Fonte: banco público de táticos Lichess · CC0.")


defaults = {"game": (ROOT / "examples/partida.pgn").read_text(encoding="utf-8"), "ply": 0,
            "reviews": {}, "archive_user": load_saved_user(), "history_loaded_user": None,
            "history_games": [], "official_accuracies": {}, "full_analysis_requested": False,
            "show_quality": True, "flip": False, "quality": "Equilibrada", "auto_classify": True,
            "engine_path": find_engine(), "analysis_signature": None, "position_results": {},
            "tutor_answers": {}, "jobs": {}, "job_errors": {}, "explanation_nonce": 0,
            "last_explanation": "", "active_tab": "Partida", "tab_history": [], "main_view": "Partida",
            "analysis_workspace_open": False, "puzzle": None, "puzzle_progress": 0,
            "puzzle_message": "", "profile_bytes": None, "photo_digest": None,
            "ai_by_fen": {}, "tutor_model": default_model()}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
state = st.session_state
if state.archive_user == 'demo_import_test' and not os.environ.get('ACERVO_USER_PREFERENCE'):
    state.archive_user, state.history_games, state.history_loaded_user = '', [], None
    state.pop('history_error', None)
# Pick up the completed local installation even in an already open session.
installed_model = default_model()
if installed_model and state.get('installed_model_seen') != installed_model:
    state.tutor_model = installed_model
    state.installed_model_seen = installed_model
# Preserve settings while their widgets are hidden on another tab.
for key in ("engine_path", "quality", "auto_classify", "flip", "show_quality", "review_side", "explanation_question"):
    if key in state:
        state[key] = state[key]
if isinstance(state.reviews, list):
    state.reviews = {r.ply: r for r in state.reviews}

st.html('''<style>
.book-page {background:linear-gradient(90deg,#e5d4ae 0,#faf2df 15px,#fff9ed 48%,#f6ecd6 100%);
color:#342a20;border:1px solid #d9c7a5;border-left:5px solid #c6aa78;border-radius:3px;
box-shadow:3px 3px 0 #e9dcc1,5px 5px 0 #cebb97,0 8px 20px #20170d15}
.lesson-text {padding:24px 28px;font:17px/1.8 Georgia,serif;overflow-wrap:anywhere}
.review-page {padding:10px 22px;max-width:380px;margin:3px 0 16px}
.review-row {display:grid;grid-template-columns:32px 1fr 1fr;gap:16px;align-items:center;padding:3px 0;font:600 15px Georgia,serif;
border-bottom:1px solid #baa48033}.review-row:last-child {border-bottom:0}
.review-row>span:not(:first-child) {text-align:center}.review-heading {font-size:13px;padding-bottom:8px}
.review-symbol {display:inline-flex;justify-content:center;align-items:center;width:26px;height:26px;
border-radius:50%;font:bold 13px sans-serif}
</style>''')
st.title(state.archive_user or "Acervo de xadrez")

with st.sidebar:
    with st.expander("Foto do perfil"):
        photo = st.file_uploader("Selecionar foto", type=["png", "jpg", "jpeg", "webp"], key="profile_photo", max_upload_size=10)
    if photo:
        digest = sha256(photo.getvalue()).hexdigest()
        if digest != state.photo_digest:
            try:
                state.profile_bytes = normalize_photo(photo.getvalue())
                state.photo_digest = digest
                state.pop("photo_error", None)
            except ValueError as error:
                state.photo_error = str(error)
                state.photo_digest = digest
    if state.get("photo_error"):
        st.error(state.photo_error)
    if state.profile_bytes:
        encoded = base64.b64encode(state.profile_bytes).decode()
        st.html(f'<img alt="Foto do perfil" src="data:image/png;base64,{encoded}" width="120" style="border-radius:12px">')
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
    with st.expander("Tutor"):
        st.text_input("Modelo local do Ollama", key="tutor_model", placeholder="Nome do modelo instalado")
        if st.button("Detectar modelos locais"):
            try:
                st.write(ollama_models())
            except ValueError as error:
                st.info(str(error))

files = tuple((item.name, item.getvalue()) for item in uploads)
book, passages, book_errors = load_library(files, book_plies)
library_id = sha256(repr(files).encode()).hexdigest()
signature = (library_id, book_plies, state.engine_path, state.quality)
if state.analysis_signature != signature:
    state.reviews, state.position_results, state.job_errors = {}, {}, {}
    state.analysis_signature = signature
for error in book_errors:
    st.warning(error)
game = current_game(state.game)

if state.full_analysis_requested:
    state.full_analysis_requested = False
    if state.engine_path and Path(state.engine_path).is_file() and list(game.mainline_moves()):
        depth, seconds = {"Rápida": (12, .1), "Equilibrada": (18, .4), "Profunda": (24, 1.5)}[state.quality]
        queue_job("full", (state.game, signature), analyse_game, game, state.engine_path, book, depth, seconds, Thresholds())
    elif not state.engine_path or not Path(state.engine_path).is_file():
        st.warning("Configure uma engine válida para executar a avaliação.")
if "full" in state.jobs:
    st.caption("Avaliando a partida em segundo plano…")
if error := state.job_errors.get(("full", (state.game, signature))):
    st.error(f"Não foi possível concluir a análise: {error}")

def render_workspace(name):
    st.button("Voltar", icon=":material/arrow_back:", disabled=not state.tab_history,
              on_click=go_back, key=f"back_{name}")
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
                        state.full_analysis_requested = True
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
                state.full_analysis_requested = True
                st.rerun()
        render_board(book, passages, library_id, state.engine_path, state.quality)
    elif name == "Anotações":
        current = game.board()
        for i, move in enumerate(game.mainline_moves(), 1):
            review = state.reviews.get(i)
            symbol = CATEGORIES[review.category].symbol if review else "📖" if book.sources(current, move) else "◌"
            st.write(f"{symbol} {current.fullmove_number}{'.' if current.turn else '...'} {current.san(move)}")
            current.push(move)
        render_review()
    elif name == "Estudo com livros":
        left, right = st.columns([1.15, 1])
        with left:
            interactive_board(chess.Board(), on_move=lambda: None, key="study_board", disabled=True)
        with right:
            st.file_uploader("Carregar livro desejado", type=["pgn", "bin", "pdf", "txt", "md"], key="study_book_upload", max_upload_size=200)
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
    if not state.pop('going_back', False):
        state.tab_history.append(state.active_tab)
state.active_tab = state.main_view = selected_page.title
state.analysis_workspace_open = selected_page.title == 'Análise'
selected_page.run()

with st.sidebar:
    reviews = list(state.reviews.values())
    st.download_button("Baixar partida PGN", export_review(game, reviews) if reviews else str(game),
                       file_name="partida.pgn", mime="application/x-chess-pgn")
if state.jobs:
    poll_jobs()
