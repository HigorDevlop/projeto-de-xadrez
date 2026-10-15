"""Identidade editorial e estilos comuns às páginas do Acervo."""
from html import escape
import streamlit as st
from chess_review import CATEGORIES
from design_tokens import palette


def classification_legend():
    with st.expander(f'Legenda dos {len(CATEGORIES)} tipos de lance'):
        entries = ''.join(f'<li><span class="quality-key" style="background:{c.color};color:{c.ink}" aria-hidden="true">{escape(c.symbol)}</span><div><strong>{escape(c.label)}</strong><p>{escape(c.description)}</p></div></li>' for c in CATEGORIES.values())
        st.html(f'<ul class="quality-legend" aria-label="{len(CATEGORIES)} classificações de lances">{entries}</ul>')


def brand():
    st.html('<div class="club-brand"><span class="club-emblem" aria-hidden="true">♞</span><div><strong>Acervo</strong><small>CLUBE DE ESTUDO</small></div></div>')


def page_heading(name):
    headings = {
        'Partida': ('01 / SEU PAINEL', 'Seu xadrez, em perspectiva.', 'Volte às suas partidas, entenda suas escolhas e prepare a próxima boa jogada.'),
        'Análise': ('02 / LABORATÓRIO', 'Análise de partidas', 'Explore cada posição, compare as escolhas e descubra o que o tabuleiro revela.'),
        'Anotações': ('03 / CADERNO', 'Suas ideias, lance a lance.', 'Acompanhe as jogadas e guarde as descobertas da partida.'),
        'Estudo com livros': ('04 / BIBLIOTECA', 'Leia. Jogue. Entenda.', 'Abra um livro e leve cada ideia das páginas para o tabuleiro.'),
        'Tático': ('05 / PRÁTICA', 'Treine o olhar.', 'Reconheça padrões, calcule possibilidades e encontre a continuação certa.'),
        'Preparo': ('06 / SEU PERCURSO', 'Preparo', 'Escolha até quatro aberturas e comece sua trilha.'),
        'Aberturas': ('07 / REPERTÓRIO', 'Aberturas', 'Aprenda e memorize seu repertório, no seu ritmo.'),
    }
    eyebrow, title, description = headings[name]
    with st.container(key='page_heading'):
        st.html(f'<span class="section-overline">{eyebrow}</span>')
        st.title(title)
        st.caption(description)


def apply_theme(dark):
    p = palette(dark)
    variables = ';'.join(f'--chess-{key.replace("_", "-")}:{value}' for key,value in p.items())
    move_colors = ''.join(f'[class*="st-key-move_quality_{key}_"] button{{background:{c.color}!important;color:{c.ink}!important;border:2px solid {c.ink}!important;min-height:44px}}[class*="st-key-move_quality_{key}_"] button *{{color:{c.ink}!important;background:transparent!important}}' for key,c in CATEGORIES.items())
    st.html('<style>:root{color-scheme:'+('dark' if dark else 'light')+';'+variables+'}'+STYLE+move_colors+'</style>')


