"""Local book pages: original PDF artwork, bounded rendering, text pagination."""
from hashlib import sha256
from base64 import b64encode
from html import escape
from io import BytesIO
from pathlib import Path
from threading import RLock
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, wait
import re
import textwrap

import streamlit as st
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from chess_review import decode_text

_PDF_LOCK = RLock()  # PDFium cannot execute concurrently, even for separate books.


class ReaderPageCache:
    """Small per-session image buffer; adjacent pages are ready before navigation."""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='reader-images')
        self.pages = OrderedDict()

    def nearby(self, identity, entry, index):
        _, data, info = entry
        wanted = [index, *range(index+1, min(info['count'], index+3))]
        if index:
            wanted.append(index-1)
        wanted_keys = {(identity, page) for page in wanted}
        for key in list(self.pages):
            if key not in wanted_keys and self.pages[key].cancel():
                del self.pages[key]
        for page in wanted:
            key = identity, page
            if key not in self.pages:
                self.pages[key] = self.executor.submit(pdf_page, data, page)
            self.pages.move_to_end(key)
        # A tiny bounded buffer also keeps recently visited pages decoded.
        for key in list(self.pages):
            if len(self.pages) <= 10:
                break
            if key not in wanted_keys and self.pages[key].done():
                del self.pages[key]
        current = self.pages[identity, index].result()
        wait([self.pages[key] for key in wanted_keys], timeout=.2)
        ready = {page: future.result() for (book, page), future in self.pages.items()
                 if (book, page) in wanted_keys and future.done() and not future.cancelled() and future.exception() is None}
        ready[index] = current
        return ready

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=True)


def reader_title(title):
    title = re.sub(r'(?i)^toaz[._ -]*info[-_ ]*', '', title)
    title = re.sub(r'(?i)(?:[-_]pr)?[-_][a-f0-9]{24,}$', '', title)
    return re.sub(r'[-_]+', ' ', title).strip() or 'Livro'


def book_id(name, data):
    return sha256(name.encode() + b'\0' + data).hexdigest()


def merge_books(existing, incoming):
    books = {book_id(name, data): (name, data) for name, data in existing}
    for name, data in incoming:
        books[book_id(name, data)] = (name, data)
    return tuple(books.values())


@st.cache_data(max_entries=32, show_spinner=False)
def book_info(name, data):
    title = Path(name).stem
    if name.lower().endswith('.pdf'):
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise ValueError('PDF protegido por senha; use uma cópia desbloqueada.')
            count = len(reader.pages)
        except PyPdfError as error:
            raise ValueError('PDF inválido ou incompleto. Use uma cópia íntegra do arquivo.') from error
        if not 0 < count <= 1000:
            raise ValueError('Use um PDF com 1 a 1.000 páginas.')
        return {'title': title, 'count': count, 'kind': 'pdf'}
    if name.lower().endswith('.bin'):
        return {'title': title, 'count': 0, 'kind': 'opening'}
    text = decode_text(data)
    if name.lower().endswith('.pgn'):
        import chess.pgn
        from io import StringIO
        source = StringIO(text)
        games = []
        while game := chess.pgn.read_game(source):
            if game.errors:
                raise ValueError('O PGN contém um lance inválido.')
            games.append(str(game))
        if games:
            return {'title': title, 'count': len(games), 'kind': 'text', 'pages': games, 'pgn': True}
    # Honor real page breaks; otherwise wrap into readable, stable text pages.
    pages = []
    for section in text.split('\f'):
        lines = []
        for paragraph in section.splitlines():
            lines.extend(textwrap.wrap(paragraph, 85, replace_whitespace=False) or [''])
        pages.extend('\n'.join(lines[i:i + 38]) for i in range(0, len(lines), 38))
    return {'title': title, 'count': max(1, len(pages)), 'kind': 'text', 'pages': pages or ['']}


@st.cache_data(max_entries=48, show_spinner=False)
def pdf_page(data, index, width=1600):
    import pypdfium2 as pdfium
    with _PDF_LOCK, pdfium.PdfDocument(data) as document:
        if not 0 <= index < len(document):
            raise ValueError('Página fora do livro.')
        page = document[index]
        try:
            w, h = page.get_size()
            if w <= 0 or h <= 0:
                raise ValueError('A página não tem dimensões válidas.')
            scale = min(width / w, 2200 / h)
            bitmap = page.render(scale=scale)
            try:
                output = BytesIO()
                bitmap.to_pil().save(output, format='PNG')
                return output.getvalue()
            finally:
                bitmap.close()
        finally:
            page.close()


def open_book(identity):
    state = st.session_state
    state.book_options_open = False
    if state.get('reader_book') != identity:
        import chess.pgn
        state.book_game = str(chess.pgn.Game())
        state.book_ply = 0
        state.book_revision = state.get('book_revision', 0) + 1
        state.book_editing = False
        state.book_follow_positions = False
        state.pop('book_page_sync', None)
        state.pop('book_load_requested', None)
    state.reader_book = identity
    state.reader_page = 0
    state.reader_page_input = 1
    state.reader_epoch = state.get('reader_epoch', 0) + 1
    state.reader_navigation_ack = 0


def turn_page(delta, count):
    state = st.session_state
    state.reader_page = max(0, min(count - 1, state.reader_page + delta))
    state.reader_page_input = state.reader_page + 1


