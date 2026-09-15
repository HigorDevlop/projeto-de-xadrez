from __future__ import annotations

from dataclasses import asdict
from html import escape
from io import StringIO
from pathlib import Path

import chess
import chess.pgn
import chess.svg
import pandas as pd
import streamlit as st

from chess_review import (BookIndex, CATEGORIES, Thresholds, analyse_game,
                          decode_text, export_review, find_engine, read_games)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Acervo • análise de xadrez", page_icon="♞", layout="wide")


@st.cache_data(max_entries=12, show_spinner=False)
def load_book(files: tuple[tuple[str, bytes], ...], max_plies: int):
    index = BookIndex()
    errors = []
    for name, data in files:
        try:
            if name.lower().endswith(".bin"):
                index.add_polyglot(data, name)
            else:
                index.add_pgn(decode_text(data), name, max_plies)
        except (ValueError, UnicodeError) as error:
            errors.append(f"{name}: {error}")
    return index, errors


def reset_game(game: chess.pgn.Game):
    st.session_state.game = str(game)
    st.session_state.ply = 0
    st.session_state.reviews = []
    st.session_state.analysis_signature = None


def jump(ply: int):
    st.session_state.ply = ply


def category_image(key: str, suffix: str = "", width: int = 310):
    cat = CATEGORIES[key]
    label = escape(f"{cat.symbol}  {cat.label}{suffix}")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="40" '
           f'viewBox="0 0 {width} 40"><rect x="1" y="1" width="{width-2}" height="38" '
           f'rx="8" fill="{cat.color}" stroke="#777777"/>'
           f'<text x="14" y="26" font-size="16" font-family="sans-serif" '
           f'font-weight="600" fill="{cat.ink}">{label}</text></svg>')
    st.image(svg, width=width)


for key, value in {"game": (ROOT / "examples/partida.pgn").read_text(encoding="utf-8"),
                   "ply": 0, "reviews": [], "analysis_signature": None}.items():
    st.session_state.setdefault(key, value)

st.title("Acervo de xadrez")
st.caption("Explore cada lance. Entenda a posição. Aprenda com a partida.")

with st.sidebar:
    st.header("Análise")
    engine_path = st.text_input("Executável do Stockfish", value=find_engine(), key="engine_path")
    if engine_path and Path(engine_path).is_file():
        st.caption("Stockfish localizado no computador.")
    else:
        st.warning("Informe o caminho do Stockfish para analisar.")
    quality = st.selectbox("Qualidade", ["Rápida", "Equilibrada", "Profunda"], index=1)
    depth, seconds = {"Rápida": (12, 0.1), "Equilibrada": (18, 0.4), "Profunda": (24, 1.5)}[quality]
    st.caption(f"Até {depth} níveis de profundidade e {seconds:g} s por busca.")
    flip = st.toggle("Pretas na parte inferior")
    st.divider()
    st.subheader("Acervo de livros")
    uploads = st.file_uploader("Carregar livros PGN ou Polyglot", type=["pgn", "bin"],
                               accept_multiple_files=True, key="books")
    demo_book = st.checkbox("Usar acervo demonstrativo", value=False)
    book_plies = st.slider("Limite de meios-lances por linha PGN", 4, 80, 40, step=2)
    st.caption("Um meio-lance é uma jogada de um dos lados. PDFs precisam ser convertidos em linhas PGN.")
    with st.expander("Critérios de classificação"):
        great = st.number_input("Ótimo: perda máxima (cp)", min_value=0, max_value=99, value=20)
        mistake = st.number_input("Ruim: perda a partir de (cp)", min_value=1, max_value=500, value=80)
        blunder = st.number_input("Péssimo: perda a partir de (cp)", min_value=2, max_value=2000, value=200)
        decisive = st.number_input("Vantagem decisiva (cp)", min_value=100, max_value=2000, value=300)
        st.caption("100 cp = 1 peão. Livro tem prioridade, depois Genial e o melhor lance da engine. "
                   "Um revés de +150 para −150 cp ou a entrada em mate forçado também é Péssimo.")
        st.caption("Genial é uma heurística: exige vantagem decisiva, perda dentro do limite de Ótimo "
                   "e sacrifício material aceito na continuação da engine. O déficit deve persistir "
                   "por duas oportunidades de recaptura, ou terminar em mate favorável. "
                   "A análise pode não reconhecer sacrifícios além do horizonte da busca.")

