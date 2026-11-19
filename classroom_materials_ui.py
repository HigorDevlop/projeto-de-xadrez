"""Teacher-authored lessons, selected tactics, studied games and exams."""
import hashlib
import json
import streamlit as st
import classroom_materials as materials

LABELS={'line':'Linha de treino','tactic':'Tático','game':'Partida estudada','exam':'Prova','video':'Vídeo','note':'Anotação'}


def _save(token,student,title,kind,payload,published=True):
    try:
        materials.save_material(token,student,title,kind,payload,published)
        st.success('Material salvo e disponível ao aluno.' if published else 'Rascunho salvo. Publique quando estiver pronto.')
    except (ValueError,PermissionError) as error:st.error(str(error))


def _preview(payload,kind,key):
    from interactive_board import interactive_board
    board,moves=materials.training_moves(payload,kind)
    ply=st.slider('Percorrer lances',0,len(moves),0,key=key+'_ply') if moves else 0
    game=materials.parse_pgn(payload['pgn']) if kind!='tactic' else None
    node=game
    for move in moves[:ply]:
        board.push_uci(move)
        if node:node=node.variation(0)
    interactive_board(board,key=key,on_move=lambda:None,disabled=True,revision=ply,flip=payload.get('side')=='black',dark=True,table=False,show_coordinates=True)
    note=next((note for note in payload.get('position_notes',[]) if note['ply']==ply and note['fen']==board.fen()),None)
    text=note['text'] if note else node.comment if node else ''
    if text:
        from classroom_coach_instructor import render_instructor
        from classroom_position_notes import positions
        label=positions(payload['pgn'])[ply]['label'] if kind!='tactic' else 'Posição do exercício'
        render_instructor([dict(label=label,text=text)],key+'_instructor')
    st.caption('Brancas jogam' if board.turn else 'Pretas jogam')


def teacher_materials(token,student):
    st.html("""<style>
    .st-key-material_studio{max-width:1250px}
    .stApp .st-key-material_studio [role=tablist]{background:transparent!important;border:0!important;border-bottom:1px solid #ffffff18!important;border-radius:0!important;padding:0!important;gap:20px!important;box-shadow:none!important}
    .stApp .st-key-material_studio [role=tab]{background:transparent!important;border-radius:0!important;padding:12px 4px!important;box-shadow:none!important}
    .st-key-material_content,.st-key-material_publish{padding:22px!important;border:1px solid #83907136!important;border-radius:16px!important;background:linear-gradient(145deg,#202620,#151a16)!important;box-shadow:inset 0 1px #ffffff0e,0 8px 20px #0003}
    .st-key-material_studio button{border-radius:11px!important;min-height:43px;box-shadow:inset 0 1px #ffffff12,0 3px 8px #0003}
    .st-key-material_studio [data-testid=stCaptionContainer]{color:#aeb9a6}
    .st-key-material_publish [data-testid=stTextInput] input{font-size:15px}
    .st-key-material_studio [data-testid=stExpander] details{background:#111711!important;border-color:#ffffff1a!important;box-shadow:none!important}
    @media(max-width:600px){.st-key-material_content,.st-key-material_publish{padding:15px!important}}
    </style>""")
    with st.container(key='material_studio'):
        st.subheader('Treino e provas',anchor=False)
        notice_slot=st.empty()
        if notice:=st.session_state.pop('prep_material_notice',None):notice_slot.success(notice)
        st.caption('Revise os materiais, arraste para as etapas e confira a trilha abaixo.')
        prefix='prep_material_'+student
        # Preserve input drafts while the other tab is lazily rendered.
        for suffix in ('kind','title','instructions','source','course','line','side_line','side_game',
                       'pgn_line','pgn_game','fen','uci','theme','puzzle_search','chosen_puzzles',
                       'question_count','publish'):
            key=prefix+'_'+suffix
            if key in st.session_state:st.session_state[key]=st.session_state[key]
        for key in list(st.session_state):
            if key.startswith(prefix+'_q_'):st.session_state[key]=st.session_state[key]
        create,library=st.tabs(['Preparar material','Materiais e correções'],key=prefix+'_tabs',on_change='rerun')
        with create:
            if create.open:_prepare_material(token,student,prefix)
        with library:
            if library.open:_material_library(token,student,prefix)


def _prepare_material(token,student,prefix):
    from classroom_trail_board import render_builder
    render_builder(token,student,[],False,LABELS)