STYLE = '''
:root{--club-ui:'Segoe UI',system-ui,-apple-system,sans-serif;--club-display:Georgia,'Times New Roman',serif}
.stApp{color:var(--chess-ink);background:var(--chess-background);font-family:var(--club-ui)}
.stMainBlockContainer{max-width:1600px;padding:4.8rem 4.6rem 4rem}
[data-testid="stHeader"]{background:var(--chess-background);border-bottom:1px solid var(--chess-border);height:58px}
[data-testid="stSidebar"]{background:var(--chess-surface);color:var(--chess-ink);border-right:1px solid var(--chess-border)}
[data-testid="stSidebarContent"]{padding-top:1.3rem}
.stApp h1,.stApp h2,.stApp h3{color:var(--chess-ink);font-family:var(--club-display);letter-spacing:-.035em;font-weight:500;line-height:1.2}
.stApp h1{font-size:clamp(2rem,3.2vw,3.25rem)}.stApp h2{font-size:1.8rem}.stApp h3{font-size:1.4rem}
.stApp p,.stApp label,.stApp summary,.stApp small,.stApp button,.stApp [data-testid="stMetricValue"]{color:var(--chess-ink);font-family:var(--club-ui)}
.stApp p{line-height:1.65}.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] *{color:var(--chess-muted)!important;opacity:1}
.stApp [data-testid="stIconMaterial"]{color:inherit}.stApp a{color:var(--chess-accent);text-underline-offset:4px}
.stAppDeployButton,[data-testid="stAppDeployButton"],[data-testid="stMainMenu"],#MainMenu{display:none}
.club-brand{display:flex;gap:12px;align-items:center;margin:2px 0 28px}.club-emblem{display:grid;place-items:center;width:44px;height:48px;background:var(--chess-accent-soft);color:var(--chess-accent);border-radius:10px;font:36px/1 Georgia,serif}
.club-brand strong{display:block;font:500 29px/1.1 var(--club-display);letter-spacing:-.04em;color:var(--chess-ink)}
.club-brand small{display:block;font:650 9px/1.8 var(--club-ui);letter-spacing:.2em;color:var(--chess-muted)}
.st-key-workspace_identity{gap:16px;padding-bottom:18px;border-bottom:1px solid var(--chess-border);margin-bottom:12px}
.st-key-sidebar_profile{margin:2px 0 12px;padding:4px 0 14px;border-bottom:1px solid var(--chess-border);gap:12px}.st-key-sidebar_profile p{line-height:1.25;margin:0}
.st-key-sidebar_profile [data-testid="stCaptionContainer"] p{font-size:11px}.st-key-sidebar_profile .avatar{border-radius:50%;width:52px;height:52px;font-size:23px}
.st-key-workspace_identity p{margin-bottom:0;font-size:15px}.st-key-workspace_identity [data-testid="stCaptionContainer"] p{font-size:12px}
.workspace-wordmark{font:500 21px/1.2 var(--club-display);color:var(--chess-ink);letter-spacing:-.03em}.workspace-wordmark small{display:block;font:11px/1.8 var(--club-ui);letter-spacing:.06em;color:var(--chess-muted)}
.st-key-page_heading{padding:16px 0 26px;margin-bottom:12px;gap:6px}.section-overline{font:650 10px/1.7 var(--club-ui);letter-spacing:.19em;color:var(--chess-gold)}
.st-key-page_heading h1{padding:6px 0 8px}.st-key-page_heading [data-testid="stCaptionContainer"] p{font-size:15px;max-width:760px}
.stApp:has(.st-key-home_shortcuts) .stMainBlockContainer{padding:3.2rem 1.2rem 0}
.stApp:has(.st-key-home_shortcuts) .st-key-page_heading{padding:0;margin-bottom:0;gap:6px}
.stApp:has(.st-key-home_shortcuts) .st-key-page_heading h1{font-size:24px;padding:0 0 6px;line-height:1.3}
.stApp:has(.st-key-home_shortcuts) .st-key-workspace_identity{display:none}
.stApp:has(.st-key-home_shortcuts) .st-key-home_recent_heading{margin:0}
.st-key-home_shortcuts{gap:8px;margin-bottom:0}.st-key-home_shortcuts a{background:var(--chess-surface);border:1px solid var(--chess-border);border-radius:9px;padding:10px 16px}
.st-key-home_shortcuts a:hover{background:var(--chess-accent-soft);border-color:var(--chess-accent)}.st-key-home_recent_heading{margin:12px 0 8px}
.stApp input,.stApp textarea,.stApp [data-baseweb="input"],.stApp [data-baseweb="base-input"],.stApp [data-baseweb="select"]>div,.stApp [data-testid="stFileUploaderDropzone"],.stApp [data-testid="stCode"],.stApp pre{background:var(--chess-surface);color:var(--chess-ink);-webkit-text-fill-color:var(--chess-ink)}
.stApp input::placeholder,.stApp textarea::placeholder{color:var(--chess-muted);-webkit-text-fill-color:var(--chess-muted)}.stApp [data-baseweb="select"] svg{color:var(--chess-ink);fill:var(--chess-ink)}
.stApp button{color:var(--chess-ink);background:var(--chess-surface);border-radius:9px;font-weight:550;min-height:40px}
.stApp button[kind="secondary"],.stApp button[kind="tertiary"],.stApp button[kind="pills"]{background:var(--chess-surface);border-color:var(--chess-border)}
.stApp button[kind="secondary"]:hover{background:var(--chess-soft);border-color:var(--chess-accent);color:var(--chess-ink)}
.stApp button[kind^="primary"],.stApp button[kind^="primary"] p{background:var(--chess-accent);color:var(--chess-accent-ink);border-color:var(--chess-accent)}
.stApp button:focus-visible,.stApp input:focus-visible{outline:3px solid var(--chess-accent);outline-offset:3px}
.stApp [role="radio"]{background:var(--chess-surface)!important;color:var(--chess-ink)!important;border-color:var(--chess-border)!important}
.stApp [role="radio"][aria-checked="true"]{background:var(--chess-accent-soft)!important;border-color:var(--chess-accent)!important}.stApp [role="radio"] p{color:var(--chess-ink)!important}
.stApp [data-testid="stBorderWrapper"],.stApp [data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--chess-border);border-radius:14px}
.stApp [data-testid="stExpander"] details,.stApp [data-testid="stForm"]{background:var(--chess-surface);border-color:var(--chess-border);border-radius:12px}
.stApp [data-testid="stExpander"] summary{color:var(--chess-ink);font-size:14px}
.stApp [data-testid="stAlert"]{background:var(--chess-soft);color:var(--chess-ink);border-radius:10px;border:1px solid var(--chess-border);border-left:3px solid var(--chess-accent)}
[data-baseweb="popover"],[data-baseweb="popover"]>div,[data-baseweb="menu"],[role="listbox"],[role="option"],[data-testid="stPopoverBody"],[data-testid="stDialog"] [role="dialog"]{background:var(--chess-surface)!important;color:var(--chess-ink)!important}
[data-testid="stPopoverBody"] p,[data-testid="stPopoverBody"] label,[data-baseweb="popover"] li{color:var(--chess-ink)!important}
.stApp [role="tab"]{color:var(--chess-muted);font-weight:600}.stApp [role="tab"][aria-selected="true"]{color:var(--chess-accent)}
.stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a{border:0;border-radius:9px;background:transparent;color:var(--chess-muted);padding:12px 14px;min-height:46px;transition:background .15s}
.stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover{background:var(--chess-soft);color:var(--chess-ink)}
.stApp [data-testid="stSidebar"] a[aria-current="page"]{background:var(--chess-accent-soft)!important;color:var(--chess-accent)!important;box-shadow:inset 3px 0 var(--chess-accent);font-weight:700}
.st-key-sidebar_navigation{gap:3px;margin-bottom:18px}.stApp [data-testid="stSidebar"] [data-testid="stExpander"] details{background:transparent}.stApp [data-testid="stSidebar"] button{font-size:13px}
.stApp [data-testid="stSidebar"],.st-key-notes_moves,.st-key-panel_moves{scrollbar-width:thin;scrollbar-color:var(--chess-border) transparent}
.st-key-analysis_toolbar{padding:12px;background:var(--chess-surface);border:1px solid var(--chess-border);border-radius:12px;margin:8px 0 16px;gap:10px}.st-key-analysis_toolbar button{min-height:44px}
.st-key-analysis_summary,.st-key-analysis_summary_pending{border-radius:14px!important;background:var(--chess-surface);border-color:var(--chess-border)!important}.st-key-analysis_summary{position:sticky;top:78px}
.st-key-question_launcher{position:fixed;top:7px;right:24px;width:44px!important;z-index:1000000}
.st-key-question_launcher [data-testid="stPopoverButton"]{width:44px;height:44px;border-radius:12px;border:1px solid var(--chess-border);padding:10px;background:var(--chess-surface)}
.st-key-question_launcher [data-testid="stPopoverButton"] p{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.st-key-question_launcher [data-testid="stPopoverButton"]>svg,.st-key-question_launcher [data-testid="stPopoverButton"]>div>[aria-hidden="true"]{display:none}.st-key-question_launcher [data-testid="stPopoverButton"]>div{margin-right:0}
[data-testid="stPopoverBody"]:has([data-testid="stForm"]){min-width:min(340px,calc(100vw - 32px));max-width:420px}
.book-cover{aspect-ratio:.7;max-height:320px;background:#203A2E;border-radius:3px 10px 10px 3px;border-left:10px solid #142A20;padding:22px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between;color:#ECDDBB;box-shadow:3px 6px 14px #0002}
.book-cover strong{font:500 24px/1.3 var(--club-display);overflow-wrap:anywhere}.book-cover span{font:64px/1 serif}.book-cover small{font:11px var(--club-ui);letter-spacing:.16em;color:#ECDDBB!important}
[class*="st-key-book_cover_"] img{max-height:320px;object-fit:contain;object-position:center}.st-key-study_position{position:sticky;top:76px}
.st-key-book_page_reader{background:#FFFEFA;border-radius:10px}.st-key-book_page_reader pre{white-space:pre-wrap;color:#202B26!important;background:#FFFEFA!important}
.book-page{background:var(--chess-surface);color:var(--chess-ink);border:1px solid var(--chess-border);border-left:3px solid var(--chess-gold);border-radius:10px;padding:20px}
.review-row{display:grid;grid-template-columns:32px 1fr 1fr;gap:16px;padding:4px 0}.review-row>span:not(:first-child){text-align:center}.review-symbol{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%}
[class*="st-key-move_quality_"]{padding:3px}[class*="st-key-move_quality_"] button[kind="primary"]{box-shadow:0 0 0 2px var(--chess-surface),0 0 0 4px var(--chess-ink);font-weight:800}
.quality-legend{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.quality-legend li{display:flex;align-items:flex-start;gap:12px}
.quality-key{display:inline-flex;flex:none;align-items:center;justify-content:center;width:34px;height:34px;border-radius:10px;border:1px solid currentColor;font:800 17px/1 var(--club-ui)}.quality-legend p{font-size:13px;line-height:1.5;margin:4px 0 0;color:var(--chess-muted)!important}
[class*="st-key-tactic_card_"]{background:var(--chess-surface);border-radius:14px;border-color:var(--chess-border)!important;padding:18px;transition:border-color .15s}[class*="st-key-tactic_card_"]:hover{border-color:var(--chess-accent)!important}
.st-key-tactic_cards button{min-height:44px;font-weight:650}.st-key-tactic_showcase{border-radius:14px;background:var(--chess-surface);border-color:var(--chess-border)!important;padding:24px;margin-bottom:28px}
.st-key-tactic_cards img{display:block;width:100%;max-width:260px;height:auto;margin:auto;border-radius:8px}
.st-key-notes_moves [data-testid="stHorizontalBlock"],.st-key-panel_moves [data-testid="stHorizontalBlock"]{flex-wrap:nowrap}.st-key-notes_moves [data-testid="stColumn"],.st-key-panel_moves [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
[data-testid="stFileUploaderDropzoneInstructions"]>div>span{font-size:0}[data-testid="stFileUploaderDropzoneInstructions"]>div>span::after{content:'Arraste os arquivos aqui';font-size:14px;color:var(--chess-ink)}
[data-testid="stFileUploaderDropzone"] button{font-size:0}[data-testid="stFileUploaderDropzone"] button::after{content:'Selecionar arquivos';font-size:14px;color:var(--chess-ink)}
[data-testid="stFileUploaderDropzoneInstructions"] small{font-size:0}[data-testid="stFileUploaderDropzoneInstructions"] small::after{content:'Use um dos formatos indicados no campo';font-size:12px;color:var(--chess-muted)}
@media(max-width:700px){.stMainBlockContainer{padding:4.4rem 1.2rem 2rem}.st-key-page_heading{padding:12px 0 18px}.st-key-page_heading h1{font-size:2.15rem}.st-key-question_launcher{right:14px}.quality-legend{grid-template-columns:1fr}.st-key-study_position,.st-key-analysis_summary{position:static}.workspace-wordmark{display:none}}
@media(prefers-reduced-motion:reduce){.stApp button,.stApp a,[class*="st-key-tactic_card_"]{transition:none!important;transform:none!important}}
'''
