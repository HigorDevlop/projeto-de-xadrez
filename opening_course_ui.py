"""Opening lessons in the reference layout, scaled for desktop."""
from html import escape
import time
import chess
import streamlit as st
from interactive_board import interactive_board
from opening_training_state import board_for, current_line, expected_move, request_hint
from opening_course_state import active_session, settle_immediate, course_lines, receive_move, resync_board
from opening_reference_style import CSS as STYLE, title_html
from opening_reference_catalog import DISPLAY_NAMES
from opening_reference_pages import rank_card, render_trail
from opening_reference_progress import continue_checkpoint, position_progress
from opening_reference_engine import evaluation
from preparation_state import today

_SCROLL_TOP=st.components.v2.component('opening_reference_scroll',html='<span hidden></span>',js="""export default function({parentElement}){
const timer=setTimeout(()=>parentElement.ownerDocument.querySelector('[data-testid=stMain]')?.scrollTo({top:0,behavior:'instant'}),80);return()=>clearTimeout(timer);}""")
def scroll_course_top():
    _SCROLL_TOP(key='opening_course_scroll_top',height=0)


def lesson_marks(line,session):
    marks=session.get('display_marks',session.get('marks',{}))
    labels={'pending':'A fazer','wrong':'Erro','unknown':'Não sei','correct':'Certo'}
    plies=list(range(0 if line['side']=='white' else 1,len(line['moves']),2))
    if session['mode']=='quiz':
        colors={'pending':('#42a7ef','#359feb','✦'),'wrong':('#c73d50','#b92236','×'),
                'unknown':('#f3ae20','#855900','?'),'correct':('#66bc24','#52c10c','✓')}
        cells=[]
        for key in labels:
            count=sum(marks.get(str(ply),'pending')==key for ply in plies)
            tone,fill,symbol=colors[key]
            if count==0: fill={'pending':'#255e89','wrong':'#641c2a','unknown':'#825800','correct':'#286415'}[key]
            cells.append(f'<div class="reference-counter {key}" style="--tone:{tone};--fill:{fill}"><small>{labels[key]}</small><div><i>{symbol}</i>{count}</div></div>')
        st.html('<div class="reference-counters" aria-label="A fazer, erro, não sei e certo">'+''.join(cells)+'</div>')
    else:
        cells=[]
        for number,ply in enumerate(plies,1):
            mark=marks.get(str(ply),'pending')
            cells.append(f'<span class="opening-mark {mark}" role="img" aria-label="Lance {number}: {labels[mark]}"></span>')
        st.html('<div class="opening-marks" role="group" aria-label="Acertos e erros da linha">'+''.join(cells)+'</div>')


