"""Teacher-authored lessons, selected tactics, studied games and exams."""
from io import StringIO
import chess
import chess.pgn
import streamlit as st
import classroom_materials as materials

LABELS={'line':'Linha de treino','tactic':'Tático','game':'Partida estudada','exam':'Prova'}


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
    if node and node.comment:st.info(node.comment)
    st.caption('Brancas jogam' if board.turn else 'Pretas jogam')


def teacher_materials(token,student):
    st.subheader('Treino e provas',anchor=False)
    if notice:=st.session_state.pop('prep_material_notice',None):st.success(notice)
    st.caption('Prepare o conteúdo deste aluno. Ele só terá acesso dentro da sala, com a chave fornecida pelo Professor.')
    prefix='prep_material_'+student
    create,library=st.tabs(['Preparar material','Materiais e correções'],key=prefix+'_tabs',on_change='rerun')
    with create:
        kind=st.segmented_control('Tipo de material',list(LABELS),format_func=LABELS.get,default='line',key=prefix+'_kind') or 'line'
        title=st.text_input('Título da aula ou prova',key=prefix+'_title')
        instructions=st.text_area('Orientações para o aluno',key=prefix+'_instructions',height=90)
        if kind in ('line','game'):
            side='white'
            if kind=='line':
                source=st.radio('Origem da linha',['Catálogo de aberturas','PGN personalizado'],horizontal=True,key=prefix+'_source')
            else:source='PGN personalizado'
            if source=='Catálogo de aberturas':
                from opening_repertoires import catalog
                courses={c['id']:c for c in catalog()}
                course=st.selectbox('Abertura',list(courses),format_func=lambda k:courses[k]['title'],key=prefix+'_course')
                lines=courses[course]['lines'];lookup={l['id']:l for l in lines}
                selected=st.selectbox('Linha exata que será treinada',list(lookup),format_func=lambda k:lookup[k].get('variation') or f"Linha {list(lookup).index(k)+1} · {len(lookup[k]['moves'])} meios-lances",key=prefix+'_line')
                line=lookup[selected];game=chess.pgn.Game();node=game
                for move in line['moves']:node=node.add_variation(chess.Move.from_uci(move))
                pgn=str(game);side=line['side']
                st.caption('Lado do aluno: '+('Brancas' if side=='white' else 'Pretas')+'. Esta linha específica será treinada, sem substituição por outra abertura.')
            else:
                side=st.selectbox('Lado que o aluno vai treinar',['white','black'],format_func=lambda s:'Brancas' if s=='white' else 'Pretas',key=prefix+'_side_'+kind)
                upload=st.file_uploader('Importar PGN',type=['pgn'],key=prefix+'_upload_'+kind)
                text=st.text_area('PGN com lances e comentários',height=180,key=prefix+'_pgn_'+kind,
                                  placeholder='1. e4 {Controle do centro} e5 2. Nf3 Nc6 *')
                pgn=upload.getvalue().decode('utf-8-sig',errors='replace') if upload else text
            payload=dict(pgn=pgn,side=side,instructions=instructions)
            if pgn:
                try:
                    materials.validate(kind,payload)
                    with st.expander('Conferir tabuleiro e comentários'):_preview(payload,kind,prefix+'_preview_'+kind)
                except ValueError as error:st.caption(str(error))
            if st.button('Disponibilizar '+LABELS[kind].lower(),type='primary',key=prefix+'_save_'+kind):_save(token,student,title,kind,payload)
        elif kind=='tactic':
            from tactics import THEMES
            mode=st.radio('Origem dos táticos',['Escolher no banco offline','Criar uma posição'],horizontal=True,key=prefix+'_tactic_source')
            if mode=='Escolher no banco offline':
                theme=st.selectbox('Tema da aula',list(THEMES.values()),format_func=lambda k:next(n for n,v in THEMES.items() if v==k),key=prefix+'_theme')
                search=st.text_input('Buscar pelo código do exercício',key=prefix+'_puzzle_search')
                puzzles=[p for p in materials.local_puzzles(theme) if search.casefold() in p.id.casefold()]
                choices={p.id:p for p in puzzles[:200]}
                st.caption(f'{len(puzzles)} exercícios encontrados. Exibindo até 200; filtre pelo código para encontrar outros.')
                selected=st.multiselect('Táticos escolhidos pelo Professor',list(choices),format_func=lambda k:f'{k} · rating {choices[k].rating}',max_selections=50,key=prefix+'_chosen_puzzles')
                if selected:
                    focus=st.selectbox('Visualizar exercício selecionado',selected,key=prefix+'_puzzle_preview')
                    p=choices[focus]
                    with st.expander('Posição e solução',expanded=True):_preview(dict(fen=p.fen,solution=list(p.solution)),'tactic',prefix+'_preview_tactic')
                if st.button('Disponibilizar táticos selecionados',type='primary',disabled=not selected,key=prefix+'_save_selected'):
                    if not title.strip():st.error('Informe o título da aula.')
                    else:
                        for identifier in selected:
                            p=choices[identifier]
                            _save(token,student,(title+' · '+p.id)[:150],'tactic',dict(fen=p.fen,solution=list(p.solution),source='Lichess · '+p.id,instructions=instructions))
            else:
                fen=st.text_input('Posição FEN (inclui o lado a jogar)',key=prefix+'_fen')
                solution=st.text_input('Solução UCI, separada por espaços',placeholder='e2e4 e7e5 g1f3',key=prefix+'_uci')
                if st.button('Disponibilizar posição',type='primary',key=prefix+'_save_custom'):
                    _save(token,student,title,'tactic',dict(fen=fen,solution=solution.split(),instructions=instructions))
        else:
            st.caption('Fechadas: escolha a alternativa correta. Abertas: respostas aceitas separadas por |, sem distinguir maiúsculas e acentos. Sem gabarito, a questão fica para correção manual. Não há avaliação semântica automática.')
            count=st.number_input('Quantidade de perguntas',1,50,1,key=prefix+'_question_count')
            questions=[]
            for i in range(int(count)):
                key=prefix+'_q_'+str(i)
                with st.container(border=True):
                    st.markdown(f'**Pergunta {i+1}**')
                    closed=st.selectbox('Formato',['Aberta','Fechada'],key=key+'_kind')=='Fechada'
                    prompt=st.text_area('Enunciado',key=key+'_prompt',height=90)
                    weight=st.number_input('Pontos',min_value=1,max_value=100,value=1,key=key+'_weight')
                    options=[]
                    if closed:
                        options=st.text_area('Alternativas (uma por linha)',key=key+'_options',height=100).splitlines()
                        answer=st.selectbox('Alternativa correta',range(len(options)),format_func=lambda n:options[n],index=None,key=key+'_correct') if options else None
                    else:answer=st.text_area('Gabarito / respostas aceitas (opcional)',key=key+'_answer',height=90)
                    questions.append(dict(kind='closed' if closed else 'open',prompt=prompt,weight=weight,options=options,answer=answer))
            publish=st.toggle('Disponibilizar ao aluno agora',value=True,key=prefix+'_publish')
            if st.button('Salvar prova',type='primary',key=prefix+'_save_exam'):_save(token,student,title,'exam',dict(questions=questions,instructions=instructions),publish)
    with library:
        items=materials.list_materials(token,student)
        if not items:st.caption('Nenhum material preparado para este aluno.')
        for item in items:
            key=prefix+'_'+item['id']
            with st.expander(LABELS[item['kind']]+' · '+item['title']+(' · Disponível' if item['published'] else ' · Oculto')):
                st.write(item['payload'].get('instructions',''))
                if st.button('Ocultar do aluno' if item['published'] else 'Disponibilizar ao aluno',key=key+'_visibility'):
                    materials.set_published(token,item['id'],not item['published']);st.rerun()
                if item['kind']=='exam':_teacher_grade(token,item,key)
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


