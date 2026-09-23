"""Local book pages: original PDF artwork, bounded rendering, text pagination."""
from hashlib import sha256
from html import escape
from io import BytesIO
from pathlib import Path
from threading import RLock
import textwrap

import streamlit as st
from pypdf import PdfReader

from chess_review import decode_text

_PDF_LOCK = RLock()  # PDFium cannot execute concurrently, even for separate books.


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
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('PDF protegido por senha; use uma cópia desbloqueada.')
        count = len(reader.pages)
        if not 0 < count <= 1000:
            raise ValueError('Use um PDF com 1 a 1.000 páginas.')
        return {'title': title, 'count': count, 'kind': 'pdf'}
    if name.lower().endswith('.bin'):
        return {'title': title, 'count': 0, 'kind': 'opening'}
    text = decode_text(data)
    # Honor real page breaks; otherwise wrap into readable, stable text pages.
    pages = []
    for section in text.split('\f'):
        lines = []
        for paragraph in section.splitlines():
            lines.extend(textwrap.wrap(paragraph, 85, replace_whitespace=False) or [''])
        pages.extend('\n'.join(lines[i:i + 38]) for i in range(0, len(lines), 38))
    return {'title': title, 'count': max(1, len(pages)), 'kind': 'text', 'pages': pages or ['']}


@st.cache_data(max_entries=48, show_spinner=False)
def pdf_page(data, index, width=1100):
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
    st.session_state.reader_book = identity
    st.session_state.reader_page = 0
    st.session_state.reader_page_input = 1


def turn_page(delta, count):
    state = st.session_state
    state.reader_page = max(0, min(count - 1, state.reader_page + delta))
    state.reader_page_input = state.reader_page + 1


def page_input_changed(count):
    state = st.session_state
    state.reader_page = max(0, min(count - 1, int(state.reader_page_input) - 1))


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
    columns = st.columns(4)
    for index, (name, data) in enumerate(files):
        identity = book_id(name, data)
        with columns[index % 4], st.container(border=True, key=f'book_cover_{identity}'):
            try:
                info = book_info(name, data)
                book_cover(name, data, info)
                st.write(info['title'])
                if info['count']:
                    readable[identity] = (name, data, info)
                    st.caption(f"{info['count']} páginas")
                    st.button('Abrir livro', key=f'open_book_{identity}', on_click=open_book,
                              args=(identity,), width='stretch')
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
    st.markdown(f'**{info["title"]}**')
    with st.container(horizontal=True, vertical_alignment='center'):
        st.button('Página anterior', icon=':material/chevron_left:', key='reader_previous',
                  disabled=state.reader_page == 0, on_click=turn_page, args=(-1, count))
        st.caption(f'Página {state.reader_page + 1} de {count}')
        st.button('Próxima página', icon=':material/chevron_right:', key='reader_next',
                  disabled=state.reader_page == count - 1, on_click=turn_page, args=(1, count))
    st.number_input('Ir para a página', min_value=1, max_value=count, value=state.reader_page + 1,
                    step=1, key='reader_page_input', on_change=page_input_changed, args=(count,))
    with st.container(height=680, border=True, key='book_page_reader'):
        try:
            if info['kind'] == 'pdf':
                st.image(pdf_page(data, state.reader_page), width='stretch')
            else:
                st.text(info['pages'][state.reader_page])
        except Exception as error:
            st.error(f'Não foi possível abrir esta página: {error}')

