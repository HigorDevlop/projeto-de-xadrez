"""Inline Streamlit v2 board; python-chess is the authority on legal moves."""
import chess
import chess.svg
import streamlit as st

_BOARD = st.components.v2.component(
    "acervo_interactive_board",
    html='<div class="board" aria-label="Tabuleiro interativo"></div><div class="promotion"></div>',
    css="""
    .board {display:grid;grid-template-columns:repeat(8,1fr);width:100%;max-width:560px;
      aspect-ratio:1; border:4px solid #383a39;border-radius:5px;overflow:hidden;box-sizing:border-box}
    .square {position:relative; padding:0;border:0;border-radius:0;aspect-ratio:1;
      min-width:0;cursor:pointer;touch-action:none;user-select:none}
    .light {background:#e5ded0}.dark {background:#69746b}
    .square svg {width:88%;height:88%;pointer-events:none;vertical-align:middle}
    .square.last {box-shadow:inset 0 0 0 4px #cba960}
    .square.brilliant:before {content:'';position:absolute;inset:3%;border-radius:50%;pointer-events:none;
      background:radial-gradient(circle,#38bdf844 10%,#009dff99 50%,transparent 72%);
      box-shadow:0 0 20px 8px #009dff;animation:brilliant-aura 900ms ease-in-out 3}
    @keyframes brilliant-aura {0%,100% {opacity:.25;transform:scale(.7)} 50% {opacity:1;transform:scale(1.1)}}
    @media (prefers-reduced-motion:reduce) {.square.brilliant:before {animation:none;opacity:.5}}
    .square.selected {box-shadow:inset 0 0 0 4px #8b5cf6}
    .square:focus-visible {outline:4px solid #8b5cf6;outline-offset:-4px;z-index:2}
    .square.target:after {content:'';position:absolute;inset:38%;border-radius:50%;background:#17132480;pointer-events:none}
    .quality {position:absolute;right:1px;top:1px;min-width:23px;height:23px;
      padding:0 3px;border-radius:50%;font:bold 14px/23px sans-serif;box-shadow:0 1px 4px #2228;pointer-events:none}
    .status {font:13px var(--st-font);color:var(--st-text-color);margin:8px 0}
    .promotion button {padding:8px 16px;margin:4px;border-radius:5px;cursor:pointer}
    .square.movable {cursor:grab}.square.dragging {cursor:grabbing}
    .square.dragging svg {opacity:0}
    .drag-ghost {position:fixed;pointer-events:none;z-index:99999;will-change:transform;
      filter:drop-shadow(0 10px 6px #0008);transform:scale(1.08)}
    .drag-ghost svg {width:100%;height:100%}
    @media (prefers-reduced-motion:reduce) {.drag-ghost {filter:none;transform:none}}
    """,
    js="""
    export default function({data,parentElement,setTriggerValue}) {
      // Engine/tutor updates must not replace squares during a drag.
      const signature=JSON.stringify([data.fen,data.cells.map(c=>c.name),data.legal,data.revision]);
      const existing=parentElement._acervoState;
      if(existing?.signature===signature) {
        existing.update(data,setTriggerValue);
        document.addEventListener('keydown',existing.keyboard);
        return existing.detach;
      }
      existing?.cleanup();
      if(parentElement._auraFen!==data.fen)parentElement._lastAura=null;
      parentElement._auraFen=data.fen;
      const grid=parentElement.querySelector('.board');
      const promo=parentElement.querySelector('.promotion');
      grid.replaceChildren(); promo.replaceChildren();
      let selected=null, pending=false, drag=null, ghost=null, animating=false, suppressClick=false, disposed=false;
      const buttons=new Map();
      function select(square) {
        selected=square;
        for(const [name,button] of buttons) {
          button.classList.toggle('selected',name===square);
          button.classList.toggle('target',data.legal.some(m=>m.slice(0,2)===square && m.slice(2,4)===name));
        }
      }
      function emit(uci) {
        if(pending)return;
        pending=true; promo.replaceChildren();
        setTriggerValue('move',{uci,fen:data.fen,revision:data.revision});
      }
      function attempt(from,to) {
        const candidates=data.legal.filter(m=>m.slice(0,2)===from && m.slice(2,4)===to);
        if(!candidates.length)return false;
        if(candidates.length===1)emit(candidates[0]);
        else {
          promo.replaceChildren();
          for(const m of candidates) {
            const button=document.createElement('button');
            button.textContent=({q:'Dama',r:'Torre',b:'Bispo',n:'Cavalo'})[m[4]];
            button.onclick=()=>emit(m);promo.append(button);
          }
          promo.firstChild?.focus();
        }
        return true;
      }
      for(const cell of data.cells) {
        const button=document.createElement('button');
        button.type='button';button.className='square '+cell.color;
        button.dataset.square=cell.name;
        button.setAttribute('aria-label',cell.label);
        button.classList.toggle('last',data.last.includes(cell.name));
        if(cell.svg)button.innerHTML=cell.svg;
        const movable=data.legal.some(m=>m.startsWith(cell.name));
        button.draggable=false;
        button.classList.toggle('movable',movable);
        button.onclick=()=>{if(suppressClick)suppressClick=false;};
        button.onpointerdown=e=>{
          if(!movable || pending || animating || e.button!==0)return;
          drag={from:cell.name,button,x:e.clientX,y:e.clientY,id:e.pointerId,moved:false};
          button.setPointerCapture(e.pointerId);
        };
        button.onpointermove=e=>{
          if(!drag || drag.id!==e.pointerId)return;
          if(!drag.moved && Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<5)return;
          if(!drag.moved){
            drag.moved=true;select(drag.from);
            const size=button.getBoundingClientRect().width;
            ghost=document.createElement('div');ghost.className='drag-ghost';
            ghost.innerHTML=cell.svg;ghost.style.width=size+'px';ghost.style.height=size+'px';
            parentElement.append(ghost);button.classList.add('dragging');
          }
          ghost.style.left=(e.clientX-ghost.offsetWidth/2)+'px';
          ghost.style.top=(e.clientY-ghost.offsetHeight/2)+'px';
        };
        async function finish(e,cancel=false){
          if(!drag || drag.id!==e.pointerId)return;
          const released=drag;drag=null;
          if(button.hasPointerCapture(e.pointerId))button.releasePointerCapture(e.pointerId);
          if(!released.moved)return;
          suppressClick=true;animating=true;
          const rect=grid.getBoundingClientRect();
          const border=4, size=(rect.width-border*2)/8;
          const x=e.clientX-rect.left-border,y=e.clientY-rect.top-border;
          const index=Math.floor(y/size)*8+Math.floor(x/size);
          const to=!cancel && x>=0 && y>=0 && x<size*8 && y<size*8 ? data.cells[index]?.name : null;
          const legal=to && data.legal.some(m=>m.slice(0,2)===released.from && m.slice(2,4)===to);
          const destination=buttons.get(legal ? to : released.from).getBoundingClientRect();
          const movingGhost=ghost;
          const from={x:parseFloat(movingGhost.style.left),y:parseFloat(movingGhost.style.top)};
          const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
          await movingGhost.animate([
            {transform:'translate(0,0) scale(1.08)'},
            {transform:`translate(${destination.x-from.x}px,${destination.y-from.y}px) scale(1)`}
          ],{duration:reduced ? 0 : 160,easing:'ease-out',fill:'forwards'}).finished.catch(()=>{});
          if(disposed)return;
          animating=false;
          if(legal)attempt(released.from,to);
          else {select(null);}
          // Keep the piece at its destination until Python confirms the move.
          if(!pending){movingGhost.remove();ghost=null;button.classList.remove('dragging');}
          setTimeout(()=>{suppressClick=false;},0);
        }
        button.onpointerup=e=>finish(e);
        button.onpointercancel=e=>finish(e,true);
        buttons.set(cell.name,button);grid.append(button);
      }
      function paintBadge() {
        for(const [name,button] of buttons) {
          button.querySelector('.quality')?.remove();
          button.classList.toggle('last',data.last.includes(name));
          if(data.badge && name===data.badge.square) {
            if(data.badge.symbol==='!!') {
              const auraKey=data.fen+name;
              if(parentElement._lastAura!==auraKey) {
                button.classList.add('brilliant');parentElement._lastAura=auraKey;
              }
            } else button.classList.remove('brilliant');
            const badge=document.createElement('span');badge.className='quality';badge.textContent=data.badge.symbol;
            badge.style.background=data.badge.color;badge.style.color=data.badge.ink;
            badge.title=data.badge.label;button.append(badge);
          } else button.classList.remove('brilliant');
        }
      }
      paintBadge();
      function keyboard(event) {
        if(!data.navigation)return;
        if(event.altKey || event.ctrlKey || event.metaKey || pending || drag || animating)return;
        const editing=event.composedPath().some(el=>el.matches?.('input,textarea,select,[contenteditable="true"],[role="slider"],[role="combobox"],[role="listbox"]'));
        if(editing)return;
        const target=event.key==='ArrowLeft' ? data.ply-1 : event.key==='ArrowRight' ? data.ply+1 :
                     event.key==='Home' ? 0 : event.key==='End' ? data.total : null;
        if(target===null)return;
        event.preventDefault();
        if(target<0 || target>data.total || target===data.ply)return;
        pending=true;
        setTriggerValue('navigate',{from:data.ply,to:target});
      }
      document.addEventListener('keydown',keyboard);
      const detach=()=>document.removeEventListener('keydown',keyboard);
      const cleanup=()=>{disposed=true;detach();ghost?.remove();};
      parentElement._acervoState={signature,keyboard,detach,cleanup,update:(next,trigger)=>{
        data=next;setTriggerValue=trigger;
        if(pending){
          ghost?.remove();ghost=null;promo.replaceChildren();select(null);
          for(const button of buttons.values())button.classList.remove('dragging');
        }
        pending=false;
        paintBadge();
      }};
      return detach;
    }
    """,
)


