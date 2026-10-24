"""Prepare personal lines in a worker, then reuse the local lesson trainer."""
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from opening_course_state import begin_line, course_lines
from personal_openings import remember_history, prepare, storage_key
from preparation_state import load_plan, save_plan, today


@st.cache_resource
def workers():
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix='personal-openings')


def render_personal_openings(owner, account):
    if not account:
        st.caption('Vincule seu usuário do Chess.com para preparar linhas das suas partidas.')
        return
    key, state = storage_key(owner, account), st.session_state
    with st.expander('Seu repertório · histórico do Chess.com', expanded=True):
        try:
            games = remember_history(owner, account, state.get('history_games', []))
        except OSError:
            st.error('Não foi possível guardar o histórico na pasta de dados.')
            return
        st.caption(f'{account} · {len(games)} partidas importadas e disponíveis offline')
        st.write('Alternativas ao seu jogo: iniciativa, desenvolvimento e solidez, comparadas pelo Stockfish local.')
        quality = st.selectbox('Precisão da preparação', ['Equilibrada', 'Profunda', 'Rápida'], key='personal_opening_quality')
        depth, seconds = {'Rápida':(16,.5), 'Equilibrada':(22,2.0), 'Profunda':(26,5.0)}[quality]
        personal = load_plan(key, namespace='openings')
        job_key = 'personal_opening_job:' + key
        job = state.get(job_key)
        if job is not None:
            @st.fragment(run_every=.5)
            def monitor():
                if not job.done():
                    st.info('Preparando linhas no computador. Você pode continuar usando o aplicativo.')
                    return
                state.pop(job_key, None)
                try:
                    result = job.result()
                    previous = load_plan(key, namespace='openings') or {}
                    identifiers = {line['id'] for line in result['personal_lines']}
                    for field in ('practice_progress', 'retention'):
                        result[field] = {k:v for k,v in previous.get(field,{}).items() if k in identifiers}
                    for field in ('achievements','achievement_progress','quiz_seen','reference_activity'):
                        if field in previous: result[field]=previous[field]
                    save_plan(result, namespace='openings')
                    state.pop('personal_opening_error:'+key, None)
                except Exception as error:
                    state['personal_opening_error:'+key] = str(error)
                st.rerun()
            monitor()
        elif st.button('Preparar linhas do meu histórico', disabled=not games, key='prepare_personal_openings'):
            state[job_key] = workers().submit(prepare, owner, account, games, depth=depth, seconds=seconds)
            st.rerun()
        if error := state.get('personal_opening_error:'+key):
            st.error(error)
        if not personal:
            st.caption('Use Atualizar partidas para importar. Depois de preparar, o treino funciona offline.')
            return
        if personal.get('recommendation_version',1)<2:
            st.info('Prepare novamente o histórico para receber as alternativas com iniciativa e solidez.')
        st.caption(f"Base: {personal['source_games']} partidas · {personal['engine']}. "
                   'Recomendações limitadas pela profundidade alcançada, sem garantia de precisão absoluta.')
        personal['start'] = personal['end'] = str(today())
        for line in course_lines(personal):
            with st.expander(line['variation'] + f" · posição após {line['context_plies']} meios-lances"):
                if line.get('played_san'):
                    st.markdown(f"**Você joga {line['played_san']}** em {line['played_count']}/{line['frequency']} partidas nessa posição.")
                    st.markdown(f"**Sugestão: {line['suggested_san']}** · "+', '.join(line.get('reasons',[])))
                    if line.get('candidate_cp') is not None:
                        def score_label(cp,mate):
                            if mate is not None: return f'mate em {mate}' if mate>0 else f'sofre mate em {abs(mate)}'
                            return f'{cp/100:+.2f}'
                        comparison=('Seu lance: '+score_label(line['played_cp'],line.get('played_mate'))+' · ' if line.get('played_cp') is not None else '')
                        st.caption(comparison+'Sugestão: '+score_label(line['candidate_cp'],line.get('candidate_mate'))+'. Estimativas para o lado a jogar.')
                    if not line.get('is_alternative'):
                        st.caption('Seu lance já aparece entre as recomendações do motor.')
                st.caption(f"Os primeiros {line['context_plies']} meios-lances são o contexto histórico; "
                           f"a recomendação começa depois. Profundidade: {line['depth']}.")
                if st.button('Estudar esta linha', key='study_'+line['id'], disabled=not line['unlocked']):
                    session = begin_line(personal, line['id'], 'train')
                    if session:
                        session['reference_mode'] = True
                        state.openings_plan = personal
                        state.openings_active = True
                        state.openings_catalog = False
                        save_plan(personal, namespace='openings')
                        st.rerun()
