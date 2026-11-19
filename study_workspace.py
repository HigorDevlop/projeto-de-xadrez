"""Book reading and a separate, editable chess position in one workspace."""
from io import StringIO
import chess
import chess.pgn
import streamlit as st

from book_reader import book_info, render_shelf, render_reader
from book_library import BookLibrary
from book_positions import BookPositionService
from game_play import play_move
from interactive_board import interactive_board
from book_position_ui import render_page_positions, page_position_snapshot, render_diagram_selector, render_diagram_navigation, _await_page
from study_focus import render_focus_button

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
        available = chess.Board(state.book_draft).castling_xfen()
        state.book_castling = [c for c in state.book_castling if c in available]
        state.pop('book_error', None)
    except (ValueError, KeyError) as error:
        state.book_error = str(error)
    finally:
        state.book_revision += 1


def move_changed():
    apply_study_move(st.session_state.book_board.move)


def move_sync():
    apply_study_move(st.session_state.book_board.sync)


def apply_study_move(event):
    state = st.session_state
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
    state.book_options_open = True
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
    turn = state.book_turn == 'Brancas'
    if board.turn != turn:
        board.ep_square = None
    board.turn = turn
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


def restart_study_board():
    """Start a fresh board without changing the book, page or orientation."""
    state = st.session_state
    state.book_game = str(chess.pgn.Game())
    state.book_ply = 0
    state.book_editing = False
    state.book_draft = chess.STARTING_FEN
    state.book_revision += 1
    for key in ('book_error', 'book_load_requested', 'book_page_sync'):
        state.pop(key, None)


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
        state.book_options_open = True
        state.book_revision += 1
        state.pop('book_error', None)
    except ValueError:
        state.book_error = 'FEN inválida. Confira os seis campos da posição.'


@st.fragment(run_every=2)
def render_preload_progress(entries):
    service = st.session_state._book_position_service
    for identity, (_, _, info) in entries.items():
        done, total, review = service.preload_progress(identity)
        if total:
            st.progress(done / total, text=f'{info["title"]} · {done}/{total} páginas preparadas')
            if review:
                st.caption(f'{review} páginas podem precisar de revisão manual no editor.')


def render_study(files, dark, table):
    init_study()
    state = st.session_state
    library = BookLibrary()
    owner = state.get('_book_library_owner', ('', 'local'))[1]
    if '_book_position_service' not in state:
        state._book_position_service = BookPositionService()
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
    def uploaded():
        selected = state[f'study_book_upload_{state.study_upload_revision}']
        try:
            incoming = tuple((item.name, item.getvalue()) for item in selected)
            for name, data in incoming:
                book_info(name, data)
            state.study_files = library.add(owner, incoming)
            state.pop('book_upload_error', None)
        except (ValueError, OSError) as error:
            state.book_upload_error = str(error)

    def upload_control():
        st.file_uploader('Adicionar livros à biblioteca', type=['pdf', 'txt', 'md', 'pgn', 'bin'],
                         accept_multiple_files=True, key=f'study_book_upload_{state.study_upload_revision}',
                         on_change=uploaded, max_upload_size=500, label_visibility='collapsed')
        st.caption('PDF · TXT · Markdown · PGN · salvos neste computador')
        st.caption('Polyglot (.bin): livros de aberturas para a análise.')

    with st.expander('Biblioteca', expanded=not bool(state.reader_book), icon=':material/local_library:'):
        used = library.used()
        st.caption(f'{used / (1024 * 1024):.1f} MB de 500 MB utilizados pelos livros')
        if state.get('book_upload_error'):
            st.error(state.book_upload_error)
        with st.container(border=True, key='study_library'):
            introduction, upload = st.columns([1, 1.4], gap='medium', vertical_alignment='center')
            with introduction:
                st.subheader(':material/local_library: Biblioteca de estudo')
                st.caption('Seu próximo aprendizado começa em uma página.')
                st.badge(f'{len(files)} ' + ('arquivo na biblioteca' if len(files) == 1 else 'arquivos na biblioteca'),
                         icon=':material/book_2:', color='gray')
            with upload:
                if files:
                    with st.expander('Adicionar livros', icon=':material/library_add:'):
                        upload_control()
                else:
                    upload_control()
        entries = render_shelf(files)
        for entry in entries.values():
            state._book_position_service.preload(entry)
        render_preload_progress(entries)
        if state.study_files and st.button('Remover todos os livros da biblioteca', icon=':material/delete:', type='tertiary'):
            library.remove_all(owner)
            state._book_position_service.cancel_preloads()
            state.study_files = ()
            state.library_uploads = ()
            state.study_upload_revision += 1
            state.reader_book = None
            st.rerun()
    render_reading_workspace(entries, files, dark, table)