def student_materials(token):
    items=materials.list_materials(token)
    if not items:st.info('O Professor ainda não disponibilizou materiais para você.');return
    choices={i['id']:i for i in items}
    selected=st.selectbox('Material da aula',list(choices),format_func=lambda k:LABELS[choices[k]['kind']]+' · '+choices[k]['title'],key='prep_student_material')
    item=choices[selected]
    st.subheader(item['title'],anchor=False)
    st.write(item['payload'].get('instructions',''))
    if item['kind']=='exam':_student_exam(token,item)
    elif item['kind']=='game':
        _preview(item['payload'],'game','prep_game_'+item['id'])
        if st.button('Abrir esta partida na análise',icon=':material/analytics:',key='prep_analyze_'+item['id']):
            st.session_state.prep_analysis_material=item['id']
            st.session_state.requested_page='Análise'
            st.rerun()
    else:assigned_training(token,item)


def _student_exam(token,item):
    key='prep_exam_'+item['id'];result=item['result'];questions=item['payload']['questions']
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
            try:materials.submit_exam(token,item['id'],answers);st.rerun()
            except (ValueError,PermissionError) as error:st.error(str(error))


@st.fragment
def assigned_training(token,item):
    from interactive_board import interactive_board
    identifier=item['id'];key='prep_training_'+identifier;state=st.session_state
    board,moves=materials.training_moves(item['payload'],item['kind'])
    side=board.turn if item['kind']=='tactic' else item['payload']['side']=='white'
    initial=1 if board.turn!=side and moves else 0
    progress=state.setdefault(key+'_ply',(item.get('progress') or {}).get('progress',initial))
    for move in moves[:progress]:board.push_uci(move)
    revision=state.get(key+'_revision',0)
    if progress==len(moves):st.success('Treino concluído!')
    st.caption(('Brancas' if side else 'Pretas')+' · seu lado neste exercício')
    def consume(event):
        if not isinstance(event,dict) or event.get('revision')!=state.get(key+'_revision',0):return False
        try:
            result=materials.check_training(token,identifier,state[key+'_ply'],event['uci'],event['fen'])
            state[key+'_ply']=result['progress'];state[key+'_notice']='Correto!' if result['correct'] else 'Tente outra ideia.'
            state[key+'_revision']=state.get(key+'_revision',0)+1
        except (ValueError,PermissionError) as error:
            state[key+'_notice']=str(error);state[key+'_revision']=state.get(key+'_revision',0)+1
        return True
    result=interactive_board(board,flip=not side,on_move=lambda:None,on_sync=lambda:None,key=key+'_board',revision=revision,
                      disabled=progress==len(moves),stable_board=True,training_mode=True,
                      training_expected=moves[progress] if progress<len(moves) else None,dark=True,table=False,show_coordinates=True)
    if state.get(key+'_notice'):st.caption(state[key+'_notice'])
    if st.button('Recomeçar esta linha' if item['kind']=='line' else 'Recomeçar este tático',key=key+'_restart'):
        state[key+'_ply']=materials.restart_training(token,identifier);state[key+'_revision']=revision+1;state.pop(key+'_notice',None);st.rerun(scope='fragment')
    for field in ('move','sync'):
        if consume(getattr(result,field,None)):st.rerun(scope='fragment')
