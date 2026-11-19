"""Activity fields reused inside the selected line editor."""
import chess
import chess.pgn
import streamlit as st
import classroom_materials as materials


def content_inputs(token,student,prefix,kind,instructions,previous=None,position_notes=None,saved_tactics=None):
    from classroom_materials_ui import _preview,_video_player,LABELS
    payload=None;selected=[];choices={}
    if kind in ('line','game'):
        side='white'
        options=['Catálogo de aberturas','PGN personalizado']+(['Continuar linha anterior'] if previous else [])
        if st.session_state.get(prefix+'_source') not in options:st.session_state[prefix+'_source']=options[0]
        source=st.segmented_control('Usar conteúdo de',options,key=prefix+'_source') if kind=='line' else 'PGN personalizado'
        start=0
        if source=='Continuar linha anterior' and st.session_state.get(prefix+'_last_source')!=source:
            st.session_state[prefix+'_move_count']=2
            st.session_state[prefix+'_side_line']=previous['payload'].get('side','white')
        st.session_state[prefix+'_last_source']=source
        if kind=='line':
            side_column,count_column=st.columns(2)
            side=side_column.segmented_control('Lado que o aluno vai treinar',['white','black'],format_func=lambda value:'Brancas' if value=='white' else 'Pretas',default='white',key=prefix+'_side_line') or 'white'
            count=count_column.number_input('Quantos lances neste bloco?',min_value=1,max_value=100,step=1,key=prefix+'_move_count',value=5,help='Um lance inclui brancas e pretas. O bloco termina antes se a sequência acabar.')
        if source=='Continuar linha anterior':
            prior=previous['payload']
            start=prior.get('start_ply',0)+len(list(materials.parse_pgn(prior['pgn']).mainline_moves()))
            st.caption('Continuação de '+previous['title']+' · começa na posição final do bloco anterior.')
            source_key=prefix+'_continuation_source'
            prior_signature=prior.get('source_pgn',prior['pgn'])+'|'+str(start)
            if st.session_state.get(prefix+'_prior_signature')!=prior_signature:
                st.session_state[source_key]=prior.get('source_pgn',prior['pgn'])
                st.session_state[prefix+'_prior_signature']=prior_signature
                st.session_state.pop(prefix+'_continuation_pgn',None)
            from classroom_line_segments import extend_sequence
            try:
                if len(list(materials.parse_pgn(st.session_state[source_key]).mainline_moves()))<start+2*count:
                    st.session_state[source_key+'_suggested']=True
            except ValueError:pass
            if st.session_state.get(source_key+'_suggested'):
                st.caption('Continuação sugerida pelo Stockfish local. Você pode editar os novos lances abaixo.')
            try:
                with st.spinner('Preparando a continuação da linha…'):
                    st.session_state[source_key]=extend_sequence(st.session_state[source_key],start+2*count)
            except ValueError as error:st.warning(str(error))
            def keep_continuation():st.session_state[source_key]=st.session_state[prefix+'_continuation_pgn']
            with st.expander('Ver ou ampliar a sequência completa',on_change='rerun') as complete:
                if complete.open:
                    st.text_area('Linha completa (PGN)',value=st.session_state[source_key],key=prefix+'_continuation_pgn',height=180,on_change=keep_continuation)
                    st.caption('Mantenha os lances anteriores e acrescente os próximos ao final.')
            pgn=st.session_state[source_key]
        elif source=='Catálogo de aberturas' or kind=='line' and not source:
            from opening_repertoires import catalog
            courses={c['id']:c for c in catalog() if c['side']==side}
            course_key=prefix+'_course'
            if st.session_state.get(course_key) not in courses:
                previous_course=st.session_state.get(course_key,'')
                related=([previous_course.removesuffix('_white'),previous_course+'_black'] if side=='black'
                         else [previous_course.removesuffix('_black'),previous_course+'_white'])
                st.session_state[course_key]=next((key for key in related if key in courses),next(iter(courses)))
            opening_column,variation_column=st.columns(2)
            course=opening_column.selectbox('Abertura',list(courses),format_func=lambda k:courses[k]['title'],key=prefix+'_course')
            lines=courses[course]['lines'];lookup={line['id']:line for line in lines}
            if st.session_state.get(prefix+'_line') not in lookup:st.session_state[prefix+'_line']=next(iter(lookup))
            selected_line=variation_column.selectbox('Linha exata que será treinada',list(lookup),format_func=lambda k:lookup[k].get('variation') or f"Linha {list(lookup).index(k)+1}",key=prefix+'_line')
            line=lookup[selected_line];game=chess.pgn.Game();node=game
            for move in line['moves']:node=node.add_variation(chess.Move.from_uci(move))
            pgn=str(game)
        else:
            if kind=='game':
                side=st.segmented_control('Lado que o aluno vai treinar',['white','black'],format_func=lambda value:'Brancas' if value=='white' else 'Pretas',default='white',key=prefix+'_side_'+kind) or 'white'
            upload=st.file_uploader('Importar PGN',type=['pgn'],key=prefix+'_upload_'+kind)
            text=st.text_area('PGN com lances e comentários',height=180,key=prefix+'_pgn_'+kind,placeholder='1. e4 {Controle do centro} e5 2. Nf3 Nc6 *')
            pgn=upload.getvalue().decode('utf-8-sig',errors='replace') if upload else text
        payload=dict(pgn=pgn,side=side,instructions=instructions)
        if kind=='line':
            if pgn:
                from classroom_line_segments import segment
                try:
                    payload=segment(pgn,start,count,side,instructions,previous['payload'] if source=='Continuar linha anterior' else None)
                    payload['continuation']=source=='Continuar linha anterior'

                except ValueError as error:st.warning(str(error));payload=None
        if pgn and payload:
            try:
                materials.validate(kind,payload)
                from classroom_position_notes import notes_state,edit_position_notes
                frames,cache=notes_state(payload,prefix,position_notes)
                with st.expander('Conferir tabuleiro e comentários',key=prefix+'_preview_drawer_'+kind,on_change='rerun',icon=':material/visibility:') as preview:
                    if preview.open:edit_position_notes(payload,prefix,frames,cache)
            except ValueError as error:st.caption(str(error))
        save_label='Disponibilizar '+LABELS[kind].lower()
    elif kind=='tactic':
        from classroom_tactic_inputs import tactic_inputs
        payload=tactic_inputs(prefix,instructions,saved_tactics)
    elif kind=='video':
        import classroom_trails as trails
        import classroom_community as community
        room,available=trails.video_catalog(token,student)
        if new:=st.session_state.pop(prefix+'_new_video',None):st.session_state[prefix+'_video_id']=new
        if available:
            videos={video['id']:video for video in available}
            selected_video=st.selectbox('Vídeo da sala',list(videos),format_func=lambda identifier:videos[identifier]['title'],key=prefix+'_video_id')
            payload=dict(video_id=selected_video,instructions=instructions)
            with st.expander('Assistir à prévia',key=prefix+'_video_preview_open',on_change='rerun') as preview:
                if preview.open:_video_player(token,payload,prefix+'_video_preview',room=room)
        else:st.caption('Adicione um vídeo da aula para anexar a uma etapa.')
        with st.expander('Adicionar vídeo à sala'):
            video_title=st.text_input('Nome do vídeo',key=prefix+'_video_title')
            upload=st.file_uploader('Arquivo de vídeo',type=['mp4','webm','mov'],max_upload_size=100,key=prefix+'_video_upload')
            url=st.text_input('Ou link HTTPS',key=prefix+'_video_url')
            if st.button('Guardar vídeo na sala',key=prefix+'_save_video'):
                try:
                    mime={'mp4':'video/mp4','webm':'video/webm','mov':'video/quicktime'}.get(upload.name.rsplit('.',1)[-1].lower(),'') if upload else ''
                    identifier=community.publish_video(token,video_title,url=url,media=upload.getbuffer() if upload else None,mime=mime,room=room)
                    st.session_state[prefix+'_new_video']=identifier;st.rerun()
                except (ValueError,PermissionError) as error:st.error(str(error))
        save_label='Disponibilizar vídeo'
    elif kind=='note':
        payload=dict(text=st.text_area('Anotação',height=180,key=prefix+'_note'),instructions=instructions)
    else:
        count=st.number_input('Quantidade de perguntas',1,50,1,key=prefix+'_question_count')
        questions=[]
        for i in range(int(count)):
            key=prefix+'_q_'+str(i)
            with st.container(border=True):
                st.markdown(f'**Pergunta {i+1}**')
                closed=st.segmented_control('Formato',['Aberta','Fechada'],default='Aberta',key=key+'_kind')=='Fechada'
                prompt=st.text_area('Enunciado',key=key+'_prompt',height=90)
                options=[]
                if closed:
                    saved=st.session_state.get(key+'_options','').splitlines()
                    st.session_state.setdefault(key+'_option_count',max(2,len(saved)))
                    size=st.number_input('Quantidade de alternativas',2,8,key=key+'_option_count')
                    for n in range(int(size)):
                        st.session_state.setdefault(key+f'_option_{n}',saved[n] if n<len(saved) else '')
                        options.append(st.text_input(f'Alternativa {chr(65+n)}',key=key+f'_option_{n}'))
                    if st.session_state.get(key+'_correct') not in range(len(options)):
                        st.session_state[key+'_correct']=None
                    answer=st.radio('Alternativa correta',range(len(options)),format_func=lambda n:chr(65+n),index=None,key=key+'_correct',horizontal=True)
                else:
                    with st.expander('Gabarito para correção automática'):
                        st.caption('Separe respostas aceitas por |. Sem gabarito, a correção é manual; não há avaliação semântica.')
                        answer=st.text_area('Gabarito / respostas aceitas (opcional)',key=key+'_answer',height=90)
                weight=st.number_input('Pontos',min_value=1,max_value=100,value=1,key=key+'_weight')
                questions.append(dict(kind='closed' if closed else 'open',prompt=prompt,weight=weight,options=options,answer=answer))
        payload=dict(questions=questions,instructions=instructions);save_label='Salvar prova'
    if payload is None and selected:
        puzzle=choices[selected[0]]
        payload=dict(fen=puzzle.fen,solution=list(puzzle.solution),source='Lichess · '+puzzle.id,instructions=instructions)
    return payload
