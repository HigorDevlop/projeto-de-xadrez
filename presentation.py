"""Identidade editorial e estilos comuns às páginas do Acervo."""
from html import escape
import streamlit as st
from chess_review import CATEGORIES
from quality_icons import icon_html
from design_tokens import palette
from cursor_theme import CURSOR_STYLE


def classification_legend():
    with st.expander(f'Legenda dos {len(CATEGORIES)} tipos de lance'):
        entries = ''.join(f'<li><span class="quality-key" style="background:{c.color};color:{c.ink}" aria-hidden="true">{icon_html(c)}</span><div><strong>{escape(c.label)}</strong><p>{escape(c.description)}</p></div></li>' for c in CATEGORIES.values())
        st.html(f'<ul class="quality-legend" aria-label="{len(CATEGORIES)} classificações de lances">{entries}</ul>')


def brand():
    from pathlib import Path
    from base64 import b64encode
    logo = b64encode((Path(__file__).parent / 'assets/coach-chess.svg').read_bytes()).decode()
    st.html('<div class="club-brand"><img class="club-emblem" alt="Coach Chess" src="data:image/svg+xml;base64,'+logo+'"/><div><strong>Coach Chess</strong><small>ESTUDO DE XADREZ</small></div></div>')


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
    dark = True
    p = palette(dark)
    variables = ';'.join(f'--chess-{key.replace("_", "-")}:{value}' for key,value in p.items())
    move_colors = ''.join(f'[class*="st-key-move_quality_{key}_"] button{{background:{c.color}!important;color:{c.ink}!important;border:2px solid {c.ink}!important;min-height:44px}}[class*="st-key-move_quality_{key}_"] button *{{color:{c.ink}!important;background:transparent!important}}' for key,c in CATEGORIES.items())
    from futurist_theme import CSS as FUTURIST_CSS
    st.html('<style>:root{color-scheme:'+('dark' if dark else 'light')+';'+variables+'}'+STYLE+SURFACE_STYLE+move_colors+CURSOR_STYLE+FUTURIST_CSS+'</style>')


