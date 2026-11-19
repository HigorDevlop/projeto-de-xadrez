"""Prepare personal lines in a worker, then reuse the local lesson trainer."""
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from functools import lru_cache
from html import escape
from pathlib import Path
import csv
import hashlib
import streamlit as st
from opening_course_state import begin_line, course_lines
from personal_openings import remember_history, prepare_history_trails, storage_key
from preparation_state import load_plan, save_plan, today


@st.cache_resource
def workers():
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix='personal-openings')


@lru_cache(maxsize=1)
def opening_names():
    names={};lengths={}
    translations={'Caro-Kann Defense':'Defesa Caro-Kann','Sicilian Defense':'Defesa Siciliana','Italian Game':'Abertura Italiana',"King's Indian Defense":'Defesa Indiana do Rei','French Defense':'Defesa Francesa','Ruy Lopez':'Abertura Espanhola',"Queen's Gambit Declined":'Gambito da Dama Recusado','Slav Defense':'Defesa Eslava','Scandinavian Defense':'Defesa Escandinava','English Opening':'Abertura Inglesa',"King's Pawn Game":'Abertura do Peão do Rei',"Queen's Pawn Game":'Abertura do Peão da Dama','Nimzo-Indian Defense':'Defesa Nimzo-Índia','Pirc Defense':'Defesa Pirc','Philidor Defense':'Defesa Philidor'}
    for path in (Path(__file__).parent/'data/openings').glob('*.tsv'):
        with path.open(encoding='utf-8-sig') as source:
            for row in csv.DictReader(source,delimiter='\t'):
                size=len(row['pgn'].split())
                if size<lengths.get(row['eco'],10000):
                    raw=row['name'].split(':')[0]
                    names[row['eco']]=translations.get(raw,raw);lengths[row['eco']]=size
    return names


def group_lines(lines):
    result=OrderedDict()
    for line in lines:
        original=line.get('opening','Abertura do seu histórico')
        title=opening_names().get(original,original)
        group=(title,line['side'])
        positions=result.setdefault(group,OrderedDict())
        position=tuple(line['moves'][:line.get('context_plies',0)])
        positions.setdefault(position,[]).append(line)
    return result


def style():
    st.html("""<style>
    .st-key-personal_repertoire{padding:24px!important;background:linear-gradient(140deg,#1d2320,#131715)!important;border:1px solid #82966b3d!important;border-radius:18px!important;box-shadow:inset 0 1px #ffffff0b,0 12px 30px #0004}
    .st-key-personal_repertoire button{min-height:46px!important;border-radius:12px!important;border:1px solid #ffffff24!important;background:linear-gradient(180deg,#303833,#202622)!important;color:#f3f5ef!important;box-shadow:inset 0 1px 0 #ffffff19,0 3px 0 #0b0f0c,0 6px 12px #0004!important;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease!important}
    .st-key-personal_repertoire button p{font:600 14px/1.45 system-ui!important;color:inherit!important;background:transparent!important}
    .st-key-personal_repertoire button:hover{transform:translateY(-2px);border-color:#cdb58099!important;box-shadow:inset 0 1px #ffffff25,0 5px 0 #0b0f0c,0 9px 18px #0005!important}
    .st-key-personal_repertoire button:active{transform:translateY(1px);box-shadow:inset 0 2px 5px #0005!important}
    .st-key-personal_repertoire button:focus-visible{outline:2px solid #f0d49b!important;outline-offset:3px}
    .st-key-personal_repertoire button[kind=primary]{background:linear-gradient(180deg,#edcf92,#cba261)!important;color:#191d17!important;border-color:#f5dcaa!important;box-shadow:inset 0 1px #fff6,0 3px 0 #795b2f,0 6px 14px #0004!important}
    .st-key-personal_repertoire button:disabled{transform:none;opacity:.5}
    [data-testid=stVerticalBlock][class*=st-key-personal_trail_]:not(.st-key-personal_trail_steps){padding:14px 18px!important;border:1px solid #879a7235!important;border-radius:14px;background:linear-gradient(145deg,#252d26,#1a211b);box-shadow:inset 0 1px #ffffff10,0 5px 14px #0003}
    @media(prefers-reduced-motion:reduce){.st-key-personal_repertoire button{transition:none!important}.st-key-personal_repertoire button:hover{transform:none}}
    .personal-intro h3{font:600 24px system-ui!important;margin:0 0 8px!important;padding:0!important;letter-spacing:-.6px}.personal-intro p{margin:0;color:#9fb09e;font:13px/1.6 system-ui}.personal-account{display:inline-block;margin-top:12px;padding:5px 10px;border-radius:20px;border:1px solid #7d956e44;color:#c1d2b5;font:11px system-ui;background:#263323}
    @media(max-width:600px){.st-key-personal_repertoire{padding:14px!important}.personal-intro h3{font-size:21px!important}}
    </style>""")


def prepare_from_history(owner,account,games):
    from chesscom import fetch_recent_games
    notice=False
    try:
        games=remember_history(owner,account,fetch_recent_games(account,limit=200))
    except (OSError,ValueError):
        notice=True
    result=prepare_history_trails(owner,account,games,depth=22,seconds=2.0)
    result['history_offline']=notice
    return result


