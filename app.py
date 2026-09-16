from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
from pathlib import Path
import os
import base64

import chess
import chess.engine
import chess.pgn
import chess.svg
import pandas as pd
import streamlit as st

from chess_review import (BookIndex, CATEGORIES, Thresholds, analyse_game,
                          decode_text, export_review, find_engine, read_games, player_accuracy)
from chesscom import fetch_recent_games, normalize_username
from game_play import play_move
from interactive_board import interactive_board
from tutor import (analyse_position, basic_lesson, explain_with_ai, load_passages,
                   ollama_models, retrieve, tutor_mood)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Acervo • análise de xadrez", page_icon="♞", layout="wide",
                   initial_sidebar_state="collapsed")


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


@st.cache_data(max_entries=1, show_spinner=False)
def load_openings():
    index = BookIndex()
    index.add_opening_catalog(ROOT / "data/openings")
    return index


@st.cache_data(max_entries=2, show_spinner=False)
def portrait_data(path, modified):
    return base64.b64encode(Path(path).read_bytes()).decode()


def show_portrait(mood):
    path = ROOT / "assets/bobby-expressions.png"
    if not path.is_file():
        return
    data = portrait_data(str(path), path.stat().st_mtime)
    offset = {"serio": "0%", "pensativo": "50%", "raiva": "100%"}[mood]
    label = {"serio": "sério", "pensativo": "pensativo", "raiva": "frustrado com o erro"}[mood]
    st.html(f'<div role="img" aria-label="Bobby Fischer virtual: {label}" '
            f'style="width:100%;max-width:125px;aspect-ratio:1;border-radius:12px;'
            f'background-image:url(data:image/png;base64,{data});background-size:300% 100%;'
            f'background-position:{offset} center"></div>')


cached_history = st.cache_data(ttl=900, max_entries=32, show_spinner=False)(fetch_recent_games)
cached_position = st.cache_data(ttl=3600, max_entries=128, show_spinner=False)(analyse_position)


def reset_game(game, accuracies=None):
    st.session_state.game = str(game)
    st.session_state.ply = 0
    st.session_state.reviews = {}
    st.session_state.pending_ply = None
    st.session_state.tutor_answer = None
    st.session_state.official_accuracies = {side: float(value) for side, value in (accuracies or {}).items()
                                          if side in {"white", "black"} and isinstance(value, (int, float))
                                          and not isinstance(value, bool) and 0 <= value <= 100}


def jump(ply):
    st.session_state.ply = ply


def slider_jump():
    st.session_state.ply = st.session_state.position_slider


def accept_move(uci, fen):
    state = st.session_state
    try:
        old_ply = state.ply
        pgn, next_ply = play_move(state.game, old_ply, uci, fen)
        if pgn != state.game:
            state.reviews = {p: r for p, r in state.reviews.items() if p <= old_ply}
            state.game = pgn
            state.official_accuracies = {}
        if next_ply not in state.reviews:
            state.pending_ply = next_ply
        state.ply = next_ply
        state.tutor_answer = None
    except ValueError as error:
        state.move_error = str(error)


def board_changed():
    event = st.session_state.interactive_board.move
    if isinstance(event, dict) and isinstance(event.get("uci"), str) and isinstance(event.get("fen"), str):
        accept_move(event["uci"], event["fen"])


def keyboard_navigate():
    event = st.session_state.interactive_board.navigate
    total = len(list(chess.pgn.read_game(StringIO(st.session_state.game)).mainline_moves()))
    if (isinstance(event, dict) and event.get("from") == st.session_state.ply
            and isinstance(event.get("to"), int) and 0 <= event["to"] <= total):
        jump(event["to"])


def select_history_game():
    index = st.session_state.history_choice
    history = st.session_state.history_games
    if isinstance(index, int) and 0 <= index < len(history):
        try:
            reset_game(read_games(history[index]["pgn"])[0], history[index].get("accuracies"))
            st.session_state.workspace_tab = "Análise"
        except ValueError as error:
            st.session_state.history_error = f"Não foi possível importar esta partida: {error}"


def badge(key):
    category = CATEGORIES[key]
    st.html(f'<span style="display:inline-flex;align-items:center;gap:9px;font-weight:600">'
            f'<span style="display:inline-block;text-align:center;min-width:30px;padding:5px;'
            f'border-radius:50%;background:{category.color};color:{category.ink}">{category.symbol}</span>'
            f'{category.label}</span>')


