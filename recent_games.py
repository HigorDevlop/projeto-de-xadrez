"""Eight recent Chess.com games, with official or explicitly estimated accuracy."""
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import math

import chess
import chess.pgn
import chess.svg
import streamlit as st

from chess_review import player_accuracy
from stockfish_analysis import analyse_with_books
from design_tokens import palette


def game_id(item):
    return sha256(item.get('pgn', '').encode()).hexdigest()


def recent_eight(history):
    seen, games = set(), []
    for item in sorted(history, key=lambda g: g.get('end_time', 0), reverse=True):
        identity = item.get('url') or game_id(item)
        if identity in seen:
            continue
        seen.add(identity)
        games.append(item)
        if len(games) == 8:
            break
    return games


def official_accuracy(item, side):
    value = (item.get('accuracies') or {}).get(side)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 100 else None


@st.cache_data(max_entries=64, show_spinner=False)
def estimate_accuracy(pgn, engine_path, _cancel=None):
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None or game.errors:
        raise ValueError('PGN inválido; não foi possível calcular a precisão.')
    result = analyse_with_books(game, engine_path, quality='Rápida', cancel=_cancel)
    reviews = list(result['reviews'].values())
    return {side: player_accuracy(reviews, label) for side, label in [('white', 'Brancas'), ('black', 'Pretas')]}


@st.cache_data(max_entries=32, show_spinner=False)
def final_board_svg(pgn, flip=False):
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None or game.errors:
        raise ValueError('PGN inválido')
    board = game.end().board()
    return chess.svg.board(board, size=320, coordinates=False, orientation=not flip,
                           lastmove=board.peek() if board.move_stack else None,
                           colors={'square light': '#F2EEDF', 'square dark': '#72977E'})


def cards_data(history, username, estimates):
    cards = []
    for index, item in enumerate(recent_eight(history)):
        side = 'black' if item.get('black', {}).get('username', '').lower() == username.lower() else 'white'
        value = official_accuracy(item, side)
        source = 'Chess.com'
        if value is None:
            value = estimates.get(game_id(item), {}).get(side)
            source = 'estimada · Stockfish'
        accuracy = 'Precisão: ' + (f'{value:.1f}% · {source}'.replace('.', ',', 1) if value is not None else 'não publicada')
        try:
            svg = final_board_svg(item['pgn'], side == 'black')
            error = ''
        except (ValueError, KeyError):
            svg = chess.svg.board(chess.Board(None), size=320, coordinates=False)
            error = 'Não foi possível ler esta partida.'
        white = item.get('white', {}).get('username', '?')
        black = item.get('black', {}).get('username', '?')
        date = datetime.fromtimestamp(item.get('end_time', 0), timezone.utc).strftime('%d/%m/%Y · %H:%M UTC')
        cards.append({'index': index, 'title': f'{white} × {black}', 'date': date, 'svg': svg,
                      'accuracy': accuracy, 'error': error, 'empty': False})
    while len(cards) < 8:
        cards.append({'index': len(cards), 'title': 'Nenhuma partida neste espaço', 'date': '',
                      'svg': chess.svg.board(chess.Board(None), size=320, coordinates=False,
                                            colors={'square light': '#c5ccc1', 'square dark': '#5d7263'}),
                      'accuracy': 'Precisão: —', 'error': '', 'empty': True})
    return cards


