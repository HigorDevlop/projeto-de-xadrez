"""Position-bound teaching instructions shared by authoring and student training."""
import hashlib
import chess


def positions(pgn):
    from classroom_materials import parse_pgn
    game=parse_pgn(pgn);board=game.board()
    frames=[dict(fen=board.fen(),label='Posição inicial',comment=game.comment)]
    for node in game.mainline():
        label=str(board.fullmove_number)+('. ' if board.turn else '... ')+board.san(node.move)
        board.push(node.move)
        frames.append(dict(fen=board.fen(),label='Após '+label,comment=node.comment))
    return frames


def validate_notes(pgn,notes):
    if not isinstance(notes,list) or len(notes)>501:raise ValueError('Use até 501 instruções por atividade.')
    frames=positions(pgn);seen=set();result=[]
    for note in notes:
        if not isinstance(note,dict):raise ValueError('Instrução de posição inválida.')
        ply=note.get('ply');text=note.get('text')
        if type(ply) is not int or not 0<=ply<len(frames) or ply in seen or note.get('fen')!=frames[ply]['fen']:
            raise ValueError('A instrução não corresponde à posição da linha.')
        if not isinstance(text,str) or not text.strip() or len(text)>5000:raise ValueError('Escreva uma instrução de até 5 mil caracteres por posição.')
        seen.add(ply);result.append(dict(ply=ply,fen=frames[ply]['fen'],text=text.strip()))
    return sorted(result,key=lambda note:note['ply'])


def visible_notes(payload,ply):
    frames=positions(payload['pgn']);notes={note['ply']:note['text'] for note in payload.get('position_notes',[])}
    result=[]
    for index in range(max(0,ply-1),min(ply+1,len(frames))):
        frame=frames[index];text=notes.get(index) or frame['comment']
        if text:result.append(dict(label=frame['label'],text=text))
    return result


def notes_state(payload,key,saved_notes):
    import streamlit as st
    frames=positions(payload['pgn']);cache=key+'_position_notes'
    st.session_state.setdefault(cache,{note['fen']:note['text'] for note in saved_notes or []})
    notes=st.session_state[cache]
    payload['position_notes']=[dict(ply=ply,fen=frame['fen'],text=notes[frame['fen']]) for ply,frame in enumerate(frames) if notes.get(frame['fen'],'').strip()]
    return frames,cache


def edit_position_notes(payload,key,frames,cache):
    import streamlit as st
    from interactive_board import interactive_board
    slider=key+'_annotation_ply'
    if st.session_state.get(slider,0)>=len(frames):st.session_state[slider]=0
    ply=st.slider('Percorrer lances para anotar',0,len(frames)-1,0,key=slider)
    frame=frames[ply]
    board_column,note_column=st.columns([1.25,1],gap='medium')
    with board_column:
        board=chess.Board(frame['fen'])
        interactive_board(board,key=key+'_annotation_board',on_move=lambda:None,disabled=True,revision=ply,
                          stable_board=True,flip=payload.get('side')=='black',dark=True,table=False,show_coordinates=True)
        st.caption(frame['label']+' · '+('Brancas jogam' if board.turn else 'Pretas jogam'))
    with note_column:
        st.markdown('**'+frame['label']+'**')
        if frame['comment']:st.caption(frame['comment'])
        widget=key+'_instruction_'+hashlib.sha256(frame['fen'].encode()).hexdigest()[:16]
        def keep_note():st.session_state[cache][frame['fen']]=st.session_state[widget]
        st.text_area('Instrução nesta posição',value=st.session_state[cache].get(frame['fen'],''),height=180,key=widget,
                     on_change=keep_note,placeholder='Explique o plano, a ameaça ou o motivo deste lance.',max_chars=5000)
        st.caption('A instrução acompanha esta posição para o aluno. Confirme em Salvar atividade.')
        from classroom_fischer_instructor import render_instructor
        text=st.session_state[cache].get(frame['fen'],'').strip() or frame['comment']
        render_instructor([dict(label=frame['label'],text=text)] if text else [],key+'_instructor')
    payload['position_notes']=[dict(ply=at,fen=entry['fen'],text=st.session_state[cache][entry['fen']]) for at,entry in enumerate(frames) if st.session_state[cache].get(entry['fen'],'').strip()]
