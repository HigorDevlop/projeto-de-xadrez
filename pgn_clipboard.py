"""Copy the complete PGN locally, with an accessible selection fallback."""
import streamlit as st


_COPY = st.components.v2.component(
    'chess_pgn_clipboard',
    html='''<button type="button">Copiar PGN</button>
    <textarea readonly aria-label="PGN completo" spellcheck="false"></textarea>
    <p role="status" aria-live="polite"></p>''',
    css='''
    textarea {display:block;width:100%;height:260px;box-sizing:border-box;margin-top:12px;
      padding:16px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);font:14px/1.6 monospace}
    button {background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:12px;padding:10px 20px;cursor:var(--club-cursor-link,pointer)}
    p {color:var(--ink);font:14px sans-serif}
    ''',
    js='''
    export default function({data,parentElement}) {
      const field=parentElement.querySelector('textarea'), button=parentElement.querySelector('button');
      (parentElement.host ?? parentElement).style.setProperty('--surface',data.dark?'#121212':'#FFFEFA');
      (parentElement.host ?? parentElement).style.setProperty('--ink',data.dark?'#f5f5f5':'#202B26');
      (parentElement.host ?? parentElement).style.setProperty('--border',data.dark?'#2b2b2b':'#D9DED5');
      field.value=data.pgn;
      button.onclick=async()=>{
        const status=parentElement.querySelector('p');
        try {await navigator.clipboard.writeText(field.value);status.textContent='PGN copiado!';}
        catch {field.focus();field.select();status.textContent='Selecione o texto e pressione Ctrl+C para copiar o PGN.';}
      };
    }
    ''',
)


def pgn_clipboard(pgn, *, key, dark=False):
    return _COPY(data={'pgn': pgn, 'dark': dark}, key=key)