for key, value in {"game": (ROOT / "examples/partida.pgn").read_text(encoding="utf-8"),
                   "ply": 0, "reviews": {}, "analysis_signature": None,
                   "pending_ply": None, "tutor_answer": None, "snapshot": None,
                   "archive_user": "", "archive_months": [], "history_games": [],
                   "history_source": None, "local_models": [], "official_accuracies": {},
                   "tutor_answers": {}, "tutor_attempt": None}.items():
    st.session_state.setdefault(key, value)
if isinstance(st.session_state.reviews, list):
    st.session_state.reviews = {r.ply: r for r in st.session_state.reviews}

st.title("Acervo de xadrez")
st.caption("Explore cada lance. Entenda a posição. Aprenda com a partida.")

st.subheader("Histórico de partidas · Chess.com")
with st.form("chesscom_user"):
    username = st.text_input("Usuário do Chess.com", placeholder="Seu nome de usuário")
    fetch = st.form_submit_button("Buscar histórico")
if fetch:
    st.session_state.history_games = []
    st.session_state.history_choice = None
    st.session_state.archive_user = ""
    try:
        user = normalize_username(username)
        with st.spinner("Carregando partidas recentes…"):
            st.session_state.history_games = cached_history(user)
        st.session_state.archive_user = user
        if not st.session_state.history_games:
            st.info("Nenhuma partida de xadrez clássico encontrada nos 12 arquivos mensais mais recentes.")
    except ValueError as error:
        st.error(str(error))
