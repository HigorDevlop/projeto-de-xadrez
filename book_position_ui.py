"""Synchronize the study board with the selected book page and diagram."""
from io import StringIO
import chess
import chess.pgn
import streamlit as st

from book_positions import BookPositionService


_READY = st.components.v2.component(
    'book_position_ready', html='<span hidden></span>',
    js='''export default function({data}) {
      const image=document.querySelector('.book-page-image');
      const workspace=document.querySelector('.st-key-reading_workspace');
      if(!workspace || (image && (image.dataset.book!==data.identity || Number(image.dataset.page)!==data.page)))return;
      const token=(data.generation??0)+':'+data.identity+':'+data.page;
      if(workspace.dataset.readyToken===token)return;
      workspace.dataset.readyToken=token;
      document.querySelector('.st-key-book_workspace_refresh button')?.click();
    }''')


def load_position(position, turn=None):
    state = st.session_state
    game = chess.pgn.read_game(StringIO(position.pgn)) if position.pgn else None
    board = game.board() if game is not None else chess.Board(position.fen)
    if game is None or (turn is not None and turn != board.turn):
        if turn is not None and turn != board.turn:
            board.turn = turn
            # En passant belongs to the original turn, not the chosen side.
            board.ep_square = None
        game = chess.pgn.Game()
        game.setup(board)
    state.book_game = str(game)
    state.book_ply = 0
    state.book_editing = False
    state.book_revision += 1
    state.book_navigation_ack = 0
    state.pop('book_error', None)


def _restore_line(key, turn):
    st.session_state[key] = 'Brancas' if turn else 'Pretas'
    st.session_state.pop('book_page_sync', None)
    request_page_position(st.session_state.reader_book, st.session_state.reader_page)


def request_page_position(identity, page):
    state = st.session_state
    if state.reader_book == identity and state.reader_page == page:
        state.book_load_requested = identity, page


def retry_page_positions(entry):
    state = st.session_state
    identity = state._book_position_service.retry(entry, state.reader_page)
    state.book_load_requested = identity, state.reader_page
    state.book_scan_generation = state.get('book_scan_generation', 0) + 1
    state.pop('book_page_sync', None)


@st.fragment(run_every=.5)
def _await_page(identity, page):
    state = st.session_state
    if state.get('reader_book') != identity or state.get('reader_page') != page:
        return
    service = state._book_position_service
    if service.result(identity, page) is not None:
        _READY(data={'identity':identity,'page':page,'generation':state.get('book_scan_generation',0)},
               key='book_ready_notice', height=0)
        return
    st.caption('Preparando as posições desta página… O restante do livro está sendo preparado em segundo plano.')


def page_position_snapshot(entry):
    state = st.session_state
    if '_book_position_service' not in state:
        state._book_position_service = BookPositionService()
    service = state._book_position_service
    page = state.reader_page
    identity = service.prepare(entry, page)
    result = service.result(identity, page)
    return identity, page, result


def render_diagram_selector(snapshot):
    identity, page, result = snapshot
    if result is not None and len(result.positions) > 1:
        return st.selectbox('Diagrama da página', range(len(result.positions)),
                            format_func=lambda i:f'Diagrama {i+1} de {len(result.positions)}',
                            key=f'book_diagram_{identity}_{page}', label_visibility='collapsed', width=180,
                            disabled=st.session_state.book_editing)
    return 0


def change_diagram(identity, page, count, delta):
    state = st.session_state
    if state.reader_book != identity or state.reader_page != page or state.book_editing:
        return
    key = f'book_diagram_{identity}_{page}'
    state[key] = max(0, min(count-1, (state.get(key) or 0)+delta))


def render_diagram_navigation(snapshot, choice):
    identity, page, result = snapshot
    if result is None or len(result.positions) < 2:
        return
    count = len(result.positions)
    editing = st.session_state.book_editing
    with st.container(horizontal=True, vertical_alignment='center', key='book_diagram_navigation'):
        st.button('Posição anterior', icon=':material/chevron_left:', key='book_diagram_previous',
                  disabled=editing or choice == 0, on_click=change_diagram, args=(identity, page, count, -1))
        st.caption(f'Posição {choice+1} de {count} · mesma página')
        st.button('Próxima posição', icon=':material/chevron_right:', key='book_diagram_next',
                  disabled=editing or choice == count-1, on_click=change_diagram, args=(identity, page, count, 1))


