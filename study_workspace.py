"""Book reading and a separate, editable chess position in one workspace."""
from io import StringIO
import chess
import chess.pgn
import streamlit as st

from book_reader import merge_books, render_shelf, render_reader
from game_play import play_move
from interactive_board import interactive_board

PIECES = {'move': 'Mover peças', 'erase': 'Apagar peça',
          'K': '♔ Rei branco', 'Q': '♕ Dama branca', 'R': '♖ Torre branca',
          'B': '♗ Bispo branco', 'N': '♘ Cavalo branco', 'P': '♙ Peão branco',
          'k': '♚ Rei preto', 'q': '♛ Dama preta', 'r': '♜ Torre preta',
          'b': '♝ Bispo preto', 'n': '♞ Cavalo preto', 'p': '♟ Peão preto'}


def init_study():
    state = st.session_state
    for key, value in {'book_game': str(chess.pgn.Game()), 'book_ply': 0, 'book_revision': 0,
                       'book_editing': False, 'book_draft': chess.STARTING_FEN, 'book_tool': 'move',
                       'reader_book': None, 'reader_page': 0, 'book_flip': False}.items():
        state.setdefault(key, value)


def study_board():
    init_study()
    state = st.session_state
    if state.book_editing:
        return chess.Board(state.book_draft)
    game = chess.pgn.read_game(StringIO(state.book_game)) or chess.pgn.Game()
    board = game.board()
    for move in list(game.mainline_moves())[:state.book_ply]:
        board.push(move)
    return board


def apply_position_edit(fen, event):
    board = chess.Board(fen)
    target = chess.parse_square(event['to'])
    if event.get('from'):
        origin = chess.parse_square(event['from'])
        piece = board.piece_at(origin)
        if piece is None:
            raise ValueError('Não há peça na casa de origem.')
        board.remove_piece_at(origin)
        board.set_piece_at(target, piece)
    else:
        symbol = event.get('piece')
        if symbol not in ('', *'PNBRQKpnbrqk'):
            raise ValueError('Peça inválida.')
        board.set_piece_at(target, chess.Piece.from_symbol(symbol) if symbol else None)
    board.ep_square = None
    board.castling_rights = board.clean_castling_rights()
    board.clear_stack()
    return board.fen()


def edit_changed():
    state = st.session_state
    event = state.book_board.edit
    if not state.book_editing or not isinstance(event, dict) or event.get('revision') != state.book_revision:
        return
    try:
        if event.get('fen') != state.book_draft:
            return
        state.book_draft = apply_position_edit(state.book_draft, event)
        state.pop('book_error', None)
    except (ValueError, KeyError) as error:
        state.book_error = str(error)
    finally:
        state.book_revision += 1


def move_changed():
    state = st.session_state
    event = state.book_board.move
    if state.book_editing or not isinstance(event, dict) or event.get('revision') != state.book_revision:
        return
    try:
        state.book_game, state.book_ply = play_move(state.book_game, event.get('ply', state.book_ply), event['uci'], event['fen'])
        state.pop('book_error', None)
    except (KeyError, ValueError) as error:
        state.book_error = str(error)
    finally:
        state.book_revision += 1


def navigate_changed():
    state = st.session_state
    event = state.book_board.navigate
    total = len(list(chess.pgn.read_game(StringIO(state.book_game)).mainline_moves()))
    if (isinstance(event, dict) and event.get('epoch') == f'book-{state.book_revision}'
            and type(event.get('to')) is int and type(event.get('sequence')) is int
            and event['sequence'] > state.get('book_navigation_ack', 0)):
        state.book_ply = max(0, min(total, event['to']))
        state.book_navigation_ack = event['sequence']


def start_edit():
    state = st.session_state
    board = study_board()
    state.book_draft = board.fen()
    state.book_turn = 'Brancas' if board.turn else 'Pretas'
    state.book_castling = [label for label, square in [('K', chess.H1), ('Q', chess.A1), ('k', chess.H8), ('q', chess.A8)]
                           if board.castling_rights & chess.BB_SQUARES[square]]
    state.book_editing = True
    state.book_revision += 1
    state.pop('book_error', None)


def reset_draft(empty=False):
    board = chess.Board(None) if empty else chess.Board()
    st.session_state.book_draft = board.fen()
    st.session_state.book_castling = [] if empty else ['K', 'Q', 'k', 'q']
    st.session_state.book_turn = 'Brancas'
    st.session_state.book_revision += 1


def finish_edit():
    state = st.session_state
    board = chess.Board(state.book_draft)
    board.turn = state.book_turn == 'Brancas'
    board.set_castling_fen(''.join(c for c in 'KQkq' if c in state.book_castling) or '-')
    if not board.is_valid():
        state.book_error = 'Confira a posição: um rei de cada cor, sem peões na primeira ou oitava fileira, xeques e direitos de roque válidos.'
        return
    game = chess.pgn.Game()
    game.setup(board)
    state.book_game, state.book_ply = str(game), 0
    state.book_editing = False
    state.book_revision += 1
    state.pop('book_error', None)


def cancel_edit():
    st.session_state.book_editing = False
    st.session_state.book_revision += 1
    st.session_state.pop('book_error', None)


def import_fen():
    state = st.session_state
    try:
        board = chess.Board(state.book_fen_input.strip())
        state.book_draft = board.fen()
        state.book_turn = 'Brancas' if board.turn else 'Pretas'
        state.book_castling = list(board.castling_xfen().replace('-', ''))
        state.book_editing = True
        state.book_revision += 1
        state.pop('book_error', None)
    except ValueError:
        state.book_error = 'FEN inválida. Confira os seis campos da posição.'


