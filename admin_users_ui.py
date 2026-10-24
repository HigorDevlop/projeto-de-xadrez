"""Creator account management with explicit, account-specific deletion."""
from datetime import datetime
from html import escape
import time
import streamlit as st
import classroom as rooms
from preparation_state import LOCAL_ZONE


@st.dialog('Excluir usuário')
def confirm_delete(token,identifier,name):
    st.write('Excluir a conta **'+name+'**?')
    st.caption('O login e os acessos automáticos serão removidos. Os registros de treino serão preservados. Esta ação não pode ser desfeita.')
    cancel,delete=st.columns(2)
    if cancel.button('Cancelar',width='stretch'):st.rerun()
    if delete.button('Excluir definitivamente',type='primary',icon=':material/delete_forever:',width='stretch'):
        try:
            rooms.delete_user(token,identifier)
        except (PermissionError,ValueError) as error:
            st.error(str(error));return
        st.session_state.admin_user_notice='Conta excluída: '+name
        st.rerun()


def render_users(token,rows):
    st.html('''<style>
    .st-key-admin_user_manager{padding:22px;border:1px solid #3d3b33;border-radius:18px;background:linear-gradient(135deg,#23241f,#141713);box-shadow:inset 0 1px #ffffff0a,0 12px 30px #0004}
    .user-detail{display:flex;align-items:center;gap:14px;padding:18px 0;font-family:system-ui}.user-avatar{width:50px;height:50px;display:grid;place-items:center;border:1px solid #af9b6066;border-radius:15px;background:linear-gradient(145deg,#54482a,#252a1d);color:#e5d4a8;font-size:23px;font-weight:600;box-shadow:inset 0 1px #ffffff14,0 4px 12px #0004}.user-detail h3{margin:0!important;padding:0!important;font:600 23px system-ui!important;color:#e8e6dd}.user-access{display:inline-block;margin-top:7px;font:11px system-ui;color:#a9cfb3}.user-access.blocked{color:#e4aaa0}.user-detail-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;padding:15px 0 24px}.user-detail-grid small{display:block;font:10px system-ui;color:#8c9988;margin-bottom:7px}.user-detail-grid strong{font:500 12px system-ui;color:#c6cdc0}.st-key-admin_user_delete button{border-color:#a9615155;color:#dfaaa0;background:linear-gradient(135deg,#3b2925,#241d1b)}
    .st-key-admin_user_manager button{box-shadow:inset 0 1px #ffffff0b,0 4px 10px #0003;transition:transform .18s,box-shadow .18s}.st-key-admin_user_manager button:hover{transform:translateY(-2px);box-shadow:inset 0 1px #ffffff17,0 7px 16px #0005}
    @media(max-width:600px){.user-detail-grid{grid-template-columns:1fr 1fr}.st-key-admin_user_manager{padding:16px}}@media(prefers-reduced-motion:reduce){.st-key-admin_user_manager button{transition:none}.st-key-admin_user_manager button:hover{transform:none}}
    </style>''')
    if notice:=st.session_state.pop('admin_user_notice',None):st.success(notice)
    with st.container(key='admin_user_manager'):
        total,active,blocked=st.columns(3)
        total.metric('Contas',len(rows))
        active.metric('Atividade recente',sum(bool(r['last_seen'] and time.time()-r['last_seen']<90) for r in rows))
        blocked.metric('Bloqueadas',sum(r['status']=='blocked' for r in rows))
        search=st.text_input('Buscar usuário',placeholder='Digite o nome...',key='admin_user_search')
        status=st.segmented_control('Filtrar acesso',['Todos','Autorizados','Bloqueados'],default='Todos',key='admin_user_filter') or 'Todos'
        filtered=[r for r in rows if search.casefold() in r['name'].casefold() and
                  (status=='Todos' or r['status']==('active' if status=='Autorizados' else 'blocked'))]
        if not filtered:
            st.caption('Nenhum usuário encontrado.');return
        accounts={r['id']:r for r in filtered}
        selected=st.selectbox('Gerenciar acesso do usuário',list(accounts),format_func=lambda key:accounts[key]['name'],key='admin_user_access')
        row=accounts[selected];allowed=row['status']=='active'
        def when(value):return datetime.fromtimestamp(value,LOCAL_ZONE).strftime('%d/%m/%Y · %H:%M') if value else '—'
        st.html('<div class="user-detail"><span class="user-avatar">'+escape(row['name'][:1].upper())+'</span><div><h3>'+escape(row['name'])+'</h3><span class="user-access'+('' if allowed else ' blocked')+'">'+('● Acesso liberado' if allowed else '● Acesso bloqueado')+'</span></div></div>'
            '<div class="user-detail-grid">'+''.join('<div><small>'+label+'</small><strong>'+escape(value)+'</strong></div>' for label,value in
            [('Cadastro',when(row['created'])),('Último login',when(row['last_login'])),('Última atividade',when(row['last_seen'])),('Professor',row['professor'] or 'Sem vínculo')])+'</div>')
        access,delete=st.columns(2)
        if access.button('Bloquear usuário' if allowed else 'Autorizar usuário',key='admin_change_user_access',icon=':material/lock:' if allowed else ':material/lock_open:',width='stretch'):
            rooms.set_user_access(token,selected,not allowed);st.rerun()
        with delete,st.container(key='admin_user_delete'):
            if st.button('Excluir usuário',icon=':material/person_remove:',width='stretch'):
                confirm_delete(token,selected,row['name'])
        with st.expander('Ver lista completa'):
            st.dataframe([{'Usuário':r['name'],'Acesso':'Autorizado' if r['status']=='active' else 'Bloqueado',
                           'Última atividade':when(r['last_seen'])} for r in rows],hide_index=True,width='stretch')