def render_page_positions(entry, *, poll=True, snapshot=None, diagram_choice=None):
    state = st.session_state
    identity, page, result = snapshot or page_position_snapshot(entry)
    if result is None:
        st.button('Carregar posição da página', key='load_book_page_pending', icon=':material/extension:',
                  disabled=state.book_editing, on_click=request_page_position, args=(identity, page))
        if poll:
            _await_page(identity, page)
        else:
            return identity, page
        return
    if result.notice:
        st.caption(result.notice)
    if not result.positions:
        if state.get('book_load_requested') == (identity, page):
            state.pop('book_load_requested', None)
        state.book_page_sync = (identity, page, None)
        st.caption('Nenhuma posição identificada com segurança. Você pode tentar uma leitura mais detalhada desta página.')
        st.button('Carregar posição da página', key='retry_book_page_position', icon=':material/extension:',
                  disabled=state.book_editing, on_click=retry_page_positions, args=(entry,))
        return
    choice = diagram_choice if diagram_choice is not None else 0
    if len(result.positions) > 1 and diagram_choice is None:
        choice = st.selectbox('Posição da página', range(len(result.positions)),
                              format_func=lambda i: f'{i+1} · {result.positions[i].label}',
                              key=f'book_diagram_{identity}_{page}')
    position = result.positions[choice]
    key = f'book_diagram_turn_{identity}_{page}_{choice}'
    state.setdefault(key, 'Brancas' if chess.Board(position.fen).turn else 'Pretas')
    selected = st.segmented_control(
        'Quem joga nesta posição?', ['Brancas', 'Pretas'], required=True, key=key,
        help='Escolha o lado e clique em Carregar posição da página para explorar o diagrama.'
             ' Em um PGN, a linha do livro volta quando você restaura o lado original.')
    side = selected == 'Brancas'
    if not position.turn_known:
        st.caption('O livro não indica a vez de jogar. Escolha o lado acima.')
    token = identity, page, choice, side
    st.button('Carregar posição da página', key='load_book_page_position', icon=':material/extension:',
              disabled=state.book_editing, on_click=request_page_position, args=(identity, page))
    requested = state.get('book_load_requested') == (identity, page)
    if requested:
        if state.book_editing:
            st.caption('Você está editando uma posição. Salve ou cancele para acompanhar a nova página.')
            if st.button('Usar posição da página', key='use_book_page_position'):
                load_position(position, side)
                state.book_page_sync = token
                state.pop('book_load_requested', None)
        else:
            load_position(position, side)
            state.book_page_sync = token
            state.pop('book_load_requested', None)
    st.caption(f'{position.label} · página {page+1} · {position.source}',
               help=None if position.castling_known else 'Roques não informados no diagrama. Ajuste-os em Editar posição, se necessário.')
    with st.expander('Reexaminar os diagramas desta página'):
        st.caption('Use se algum diagrama não apareceu. O PDF será examinado novamente em maior resolução.')
        st.button('Reexaminar página', key='retry_book_diagrams', on_click=retry_page_positions, args=(entry,),
                  disabled=state.book_editing)
    if st.button('Restaurar posição do livro', key='restore_book_position', disabled=state.book_editing,
                 help='Volta ao diagrama original para recomeçar o exercício.'):
        load_position(position, side)
    if position.pgn:
        original = chess.pgn.read_game(StringIO(position.pgn))
        moves = list(original.mainline_moves()) if original else []
        if moves:
            st.markdown('**Linha do livro**')
            st.code(position.pgn, language=None)
            if side != original.board().turn:
                st.caption('Restaure o lado indicado pelo livro para percorrer esta linha.')
            st.button('Ver linha do livro', key='restore_book_line', disabled=state.book_editing,
                      on_click=_restore_line, args=(key, original.board().turn))