def _material_library(token,student,prefix):
    items=materials.list_materials(token,student)
    if not items:st.caption('Nenhum material preparado para este aluno.')
    for item in items:
        key=prefix+'_'+item['id']
        with st.expander(LABELS[item['kind']]+' · '+item['title']+(' · Disponível' if item['published'] else ' · Oculto'),key=key+'_entry',on_change='rerun') as entry:
            if not entry.open:continue
            st.write(item['payload'].get('instructions',''))
            if st.button('Ocultar do aluno' if item['published'] else 'Disponibilizar ao aluno',key=key+'_visibility'):
                materials.set_published(token,item['id'],not item['published']);st.rerun()
            if item['kind']=='exam':_teacher_grade(token,item,key)
            elif item['kind']=='note':st.write(item['payload']['text'])
            elif item['kind']=='video':_video_player(token,item['payload'],key+'_video',room=item['room'])
            else:
                progress=item['progress']
                if progress:st.caption(('Concluído' if progress['completed'] else 'Em treino')+f" · {progress['errors']} erros registrados")
                _preview(item['payload'],item['kind'],key+'_view')


def _teacher_grade(token,item,key):
    result=item['result'];questions=item['payload']['questions']
    if not result:
        st.caption('Aguardando envio do aluno.')
        for i,q in enumerate(questions):
            st.write(f"{i+1}. {q['prompt']}")
            st.caption('Gabarito: '+(q['options'][q['answer']] if q['kind']=='closed' else q['answer'] or 'Correção manual'))
        return
    st.metric('Nota',f"{result['score']:g} / {result['maximum']:g}")
    st.caption(f"{result['pending']} questões aguardam correção manual.")
    with st.form(key+'_grade'):
        scores=[];notes=[]
        for i,(q,answer) in enumerate(zip(questions,result['questions'])):
            st.write(f"{i+1}. {q['prompt']}")
            st.text('Resposta: '+(q['options'][answer['answer']] if q['kind']=='closed' else answer['answer']))
            scores.append(st.number_input('Nota da pergunta '+str(i+1),0.,float(q['weight']),float(answer['score'] or 0),step=.5,key=key+f'_score_{i}'))
            notes.append(st.text_area('Comentário do Professor '+str(i+1),value=answer['feedback'],key=key+f'_feedback_{i}',height=80))
        if st.form_submit_button('Salvar correção'):
            try:
                materials.grade_exam(token,item['id'],scores,notes)
                st.session_state.prep_material_notice='Correção salva.'
                st.rerun()
            except (PermissionError,ValueError) as error:st.error(str(error))


@st.fragment(run_every='3s')
def _watch_student_trail(token):
    from classroom_trails import student_trail
    signature=json.dumps(student_trail(token),sort_keys=True)
    key='prep_trail_watch_'+hashlib.sha256(token.encode()).hexdigest()[:16]
    before=st.session_state.get(key)
    st.session_state[key]=signature
    if before is not None and before!=signature:st.rerun()


def _video_player(token,payload,key,room=None,material=None):
    import classroom_community as community
    cache='prep_active_material_video'
    session_key=key+'_'+hashlib.sha256(token.encode()).hexdigest()[:12]
    active=st.session_state.get(cache)
    if material:
        try:materials.authorized_video(token,material)
        except PermissionError:
            st.session_state.pop(cache,None)
            st.info('Esta etapa aguarda a liberação do Professor.');return
    metadata=next((video for video in community.videos(token,room) if video['id']==payload['video_id']),None)
    if not metadata:
        if active and active['owner']==session_key:st.session_state.pop(cache,None)
        st.warning('Vídeo indisponível nesta sala.');return
    if active and active['owner']==session_key and active['video_id']!=payload['video_id']:
        st.session_state.pop(cache,None)
    if st.button('Assistir ao vídeo',key=session_key+'_watch',icon=':material/play_arrow:'):
        try:
            source=community.video_media(token,payload['video_id'],room) or metadata['url']
            st.session_state[cache]=dict(owner=session_key,video_id=payload['video_id'],source=source)
        except PermissionError:st.warning('Vídeo indisponível.');return
    active=st.session_state.get(cache)
    if active and active['owner']==session_key and active['video_id']==payload['video_id']:
        st.video(active['source'],autoplay=False)
        if st.button('Fechar vídeo',key=session_key+'_close'):
            st.session_state.pop(cache,None);st.rerun()


