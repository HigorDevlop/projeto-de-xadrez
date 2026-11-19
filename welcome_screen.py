"""Local, offline welcome artwork and shared entry layout."""
from base64 import b64encode
from pathlib import Path
import streamlit as st


@st.cache_data(show_spinner=False)
def artwork_source():
    return 'data:image/jpeg;base64,' + b64encode((Path(__file__).parent / 'assets/welcome-king.jpg').read_bytes()).decode()


def entry_style():
    st.html('''<style>
    [data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
    .st-key-coach_entrance{max-width:1500px;margin:clamp(0px,4vh,50px) auto}
    .entry-brand{font:700 19px/1.4 system-ui;letter-spacing:-.4px;color:#eee;margin-bottom:28px}
    .entry-brand span{color:#d5ac6b;font-size:11px;letter-spacing:3px;margin-left:14px;font-weight:500}
    .legends-art{position:relative;overflow:hidden;border-radius:20px;border:1px solid #17617b;background:#020d20;box-shadow:0 24px 80px #0007}
    .legends-art img{display:block;width:100%;height:auto}
    .legends-names{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:15px 12px;background:#04172c;border-top:1px solid #17617b66;text-align:center;font:600 11px/1.5 system-ui;color:#9fd9ec;letter-spacing:1.2px;text-transform:uppercase}
    .entry-kicker{font:600 10px/1.5 system-ui;letter-spacing:3px;color:#ccaa72;margin:27px 0 12px}
    .entry-headline{font:600 clamp(27px,3.1vw,46px)/1.14 system-ui;letter-spacing:-1.4px;color:#f4f1eb;margin:0 0 14px;max-width:680px}
    .entry-description{font:14px/1.7 system-ui;color:#aaa49a;margin:0;max-width:570px}
    .entry-tribute{font:10px/1.6 system-ui;color:#746f66;margin:14px 0 0}
    .st-key-entry_access{background:linear-gradient(145deg,#06213a,#031428);border:1px solid #17617b;border-radius:20px;padding:clamp(20px,3vw,40px);box-shadow:inset 0 1px #ffffff08,0 15px 45px #0003}
    .st-key-entry_access h2{font-size:26px;letter-spacing:-.6px}
    .st-key-entry_access button[kind="primaryFormSubmit"],.st-key-entry_access button[kind="primary"]{min-height:48px}
    @media(max-width:750px){.entry-brand{margin-bottom:14px}.entry-brand span{font-size:9px;letter-spacing:1px}.entry-headline{letter-spacing:-.7px}.legends-names{font-size:9px;padding:11px 5px}.st-key-coach_entrance{margin:0 auto}.st-key-entry_access{padding:20px}}
    </style>''')


def hero():
    st.html('<div class="entry-brand">Coach Chess <span>ESTUDO DE XADREZ</span></div>'
        '<section class="legends-art" aria-label="Peças de xadrez">'
        '<img src="'+artwork_source()+'" alt="Fotografia de um rei preto de pé entre peças brancas derrubadas"/>'
        '<div class="legends-names"><span>Aberturas</span><span>Táticos</span><span>Análise</span><span>Finais</span></div></section>'
        '<p class="entry-kicker">ESTUDE COM MÉTODO. ENCONTRE SEU JOGO.</p>'
        '<h1 class="entry-headline">A próxima grande ideia<br>pode ser sua.</h1>'
        '<p class="entry-description">Estude suas partidas, aprenda novas linhas e treine seu olhar. '
        'Um lance de cada vez.</p>'
        '<p class="entry-tribute">Fotografia em domínio público (CC0) · rawpixel.</p>')


def remembered_entry(user):
    """An authenticated device enters directly without another welcome gate."""
    st.session_state.welcome_entered = True
