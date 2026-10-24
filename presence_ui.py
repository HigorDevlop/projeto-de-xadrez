"""Private creator console and an invisible, independently timed heartbeat."""
from datetime import datetime
from urllib.error import HTTPError,URLError

import streamlit as st
import classroom as rooms
import desktop_presence as presence


@st.fragment(run_every='15s')
def heartbeat():
    actor=rooms.identity(st.session_state.get('classroom_token'))
    url=presence.service_url()
    if not actor or not url:return
    snapshot=presence.client(url,str(presence.base_dir()/'installation.json')).poll(actor['name'],presence.version())
    blocked=snapshot['blocked'] and actor['role']!='admin'
    previous=st.session_state.get('presence_blocked',False)
    st.session_state.presence_blocked=blocked
    if previous!=blocked:st.rerun()


def enforce_presence(actor):
    heartbeat()
    if st.session_state.get('presence_blocked') and actor['role']!='admin':
        st.error('Este dispositivo foi bloqueado pelo criador. Seus dados continuam salvos.')
        st.caption('O aplicativo verifica novamente a autorização quando houver conexão.')
        st.stop()


def online_panel(token):
    actor=rooms.identity(token)
    if not actor or actor['role']!='admin':return
    st.subheader('Quem está com o aplicativo aberto')
    url=presence.service_url()
    with st.expander('Conexão com o servidor central',expanded=not bool(url)):
        value=st.text_input('Endereço HTTPS do servidor',value=url,key='remote_server_address',placeholder='https://seu-servidor.example')
        if st.button('Salvar endereço',key='remote_save_url'):
            try:
                presence.save_url(value)
                st.session_state.pop('remote_owner_token',None)
                st.rerun()
            except ValueError as error:st.error(str(error))
    if not url:
        st.info('O servidor central ainda não foi configurado. As instalações dos seus amigos só aparecerão depois que se conectarem a ele.')
        return
    if st.session_state.get('remote_owner_url')!=url:
        st.session_state.pop('remote_owner_token',None)
    if not st.session_state.get('remote_owner_token'):
        with st.form('remote_owner_login'):
            st.caption('Entre com a conta do criador cadastrada no servidor central.')
            name=st.text_input('Superadministrador central',value='superadmin')
            password=st.text_input('Senha do painel central',type='password')
            submitted=st.form_submit_button('Conectar ao painel central')
        if submitted:
            try:
                result=presence.api(url,'/v1/login',{'name':name,'password':password})
                if result.get('account',{}).get('role')!='admin':raise PermissionError('Esta conta não é o Superadministrador.')
                st.session_state.remote_owner_token=result['token']
                st.session_state.remote_owner_url=url
                st.rerun()
            except (OSError,ValueError,KeyError,PermissionError):st.error('Não foi possível entrar. Confira o servidor e as credenciais do criador.')
        return
    authorization='Bearer '+st.session_state.remote_owner_token
    try:
        rows=presence.api(url,'/v1/admin/installations',authorization=authorization)['installations']
    except HTTPError as error:
        if error.code in (401,403):st.session_state.pop('remote_owner_token',None)
        st.warning('O painel central não pôde ser consultado. Reconecte sua conta se necessário.')
        return
    except (OSError,ValueError,KeyError):
        st.warning('Sem conexão com o painel central. Não foi possível atualizar quem está online.')
        return
    online=sum(row['online'] for row in rows)
    a,b=st.columns(2);a.metric('Online agora',online);b.metric('Instalações identificadas',len(rows))
    st.caption('Online: sinal recebido nos últimos 90 segundos. A conta exibida é a conta local em uso no dispositivo. Um aparelho que nunca se conectou ainda não pode aparecer aqui.')
    if not rows:
        st.caption('Nenhuma instalação se conectou ainda.');return
    from preparation_state import LOCAL_ZONE
    st.dataframe([{'Usuário':row['name'],'Estado':'Online' if row['online'] else 'Offline',
                   'Acesso':'Bloqueado' if row['blocked'] else 'Livre','Sistema':row['platform'],
                   'Versão':row['version'],'Última conexão':datetime.fromtimestamp(row['last_seen'],LOCAL_ZONE).strftime('%d/%m/%Y %H:%M:%S'),
                   'Dispositivo':row['device']} for row in rows],hide_index=True,width='stretch')
    options={row['device']:row for row in rows}
    selected=st.selectbox('Gerenciar dispositivo',list(options),format_func=lambda key:options[key]['name']+' · '+key[:8],key='remote_installation')
    blocked=options[selected]['blocked']
    if st.button('Desbloquear dispositivo' if blocked else 'Bloquear dispositivo',key='remote_change_access'):
        try:
            presence.api(url,f'/v1/admin/installations/{selected}/access',{'allowed':bool(blocked)},authorization)
            st.rerun()
        except (OSError,ValueError):st.error('Não foi possível alterar o acesso. Tente novamente.')
