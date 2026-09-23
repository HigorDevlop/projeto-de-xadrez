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
      .tactic-demo {display:flex;flex-direction:column;align-items:center;text-align:center;
        padding:12px;color:var(--ink);font:16px/1.6 sans-serif}
      .eyebrow {font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--muted)}
      h2 {font-size:clamp(22px,3vw,32px);margin:8px 0 20px}
      .demo-board {width:min(100%,66vh,640px);border:6px solid #34583f;border-radius:12px;overflow:hidden;
        box-shadow:0 18px 42px #0003;line-height:0}
      .demo-board svg {width:100%;height:auto}
      .caption {margin:18px 0 3px;font-weight:600}
      small {color:var(--muted)}
      button {margin-top:12px;border:1px solid var(--muted);border-radius:20px;padding:7px 16px;
        color:var(--ink);background:transparent;cursor:pointer}
    ''',
    js='''export default function({data,parentElement}) {
      const host=parentElement.host ?? parentElement;
      host.style.setProperty('--ink',data.dark?'#f3f4f6':'#202530');
      host.style.setProperty('--muted',data.dark?'#c4cbd6':'#505968');
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
