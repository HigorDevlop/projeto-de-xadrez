"""Accessible piece palette using the same SVG pieces as the board."""
import streamlit as st
from interactive_board import piece_images
from study_workspace import PIECES


_PALETTE = st.components.v2.component(
    'analysis_position_palette',
    html='<div class="edit-palette"><div class="tools"></div><div class="piece-rows"></div><p class="selection" aria-live="polite"></p></div>',
    css='''
    .edit-palette{font:14px/1.4 "Segoe UI",sans-serif;color:#f2f2f2}
    .tools{display:flex;gap:8px;margin-bottom:20px}
    button{font:inherit;cursor:var(--club-cursor-link,pointer);border:1px solid #414141;border-radius:11px;color:inherit;
      background:linear-gradient(150deg,#303030,#232323);box-shadow:inset 0 1px 0 #ffffff0b;transition:border-color .12s,background .12s}
    .tools button{display:flex;align-items:center;gap:8px;padding:10px 14px;font-size:13px}
    .tools svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
    .piece-row{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:8px 0 18px}
    .piece-label{font-size:11px;color:#a8a8a8;letter-spacing:.07em;text-transform:uppercase}
    .piece-row button{aspect-ratio:1;min-width:0;max-height:62px;padding:7px;background:linear-gradient(145deg,#b2b3ac,#92958c);border-color:#b9bab333}
    .piece-row button svg{display:block;width:100%;height:100%;pointer-events:none}
    button:hover{border-color:#868686}
    button[aria-pressed=true]{border-color:#ff9b3c;background:#3a291d;box-shadow:0 0 0 2px #ff800033,inset 0 1px 0 #ffffff0b}
    .piece-row button[aria-pressed=true]{background:linear-gradient(145deg,#d6c2a3,#ae946c);border-color:#ff9b3c}
    button:focus-visible{outline:3px solid #ff9b3c;outline-offset:3px}
    .selection{font-size:12px;color:#bcbcbc;margin:0;min-height:18px}
    @media(max-width:420px){.piece-row{gap:5px}.tools button{padding:9px 11px}.piece-row button{padding:5px}}
    @media(prefers-reduced-motion:reduce){button{transition:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}){
      const root=parentElement.querySelector('.edit-palette');
      const tools=root.querySelector('.tools'), rows=root.querySelector('.piece-rows');
      tools.replaceChildren();rows.replaceChildren();
      const select=value=>{
        for(const b of root.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.tool===value));
        root.querySelector('.selection').textContent=data.labels[value];
        setTriggerValue('tool',value);
      };
      const button=(tool,label,svg)=>{
        const b=document.createElement('button');b.type='button';b.dataset.tool=tool;
        b.setAttribute('aria-label',label);b.title=label;b.setAttribute('aria-pressed',String(tool===data.selected));
        b.innerHTML=svg;b.onclick=()=>select(tool);return b;
      };
      for(const [tool,label,path] of [
        ['move','Mover peças','<path d="M12 3v18M3 12h18M8 7l4-4 4 4M8 17l4 4 4-4M7 8l-4 4 4 4M17 8l4 4-4 4"/>'],
        ['erase','Apagar peça','<path d="m4 14 9-10a2 2 0 0 1 3 0l5 5a2 2 0 0 1 0 3l-8 8H8l-4-4a2 2 0 0 1 0-2ZM10 8l8 8M13 20h9"/>']]){
        const b=button(tool,label,'<svg viewBox="0 0 24 24" aria-hidden="true">'+path+'</svg>');
        b.append(document.createTextNode(label));tools.append(b);
      }
      for(const [title,symbols] of [['Peças brancas','KQRBNP'],['Peças pretas','kqrbnp']]){
        const label=document.createElement('div');label.className='piece-label';label.textContent=title;rows.append(label);
        const row=document.createElement('div');row.className='piece-row';row.setAttribute('role','group');row.setAttribute('aria-label',title);
        for(const symbol of symbols)row.append(button(symbol,data.labels[symbol],data.pieces[symbol]));
        rows.append(row);
      }
      root.querySelector('.selection').textContent=data.labels[data.selected];
    }''',
)


def selected():
    value = st.session_state.analysis_palette.tool
    if value in PIECES:
        st.session_state.analysis_edit_tool = value


def render():
    _PALETTE(data={'selected': st.session_state.analysis_edit_tool, 'pieces': piece_images(), 'labels': PIECES},
             key='analysis_palette', on_tool_change=selected)