@st.fragment
def render_reading_workspace(entries, files, dark, table):
    state = st.session_state
    with st.container(key='reading_workspace'):
        if state.reader_book in entries:
            render_focus_button(entries[state.reader_book][2]['count'])
            st.button('Atualizar posição preparada', key='book_workspace_refresh')
        reader, board_column = st.columns([1, 1], gap='medium')
        with reader, st.container(border=True, key='study_reading_panel'):
            if state.reader_book in entries:
                render_reader(entries[state.reader_book])
            else:
                st.subheader('Um livro aberto. Novas possibilidades.')
                with st.container(horizontal_alignment='center', gap='small'):
                    st.space('medium')
                    st.markdown('# :material/auto_stories:')
                    st.markdown('**Seu espaço de leitura**')
                    st.caption('Escolha uma capa e clique em Abrir livro.' if files else
                               'Adicione seu primeiro livro na biblioteca acima.')
                    st.caption('As páginas aparecem aqui, ao lado das suas ideias no tabuleiro.')
                    st.space('medium')
                st.divider()
                st.markdown(':material/menu_book: **Leia no seu ritmo**')
                st.caption('Percorra as páginas e volte aos trechos que merecem atenção.')
                st.markdown(':material/extension: **Leve a ideia ao tabuleiro**')
                st.caption('Use Editar posição para reproduzir um diagrama e explorar os lances.')
                st.markdown(':material/bookmark: **Construa seu repertório**')
                st.caption('Conecte cada conceito à prática, uma posição de cada vez.')
        with board_column, st.container(key='study_position', border=True):
            render_study_board(entries, dark, table)


@st.fragment
def render_study_board(entries, dark, table):
    state = st.session_state
    pending_page = None
    snapshot = page_position_snapshot(entries[state.reader_book]) if state.reader_book in entries else None
    with st.container(key='study_board_heading'):
        st.subheader('Tabuleiro', anchor=False)
    board_area = st.container()
    with st.container(key='book_study_controls'), st.expander(
            'Opções de estudo', expanded=False, key='book_options_open',
            on_change='rerun', icon=':material/tune:'):
        choice = render_diagram_selector(snapshot) if snapshot else 0
        if snapshot:
            pending_page = render_page_positions(entries[state.reader_book], poll=False,
                                                 snapshot=snapshot, diagram_choice=choice)
            render_diagram_navigation(snapshot, choice)
        if not state.book_editing:
            st.button('Editar posição', on_click=start_edit, icon=':material/edit:')
        st.button('Reiniciar tabuleiro', on_click=restart_study_board, icon=':material/restart_alt:')
        st.toggle('Virar tabuleiro de estudo', key='book_flip', persist_state='session')
        with st.expander('Importar ou copiar posição FEN'):
            st.code(study_board().fen(), language=None)
            st.text_input('FEN para montar', key='book_fen_input')
            st.button('Carregar FEN no editor', on_click=import_fen)
        if state.book_editing:
            render_book_editor()
    with board_area:
        render_book_board(dark, table, pending_page)


def render_book_board(dark, table, pending_page=None):
    state = st.session_state
    board = study_board()
    game = chess.pgn.read_game(StringIO(state.book_game))
    total = len(list(game.mainline_moves()))
    if state.get('book_navigation_revision') != state.book_revision:
        state.book_navigation_revision, state.book_navigation_ack = state.book_revision, 0
    interactive_board(board, key='book_board', on_move=move_changed,
                      on_sync=None if state.book_editing else move_sync,
                      revision=state.book_revision, ply=state.book_ply, total=total,
                      on_navigate=None if state.book_editing else navigate_changed,
                      epoch=f'book-{state.book_revision}', pgn=state.book_game,
                      navigation_ack=state.book_navigation_ack,
                      dark=dark, table=table, aligned=True, stable_board=True, instant_moves=True,
                      editing=state.book_editing, edit_tool=state.book_tool, on_edit=edit_changed,
                      turn_override=(state.book_turn == 'Brancas') if state.book_editing else None,
                      disabled=state.book_editing, flip=state.book_flip,
                      last_move=board.peek() if board.move_stack else None)
    if pending_page:
        _await_page(*pending_page)
    if state.get('book_error'):
        st.error(state.book_error)


def render_book_editor():
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
