"""Mandatory login and revocable, browser-scoped automatic access."""
import secrets
import time
from datetime import datetime
import streamlit as st
import classroom as rooms
from classroom_ui import _switch


_DEVICE=st.components.v2.component('coach_login_device',html='<span hidden></span>',js='''
export default function({data,parentElement,setStateValue}){
 if(parentElement._nonce===data.nonce)return;parentElement._nonce=data.nonce;
 let device='',ok=true;
 try{
   const key='coach_chess_device_v1';
   if(data.action==='set')localStorage.setItem(key,data.device);
   if(data.action==='clear')localStorage.removeItem(key);
   if(data.action==='read')device=localStorage.getItem(key)||'';
 }catch{ok=false;}
 setStateValue('sync',{nonce:data.nonce,device,ok});
}''')


def _command(action,device=''):
    st.session_state.auth_storage_command=dict(action=action,device=device,nonce=secrets.token_hex(12))


def logout_current():
    rooms.forget_device(st.session_state.get('auth_device',''))
    st.session_state.pop('auth_device',None)
    _switch()
    _command('clear')


def _bridge():
    state=st.session_state
    if 'auth_storage_command' not in state:_command('read')
    command=state.auth_storage_command
    result=_DEVICE(data=command,key='coach_login_device',height=0,on_sync_change=lambda:None)
    event=getattr(result,'sync',None)
    if not isinstance(event,dict) or event.get('nonce')!=command['nonce'] or state.get('auth_storage_handled')==command['nonce']:
        return
    state.auth_storage_handled=command['nonce']
    if command['action']=='read' and not state.get('classroom_token'):
        device=event.get('device','')
        token=rooms.restore_device(device) if device else None
        if token:
            state.auth_device=device;_switch(token);st.rerun()
        if device:
            _command('clear');st.rerun()
    if command['action']=='set' and not event.get('ok'):
        st.warning('O navegador não permitiu salvar o acesso automático. Seu login continua válido nesta janela.')


def require_login():
    _bridge()
    state=st.session_state
    command=state.get('auth_storage_command',{})
    if (not state.get('classroom_token') and command.get('action')=='read'
            and state.get('auth_storage_handled')!=command.get('nonce')):
        # Wait for saved access before flashing the credentials screen.
        st.stop()
    user=rooms.identity(state.get('classroom_token'))
    if user:
        # Also remember sessions opened before automatic access became the default.
        if not state.get('auth_device'):
            state.auth_device=rooms.remember_device(state.classroom_token)
            _command('set',state.auth_device)
            st.rerun()
        from presence_ui import enforce_presence
        enforce_presence(user)
        from welcome_screen import remembered_entry
        remembered_entry(user)
        from streak_style import login_streak
        state.login_streak=login_streak(state.classroom_token,record=True)
        return user
    if state.get('classroom_token'):
        renewed=rooms.restore_device(state.get('auth_device',''))
        if renewed:
            _switch(renewed);st.rerun()
        _switch();rooms.forget_device(state.get('auth_device',''));_command('clear')
    from welcome_screen import entry_style, hero
    entry_style()
    with st.container(key='coach_entrance'):
        art,center=st.columns([1.7,1],gap='large',vertical_alignment='center')
    with art:
        hero()
    with center, st.container(key='entry_access'):
        st.header('Bem-vindo ao seu próximo nível.')
        st.caption('Entre para acessar o aplicativo.')
        role=st.segmented_control('Tipo de acesso',['Usuário','Professor'],default='Usuário',width='stretch') or 'Usuário'
        create=st.checkbox('Criar conta de usuário') if role=='Usuário' else False
        with st.form('coach_required_login'):
            name=st.text_input('Usuário')
            password=st.text_input('Senha',type='password')
            invitation=st.text_input('Chave especial do Professor (obrigatória)',type='password') if role=='Professor' else ''
            st.caption('Seu acesso será lembrado neste dispositivo.')
            submitted=st.form_submit_button('Entrar',type='primary',width='stretch')
        if submitted:
            try:
                if role=='Usuário':token=rooms.register_user(name,password) if create else rooms.login_user(name,password)
                else:token=rooms.enter_professor(name,password,invitation)
                _switch(token)
                state.welcome_entered=True
                state.auth_device=rooms.remember_device(token)
                _command('set',state.auth_device)
                st.rerun()
            except rooms.RegistrationPending as error:
                st.info(str(error))
            except (ValueError,PermissionError) as error:
                st.error(str(error))
        if role=='Professor':
            st.caption('A chave é obrigatória e emitida somente pelo criador. No primeiro acesso, escolha usuário e senha; depois, utilize os mesmos dados e sua chave.')
    st.stop()