history = st.session_state.history_games
if history:
    def history_label(i):
        item = history[i]
        date = datetime.fromtimestamp(item.get("end_time", 0), timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        white, black = item.get("white", {}), item.get("black", {})
        result = "1–0" if white.get("result") == "win" else "0–1" if black.get("result") == "win" else "½–½"
        return f"{date} · {white.get('username', '?')} × {black.get('username', '?')} · {result} · {item.get('time_class', '')}"
    st.selectbox("Partida do histórico", range(len(history)), format_func=history_label,
                 index=None, placeholder="Selecione uma partida para abrir no tabuleiro",
                 key="history_choice", on_change=select_history_game)
    st.caption(f"{len(history)} partidas recentes de {st.session_state.archive_user} · até 100 partidas dos 12 arquivos mensais mais recentes.")
if error := st.session_state.pop("history_error", None):
    st.error(error)


analysis_tab, study_tab = st.tabs(["Análise", "Estudo com livros"], key="workspace_tab", on_change="rerun")
if study_tab.open:
    with study_tab:
        study_board, study_book = st.columns([1.15, 1], gap="large")
        with study_board:
            st.image(chess.svg.board(chess.Board(), size=560, coordinates=False,
                     colors={"square light": "#E5DED0", "square dark": "#69746B"}), width=560)
        with study_book:
            with st.container(border=True):
                st.subheader("Carregar livro")
                st.file_uploader("Escolha o livro desejado", type=["pdf", "pgn", "bin", "txt", "md"],
                                 key="study_book_upload", max_upload_size=25)
    st.stop()

with analysis_tab:
    with st.sidebar:
        st.header("Configurações")
        st.caption("Bobby Fischer é uma recriação virtual. Sem IA conectada, as explicações são geradas "
                   "a partir dos efeitos reais do lance no tabuleiro e da análise disponível.")
        engine_path = st.text_input("Executável do Stockfish", value=find_engine(), key="engine_path")
        engine_ready = bool(engine_path and Path(engine_path).is_file())
        if not engine_ready:
            st.warning("Informe o caminho do Stockfish para avaliar os lances.")
        quality = st.selectbox("Qualidade", ["Rápida", "Equilibrada", "Profunda"], index=1)
        depth, seconds = {"Rápida": (12, 0.1), "Equilibrada": (18, 0.4), "Profunda": (24, 1.5)}[quality]
        auto_classify = st.toggle("Classificar ao mover peças", value=True)
        flip = st.toggle("Pretas na parte inferior")
        with st.expander("IA local · Ollama"):
            st.caption("O tutor consulta os livros carregados usando um modelo instalado no seu computador.")
            if st.button("Detectar modelos locais"):
                try:
                    st.session_state.local_models = ollama_models()
                    if not st.session_state.local_models:
                        st.info("Nenhum modelo instalado no Ollama.")
                except ValueError as error:
                    st.error(str(error))
            if st.session_state.local_models:
                model = st.selectbox("Modelo instalado", st.session_state.local_models)
            else:
                model = st.text_input("Nome do modelo instalado", value=os.environ.get("OLLAMA_MODEL", ""),
                                      placeholder="Nome mostrado por ollama list")
            st.caption("Sem modelo conectado, use a orientação básica e a continuação do Stockfish.")
        with st.expander("Critérios de classificação"):
            st.caption("A precisão do Chess.com é exibida quando fornecida pela API. Caso contrário, "
                       "a precisão estimada usa a média da qualidade dos lances avaliados; não é o CAPS2 do Chess.com.")
            st.caption("Limites públicos do Chess.com: Excelente <2%, Bom <5%, Imprecisão <10%, "
                       "Erro <20% e Erro grave a partir de 20% de perda de pontos esperados.")
            st.caption("Aproximação local com probabilidades do Stockfish. O modelo completo ajustado ao rating "
                       "não foi disponibilizado na documentação pública consultada. Brilhante, Ótimo e "
                       "Oportunidade perdida usam heurísticas locais; os resultados podem diferir do Chess.com.")
        with st.expander("Legenda das categorias"):
            for key, category in CATEGORIES.items():
                badge(key)
                st.caption(category.description)

    thresholds, criteria_error = Thresholds(), None

    with st.expander("Importar PGN ou iniciar uma partida"):
        pgn_upload = st.file_uploader("Arquivo de partida", type="pgn", key="game_upload")
        pgn_text = st.text_area("Ou cole o PGN", height=100, placeholder="1. e4 e5 2. Nf3 Nc6 ...")
        parsed = []
        try:
            source = decode_text(pgn_upload.getvalue()) if pgn_upload else pgn_text
            if source.strip():
                parsed = read_games(source)
        except (ValueError, UnicodeError) as error:
            st.error(str(error))
        chosen = st.selectbox("Partida do arquivo", range(len(parsed)),
                              format_func=lambda i: f"{i+1}. {parsed[i].headers.get('White', '?')} × "
                                                    f"{parsed[i].headers.get('Black', '?')}") if parsed else 0
        with st.container(horizontal=True):
            if st.button("Carregar partida", disabled=not parsed):
                reset_game(parsed[chosen])
                st.rerun()
            if st.button("Nova partida · jogar livremente"):
                reset_game(chess.pgn.Game())
                st.rerun()
            if st.button("Carregar exemplo"):
                reset_game(read_games((ROOT / "examples/partida.pgn").read_text(encoding="utf-8"))[0])
                st.rerun()

    game = chess.pgn.read_game(StringIO(st.session_state.game))
    moves = list(game.mainline_moves())
    ply = min(st.session_state.ply, len(moves))
    st.session_state.ply = ply
    board = game.board()
    for move in moves[:ply]:
        board.push(move)

    board_column, tutor_column = st.columns([1.15, 1], gap="large")
    with tutor_column:
        st.subheader("Aprenda com a posição")
        with st.expander("Livros do tutor"):
            uploads = st.file_uploader("Carregar livros e comentários", type=["pgn", "bin", "pdf", "txt", "md"],
                                       accept_multiple_files=True, key="books", max_upload_size=25)
            book_plies = st.slider("Meios-lances por linha do livro PGN", 4, 80, 40, step=2)
            st.caption("PDF e texto ensinam conceitos; PGN e Polyglot também identificam lances de livro. "
                       "PDFs digitalizados precisam de OCR.")
        tutor_slot = st.container()

    files = tuple((item.name, item.getvalue()) for item in uploads)
    book, passages, book_errors = load_library(files, book_plies)
    library_id = sha256(repr(files).encode()).hexdigest()
    signature = ("expected-points-v1", library_id, book_plies, engine_path, quality, asdict(thresholds))
    if st.session_state.analysis_signature != signature:
        st.session_state.reviews = {}
        st.session_state.analysis_signature = signature

    pending = st.session_state.pending_ply
    if pending:
        st.session_state.pending_ply = None
        if auto_classify and engine_ready and not criteria_error:
            before = game.board()
            for move in moves[:pending - 1]:
                before.push(move)
            one_move_game = chess.pgn.Game()
            one_move_game.setup(before)
            one_move_game.add_main_variation(moves[pending - 1])
            try:
                with st.spinner("Avaliando seu lance…"):
                    result = analyse_game(one_move_game, engine_path, book, depth, seconds, thresholds)[0]
                result.ply = pending
                st.session_state.reviews[pending] = result
            except (ValueError, OSError, chess.engine.EngineError, TimeoutError) as error:
                st.warning(f"Lance registrado; a avaliação não foi concluída: {error}")

    review_map = st.session_state.reviews
    reviews = [review_map[p] for p in sorted(review_map)]
    selected = review_map.get(ply)
    last_move = moves[ply - 1] if ply else None
    previous = board.copy()
    if ply:
        previous.pop()
    book_sources = book.sources(previous, last_move) if last_move else []
    selected_category = selected.category if selected else "book" if book_sources else None

    with board_column:
        st.subheader("Tabuleiro")
        st.caption(f"{game.headers.get('White', 'Brancas')} × {game.headers.get('Black', 'Pretas')} · "
                   f"Resultado: {game.headers.get('Result', '*')}")
        with st.container(horizontal=True):
            st.button("Início", on_click=jump, args=(0,), disabled=ply == 0)
            st.button("Anterior", on_click=jump, args=(ply - 1,), disabled=ply == 0)
            st.button("Próximo", on_click=jump, args=(ply + 1,), disabled=ply == len(moves))
            st.button("Final", on_click=jump, args=(len(moves),), disabled=ply == len(moves))
        if moves:
            st.session_state.position_slider = ply
            st.slider("Posição na partida", 0, len(moves), key="position_slider", on_change=slider_jump)
        interactive_board(board, flip=flip, last_move=last_move,
                          category=CATEGORIES[selected_category] if selected_category else None,
                          on_move=board_changed, ply=ply, total=len(moves), on_navigate=keyboard_navigate)
        st.caption("← lance anterior · → próximo lance · Home início · End final")
        if message := st.session_state.pop("move_error", None):
            st.error(message)
        st.caption(f"Posição encerrada · {board.result()}" if board.is_game_over() else
                   f"Vez das {'brancas' if board.turn else 'pretas'}" + (" · xeque" if board.is_check() else ""))
        analysis_slot = st.container()
        with st.expander("Jogar por notação ou consultar FEN"):
            st.caption("Ao testar outro lance, a continuação anterior fica preservada como variante no PGN.")
            legal = sorted(board.legal_moves, key=board.san) if not board.is_game_over() else []
            with st.form("play_move"):
                choice = st.selectbox("Lance legal (SAN)", [m.uci() for m in legal],
                                       format_func=lambda value: board.san(chess.Move.from_uci(value)))
                add = st.form_submit_button("Jogar lance", disabled=not legal)
            if add and choice:
                accept_move(choice, board.fen())
                st.rerun()
            st.code(board.fen(), language=None)


    with board_column:
        if moves:
            with st.expander("Lances da partida", expanded=True):
                nav = st.container(horizontal=True)
                current = game.board()
                for i, move in enumerate(moves, 1):
                    r = review_map.get(i)
                    symbol = CATEGORIES[r.category].symbol if r else CATEGORIES["book"].symbol if book.sources(current, move) else "·"
                    number = f"{current.fullmove_number}{'.' if current.turn else '...'}"
                    with nav:
                        st.button(f"{symbol} {number} {current.san(move)}", key=f"nav_{i}",
                                  on_click=jump, args=(i,), type="primary" if i == ply else "secondary")
                    current.push(move)
                st.caption("· = ainda não avaliado. Clique em um lance para voltar à posição.")

    with tutor_slot:
        st.caption(f"{book.size} entradas de abertura · {len(passages)} trechos de leitura")
        for error in book_errors:
            st.warning(error)
        question = st.text_input("O que você quer entender?", placeholder="Qual é o plano e a ameaça do adversário?", max_chars=1000)
        explain = st.button("Reexplicar lance", icon=":material/refresh:")
        snapshot_key = (board.fen(), engine_path, quality)
        snapshot_record = st.session_state.snapshot
        snapshot = snapshot_record[1] if snapshot_record and snapshot_record[0] == snapshot_key else None
        matched = retrieve(passages, board, question, previous.fen() if ply else None)
        if engine_ready and ply and snapshot is None:
            try:
                snapshot = cached_position(board.fen(), engine_path, depth, seconds)
                st.session_state.snapshot = (snapshot_key, snapshot)
            except (ValueError, OSError, chess.engine.EngineError, TimeoutError) as error:
                st.warning(f"A continuação não pôde ser calculada: {error}")
        answer_key = ("move-prose-v2", snapshot_key, previous.fen(), last_move.uci() if last_move else "",
                      library_id, question, model, selected.explanation if selected else "")
        answer_cache = st.session_state.tutor_answers
        with st.container(border=True, key="bobby_explanation"):
            mood, _ = tutor_mood(selected_category, thinking=explain)
            heading, portrait = st.columns([3, 1])
            with heading:
                st.markdown("### Bobby Fischer")
            with portrait:
                show_portrait(mood)
            explanation_slot = st.empty()
            explanation_slot.write(answer_cache.get(answer_key) or basic_lesson(board, selected, snapshot))
        if (model.strip() and ply and (explain or (answer_key not in answer_cache
                and st.session_state.tutor_attempt != answer_key))):
            st.session_state.tutor_attempt = answer_key
            try:
                with st.spinner("Preparando a explicação deste lance…"):
                    answer = explain_with_ai(model.strip(), board, selected, snapshot, matched, question)
                if len(answer_cache) >= 64:
                    answer_cache.pop(next(iter(answer_cache)))
                answer_cache[answer_key] = answer
                explanation_slot.write(answer)
            except ValueError as error:
                st.warning(str(error))
        if matched:
            with st.expander("Referências consultadas"):
                for i, passage in enumerate(matched, 1):
                    st.write(f"**[{i}] {passage.source}**")
                    st.text(passage.text)
        else:
            st.caption("Nenhum trecho relevante encontrado nos livros carregados para esta posição.")

    with analysis_slot:
        st.markdown("#### Análise da partida")
        if st.button("Analisar partida", icon=":material/analytics:", type="primary",
                     disabled=not moves or not engine_ready or criteria_error is not None):
            bar = st.progress(0, text="Preparando a engine…")
            try:
                results = analyse_game(game, engine_path, book, depth, seconds, thresholds,
                                       lambda done, total: bar.progress(done / total, text=f"Analisando lance {done} de {total}…"))
                st.session_state.reviews = {r.ply: r for r in results}
                st.session_state.analysis_signature = signature
                st.rerun()
            except (ValueError, OSError, chess.engine.EngineError, TimeoutError) as error:
                st.error(f"Não foi possível concluir a análise: {error}")
            finally:
                bar.empty()


        counts = {key: {"Brancas": 0, "Pretas": 0} for key in CATEGORIES}
        current = game.board()
        unclassified = 0
        for i, move in enumerate(moves, 1):
            review = review_map.get(i)
            category = review.category if review else "book" if book.sources(current, move) else None
            if category:
                counts[category]["Brancas" if current.turn else "Pretas"] += 1
            else:
                unclassified += 1
            current.push(move)
        rows = pd.DataFrame([{"Classificação": f"{cat.symbol} {cat.label}",
                              "Brancas": counts[key]["Brancas"], "Pretas": counts[key]["Pretas"]}
                             for key, cat in CATEGORIES.items()])
        for metric_column, side, api_side in zip(st.columns(2), ["Brancas", "Pretas"], ["white", "black"]):
            official = st.session_state.official_accuracies.get(api_side)
            accuracy = official if official is not None else player_accuracy(reviews, side)
            label = f"Precisão · {side}" if official is not None else f"Precisão estimada · {side}"
            with metric_column:
                st.metric(label, f"{accuracy:.1f}%" if accuracy is not None else "—",
                          help="Chess.com" if official is not None else "Estimativa local dos lances avaliados; não é o CAPS2.")
        st.dataframe(rows, hide_index=True, height=280)
        if len(reviews) < len(moves) and not st.session_state.official_accuracies:
            st.caption("A precisão estimada é parcial até a análise de todos os lances.")
        if unclassified:
            st.caption(f"{unclassified} lances ainda não avaliados. Os lances de livro já estão identificados.")
        else:
            st.caption("1 lance classificado." if len(moves) == 1 else f"{len(moves)} lances classificados.")
    with st.sidebar:
        st.download_button("Baixar partida PGN", export_review(game, reviews) if reviews else str(game),
                           file_name="partida.pgn", mime="application/x-chess-pgn")
