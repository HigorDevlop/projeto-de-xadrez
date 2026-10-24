"""Offline, account-scoped study notes attached to a game and its positions."""
from hashlib import sha256
from io import StringIO
import time
import chess.pgn
import streamlit as st
import classroom as rooms


def game_key(pgn):
    game=chess.pgn.read_game(StringIO(pgn))
    if not game:raise ValueError('Partida inválida.')
    source=game.board().fen()+'|'+str(dict(game.headers))+'|'+' '.join(m.uci() for m in game.mainline_moves())
    return sha256(source.encode()).hexdigest()


def _table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS study_notebook(owner TEXT,game TEXT,position TEXT,
        title TEXT,fen TEXT,body TEXT,updated REAL,PRIMARY KEY(owner,game,position))''')
    db.execute('''CREATE TABLE IF NOT EXISTS study_notebook_games(owner TEXT,game TEXT,title TEXT,pgn TEXT,
        updated REAL,PRIMARY KEY(owner,game))''')


def saved_games(token,identifier=None):
    with rooms.database() as db:
        _table(db);actor=rooms._identity(db,token)
        rows=db.execute('SELECT * FROM study_notebook_games WHERE owner=? ORDER BY updated DESC',(actor['id'],)).fetchall()
        return next((dict(r) for r in rows if r['game']==identifier),None) if identifier else [dict(r) for r in rows]


def entries(token,game):
    with rooms.database() as db:
        _table(db);actor=rooms._identity(db,token)
        return [dict(r) for r in db.execute('SELECT * FROM study_notebook WHERE owner=? AND game=? ORDER BY updated DESC',(actor['id'],game))]


def board_notebook_data(pgn):
    state=st.session_state;token=state.get('classroom_token')
    actor=rooms.identity(token)
    if not actor:return None
    identifier=state.setdefault('analysis_notebook_id',game_key(pgn))
    return dict(id=identifier,owner=actor['id'],entries=entries(token,identifier),
                games=[dict(id=g['game'],title=g['title']) for g in saved_games(token)],
                ack=state.get('analysis_note_ack'),status=state.get('analysis_note_status',''))


def board_note_changed():
    state=st.session_state;event=state.interactive_board.note
    if not isinstance(event,dict) or event.get('nonce')==state.get('analysis_note_ack'):return
    token=state.get('classroom_token')
    try:
        if event.get('action')=='resume':
            saved=saved_games(token,event.get('id'))
            if not saved:raise ValueError('Caderno não encontrado nesta conta.')
            state.analysis_notebook_load=saved['game'];state.requested_page='Análise'
            state.analysis_note_ack=event.get('nonce');st.rerun(scope='app')
        if event.get('id')!=state.get('analysis_notebook_id'):raise ValueError('A partida mudou. Confira sua anotação antes de salvar.')
        board=chess.Board(event['fen'])
        position='general' if event.get('mode')=='general' else board.epd()
        save_entry(token,event['id'],position,'Resumo da partida' if position=='general' else str(event.get('label','Posição'))[:100],
                   '' if position=='general' else board.fen(),event.get('body',''),pgn=state.game)
        state.analysis_note_status='Anotação salva no caderno.'
    except (ValueError,PermissionError,KeyError) as error:state.analysis_note_status=str(error)
    state.analysis_note_ack=event.get('nonce')


def save_entry(token,game,position,title,fen,body,pgn=None):
    if not isinstance(body,str) or len(body)>20_000:raise ValueError('A anotação pode ter até 20 mil caracteres.')
    with rooms.database() as db:
        _table(db);actor=rooms._identity(db,token)
        if pgn is not None:
            parsed=chess.pgn.read_game(StringIO(pgn))
            if not parsed or parsed.errors:raise ValueError('Partida inválida.')
            name=f"{parsed.headers.get('White','?')} × {parsed.headers.get('Black','?')} · {len(list(parsed.mainline_moves()))} meios-lances"
            db.execute('INSERT INTO study_notebook_games VALUES(?,?,?,?,?) ON CONFLICT(owner,game) DO UPDATE SET title=excluded.title,pgn=excluded.pgn,updated=excluded.updated',
                       (actor['id'],game,name,pgn,time.time()))
        if body.strip():
            db.execute('INSERT INTO study_notebook VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner,game,position) DO UPDATE SET title=excluded.title,fen=excluded.fen,body=excluded.body,updated=excluded.updated',
                       (actor['id'],game,position,title,fen,body.strip(),time.time()))
        else:db.execute('DELETE FROM study_notebook WHERE owner=? AND game=? AND position=?',(actor['id'],game,position))


def render_notebook(pgn,ply):
    state=st.session_state;token=state.get('classroom_token')
    actor=rooms.identity(token)
    if not actor:return
    saved=saved_games(token)
    if saved:
        lookup={item['game']:item for item in saved}
        selected=st.selectbox('Cadernos salvos',list(lookup),format_func=lambda k:lookup[k]['title'],key='analysis_notebook_saved')
        if st.button('Retomar partida anotada',key='analysis_notebook_resume'):
            state.analysis_notebook_load=selected
            state.requested_page='Análise';st.rerun(scope='app')
    identifier=state.setdefault('analysis_notebook_id',game_key(pgn))
    game=chess.pgn.read_game(StringIO(pgn));board=game.board();label='Posição inicial'
    for index,move in enumerate(list(game.mainline_moves())[:ply]):
        label=f"{board.fullmove_number}{'.' if board.turn else '...'} {board.san(move)}"
        board.push(move)
    mode=st.radio('Anotar sobre',['Posição atual','Resumo da partida'],horizontal=True,key='analysis_notebook_mode')
    position=board.epd() if mode=='Posição atual' else 'general'
    title=label if mode=='Posição atual' else 'Resumo da partida'
    rows=entries(token,identifier)
    current=next((r['body'] for r in rows if r['position']==position),'')
    key='analysis_note_'+sha256((actor['id']+identifier+position).encode()).hexdigest()[:24]
    st.caption(title+' · anotações privadas, salvas neste computador')
    with st.form(key+'_form'):
        body=st.text_area('Pontos importantes do estudo',value=current,height=180,max_chars=20_000,key=key)
        if st.form_submit_button('Salvar anotação',type='primary'):
            save_entry(token,identifier,position,title,board.fen() if position!='general' else '',body,pgn=pgn)
            rows=entries(token,identifier);st.success('Anotação salva no caderno.')
    with st.expander(f'Pontos anotados · {len(rows)}'):
        for row in rows:
            st.markdown('**'+row['title']+'**');st.text(row['body'])
        if not rows:st.caption('Registre ideias, planos e dúvidas durante a análise.')
    exported='# Caderno de estudo\n\n'+'\n\n'.join('## '+r['title']+'\n'+r['body']+('\n\nFEN: '+r['fen'] if r['fen'] else '') for r in rows)
    st.download_button('Baixar caderno',exported,file_name='caderno-de-estudo.md',mime='text/markdown',key='analysis_notebook_download')