def interactive_board(board, *, flip=False, last_move=None, category=None, on_move,
                      ply=0, total=0, on_navigate=None, key="interactive_board", disabled=False, revision=0):
    names = {chess.PAWN: "peão", chess.KNIGHT: "cavalo", chess.BISHOP: "bispo",
             chess.ROOK: "torre", chess.QUEEN: "dama", chess.KING: "rei"}
    cells = []
    for rank in (range(8) if flip else range(7, -1, -1)):
        for file in (range(7, -1, -1) if flip else range(8)):
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            name = chess.square_name(square)
            label = f"{names[piece.piece_type]} {'branco' if piece.color else 'preto'}" if piece else "vazia"
            cells.append({"name": name, "label": f"{name}: {label}",
                          "color": "dark" if (file + rank) % 2 == 0 else "light",
                          "svg": chess.svg.piece(piece) if piece else ""})
    badge = ({"square": chess.square_name(last_move.to_square), "symbol": category.symbol,
              "label": category.label, "color": category.color, "ink": category.ink}
             if last_move and category else None)
    return _BOARD(data={"fen": board.fen(), "cells": cells, "revision": revision,
                        "legal": [] if disabled or board.is_game_over() else [m.uci() for m in board.legal_moves],
                        "last": [chess.square_name(s) for s in (last_move.from_square, last_move.to_square)] if last_move else [],
                        "badge": badge, "ply": ply, "total": total, "navigation": on_navigate is not None}, key=key,
                  on_move_change=on_move, on_navigate_change=on_navigate or (lambda: None))