def history_trails(lines):
    result=[]
    for identity,positions in group_lines(lines).items():
        lessons=[line for options in positions.values() for line in options]
        lessons.sort(key=lambda line:(-line.get('frequency',0),line.get('context_plies',0),
                     {'Principal do motor':0,'Iniciativa com segurança':1,'Opção sólida':2}.get(line.get('recommendation'),3)))
        frequency=max(line.get('opening_frequency',line.get('frequency',0)) for line in lessons)
        result.append((identity,lessons,frequency))
    return sorted(result,key=lambda trail:-trail[2])


def render_personal_openings(owner, account):
    if not account:
        st.caption('Vincule seu Chess.com em Minha conta para montar sua trilha pessoal.')
        return
    key,state=storage_key(owner,account),st.session_state
    style()
    with st.container(key='personal_repertoire'):
        try:games=remember_history(owner,account,state.get('history_games',[]))
        except OSError:
            st.error('Não foi possível guardar seu histórico.');return
        personal=load_plan(key,namespace='openings')
        job_key='personal_opening_job:'+key
        job=state.get(job_key)
        intro,actions=st.columns([2.3,1],vertical_alignment='center')
        with intro:
            basis=personal.get('source_games',len(games)) if personal else len(games)
            st.html('<div class="personal-intro"><h3>Suas trilhas</h3><p>'+escape(account)+' · '+str(basis)+' de até 200 partidas recentes</p></div>')
        with actions:
            if st.button('Atualizar trilhas' if personal else 'Montar minhas trilhas',
                         key='prepare_personal_openings',disabled=job is not None,
                         icon=':material/refresh:' if personal else ':material/route:',width='stretch'):
                state[job_key]=workers().submit(prepare_from_history,owner,account,games);st.rerun()
        if job is not None:
            @st.fragment(run_every=.5)
            def monitor():
                if not job.done():
                    st.caption('Analisando seu histórico em segundo plano…');return
                state.pop(job_key,None)
                try:
                    result=job.result();previous=load_plan(key,namespace='openings') or {}
                    identifiers={line['id'] for line in result['personal_lines']}
                    for field in ('practice_progress','retention'):
                        result[field]={k:v for k,v in previous.get(field,{}).items() if k in identifiers}
                    for field in ('achievements','achievement_progress','quiz_seen','reference_activity'):
                        if field in previous:result[field]=previous[field]
                    save_plan(result,namespace='openings');state.pop('personal_opening_error:'+key,None)
                except Exception as error:state['personal_opening_error:'+key]=str(error)
                st.rerun()
            monitor()
        if error:=state.get('personal_opening_error:'+key):st.error(error)
        if not personal:
            st.caption('Suas aberturas mais jogadas viram uma sequência de treinos, com análise do Stockfish local.')
            return
        if personal.get('recommendation_version',1)<3:
            st.caption('Atualize as trilhas para usar as últimas 200 partidas e manter cada abertura na sua sequência.')
        elif personal.get('history_offline'):
            st.caption('Sem conexão na última preparação: foram usadas as partidas salvas neste aparelho.')
        personal['start']=personal['end']=str(today())
        lines=course_lines(personal)
        trails=history_trails(lines)
        if not trails:st.caption('Nenhuma trilha preparada ainda.');return
        selected_key='personal_selected_trail:'+key
        selected=state.get(selected_key)
        trail=next((item for item in trails if item[0]==selected),None)

        def begin(line,lessons):
            personal['personal_trail_ids']=[item['id'] for item in lessons]
            session=begin_line(personal,line['id'],'train')
            if session:
                session['reference_mode']=True
                state.openings_plan=personal;state.openings_active=True;state.openings_catalog=False
                save_plan(personal,namespace='openings');st.rerun()

        if trail is None:
            for identity,lessons,frequency in trails:
                name,color=identity
                done=sum(bool(line['learned']) for line in lessons)
                row_key='personal_trail_'+hashlib.sha256(repr(identity).encode()).hexdigest()[:16]
                with st.container(key=row_key):
                    label,action=st.columns([3,1],vertical_alignment='center')
                    with label:
                        st.markdown('**'+name+'** · '+('Brancas' if color=='white' else 'Pretas'))
                        st.caption(str(frequency)+' partidas · '+str(done)+'/'+str(len(lessons))+' etapas concluídas')
                    with action:
                        if st.button('Continuar' if done else 'Começar',key=row_key+'_open',width='stretch',type='primary'):
                            state[selected_key]=identity;st.rerun()
            return

        identity,lessons,frequency=trail
        if st.button('Todas as trilhas',icon=':material/arrow_back:',key='personal_trails_back'):
            state.pop(selected_key,None);st.rerun()
        st.subheader(identity[0])
        done=sum(bool(line['learned']) for line in lessons)
        st.progress(done/len(lessons),text=str(done)+' de '+str(len(lessons))+' etapas concluídas')
        next_line=next((line for line in lessons if not line['learned']),lessons[0])
        if st.button('Continuar treino' if done else 'Começar treino',icon=':material/play_arrow:',
                     key='personal_trail_continue',width='stretch',type='primary'):
            begin(next_line,lessons)
        with st.container(key='personal_trail_steps'):
            columns=st.columns(min(5,len(lessons)))
            for index,line in enumerate(lessons):
                with columns[index%len(columns)]:
                    if st.button(str(index+1),icon=':material/check:' if line['learned'] else None,
                                 key='study_'+line['id'],width='stretch',
                                 help='Etapa '+str(index+1)+(' · Concluída' if line['learned'] else ' · Praticar')):
                        begin(line,lessons)