@st.fragment
def render_lesson(plan,save,back,dark=True):
    state=st.session_state
    plan=state.openings_plan
    session=active_session(plan)
    if session is None:
        back();st.rerun()
    session['reference_mode']=True
    if settle_immediate(plan,session): save(plan)
    line=current_line(plan,session)
    board=board_for(session)
    checkpoint=session.get('ui_checkpoint')
    complete=session['phase']=='complete'
    expected=expected_move(plan,session)
    learning=session['mode']=='learn'
    show_hint=bool(expected and (learning or session['hint'] or checkpoint and checkpoint['kind']=='error'))
    title=DISPLAY_NAMES.get(plan['repertoire_ids'][0],line['opening'])
    feedback=dict(session['feedback'] or {})
    if checkpoint and checkpoint['kind']=='error': feedback.update(correct=False,uci=checkpoint['wrong'])

    def hint():
        if request_hint(plan,session): save(plan)
    def pause():
        session['paused']=not session.get('paused',False)
        session['revision']+=1;save(plan)
    def next_step():
        continue_checkpoint(plan,session)
        settle_immediate(plan,session)
        save(plan)
    def finish():
        upcoming=next((item for item in course_lines(plan) if item['unlocked'] and not item['learned']),None)
        state.reference_next_line=upcoming['id'] if upcoming and session.get('practice_intent')=='learn' else None
        known,total=position_progress(plan);target=min(25,total)
        if session.get('practice_intent')!='explore' and target and known>=target and not plan.get('reference_award_seen'):
            plan['reference_award_seen']=True;state.openings_overlay='award'
        elif plan.get('reference_streak_seen')!=str(today()) and session.get('practice_intent')!='explore':
            plan['reference_streak_seen']=str(today());state.openings_overlay='streak_reward'
        else:
            state.openings_overlay=None
        save(plan);back()
        if not state.openings_overlay and state.reference_next_line:
            from opening_course_state import begin_line
            begin_line(plan,state.reference_next_line)['reference_mode']=True
            state.openings_active=True;save(plan)
        st.rerun()

    message='Jogue o lance indicado pela seta verde' if show_hint else 'Jogue o lance que você aprendeu'
    css=''
    if session.get('paused'): message='Treino pausado'
    elif complete: message='Bom trabalho!';css='success'
    elif checkpoint and checkpoint['kind']=='stage':
        message='Tente de novo!' if learning else 'Mais uma vez!';css='success'
    elif checkpoint and checkpoint['kind']=='error': message='Jogue o lance que você aprendeu'
    elif session.get('line_error') and not learning: message='Erro anterior'
    resolved=sum(v=='correct' for v in session.get('display_marks',{}).values())
    decisions=len(range(0 if line['side']=='white' else 1,len(line['moves']),2))
    ratio=1 if complete else min(1,session['ply']/max(1,len(line['moves']))) if session['mode']!='quiz' else resolved/max(1,decisions)
    with st.container(key='opening_lesson',gap='xsmall'):
        with st.container(key='opening_lesson_toolbar',horizontal=True):
            st.button('Voltar ao curso',icon=':material/chevron_left:',type='tertiary',on_click=back)
            st.button('Retomar treino' if session.get('paused') else 'Pausar treino',type='tertiary',on_click=pause)
        if not state.get('openings_active'): st.rerun()
        st.html(title_html(title,line.get('variation','')))
        st.html(f'<div class="reference-meter" role="progressbar" aria-label="Progresso da aula" aria-valuenow="{round(ratio*100)}" aria-valuemin="0" aria-valuemax="100"><span style="width:{ratio*100}%"></span></div>')
        with st.container(key='opening_lesson_columns'):
            left,right=st.columns([1.65,1],gap='large')
            with left:
                with st.container(key='opening_lesson_board',gap='xsmall'):
                    score=evaluation(board.fen())
                    st.html('<div class="reference-evaluation"><span>Avaliação: <b>'+escape(score or '—')+'</b></span>'+( '<small>Stockfish local</small>' if score else '<small>Motor indisponível</small>')+'</div>')
                    if complete: st.html('<style>.st-key-opening_lesson_board [class*="st-key-openings_board"]{filter:blur(4px)}</style>')
                    result=interactive_board(board,key=f"openings_board_{session['token']}",on_move=lambda:None,on_sync=lambda:None,
                        epoch=session['token'],instant=True,revision=f"{session['token']}:{session['revision']}",
                        flip=line['side']=='black',dark=True,disabled=bool(complete or checkpoint or session.get('paused') or session['phase']!='answer'),
                        hint_move=expected if show_hint else None,training_mode=True,
                        training_expected=expected if not checkpoint and session['phase']=='answer' else None,
                        training_feedback=feedback or None,show_coordinates=True)
                    for kind,handler in (('move',receive_move),('sync',resync_board)):
                        event=getattr(result,kind,None)
                        if not isinstance(event,dict): continue
                        attempts=event.get('attempts',[event])
                        if not isinstance(attempts,list) or not attempts or not isinstance(attempts[-1],dict): continue
                        latest=attempts[-1]
                        identifier=(latest.get('revision'),latest.get('fen'),latest.get('uci'))
                        key='openings_board_handled_'+kind
                        if state.get(key)==identifier: continue
                        state[key]=identifier
                        changed=handler(plan,event,time.time()) if kind=='move' else handler(plan,event)
                        if changed: save(plan);st.rerun(scope='fragment')
                    st.html(f'<div class="reference-feedback {css}" role="status" aria-live="polite">'+('<span class="red">↻</span>' if message=='Erro anterior' else '')+escape(message)+'</div>')
            with right:
                with st.container(key='opening_lesson_side'):
                    lesson_marks(line,session)
                    if checkpoint and checkpoint['kind']=='error':
                        st.html('<p class="reference-side-label">Observe a seta verde e revise o lance.</p>')
                        if st.button('Próximo',type='primary',width='stretch'): next_step();st.rerun(scope='fragment')
                    elif checkpoint:
                        st.html('<p class="reference-side-label">'+('Repita os lances de memória.' if learning else 'Revise as posições que você aprendeu.')+'</p>')
                        if st.button('Continuar',type='primary',width='stretch'): next_step();st.rerun(scope='fragment')
                    elif complete:
                        if st.button('Continuar',type='primary',width='stretch'): finish()
                    else:
                        st.html('<p class="reference-side-label">'+('Siga a seta verde.' if learning else 'Sua vez. Jogue o lance que você aprendeu.')+'</p>')
                        if not learning:
                            st.button('Não sei',on_click=hint,width='stretch',disabled=bool(session.get('paused') or session['hint']))
                    with st.container(key='reference_hint'):
                        with st.popover('Analisar posição',icon=':material/search:',width='stretch'):
                            st.write('Avaliação: '+(score or 'indisponível'))
                            st.caption('Valores calculados pelo Stockfish instalado no computador.')
                            st.code(board.fen(),language=None)
                            if expected and not complete:
                                st.write('Lance da linha: **'+board.san(chess.Move.from_uci(expected))+'**')