def render_study(files, dark, table):
    init_study()
    state = st.session_state
    st.html('''<style>
    .st-key-reading_workspace{margin-top:28px;padding-top:28px;border-top:1px solid var(--chess-border)}
    .st-key-reading_workspace h3{margin-bottom:0}.st-key-reader_toolbar{gap:8px;justify-content:space-between}
    [class*="st-key-book_cover_"]{padding:18px!important;background:var(--chess-surface);border-color:var(--chess-border)!important}
    [class*="st-key-book_cover_"]:has(button[kind="primary"]){border-color:var(--chess-accent)!important}
    [class*="st-key-book_cover_"] [data-testid="stMarkdownContainer"] p{line-height:1.4;font-size:15px}
    [class*="st-key-book_cover_"] [data-testid="stImage"]{min-height:210px;display:flex;align-items:center;justify-content:center}
    .reader-prose{white-space:pre-wrap;font:19px/1.85 Georgia,'Times New Roman',serif;color:#202B26;padding:20px 16px;overflow-wrap:anywhere}
    .st-key-book_page_reader{box-shadow:0 4px 18px #00000007}
    @media(max-width:700px){.st-key-reading_workspace{margin-top:16px;padding-top:16px}.reader-prose{font-size:17px;padding:12px 6px}}
    </style>''')
    st.subheader('Biblioteca de estudo')
    def uploaded():
        selected = state[f'study_book_upload_{state.study_upload_revision}']
        state.study_files = merge_books(state.study_files, ((item.name, item.getvalue()) for item in selected))
    with st.expander('Adicionar livros à biblioteca', expanded=not files, icon=':material/library_add:'):
        st.file_uploader('Adicionar livros à biblioteca', type=['pdf', 'txt', 'md', 'pgn', 'bin'],
                         accept_multiple_files=True, key=f'study_book_upload_{state.study_upload_revision}',
                         on_change=uploaded, max_upload_size=200)
        st.caption('PDF, texto, Markdown e PGN para leitura. Arquivos Polyglot complementam as aberturas da análise.')
    if not files:
        st.info('Adicione um PDF para ver a capa e ler as páginas ao lado do tabuleiro. Você já pode montar uma posição abaixo.')
    entries = render_shelf(files)
    if state.study_files and st.button('Remover livros desta aba', icon=':material/delete:', type='tertiary'):
        state.study_files = ()
        state.study_upload_revision += 1
        state.reader_book = None
        st.rerun()
    with st.container(key='reading_workspace'):
        reader, board_column = st.columns([1, 1], gap='large')
        with reader:
            if state.reader_book in entries:
                render_reader(entries[state.reader_book])
            else:
                st.info('Selecione uma capa e clique em Abrir livro. A leitura começa na primeira página.')
        with board_column, st.container(key='study_position'):
            st.subheader('Tabuleiro de estudo')
            st.caption('Experimente as ideias do livro e monte suas próprias posições.')
            if not state.book_editing:
                st.button('Editar posição', on_click=start_edit, icon=':material/edit:')
            else:
                st.selectbox('Peça para colocar', list(PIECES), format_func=PIECES.get, key='book_tool')
                st.caption('Escolha uma peça e clique em uma casa. Use Mover peças para arrastar; Apagar peça para retirar.')
                with st.container(horizontal=True):
                    st.button('Limpar tabuleiro', on_click=reset_draft, args=(True,))
                    st.button('Posição inicial', on_click=reset_draft)
                st.selectbox('Lado a jogar', ['Brancas', 'Pretas'], key='book_turn')
                st.multiselect('Direitos de roque', ['K', 'Q', 'k', 'q'], key='book_castling',
                               format_func=lambda c: {'K': 'Brancas: pequeno', 'Q': 'Brancas: grande',
                                                     'k': 'Pretas: pequeno', 'q': 'Pretas: grande'}[c])
                with st.container(horizontal=True):
                    st.button('Concluir edição', on_click=finish_edit, type='primary')
                    st.button('Cancelar edição', on_click=cancel_edit)
            if state.get('book_error'):
                st.error(state.book_error)
            board = study_board()
            game = chess.pgn.read_game(StringIO(state.book_game))
            total = len(list(game.mainline_moves()))
            if state.get('book_navigation_revision') != state.book_revision:
                state.book_navigation_revision, state.book_navigation_ack = state.book_revision, 0
            interactive_board(board, key='book_board', on_move=move_changed,
                              revision=state.book_revision, ply=state.book_ply, total=total,
                              on_navigate=None if state.book_editing else navigate_changed,
                              epoch=f'book-{state.book_revision}', pgn=state.book_game,
                              navigation_ack=state.book_navigation_ack,
                              dark=dark, table=table,
                              editing=state.book_editing, edit_tool=state.book_tool, on_edit=edit_changed,
                              disabled=state.book_editing, flip=state.book_flip,
                              last_move=board.peek() if board.move_stack else None)
            st.toggle('Virar tabuleiro de estudo', key='book_flip', persist_state='session')
            with st.expander('Importar ou copiar posição FEN'):
                st.code(board.fen(), language=None)
                st.text_input('FEN para montar', key='book_fen_input')
                st.button('Carregar FEN no editor', on_click=import_fen)