def page_input_changed(count):
    state = st.session_state
    state.reader_page = max(0, min(count - 1, int(state.reader_page_input) - 1))
    state.reader_epoch = state.get('reader_epoch', 0) + 1
    state.reader_navigation_ack = 0


def navigate_reader(count):
    """Apply the latest absolute target, ignoring superseded book events."""
    state = st.session_state
    event = getattr(state.get('study_focus_control'), 'navigate', None)
    if not isinstance(event, dict):
        return
    page, sequence = event.get('page'), event.get('sequence')
    if (event.get('book') != state.reader_book
            or event.get('epoch') != state.get('reader_epoch', 0)
            or type(page) is not int or type(sequence) is not int
            or sequence <= state.get('reader_navigation_ack', 0)):
        return
    state.reader_page = max(0, min(count - 1, page))
    state.reader_page_input = state.reader_page + 1
    state.reader_navigation_ack = sequence


def book_cover(name, data, info):
    if info['kind'] == 'pdf':
        st.image(pdf_page(data, 0, 280), width='stretch')
    else:
        label = 'ABERTURAS' if info['kind'] == 'opening' else Path(name).suffix.lstrip('.').upper()
        st.html(f'<div class="book-cover" role="img" aria-label="Capa de {escape(info["title"])}">'
                f'<small>{label}</small><strong>{escape(info["title"])}</strong><span>♞</span></div>')


def render_shelf(files):
    state = st.session_state
    readable = {}
    if not files:
        return readable
    st.caption(f'{len(files)} {"livro na biblioteca" if len(files) == 1 else "livros na biblioteca"} · escolha uma capa para começar')
    columns = st.columns(4, gap='large')
    for index, (name, data) in enumerate(files):
        identity = book_id(name, data)
        with columns[index % 4], st.container(border=True, key=f'book_cover_{identity}'):
            try:
                info = book_info(name, data)
                book_cover(name, data, info)
                st.markdown(f'**{escape(info["title"])}**')
                if info['count']:
                    readable[identity] = (name, data, info)
                    selected = state.get('reader_book') == identity
                    st.caption(f"{info['count']} páginas" + (' · Em leitura' if selected else ''))
                    st.button('Abrir livro', key=f'open_book_{identity}', on_click=open_book,
                              args=(identity,), width='stretch', icon=':material/menu_book:',
                              type='primary' if selected else 'secondary')
                else:
                    st.caption('Livro de aberturas Polyglot: usado na análise, sem páginas de leitura.')
            except Exception as error:
                st.warning(f'{name}: {error}')
    if state.get('reader_book') not in readable:
        state.reader_book = None
    return readable


def render_reader(entry):
    name, data, info = entry
    state = st.session_state
    count = info['count']
    state.reader_page = max(0, min(count - 1, state.get('reader_page', 0)))
    with st.container(key="reader_heading"):
        st.html(f'<h3 class="reader-title" title="{escape(info["title"], quote=True)}">{escape(reader_title(info["title"]))}</h3>')
    st.html('''<style>
    .reader-title{font:600 18px/1.4 system-ui!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:0 0 8px}
    .st-key-book_page_reader{padding:0!important;overflow:visible!important;border:0!important}
    .book-page-image{display:block;width:100%;height:auto;
      object-fit:contain;background:#fff;border-radius:8px}
    .st-key-book_page_reader .reader-prose{font-size:19px;line-height:1.7;padding:18px;
      background:#fff;border-radius:8px;margin:0}
    </style>''')
    with st.container(border=False, key='book_page_reader'):
        try:
            if info['kind'] == 'pdf':
                if '_reader_page_cache' not in state:
                    state._reader_page_cache = ReaderPageCache()
                identity = state.get('reader_book') or book_id(name, data)
                ready = state._reader_page_cache.nearby(identity, entry, state.reader_page)
                encoded = {page: b64encode(value).decode('ascii') for page, value in ready.items()}
                source = encoded[state.reader_page]
                preloads = ''.join(f'<img data-page="{page}" src="data:image/png;base64,{value}">' for page, value in encoded.items())
                st.html(f'<img class="book-page-image" data-book="{identity}" data-page="{state.reader_page}" '
                        f'alt="Página {state.reader_page + 1} de {escape(info["title"])}" '
                        f'src="data:image/png;base64,{source}"><div class="book-page-preloads" hidden>{preloads}</div>')
            else:
                st.html('<article class="reader-prose">' + escape(info['pages'][state.reader_page]) + '</article>')
        except Exception as error:
            st.error(f'Não foi possível abrir esta página: {error}')
    with st.container(horizontal=True, vertical_alignment='center', key='reader_toolbar'):
        st.button('Página anterior', icon=':material/chevron_left:', key='reader_previous',
                  disabled=state.reader_page == 0, on_click=turn_page, args=(-1, count))
        with st.popover(f'Página {state.reader_page + 1} de {count}'):
            st.number_input('Ir para a página', min_value=1, max_value=count,
                            step=1, key='reader_page_input', on_change=page_input_changed, args=(count,))
        st.button('Próxima página', icon=':material/chevron_right:', key='reader_next',
                  disabled=state.reader_page == count - 1, on_click=turn_page, args=(1, count))
