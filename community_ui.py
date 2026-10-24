"""Responsive classroom lounge, conversations and live lessons."""
from datetime import datetime
from pathlib import Path
import os
import json
import secrets
import streamlit as st
import classroom_community as community
from classroom_design import apply as apply_design,empty,icon,section
from preparation_state import LOCAL_ZONE

_CHAT=st.components.v2.component('classroom_messenger',html='<section class="messenger"><header><span class="chat-avatar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-17a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5v2"/></svg></span><div><strong></strong><small>Mensagens da sua turma</small></div></header><div class="messages" role="log" aria-live="polite"></div></section>',css='''
*{box-sizing:border-box}
.messenger{font:14px/1.5 "Segoe UI",sans-serif;border:1px solid #293438;border-radius:20px;overflow:hidden;background:radial-gradient(circle at 1px 1px,#28383c55 1px,transparent 0) 0 0/20px 20px,#111a20;color:#e9edef}header{display:flex;align-items:center;gap:14px;background:#1b292f;padding:18px 22px}header span{color:#55c99b}header strong,header small{display:block}header small{color:#9cabae;font-size:12px}.messages{height:360px;overflow:auto;padding:22px;display:flex;flex-direction:column;gap:12px}.bubble{align-self:flex-start;background:#25343b;border-radius:4px 15px 15px;padding:10px 14px;max-width:82%;overflow-wrap:anywhere;white-space:pre-wrap}.bubble.mine{align-self:flex-end;background:#075e54;border-radius:15px 4px 15px 15px}.bubble b{display:block;color:#7dd6b4;font-size:12px}.bubble small{display:block;text-align:right;color:#acbfbc;font-size:10px;margin-top:5px}.chat-avatar{height:42px;width:42px;display:grid;place-items:center;border:1px solid #426252;border-radius:14px;background:#2a4437}.chat-avatar svg{width:23px;height:23px}.empty{text-align:center;color:#a8b7b8;margin:auto;max-width:320px}.empty-icon{display:grid;place-items:center;width:64px;height:64px;margin:0 auto 18px;border-radius:21px;background:#233a31;border:1px solid #3f5e4b;color:#bbd5c4}.empty-icon img{height:30px;width:30px}.empty strong{font-size:17px;color:#dce5e7;font-weight:600}.empty p{font-size:12px;line-height:1.6;color:#889da7;margin:8px 0 0}@media(max-width:600px){.messages{height:320px;padding:12px}.bubble{max-width:92%}}''',js='''export default function({data,parentElement}){
 const box=parentElement.querySelector('.messages'),near=box.scrollHeight-box.scrollTop-box.clientHeight<100;
 parentElement.querySelector('header strong').textContent=data.title;
 const signature=data.messages.map(m=>m.id+':'+m.mine).join(',');if(parentElement._signature===signature)return;
 parentElement._signature=signature;box.replaceChildren();
 if(!data.messages.length){const empty=document.createElement('div');empty.className='empty';const emblem=document.createElement('div');emblem.className='empty-icon';emblem.innerHTML=data.emptyIcon||'';const title=document.createElement('strong');title.textContent='Converse com sua turma';const note=document.createElement('p');note.textContent='Envie a primeira mensagem, combine os treinos e compartilhe suas dúvidas.';empty.append(emblem,title,note);box.append(empty);}
 for(const m of data.messages){const bubble=document.createElement('div');bubble.className='bubble'+(m.mine?' mine':'');const name=document.createElement('b');name.textContent=m.name;const text=document.createElement('span');text.textContent=m.body;const time=document.createElement('small');time.textContent=m.time;bubble.append(name,text,time);box.append(bubble);}
 if(near)box.scrollTop=box.scrollHeight;
}''')

_LIVE=st.components.v2.component('classroom_live_video',html='<section class="live-video"><video playsinline controls></video><p class="live-status">Aguardando transmissão do Professor</p><div class="controls"><button class="broadcast">Transmitir câmera</button><button class="mic" hidden>Microfone ligado</button><button class="camera" hidden>Câmera ligada</button><button class="sound">Ativar áudio</button></div></section>',css='''
*{box-sizing:border-box}
.live-video{font:14px "Segoe UI",sans-serif;background:#13171c;color:#e5e9ed;border:1px solid #30383f;border-radius:18px;padding:12px}video{width:100%;max-height:420px;aspect-ratio:16/9;background:#050505;border-radius:12px}.controls{display:flex;flex-wrap:wrap;gap:8px}button{border:1px solid #43504a;border-radius:20px;background:#23382e;color:white;padding:10px 18px;cursor:var(--club-cursor-link,pointer)}button:disabled{opacity:.5}button[hidden]{display:none}@media(max-width:600px){button{flex:1;padding:10px}.live-video{padding:8px}}''',js=(Path(__file__).parent/'assets/classroom-live.js').read_text(encoding='utf-8'))


@st.fragment(run_every='3s')
def conversations(token,room,student=None,teacher=False,live_chat=False):
    namespace=room+('_live' if live_chat else '')
    options=['Grupo da sala','Conversa com aluno' if teacher else 'Meu Professor']
    choice=options[0] if live_chat else st.segmented_control('Conversa',options,default=options[0],key='conversation_'+namespace)
    channel='group' if choice==options[0] else student
    if not channel:st.info('Selecione um aluno.');return
    try:rows=community.messages(token,channel,room)
    except PermissionError:
        st.info('Conversa indisponível.');return
    for row in rows:row['time']=datetime.fromtimestamp(row['created'],LOCAL_ZONE).strftime('%d/%m %H:%M')
    _CHAT(data={'title':'Grupo da sala' if channel=='group' else 'Conversa privada','messages':rows,'emptyIcon':icon('chat')},key='classroom_messages_'+namespace)
    def submit():
        text=st.session_state.get('compose_'+namespace,'')
        if text:community.send(token,text,channel,room,nonce=secrets.token_hex(16))
    st.chat_input('Escreva uma mensagem',max_chars=4000,key='compose_'+namespace,on_submit=submit)


