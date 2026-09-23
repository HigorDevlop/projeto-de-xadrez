"""Inline Streamlit v2 board; python-chess is the authority on legal moves."""
import chess
import chess.svg
import streamlit as st
from io import StringIO
from functools import lru_cache
import chess.pgn

_BOARD = st.components.v2.component(
    "acervo_interactive_board",
    html='''<div class="workspace"><section><div class="board-floor"><div class="board-stage"><div class="board" aria-label="Tabuleiro interativo"></div>
    <svg class="arrows" viewBox="0 0 800 800" aria-hidden="true"></svg></div><div class="cat-place" aria-hidden="true"></div></div>
    <div class="promotion"></div><nav aria-label="Navegação de lances">
    <button type="button" data-nav="first" aria-label="Posição inicial">⏮</button>
    <button type="button" data-nav="previous" aria-label="Lance anterior">←</button>
    <span class="move-counter" aria-live="polite"></span>
    <button type="button" data-nav="next" aria-label="Próximo lance">→</button>
    <button type="button" data-nav="last" aria-label="Último lance">⏭</button></nav></section>
    <aside class="lesson" hidden><h3>Estudo com Bobby Fischer</h3>
    <p class="lesson-text" aria-live="polite"></p><small>Explicações preparadas para toda a partida.</small></aside></div>''',
    css="""
    .workspace {display:grid;grid-template-columns:minmax(0,1fr);gap:24px;color:var(--ink)}
    .workspace.split {grid-template-columns:minmax(0,1fr)}
    .workspace section {min-width:0;container-type:inline-size}
    .cat-place {display:none}
    .board-floor {position:relative}
    .workspace.table .board-floor {padding:28px 0}
    .workspace.table .board-stage:before {content:'';position:absolute;inset:-22px;z-index:-1;border-radius:22px;
      background:repeating-linear-gradient(3deg,#ffffff05 0 2px,#00000006 3px 5px,transparent 6px 16px),
        repeating-linear-gradient(92deg,#422416 0,#785034 70px,#52321f 145px,#8a5c38 240px);
      border:4px solid #321e14;box-shadow:0 10px 0 #28180f,0 24px 36px #0008,inset 0 2px 3px #c1976780}
    .workspace.table .board-stage {isolation:isolate}
    .workspace.mascot {--board-size:min(78vh,900px,calc((100cqw - 80px)/2.25))}
    .workspace.mascot .board-stage {width:var(--board-size)}
    .workspace.mascot .cat-place {display:block;position:absolute;bottom:0;
      left:calc(50% + var(--board-size)/2 + 28px);width:calc(var(--board-size)*1.1);aspect-ratio:1}
    @container(max-width:900px){
      .workspace.mascot .board-stage {width:min(100%,78vh,900px)}
      .workspace.mascot .cat-place {position:relative;left:auto;width:min(100%,84vh,936px);margin:20px 0 0 auto}
    }
    .board-stage {position:relative;width:min(100%,78vh,900px);margin:auto}
    .workspace.table .board-stage {max-width:calc(100% - 52px)}
    .workspace.editing .square {cursor:crosshair}
    .arrows {position:absolute;inset:4px;width:calc(100% - 8px);height:calc(100% - 8px);pointer-events:none;z-index:3}
    .board {display:grid;grid-template-columns:repeat(8,1fr);width:100%;margin:auto;scroll-margin-top:80px;
      aspect-ratio:1; border:4px solid #383a39;border-radius:5px;overflow:hidden;box-sizing:border-box}
    .square {position:relative; padding:0;border:0;border-radius:0;aspect-ratio:1;
      min-width:0;cursor:pointer;touch-action:none;user-select:none}
    .light {background:#f3f7eb}.dark {background:#629269}
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
    nav {display:flex;align-items:center;justify-content:center;gap:12px;margin-top:12px}
    nav[hidden],.lesson[hidden] {display:none}
    nav button,.promotion button {background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:10px;
      min-width:42px;min-height:42px;font-size:18px;cursor:pointer}
    nav button:disabled {opacity:.4;cursor:default}
    .move-counter {font:14px sans-serif;min-width:100px;text-align:center}
    .lesson {background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:16px;padding:24px;
      width:min(100%,760px);box-sizing:border-box;justify-self:center;align-self:start}
    .lesson h3 {font:600 21px sans-serif;margin-top:0}
    .lesson-text {font:18px/1.8 Georgia,serif;white-space:pre-wrap;overflow-wrap:anywhere}
    .lesson small {font:13px/1.6 sans-serif}
    @media(max-width:700px) {.workspace.split {grid-template-columns:1fr}.lesson {padding:16px}}
    .square.movable {cursor:grab}.square.dragging {cursor:grabbing}
    .square.dragging svg {opacity:0}
    .drag-ghost {position:fixed;pointer-events:none;z-index:99999;will-change:transform;
      filter:drop-shadow(0 10px 6px #0008);transform:scale(1.08)}
    .drag-ghost svg {width:100%;height:100%}
    @media (prefers-reduced-motion:reduce) {.drag-ghost {filter:none;transform:none}}
    """,
    js="""
    export default function render({data,parentElement,setTriggerValue}) {
      const epoch=data.epoch ?? data.revision;
      let navigation=parentElement._navigation;
      if(!navigation || navigation.epoch!==epoch) {
        clearTimeout(navigation?.timer);
        navigation=parentElement._navigation={epoch,index:data.ply,sequence:data.navigation_ack ?? 0,timer:null};
      } else if(data.frames && (data.navigation_ack ?? 0)<navigation.sequence) {
        data={...data,...data.frames[navigation.index],ply:navigation.index};
      } else navigation.index=data.ply;
      (parentElement.host ?? parentElement).style.setProperty('--surface',data.dark?'#202936':'#fffaf0');
      (parentElement.host ?? parentElement).style.setProperty('--ink',data.dark?'#f3f4f6':'#202530');
      (parentElement.host ?? parentElement).style.setProperty('--border',data.dark?'#566273':'#b5a991');
      function paintLesson() {
        const lesson=parentElement.querySelector('.lesson');
        const ready=Boolean(data.study && data.explanations);
        parentElement.querySelector('.workspace').classList.toggle('split',Boolean(data.study));
        parentElement.querySelector('.workspace').classList.toggle('mascot',Boolean(data.mascot));
        parentElement.querySelector('.workspace').classList.toggle('table',Boolean(data.table));
        parentElement.querySelector('.workspace').classList.toggle('editing',Boolean(data.editing));
        lesson.hidden=!ready;
        parentElement.querySelector('.lesson-text').textContent=ready ? data.explanations[data.ply] ?? '' : '';
        parentElement.querySelector('nav').hidden=!data.navigation;
        parentElement.querySelector('.move-counter').textContent=`Lance ${data.ply} de ${data.total}`;
        for(const b of parentElement.querySelectorAll('[data-nav]')) {
          const action=b.dataset.nav;
          b.disabled=['first','previous'].includes(action) ? data.ply===0 : data.ply===data.total;
          b.onclick=()=>navigate(action==='first'?0:action==='last'?data.total:data.ply+(action==='next'?1:-1));
        }
      }
      function navigate(target) {
        if(!data.navigation || drag || animating)return;
        target=Math.max(0,Math.min(data.total,target));
        if(target===navigation.index)return;
        navigation.index=target;
        navigation.sequence++;
        const payload={to:target,epoch,sequence:navigation.sequence};
        // Local positions and lessons change together, even while Python is busy.
        if(data.frames?.[target]) {
          render({data:{...data,...data.frames[target],ply:target,navigation_ack:navigation.sequence},parentElement,setTriggerValue});
        }
        clearTimeout(navigation.timer);
        navigation.timer=setTimeout(()=>setTriggerValue('navigate',payload),30);
      }
      // Engine/tutor updates must not replace squares during a drag.
      const signature=JSON.stringify([data.fen,data.cells.map(c=>c.name),data.legal,data.revision,data.ply,data.total,data.editing,data.editTool]);
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
      const arrowLayer=parentElement.querySelector('.arrows');
      const arrowContext=JSON.stringify([data.fen,data.revision,data.ply,data.cells.map(c=>c.name)]);
      if(parentElement._arrowContext!==arrowContext){parentElement._arrows=new Map();parentElement._arrowContext=arrowContext;}
      const arrows=parentElement._arrows;
      let arrowDrag=null;
      grid.oncontextmenu=e=>e.preventDefault();
      function squareAt(e) {
        const rect=grid.getBoundingClientRect(),size=(rect.width-8)/8;
        const x=e.clientX-rect.left-4,y=e.clientY-rect.top-4;
        return x>=0 && y>=0 && x<size*8 && y<size*8 ? data.cells[Math.floor(y/size)*8+Math.floor(x/size)]?.name : null;
      }
      function paintArrows(preview=null) {
        arrowLayer.replaceChildren();
        for(const [from,to] of [...arrows.values(),...(preview?[preview]:[])]) {
          if(!to || from===to)continue;
          const a=data.cells.findIndex(c=>c.name===from),b=data.cells.findIndex(c=>c.name===to);
          if(a<0 || b<0)continue;
          const x=a%8*100+50,y=Math.floor(a/8)*100+50;
          const dx=(b%8-a%8)*100,dy=(Math.floor(b/8)-Math.floor(a/8))*100,length=Math.hypot(dx,dy);
          const polygon=document.createElementNS('http://www.w3.org/2000/svg','polygon');
          polygon.setAttribute('class','annotation-arrow');
          polygon.setAttribute('points',`0,-9 ${length-36},-9 ${length-36},-26 ${length},0 ${length-36},26 ${length-36},9 0,9`);
          polygon.setAttribute('transform',`translate(${x} ${y}) rotate(${Math.atan2(dy,dx)*180/Math.PI})`);
          polygon.setAttribute('fill','#f5a623');polygon.setAttribute('fill-opacity','.86');
          polygon.setAttribute('stroke','#573600');polygon.setAttribute('stroke-width','1.5');
          arrowLayer.append(polygon);
        }
      }
      function clearArrows(){arrows.clear();paintArrows();}
      paintArrows();
      const promo=parentElement.querySelector('.promotion');
      grid.replaceChildren(); promo.replaceChildren();
      let selected=null, pending=false, drag=null, ghost=null, animating=false, suppressClick=false, disposed=false;
      paintLesson();
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
        clearArrows();
        pending=true; promo.replaceChildren();
        setTriggerValue('move',{uci,fen:data.fen,revision:data.revision,ply:data.ply});
      }
      function attempt(from,to) {
        if(data.editing){
          if(pending)return false;
          pending=true;clearArrows();
          setTriggerValue('edit',{from,to,revision:data.revision,fen:data.fen});return true;
        }
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
        const pieceSvg=cell.svg || data.pieces?.[cell.piece] || '';
        if(pieceSvg)button.innerHTML=pieceSvg;
        const movable=data.editing ? Boolean(cell.piece || cell.svg) && data.editTool==='move' : data.legal.some(m=>m.startsWith(cell.name));
        button.draggable=false;
        button.classList.toggle('movable',movable);
        button.onclick=()=>{
          if(suppressClick){suppressClick=false;return;}
          if(data.editing && data.editTool!=='move' && !pending){
            pending=true;setTriggerValue('edit',{to:cell.name,piece:data.editTool==='erase'?'':data.editTool,
              revision:data.revision,fen:data.fen});
          } else if(data.editing && data.editTool==='move'){
            if(selected && selected!==cell.name){attempt(selected,cell.name);select(null);}
            else select(cell.name);
          }
        };
        button.onpointerdown=e=>{
          if(e.button===2){
            e.preventDefault();
            if(drag || animating)return;
            arrowDrag={from:cell.name,id:e.pointerId};button.setPointerCapture(e.pointerId);return;
          }
          if(!movable || pending || animating || e.button!==0)return;
          clearArrows();
          drag={from:cell.name,button,x:e.clientX,y:e.clientY,id:e.pointerId,moved:false};
          button.setPointerCapture(e.pointerId);
        };
        button.onpointermove=e=>{
          if(arrowDrag?.id===e.pointerId){paintArrows([arrowDrag.from,squareAt(e)]);return;}
          if(!drag || drag.id!==e.pointerId)return;
          if(!drag.moved && Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<5)return;
          if(!drag.moved){
            drag.moved=true;select(drag.from);
            const size=button.getBoundingClientRect().width;
            ghost=document.createElement('div');ghost.className='drag-ghost';
            ghost.innerHTML=pieceSvg;ghost.style.width=size+'px';ghost.style.height=size+'px';
            parentElement.append(ghost);button.classList.add('dragging');
          }
          ghost.style.left=(e.clientX-ghost.offsetWidth/2)+'px';
          ghost.style.top=(e.clientY-ghost.offsetHeight/2)+'px';
        };
        async function finish(e,cancel=false){
          if(arrowDrag?.id===e.pointerId){
            const from=arrowDrag.from,to=cancel?null:squareAt(e);arrowDrag=null;
            if(button.hasPointerCapture(e.pointerId))button.releasePointerCapture(e.pointerId);
            if(to && to!==from){const key=from+'-'+to;if(arrows.has(key))arrows.delete(key);else arrows.set(key,[from,to]);}
            paintArrows();return;
          }
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
          const legal=to && (data.editing || data.legal.some(m=>m.slice(0,2)===released.from && m.slice(2,4)===to));
          const destination=buttons.get(legal ? to : released.from).getBoundingClientRect();
          const movingGhost=ghost;
          const from={x:parseFloat(movingGhost.style.left),y:parseFloat(movingGhost.style.top)};
          const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
          // Submit on release; server validation runs during the short visual settling.
          if(legal)attempt(released.from,to);
          await movingGhost.animate([
            {transform:'translate(0,0) scale(1.08)'},
            {transform:`translate(${destination.x-from.x}px,${destination.y-from.y}px) scale(1)`}
          ],{duration:reduced ? 0 : 90,easing:'ease-out',fill:'forwards'}).finished.catch(()=>{});
          if(disposed)return;
          animating=false;
          if(!legal)select(null);
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
        if(event.altKey || event.ctrlKey || event.metaKey || drag || arrowDrag || animating)return;
        const editing=event.composedPath().some(el=>el.matches?.('input,textarea,select,[contenteditable="true"],[role="slider"],[role="combobox"],[role="listbox"],[role="radio"],[role="tab"]'));
        if(editing)return;
        const target=event.key==='ArrowLeft' ? data.ply-1 : event.key==='ArrowRight' ? data.ply+1 :
                     event.key==='Home' ? 0 : event.key==='End' ? data.total : null;
        if(target===null)return;
        event.preventDefault();
        if(target<0 || target>data.total || target===data.ply)return;
        navigate(target);
      }
      document.addEventListener('keydown',keyboard);
      const detach=()=>document.removeEventListener('keydown',keyboard);
      const cleanup=()=>{disposed=true;detach();ghost?.remove();};
      parentElement._acervoState={signature,keyboard,detach,cleanup,update:(next,trigger)=>{
        data=next;setTriggerValue=trigger;
        // Same-revision refreshes do not acknowledge a move. Only a new revision
        // rebuilds the board and unlocks the next attempt.
        paintBadge();
        paintLesson();
      }};
      return detach;
    }
    """,
)