_RECENT = st.components.v2.component(
    'recent_chesscom_games', html='<section class="recent-grid" aria-label="Últimas oito partidas do Chess.com"></section><nav class="recent-pages" aria-label="Páginas de partidas"></nav>',
    css='''
    .recent-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;color:var(--ink);font-family:'Segoe UI',system-ui,sans-serif}
    article {padding:18px;background:var(--surface);border:1px solid var(--border);border-radius:14px;min-width:0;
      transition:border-color .15s;display:flex;flex-direction:column}
    article:not(.empty):hover {border-color:var(--accent)}
    .game-number {font-size:10px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:var(--gold);margin:0 0 10px}
    h3 {font:600 15px/1.45 'Segoe UI',system-ui,sans-serif;margin:0 0 5px;overflow-wrap:anywhere}
    .date {font-size:11px;line-height:1.5;color:var(--muted);min-height:18px;margin:0 0 16px}
    .mini-board {display:block;width:100%;padding:0;border:0;background:none;cursor:pointer}
    .mini-board svg {display:block;width:100%;height:auto;border-radius:4px}
    .accuracy {font-size:13px;font-weight:600;line-height:1.6;margin:14px 0;min-height:40px}
    .actions {display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px;border-top:1px solid var(--border)}
    .actions button {border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--ink);padding:9px 8px;
      cursor:pointer;flex:1;font:600 12px 'Segoe UI',system-ui,sans-serif;transition:background .15s}
    .actions button:last-child {background:var(--accent-soft);color:var(--accent);border-color:transparent}
    .actions button:hover:not(:disabled) {background:var(--soft)}
    button:focus-visible {outline:3px solid var(--accent);outline-offset:3px}
    article.empty {opacity:.6}button:disabled {cursor:default}
    .error {font-size:12px;line-height:1.5;color:#B85B42}
    @media(max-width:1050px){.recent-grid {grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
    @media(max-width:450px){article{padding:10px}h3{font-size:13px}.game-number{font-size:9px;margin-bottom:7px}
      .date{font-size:10px;margin-bottom:12px}.actions{gap:5px}.actions button{font-size:11px;padding:8px 4px}.accuracy{font-size:11px}}

    .recent-grid{gap:10px}
    article{padding:10px;box-sizing:border-box;overflow:hidden}
    .game-number{margin-bottom:3px;font-size:9px}
    h3{font-size:13px;line-height:1.3;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
    .date{font-size:10px;margin-bottom:6px;min-height:14px}
    .mini-board{width:min(100%,var(--preview-size,160px));margin:auto}
    .accuracy{font-size:11px;line-height:1.3;margin:6px 0;min-height:15px}
    .actions{padding-top:6px;gap:6px}.actions button{padding:6px}
    .recent-grid.short .date,.recent-grid.short .game-number{display:none}
    .recent-grid.short article{padding:6px}
    .recent-grid.short .accuracy{margin:4px 0;font-size:10px}
    .recent-pages{display:flex;justify-content:center;gap:8px;margin-top:8px}
    .recent-pages:empty{display:none}.recent-pages button{background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:6px;padding:6px 12px;cursor:pointer}
    .recent-pages button[aria-current=page]{background:var(--accent-soft)}
    @media(prefers-reduced-motion:reduce){article,.actions button{transition:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}) {
      const host=parentElement.host ?? parentElement;
      const theme=data.theme ?? (data.dark ?
        {surface:'#1A2720',soft:'#223329',ink:'#EDF3ED',muted:'#ACBCAF',border:'#354A3C',accent:'#85C69A',accent_soft:'#263E30',gold:'#CFB780'} :
        {surface:'#FFFEFA',soft:'#ECEFE8',ink:'#202B26',muted:'#626F66',border:'#D9DED5',accent:'#176B4A',accent_soft:'#E3EFE6',gold:'#8A6A35'});
      for(const [token,value] of Object.entries(theme))host.style.setProperty('--'+token.replaceAll('_','-'),value);
      const grid=parentElement.querySelector('.recent-grid'),pager=parentElement.querySelector('.recent-pages');
      let page=parentElement._page??0;
      function paint(){
      const width=grid.clientWidth,columns=width>900?4:2;
      const available=Math.max(170,window.innerHeight-grid.getBoundingClientRect().top-32);
      const rows=available>=430?2:1,pageSize=columns*rows;
      const pages=Math.ceil(data.cards.length/pageSize);page=Math.min(page,pages-1);
      grid.classList.toggle('short',available<300);
      grid.style.gridTemplateColumns='repeat('+columns+',minmax(0,1fr))';
      host.style.setProperty('--preview-size',Math.max(32,(available-(pages>1?40:0))/rows-145)+'px');
      grid.replaceChildren();pager.replaceChildren();
      for(let index=0;index<pages && pages>1;index++){
        const button=document.createElement('button');button.type='button';button.textContent=String(index+1);
        button.setAttribute('aria-label','Página '+(index+1));
        if(index===page)button.setAttribute('aria-current','page');
        button.onclick=()=>{page=index;parentElement._page=page;paint();};pager.append(button);
      }
      for(const card of data.cards.slice(page*pageSize,(page+1)*pageSize)){
        const article=document.createElement('article');article.classList.toggle('empty',card.empty);
        const number=document.createElement('p');number.className='game-number';number.textContent='Partida '+String(card.index+1).padStart(2,'0');
        const title=document.createElement('h3');title.textContent=card.title;
        const date=document.createElement('p');date.className='date';date.textContent=card.date;
        const board=document.createElement('button');board.type='button';board.className='mini-board';
        board.setAttribute('aria-label','Abrir partida '+(card.index+1));board.innerHTML=card.svg;board.disabled=card.empty || Boolean(card.error);
        const choose=action=>setTriggerValue('select',{index:card.index,action,revision:data.revision});
        board.onclick=()=>choose('open');
        const accuracy=document.createElement('p');accuracy.className='accuracy';accuracy.textContent=card.accuracy;
        const actions=document.createElement('div');actions.className='actions';
        for(const [action,label] of [['open','Abrir'],['analyse','Analisar']]){
          const button=document.createElement('button');button.type='button';button.textContent=label;
          button.setAttribute('aria-label',label+' partida '+(card.index+1));
          button.disabled=board.disabled;button.onclick=()=>choose(action);actions.append(button);
        }
        article.append(number,title,date,board,accuracy,actions);
        if(card.error){const error=document.createElement('p');error.className='error';error.textContent=card.error;article.append(error);}
        grid.append(article);
      }
      }
      const observer=new ResizeObserver(paint);observer.observe(host);
      window.addEventListener('resize',paint);paint();
      return()=>{observer.disconnect();window.removeEventListener('resize',paint);};
    }''')


def history_revision(history):
    return sha256('|'.join(game_id(item) for item in recent_eight(history)).encode()).hexdigest()


def recent_games(history, username, estimates, dark, on_select):
    _RECENT(data={'cards': cards_data(history, username, estimates), 'dark': dark, 'theme': palette(dark),
                  'revision': history_revision(history)}, key='recent_games', on_select_change=on_select)