@st.fragment(run_every='15s')
def admin_workspace(token):
    user=rooms.identity(token)
    if not user or user['role']!='admin':
        st.error('Acesso exclusivo do Superadministrador.');return
    overview=rooms.admin_overview(token)
    roster=rooms.students(token)
    teachers={row['id']:row['name'] for row in overview['professors']}
    available=sum(not row['revoked'] and not row['used_by'] and not row['expired'] for row in overview['invitations'])
    st.html("""<style>
    .st-key-admin_console [data-testid="stMetric"]{background:linear-gradient(135deg,#1b1b1b,#111);border:1px solid #292929;border-radius:16px;padding:18px 22px}
    .st-key-admin_console [data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px}
    .st-key-admin_console [data-testid="stCode"]{border:1px solid #805219;border-radius:12px}
    </style>""")
    with st.container(key='admin_console'):
        from presence_ui import online_panel
        online_panel(token)
        title,action=st.columns([3,1],vertical_alignment='center')
        with title:
            st.header('Usuários')
            st.caption('Superadministrador')
        with action:
            if st.button('Criar chave',type='primary',icon=':material/add:',width='stretch'):
                st.session_state.last_professor_invite=rooms.issue_professor_key(token)
                st.session_state.last_professor_invite_created=time.time()
                st.rerun()
        if key:=st.session_state.get('last_professor_invite'):
            with st.container(border=True):
                label,dismiss=st.columns([4,1],vertical_alignment='center')
                label.write('**Chave de Professor criada**')
                if dismiss.button('Fechar',key='dismiss_professor_key',width='stretch'):
                    st.session_state.pop('last_professor_invite',None);st.rerun()
                if time.time()-st.session_state.get('last_professor_invite_created',0)<rooms.PROFESSOR_KEY_TTL:
                    st.code(key,language=None)
                    st.caption('Validade para ativação: 15 minutos.')
                else:st.caption('Prazo de ativação encerrado. Consulte o status em Chaves.')
        counts=st.columns(3)
        counts[0].metric('Chaves disponíveis',available)
        counts[1].metric('Professores',len(overview['professors']))
        counts[2].metric('Usuários',len(overview['users']))
        keys,professors,users,students=st.tabs(['Chaves','Professores','Usuários','Alunos'])
        with keys:
            if not overview['invitations']:st.caption('Nenhuma chave criada.')
            for invite in overview['invitations']:
                with st.container(border=True):
                    details,action,delete=st.columns([4,1,1],vertical_alignment='center')
                    status='Revogada' if invite['revoked'] else 'Em uso' if invite['used_by'] else 'Expirada' if invite['expired'] else 'Disponível'
                    details.write('**'+invite['label']+'**')
                    details.caption(status+(' · '+teachers.get(invite['used_by'],'Professor') if invite['used_by'] else ''))
                    from preparation_state import LOCAL_ZONE
                    details.caption('Criada '+datetime.fromtimestamp(invite['created'],LOCAL_ZONE).strftime('%d/%m %H:%M')+
                        (' · Validade '+datetime.fromtimestamp(invite['expires_at'],LOCAL_ZONE).strftime('%H:%M') if not invite['used_by'] else ''))
                    if not invite['revoked'] and not invite['expired'] and action.button('Revogar',key='revoke_'+invite['id'],width='stretch'):
                        rooms.revoke_professor_key(token,invite['id']);st.rerun()
                    if delete.button('Excluir',key='delete_'+invite['id'],width='stretch'):
                        rooms.delete_professor_key(token,invite['id'])
                        st.session_state.pop('last_professor_invite',None);st.rerun()
        with professors:
            if not overview['professors']:st.caption('Nenhum professor cadastrado.')
            for teacher in overview['professors']:
                with st.container(border=True):
                    has_key=any(row['used_by']==teacher['id'] and not row['revoked'] for row in overview['invitations'])
                    status='Ativo' if teacher['approved'] and has_key else 'Sem chave ativa' if teacher['approved'] else 'Suspenso'
                    details,access,new_key=st.columns([3,1.5,1.5],vertical_alignment='center')
                    details.write('**'+teacher['name']+'**')
                    details.caption(status)
                    if access.button('Suspender' if teacher['approved'] else 'Autorizar',key='teacher_access_'+teacher['id'],width='stretch'):
                        rooms.set_professor_access(token,teacher['id'],not teacher['approved']);st.rerun()
                    if new_key.button('Nova chave',key='teacher_key_'+teacher['id'],width='stretch'):
                        st.session_state.last_professor_invite=rooms.issue_professor_key(token,teacher['name'],teacher['id'])
                        st.session_state.last_professor_invite_created=time.time();st.rerun()
        with users:
            from admin_users_ui import render_users
            render_users(token,overview['users'])
            from mobile_sync import devices_for_owner
            devices=devices_for_owner(token)
            st.markdown('**Dispositivos identificados**')
            st.caption('A lista mostra aparelhos que se identificaram e sincronizaram. Atividades offline aparecem apenas depois da reconexão.')
            if devices:
                from preparation_state import LOCAL_ZONE
                st.dataframe([{'Usuário':row['name'],'Dispositivo':row['device'],'Sistema':row['platform'],
                    'Versão':row['version'],'Última sincronização':datetime.fromtimestamp(row['last_sync'],LOCAL_ZONE).strftime('%d/%m/%Y %H:%M'),
                    'Eventos recebidos':row['sequence']} for row in devices],hide_index=True,width='stretch')
            else:st.caption('Nenhum dispositivo móvel sincronizado.')
        with students:
            if roster:
                st.dataframe([{'Professor':s['professor'],'Aluno':s['name'],'Chess.com':s['chesscom'],
                    'Advertências':s['warnings'],'Banido':bool(s['banned'])} for s in roster],hide_index=True,width='stretch')
            else:st.caption('Nenhum aluno cadastrado.')
