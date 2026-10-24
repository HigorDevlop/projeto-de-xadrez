"""Inline Streamlit v2 board; python-chess is the authority on legal moves."""
import chess
import chess.svg
import streamlit as st
from io import StringIO
from functools import lru_cache
import chess.pgn
import re
from chess_review import CATEGORIES, SPECIAL_CATEGORIES, canonical_category
from design_tokens import palette

_BOARD = st.components.v2.component(
    "acervo_interactive_board",
    html='''<div class="workspace"><section><div class="board-floor"><div class="board-stage"><div class="evaluation-bar" hidden role="meter" aria-label="Avaliação da posição" aria-valuemin="0" aria-valuemax="100"><div class="evaluation-white"></div><i class="evaluation-mid"></i><span class="evaluation-top" aria-hidden="true">♚</span><span class="evaluation-bottom" aria-hidden="true">♔</span><span class="evaluation-label"></span></div><div class="board" aria-label="Tabuleiro interativo"></div>
    <svg class="arrows" viewBox="0 0 800 800" aria-hidden="true"></svg>
    <svg class="training-hint-layer" viewBox="0 0 800 800" aria-hidden="true"></svg>
    <svg class="move-effect-layer" viewBox="0 0 800 800" aria-hidden="true"></svg></div><div class="cat-place" aria-hidden="true"></div></div>
    <div class="promotion"></div><nav aria-label="Navegação de lances">
    <button type="button" data-nav="first" aria-label="Posição inicial">⏮</button>
    <button type="button" data-nav="previous" aria-label="Lance anterior">←</button>
    <span class="move-counter" aria-live="polite"></span>
    <button type="button" data-nav="next" aria-label="Próximo lance">→</button>
    <button type="button" data-nav="last" aria-label="Último lance">⏭</button></nav>
    <div class="turn-indicator" role="status" aria-live="polite"><span class="turn-dot" aria-hidden="true"></span><span class="turn-label"></span></div>
    <p class="evaluation-readout" hidden role="status" aria-live="polite"></p>
    <p class="move-quality" role="status" aria-live="polite" hidden><span aria-hidden="true"></span><strong></strong></p></section>
    <aside class="analysis-notes" hidden aria-label="Anotações da partida"><header><div><small>SUA PARTIDA</small><h3>Lances e anotações</h3></div><button type="button" class="notes-start">Início</button></header><div class="analysis-panel-tabs" role="tablist" aria-label="Painel de estudo"><button type="button" class="notes-tab" role="tab" aria-selected="true">Anotações</button><button type="button" class="notebook-tab" role="tab" aria-selected="false" hidden>Caderno</button></div><div class="notes-pane"><div class="notes-colours"><span></span><span>Brancas</span><span>Pretas</span></div><div class="notes-list" tabindex="0"></div><footer class="notes-comment"></footer></div><div class="notebook-pane" hidden><div class="notebook-saved" hidden><select aria-label="Cadernos salvos"></select><button type="button" class="notebook-resume">Retomar partida anotada</button></div><div class="notebook-modes"><button type="button" data-note-mode="position">Posição atual</button><button type="button" data-note-mode="general">Resumo</button></div><small class="notebook-position"></small><label class="notebook-label" for="study-notebook-text">Pontos importantes do estudo</label><textarea id="study-notebook-text" class="notebook-editor" aria-label="Pontos importantes do estudo" placeholder="Ideias, planos e pontos importantes..." spellcheck="true" lang="pt-BR" maxlength="20000"></textarea><div class="notebook-actions"><button type="button" class="notebook-save">Salvar anotação</button><button type="button" class="notebook-download">Baixar caderno</button></div><small class="notebook-status" role="status" aria-live="polite"></small><details class="notebook-history"><summary>Pontos anotados</summary><div></div></details></div></aside>
    <aside class="lesson" hidden><h3>Estudo com Bobby Fischer</h3>
    <p class="lesson-text" aria-live="polite"></p><small>Explicações preparadas para toda a partida.</small></aside></div>''',
    css="""
    .workspace {display:grid;grid-template-columns:minmax(0,1fr);gap:24px;color:var(--ink);font-family:'Segoe UI',system-ui,sans-serif}
    .workspace.split {grid-template-columns:minmax(0,1fr)}
    .workspace.with-notes{grid-template-columns:minmax(0,1.9fr) minmax(245px,1fr);align-items:start;max-width:1180px;margin:auto;gap:22px}
    .analysis-notes[hidden]{display:none}
    .notes-clock{display:block;padding:0 10px 7px;font:500 11px/1.4 system-ui;color:#aaa69d;font-variant-numeric:tabular-nums}
    .analysis-notes{box-sizing:border-box;height:var(--analysis-board-height,60vh);min-height:0;margin-top:8px;display:flex;flex-direction:column;overflow:hidden;border:1px solid #3c3a35;border-radius:16px;background:linear-gradient(145deg,#242320,#171716);box-shadow:inset 0 1px #ffffff08,0 12px 30px #0003}
    .analysis-notes header{display:flex;justify-content:space-between;align-items:center;padding:18px 16px 14px;gap:8px}.analysis-notes h3{margin:4px 0 0;font:600 17px/1.3 system-ui;color:#f1eee7}.analysis-notes header small{font:600 9px system-ui;letter-spacing:2px;color:#b99a69}
    .analysis-notes button{font:500 14px/1.4 system-ui;cursor:pointer;color:#eee;background:transparent;border:1px solid transparent;border-radius:8px;padding:9px 10px;text-align:left}.analysis-notes button:focus-visible{outline:2px solid #e3ad5e;outline-offset:-2px}.analysis-notes button:hover{background:#ffffff09}.analysis-notes .notes-start{font-size:11px;border-color:#49443b;color:#cbbc9f}
    .notes-colours,.notes-row{display:grid;grid-template-columns:28px minmax(0,1fr) minmax(0,1fr);gap:5px;align-items:start}.notes-colours{padding:8px 14px;font:11px system-ui;color:#8f8b83;border-block:1px solid #ffffff0a}.notes-list{overflow:auto;min-height:0;flex:1;padding:8px;scrollbar-width:thin;scrollbar-color:#514536 transparent}.notes-row{border-radius:8px;padding:2px 0}.notes-row:nth-child(even){background:#ffffff03}.notes-number{font:11px/38px system-ui;color:#77746e;text-align:center}.notes-move{min-width:0}.notes-move button{width:100%;display:flex;align-items:center;justify-content:space-between;gap:5px}.notes-move button[aria-current=true]{background:#a46c252b;border-color:#ac793c;color:#ffe0a9}.notes-quality{font-size:11px;font-weight:750;color:var(--note-quality,#cfa96c)}.notes-inline-comment{font:11px/1.5 system-ui;color:#a4a097;padding:0 10px 8px;overflow-wrap:anywhere}.notes-comment{border-top:1px solid #ffffff0c;padding:12px 16px;font:12px/1.55 system-ui;color:#aaa69d;max-height:100px;overflow:auto}.notes-empty{padding:24px 10px;font:13px/1.6 system-ui;color:#99968d}
    @media(max-width:760px){.workspace.with-notes{grid-template-columns:minmax(0,1fr);gap:12px}.analysis-notes{margin:0;height:300px!important;max-height:45vh}}

    .analysis-panel-tabs{display:flex;gap:5px;padding:0 12px 11px;border-bottom:1px solid #ffffff0d}.analysis-panel-tabs button{flex:1;text-align:center;font-size:12px;border:1px solid #ffffff0d;background:#ffffff03}.analysis-panel-tabs button[aria-selected=true]{color:#f2d59c;border-color:#b3975c77;background:linear-gradient(140deg,#49402a,#2d3023);box-shadow:inset 0 1px #ffffff11,0 3px 7px #0003}.analysis-panel-tabs [hidden]{display:none}
    .notes-pane{display:flex;flex-direction:column;flex:1;min-height:0}.notes-pane[hidden],.notebook-pane[hidden]{display:none}.notebook-pane{display:flex;flex-direction:column;gap:9px;flex:1;min-height:0;padding:14px}.notebook-modes{display:flex;gap:4px}.notebook-modes button{font-size:10px;padding:6px 8px;color:#a9ae9d}.notebook-modes button.active{background:#bda46b22;border-color:#bda46b55;color:#e5d1a2}.notebook-position{font:10px system-ui;color:#aaa791}.notebook-label{font:11px system-ui;color:#c5c7b8}.notebook-editor{box-sizing:border-box;width:100%;min-height:100px;flex:1;resize:none;border:1px solid #91846535;border-left:3px solid #a9785e66;border-radius:9px;padding:12px 12px 12px 16px;font:14px/28px system-ui;color:#e4e5d4;outline:none;background-color:#1a211b;background-image:repeating-linear-gradient(to bottom,transparent 0,transparent 27px,#bca77826 27px,#bca77826 28px);background-origin:content-box;background-clip:padding-box;box-shadow:inset 0 2px 12px #0003}.notebook-editor:focus{border-color:#bba36d}.notebook-editor::placeholder{color:#727f6d}.notebook-actions{display:flex;gap:5px}.notebook-actions button{font-size:11px;padding:8px}.notebook-actions .notebook-save{background:linear-gradient(135deg,#c9a768,#aa8b54);color:#182018;font-weight:650;box-shadow:inset 0 1px #ffffff25,0 3px 7px #0003}.notebook-status{font:10px/1.5 system-ui;color:#9dbc94;min-height:15px}.notebook-history{font:11px system-ui;color:#bbb9a8;max-height:105px;overflow:auto;border-top:1px solid #ffffff0a;padding-top:8px}.notebook-history summary{cursor:pointer}.notebook-history p{white-space:pre-wrap;font:11px/1.6 system-ui;color:#a7ae9b}.notebook-saved{display:flex;gap:6px;flex-wrap:wrap}.notebook-saved[hidden]{display:none}.notebook-saved select{box-sizing:border-box;max-width:100%;min-width:0;width:100%;border:1px solid #64624b55;border-radius:7px;background:#20251c;color:#bfcaaf;font:10px system-ui;padding:6px}.notebook-saved button{font-size:10px;padding:5px 0;color:#cdb787}
    .workspace.with-evaluation .board-stage{max-width:calc(100% - 44px);left:22px}.evaluation-bar{width:32px;border:1px solid #756d5a55;background:linear-gradient(90deg,#242a30,#343a41);border-radius:10px;box-shadow:inset 0 1px #ffffff15,0 6px 16px #0006}.evaluation-white{background:linear-gradient(90deg,#d3cdbf,#f4f0e5);box-shadow:inset 2px 0 #ffffff55}.evaluation-mid{position:absolute;top:50%;width:100%;border-top:1px dashed #b39f7766}.evaluation-label,.evaluation-bar.negative .evaluation-label,.evaluation-bar.flipped .evaluation-label,.evaluation-bar.flipped.negative .evaluation-label{position:absolute;writing-mode:horizontal-tb;top:calc(50% - 12px);bottom:auto;left:1px;right:1px;border-radius:5px;background:#18201dd9;padding:6px 0;color:#f2e4c7;font:650 10px/1 system-ui;box-shadow:0 2px 7px #0006}.evaluation-top,.evaluation-bottom{position:absolute;left:0;right:0;text-align:center;font:20px/1 Georgia;top:8px;color:#d4d0c5;text-shadow:0 1px #0008}.evaluation-bottom{top:auto;bottom:8px;color:#3b3b31}.evaluation-bar.flipped .evaluation-top{color:#3b3b31}.evaluation-bar.flipped .evaluation-bottom{color:#d4d0c5}.evaluation-readout{margin:8px auto 0;text-align:center;font:11px/1.6 system-ui;color:#beb8a4;max-width:95%;padding:5px 12px;border-radius:9px;background:#b29d6a0b}.evaluation-readout[hidden]{display:none}
    @media(max-width:760px){.analysis-notes.notebook-open{height:480px!important;max-height:75vh;min-height:350px}}

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
    .evaluation-bar[hidden]{display:none}
    .evaluation-bar{position:absolute;right:calc(100% + 8px);top:0;bottom:0;overflow:hidden}
    .evaluation-white{position:absolute;bottom:0;width:100%;height:50%;transition:height .2s ease-out}
    .evaluation-bar.flipped .evaluation-white{bottom:auto;top:0}
    .evaluation-bar.unknown{background:repeating-linear-gradient(135deg,#353535 0 6px,#292929 6px 12px)}
    .evaluation-bar.unknown .evaluation-white{opacity:.25}.evaluation-bar.unknown .evaluation-label{color:#eee}
    .workspace.table .board-stage {max-width:calc(100% - 52px)}
    .workspace.expanded section {display:grid;grid-template-columns:minmax(0,1fr)}
    .workspace.expanded .board-floor {display:contents}
    .workspace.expanded .board-stage {grid-row:1;width:min(100%,72vh,840px);margin:8px auto}
    .workspace.expanded nav {grid-row:2}
    .workspace.expanded .turn-indicator {grid-row:3}
    .workspace.aligned .board-floor{padding:0}
    .workspace.aligned .board-stage{width:var(--study-board-size,min(100%,calc(100dvh - 250px)));max-width:100%;margin:0 auto}
    .workspace.aligned .board-stage:before{display:none}
    .workspace.expanded .promotion {grid-row:4}
    .workspace.expanded .move-quality {grid-row:5}
    .workspace.expanded .cat-place {grid-row:6;position:relative;left:auto;bottom:auto;justify-self:end;
      width:min(100%,84vh,980px);margin:24px 0 0}
    .workspace.editing .square {cursor:var(--club-cursor-crosshair,crosshair)}
    .turn-indicator{display:flex;align-items:center;gap:8px;width:fit-content;margin:8px auto 0;padding:7px 12px;background:var(--surface,#191919);border:1px solid var(--border,#343434);border-radius:999px;font:600 12px/1.3 'Segoe UI',sans-serif;color:var(--ink,#f5f5f5)}
    .turn-dot{width:10px;height:10px;border-radius:50%;background:#f4f0e5;border:1px solid #b8b6ae;box-shadow:0 1px 3px #0004}
    .turn-indicator[data-side="b"] .turn-dot{background:#242424;border-color:#949494}
    .arrows,.training-hint-layer {position:absolute;inset:4px;width:calc(100% - 8px);height:calc(100% - 8px);pointer-events:none;z-index:3}
    .board {display:grid;grid-template-columns:repeat(8,1fr);width:100%;margin:auto;scroll-margin-top:80px;
      aspect-ratio:1; border:4px solid #344D3D;border-radius:5px;overflow:hidden;box-sizing:border-box}
    .square {position:relative; padding:0;border:0;border-radius:0;aspect-ratio:1;
      min-width:0;cursor:var(--club-cursor-link,pointer);touch-action:none;user-select:none}
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
    .quality {position:absolute;right:2px;top:2px;min-width:28px;height:28px;display:flex;align-items:center;justify-content:center;
      padding:0 5px;box-sizing:border-box;border:2px solid #fff;border-radius:8px;font:800 15px/1 'Segoe UI',system-ui,sans-serif;
      box-shadow:0 1px 5px #10251955;pointer-events:none;z-index:5}
    .move-quality {display:flex;align-items:center;justify-content:center;gap:9px;width:fit-content;max-width:100%;
      margin:14px auto 0;padding:7px 14px;border-radius:8px;border:1px solid #ffffff88;
      font:600 14px/1.4 'Segoe UI',system-ui,sans-serif;box-sizing:border-box}
    .move-quality span {font-size:21px;font-weight:800}.move-quality[hidden] {display:none}
    .status {font:13px var(--st-font);color:var(--st-text-color);margin:8px 0}
    .promotion button {padding:8px 16px;margin:4px;border-radius:5px;cursor:var(--club-cursor-link,pointer)}
    nav {display:flex;align-items:center;justify-content:center;gap:8px;width:fit-content;max-width:100%;margin:12px auto 0;
      background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:6px;box-sizing:border-box}
    nav[hidden],.lesson[hidden] {display:none}
    nav button,.promotion button {background:var(--surface);color:var(--ink);border:1px solid transparent;border-radius:9px;
      min-width:42px;min-height:42px;font-size:18px;cursor:var(--club-cursor-link,pointer);transition:background .15s,border-color .15s}
    nav button:hover:not(:disabled) {background:var(--soft);border-color:var(--border)}
    nav button:focus-visible,.promotion button:focus-visible {outline:3px solid var(--accent);outline-offset:2px}
    @media(prefers-reduced-motion:reduce){
      .workspace *,.workspace *:before,.workspace *:after{animation:none!important;transition:none!important}
    }
    nav button:disabled {opacity:.4;cursor:var(--club-cursor-default,default)}
    .move-counter {font:600 13px 'Segoe UI',system-ui,sans-serif;min-width:100px;text-align:center;font-variant-numeric:tabular-nums;color:var(--muted)}
    @media(max-width:400px) {nav{gap:4px;padding:5px}nav button{min-width:36px;min-height:40px}.move-counter{min-width:84px;font-size:12px}}
    .lesson {background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:14px;padding:24px;
      width:min(100%,760px);box-sizing:border-box;justify-self:center;align-self:start}
    .lesson h3 {font:400 25px/1.3 Georgia,serif;margin-top:0}
    .lesson-text {font:18px/1.8 Georgia,serif;white-space:pre-wrap;overflow-wrap:anywhere}
    .lesson small {font:13px/1.6 'Segoe UI',system-ui,sans-serif;color:var(--muted)}
    @media(max-width:700px) {.workspace.split {grid-template-columns:1fr}.lesson {padding:16px}}
    .square.movable {cursor:var(--club-cursor-grab,grab)}.square.dragging {cursor:var(--club-cursor-grabbing,grabbing)}
    .workspace.editing[data-edit-tool="move"] .square.movable {cursor:var(--club-cursor-grab,grab)}
    .board:has(.dragging) .square {cursor:var(--club-cursor-grabbing,grabbing)!important}
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
      parentElement.querySelector('.board').dataset.fen=data.fen;
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
        {surface:'#121212',ink:'#f5f5f5',muted:'#a3a3a3',border:'#2b2b2b',soft:'#1d1d1d',accent:'#ff8000'} :
        {surface:'#FFFEFA',ink:'#202B26',muted:'#626F66',border:'#D9DED5',soft:'#ECEFE8',accent:'#176B4A'});
      for(const [token,value] of Object.entries(theme))
        (parentElement.host ?? parentElement).style.setProperty('--'+token.replaceAll('_','-'),value);
      function paintTurn() {
        const side=data.editing && data.turnOverride ? data.turnOverride : data.fen.split(' ')[1];
        const indicator=parentElement.querySelector('.turn-indicator');
        indicator.dataset.side=side;
        indicator.querySelector('.turn-label').textContent=side==='b'?'Pretas jogam':'Brancas jogam';
      }
      function paintLesson() {
        paintTurn();
        paintEvaluation();
        paintNotes();
        const lesson=parentElement.querySelector('.lesson');
        const ready=Boolean(data.study && data.explanations);
        parentElement.querySelector('.workspace').classList.toggle('split',Boolean(data.study));
        parentElement.querySelector('.workspace').classList.toggle('mascot',Boolean(data.mascot));
        parentElement.querySelector('.workspace').classList.toggle('table',Boolean(data.table));
        parentElement.querySelector('.workspace').classList.toggle('expanded',Boolean(data.expanded));
        parentElement.querySelector('.workspace').classList.toggle('aligned',Boolean(data.aligned));
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
      function paintEvaluation(){
        const bar=parentElement.querySelector('.evaluation-bar'),score=data.evaluation;
        const visible=Boolean(data.evaluationBar && !data.editing);
        bar.hidden=!visible;parentElement.querySelector('.workspace').classList.toggle('with-evaluation',visible);
        const readout=parentElement.querySelector('.evaluation-readout');readout.hidden=!visible;
        const known=score && (Number.isFinite(score.cp) || Number.isFinite(score.mate));
        const mate=known && Number.isFinite(score.mate);
        const value=mate ? (score.mate===0 ? (data.fen.split(' ')[1]==='b'?1:-1) : Math.sign(score.mate))*10000 : known?score.cp:0;
        const percent=known?50+49*Math.tanh(value/400):50;
        const label=!known?'—':mate?'M'+Math.abs(score.mate):(score.cp>0?'+':'')+(score.cp/100).toFixed(2).replace('.',',');
        const description=!known?'Sem avaliação. Clique em Analisar Partida.':mate?`Mate ${Math.abs(score.mate)} · ${value>0?'brancas':'pretas'}`:value===0?'Posição equilibrada':`Vantagem das ${value>0?'brancas':'pretas'}: ${Math.abs(score.cp/100).toFixed(2)} peões`;
        bar.classList.toggle('unknown',!known);bar.classList.toggle('negative',value<0);bar.classList.toggle('flipped',Boolean(data.flip));
        bar.querySelector('.evaluation-white').style.height=percent+'%';
        bar.querySelector('.evaluation-label').textContent=label;
        readout.textContent=!known?'Sem avaliação · clique em Analisar Partida':description+(mate?'':' · valores em peões, pelo lado das brancas');
        bar.querySelector('.evaluation-top').textContent=data.flip?'♔':'♚';bar.querySelector('.evaluation-bottom').textContent=data.flip?'♚':'♔';
        bar.title=description;bar.setAttribute('aria-valuenow',String(Math.round(percent)));bar.setAttribute('aria-valuetext',description);
      }
      function paintNotes() {
        const root=parentElement.querySelector('.workspace'),panel=parentElement.querySelector('.analysis-notes');
        const enabled=Boolean(data.analysisNotes && !data.editing);
        panel.hidden=!enabled;root.classList.toggle('with-notes',enabled);
        if(!enabled){parentElement._notesObserver?.disconnect();parentElement._notesObserver=null;return;}
        if(!parentElement._notesObserver){
          parentElement._notesObserver=new ResizeObserver(entries=>root.style.setProperty('--analysis-board-height',entries[0].target.getBoundingClientRect().height+'px'));
          parentElement._notesObserver.observe(parentElement.querySelector('.board'));
        }
        paintNotebook();
        const list=panel.querySelector('.notes-list'),oldScroll=list.scrollTop;list.replaceChildren();
        panel.querySelector('.notes-start').onclick=()=>navigate(0);
        const rows=new Map();
        for(const note of data.analysisNotes){
          let row=rows.get(note.number);
          if(!row){row=document.createElement('div');row.className='notes-row';const number=document.createElement('span');number.className='notes-number';number.textContent=note.number+'.';row.append(number,document.createElement('div'),document.createElement('div'));rows.set(note.number,row);list.append(row);}
          const cell=row.children[note.side==='white'?1:2];cell.className='notes-move';
          const button=document.createElement('button');button.type='button';button.dataset.ply=note.ply;button.setAttribute('aria-current',String(note.ply===data.ply));button.setAttribute('aria-label',`${note.number}${note.side==='white'?'.':'...'} ${note.san}`);button.textContent=note.san;button.onclick=()=>navigate(note.ply);
          if(note.symbol){const quality=document.createElement('span');quality.className='notes-quality';quality.textContent=note.symbol;quality.style.setProperty('--note-quality',note.color);quality.title=note.quality;button.append(quality);}
          cell.append(button);
          if(note.clock){const clock=document.createElement('small');clock.className='notes-clock';clock.textContent='◷ '+note.clock;clock.title='Tempo restante';cell.append(clock);}
          if(note.comment){const comment=document.createElement('p');comment.className='notes-inline-comment';comment.textContent=note.comment;cell.append(comment);}
        }
        if(!data.analysisNotes.length){const empty=document.createElement('p');empty.className='notes-empty';empty.textContent='Faça seu primeiro lance ou importe uma partida. As anotações aparecem aqui.';list.append(empty);}
        list.scrollTop=oldScroll;
        const selected=list.querySelector('[aria-current=true]');
        if(selected){const item=selected.parentElement.parentElement;const y=item.offsetTop-list.offsetTop;if(y<list.scrollTop || y+item.offsetHeight>list.scrollTop+list.clientHeight)list.scrollTop=Math.max(0,y-list.clientHeight/2);}
        const current=data.analysisNotes.find(note=>note.ply===data.ply);
        panel.querySelector('.notes-comment').textContent=current?.comment || (current?.quality ? current.quality+' · '+current.san : 'Clique em um lance para acompanhar a posição.');
      }
      function paintNotebook(){
        const panel=parentElement.querySelector('.analysis-notes'),book=data.notebook;
        const tab=panel.querySelector('.notebook-tab');tab.hidden=!book;
        const open=Boolean(book&&parentElement._analysisPane==='notebook');
        panel.classList.toggle('notebook-open',open);panel.querySelector('.notes-pane').hidden=open;panel.querySelector('.notebook-pane').hidden=!open;
        panel.querySelector('.notes-tab').setAttribute('aria-selected',String(!open));tab.setAttribute('aria-selected',String(open));
        panel.querySelector('.notes-tab').onclick=()=>{parentElement._analysisPane='notes';paintNotebook();};tab.onclick=()=>{parentElement._analysisPane='notebook';paintNotebook();};
        if(!book)return;
        const mode=parentElement._notebookMode||'position',position=mode==='general'?'general':data.fen.split(' ').slice(0,4).join(' ');
        const key=book.owner+'|'+book.id+'|'+position,drafts=parentElement._notebookDrafts ||= new Map();
        const entry=book.entries.find(row=>row.position===position),editor=panel.querySelector('.notebook-editor');
        editor.value=drafts.has(key)?drafts.get(key):(entry?.body||'');editor.oninput=()=>{drafts.set(key,editor.value);panel.querySelector('.notebook-status').textContent='Alterações ainda não salvas';};
        const note=data.analysisNotes?.find(row=>row.ply===data.ply),label=note?`${note.number}${note.side==='white'?'.':'...'} ${note.san}`:'Posição inicial';
        panel.querySelector('.notebook-position').textContent=mode==='general'?'Resumo da partida · privado':label+' · notas da posição';
        for(const button of panel.querySelectorAll('[data-note-mode]')){button.classList.toggle('active',button.dataset.noteMode===mode);button.onclick=()=>{parentElement._notebookMode=button.dataset.noteMode;paintNotebook();};}
        panel.querySelector('.notebook-save').onclick=()=>{
          const nonce=Date.now()+':'+Math.random().toString(36).slice(2);parentElement._notePending=nonce;drafts.set(key,editor.value);
          panel.querySelector('.notebook-status').textContent='Salvando...';
          setStateValue('note',{action:'save',nonce,id:book.id,fen:data.fen,mode,label,body:editor.value});
        };
        const status=panel.querySelector('.notebook-status');
        if(book.ack&&book.ack===parentElement._notePending){status.textContent=book.status;parentElement._notePending=null;}
        const history=panel.querySelector('.notebook-history');history.querySelector('summary').textContent='Pontos anotados · '+book.entries.length;
        const list=history.querySelector('div');list.replaceChildren();
        for(const row of book.entries){const title=document.createElement('strong'),body=document.createElement('p');title.textContent=row.title;body.textContent=row.body;list.append(title,body);}
        const saved=panel.querySelector('.notebook-saved'),select=saved.querySelector('select');saved.hidden=!book.games.length;
        const selected=select.value;select.replaceChildren();
        for(const game of book.games){const option=document.createElement('option');option.value=game.id;option.textContent=game.title;select.append(option);}
        if(book.games.some(game=>game.id===selected))select.value=selected;
        saved.querySelector('button').onclick=()=>setStateValue('note',{action:'resume',nonce:Date.now()+':resume',id:select.value});
        panel.querySelector('.notebook-download').onclick=()=>{
          const text='# Caderno de estudo\\n\\n'+book.entries.map(row=>'## '+row.title+'\\n'+row.body+(row.fen?'\\nFEN: '+row.fen:'')).join('\\n\\n');
          const link=document.createElement('a'),url=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));link.href=url;link.download='caderno-de-estudo.md';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        };
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
            navigation_ack:data.navigation_ack ?? 0},parentElement,setTriggerValue,setStateValue});
        }
        clearTimeout(navigation.timer);
        // Send only the final position after a pause, not a rerun for every arrow.
        if(data.frames)navigation.timer=setTimeout(navigation.flush,360);
        else navigation.flush(); // A board without a PGN must ask Python for its next position.
      }
      // Engine/tutor updates must not replace squares during a drag.
      const signature=JSON.stringify([data.stableBoard ? null : data.trainingMode ? data.epoch : epoch,data.cells.map(c=>c.name),
        data.trainingMode || data.stableBoard ? null : data.revision,data.trainingMode ? null : data.disabled,
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
        for(const button of grid.querySelectorAll('.square')){
          const rect=button.getBoundingClientRect();
          if(e.clientX>=rect.left && e.clientX<rect.right && e.clientY>=rect.top && e.clientY<rect.bottom)return button.dataset.square;
        }
        return null;
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
      let pendingEvent=data.trainingMode ? parentElement._trainingPending : data.editing ? parentElement._editPending : null;
      if(pendingEvent && (pendingEvent.revision!==data.revision || pendingEvent.fen!==data.fen)){
        pendingEvent=null;parentElement._trainingPending=null;parentElement._editPending=null;
      }
      let selected=null, pending=Boolean(pendingEvent), drag=null, ghost=null, animating=false, suppressClick=false, disposed=false;
      let interaction=0;
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
        // A new branch supersedes the delayed navigation notification.
        clearTimeout(navigation.timer);
        navigation.timer=null;
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
        // Preview only server-validated legal successors; retain the original
        // event FEN/revision and lock further input until acknowledgement.
        const tactical=data.trainingPreview;
        const prepared=tactical?.sourceFen===data.fen && tactical.expected===uci ? tactical.position : null;
        const preview=data.previewFen===data.fen ? data.movePreviews?.[uci] : null;
        if(prepared || preview){
          const dragged=Boolean(ghost);
          data={...data,...resolveFrame(prepared || {fen:preview,legal:[],last:[uci.slice(0,2),uci.slice(2,4)]}),badge:null,evaluation:null};
          ghost?.remove();ghost=null;
          for(const button of buttons.values())button.classList.remove('dragging');
          select(null);paintPosition(dragged?uci:null);paintBadge();paintEvaluation();paintTurn();
        }
        parentElement._lastTrainingEmit=pendingEvent;
        if((data.quiz || data.trainingLine) && data.syncRecovery){
          const attempts=parentElement._quizAttempts ||= [];
          attempts.push(pendingEvent);
          const source=data, quiz=data.quiz, correct=uci===data.trainingExpected;
          let next=null;
          if(quiz){
          const queue=[...quiz.queue], retry=[], states={...quiz.states}, answered=queue.shift();
          const previous=states[String(answered)] || 'pending';
          states[String(answered)]=!correct?'wrong':quiz.assisted?(previous==='wrong'?'wrong':'unknown'):previous==='wrong'?'unknown':'correct';
          if(states[String(answered)]!=='correct'){
            let hash=2166136261;
            const seed=String(data.revision).split(':')[0]+'|'+revisionNumber(data.revision)+'|'+answered;
            for(const character of seed)hash=Math.imul(hash^character.charCodeAt(0),16777619)>>>0;
            queue.splice(queue.length?1+hash%queue.length:0,0,answered);
          }
          const frame=quiz.positions[String(queue[0])];
          if(frame){
            next={...data,...frame,trainingFeedback:null,trainingHint:null,animateMove:null,
              revision:String(data.revision).split(':')[0]+':'+(revisionNumber(data.revision)+2),
              quiz:{...quiz,queue,retry,states,assisted:false}};
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
      function emitEdit(event) {
        if(pending)return false;
        pending=true;clearArrows();
        pendingEvent={...event,revision:data.revision,fen:data.fen};
        if(data.syncRecovery){
          parentElement._editPending=pendingEvent;
          if(setStateValue)setStateValue('edit',pendingEvent);
          else setTriggerValue('edit',pendingEvent);
        } else setTriggerValue('edit',pendingEvent);
        waitForAck();
        return true;
      }
      function attempt(from,to) {
        if(data.editing){
          return emitEdit({from,to});
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
        const movable=()=>data.editing ? Boolean(cellSvg()) : data.legal.some(m=>m.startsWith(cell.name));
        button.draggable=false;
        button.classList.toggle('movable',movable());
        button.onclick=()=>{
          parentElement._lastTrainingClick={square:cell.name,revision:data.revision,selected,pending,animating,suppressClick};
          if(suppressClick){suppressClick=false;return;}
          if(!data.editing){
            if(pending || animating || data.disabled)return;
            if(selected && selected!==cell.name){
              if(attempt(selected,cell.name)){select(null);return;}
            }
            select(movable()?cell.name:null);return;
          }
          if(data.editing && data.editTool!=='move' && !pending){
            emitEdit({to:cell.name,piece:data.editTool==='erase'?'':data.editTool});
          } else if(data.editing && data.editTool==='move'){
            if(selected && selected!==cell.name){attempt(selected,cell.name);select(null);}
            else select(cellSvg()?cell.name:null);
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
          interaction++;
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
            // Keep the overlay in viewport coordinates, outside component zoom
            // and transformed Streamlit containers.
            Object.assign(ghost.style,{position:'fixed',pointerEvents:'none',zIndex:'99999',filter:'drop-shadow(0 5px 5px #0005)'});
            const image=ghost.querySelector('svg');if(image){image.style.width='100%';image.style.height='100%';}
            document.body.append(ghost);button.classList.add('dragging');
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
          const releasedInteraction=interaction;
          if(button.hasPointerCapture(e.pointerId))button.releasePointerCapture(e.pointerId);
          if(!released.moved)return;
          if(disposed || !ghost){animating=false;suppressClick=false;return;}
          suppressClick=true;animating=true;
          const to=cancel?null:squareAt(e);
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
            ],{duration:reduced ? 0 : 110,easing:'ease-out',fill:'forwards'}).finished;
          } catch {
            // Cancelling a visual transition must still release pointer state.
          } finally {
            if(!disposed && interaction===releasedInteraction){
              animating=false;
              if(!legal)select(null);
              // Keep the piece at its destination until Python confirms the move.
              if(!pending){movingGhost.remove();if(ghost===movingGhost)ghost=null;button.classList.remove('dragging');}
              setTimeout(()=>{suppressClick=false;},0);
            } else movingGhost.remove();
          }
        }
        button.onpointerup=e=>finish(e);
        button.onpointercancel=e=>finish(e,true);
        button.onlostpointercapture=e=>finish(e,true);
        buttons.set(cell.name,button);grid.append(button);
      }
      function paintPosition(skipMove=null) {
        paintTurn();
        grid.dataset.fen=data.fen;
        const previous=[...buttons.values()].map(button=>({button,svg:button._pieceSvg}));
        for(const cell of data.cells) {
          const button=buttons.get(cell.name),svg=cell.svg || data.pieces?.[cell.piece] || '';
          if(button._pieceSvg!==svg){
            const sources=previous.filter(item=>item.svg===svg && item.button!==button &&
              item.svg!==(data.cells.find(c=>c.name===item.button.dataset.square)?.svg || data.pieces?.[data.cells.find(c=>c.name===item.button.dataset.square)?.piece] || ''));
            button.querySelectorAll(':scope > svg').forEach(piece=>piece.remove());
            if(svg)button.insertAdjacentHTML('afterbegin',svg);
            const alreadyDragged=skipMove && sources.length===1 && sources[0].button.dataset.square===skipMove.slice(0,2) && cell.name===skipMove.slice(2,4);
            if(svg && sources.length===1 && !alreadyDragged && !ghost && !data.animateMove && !matchMedia('(prefers-reduced-motion: reduce)').matches){
              const a=sources[0].button.getBoundingClientRect(),b=button.getBoundingClientRect();
              const piece=button.querySelector(':scope > svg');button.style.zIndex='2';
              piece?.animate([{transform:`translate(${a.x-b.x}px,${a.y-b.y}px)`},{transform:'translate(0,0)'}],{duration:160,easing:'cubic-bezier(.2,.65,.3,1)'}).finished.catch(()=>{}).finally(()=>{if(button.querySelector(':scope > svg')===piece)button.style.zIndex='';});
            }
            button._pieceSvg=svg;
          }
          button.setAttribute('aria-label',cell.label);
          button.classList.toggle('last',data.last.includes(cell.name));
          button.classList.toggle('movable',data.editing ? Boolean(svg) :
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
        if(!data.navigation || event.defaultPrevented)return;
        const workspace=(parentElement.host ?? parentElement).closest('.st-key-reading_workspace');
        if(workspace && workspace.dataset.keyboardArea!=='board')return;
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
        // Stable study boards retain their handlers across server revisions.
        // Those handlers must use the current navigation epoch as well.
        navigation=parentElement._navigation ?? navigation;
        const changedPosition=data.fen!==next.fen || data.ply!==next.ply || data.revision!==next.revision;
        data=next;setTriggerValue=trigger;setStateValue=stateValue;
        if(changedPosition){
          interaction++;
          clearArrows();promo.replaceChildren();select(null);pending=false;pendingEvent=null;
          parentElement._trainingPending=null;parentElement._editPending=null;drag=null;arrowDrag=null;animating=false;suppressClick=false;
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
            "legal": [m.uci() for m in board.legal_moves],
            "last": [chess.square_name(s) for s in (last_move.from_square, last_move.to_square)] if last_move else []}


@st.cache_data(max_entries=8, show_spinner=False)
def game_frames(pgn, flip=False):
    game = chess.pgn.read_game(StringIO(pgn)) or chess.pgn.Game()
    board = game.board()
    def frame(last=None):
        return {'fen': board.fen(), 'legal': ' '.join(move.uci() for move in board.legal_moves),
                'last': [chess.square_name(last.from_square), chess.square_name(last.to_square)] if last else []}
    frames = [frame()]
    for move in game.mainline_moves():
        board.push(move)
        frames.append(frame(move))
    return frames


@lru_cache(maxsize=1)
def piece_images():
    return {symbol: chess.svg.piece(chess.Piece.from_symbol(symbol)) for symbol in 'PNBRQKpnbrqk'}


def annotation_rows(pgn, reviews=None):
    """Keep recorded PGN comments beside their own move, including black starts."""
    if not pgn:
        return []
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return []
    board, rows = game.board(), []
    for ply, node in enumerate(game.mainline(), 1):
        review = (reviews or {}).get(ply)
        category = CATEGORIES.get(canonical_category(review.category)) if review else None
        nags = {1:'!', 2:'?', 3:'!!', 4:'??', 5:'!?', 6:'?!'}
        nag = next((nags[value] for value in sorted(node.nags) if value in nags), '')
        clock=node.clock()
        seconds=max(0,round(clock)) if clock is not None else None
        clock_text=(f'{seconds//3600}:{seconds//60%60:02d}:{seconds%60:02d}' if seconds>=3600 else f'{seconds//60}:{seconds%60:02d}') if seconds is not None else ''
        comment=re.sub(r'\[\%[^\]]*\]', '', node.comment).strip()
        rows.append(dict(ply=ply, number=board.fullmove_number, side='white' if board.turn else 'black',
                         san=board.san(node.move), comment=comment, clock=clock_text,
                         symbol=category.symbol if category else nag, quality=category.label if category else 'Anotação do PGN' if nag else '',
                         color=category.color if category else ''))
        board.push(node.move)
    return rows


def quality_badge(category, square, side):
    if category is None or square is None:
        return None
    key = next((key for key, item in CATEGORIES.items() if item == category), None)
    return {'square': square, 'symbol': category.symbol, 'label': category.label,
            'color': category.color, 'ink': category.ink, 'description': category.description,
            'special': key in SPECIAL_CATEGORIES, 'side': side}


@lru_cache(maxsize=128)
def legal_move_previews(fen):
    """Small FEN previews for immediate display; no engine or evaluation."""
    board = chess.Board(fen)
    previews = {}
    for move in list(board.legal_moves):
        board.push(move)
        previews[move.uci()] = board.fen()
        board.pop()
    return previews


def interactive_board(board, *, flip=False, last_move=None, category=None, on_move,
                      ply=0, total=0, on_navigate=None, key="interactive_board", disabled=False, revision=0,
                      pgn=None, epoch=None, navigation_ack=0, explanations=None, study=False, dark=False, reviews=None,
                      mascot=False, table=False, editing=False, edit_tool='move', on_edit=None,
                      expanded=False, analysis_effects=False, hint_move=None, training_feedback=None,
                      training_mode=False, training_expected=None, animate_move=None, show_coordinates=False,
                      on_sync=None, quiz=None, training_line=None, instant=False, instant_moves=False,
                      turn_override=None, aligned=False, stable_board=False, analysis_notes=False,
                      evaluation_bar=False, evaluation_reviews=None, position_evaluation=None,training_preview=None,
                      notebook=None,on_note=None):
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
            score=(evaluation_reviews or {}).get(index)
            frame['evaluation']={'cp':score.white_cp,'mate':score.white_mate} if score else position_evaluation if index==ply else None
    score=(evaluation_reviews or {}).get(ply)
    return _BOARD(data={**position_data(board, flip, last_move), "revision": revision,
                        "legal": [] if disabled else [m.uci() for m in board.legal_moves],
                        "last": [chess.square_name(s) for s in (last_move.from_square, last_move.to_square)] if last_move else [],
                        "badge": badge, "ply": ply, "total": total, "navigation": on_navigate is not None,
                        "disabled": disabled,
                        "evaluationBar": evaluation_bar, "flip": flip,
                        "evaluation": {'cp':score.white_cp,'mate':score.white_mate} if score else position_evaluation,
                        "turnOverride": ('w' if turn_override else 'b') if turn_override is not None else None,
                        "frames": frames, "pieces": piece_images(), "epoch": epoch, "navigation_ack": navigation_ack,
                        "analysisNotes": annotation_rows(pgn, reviews) if analysis_notes else None,"notebook":notebook,
                        "movePreviews": legal_move_previews(board.fen()) if instant_moves and not disabled else None,
                        "previewFen": board.fen() if instant_moves else None,
                        "explanations": explanations, "study": study, "dark": dark, "theme": palette(dark), "mascot": mascot,
                        "table": table, "editing": editing, "editTool": edit_tool,
                        "expanded": expanded, "aligned": aligned, "stableBoard": stable_board, "analysisEffects": analysis_effects,
                        "trainingHint": hint_move, "trainingFeedback": training_feedback,
                        "trainingMode": training_mode, "trainingExpected": training_expected,
                        "trainingPreview": training_preview,
                        "quiz": quiz,
                        "trainingLine": training_line, "instant": instant,
                        "syncRecovery": on_sync is not None,
                        "showCoordinates": show_coordinates,
                        "animateMove": animate_move}, key=key,
                  on_move_change=on_move, on_note_change=on_note or (lambda:None),on_navigate_change=on_navigate or (lambda: None),
                  on_edit_change=on_edit or (lambda: None), on_sync_change=on_sync or (lambda: None))