STYLE = '''
:root{--club-ui:'Segoe UI',system-ui,-apple-system,sans-serif;--club-display:'Segoe UI',system-ui,-apple-system,sans-serif}
.stApp{color:var(--chess-ink);background:var(--chess-background);font-family:var(--club-ui)}
.stMainBlockContainer{max-width:1600px;padding:4.8rem 4.6rem 4rem}
[data-testid="stHeader"]{background:var(--chess-background);border-bottom:1px solid var(--chess-border);height:58px}
[data-testid="stSidebar"]{background:var(--chess-surface);color:var(--chess-ink);border-right:1px solid var(--chess-border)}
[data-testid="stSidebarContent"]{padding-top:1.3rem}.club-brand .club-emblem{background:#000;color:#fff;padding:0;object-fit:contain}.stApp [data-testid="stExpander"] details,.stApp [data-testid="stForm"],.stApp [data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(145deg,#1b1b1b,#121212);border:1px solid #2b2b2b}
.stApp h1,.stApp h2,.stApp h3{color:var(--chess-ink);font-family:var(--club-display);letter-spacing:-.035em;font-weight:500;line-height:1.2}
.stApp h1{font-size:clamp(2rem,3.2vw,3.25rem)}.stApp h2{font-size:1.8rem}.stApp h3{font-size:1.4rem}
.stApp p,.stApp label,.stApp summary,.stApp small,.stApp button,.stApp [data-testid="stMetricValue"]{color:var(--chess-ink);font-family:var(--club-ui)}
.stApp p{line-height:1.65}.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] *{color:var(--chess-muted)!important;opacity:1}
.stApp [data-testid="stIconMaterial"]{color:inherit}.stApp a{color:var(--chess-accent);text-underline-offset:4px}
.stAppDeployButton,[data-testid="stAppDeployButton"],[data-testid="stMainMenu"],#MainMenu{display:none}
.club-brand{display:flex;gap:12px;align-items:center;margin:2px 0 28px}.club-emblem{display:grid;place-items:center;width:44px;height:48px;background:var(--chess-accent-soft);color:var(--chess-accent);border-radius:10px;font:36px/1 Georgia,serif}
.club-brand strong{display:block;font:650 24px/1.1 var(--club-display);letter-spacing:-.04em;color:var(--chess-ink)}
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

.stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a{position:relative;border:1px solid #ffffff0c;border-radius:12px;background:linear-gradient(135deg,#262721,#191c18);box-shadow:inset 0 1px #ffffff09,0 3px 7px #0004;padding:11px 14px;min-height:43px;color:#c9cbbf;transition:transform .18s,box-shadow .18s,border-color .18s,background .18s}
.stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover{transform:translateX(3px) translateY(-1px);border-color:#c4ab6866;background:linear-gradient(135deg,#34372b,#23281e);box-shadow:inset 0 1px #ffffff13,0 6px 13px #0006;color:#f1e3c4}
.stApp [data-testid="stSidebar"] a[aria-current="page"]{border-color:#b69e6355!important;box-shadow:inset 3px 0 #d5b777,inset 0 1px #ffffff09,0 4px 12px #0004;background:linear-gradient(135deg,#423b29,#282b20)!important;color:#f0d6a5!important}
.st-key-sidebar_tactics button{justify-content:flex-start;text-align:left;min-height:43px;border-radius:12px;background:linear-gradient(135deg,#262721,#191c18);color:#c9cbbf;padding:11px 14px}.st-key-sidebar_tactics button:hover{transform:translateX(3px) translateY(-1px)}.st-key-sidebar_navigation{gap:7px;padding-right:4px}.stApp [data-testid="stSidebar"] button,.stApp [data-testid="stSidebar"] summary{box-shadow:inset 0 1px #ffffff0a,0 4px 9px #0004;transition:transform .18s,box-shadow .18s,border-color .18s}.stApp [data-testid="stSidebar"] button:hover,.stApp [data-testid="stSidebar"] summary:hover{transform:translateY(-2px);border-color:#b8a66a66;box-shadow:inset 0 1px #ffffff16,0 7px 14px #0005}
.st-key-sidebar_tactics button{justify-content:flex-start!important;text-align:left!important}.st-key-sidebar_tactics button>div{display:flex;justify-content:flex-start!important;width:100%;gap:8px}.st-key-sidebar_tactics button [data-testid="stMarkdownContainer"]{text-align:left!important}
.stApp [data-testid="stSidebar"] [class*="st-key-sidebar_nav_"][class*="_active"] a,.stApp [data-testid="stSidebar"] .st-key-sidebar_tactics button[kind="primary"]{position:relative;overflow:hidden;border:1px solid #d3b57588!important;background:linear-gradient(125deg,#4a412c,#292e21)!important;color:#f3dba7!important;box-shadow:inset 3px 0 #dfbf7c,inset 0 1px #ffffff12,0 4px 14px #b3984b18!important;animation:sidebar-selected-glow 1.5s ease-in-out 2}
.stApp [data-testid="stSidebar"] .st-key-sidebar_tactics button[kind="primary"] p{color:#f3dba7!important;background:transparent!important}
.stApp [data-testid="stSidebar"] [class*="st-key-sidebar_nav_"][class*="_active"] a:after,.stApp [data-testid="stSidebar"] .st-key-sidebar_tactics button[kind="primary"]:after{content:'';position:absolute;inset:0;pointer-events:none;background:linear-gradient(110deg,transparent 20%,#efd49b20 50%,transparent 80%);transform:translateX(-120%);animation:sidebar-selected-shine .75s ease-out}
@keyframes sidebar-selected-glow{0%,100%{filter:brightness(1)}50%{filter:brightness(1.2)}}@keyframes sidebar-selected-shine{to{transform:translateX(120%)}}
@media(prefers-reduced-motion:reduce){.stApp [data-testid="stSidebar"] [class*="st-key-sidebar_nav_"][class*="_active"] a,.stApp [data-testid="stSidebar"] .st-key-sidebar_tactics button[kind="primary"],.stApp [data-testid="stSidebar"] [class*="st-key-sidebar_nav_"][class*="_active"] a:after,.stApp [data-testid="stSidebar"] .st-key-sidebar_tactics button[kind="primary"]:after{animation:none!important}}
.st-key-session_settings{background:linear-gradient(140deg,#292b23,#191d17);border-radius:13px;box-shadow:inset 0 1px #ffffff09,0 5px 15px #0003;padding:14px}
@media(prefers-reduced-motion:reduce){.stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a,.stApp [data-testid="stSidebar"] button,.stApp [data-testid="stSidebar"] summary{transition:none}.stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover,.stApp [data-testid="stSidebar"] button:hover,.stApp [data-testid="stSidebar"] summary:hover{transform:none}}
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


# A shared surface treatment: only panels and controls, never board squares or text nodes.
SURFACE_STYLE = r'''
:root {
  --club-panel: linear-gradient(150deg, #242424 0%, #1c1c1c 45%, #181818 100%);
  --club-relief: inset 0 1px 0 #ffffff0d, inset 0 -1px 0 #00000040,
                 0 3px 8px #00000040, 0 12px 24px #0000001f;
}
.stApp.stApp {background:#0a0a0a!important}
/* Keep the sidebar canvas separate from its raised account and settings panels. */
.stApp.stApp [data-testid="stSidebar"] {background:#121212}
.stApp.stApp :is(
  [data-testid="stVerticalBlockBorderWrapper"],
  [data-testid="stForm"], [data-testid="stExpander"] details,
  [data-testid="stMetric"], [data-testid="stChatMessage"],
  .st-key-sidebar_account_card, .st-key-analysis_source,
  .st-key-analysis_toolbar, .st-key-centered_board,
  .st-key-analysis_summary, .st-key-analysis_summary_pending,
  .st-key-study_library, .st-key-study_reading_panel, .st-key-study_position,
  .st-key-routine_editor, .st-key-tactic_showcase,
  [class*="st-key-book_cover_"], [class*="st-key-tactic_card_"],
  .reference-rank, .reference-profile-card, .quality-accuracy,
  .prep-profile, .prep-empty, .book-page
) {
  background:var(--club-panel)!important;
  box-shadow:var(--club-relief)!important;
  border-color:#383838!important;
}
.stApp.stApp [data-testid="stMetric"] {
  border:1px solid #383838;border-radius:14px;padding:16px;
}
/* Colored banners retain their meaning while receiving the same edge lighting. */
.stApp.stApp :is(.reference-banner, .prep-plan, .prep-live-cover, [data-testid="stAlert"]) {
  box-shadow:var(--club-relief);
}
.stApp.stApp :is([data-baseweb="input"], [data-baseweb="select"]>div,
  [data-baseweb="textarea"], [data-testid="stFileUploaderDropzone"], [data-testid="stCode"]) {
  background:#1c1c1c!important;
  border-color:#3b3b3b!important;
  box-shadow:inset 0 1px 3px #00000050, 0 1px 0 #ffffff09;
}
.stApp.stApp :is(input, textarea, [data-baseweb="base-input"]) {background:transparent}
.stApp.stApp button[kind="secondary"] {
  background:linear-gradient(160deg,#292929,#1c1c1c);
  box-shadow:inset 0 1px 0 #ffffff0c,0 2px 4px #00000030;
}
.stApp.stApp button[kind="secondary"]:hover {border-color:var(--chess-accent);background:#2c2c2c}
/* Analysis places the board first, with controls and reports underneath. */
.stApp:has(.st-key-analysis_board_focus) .stMainBlockContainer {padding-top:4.2rem}
.st-key-analysis_board_focus {max-width:1000px;margin:0 auto;gap:4px}
.st-key-analysis_board_focus h3 {font-size:22px;padding:0 0 4px}
.stApp:has(.st-key-analysis_board_focus) .st-key-analysis_toolbar {max-width:1000px;margin:8px auto 12px}
.stApp:has(.st-key-analysis_board_focus) .st-key-analysis_summary {position:static;max-width:1000px;margin:auto;padding:20px}
.stApp.stApp .st-key-analysis_editor_controls {max-width:1000px;margin:12px auto 20px;padding:24px!important;background:var(--club-panel)!important;box-shadow:var(--club-relief);border:1px solid #383838!important;border-radius:18px!important;box-sizing:border-box}
.st-key-analysis_editor_controls h3{font-size:23px!important;letter-spacing:-.04em;padding:0;margin:0}
.st-key-analysis_editor_controls hr{margin:4px 0;border-color:#ffffff0c}
.st-key-analysis_editor_settings{padding:16px 18px;background:#ffffff03;border:1px solid #ffffff09;border-radius:14px}
.st-key-analysis_editor_settings [data-testid="stCheckbox"] p{font-size:13px}
.st-key-analysis_editor_actions{gap:12px}
.st-key-analysis_secondary,.st-key-analysis_legend{max-width:1000px;width:100%;margin:0 auto;box-sizing:border-box}
@media(max-width:700px){.stApp.stApp .st-key-analysis_editor_controls{padding:16px!important}.st-key-analysis_editor_settings{padding:14px}}
@media(max-width:700px){.stApp:has(.st-key-analysis_board_focus) .stMainBlockContainer{padding:4rem .8rem 2rem}}
/* Keep actual book pages paper-colored and legible. */
.stApp.stApp .st-key-book_page_reader {background:#fffefa!important}
'''
