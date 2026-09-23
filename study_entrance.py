"""Abertura cinematográfica local; aceita um filme contínuo em BOBBY_STUDY_VIDEO."""
import base64
import os
from pathlib import Path
import streamlit as st


_VIDEO = st.components.v2.component(
    'bobby_study_video',
    html='''<div class="opening" hidden role="dialog" aria-modal="true" aria-label="Fischer diante de Karpov">
      <video class="scene" muted playsinline preload="auto" aria-label="Fischer e Karpov se preparando para uma partida"></video>
      <span class="scene-caption">Fischer × Karpov · cena imaginada</span>
      <button type="button">Pular abertura</button></div>''',
    css='''
    .opening {position:fixed;inset:0;z-index:2000000;display:grid;place-items:center;background:#030506}
    .opening[hidden] {display:none}
    video {width:100%;height:100%;max-height:100vh;object-fit:contain}
    .scene-caption {position:absolute;left:24px;bottom:30px;color:#d0c8bb;font:13px/1.5 sans-serif;letter-spacing:.06em}
    button {position:absolute;right:24px;bottom:24px;padding:12px 20px;border:1px solid #a9b3c4;
      border-radius:12px;background:#202936;color:#f3f4f6;cursor:pointer}
    @media(max-width:560px){.scene-caption{left:16px;bottom:86px}button{right:16px;bottom:20px}}
    ''',
    js='''
    export default function({data,parentElement,setTriggerValue}) {
      const overlay=parentElement.querySelector('.opening'),video=parentElement.querySelector('video');
      const previous=parentElement._entrance;
      if(previous){if(!data.enabled)previous.close();return;}
      // A visita pertence ao documento do navegador, não à aba interna nem ao rerun.
      let closed=false,watchdog;
      const previousFocus=document.activeElement;
      function keyboard(event){if(event.key==='Escape'){event.preventDefault();close();}}
      function close(){
        if(closed)return;closed=true;video.pause();overlay.hidden=true;
        clearTimeout(watchdog);document.removeEventListener('keydown',keyboard);
        window.__chessIntroActive=false;
        if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true});
        window.__chessIntroSeen=true;setTriggerValue('finished',true);
      }
      parentElement._entrance={close};
      parentElement.querySelector('button').onclick=close;
      video.onended=video.onerror=close;
      if(!data.enabled || window.__chessIntroSeen || window.matchMedia('(prefers-reduced-motion: reduce)').matches){close();return;}
      window.__chessIntroSeen=true;window.__chessIntroActive=true;
      overlay.hidden=false;video.src=data.source;video.poster=data.poster || '';video.muted=true;
      document.addEventListener('keydown',keyboard);
      parentElement.querySelector('button').focus({preventScroll:true});
      watchdog=setTimeout(close,20000);
      video.play().catch(close);
    }
    ''',
)


@st.cache_data(max_entries=3, show_spinner=False)
def asset_source(path, modified):
    source = Path(path)
    mime = {'.webm': 'video/webm', '.mp4': 'video/mp4', '.png': 'image/png', '.jpg': 'image/jpeg'}[source.suffix.lower()]
    return f'data:{mime};base64,' + base64.b64encode(source.read_bytes()).decode()


def study_entrance(enabled, on_finished):
    root = Path(__file__).parent / 'assets'
    configured = os.environ.get('BOBBY_STUDY_VIDEO')
    source = Path(configured) if configured else root / 'fischer-karpov-opening.mp4'
    if not source.is_file() or source.suffix.lower() not in {'.mp4', '.webm'}:
        source = root / 'fischer-karpov-opening.mp4'
    poster = root / 'fischer-karpov-scene.png'
    _VIDEO(data={'enabled': enabled,
                 'poster': asset_source(str(poster), poster.stat().st_mtime_ns) if enabled and not configured else '',
                 'source': asset_source(str(source), source.stat().st_mtime_ns) if enabled else ''},
           on_finished_change=on_finished, key='study_entrance', height=0)
