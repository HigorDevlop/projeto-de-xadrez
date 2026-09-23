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
                           colors={'square light': '#f3f7eb', 'square dark': '#629269'})


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
    'recent_chesscom_games', html='<section class="recent-grid" aria-label="Últimas oito partidas do Chess.com"></section>',
    css='''
    .recent-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;color:var(--ink)}
    article {padding:14px;background:var(--surface);border:1px solid var(--border);border-radius:18px;min-width:0}
    h3 {font:600 15px/1.4 sans-serif;margin:0 0 5px;overflow-wrap:anywhere}
    .date {font:11px/1.5 sans-serif;opacity:.7;min-height:18px;margin:0 0 12px}
    .mini-board {display:block;width:100%;padding:0;border:0;background:none;cursor:pointer}
    .mini-board svg {display:block;width:100%;height:auto;border-radius:6px}
    .accuracy {font:600 13px/1.5 sans-serif;margin:12px 0 8px;min-height:40px}
    .actions {display:flex;gap:8px;flex-wrap:wrap}
    .actions button {border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--ink);padding:8px;cursor:pointer;flex:1}
    button:focus-visible {outline:3px solid #a78bfa;outline-offset:3px}
    article.empty {opacity:.5}button:disabled {cursor:default}
    .error {font:12px/1.5 sans-serif;color:#ec9c7f}
    @media(max-width:1050px){.recent-grid {grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
    @media(max-width:450px){article{padding:8px}h3{font-size:12px}.actions button{font-size:12px;padding:7px 4px}.accuracy{font-size:11px}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}) {
      const host=parentElement.host ?? parentElement;
      host.style.setProperty('--surface',data.dark?'#171e28':'#fffaf0');
      host.style.setProperty('--ink',data.dark?'#f3f4f6':'#202530');
      host.style.setProperty('--border',data.dark?'#414c5b':'#b5a991');
      const grid=parentElement.querySelector('.recent-grid');grid.replaceChildren();
      for(const card of data.cards){
        const article=document.createElement('article');article.classList.toggle('empty',card.empty);
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
        article.append(title,date,board,accuracy,actions);
        if(card.error){const error=document.createElement('p');error.className='error';error.textContent=card.error;article.append(error);}
        grid.append(article);
      }
    }''')


def history_revision(history):
    return sha256('|'.join(game_id(item) for item in recent_eight(history)).encode()).hexdigest()


def recent_games(history, username, estimates, dark, on_select):
    _RECENT(data={'cards': cards_data(history, username, estimates), 'dark': dark,
                  'revision': history_revision(history)}, key='recent_games', on_select_change=on_select)
