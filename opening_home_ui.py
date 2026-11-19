"""Opening shelves and searchable catalogue matching the supplied reference."""
import chess
import chess.svg
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from opening_course_state import opening_rankings
from opening_repertoires import catalog
from opening_reference_catalog import display_name
from opening_reference_style import badge, FLAME
from opening_reference_progress import streak
from streak_style import flame

_HOME = st.components.v2.component(
    'opening_reference_home',
    html='<section class="home"><header><strong>Coach Chess <b>PRO</b></strong><nav><button data-action="streak" aria-label="Sequência diária"></button><button data-action="profile" aria-label="Perfil"><svg viewBox="0 0 48 48"><circle cx="24" cy="13" r="9" fill="currentColor"/><path d="M8 44v-7c0-17 32-17 32 0v7" fill="currentColor"/></svg></button></nav></header><div class="catalog-tools" hidden><div class="search-row"><button class="back" aria-label="Voltar às aberturas">‹</button><input aria-label="Buscar aberturas" type="search" placeholder="Buscar aberturas"/><button class="cancel">Cancelar</button></div><div class="filters" role="group" aria-label="Primeiro lance"></div></div><div class="shelves"></div><p class="empty" hidden>Nenhuma abertura encontrada.</p><nav class="pagination" aria-label="Páginas de aberturas" hidden></nav></section>',
    css='''
    .card{background:linear-gradient(150deg,#242424,#1c1c1c 45%,#181818)!important;border-color:#383838!important;box-shadow:inset 0 1px 0 #ffffff0d,inset 0 -1px 0 #00000040,0 3px 8px #00000040,0 12px 24px #0000001f}

    *{box-sizing:border-box}[hidden]{display:none!important}.home{font:16px/1.5 "Segoe UI",sans-serif;color:#f4f4f4;width:100%;padding:0 0 22px}header{display:flex;justify-content:space-between;align-items:center;padding:5px 0 24px}header strong{font-size:34px;font-weight:700;letter-spacing:-.6px}header strong b{font-size:17px;background:#fff;border-radius:5px;padding:1px 7px;color:#d3114b;letter-spacing:-.5px;vertical-align:middle;margin-left:7px}header nav{display:flex;gap:26px}button{font:inherit;cursor:var(--club-cursor-link,pointer);color:inherit;border:0}header button{width:32px;background:transparent;padding:0;color:#525b62}header button svg{width:100%;height:36px}button:focus-visible,input:focus-visible{outline:3px solid #ff8a00;outline-offset:4px}.shelf-head{display:flex;align-items:center;justify-content:space-between;margin:24px 0 14px}.shelf-head h2{font-size:25px;font-weight:500;margin:0}.shelf-head button{background:none;color:#949da3;font-size:14px;padding:8px}.rail{display:flex;overflow-x:auto;gap:22px;padding:20px 0 18px;scrollbar-width:thin;scrollbar-color:#3d474d transparent;scroll-snap-type:x mandatory}.card{position:relative;flex:0 0 calc((100% - 66px)/4);min-width:200px;max-width:280px;background:linear-gradient(145deg,#1e1e1e,#121212);border:1px solid #292929;border-radius:24px;padding:25px 18px 18px;text-align:center;scroll-snap-align:start;transition:background .15s}.card:hover{background:#252525}.card strong{font-weight:500;font-size:18px;display:flex;align-items:center;justify-content:center;min-height:56px;margin-bottom:18px;line-height:1.35}.preview svg{display:block;width:100%;height:auto;border-radius:12px}.badge{position:absolute;right:12px;top:-22px;width:40px;height:48px}.badge svg{height:100%;width:100%}.check{position:absolute;right:10px;top:-19px;width:43px;height:43px;border-radius:12px;background:linear-gradient(120deg,#85e41a,#56cf09);color:white;font-size:36px;font-weight:700;line-height:43px}.catalog-tools{margin:10px 0 18px}.search-row{display:flex;align-items:center;gap:20px}.search-row input{border:0;border-radius:20px;background:#171717;color:white;padding:16px 22px;font:22px "Segoe UI",sans-serif;min-width:0;flex:1}.back{font-size:44px;background:none;line-height:1}.cancel{color:#858d94;background:none;font-size:18px}.filters{display:flex;margin:24px 0 8px;border-radius:22px;padding:5px;background:#171717}.filters button{background:transparent;color:#969da3;border-radius:17px;flex:1;padding:11px;font-size:18px}.filters button[aria-pressed=true]{background:#565e64;color:white}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:40px 24px;padding:28px 0}.grid .card{min-width:0;max-width:none;width:100%;padding:24px}.grid .card .preview{max-width:238px;display:block;margin:auto}.pagination{display:flex;justify-content:space-between;align-items:center;padding:22px 8px 10px;max-width:750px;margin:auto}.pagination button{background:none;font-size:30px;padding:4px 16px}.pagination button:disabled{color:#576168;cursor:var(--club-cursor-default,default)}.empty{text-align:center;padding:42px;color:#a2abb1}
    @media(max-width:850px){.card{flex-basis:calc((100% - 44px)/3);min-width:190px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.shelf-head h2{font-size:23px}}
    @media(max-width:500px){header strong{font-size:29px}header nav{gap:20px}.card{min-width:205px;padding:24px 14px 14px}.rail{gap:18px}.card strong{font-size:17px}.grid{gap:36px 14px}.grid .card{padding:20px 10px 12px;min-width:0}.grid .card strong{font-size:15px;min-height:48px}.search-row{gap:10px}.search-row input{font-size:18px;padding:14px}.cancel{font-size:14px}.filters button{font-size:16px}.check{width:35px;height:35px;line-height:35px;font-size:29px}.shelf-head button{font-size:12px}}
    header{padding:18px 22px;border:1px solid #2a3035;border-radius:24px;background:radial-gradient(ellipse at top right,#24251e,#15191c 65%);margin-bottom:22px}header strong{font-size:30px}header strong b{font-size:11px;border:1px solid #806121;background:#362c15;color:#f4c66b;border-radius:20px;padding:4px 8px}header nav{gap:12px;align-items:center}header button{width:46px;height:48px;border-radius:15px;background:#21272b;display:flex;align-items:center;justify-content:center;gap:5px}header button[data-action=streak]{width:78px;color:#ffbb64;font-weight:700}header button svg{width:25px;height:34px}header button:hover{background:#303a40}.card:hover{transform:translateY(-4px);border-color:#806132;box-shadow:0 12px 24px #0004}.card{transition:transform .2s,border-color .2s}.shelf-head h2{font-weight:650;font-size:23px}@media(max-width:500px){header{padding:14px 12px;border-radius:18px}header strong{font-size:21px}header strong b{font-size:9px;margin-left:2px}header nav{gap:6px}header button{width:34px;height:40px}header button[data-action=streak]{width:56px;font-size:13px}header button svg{width:20px;height:27px}.card{min-width:170px;border-radius:20px}.shelf-head h2{font-size:20px}.rail{gap:12px}.grid{gap:28px 12px}}
    @media(prefers-reduced-motion:reduce){.card{transition:none}}

    .home header,.home .card{background:linear-gradient(140deg,#073149,#031327)!important;border:1px solid #176f88!important;border-radius:5px!important;box-shadow:inset 0 1px #2deafa15,0 9px 22px #0003!important}
    .home header{border-top:2px solid #ff8737!important}.home .card:hover{border-color:#27d8e7!important}.home .card strong,.home .shelf-head h2{color:#bff7ff!important;font-family:Bahnschrift,'Segoe UI',sans-serif}.home header strong b{background:#0a4057!important;color:#6de5ef!important;border-color:#18829a!important}.home .filters,.home .search-row input,.home header button{background:#06283e!important;border-radius:4px!important;color:#9de8f4!important}.home .filters button[aria-pressed=true]{background:#09506a!important;color:#e2fbff!important}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}){
      const root=parentElement.querySelector('.home');let pending=false;
      const local=parentElement._view??{side:null,filter:'all',query:'',page:0};parentElement._view=local;
      const make=(tag,cls,text)=>{const e=document.createElement(tag);e.className=cls||'';if(text!==undefined)e.textContent=text;return e;};
      const emit=event=>{if(pending)return;pending=true;setTriggerValue('select',event);};
      root.querySelector('[data-action=streak]').innerHTML=data.flame+'<span>'+data.streak+'</span>';
      root.querySelector('[data-action=streak]').title=data.streak+' dias consecutivos de acesso';
      root.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>emit({action:b.dataset.action}));
      const input=root.querySelector('input');input.value=local.query;
      input.oninput=()=>{local.query=input.value;local.page=0;paint();};
      root.querySelector('.back').onclick=()=>{local.side=null;local.query='';local.filter='all';local.page=0;paint();};
      root.querySelector('.cancel').onclick=()=>{input.value=local.query='';local.filter='all';local.page=0;paint();};
      const filters=root.querySelector('.filters');filters.replaceChildren();
      [['all','Todos'],['e4','e4'],['d4','d4'],['other','Outro']].forEach(([id,label])=>{const b=make('button','',label);b.type='button';b.dataset.filter=id;b.onclick=()=>{local.filter=id;local.page=0;paint();};filters.append(b);});
      function card(c,grid){const b=make('button','card');b.type='button';b.dataset.id=c.id;b.setAttribute('aria-label',c.title+', '+(c.side==='white'?'brancas':'negras'));b.onclick=()=>emit({id:c.id});const preview=make('span','preview');preview.innerHTML=c.svg;b.append(make('strong','',c.title),preview);if(c.learned){const mark=make('span',grid?'check':'badge',grid?'✓':undefined);if(!grid)mark.innerHTML=data.badge;b.append(mark);}return b;}
      function paint(){
        root.querySelector('.catalog-tools').hidden=!local.side;root.querySelector('header').hidden=!!local.side;
        filters.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===local.filter)));
        const shelves=root.querySelector('.shelves');shelves.replaceChildren();
        const pages=root.querySelector('.pagination');pages.replaceChildren();pages.hidden=!local.side;
        if(!local.side){for(const [side,label] of [['white','Aberturas de Brancas'],['black','Aberturas de Negras']]){const section=make('section'),head=make('div','shelf-head'),all=make('button','','Ver todas ›');all.onclick=()=>{local.side=side;local.page=0;paint();};head.append(make('h2','',label),all);const rail=make('div','rail');rail.setAttribute('aria-label',label);data.courses.filter(c=>c.side===side&&c.featured).forEach(c=>rail.append(card(c,false)));section.append(head,rail);shelves.append(section);}root.querySelector('.empty').hidden=true;return;}
        const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
        const list=data.courses.filter(c=>c.side===local.side&&(local.filter==='all'||c.first_move===local.filter)&&normalize(c.title+' '+c.alias).includes(normalize(local.query)));
        const total=Math.max(1,Math.ceil(list.length/6));local.page=Math.min(local.page,total-1);
        const grid=make('div','grid');list.slice(local.page*6,local.page*6+6).forEach(c=>grid.append(card(c,true)));shelves.append(grid);
        const nav=(label,aria,target)=>{const b=make('button','',label);b.type='button';b.setAttribute('aria-label',aria);b.disabled=target<0||target>=total||target===local.page;b.onclick=()=>{local.page=target;paint();root.scrollIntoView({block:'start'});};return b;};
        pages.append(nav('«','Primeira página',0),nav('‹','Página anterior',local.page-1),make('span','',`${local.page+1}/${total}`),nav('›','Próxima página',local.page+1),nav('»','Última página',total-1));
        root.querySelector('.empty').hidden=list.length>0;pages.hidden=list.length===0;
      }paint();
    }''',
)

