"""Build one tactical activity from any number of offline or custom exercises."""
import streamlit as st
import classroom_materials as materials
from classroom_tactic_blocks import puzzle_id


def tactic_inputs(prefix,instructions,saved=None):
    from classroom_materials_ui import _preview
    cache=prefix+'_tactic_basket'
    st.session_state.setdefault(cache,{puzzle_id(p):dict(p) for p in saved or []})
    st.session_state.setdefault(cache+'_edited',bool(saved))
    basket=st.session_state[cache]
    def add(entries):
        for entry in entries:
            entry=materials.validate('tactic',entry);basket[puzzle_id(entry)]=entry
        st.session_state[cache+'_edited']=True
        st.rerun(scope='fragment')
    mode=st.segmented_control('Usar táticos de',['Escolher no banco offline','Criar uma posição'],default='Escolher no banco offline',key=prefix+'_tactic_source') or 'Escolher no banco offline'
    fallback=[]
    if mode=='Escolher no banco offline':
        from tactics import THEMES
        theme=st.selectbox('Tema da aula',list(THEMES.values()),format_func=lambda key:next(name for name,value in THEMES.items() if value==key),key=prefix+'_theme')
        with st.expander('Buscar exercício pelo código'):
            search=st.text_input('Buscar pelo código do exercício',key=prefix+'_puzzle_search')
        puzzles=[p for p in materials.local_puzzles(theme) if search.casefold() in p.id.casefold()]
        choices={p.id:p for p in puzzles}
        selected=st.multiselect('Táticos escolhidos pelo Professor',list(choices),format_func=lambda key:f'{key} · rating {choices[key].rating}',key=prefix+'_chosen_puzzles')
        fallback=[dict(fen=choices[key].fen,solution=list(choices[key].solution),source='Lichess · '+key) for key in selected]
        if st.button('Adicionar selecionados ao bloco',key=prefix+'_add_puzzles',disabled=not fallback,icon=':material/add:'):add(fallback)
        st.caption(str(len(puzzles))+' disponíveis offline · selecione vários e adicione ao mesmo bloco.')
    else:
        fen=st.text_input('Posição FEN (inclui o lado a jogar)',key=prefix+'_fen')
        solution=st.text_input('Solução UCI, separada por espaços',placeholder='e2e4 e7e5 g1f3',key=prefix+'_uci')
        if fen and solution:fallback=[dict(fen=fen,solution=solution.split(),source='Professor')]
        if st.button('Adicionar posição ao bloco',key=prefix+'_add_custom',disabled=not fallback,icon=':material/add:'):
            try:add(fallback)
            except ValueError as error:st.error(str(error))
    group=list(basket.values()) if st.session_state[cache+'_edited'] else list(basket.values()) or fallback
    st.caption(str(len(group))+' táticos neste bloco · o aluno precisa concluir a rodada com pelo menos 90% sem erro.')
    if group:
        with st.expander('Revisar táticos do bloco',key=prefix+'_review_pack',on_change='rerun') as review:
            if review.open:
                focus=st.selectbox('Exercício do bloco',range(len(group)),format_func=lambda index:str(index+1)+' · '+group[index].get('source','Professor'),key=prefix+'_pack_focus')
                _preview(group[focus],'tactic',prefix+'_pack_view')
                if basket and st.button('Retirar este tático do bloco',key=prefix+'_remove_puzzle'):
                    basket.pop(puzzle_id(group[focus]),None);st.session_state[cache+'_edited']=True;st.rerun(scope='fragment')
    return dict(puzzles=group,instructions=instructions)
