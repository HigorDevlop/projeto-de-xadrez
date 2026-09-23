"""Paleta compartilhada e uma entrada curta, sem depender de serviços externos."""

import streamlit as st


def apply_theme(dark):
    ink, muted, background, surface, border = (
        ('#f3f4f6', '#c4cbd6', '#090d12', '#171e28', '#414c5b') if dark else
        ('#202530', '#505968', '#f5f0e6', '#fffaf0', '#b5a991'))
    st.html(f'''<style>
    :root {{color-scheme:{'dark' if dark else 'light'};--chess-ink:{ink};--chess-muted:{muted};
      --chess-bg:{background};--chess-surface:{surface};--chess-border:{border}}} 
    .stApp {{color:{ink};background-color:{background}}}
    [data-testid="stHeader"], [data-testid="stSidebar"] {{background:{background};color:{ink}}}
    .stMainBlockContainer {{padding-top:4.5rem;padding-bottom:2rem}}
    .book-cover {{aspect-ratio:.7;max-height:320px;background:linear-gradient(120deg,#244039,#10211f);
      border-radius:4px 12px 12px 4px;border-left:12px solid #101c18;padding:22px;box-sizing:border-box;
      display:flex;flex-direction:column;justify-content:space-between;color:#e8d6ae;box-shadow:4px 8px 16px #0003}}
    .book-cover strong {{font:600 24px/1.3 Georgia,serif;overflow-wrap:anywhere}}
    .book-cover span {{font:64px/1 serif}}
    .book-cover small {{font:11px sans-serif;letter-spacing:.2em;color:#e8d6ae!important}}
    [class*="st-key-book_cover_"] img {{max-height:320px;object-fit:contain;object-position:center}}
    .st-key-study_position {{position:sticky;top:76px}}
    .st-key-book_page_reader {{background:#f4efe4}}
    .st-key-book_page_reader pre {{white-space:pre-wrap;color:#202530!important;background:#f4efe4!important}}
    @media(max-width:700px) {{.st-key-study_position{{position:static}}}}
    .st-key-question_launcher {{position:fixed;top:10px;right:24px;width:48px!important;z-index:1000000}}
    .st-key-question_launcher [data-testid="stPopoverButton"] {{width:48px;height:44px;border-radius:50%;
      border:1px solid {border};box-shadow:0 4px 16px #0002;padding:10px}}
    .st-key-question_launcher [data-testid="stPopoverButton"] p {{position:absolute;width:1px;height:1px;
      overflow:hidden;clip-path:inset(50%);white-space:nowrap}}
    .st-key-question_launcher [data-testid="stPopoverButton"]>svg {{display:none}}
    .st-key-question_launcher [data-testid="stPopoverButton"]>div>[aria-hidden="true"] {{display:none}}
    .st-key-question_launcher [data-testid="stPopoverButton"]>div {{margin-right:0}}
    [data-testid="stPopoverBody"]:has([data-testid="stForm"]) {{min-width:min(340px,calc(100vw - 32px));max-width:420px}}
    @media(max-width:600px) {{.st-key-question_launcher {{right:16px}}}}
    .stAppDeployButton, [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], #MainMenu {{display:none}}
    .stApp h1,.stApp h2,.stApp h3,.stApp p,.stApp label,.stApp summary,.stApp small,
    .stApp [data-testid="stMetricValue"],.stApp [data-testid="stIconMaterial"] {{color:{ink}}}
    .stApp [data-testid="stCaptionContainer"] p {{color:{muted}}}
    .stApp input,.stApp textarea,.stApp [data-baseweb="input"],.stApp [data-baseweb="base-input"],
    .stApp [data-baseweb="select"]>div,.stApp [data-testid="stFileUploaderDropzone"],
    .stApp [data-testid="stCode"],.stApp pre {{background:{surface};color:{ink};-webkit-text-fill-color:{ink}}}
    .stApp input::placeholder,.stApp textarea::placeholder {{color:{muted};-webkit-text-fill-color:{muted}}}
    .stApp button {{color:{ink};background:{surface};border-radius:12px}}
    .stApp [data-testid="stSidebar"] a {{color:{ink};border-radius:12px}}
    .stApp button[kind="secondary"],.stApp button[kind="tertiary"],.stApp button[kind="pills"] {{background:{surface};border-color:{border}}}
    .stApp button[kind^="primary"],.stApp button[kind^="primary"] p {{background:#6840b8;color:#fff}}
    .stApp [role="radio"] {{background:{surface}!important;color:{ink}!important;border-color:{border}!important}}
    .stApp [role="radio"][aria-checked="true"] {{background:{'#49356a' if dark else '#e6dcfa'}!important}}
    .stApp [role="radio"] p {{color:{ink}!important}}
    .stApp [data-baseweb="select"] svg {{color:{ink};fill:{ink}}}
    .stApp [data-baseweb="select"]>div>div {{background:{surface};color:{ink}}}
    .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] * {{color:{muted}!important;opacity:1}}
    .stApp [data-testid="stBorderWrapper"],.stApp [data-testid="stVerticalBlockBorderWrapper"] {{border-color:{border}}}
    .stApp [data-testid="stExpander"] details,.stApp [data-testid="stForm"],.stApp [data-testid="stAlert"] {{background:{surface};color:{ink};border-color:{border}}}
    [data-baseweb="popover"], [data-baseweb="popover"]>div, [data-baseweb="menu"], [role="listbox"], [role="option"],
    [data-testid="stPopoverBody"], [data-testid="stDialog"] [role="dialog"] {{background:{surface}!important;color:{ink}!important}}
    [data-testid="stPopoverBody"] p,[data-testid="stPopoverBody"] label,[data-baseweb="popover"] li {{color:{ink}!important}}
    .stApp [role="tab"] {{color:{ink}}}
    .stApp [role="tab"][aria-selected="true"] {{color:{'#c4b5fd' if dark else '#6238a8'}}}
    .stApp a {{color:{'#c4b5fd' if dark else '#6238a8'}}}
    .stApp [data-testid="stSidebar"] button,.stApp [data-testid="stSidebar"] a {{padding:.65rem .9rem;transition:background .15s}}
    .stApp [data-testid="stSidebar"] [data-testid="stPageLink"] a {{background:{surface};
      border:1px solid {border};border-radius:16px;min-height:48px;box-shadow:0 3px 10px #00000009;
      transition:transform .15s,border-color .15s,box-shadow .15s}}
    .stApp [data-testid="stSidebar"] a:hover {{background:{surface};border-color:#629269;
      transform:translateX(3px);box-shadow:0 4px 14px #00000018}}
    .stApp [data-testid="stSidebar"] a[aria-current="page"] {{border-left:4px solid #629269}}
    .stApp [data-testid="stSidebar"] [data-testid="stExpander"] details {{border-radius:16px}}
    .st-key-switch_user {{position:sticky;top:0;z-index:5;background:{background};padding-bottom:.6rem}}
    .book-page {{background:{surface};color:{ink};border:1px solid {border};border-left:4px solid #b69055;border-radius:12px;padding:16px}}
    .review-row {{display:grid;grid-template-columns:32px 1fr 1fr;gap:16px;padding:4px 0}}
    .review-row>span:not(:first-child) {{text-align:center}}
    .review-symbol {{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%}}
    [class*="st-key-tactic_card_"] {{background:linear-gradient(145deg,{surface}, {background});
      border-radius:22px;border-color:{border}!important;padding:16px;box-shadow:0 8px 24px #0000000b;
      transition:transform .18s,box-shadow .18s}}
    [class*="st-key-tactic_card_"]:hover {{transform:translateY(-3px);box-shadow:0 12px 28px #00000020}}
    .st-key-tactic_cards button {{min-height:48px;border:1px solid #629269!important;font-weight:600}}
    .st-key-tactic_showcase {{border-radius:24px;background:{surface};border-color:{border}!important;
      box-shadow:0 16px 44px #00000015;padding:20px;margin-bottom:24px}}
    @media(prefers-reduced-motion:reduce) {{[class*="st-key-tactic_card_"],.stApp [data-testid="stSidebar"] a {{transition:none!important;transform:none!important}}}}
    .st-key-tactic_cards img {{display:block;width:100%;max-width:280px;height:auto;margin:auto;border-radius:12px}}
    .st-key-notes_moves [data-testid="stHorizontalBlock"], .st-key-panel_moves [data-testid="stHorizontalBlock"] {{flex-wrap:nowrap}}
    .st-key-notes_moves [data-testid="stColumn"], .st-key-panel_moves [data-testid="stColumn"] {{min-width:0!important;flex:1 1 0!important}}
    /* Translate the native upload affordance; the input remains keyboard accessible. */
    [data-testid="stFileUploaderDropzoneInstructions"]>div>span {{font-size:0}}
    [data-testid="stFileUploaderDropzoneInstructions"]>div>span::after {{content:'Arraste os arquivos aqui';font-size:14px;color:{ink}}}
    [data-testid="stFileUploaderDropzone"] button {{font-size:0}}
    [data-testid="stFileUploaderDropzone"] button::after {{content:'Selecionar arquivos';font-size:14px;color:{ink}}}
    [data-testid="stFileUploaderDropzoneInstructions"] small {{font-size:0}}
    [data-testid="stFileUploaderDropzoneInstructions"] small::after {{content:'Use um dos formatos indicados no campo';font-size:12px;color:{muted}}}
    </style>''')