files = tuple((item.name, item.getvalue()) for item in uploads)
if demo_book:
    files += (("Acervo demonstrativo", (ROOT / "examples/acervo.pgn").read_bytes()),)
book, book_errors = load_book(files, book_plies)
with st.sidebar:
    st.caption(f"{book.size} entradas no acervo carregado.")
    for error in book_errors:
        st.error(error)

try:
    thresholds = Thresholds(great, mistake, blunder, decisive)
    criteria_error = None
except ValueError as error:
    thresholds = Thresholds()
    criteria_error = str(error)
    st.error(criteria_error)

with st.expander("Importar ou iniciar uma partida"):
    pgn_upload = st.file_uploader("Arquivo de partida", type="pgn", key="game_upload")
    pgn_text = st.text_area("Ou cole o PGN", height=130, placeholder="1. e4 e5 2. Nf3 Nc6 ...")
    source = decode_text(pgn_upload.getvalue()) if pgn_upload else pgn_text
    parsed = []
    if source.strip():
        try:
            parsed = read_games(source)
        except ValueError as error:
            st.error(str(error))
    chosen = st.selectbox("Partida do arquivo", range(len(parsed)),
                          format_func=lambda i: f"{i+1}. {parsed[i].headers.get('White', '?')} × "
                                                f"{parsed[i].headers.get('Black', '?')}") if parsed else 0
    with st.container(horizontal=True):
        if st.button("Carregar partida", disabled=not parsed):
            reset_game(parsed[chosen])
            st.rerun()
        if st.button("Nova partida"):
            reset_game(chess.pgn.Game())
            st.rerun()
        if st.button("Carregar exemplo"):
            reset_game(read_games((ROOT / "examples/partida.pgn").read_text(encoding="utf-8"))[0])
            st.rerun()

game = chess.pgn.read_game(StringIO(st.session_state.game))
moves = list(game.mainline_moves())
st.session_state.ply = min(st.session_state.ply, len(moves))
signature = (st.session_state.game, files, book_plies, engine_path, quality, asdict(thresholds))
if st.session_state.analysis_signature != signature:
    st.session_state.reviews = []
reviews = st.session_state.reviews

toolbar = st.container(horizontal=True, vertical_alignment="center")
with toolbar:
    run_analysis = st.button("Analisar partida", icon=":material/analytics:", type="primary",
                            disabled=not moves or not engine_path or criteria_error is not None)
    st.caption(f"{game.headers.get('White', 'Brancas')} × {game.headers.get('Black', 'Pretas')} · "
               f"{len(moves)} meios-lances · {game.headers.get('Result', '*')}")

if run_analysis:
    bar = st.progress(0, text="Preparando a engine…")
    try:
        reviews = analyse_game(game, engine_path, book, depth, seconds, thresholds,
                               lambda done, total: bar.progress(done / total,
                                                                text=f"Analisando lance {done} de {total}…"))
        st.session_state.reviews = reviews
        st.session_state.analysis_signature = signature
        st.success(f"Análise concluída: {len(reviews)} lances classificados.")
    except (ValueError, OSError, chess.engine.EngineError, TimeoutError) as error:
        st.error(f"Não foi possível concluir a análise: {error}")
    finally:
        bar.empty()

board_column, detail_column = st.columns([1.15, 1], gap="large")
with board_column:
    ply = st.session_state.ply
    with st.container(horizontal=True):
        st.button("Início", on_click=jump, args=(0,), disabled=ply == 0)
        st.button("Anterior", on_click=jump, args=(ply - 1,), disabled=ply == 0)
        st.button("Próximo", on_click=jump, args=(ply + 1,), disabled=ply == len(moves))
        st.button("Final", on_click=jump, args=(len(moves),), disabled=ply == len(moves))
    if moves:
        ply = st.slider("Posição na partida", 0, len(moves), key="ply")
    board = game.board()
    for move in moves[:ply]:
        board.push(move)
    selected = reviews[ply - 1] if reviews and ply else None
    last_move = moves[ply - 1] if ply else None
    fill = {last_move.to_square: CATEGORIES[selected.category].color + "CC"} if selected else {}
    svg = chess.svg.board(board, size=560, orientation=not flip, lastmove=last_move,
                          check=board.king(board.turn) if board.is_check() else None,
                          fill=fill, colors={"square light": "#E5DED0", "square dark": "#69746B",
                                             "margin": "#27272A", "coord light": "#E5DED0",
                                             "coord dark": "#E5DED0"})
    st.image(svg, width=560)
    if board.is_game_over():
        st.caption(f"Posição encerrada · resultado {board.result()}")
    else:
        st.caption(f"Vez das {'brancas' if board.turn else 'pretas'}" + (" · xeque" if board.is_check() else ""))
    with st.expander("Jogar a partir desta posição"):
        st.caption("Escolha um lance legal. Ao jogar de uma posição anterior, a continuação é substituída.")
        legal = sorted(board.legal_moves, key=board.san) if not board.is_game_over() else []
        with st.form("play_move"):
            choice = st.selectbox("Lance legal (notação SAN)", [m.uci() for m in legal],
                                   format_func=lambda value: board.san(chess.Move.from_uci(value)),
                                   key=f"move_{board.fen()}")
            add = st.form_submit_button("Jogar lance", disabled=not legal)
        if add and choice:
            node = game
            for _ in range(ply):
                node = node.variations[0]
            node.variations.clear()
            node.add_main_variation(chess.Move.from_uci(choice))
            after = board.copy()
            after.push_uci(choice)
            game.headers["Result"] = after.result()
            reset_game(game)
            st.session_state.ply = ply + 1
            st.rerun()
    with st.expander("Posição FEN"):
        st.code(board.fen(), language=None)

