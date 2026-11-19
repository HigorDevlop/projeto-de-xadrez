"""Account-scoped, offline archive of completed game and FEN analyses."""
from dataclasses import asdict
from hashlib import sha256
from io import StringIO
import json
import time
import chess.pgn
import classroom as rooms
from chess_review import MoveReview
from book_study import BookReference


def identifier(pgn):
    game=chess.pgn.read_game(StringIO(pgn))
    if not game or game.errors:raise ValueError('Partida inválida.')
    return sha256((game.board().fen()+'|'+' '.join(move.uci() for move in game.mainline_moves())).encode()).hexdigest()


def _table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS saved_analyses(owner TEXT,game TEXT,pgn TEXT,title TEXT,
        payload TEXT,updated REAL,PRIMARY KEY(owner,game))''')


def save(token,pgn,result,*,ply=0,settings=None,accuracies=None):
    game=chess.pgn.read_game(StringIO(pgn));key=identifier(pgn)
    moves=list(game.mainline_moves());reviews=result['reviews']
    if set(reviews)!=set(range(1,len(moves)+1)) or (not moves and not result.get('position')):
        raise ValueError('Somente análises completas podem ser arquivadas.')
    data=dict(version=1,reviews={str(k):asdict(v) for k,v in reviews.items()},
        explanations=result['explanations'],references={str(k):[asdict(ref) for ref in refs] for k,refs in result['references'].items()},
        position=result.get('position'),engine_name=result.get('engine_name','Stockfish'),
        ply=max(0,min(len(moves),int(ply))),settings=settings or {},accuracies=accuracies or {})
    payload=json.dumps(data,ensure_ascii=False,allow_nan=False)
    title=(f"{game.headers.get('White','?')} × {game.headers.get('Black','?')} · {game.headers.get('Date','')}" if moves else 'Posição FEN · '+game.board().fen())
    with rooms.database() as db:
        _table(db);owner=rooms._identity(db,token)['id']
        db.execute('''INSERT INTO saved_analyses VALUES(?,?,?,?,?,?) ON CONFLICT(owner,game)
            DO UPDATE SET pgn=excluded.pgn,title=excluded.title,payload=excluded.payload,updated=excluded.updated''',
            (owner,key,pgn,title,payload,time.time()))
    return key


def listing(token):
    with rooms.database() as db:
        _table(db);owner=rooms._identity(db,token)['id']
        return [dict(row) for row in db.execute('SELECT game,title,updated FROM saved_analyses WHERE owner=? ORDER BY updated DESC',(owner,))]


def load(token,key=None,*,pgn=None):
    if pgn is not None:key=identifier(pgn)
    with rooms.database() as db:
        _table(db);owner=rooms._identity(db,token)['id']
        row=db.execute('SELECT * FROM saved_analyses WHERE owner=? AND game=?',(owner,key)).fetchone() if key else db.execute('SELECT * FROM saved_analyses WHERE owner=? ORDER BY updated DESC LIMIT 1',(owner,)).fetchone()
    if not row:return None
    try:
        data=json.loads(row['payload'])
        if data['version']!=1:return None
        data['reviews']={int(k):MoveReview(**value) for k,value in data['reviews'].items()}
        data['explanations']={int(k):v for k,v in data['explanations'].items()}
        data['references']={int(k):[BookReference(**dict(ref,topics=tuple(ref.get('topics',())))) for ref in refs] for k,refs in data['references'].items()}
        return dict(data,pgn=row['pgn'],id=row['game'],updated=row['updated'])
    except (ValueError,TypeError,KeyError):return None


def restore(state,saved):
    if not saved:return False
    state.reviews=saved['reviews'];state.explanations=saved['explanations'];state.book_references=saved['references']
    state.position_evaluation=saved.get('position')
    state.analysis_signature=('saved',saved['version'],saved['id'])
    state.loaded_analysis=(state.game,state.analysis_signature,state.analysis_generation)
    state.analysis_requested=True;state.analysis_options_open=False
    state.official_accuracies=saved.get('accuracies') or state.get('official_accuracies',{})
    state.analysis_saved_at=saved['updated']
    return True


def render_saved(reset_game):
    import streamlit as st
    from datetime import datetime
    from preparation_state import LOCAL_ZONE
    token=st.session_state.get('classroom_token')
    if not token:return
    items=listing(token)
    if not items:return
    with st.expander(f'Análises salvas · {len(items)}',icon=':material/save:'):
        lookup={item['game']:item for item in items}
        selected=st.selectbox('Partida ou posição avaliada',list(lookup),format_func=lambda k:lookup[k]['title'],key='saved_analysis_choice')
        st.caption('Salva em '+datetime.fromtimestamp(lookup[selected]['updated'],LOCAL_ZONE).strftime('%d/%m/%Y às %H:%M')+' · disponível offline nesta conta')
        if st.button('Abrir análise salva',icon=':material/restore:',key='saved_analysis_open'):
            saved=load(token,selected)
            if saved:
                reset_game(chess.pgn.read_game(StringIO(saved['pgn'])))
                st.session_state.ply=saved['ply'];st.rerun(scope='app')
            else:st.warning('Não foi possível ler esta análise salva.')