def student_materials(token):
    _watch_student_trail(token)
    items=materials.list_materials(token)
    if previous:=st.session_state.pop('prep_next_after',None):
        from classroom_trails import student_trail
        steps=student_trail(token);ordered=[(step['id'],identifier) for step in steps for identifier in step['materials']]
        at=next((index for index,(_,identifier) in enumerate(ordered) if identifier==previous),None)
        if at is None:
            legacy=[i['id'] for i in items if i['id'] not in {identifier for _,identifier in ordered}]
            if previous in legacy and legacy.index(previous)+1<len(legacy):
                st.session_state.prep_student_material=legacy[legacy.index(previous)+1]
        if at is not None and at+1<len(ordered) and not next(step for step in steps if step['id']==ordered[at+1][0])['blocked']:
            stage,identifier=ordered[at+1]
            st.session_state.prep_student_selected_step=stage;st.session_state.prep_student_material=identifier
    from classroom_trail_student import select_step
    items,waiting=select_step(token,items)
    if waiting:
        st.session_state.pop('prep_active_material_video',None);return
    if not items:st.info('O Professor ainda não disponibilizou materiais para você.');return
    choices={i['id']:i for i in items}
    if st.session_state.get('prep_student_material') not in choices:st.session_state.prep_student_material=next(iter(choices))
    selected=st.selectbox('Material da aula',list(choices),format_func=lambda k:LABELS[choices[k]['kind']]+' · '+choices[k]['title'],key='prep_student_material')
    item=choices[selected]
    if item['kind']!='video':st.session_state.pop('prep_active_material_video',None)
    st.subheader(item['title'],anchor=False)
    st.write(item['payload'].get('instructions',''))
    if item['kind']=='note':st.write(item['payload']['text'])
    elif item['kind']=='exam':_student_exam(token,item)
    elif item['kind']=='video':_video_player(token,item['payload'],'prep_student_video_'+item['id'],room=item['room'],material=item['id'])
    elif item['kind']=='game':
        _preview(item['payload'],'game','prep_game_'+item['id'])
        if st.button('Abrir esta partida na análise',icon=':material/analytics:',key='prep_analyze_'+item['id']):
            st.session_state.prep_analysis_material=item['id']
            st.session_state.requested_page='Análise'
            st.rerun()
    elif item['kind']=='tactic' and 'puzzles' in item['payload']:
        from classroom_tactic_block_ui import render_block
        render_block(item['payload'],'prep_tactic_block_'+item['id'],token,item['id'])
    else:assigned_training(token,item)
    if item['kind'] in ('note','video','game') and st.button('Concluir e continuar',key='prep_continue_'+item['id']):
        st.session_state.prep_next_after=item['id'];st.rerun()


def _student_exam(token,item,simulation=False,on_complete=None):
    key=('prep_exam_preview_' if simulation else 'prep_exam_')+item['id'];result=st.session_state.get(key+'_result') if simulation else item['result'];questions=item['payload']['questions']
    if result:
        st.success(f"Prova enviada · {result['score']:g}/{result['maximum']:g} pontos"+(' · Nota parcial' if result['pending'] else ''))
        if result['pending']:st.caption(f"{result['pending']} perguntas aguardam o Professor.")
        for i,(q,answer) in enumerate(zip(questions,result['questions'])):
            with st.container(border=True):
                st.write(f"{i+1}. {q['prompt']}")
                st.text('Sua resposta: '+(q['options'][answer['answer']] if q['kind']=='closed' else answer['answer']))
                st.caption('Aguardando correção' if answer['score'] is None else f"{answer['score']:g}/{q['weight']:g} pontos")
                if answer['feedback']:st.write(answer['feedback'])
        return
    with st.form(key):
        answers=[]
        for i,q in enumerate(questions):
            st.markdown(f"**{i+1}. {q['prompt']}**")
            if q['kind']=='closed':answers.append(st.radio('Escolha uma alternativa',list(range(len(q['options']))),format_func=lambda n,options=q['options']:options[n],index=None,key=key+f'_{i}'))
            else:answers.append(st.text_area('Sua resposta',key=key+f'_{i}'))
        st.caption('Ao enviar, as respostas ficam registradas e não podem ser reenviadas.')
        if st.form_submit_button('Entregar prova',type='primary'):
            try:
                if simulation:
                    st.session_state[key+'_result']=materials.evaluate_exam(questions,answers)
                    if on_complete:on_complete()
                else:
                    materials.submit_exam(token,item['id'],answers)
                    st.session_state.prep_next_after=item['id']
                st.rerun(scope='fragment' if simulation else 'app')
            except (ValueError,PermissionError) as error:st.error(str(error))


