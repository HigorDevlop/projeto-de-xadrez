"""Offline timed training, independent of the per-puzzle resolution clock."""
from time import perf_counter
import streamlit as st


def remaining(state, now=None):
    deadline=state.get('tactic_deadline')
    if deadline is None:return None
    return max(0,deadline-(perf_counter() if now is None else now))


def expired(state):
    seconds=remaining(state)
    return seconds is not None and seconds<=0


CLOCK=st.components.v2.component('tactics_session_clock',
    html='<div class="session-clock"><span>TEMPO DO TREINO</span><strong aria-live="off"></strong><div><i></i></div></div>',
    css='''.session-clock{font:11px system-ui;color:#b8aa8b;letter-spacing:1px;display:flex;align-items:center;gap:16px;padding:12px 16px;border:1px solid #65583c;border-radius:13px;background:linear-gradient(120deg,#28291e,#131913)}.session-clock strong{color:#efdbb2;font:600 24px system-ui;font-variant-numeric:tabular-nums}.session-clock>div{flex:1;height:4px;background:#ffffff12;border-radius:4px;overflow:hidden}.session-clock i{display:block;height:100%;background:#d4b073;transition:width .2s}.session-clock.ending strong{color:#edaa8a}''',
    js='''export default function({data,parentElement,setTriggerValue}){
      const end=performance.now()+data.remaining*1000;let sent=false;
      function paint(){const left=Math.max(0,Math.ceil((end-performance.now())/1000));parentElement.querySelector('strong').textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0');parentElement.querySelector('i').style.width=(100*left/data.duration)+'%';parentElement.querySelector('.session-clock').classList.toggle('ending',left<=10);if(!left&&!sent){sent=true;setTriggerValue('finish',data.session);}}
      paint();const timer=setInterval(paint,200);return()=>clearInterval(timer);
    }''')


def render_clock(state):
    def finish():
        if expired(state):st.rerun('tactics_workspace')
    CLOCK(data=dict(remaining=remaining(state),duration=state.get('tactic_duration_seconds',180),session=state.tactic_session_id),
          key='tactics_session_clock',on_finish_change=finish)
