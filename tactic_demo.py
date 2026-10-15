"""Demonstrações locais: lances legais e animação independente do servidor."""
from functools import lru_cache
import chess
import chess.svg
import streamlit as st


DEMONSTRATIONS = (
    ('Mate na última fileira', '6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1', ('a1a8',)),
    ('Garfo / ataque duplo', '3q3k/8/8/4N3/8/8/8/4K3 w - - 0 1', ('e5f7', 'h8g8', 'f7d8')),
    ('Mate abafado', '6rk/6pp/8/4N3/8/8/8/6K1 w - - 0 1', ('e5f7',)),
)


@lru_cache(maxsize=1)
def demo_frames():
    frames = []
    for title, fen, moves in DEMONSTRATIONS:
        board = chess.Board(fen)
        for index in range(len(moves) + 1):
            last = board.peek() if board.move_stack else None
            frames.append({'title': title,
                           'caption': 'Observe a posição…' if index == 0 else 'Exercício resolvido!' if index == len(moves) else 'O adversário responde…',
                           'svg': chess.svg.board(board, lastmove=last, coordinates=False, size=640,
                                                  colors={'square light': '#f3f7eb', 'square dark': '#629269'}),
                           'duration': 2200 if index in (0, len(moves)) else 1400})
            if index < len(moves):
                move = chess.Move.from_uci(moves[index])
                if move not in board.legal_moves:
                    raise ValueError('Lance inválido na demonstração.')
                board.push(move)
    return frames


_DEMO = st.components.v2.component(
    'tactic_demonstration',
    html='''<section class="tactic-demo" aria-label="Demonstração automática de táticos">
      <span class="eyebrow">OBSERVE · DESCUBRA · PRATIQUE</span><h2></h2>
      <div class="demo-board" aria-hidden="true"></div><p class="caption"></p>
      <small>Escolha um tema abaixo para começar a jogar.</small>
      <button type="button">Pausar demonstração</button></section>''',
    css='''
      .tactic-demo {display:grid;grid-template-columns:minmax(220px,1fr) 1fr;column-gap:40px;align-items:start;
        padding:12px;color:var(--ink);font:16px/1.6 'Segoe UI',system-ui,sans-serif}
      .eyebrow {grid-column:2;font-size:10px;font-weight:700;letter-spacing:.2em;color:var(--muted);padding-top:12px}
      h2 {grid-column:2;font:500 clamp(25px,3vw,36px)/1.2 Georgia,serif;margin:8px 0 12px;letter-spacing:-.03em}
      .demo-board {grid-column:1;grid-row:1/7;align-self:center;justify-self:center;width:min(100%,400px);border:5px solid #34583f;border-radius:8px;overflow:hidden;line-height:0}
      .demo-board svg {width:100%;height:auto}
      .caption {grid-column:2;margin:12px 0 3px;font-weight:600}
      small {grid-column:2;color:var(--muted)}
      button {grid-column:2;justify-self:start;margin-top:20px;border:1px solid var(--muted);border-radius:9px;padding:9px 16px;
        color:var(--ink);background:transparent;cursor:pointer}
      @media(max-width:640px){.tactic-demo{display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px}.demo-board{order:3;width:min(100%,330px)}.caption{order:4}small{order:5}button{order:6}}
    ''',
    js='''export default function({data,parentElement}) {
      const host=parentElement.host ?? parentElement;
      host.style.setProperty('--ink',data.dark?'#EDF3ED':'#202B26');
      host.style.setProperty('--muted',data.dark?'#ACBCAF':'#626F66');
      const state=parentElement._demo ??= {index:0,paused:matchMedia('(prefers-reduced-motion: reduce)').matches,timer:null};
      const button=parentElement.querySelector('button');
      function paint(){
        const frame=data.frames[state.index];
        parentElement.querySelector('h2').textContent=frame.title;
        parentElement.querySelector('.caption').textContent=frame.caption;
        parentElement.querySelector('.demo-board').innerHTML=frame.svg;
        button.textContent=state.paused?'Reproduzir demonstração':'Pausar demonstração';
      }
      function schedule(){clearTimeout(state.timer);if(!state.paused)state.timer=setTimeout(()=>{
        state.index=(state.index+1)%data.frames.length;paint();schedule();
      },data.frames[state.index].duration);}
      button.onclick=()=>{state.paused=!state.paused;paint();schedule();};
      paint();schedule();return ()=>clearTimeout(state.timer);
    }''',
)


def tactic_demo(dark=False):
    _DEMO(data={'frames': demo_frames(), 'dark': dark}, key='tactic_demonstration')