@st.fragment(run_every='2s')
def live_stage(token,room):
    call=community.live(token,room)
    if not call:
        st.caption('Nenhuma aula ao vivo no momento.');return
    st.markdown('**🔴 '+call['title'].replace('<','').replace('>','')+'**')
    peer=st.session_state.get('live_peer_'+call['id'])
    if not peer:
        if st.button('Entrar na aula ao vivo',key='join_live_'+room,type='primary'):
            st.session_state['live_peer_'+call['id']]=community.join_live(token,room)
            st.session_state['live_view_class_'+room]=call['id'];st.rerun(scope='fragment')
        return
    cache_key='live_exchange_'+peer
    def sync():
        event=st.session_state['rtc_'+peer].exchange
        if not event:return
        try:
            result=community.exchange(token,peer,event.get('outbox',[]),event.get('after',0),room)
            result['acked']=[e['nonce'] for e in event.get('outbox',[])]
            st.session_state[cache_key]=result
        except (ValueError,PermissionError):
            st.session_state.pop('live_peer_'+call['id'],None)
    try:
        data=st.session_state.get(cache_key) or community.exchange(token,peer,room=room)
        data['iceServers']=json.loads(os.environ.get('COACH_WEBRTC_ICE_SERVERS','[{"urls":"stun:stun.l.google.com:19302"}]'))
        _LIVE(data=data,key='rtc_'+peer,on_exchange_change=sync)
        if st.button('Sair da transmissão',key='leave_live_'+room):
            community.leave_live(token,peer,room);st.session_state.pop('live_peer_'+call['id'],None);st.rerun(scope='fragment')
    except (ValueError,PermissionError):
        st.session_state.pop('live_peer_'+call['id'],None);st.caption('Aula encerrada.')


def lesson_room(token,room,teacher=False):
    apply_design()
    st.subheader('Sala de aula')
    call=community.live(token,room)
    with st.container(border=True,key='prep_live_controls'):
        intro,actions=st.columns([2.2,1],vertical_alignment='center')
        with intro:
            st.html('<div class="prep-live-cover"><div><span class="prep-eyebrow">ENCONTRO AO VIVO</span><h3>A turma mais perto.</h3><p>'+('Transmita sua aula e converse com os alunos em tempo real.' if teacher else 'Entre na transmissão quando o Professor iniciar a aula.')+'</p></div><span>'+icon('video')+'</span></div>')
        with actions:
            if teacher:
                if not call:
                    if st.button('Iniciar aula ao vivo',icon=':material/videocam:',type='primary',width='stretch'):
                        community.start_live(token,room=room);st.rerun()
                elif st.button('Encerrar aula para todos',type='primary',width='stretch'):
                    community.end_live(token,room);st.rerun()
            if st.button('Atualizar aulas',icon=':material/refresh:',key='refresh_lessons_'+room,width='stretch'):st.rerun()
    live_stage(token,room)
    if call:
        with st.expander('Conversa durante a aula',expanded=True):
            conversations(token,room,teacher=teacher,live_chat=True)
    library,publish=st.columns([2.5,1],vertical_alignment='center')
    library.subheader('Vídeos gravados')
    if teacher:
        with publish.popover('Publicar vídeo',icon=':material/add:',width='stretch'):
            with st.form('publish_video_'+room,clear_on_submit=True):
                title=st.text_input('Título da aula',max_chars=150)
                url=st.text_input('Link do vídeo',placeholder='https://…')
                upload=st.file_uploader('Ou envie um vídeo (até 100 MB)',type=['mp4','webm','mov'])
                if st.form_submit_button('Publicar',type='primary',width='stretch'):
                    try:
                        mime={'mp4':'video/mp4','webm':'video/webm','mov':'video/quicktime'}.get(upload.name.rsplit('.',1)[-1].lower(),'') if upload else ''
                        community.publish_video(token,title,url,upload.getvalue() if upload else None,mime,room);st.rerun()
                    except ValueError as e:st.error(str(e))
    recorded_videos(token,room,teacher)


def recorded_videos(token,room=None,teacher=False):
    apply_design()
    lessons=community.videos(token,room)
    if not lessons:
        empty('Aulas para assistir e rever','Publique a primeira aula para começar a biblioteca da turma.' if teacher else 'Os vídeos publicados pelo Professor ficarão disponíveis aqui a qualquer momento.','video')
    grid=st.columns(2)
    for index,video in enumerate(lessons):
        with grid[index%2].container(border=True,key='lesson_video_'+video['id']):
            st.html('<div class="prep-video-cover">'+icon('play')+'</div>')
            st.caption('AULA GRAVADA · '+datetime.fromtimestamp(video['created'],LOCAL_ZONE).strftime('%d/%m/%Y'))
            with st.expander(video['title']):
                if st.button('Assistir',key='watch_'+video['id']):st.session_state['watch_'+video['id']+'_active']=True
                if st.session_state.get('watch_'+video['id']+'_active'):
                    st.video(video['url'] or community.video_media(token,video['id'],room),format=video['mime'] or 'video/mp4')
                if teacher and st.button('Excluir vídeo',key='remove_video_'+video['id']):
                    community.delete_video(token,video['id'],room);st.rerun()


def release_live_view(token,room):
    call=st.session_state.pop('live_view_class_'+room,None)
    if not call:return
    peer=st.session_state.pop('live_peer_'+call,None)
    if peer:
        try:community.leave_live(token,peer,room)
        except PermissionError:pass
