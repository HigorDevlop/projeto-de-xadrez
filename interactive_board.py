"""Inline Streamlit v2 board; python-chess is the authority on legal moves."""
import chess
import chess.svg
import streamlit as st
from io import StringIO
from functools import lru_cache
import chess.pgn
from chess_review import CATEGORIES, SPECIAL_CATEGORIES, canonical_category
from design_tokens import palette

_BOARD = st.components.v2.component(
    "acervo_interactive_board",
    html='''<div class="workspace"><section><div class="board-floor"><div class="board-stage"><div class="board" aria-label="Tabuleiro interativo"></div>
    <svg class="arrows" viewBox="0 0 800 800" aria-hidden="true"></svg>
    <svg class="training-hint-layer" viewBox="0 0 800 800" aria-hidden="true"></svg>
    <svg class="move-effect-layer" viewBox="0 0 800 800" aria-hidden="true"></svg></div><div class="cat-place" aria-hidden="true"></div></div>
    <div class="promotion"></div><nav aria-label="Navegação de lances">
    <button type="button" data-nav="first" aria-label="Posição inicial">⏮</button>
    <button type="button" data-nav="previous" aria-label="Lance anterior">←</button>
    <span class="move-counter" aria-live="polite"></span>
    <button type="button" data-nav="next" aria-label="Próximo lance">→</button>
    <button type="button" data-nav="last" aria-label="Último lance">⏭</button></nav>
    <p class="move-quality" role="status" aria-live="polite" hidden><span aria-hidden="true"></span><strong></strong></p></section>
    <aside class="lesson" hidden><h3>Estudo com Bobby Fischer</h3>
    <p class="lesson-text" aria-live="polite"></p><small>Explicações preparadas para toda a partida.</small></aside></div>''',
    css="""
    .workspace {display:grid;grid-template-columns:minmax(0,1fr);gap:24px;color:var(--ink);font-family:'Segoe UI',system-ui,sans-serif}
    .workspace.split {grid-template-columns:minmax(0,1fr)}
    .workspace section {min-width:0;container-type:inline-size}
    .cat-place {display:none}
    .board-floor {position:relative}
    .workspace.table .board-floor {padding:28px 0}
    .workspace.table .board-stage:before {content:'';position:absolute;inset:-22px;z-index:-1;border-radius:14px;
      background:repeating-linear-gradient(92deg,#614731 0,#71533a 90px,#654a34 180px);
      border:1px solid #8c7051;box-shadow:0 5px 0 #443224,0 12px 24px #0003}
    .workspace.table .board-stage {isolation:isolate}
    .workspace.mascot {--board-size:min(78vh,900px,calc((100cqw - 80px)/3.2))}
    .workspace.mascot .board-stage {width:var(--board-size)}
    .workspace.mascot .cat-place {display:block;position:absolute;bottom:0;
      left:calc(50% + var(--board-size)/2 + 28px);width:calc(var(--board-size)*1.1);aspect-ratio:1}
    @container(max-width:900px){
      .workspace.mascot .board-stage {width:min(100%,78vh,900px)}
      .workspace.mascot .cat-place {position:relative;left:auto;width:min(100%,84vh,936px);margin:20px 0 0 auto}
    }
    .board-stage {position:relative;width:min(100%,78vh,900px);margin:auto}
    .workspace.table .board-stage {max-width:calc(100% - 52px)}
    .workspace.expanded section {display:grid;grid-template-columns:minmax(0,1fr)}
    .workspace.expanded .board-floor {display:contents}
    .workspace.expanded .board-stage {grid-row:1;width:min(100%,82vh,960px);margin:28px auto}
    .workspace.expanded nav {grid-row:2}
    .workspace.expanded .promotion {grid-row:3}
    .workspace.expanded .move-quality {grid-row:4}
    .workspace.expanded .cat-place {grid-row:5;position:relative;left:auto;bottom:auto;justify-self:end;
      width:min(100%,84vh,980px);margin:24px 0 0}
    .workspace.editing .square {cursor:crosshair}
    .arrows,.training-hint-layer {position:absolute;inset:4px;width:calc(100% - 8px);height:calc(100% - 8px);pointer-events:none;z-index:3}
    .board {display:grid;grid-template-columns:repeat(8,1fr);width:100%;margin:auto;scroll-margin-top:80px;
      aspect-ratio:1; border:4px solid #344D3D;border-radius:5px;overflow:hidden;box-sizing:border-box}
    .square {position:relative; padding:0;border:0;border-radius:0;aspect-ratio:1;
      min-width:0;cursor:pointer;touch-action:none;user-select:none}
    .light {background:#F2EEDF}.dark {background:#72977E}
    .square svg {width:88%;height:88%;pointer-events:none;vertical-align:middle}
    .board-coordinate{position:absolute;pointer-events:none;font:600 clamp(9px,1.2vw,13px)/1 sans-serif;z-index:2}
    .board-coordinate.rank{top:3px;left:3px}.board-coordinate.file{bottom:3px;right:3px}
    .light .board-coordinate{color:#574028}.dark .board-coordinate{color:#fff3dc}
    .square.last {box-shadow:inset 0 0 0 4px #B99350}
    .square.training-correct {box-shadow:inset 0 0 0 7px #16a34a}
    .square.training-wrong {box-shadow:inset 0 0 0 7px #ef4444}
    .workspace.repertoire .board{border-color:#081219;border-radius:0;box-shadow:none}
    .workspace.repertoire .square.light{background:#efdcba}
    .workspace.repertoire .square.dark{background:#af8b68}
    .workspace.repertoire .square.last{background:#a8b483}
    .workspace.repertoire .square.training-correct{animation:recall-correct .6s ease-out both}
    .workspace.repertoire .square.training-wrong{animation:recall-wrong .6s ease-out both}
    @keyframes recall-correct{0%,40%{box-shadow:inset 0 0 0 100px #5cbb7755}100%{box-shadow:inset 0 0 0 0 transparent}}
    @keyframes recall-wrong{0%,40%{box-shadow:inset 0 0 0 100px #d879794d}100%{box-shadow:inset 0 0 0 0 transparent}}
    @media(prefers-reduced-motion:reduce){.workspace.repertoire .square.training-correct,.workspace.repertoire .square.training-wrong{animation-duration:.01s}}
    .square.special-white {--aura-color:#35a8ff;--aura-soft:#35a8ff66}
    .square.special-black {--aura-color:#ff453a;--aura-soft:#ff453a77}
    .square.special:before {content:'';position:absolute;inset:9%;border-radius:50%;pointer-events:none;
      background:radial-gradient(circle,var(--aura-soft) 10%,transparent 72%);
      box-shadow:0 0 13px 4px var(--aura-color);animation:piece-aura 2.4s ease-in-out infinite}
    .square.special>svg {position:relative;filter:drop-shadow(0 0 5px var(--aura-color))}
    @keyframes piece-aura {0%,100% {opacity:.5;transform:scale(.78)} 50% {opacity:.95;transform:scale(1.03)}}
    .move-effect-layer {position:absolute;inset:4px;width:calc(100% - 8px);height:calc(100% - 8px);
      overflow:hidden;pointer-events:none;z-index:4}
    .lightning-bolt {fill:none;stroke-linecap:round;stroke-linejoin:round;animation:lightning-strike 950ms ease-out both}
    .lightning-halo {stroke:#35a8ff;stroke-width:14;filter:blur(5px)}
    .lightning-core {stroke:#e3f5ff;stroke-width:4}
    @keyframes lightning-strike {0%{opacity:0}12%{opacity:1}25%{opacity:.35}36%{opacity:1}60%{opacity:.85}100%{opacity:0}}
    .impact {fill:none;stroke-width:5;transform-origin:center;transform-box:fill-box;
      animation:impact-ring 900ms ease-out both}
    @keyframes impact-ring {0%,25% {opacity:0;transform:scale(.2)}40%{opacity:.9}100%{opacity:0;transform:scale(2)}}
    .meteor-flight {animation:meteor-strike 1.1s cubic-bezier(.3,.1,.55,1) both}
    @keyframes meteor-strike {0%{transform:translate(220px,-320px) scale(.35);opacity:0}
      15%{opacity:1}62%{transform:translate(0,0) scale(1);opacity:1}100%{transform:translate(0,0) scale(1.3);opacity:0}}
    .meteor-impact {animation-delay:250ms;stroke:#ff453a}
    @media (prefers-reduced-motion:reduce) {.square.special:before {animation:none;opacity:.5}.move-effect-layer {display:none}}
    .square.selected {box-shadow:inset 0 0 0 4px #176B4A}
    .square:focus-visible {outline:4px solid #176B4A;outline-offset:-4px;z-index:2}
    .square.target:after {content:'';position:absolute;inset:38%;border-radius:50%;background:#203B2B80;pointer-events:none}
    .quality {position:absolute;right:2px;top:2px;min-width:32px;height:28px;display:flex;align-items:center;justify-content:center;
      padding:0 5px;box-sizing:border-box;border:2px solid #fff;border-radius:8px;font:800 15px/1 'Segoe UI',system-ui,sans-serif;
      box-shadow:0 1px 5px #10251955;pointer-events:none;z-index:5}
    .move-quality {display:flex;align-items:center;justify-content:center;gap:9px;width:fit-content;max-width:100%;
      margin:14px auto 0;padding:7px 14px;border-radius:8px;border:1px solid #ffffff88;
      font:600 14px/1.4 'Segoe UI',system-ui,sans-serif;box-sizing:border-box}
    .move-quality span {font-size:21px;font-weight:800}.move-quality[hidden] {display:none}
    .status {font:13px var(--st-font);color:var(--st-text-color);margin:8px 0}
    .promotion button {padding:8px 16px;margin:4px;border-radius:5px;cursor:pointer}
    nav {display:flex;align-items:center;justify-content:center;gap:8px;width:fit-content;max-width:100%;margin:12px auto 0;
      background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:6px;box-sizing:border-box}
    nav[hidden],.lesson[hidden] {display:none}
    nav button,.promotion button {background:var(--surface);color:var(--ink);border:1px solid transparent;border-radius:9px;
      min-width:42px;min-height:42px;font-size:18px;cursor:pointer;transition:background .15s,border-color .15s}
    nav button:hover:not(:disabled) {background:var(--soft);border-color:var(--border)}
    nav button:focus-visible,.promotion button:focus-visible {outline:3px solid var(--accent);outline-offset:2px}
    nav button:disabled {opacity:.4;cursor:default}
    .move-counter {font:600 13px 'Segoe UI',system-ui,sans-serif;min-width:100px;text-align:center;font-variant-numeric:tabular-nums;color:var(--muted)}
    @media(max-width:400px) {nav{gap:4px;padding:5px}nav button{min-width:36px;min-height:40px}.move-counter{min-width:84px;font-size:12px}}
    .lesson {background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:14px;padding:24px;
      width:min(100%,760px);box-sizing:border-box;justify-self:center;align-self:start}
    .lesson h3 {font:400 25px/1.3 Georgia,serif;margin-top:0}
    .lesson-text {font:18px/1.8 Georgia,serif;white-space:pre-wrap;overflow-wrap:anywhere}
    .lesson small {font:13px/1.6 'Segoe UI',system-ui,sans-serif;color:var(--muted)}
    @media(max-width:700px) {.workspace.split {grid-template-columns:1fr}.lesson {padding:16px}}
    .square.movable {cursor:grab}.square.dragging {cursor:grabbing}
    .square.dragging svg {opacity:0}
    .drag-ghost {position:fixed;pointer-events:none;z-index:99999;will-change:transform;
      filter:drop-shadow(0 10px 6px #0008);transform:scale(1.08)}
    .drag-ghost svg {width:100%;height:100%}
    @media (prefers-reduced-motion:reduce) {.drag-ghost {filter:none;transform:none}}
    """,
    js="""
    export default function render({data,parentElement,setTriggerValue,setStateValue}) {
      const revisionNumber=value=>Number(String(value).split(':').at(-1));
      // Reconcile asynchronous acknowledgements without rolling a locally played
      // quiz back to an older position. Unacknowledged attempts travel together.
      const local=parentElement._quizLocal;
      const divergent=local && local.epoch===data.epoch &&
        revisionNumber(data.revision)<revisionNumber(local.revision) &&
        !parentElement._predictedRevisions?.has(data.revision);
      parentElement._quizAttempts=divergent ? [] : (parentElement._quizAttempts || []).filter(event=>
        String(event.revision).split(':')[0]===String(data.revision).split(':')[0] &&
        revisionNumber(event.revision)>=revisionNumber(data.revision));
      if(!parentElement._quizAttempts.length)clearTimeout(parentElement._quizRetryTimer);
      if(local && !divergent && local.epoch===data.epoch && revisionNumber(data.revision)<revisionNumber(local.revision)) {
        data=local;
      } else {
        parentElement._quizLocal=null;
      }
      const epoch=data.epoch ?? data.revision;
      parentElement.querySelector('.board').dataset.revision=String(data.revision);
      // Frames carry FEN and legal moves once; square labels/SVGs are shared.
      // Full frames remain accepted for independently mounted board components.
      function resolveFrame(frame) {
        if(frame.cells)return data.disabled?{...frame,legal:[]}:frame;
        const pieces=new Map(),names={p:'peão',n:'cavalo',b:'bispo',r:'torre',q:'dama',k:'rei'};
        let rank=7,file=0;
        for(const token of frame.fen.split(' ')[0]) {
          if(token==='/'){rank--;file=0;}
          else if(/[1-8]/.test(token))file+=Number(token);
          else {pieces.set(String.fromCharCode(97+file)+(rank+1),token);file++;}
        }
        const cells=data.cells.map(cell=>{
          const piece=pieces.get(cell.name) || '';
          const label=piece?`${names[piece.toLowerCase()]} ${piece===piece.toUpperCase()?'branco':'preto'}`:'vazia';
          return {name:cell.name,color:cell.color,piece,label:`${cell.name}: ${label}`};
        });
        return {...frame,cells,legal:data.disabled?[]:
          typeof frame.legal==='string'?frame.legal.split(' ').filter(Boolean):frame.legal};
      }
      let navigation=parentElement._navigation;
      if(!navigation || navigation.epoch!==epoch) {
        clearTimeout(navigation?.timer);
        navigation=parentElement._navigation={epoch,index:data.ply,sequence:data.navigation_ack ?? 0,
          sent:data.navigation_ack ?? 0,timer:null,trigger:setTriggerValue};
        navigation.flush=()=>{
          clearTimeout(navigation.timer);navigation.timer=null;
          if(parentElement._navigation!==navigation || !(parentElement.host ?? parentElement).isConnected ||
             navigation.sent>=navigation.sequence)return;
          navigation.sent=navigation.sequence;
          navigation.trigger('navigate',{to:navigation.index,epoch:navigation.epoch,sequence:navigation.sequence});
        };
      } else if(data.frames && (data.navigation_ack ?? 0)<navigation.sequence) {
        data={...data,...resolveFrame(data.frames[navigation.index]),ply:navigation.index};
      } else {
        navigation.index=data.ply;
        navigation.sequence=Math.max(navigation.sequence,data.navigation_ack ?? 0);
        navigation.sent=Math.max(navigation.sent,data.navigation_ack ?? 0);
      }
      navigation.trigger=setTriggerValue;
      const theme=data.theme ?? (data.dark ?
        {surface:'#1A2720',ink:'#EDF3ED',muted:'#ACBCAF',border:'#354A3C',soft:'#223329',accent:'#85C69A'} :
        {surface:'#FFFEFA',ink:'#202B26',muted:'#626F66',border:'#D9DED5',soft:'#ECEFE8',accent:'#176B4A'});
      for(const [token,value] of Object.entries(theme))
        (parentElement.host ?? parentElement).style.setProperty('--'+token.replaceAll('_','-'),value);
      function paintLesson() {
        const lesson=parentElement.querySelector('.lesson');
        const ready=Boolean(data.study && data.explanations);
        parentElement.querySelector('.workspace').classList.toggle('split',Boolean(data.study));
        parentElement.querySelector('.workspace').classList.toggle('mascot',Boolean(data.mascot));
        parentElement.querySelector('.workspace').classList.toggle('table',Boolean(data.table));
        parentElement.querySelector('.workspace').classList.toggle('expanded',Boolean(data.expanded));
        parentElement.querySelector('.workspace').classList.toggle('editing',Boolean(data.editing));
        parentElement.querySelector('.workspace').dataset.editTool=data.editTool || 'move';
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
        // Local positions and lessons change together, even while Python is busy.
        if(data.frames?.[target]) {
          render({data:{...data,...resolveFrame(data.frames[target]),ply:target,
            navigation_ack:data.navigation_ack ?? 0},parentElement,setTriggerValue});
        }
        clearTimeout(navigation.timer);
        // Send only the final position after a pause, not a rerun for every arrow.
        if(data.frames)navigation.timer=setTimeout(navigation.flush,360);
        else navigation.flush(); // A board without a PGN must ask Python for its next position.
      }
      // Engine/tutor updates must not replace squares during a drag.
      const signature=JSON.stringify([data.trainingMode ? data.epoch : epoch,data.cells.map(c=>c.name),
        data.trainingMode ? null : data.revision,data.trainingMode ? null : data.disabled,
        data.navigation,data.editing,data.editTool,data.showCoordinates]);
      const existing=parentElement._acervoState;
      const preservedSelection=data.trainingMode && existing?.signature===signature ? existing.status().selected : null;
      if(existing?.signature===signature) {
        existing.update(data,setTriggerValue,setStateValue);
        document.addEventListener('keydown',existing.keyboard);
        document.addEventListener('click',existing.externalSync);
        return existing.detach;
      }
      existing?.cleanup();
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
      let pendingEvent=data.trainingMode ? parentElement._trainingPending : null;
      if(pendingEvent && (pendingEvent.revision!==data.revision || pendingEvent.fen!==data.fen)){
        pendingEvent=null;parentElement._trainingPending=null;
      }
      let selected=null, pending=Boolean(pendingEvent), drag=null, ghost=null, animating=false, suppressClick=false, disposed=false;
      let pendingTimer=null;
      function waitForAck() {
        clearTimeout(pendingTimer);
        if(disposed || !data.syncRecovery)return;
        pendingTimer=setTimeout(()=>{
          if(disposed || !pending || !(parentElement.host ?? parentElement).isConnected)return;
          // Python applies this only if the original revision is still waiting.
          const event=pendingEvent ?? {revision:data.revision,fen:data.fen};
          if(data.syncRecovery && setStateValue)setStateValue('sync',event);
          else setTriggerValue('sync',event);
          waitForAck();
        },2000);
      }
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
        if(data.trainingMode && data.trainingExpected){
          const correct=uci===data.trainingExpected;
          const target=buttons.get(uci.slice(2,4));
          target?.classList.remove('training-correct','training-wrong');
          if(target){void target.offsetWidth;target.classList.add(correct?'training-correct':'training-wrong');}
          if(!correct){
            ghost?.remove();ghost=null;
            buttons.get(uci.slice(0,2))?.classList.remove('dragging');
          }
        }
        pendingEvent={uci,fen:data.fen,revision:data.revision,ply:data.ply};
        parentElement._lastTrainingEmit=pendingEvent;
        if((data.quiz || data.trainingLine) && data.syncRecovery){
          const attempts=parentElement._quizAttempts ||= [];
          attempts.push(pendingEvent);
          const source=data, quiz=data.quiz, correct=uci===data.trainingExpected;
          let next=null;
          if(quiz){
          const queue=[...quiz.queue], retry=[...quiz.retry];
          if(correct){
            if(quiz.assisted && !retry.includes(queue[0]))retry.push(queue[0]);
            queue.shift();
            if(!queue.length){queue.push(...retry);retry.length=0;}
          }
          const frame=quiz.positions[String(queue[0])];
          if(frame){
            next={...data,...frame,trainingFeedback:null,trainingHint:null,animateMove:null,
              revision:String(data.revision).split(':')[0]+':'+(revisionNumber(data.revision)+2),
              quiz:{...quiz,queue,retry,assisted:false}};
          }
          } else if(correct){
            const line=data.trainingLine, current=line.current+2;
            const frame=line.positions[String(current)];
            if(frame)next={...data,...frame,trainingFeedback:null,animateMove:null,
              trainingHint:line.mode==='learn'?frame.trainingExpected:null,
              revision:String(data.revision).split(':')[0]+':'+(revisionNumber(data.revision)+3),
              trainingLine:{...line,current}};
          }
          if(next){
            const known=parentElement._predictedRevisions ||= new Set();
            known.add(data.revision);known.add(next.revision);
            clearTimeout(parentElement._quizTimer);
            const showNext=()=>{
              if(data.revision!==source.revision || disposed || !grid.isConnected)return;
              parentElement._quizLocal=next;
              grid.dataset.revision=String(next.revision);
              parentElement._acervoState.update(next,setTriggerValue,setStateValue);
            };
            if(data.instant)showNext();
            else parentElement._quizTimer=setTimeout(showNext,120);
          } else if(correct && data.instant){
            const played=data.trainingLine?.positions[String(data.trainingLine.current)]?.played ||
              data.quiz?.positions[String(data.quiz.queue[0])]?.played;
            if(played){data={...data,...played};paintPosition();}
          }
          pendingEvent={attempts:[...attempts]};
          clearTimeout(parentElement._quizRetryTimer);
          const retrySync=()=>{
            if(!grid.isConnected || !parentElement._quizAttempts?.length)return;
            setStateValue('sync',{attempts:[...parentElement._quizAttempts]});
            parentElement._quizRetryTimer=setTimeout(retrySync,2000);
          };
          parentElement._quizRetryTimer=setTimeout(retrySync,2000);
        }
        if(data.trainingMode)parentElement._trainingPending=pendingEvent;
        // Keep an opening move until Python acknowledges its revision. A trigger
        // can be consumed by a simultaneous timed rerun before the lesson sees it.
        if(data.syncRecovery && setStateValue)setStateValue('move',pendingEvent);
        else setTriggerValue('move',pendingEvent);
        waitForAck();
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
        const cellSvg=()=>{const current=data.cells.find(item=>item.name===cell.name);
          return current?.svg || data.pieces?.[current?.piece] || '';};
        const pieceSvg=cellSvg();
        if(pieceSvg)button.innerHTML=pieceSvg;
        if(data.showCoordinates){
          const index=data.cells.indexOf(cell);
          for(const [kind,label,visible] of [['rank',cell.name[1],index%8===0],['file',cell.name[0],index>=56]]){
            if(!visible)continue;
            const coordinate=document.createElement('span');
            coordinate.className='board-coordinate '+kind;coordinate.textContent=label;
            coordinate.setAttribute('aria-hidden','true');button.append(coordinate);
          }
        }
        button._pieceSvg=pieceSvg;
        const movable=()=>data.editing ? Boolean(cellSvg()) && data.editTool==='move' : data.legal.some(m=>m.startsWith(cell.name));
        button.draggable=false;
        button.classList.toggle('movable',movable());
        button.onclick=()=>{
          parentElement._lastTrainingClick={square:cell.name,revision:data.revision,selected,pending,animating,suppressClick};
          if(suppressClick){suppressClick=false;return;}
          if(data.trainingMode && !data.editing){
            if(pending || animating || data.disabled)return;
            if(selected && selected!==cell.name){
              if(attempt(selected,cell.name)){select(null);return;}
            }
            select(movable()?cell.name:null);return;
          }
          if(data.editing && data.editTool!=='move' && !pending){
            pending=true;setTriggerValue('edit',{to:cell.name,piece:data.editTool==='erase'?'':data.editTool,
              revision:data.revision,fen:data.fen});
          } else if(data.editing && data.editTool==='move'){
            if(selected && selected!==cell.name){attempt(selected,cell.name);select(null);}
            else select(cell.name);
          }
        };
        button.onpointerdown=e=>{
          parentElement._lastTrainingPointer={square:cell.name,revision:data.revision,x:e.clientX,y:e.clientY,pending,animating};
          if(e.button===2){
            e.preventDefault();
            if(drag || animating)return;
            arrowDrag={from:cell.name,id:e.pointerId};button.setPointerCapture(e.pointerId);return;
          }
          if(!movable() || pending || animating || e.button!==0)return;
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
            ghost.innerHTML=cellSvg();ghost.style.width=size+'px';ghost.style.height=size+'px';
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
          if(disposed || !ghost){animating=false;suppressClick=false;return;}
          suppressClick=true;animating=true;
          const rect=grid.getBoundingClientRect();
          const border=4, size=(rect.width-border*2)/8;
          const x=e.clientX-rect.left-border,y=e.clientY-rect.top-border;
          const index=Math.floor(y/size)*8+Math.floor(x/size);
          const to=!cancel && x>=0 && y>=0 && x<size*8 && y<size*8 ? data.cells[index]?.name : null;
          const legal=to && (data.editing || data.legal.some(m=>m.slice(0,2)===released.from && m.slice(2,4)===to));
          parentElement._lastTrainingRelease={from:released.from,to,legal,cancel,revision:data.revision};
          const destination=buttons.get(legal ? to : released.from).getBoundingClientRect();
          const movingGhost=ghost;
          const from={x:parseFloat(movingGhost.style.left),y:parseFloat(movingGhost.style.top)};
          const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
          // Submit on release; server validation runs during the short visual settling.
          if(legal)attempt(released.from,to);
          try {
            await movingGhost.animate([
              {transform:'translate(0,0) scale(1.08)'},
              {transform:`translate(${destination.x-from.x}px,${destination.y-from.y}px) scale(1)`}
            ],{duration:reduced || data.instant ? 0 : 90,easing:'ease-out',fill:'forwards'}).finished;
          } catch {
            // Cancelling a visual transition must still release pointer state.
          } finally {
            if(!disposed){
              animating=false;
              if(!legal)select(null);
              // Keep the piece at its destination until Python confirms the move.
              if(!pending){movingGhost.remove();ghost=null;button.classList.remove('dragging');}
              setTimeout(()=>{suppressClick=false;},0);
            }
          }
        }
        button.onpointerup=e=>finish(e);
        button.onpointercancel=e=>finish(e,true);
        button.onlostpointercapture=e=>finish(e,true);
        buttons.set(cell.name,button);grid.append(button);
      }
      function paintPosition() {
        for(const cell of data.cells) {
          const button=buttons.get(cell.name),svg=cell.svg || data.pieces?.[cell.piece] || '';
          if(button._pieceSvg!==svg){
            button.querySelectorAll(':scope > svg').forEach(piece=>piece.remove());
            if(svg)button.insertAdjacentHTML('afterbegin',svg);
            button._pieceSvg=svg;
          }
          button.setAttribute('aria-label',cell.label);
          button.classList.toggle('last',data.last.includes(cell.name));
          button.classList.toggle('movable',data.editing ? Boolean(svg) && data.editTool==='move' :
            data.legal.some(move=>move.startsWith(cell.name)));
        }
      }
      function paintTraining() {
        for(const [name,button] of buttons) {
          const feedback=data.trainingFeedback;
          button.classList.toggle('training-correct',feedback?.square===name && feedback.correct===true);
          button.classList.toggle('training-wrong',feedback?.square===name && feedback.correct===false);
        }
        const layer=parentElement.querySelector('.training-hint-layer');layer.replaceChildren();
        const hints=[];
        if(data.trainingHint)hints.push([data.trainingHint,'#399748','training-hint']);
        if(data.trainingFeedback?.correct===false && data.trainingFeedback.uci)hints.push([data.trainingFeedback.uci,'#db2739','training-error-arrow']);
        for(const [move,color,cls] of hints){
          if(!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(move||''))continue;
          const from=data.cells.findIndex(cell=>cell.name===move.slice(0,2));
          const to=data.cells.findIndex(cell=>cell.name===move.slice(2,4));
          if(from<0||to<0||from===to)continue;
          const x=from%8*100+50,y=Math.floor(from/8)*100+50;
          const dx=(to%8-from%8)*100,dy=(Math.floor(to/8)-Math.floor(from/8))*100,length=Math.hypot(dx,dy);
          const arrow=document.createElementNS('http://www.w3.org/2000/svg','polygon');
          arrow.setAttribute('class',cls);
          arrow.setAttribute('points',`0,-5 ${length-25},-5 ${length-25},-17 ${length},0 ${length-25},17 ${length-25},5 0,5`);
          arrow.setAttribute('transform',`translate(${x} ${y}) rotate(${Math.atan2(dy,dx)*180/Math.PI})`);
          arrow.setAttribute('fill',color);arrow.setAttribute('fill-opacity','.9');layer.append(arrow);
        }
      }
      function paintSpecialEffect(enabled) {
        const layer=parentElement.querySelector('.move-effect-layer');
        const key=enabled?JSON.stringify([epoch,data.fen,data.ply,data.badge.square,data.badge.side,data.badge.symbol]):null;
        if(parentElement._specialEffectKey===key)return;
        parentElement._specialEffectKey=key;
        clearTimeout(parentElement._effectTimer);layer.replaceChildren();delete layer.dataset.effect;
        if(!enabled || matchMedia('(prefers-reduced-motion: reduce)').matches)return;
        const index=data.cells.findIndex(cell=>cell.name===data.badge.square);
        const x=index%8*100+50,y=Math.floor(index/8)*100+50;
        const ns='http://www.w3.org/2000/svg';
        function svg(tag,attributes,parent=layer){
          const node=document.createElementNS(ns,tag);
          for(const [name,value] of Object.entries(attributes))node.setAttribute(name,String(value));
          parent.append(node);return node;
        }
        if(data.badge.side==='white'){
          layer.dataset.effect='lightning';
          const start=Math.min(775,Math.max(25,x+65));
          const path=`M ${start} 0 L ${x-32} ${y*.30} L ${x+28} ${y*.43} L ${x-22} ${y*.68} L ${x+12} ${y*.76} L ${x} ${y}`;
          svg('path',{d:path,class:'lightning-bolt lightning-halo'});
          svg('path',{d:path,class:'lightning-bolt lightning-core'});
          svg('circle',{cx:x,cy:y,r:38,class:'impact',stroke:'#35a8ff'});
        } else {
          layer.dataset.effect='meteor';
          const position=svg('g',{transform:`translate(${x} ${y})`});
          const meteor=svg('g',{class:'meteor-flight'},position);
          svg('path',{d:'M -13 8 L 145 -235 L 17 -5 Z',fill:'#ff453a',opacity:'.45'},meteor);
          svg('path',{d:'M -8 4 L 95 -150 L 10 -7 Z',fill:'#ff8d35',opacity:'.85'},meteor);
          svg('circle',{cx:0,cy:0,r:18,fill:'#ff453a'},meteor);
          svg('circle',{cx:-3,cy:-4,r:11,fill:'#ffe6bb'},meteor);
          svg('circle',{cx:x,cy:y,r:42,class:'impact meteor-impact'});
        }
        parentElement._effectTimer=setTimeout(()=>{
          if(parentElement._specialEffectKey===key){layer.replaceChildren();delete layer.dataset.effect;}
        },1500);
      }
      function paintBadge() {
        const special=Boolean(data.analysisEffects && data.badge?.special &&
          ['white','black'].includes(data.badge.side) && data.last.includes(data.badge.square));
        paintSpecialEffect(special);
        const quality=parentElement.querySelector('.move-quality');
        quality.hidden=!data.badge;
        if(data.badge){
          quality.style.background=data.badge.color;quality.style.color=data.badge.ink;
          quality.querySelector('span').textContent=data.badge.symbol;
          quality.querySelector('strong').textContent=data.badge.label;
          quality.title=data.badge.description || data.badge.label;
        }
        for(const [name,button] of buttons) {
          button.querySelector('.quality')?.remove();
          button.classList.toggle('last',data.last.includes(name));
          const aura=special && name===data.badge.square;
          button.classList.toggle('special',aura);
          button.classList.toggle('special-white',aura && data.badge.side==='white');
          button.classList.toggle('special-black',aura && data.badge.side==='black');
          if(data.badge && name===data.badge.square) {
            const badge=document.createElement('span');badge.className='quality';badge.textContent=data.badge.symbol;
            badge.style.background=data.badge.color;badge.style.color=data.badge.ink;
            badge.title=data.badge.label;badge.setAttribute('aria-label',data.badge.label);button.append(badge);
          }
        }
      }
      paintBadge();
      paintTraining();
      if(preservedSelection && !pending)select(preservedSelection);
      if(pending)waitForAck();
      parentElement.querySelector('.workspace').classList.toggle('repertoire',Boolean(data.trainingMode));
      function animatePosition() {
      const animationKey=data.animateMove && !data.instant?JSON.stringify([epoch,data.revision,data.animateMove]):null;
      if(animationKey && parentElement._trainingAnimation!==animationKey){
        parentElement._trainingAnimation=animationKey;
        const move=data.animateMove,from=buttons.get(move.slice(0,2)),to=buttons.get(move.slice(2,4));
        const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
        async function slide(origin,destination){
          const piece=destination?.querySelector(':scope > svg');if(!piece||!origin)return;
          const a=origin.getBoundingClientRect(),b=destination.getBoundingClientRect();
          destination.style.zIndex='2';
          await piece.animate([{transform:`translate(${a.x-b.x}px,${a.y-b.y}px)`},{transform:'translate(0,0)'}],
            {duration:reduced?0:260,easing:'cubic-bezier(.2,.65,.3,1)'}).finished.catch(()=>{});
          destination.style.zIndex='';
        }
        animating=true;
        const slides=[slide(from,to)];
        const symbol=data.cells.find(c=>c.name===move.slice(2,4))?.piece;
        if(symbol?.toLowerCase()==='k' && Math.abs(move.charCodeAt(0)-move.charCodeAt(2))===2){
          const rank=move[1],kingSide=move[2]==='g';
          slides.push(slide(buttons.get((kingSide?'h':'a')+rank),buttons.get((kingSide?'f':'d')+rank)));
        }
        Promise.all(slides).catch(()=>{}).finally(()=>{animating=false;});
      }
      }
      animatePosition();
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
      function externalSync(event) {
        const path=event.composedPath();
        if(path.includes(parentElement) || path.includes(parentElement.host))return;
        // Bubble after the native control handles its click. Flushing during
        // capture or pointerdown can disable that control and swallow its action.
        navigation.flush();
      }
      document.addEventListener('keydown',keyboard);
      document.addEventListener('click',externalSync);
      const detach=()=>{
        document.removeEventListener('keydown',keyboard);
        document.removeEventListener('click',externalSync);
      };
      const cleanup=()=>{disposed=true;detach();clearTimeout(pendingTimer);clearTimeout(parentElement._quizTimer);ghost?.remove();};
      parentElement._acervoState={signature,keyboard,externalSync,detach,cleanup,
        status:()=>({pending,animating,suppressClick,disposed,gridConnected:grid.isConnected,
          connectedButtons:[...buttons.values()].filter(button=>button.isConnected).length,
          revision:data.revision,disabled:data.disabled,legal:data.legal,selected,trainingMode:data.trainingMode,
          click:parentElement._lastTrainingClick,pointer:parentElement._lastTrainingPointer,
          release:parentElement._lastTrainingRelease,emit:parentElement._lastTrainingEmit}),
        update:(next,trigger,stateValue)=>{
        const changedPosition=data.fen!==next.fen || data.ply!==next.ply || data.revision!==next.revision;
        data=next;setTriggerValue=trigger;setStateValue=stateValue;
        if(changedPosition){
          clearArrows();promo.replaceChildren();select(null);pending=false;pendingEvent=null;
          parentElement._trainingPending=null;drag=null;arrowDrag=null;animating=false;suppressClick=false;
          clearTimeout(pendingTimer);
          ghost?.remove();ghost=null;
          for(const button of buttons.values())button.classList.remove('dragging');
        }
        paintPosition();
        // Acknowledged revisions unlock input while retaining all 64 square nodes.
        paintBadge();
        paintTraining();
        paintLesson();
        animatePosition();
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
    def frame(last=None):
        return {'fen': board.fen(), 'legal': ' '.join(move.uci() for move in board.legal_moves)
                if not board.is_game_over() else '',
                'last': [chess.square_name(last.from_square), chess.square_name(last.to_square)] if last else []}
    frames = [frame()]
    for move in game.mainline_moves():
        board.push(move)
        frames.append(frame(move))
    return frames


@lru_cache(maxsize=1)
def piece_images():
    return {symbol: chess.svg.piece(chess.Piece.from_symbol(symbol)) for symbol in 'PNBRQKpnbrqk'}


def quality_badge(category, square, side):
    if category is None or square is None:
        return None
    key = next((key for key, item in CATEGORIES.items() if item == category), None)
    return {'square': square, 'symbol': category.symbol, 'label': category.label,
            'color': category.color, 'ink': category.ink, 'description': category.description,
            'special': key in SPECIAL_CATEGORIES, 'side': side}


def interactive_board(board, *, flip=False, last_move=None, category=None, on_move,
                      ply=0, total=0, on_navigate=None, key="interactive_board", disabled=False, revision=0,
                      pgn=None, epoch=None, navigation_ack=0, explanations=None, study=False, dark=False, reviews=None,
                      mascot=False, table=False, editing=False, edit_tool='move', on_edit=None,
                      expanded=False, analysis_effects=False, hint_move=None, training_feedback=None,
                      training_mode=False, training_expected=None, animate_move=None, show_coordinates=False,
                      on_sync=None, quiz=None, training_line=None, instant=False):
    badge = quality_badge(category, chess.square_name(last_move.to_square) if last_move else None,
                          'black' if board.turn else 'white')
    frames = game_frames(pgn, flip) if pgn is not None else None
    if frames:
        for index, frame in enumerate(frames):
            if disabled:
                frame['legal'] = ''
            review = (reviews or {}).get(index)
            quality = CATEGORIES[canonical_category(review.category)] if review else None
            frame['badge'] = quality_badge(quality, frame['last'][-1] if frame['last'] else None,
                                           'white' if frame['fen'].split()[1] == 'b' else 'black')
    return _BOARD(data={**position_data(board, flip, last_move), "revision": revision,
                        "legal": [] if disabled or board.is_game_over() else [m.uci() for m in board.legal_moves],
                        "last": [chess.square_name(s) for s in (last_move.from_square, last_move.to_square)] if last_move else [],
                        "badge": badge, "ply": ply, "total": total, "navigation": on_navigate is not None,
                        "disabled": disabled,
                        "frames": frames, "pieces": piece_images(), "epoch": epoch, "navigation_ack": navigation_ack,
                        "explanations": explanations, "study": study, "dark": dark, "theme": palette(dark), "mascot": mascot,
                        "table": table, "editing": editing, "editTool": edit_tool,
                        "expanded": expanded, "analysisEffects": analysis_effects,
                        "trainingHint": hint_move, "trainingFeedback": training_feedback,
                        "trainingMode": training_mode, "trainingExpected": training_expected,
                        "quiz": quiz,
                        "trainingLine": training_line, "instant": instant,
                        "syncRecovery": on_sync is not None,
                        "showCoordinates": show_coordinates,
                        "animateMove": animate_move}, key=key,
                  on_move_change=on_move, on_navigate_change=on_navigate or (lambda: None),
                  on_edit_change=on_edit or (lambda: None), on_sync_change=on_sync or (lambda: None))
