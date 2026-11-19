"""Offline noir Zombies-inspired backdrop, scoped to the tactics workspace."""
import base64
from pathlib import Path
import streamlit as st


@st.cache_data(show_spinner=False)
def frame_art():
    path=Path(__file__).resolve().parent/'assets/tactics-zombies-district.png'
    return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode('ascii')


def style_frame():
    st.html('''<style>
    [data-testid="stAppViewContainer"]:has(.st-key-tactics_workbench){
      background-color:#070c0e!important;
      background-image:linear-gradient(90deg,#03070980,#06101445 50%,#03070985),url("'''+frame_art()+'''")!important;
      background-size:cover!important;background-position:center!important;
      background-attachment:fixed!important;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-tactics_workbench) [data-testid="stMain"]{
      background:transparent!important;
    }
    .st-key-tactics_workbench{padding:22px!important;border-radius:22px;
      background:linear-gradient(135deg,#071014b8,#050909a8)!important;
      border:1px solid #9f845638;box-shadow:0 24px 80px #0007;}
    .st-key-tactics_coach{background:linear-gradient(145deg,#162625ed,#0b1719ed)!important;
      border-color:#83988a55!important;box-shadow:inset 0 1px #e0c18a22,0 16px 40px #0009!important;}
    .st-key-tactics_board_panel{
      padding:24px 30px 30px!important;border:1px solid #927449!important;
      border-radius:18px!important;background-color:#060b0d!important;
      background-image:linear-gradient(180deg,#02060720,#02040555),url("'''+frame_art()+'''")!important;
      background-size:100% 100%!important;background-position:center!important;
      box-shadow:inset 0 0 0 3px #0a0e0dbb,inset 0 0 36px #0008,0 18px 50px #0008!important;
    }
    .zombies-board-plaque{display:flex;justify-content:space-between;gap:12px;align-items:center;
      border-bottom:1px solid #b49a5f44;padding:0 0 12px;margin:0 0 4px;
      font:600 9px/1.4 system-ui;letter-spacing:2px;color:#dbc79e;text-shadow:0 2px 5px #000;
    }.zombies-board-plaque span+span{color:#7fbdc3;font-size:8px;letter-spacing:1px}
    @media(max-width:700px){.st-key-tactics_workbench{padding:10px!important}.st-key-tactics_board_panel{padding:14px 12px 18px!important}.zombies-board-plaque{letter-spacing:1px;font-size:8px}}
    </style>''')


def plaque():
    st.html('<div class="zombies-board-plaque"><span>SHADOWS OF EVIL</span><span>INSPIRAÇÃO · ZOMBIES</span></div>')
