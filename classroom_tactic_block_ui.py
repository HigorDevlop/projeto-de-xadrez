"""Fragment-based tactical blocks with bounded background preloading."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import hashlib
import json
from threading import Lock
import chess
import streamlit as st
import classroom_tactic_blocks as blocks

_futures={};_lock=Lock()

@lru_cache(maxsize=1)
def workers():return ThreadPoolExecutor(max_workers=1,thread_name_prefix='classroom-tactic-preload')

@lru_cache(maxsize=256)
def root_frame(fen):
    board=chess.Board(fen)
    return dict(fen=board.fen(),legal=[move.uci() for move in board.legal_moves],last=[])


def preload(group,index):
    ready=0
    with _lock:
        for puzzle in group[index+1:index+4]:
            fen=puzzle['fen']
            if fen not in _futures:_futures[fen]=workers().submit(root_frame,fen)
            ready+=int(_futures[fen].done() and _futures[fen].exception() is None)
        while len(_futures)>32:_futures.pop(next(iter(_futures)))
    return ready


def forecast(payload,state):
    board,moves,side=blocks.position(payload,state);source=board.fen();expected=moves[state['ply']]
    board.push_uci(expected);at=state['ply']+1
    if at<len(moves) and board.turn!=side:board.push_uci(moves[at]);at+=1
    group=blocks.puzzles(payload)
    if at==len(moves) and state['index']+1<len(group):frame=root_frame(group[state['index']+1]['fen'])
    else:frame=dict(fen=board.fen(),legal=[],last=[])
    return dict(sourceFen=source,expected=expected,position=frame)


@st.fragment
def render_block(payload,key,token=None,identifier=None,refresh_parent=False,on_complete=None):
    from interactive_board import interactive_board
    preview=token is None
    if preview:
        signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        if st.session_state.get(key+'_source')!=signature:
            st.session_state[key+'_source']=signature;st.session_state[key+'_state']=blocks.initial();st.session_state[key+'_revision']=st.session_state.get(key+'_revision',0)+1
        state=st.session_state[key+'_state']
    else:
        try:payload,state=blocks.get_state(token,identifier)
        except PermissionError:st.info('Esta atividade aguarda liberação.');return
    group=blocks.puzzles(payload);score=blocks.summary(payload,state);revision=st.session_state.get(key+'_revision',0)
    ready=preload(group,state['index']) if not score['done'] else 0
    st.caption(('Simulação do professor · ' if preview else '')+str(score['total'])+' táticos · mínimo de 90% sem erro para avançar')
    cols=st.columns(3);cols[0].metric('Concluídos',str(score['finished'])+'/'+str(score['total']));cols[1].metric('Sem erro',score['clean']);cols[2].metric('Precisão',f"{score['accuracy']:.1f}%")
    def apply(action,event=None):
        correct=None
        if preview:
            if action=='restart':new=blocks.initial(state['passed'],state.get('history',[]))
            elif action=='skip':new=blocks.advance_without_credit(payload,state,state['index'],state['ply'])
            else:new,correct=blocks.attempt(payload,state,state['index'],state['ply'],event['uci'],event['fen'])
            st.session_state[key+'_state']=new
        else:
            new,correct=blocks.act(token,identifier,state['index'],state['ply'],event.get('uci') if event else None,event.get('fen') if event else None,action)
        st.session_state[key+'_revision']=revision+1
        st.session_state[key+'_notice']='Correto!' if correct else 'Este exercício teve erro. Continue ou tente outra rodada.' if correct is False else ''
        if preview and blocks.summary(payload,new)['done'] and blocks.summary(payload,new)['passed'] and on_complete:on_complete()
        if not preview:
            _,latest=blocks.get_state(token,identifier)
            if action!='restart' and blocks.summary(payload,latest)['done'] and blocks.summary(payload,latest)['passed']:
                st.session_state.prep_next_after=identifier;st.rerun(scope='app')
        if preview and refresh_parent and blocks.summary(payload,new)['done']:st.rerun(scope='app')
        st.rerun(scope='fragment')
    if score['done']:
        if score['current_pass']:st.success('Bloco aprovado! Próxima atividade liberada.' if not preview else 'Simulação aprovada: a próxima atividade seria liberada.')
        elif score['passed']:st.info('Esta rodada ficou abaixo de 90%. O avanço já foi conquistado em uma rodada anterior.')
        else:st.warning('Rodada concluída abaixo de 90%. Faça uma nova tentativa para liberar a próxima atividade.')
        if st.button('Nova tentativa do bloco',key=key+'_retry',type='primary'):apply('restart')
        if not preview and score['passed'] and st.button('Continuar para a próxima atividade',key=key+'_continue'):
            st.session_state.prep_next_after=identifier;st.rerun(scope='app')
        return
    board,moves,side=blocks.position(payload,state)
    st.caption('Exercício '+str(state['index']+1)+' de '+str(len(group))+' · '+('Brancas jogam' if side else 'Pretas jogam'))
    result=interactive_board(board,key=key+'_board',on_move=lambda:None,on_sync=lambda:None,revision=revision,
        flip=not side,stable_board=True,training_mode=True,training_expected=moves[state['ply']],training_preview=forecast(payload,state),
        dark=True,table=False,show_coordinates=True)
    if notice:=st.session_state.get(key+'_notice'):st.caption(notice)
    if ready:st.caption(str(ready)+' próximos exercícios preparados')
    left,right=st.columns(2)
    if left.button('Pular exercício (conta como erro)',key=key+'_skip'):apply('skip')
    if right.button('Recomeçar bloco',key=key+'_restart'):apply('restart')
    for field in ('move','sync'):
        event=getattr(result,field,None)
        if isinstance(event,dict) and event.get('revision')==revision:
            try:apply('move',event)
            except (ValueError,PermissionError) as error:
                st.session_state[key+'_notice']=str(error);st.session_state[key+'_revision']=revision+1;st.rerun(scope='fragment')