@st.cache_data(show_spinner=False)
def reference_cards():
    featured={'italian','queens_gambit','london','english','sicilian_white','french_white','caro','sicilian','french','kings_indian','slav','nimzo'}
    result=[]
    for course in catalog():
        first=course['notation'].split()[0].split('.')[-1]
        result.append(dict(id=course['id'],title=display_name(course),alias=course['title'],side=course['side'],first_move=first if first in ('e4','d4') else 'other',featured=course['id'] in featured,
            svg=chess.svg.board(chess.Board(course['fen']),orientation=course['side']=='white',coordinates=False,size=240,colors={'square light':'#efdcba','square dark':'#af8b68'})))
    order=['italian','queens_gambit','london','english','caro','sicilian']
    result.sort(key=lambda c:order.index(c['id']) if c['id'] in order else len(order))
    return result


@st.cache_resource
def reference_cards_job():
    """Build the offline catalogue outside the UI thread, once per server."""
    pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='opening-catalog')
    job=pool.submit(reference_cards)
    pool.shutdown(wait=False)
    return job


def opening_home(plan,on_select,allowed_ids=None):
    job=reference_cards_job()
    if not job.done():
        @st.fragment(run_every=.3)
        def ready():
            if job.done():st.rerun()
            st.caption('Preparando os cursos em segundo plano… Você já pode usar as outras abas.')
        ready()
        return
    try:prepared=job.result()
    except Exception:
        st.error('Não foi possível preparar os cursos locais.')
        if st.button('Tentar novamente',key='retry_opening_catalog'):
            reference_cards_job.clear();st.rerun()
        return
    ranking={row['id']:row for row in opening_rankings(plan)}
    cards=[dict(c,learned=ranking[c['id']]['learned'],featured=True if allowed_ids is not None else c['featured'])
           for c in prepared if allowed_ids is None or c['id'] in allowed_ids]
    _HOME(data=dict(courses=cards,flame=flame(st.session_state.get('login_streak',streak(plan))),streak=st.session_state.get('login_streak',streak(plan)),badge=badge()),key='openings_home',on_select_change=on_select)