@st.fragment
def assigned_training(token,item,*,simulation=False,preview_key=None,on_complete=None,on_stop=None):
    from interactive_board import interactive_board
    identifier=item['id'];key=preview_key or 'prep_training_'+identifier;state=st.session_state
    if simulation:
        signature=hashlib.sha256(json.dumps(item['payload'],sort_keys=True).encode()).hexdigest()
        if state.get(key+'_source')!=signature:
            for suffix in ('_marks','_quiz_states','_errors','_feedback','_stopped'):
                state.pop(key+suffix,None)
            state[key+'_source']=signature;state.pop(key+'_ply',None);state.pop(key+'_notice',None);state.pop(key+'_phase',None);state.pop(key+'_quiz',None);state[key+'_revision']=state.get(key+'_revision',0)+1
    board,moves=materials.training_moves(item['payload'],item['kind'])
    side=board.turn if item['kind']=='tactic' else item['payload']['side']=='white'
    initial=1 if board.turn!=side and moves else 0
    progress=state.setdefault(key+'_ply',(item.get('progress') or {}).get('progress',initial))
    phase=state.setdefault(key+'_phase','done' if (item.get('progress') or {}).get('completed') else 'learn')
    if state.get(key+'_stopped'):
        st.success('Treino encerrado. Você pode retomar quando quiser.')
        if st.button('Retomar treino',key=key+'_resume'):
            state.pop(key+'_stopped',None);st.rerun(scope='fragment')
        return
    if item['kind']=='line' and progress==len(moves) and phase!='done':
        if phase=='learn' or phase=='recall' and state.get(key+'_errors',0):
            state[key+'_phase']='recall';state[key+'_errors']=0;state[key+'_marks']={}
            state[key+'_ply']=initial if simulation else materials.restart_training(token,identifier)
            state[key+'_notice']='Repita a linha sem dicas.'
        elif phase=='recall':
            state[key+'_phase']='quiz'
            state[key+'_quiz']=list(reversed(range(initial,len(moves),2)))
            state[key+'_quiz_states']={str(ply):'pending' for ply in range(initial,len(moves),2)}
            state[key+'_ply']=state[key+'_quiz'][0]
            state[key+'_notice']='Quiz: encontre o lance em cada posição.'
        state[key+'_revision']=state.get(key+'_revision',0)+1
        st.rerun()
    for move in moves[:progress]:board.push_uci(move)
    if item['kind']=='line':st.caption(dict(learn='Aprender a linha',recall='Repetir sem dicas',quiz='Quiz de posições',done='Treino finalizado')[phase])
    revision=state.get(key+'_revision',0)
    if progress==len(moves):st.success('Treino concluído!')
    st.caption(('Brancas' if side else 'Pretas')+' · seu lado neste exercício')
    if item['kind']=='line' and phase=='learn':
        from classroom_position_notes import visible_notes
        from classroom_coach_instructor import render_instructor
        notes=visible_notes(item['payload'],progress)
        if notes:render_instructor(notes,key+'_instructor')
    def consume(event):
        if not isinstance(event,dict) or event.get('revision')!=state.get(key+'_revision',0):return False
        try:
            result=(materials.check_prepared_move(item['payload'],item['kind'],state[key+'_ply'],event['uci'],event['fen']) if simulation or phase=='quiz'
                    else materials.check_training(token,identifier,state[key+'_ply'],event['uci'],event['fen'],finalize=item['kind']!='line'))
            mark_key=str(state[key+'_ply'])
            state.setdefault(key+'_marks',{})[mark_key]='correct' if result['correct'] else 'wrong'
            state[key+'_feedback']=dict(correct=result['correct'],uci=event['uci'])
            if not result['correct']:state[key+'_errors']=state.get(key+'_errors',0)+1
            if phase=='quiz':
                queue=state[key+'_quiz']
                from opening_repetition import next_status
                marks=state.setdefault(key+'_quiz_states',{})
                marks[mark_key]=next_status(marks.get(mark_key,'pending'),result['correct'])
                if marks[mark_key]=='correct':
                    if len(queue)==1 and not simulation:materials.finish_line_training(token,identifier)
                    queue.pop(0)
                elif len(queue)>1:queue.append(queue.pop(0))
                result['progress']=queue[0] if queue else len(moves)
                result['completed']=not queue
                if not queue:state[key+'_phase']='done'
            state[key+'_ply']=result['progress'];state[key+'_notice']='Correto!' if result['correct'] else 'Tente outra ideia.'
            state[key+'_revision']=state.get(key+'_revision',0)+1
            if result['completed'] and item['kind']!='line':
                if on_complete:on_complete()
                elif not simulation:
                    state.prep_next_after=identifier;st.rerun(scope='app')
        except (ValueError,PermissionError) as error:
            state[key+'_notice']=str(error);state[key+'_revision']=state.get(key+'_revision',0)+1
        return True
    def render_board():
        return interactive_board(board,flip=not side,on_move=lambda:None,on_sync=lambda:None,key=key+'_board',revision=revision,
                      disabled=progress==len(moves),stable_board=True,training_mode=True,
                      training_expected=moves[progress] if progress<len(moves) else None,
                      hint_move=moves[progress] if item['kind']=='line' and phase=='learn' and progress<len(moves) else None,
                      training_feedback=state.get(key+'_feedback'),
                      dark=True,table=False,show_coordinates=True)
    if item['kind']=='line':
        from html import escape
        from opening_reference_style import CSS
        from opening_lesson_marks import lesson_marks
        st.html('<style>'+CSS+'</style>')
        line=dict(moves=moves,side='white' if side else 'black',context_plies=initial)
        session=dict(mode='quiz' if phase in ('quiz','done') else phase,
                     marks=state.get(key+'_marks',{}),quiz_states=state.get(key+'_quiz_states',{}))
        message=state.get(key+'_notice') or ('Jogue o lance indicado pela seta verde' if phase=='learn' else 'Jogue o lance que você aprendeu')
        if phase=='done':message='Bom trabalho!'
        with st.container(key='opening_lesson_columns'):
            left,right=st.columns([1.65,1],gap='large',vertical_alignment='center')
            with left:
                with st.container(key='opening_lesson_board',gap='xsmall'):
                    result=render_board()
                    tone='success' if phase=='done' or message=='Correto!' else ''
                    st.html(f'<div class="reference-feedback {tone}" role="status" aria-live="polite">{escape(message)}</div>')
            with right:
                with st.container(key='opening_lesson_side'):
                    lesson_marks(line,session)
                    label='Siga a seta verde.' if phase=='learn' else 'Sua vez. Jogue o lance que você aprendeu.'
                    if phase=='quiz':label='Quiz · Resolva as posições fora de ordem. As posições com erro serão repetidas.'
                    if phase=='done':label='Quiz concluído. Todas as posições foram acertadas.'
                    st.html('<p class="reference-side-label">'+label+'</p>')
    else:
        result=render_board()
        if state.get(key+'_notice'):st.caption(state[key+'_notice'])
    if item['kind']=='line' and phase=='done':
        st.info('Linha concluída. Quer continuar para a próxima linha ou parar por aqui?')
        with st.container(horizontal=True):
            if st.button('Continuar para a próxima linha',key=key+'_continue',type='primary',disabled=simulation and on_complete is None):
                if on_complete:on_complete()
                elif not simulation:
                    state.prep_next_after=identifier;st.rerun(scope='app')
            if st.button('Parar por aqui',key=key+'_stop'):
                if on_stop:on_stop()
                else:
                    state[key+'_stopped']=True;st.rerun(scope='fragment')
    if state.get(key+'_stopped'):st.success('Treino encerrado. Você pode retomar quando quiser.')
    if st.button('Recomeçar esta linha' if item['kind']=='line' else 'Recomeçar este tático',key=key+'_restart'):
        state[key+'_phase']='learn';state[key+'_errors']=0;state.pop(key+'_quiz',None)
        for suffix in ('_marks','_quiz_states','_feedback','_stopped'):state.pop(key+suffix,None)
        state[key+'_ply']=initial if simulation else materials.restart_training(token,identifier);state[key+'_revision']=revision+1;state.pop(key+'_notice',None);st.rerun(scope='fragment')
    for field in ('move','sync'):
        if consume(getattr(result,field,None)):st.rerun(scope='fragment')
