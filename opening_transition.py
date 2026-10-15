"""One browser wake-up per opening animation; no polling while thinking."""
import time
import streamlit as st


_TRANSITION = st.components.v2.component(
    'opening_transition', html='<span hidden></span>',
    js='''export default function({data,setTriggerValue}) {
      if (!data.active) return;
      const timer=setTimeout(()=>setTriggerValue('tick',data.revision),data.delay);
      return ()=>clearTimeout(timer);
    }''',
)


def transition(session, on_tick, *, auto_continue=True, key='opening_transition'):
    _TRANSITION(data={
        'active': session['phase'] in ('feedback', 'opponent', 'settling', 'restart')
                  or (auto_continue and session['phase'] == 'line_end'),
        'revision': f"{session['token']}:{session['revision']}",
        'delay': max(30, int((session['next_at'] - time.time()) * 1000) + 20),
    }, key=key, on_tick_change=on_tick, height=0)
