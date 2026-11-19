"""Student cards and a focused, persistent student record."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import escape
import time
import unicodedata

import streamlit as st

import classroom as rooms
import classroom_student_profiles as profiles
from preparation_state import LOCAL_ZONE


@st.cache_resource
def _profile_worker():
    return ThreadPoolExecutor(max_workers=1,thread_name_prefix='student-profile')


def _date(value):
    try:return datetime.fromtimestamp(value,LOCAL_ZONE).strftime('%d/%m/%Y · %H:%M')
    except (ValueError,TypeError,OverflowError,OSError):return 'Não informado'


@st.fragment(run_every='2s')
def _chess_profile(token, student):
    username=student['chesscom']
    if not username:
        st.info('Informe o usuário Chess.com nos dados abaixo para consultar ID e ratings.');return
    saved=profiles.load(token,student['id'],username)
    key='prep_student_lookup_'+student['id']
    state=st.session_state.get(key)
    refresh=st.button('Atualizar Chess.com',icon=':material/sync:',key='student_sync_'+student['id'],
                      disabled=bool(state and state.get('future') and not state['future'].done()))
    if refresh or (not state or state['username']!=username) and (not saved or time.time()-saved['updated']>43200):
        from chesscom import fetch_player_profile
        state={'username':username,'future':_profile_worker().submit(fetch_player_profile,username)}
        st.session_state[key]=state
    if state and state['username']==username and (future:=state.get('future')) and future.done():
        try:
            profiles.save(token,student['id'],username,future.result())
            saved=profiles.load(token,student['id'],username)
        except (ValueError,OSError) as error:state['error']=str(error)
        finally:state['future']=None
    if state and state.get('error'):st.warning(state['error'])
    if state and state.get('future'):st.caption('Consultando o perfil público… Você pode continuar editando a ficha.')
    if not saved:return
    data=saved['data']
    identity,link=st.columns([2,1],vertical_alignment='center')
    identity.markdown('**ID Chess.com:** '+str(data.get('player_id') or 'Não informado'))
    link.link_button('Ver perfil',f'https://www.chess.com/member/{username}',icon=':material/open_in_new:',width='stretch')
    if data.get('title') or data.get('name'):
        st.caption(' · '.join(value for value in [data.get('title'),data.get('name')] if value))
    for column,(label,rating) in zip(st.columns(4),data['ratings'].items()):
        column.metric(label,str(rating) if rating is not None else '—')
    st.caption('Último acesso ao Chess.com: '+_date(data.get('last_online')))
    if data.get('joined'):st.caption('No Chess.com desde '+_date(data['joined']).split(' · ')[0])
    st.caption('Dados salvos em '+_date(saved['updated'])+' · Ratings públicos do Chess.com.')


@st.dialog('Ficha do aluno',width='large',on_dismiss='rerun')
def student_record(token,identifier):
    student=next((row for row in rooms.students(token) if row['id']==identifier),None)
    if not student:st.error('Aluno não encontrado nesta sala.');return
    st.html('<div class="student-record-title"><span class="roster-avatar">'+escape(student['name'][:1].upper())+
            '</span><div><h3>'+escape(student['name'])+'</h3><p>'+escape(student.get('account_name') or 'Aguardando vínculo com uma conta')+'</p></div></div>')
    from classroom_session_ui import student_progress
    student_progress(token,identifier)
    if st.button('Abrir e editar a trilha deste aluno',icon=':material/route:',type='primary',width='stretch'):
        st.session_state.prep_workspace_student=identifier
        st.session_state.prep_workspace_tabs='Treino e provas'
        st.session_state.requested_page='Preparo'
        st.rerun()
    _chess_profile(token,student)
    with st.form('student_details_'+identifier):
        st.markdown('**Dados do aluno**')
        name=st.text_input('Nome do aluno',value=student['name'])
        chesscom=st.text_input('Usuário Chess.com do aluno',value=student['chesscom'],help='Apenas o usuário, sem o endereço do site.')
        if st.form_submit_button('Salvar dados do aluno',icon=':material/check:',type='primary',width='stretch'):
            try:
                rooms.update_student(token,identifier,name,chesscom)
                st.session_state.pop('classroom_games_'+identifier,None)
                st.session_state['prep_student_saved']=name.strip()
                st.rerun()
            except ValueError as error:st.error(str(error))
    summary=rooms.dashboard(token,identifier)
    st.markdown('**Acompanhamento na sala**')
    columns=st.columns(3)
    columns[0].metric('Advertências',f"{student['warnings']} / 3")
    columns[1].metric('Linhas hoje',summary['lines'])
    columns[2].metric('Tempo ativo hoje',f"{summary['seconds']/60:.0f} min")
    st.caption('Rotina definida' if summary['routine'] else 'Nenhuma rotina definida para este aluno.')
    with st.expander('Identificação e acesso'):
        st.caption('ID Coach Chess');st.code(identifier,language=None)
        st.write('Conta vinculada: '+(student.get('account_name') or 'Ainda não vinculada'))
        if student['banned']:st.error('Acesso revogado.')
        else:st.caption('Chave da sala');st.code(student['access_key'],language=None)


def _open_training(identifier):
    st.session_state.prep_roster_training_request=identifier
    st.session_state.requested_page='Preparo'


def _search_text(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))


def roster_cards(token,roster):
    from classroom_design import section
    section('01','Alunos e acessos','Abra uma ficha para consultar o perfil, editar os dados e acompanhar o aluno.')
    if saved:=st.session_state.pop('prep_student_saved',None):st.success('Dados de '+saved+' salvos.')
    linked=sum(bool(row.get('linked')) and not row['banned'] for row in roster)
    waiting=sum(not row.get('linked') and not row['banned'] for row in roster)
    revoked=sum(bool(row['banned']) for row in roster)
    st.html('<div class="roster-stats">'+''.join(
        f'<div class="roster-stat {kind}"><span>{label}</span><strong>{value:02d}</strong><small>{note}</small></div>'
        for kind,label,value,note in [('total','Vagas na sala',len(roster),'Seu espaço de acompanhamento'),
            ('linked','Contas vinculadas',linked,'Alunos com conta conectada'),
            ('waiting','Aguardando vínculo',waiting,'Compartilhe a chave de acesso'),
            ('revoked','Acessos revogados',revoked,'Vagas com acesso bloqueado')])+'</div>')
    with st.container(key='roster_tools'):
        search,filters=st.columns([1.3,1],vertical_alignment='bottom')
        query=search.text_input('Buscar aluno',placeholder='Nome, usuário Chess.com ou professor',icon=':material/search:',key='roster_search')
        status_filter=filters.selectbox('Filtrar por acesso',['Todos os acessos','Contas vinculadas','Aguardando vínculo','Acessos revogados'],key='roster_filter')
    needle=_search_text(query.strip())
    visible=[row for row in roster if (not needle or needle in _search_text(' '.join(str(row.get(field) or '') for field in ('name','chesscom','professor','account_name'))))
             and (status_filter=='Todos os acessos' or
                  status_filter=='Contas vinculadas' and row.get('linked') and not row['banned'] or
                  status_filter=='Aguardando vínculo' and not row.get('linked') and not row['banned'] or
                  status_filter=='Acessos revogados' and row['banned'])]
    st.caption(f'{len(visible)} de {len(roster)} vagas · Abra a ficha ou vá direto para a trilha do aluno.')
    if not visible:
        from classroom_design import empty
        empty('Nenhum aluno encontrado','Tente outro nome ou selecione todos os acessos.','users')
        st.button('Limpar busca e filtros',icon=':material/filter_alt_off:',on_click=_clear_filters)
        return
    seats=st.columns(2,gap='medium')
    for index,row in enumerate(visible):
        status='Acesso revogado' if row['banned'] else 'Conta vinculada' if row.get('linked') else 'Aguardando uso da chave'
        kind='revoked' if row['banned'] else 'linked' if row.get('linked') else 'waiting'
        with seats[index%2].container(border=True,key='seat_'+row['id']):
            st.html(f'<div class="roster-card-top"><span class="roster-avatar">{escape(row["name"][:1].upper())}</span><div><span class="roster-seat">VAGA {row["slot"]}</span><span class="roster-status {kind}">{status}</span></div></div>')
            if st.button(row['name'],key='prep_student_open_'+row['id'],icon=':material/person:',width='stretch'):
                student_record(token,row['id'])
            st.caption('@'+row['chesscom'] if row['chesscom'] else 'Chess.com ainda não informado')
            dots=''.join('<i class="filled"></i>' if n<row['warnings'] else '<i></i>' for n in range(3))
            st.html(f'<div class="roster-card-footer"><span>{row["warnings"]}/3 advertências</span><span class="roster-warning-dots" aria-hidden="true">{dots}</span></div>')
            details,training=st.columns(2)
            if details.button('Ver ficha',key='roster_record_'+row['id'],icon=':material/badge:',width='stretch'):
                student_record(token,row['id'])
            if training.button('Abrir trilha',key='roster_training_'+row['id'],icon=':material/route:',width='stretch',
                               disabled=bool(row['banned'])):
                _open_training(row['id'])
                st.rerun()
            if not row['banned']:
                with st.expander('Chave de acesso'):
                    st.code(row['access_key'],language=None)
                    st.caption('O aluno usa esta chave em “Juntar-se à sala”.')
    st.caption('Depois que o aluno vincula a conta, o cadastro permanece nesta sala após sair e entrar novamente.')


def _clear_filters():
    st.session_state.roster_search=''
    st.session_state.roster_filter='Todos os acessos'
