"""Nonblocking local preparation of the next opening level."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import streamlit as st
from opening_levels import prepare_level
from opening_training_state import lines_for


@st.cache_resource
def worker():
    return ThreadPoolExecutor(max_workers=1,thread_name_prefix='opening-levels')


def request_level(plan,line,target,auto_start=False):
    state=st.session_state
    if state.get('openings_level_job'): return
    state.openings_level_job=dict(owner=plan['username'],course=list(plan['repertoire_ids']),
        future=worker().submit(prepare_level,deepcopy(plan),deepcopy(line),target),auto_start=auto_start)


def render_levels(plan,save,start):
    state=st.session_state
    job=state.get('openings_level_job')
    if job:
        if job['owner']!=plan['username'] or job['course']!=plan['repertoire_ids']:
            job['future'].cancel();state.pop('openings_level_job',None)
        else:
            @st.fragment(run_every=.5)
            def monitor():
                if not job['future'].done():
                    st.info('Preparando a continuação com Stockfish local…')
                    return
                state.pop('openings_level_job',None)
                try:
                    line=job['future'].result()
                    extensions=plan.setdefault('course_extensions',[])
                    if not any(item['id']==line['id'] for item in extensions): extensions.append(line)
                    save(plan)
                    state.pop('openings_level_error',None)
                    if job['auto_start']: start(line['id'],'train')
                except Exception as error:
                    state.openings_level_error=str(error)
                st.rerun()
            monitor()
    if error:=state.get('openings_level_error'): st.warning(error)
    lessons=list(lines_for(plan).values())
    from opening_rounds import cycle,next_lesson,target,quiz_target,phase_number
    if cycle(plan) is not None:
        if phase_number(plan)>50:
            st.success('Trilha concluída · 50 fases. Suas revisões continuam disponíveis.')
            return
        available,source=next_lesson(plan,lessons)
        level,quota=quiz_target(plan)
        with st.expander('Continuar a trilha',icon=':material/route:'):
            st.caption(f'Fase {min(50,phase_number(plan))} de 50 · {level} lances · {quota} desafios.')
            if source and st.button(f"Continuar · linha {source['branch']}",disabled=bool(state.get('openings_level_job'))):
                if available: start(available['id'],'train')
                else: request_level(plan,source,level,auto_start=True)
                st.rerun()
        return
    foundations=[line for line in lessons if line.get('stage')=='foundation']
    progress=plan.get('practice_progress',{})
    if not foundations or not all(progress.get(line['id'],{}).get('learned') for line in foundations): return
    with st.expander('Aprofundar uma linha',icon=':material/route:'):
        st.caption('5 → 7 → 9 → 11 → 13 lances, avançando de dois em dois. Preparação local e offline.')
        for root in foundations:
            learned=[line for line in lessons if line.get('branch')==root['branch'] and progress.get(line['id'],{}).get('learned')]
            source=max(learned,key=lambda line:line.get('lesson_moves',5))
            target=source.get('lesson_moves',5)+2
            available=next((line for line in lessons if line.get('branch')==root['branch'] and line.get('lesson_moves')==target),None)
            remaining=[line for line in lessons if line.get('branch')==root['branch'] and not progress.get(line['id'],{}).get('learned')]
            if remaining and remaining[0].get('lesson_moves',target)<=target:
                available=remaining[0]
                target=available['lesson_moves']
            if st.button(f"Linha {root['branch']} · {target} lances",key=f"opening_deepen_{root['branch']}",disabled=bool(state.get('openings_level_job'))):
                if available: start(available['id'],'train')
                else: request_level(plan,source,target,auto_start=True)
                st.rerun()