def position_data(board, flip=False, last_move=None):
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
                          "piece": piece.symbol() if piece else ""})
    return {"fen": board.fen(), "cells": cells,
            "legal": [] if board.is_game_over() else [m.uci() for m in board.legal_moves],
            "last": [chess.square_name(s) for s in (last_move.from_square, last_move.to_square)] if last_move else []}


@st.cache_data(max_entries=8, show_spinner=False)
def game_frames(pgn, flip=False):
    game = chess.pgn.read_game(StringIO(pgn)) or chess.pgn.Game()
    board = game.board()
    frames = [position_data(board, flip)]
    for move in game.mainline_moves():
        board.push(move)
        frames.append(position_data(board, flip, move))
    return frames


@lru_cache(maxsize=1)
def piece_images():
    return {symbol: chess.svg.piece(chess.Piece.from_symbol(symbol)) for symbol in 'PNBRQKpnbrqk'}


def interactive_board(board, *, flip=False, last_move=None, category=None, on_move,
                      ply=0, total=0, on_navigate=None, key="interactive_board", disabled=False, revision=0,
                      pgn=None, epoch=None, navigation_ack=0, explanations=None, study=False, dark=False, reviews=None,
                      mascot=False, table=False, editing=False, edit_tool='move', on_edit=None):
    badge = ({"square": chess.square_name(last_move.to_square), "symbol": category.symbol,
              "label": category.label, "color": category.color, "ink": category.ink}
             if last_move and category else None)
    frames = game_frames(pgn, flip) if pgn is not None else None
    if frames:
        from chess_review import CATEGORIES
        for index, frame in enumerate(frames):
            review = (reviews or {}).get(index)
            quality = CATEGORIES[review.category] if review else None
            frame['badge'] = ({'square': frame['last'][-1], 'symbol': quality.symbol, 'label': quality.label,
                               'color': quality.color, 'ink': quality.ink} if quality and frame['last'] else None)
    return _BOARD(data={**position_data(board, flip, last_move), "revision": revision,
                        "legal": [] if disabled or board.is_game_over() else [m.uci() for m in board.legal_moves],
                        "last": [chess.square_name(s) for s in (last_move.from_square, last_move.to_square)] if last_move else [],
                        "badge": badge, "ply": ply, "total": total, "navigation": on_navigate is not None,
                        "frames": frames, "pieces": piece_images(), "epoch": epoch, "navigation_ack": navigation_ack,
                        "explanations": explanations, "study": study, "dark": dark, "mascot": mascot,
                        "table": table, "editing": editing, "editTool": edit_tool}, key=key,
                  on_move_change=on_move, on_navigate_change=on_navigate or (lambda: None),
                  on_edit_change=on_edit or (lambda: None))