with detail_column:
    st.subheader("Leitura do lance")
    if selected:
        category_image(selected.category)
        st.subheader(f"{selected.number} {selected.san}")
        st.write(selected.explanation)
        with st.container(horizontal=True):
            evaluation = (f"M{selected.white_mate:+d}" if selected.white_mate is not None
                          else f"{selected.white_cp / 100:+.2f}")
            st.metric("Avaliação · brancas", evaluation, border=True)
            st.metric("Perda do lance", f"{selected.loss} cp", border=True)
        st.caption("Valores positivos favorecem as brancas; negativos, as pretas. M indica mate forçado.")
        st.write(f"**Melhor lance:** {selected.best_san}")
        st.write("**Continuação do lance jogado:**")
        st.code(selected.line, language=None, wrap_lines=True)
    elif reviews:
        st.info("Avance no tabuleiro para ver a classificação de cada lance.")
    else:
        st.info("Clique em Analisar partida para consultar a avaliação e as categorias.")
    with st.expander("Legenda das sete categorias", expanded=not bool(reviews)):
        for key, cat in CATEGORIES.items():
            category_image(key)
            st.caption(cat.description)

if reviews:
    st.divider()
    st.subheader("Visão geral da partida")
    counts = pd.DataFrame([{ "Categoria": c.label, "Brancas": sum(r.category == key and r.side == "Brancas" for r in reviews),
                            "Pretas": sum(r.category == key and r.side == "Pretas" for r in reviews)}
                           for key, c in CATEGORIES.items()])
    with st.expander("Contagem por jogador", expanded=True):
        st.dataframe(counts, hide_index=True)
    graph = pd.DataFrame({"Meio-lance": [r.ply for r in reviews],
                          "Avaliação (peões)": [max(-10, min(10, r.white_cp / 100)) for r in reviews]})
    st.line_chart(graph, x="Meio-lance", y="Avaliação (peões)", color="#8B5CF6")
    st.caption("Avaliação pelas brancas. O gráfico é limitado a ±10 peões; mates ficam nos extremos.")
    rows = pd.DataFrame([{"Nº": r.ply, "Lado": r.side, "Lance": f"{r.number} {r.san}",
                          "Categoria": CATEGORIES[r.category].label, "Símbolo": CATEGORIES[r.category].symbol,
                          "Perda (cp)": r.loss, "Melhor": r.best_san,
                          "Acervo": ", ".join(r.sources)} for r in reviews])
    colors = {c.label: c for c in CATEGORIES.values()}
    def paint_category(value):
        cat = colors[value]
        return f"background-color: {cat.color}; color: {cat.ink}; font-weight: bold"
    st.dataframe(rows.style.map(paint_category, subset=["Categoria"]), hide_index=True)
    with st.container(horizontal=True):
        st.download_button("Baixar PGN comentado", export_review(game, reviews),
                           file_name="partida_analisada.pgn", mime="application/x-chess-pgn")
        st.download_button("Baixar relatório CSV", rows.to_csv(index=False).encode("utf-8-sig"),
                           file_name="analise.csv", mime="text/csv")
else:
    st.download_button("Baixar partida PGN", str(game), file_name="partida.pgn", mime="application/x-chess-pgn")

st.caption("Acervo · análise local com Stockfish · resultados dependem do tempo e da profundidade da busca.")
