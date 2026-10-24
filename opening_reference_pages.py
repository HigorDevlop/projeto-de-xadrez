"""Course trail, achievement, streak and profile screens from the reference model."""
from collections import defaultdict
from datetime import datetime, timedelta
from html import escape
import streamlit as st
from opening_reference_style import badge, FLAME, STAR, title_html, svg_image
from opening_reference_progress import position_progress, activity_days, streak
from preparation_state import today, LOCAL_ZONE


TRAIL = st.components.v2.component('reference_star_trail',
    html='<div class="course-trail" role="group" aria-label="Trilha do curso"></div>',
    css='''
    *{box-sizing:border-box}.trail-section{grid-column:1/-1;font:600 14px system-ui;color:#c9b28a;margin:10px 0 8px;padding:12px 0;border-bottom:1px solid #ffffff12}
.course-trail{font-family:"Segoe UI",sans-serif;position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:55px 20px;padding:34px 45px 50px;min-height:260px}.step{position:relative;display:flex;align-items:center;flex-direction:column;gap:13px;color:#91999f;min-height:142px}.step:nth-child(even){padding-top:45px}.node{border:0;border-radius:50%;background:#171717;color:#4c575f;width:94px;height:94px;padding:26px;cursor:var(--club-cursor-link,pointer)}.node svg{width:100%;height:100%}.node.current{background:linear-gradient(140deg,#8a22c8,#d60024,#ff8500);color:white;outline:9px solid #dc001e;outline-offset:7px}.node.learned{background:linear-gradient(130deg,#46ce91,#23ac71);color:white}.node:disabled{cursor:var(--club-cursor-default,default)}.node:focus-visible{outline:5px solid #ff8a00;outline-offset:12px}.label{font-size:12px;text-align:center;max-width:180px}.start{position:absolute;top:-31px;left:50%;translate:-50% 0;background:white;border-radius:15px;padding:9px 14px;color:#d50016;font-size:13px;font-weight:700;white-space:nowrap}.step:nth-child(even) .start{top:14px}.start:after{content:"";position:absolute;bottom:-8px;left:calc(50% - 8px);border-left:8px solid transparent;border-right:8px solid transparent;border-top:8px solid white}@media(max-width:700px){.course-trail{grid-template-columns:repeat(2,1fr);padding:35px 20px;gap:30px 10px}.node{width:90px;height:90px}.label{font-size:11px}}''',
    js='''export default function({data,parentElement,setTriggerValue}){
const root=parentElement.querySelector('.course-trail');root.replaceChildren();let current=false;data.lines.forEach((line,index)=>{if(line.stage&&(index===0||line.stage!==data.lines[index-1].stage||(line.stage==='depth'&&line.branch!==data.lines[index-1].branch))){const heading=document.createElement('h3');heading.className='trail-section';heading.textContent=line.stage==='foundation'?'Linhas principais':'Aprofundamento · Linha '+line.branch;root.append(heading);}const step=document.createElement('div');step.className='step';const button=document.createElement('button');button.className='node '+(line.learned?'learned':line.unlocked&&!current?'current':'');button.type='button';button.disabled=!line.unlocked;button.dataset.line=line.id;button.setAttribute('aria-label','Estudar linha '+line.number);button.innerHTML=data.star;button.onclick=()=>setTriggerValue('select',{id:line.id,mode:'learn',token:data.token});if(line.unlocked&&!line.learned&&!current){const flag=document.createElement('span');flag.className='start';flag.textContent='COMEÇAR';step.append(flag);current=true;}const copy=document.createElement('span');copy.className='label';copy.textContent=(line.variation||'Linha '+line.number)+(line.learned?' · Concluída':'');step.append(button,copy);root.append(step);});}''')


def rank_card(plan):
    known, total = position_progress(plan)
    target = min(25, total)
    complete = known >= target and target > 0
    st.html('<section class="reference-rank" aria-label="Progresso da abertura">'
        '<div class="reference-rank-labels"><div>Rank atual<strong>Iniciante</strong></div>'
        '<div>Próximo rank<strong>Iniciante</strong></div></div><div class="reference-rank-path">'
        '<span style="color:white;font-size:30px">‹</span><span class="medal">'+svg_image(badge('#35bd7e' if complete else '#ff8b00',int(complete)), 'Medalha atual')+'</span>'
        '<span class="path"></span><span class="square"></span><span class="path"></span><span class="medal future">'+svg_image(badge('#74818b'), 'Próxima medalha')+'</span>'
        '<span style="color:white;font-size:30px">›</span></div>'
        f'<p class="reference-rank-caption">{min(known,target)}/{target} posições aprendidas</p></section>')


def render_trail(plan, on_select):
    from opening_course_state import course_lines
    from opening_rounds import cycle,phases,next_lesson
    if cycle(plan) is not None:
        from opening_phase_trail import TRAIL as PHASE_TRAIL
        available,source=next_lesson(plan,course_lines(plan))
        PHASE_TRAIL(data=dict(phases=phases(plan),currentLine=(available or source or {}).get('id'),token=plan['created']),
                    key='openings_trail',on_select_change=on_select)
    else:
        TRAIL(data=dict(lines=course_lines(plan),star=STAR,token=plan['created']),key='openings_trail',on_select_change=on_select)


def celebrate(plan, kind, on_continue):
    is_streak = kind.startswith('streak')
    count = st.session_state.get('login_streak',streak(plan))
    from streak_style import flame
    known, total = position_progress(plan) if plan else (0,0)
    target = min(total,25)
    confetti = '<div class="reference-confetti">'+''.join(
        f'<i style="--x:{(i*29+7)%97}%;--y:{(i*17+11)%89}%;--r:{i*41}deg;--c:{["#258ee1","#f61e70","#ff9d00","#9026bf"][i%4]}"></i>' for i in range(14))+'</div>'
    if is_streak:
        visual = '<div class="reference-flame">'+svg_image(flame(count))+f'<strong>{count}</strong></div>'
        days = activity_days(plan)
        if token:=st.session_state.get('classroom_token'):
            import classroom as rooms
            with rooms.database() as db:
                actor=rooms._identity(db,token)
                days={row[0] for row in db.execute('SELECT day FROM login_days WHERE role=? AND owner=?',(actor['role'],actor['id']))}
        week = [today()-timedelta(days=6-i) for i in range(7)]
        calendar = '<div class="reference-week">'+''.join(f'<span class="{"done" if str(day) in days else ""}">{"STQQSSD"[day.weekday()]}</span>' for day in week)+'</div>'
        body = '<h1>'+('Você salvou seu streak!' if str(today()) in days else 'Sua sequência diária')+'</h1>'+visual+'<h2>Dias consecutivos de acesso</h2>'+calendar+'<p>Volte amanhã para manter sua sequência</p>'
    else:
        ring = '<svg viewBox="0 0 260 280"><circle cx="130" cy="130" r="111" fill="none" stroke="#34bd7c" stroke-width="20" stroke-dasharray="590 110" transform="rotate(110 130 130)" stroke-linecap="round"/></svg>'
        visual = '<div class="reference-award">'+svg_image(ring)+'<div class="medal">'+svg_image(badge())+'</div>'+f'<strong>{min(known,target)}/{target}</strong></div>'
        body = '<h1>Parabéns!</h1>'+visual+'<h2>Novo ranking!</h2>'+f'<p>Ao aprender as {target} posições, você conquistou o título de Iniciante!</p>'
    st.html('<section class="reference-celebration">'+confetti+body+'</section>')
    with st.container(key='reference_reward_streak' if is_streak else 'reference_reward_award'):
        if st.button('Continuar',type='primary',width='stretch',key='reference_reward_continue'):
            on_continue()
            st.rerun()


@st.cache_data(show_spinner=False,max_entries=8)
def profile_records(history, username):
    from preparation_data import _records
    rows = _records(history, username)
    # Reject the parser's fallback rating; the graph uses recorded ratings only.
    by_id={item.get('url'):item for item in history if isinstance(item,dict) and item.get('url')}
    for row in rows:
        header = 'WhiteElo' if row['side']=='white' else 'BlackElo'
        raw = row['game'].headers.get(header,'')
        row['actual_rating'] = int(raw) if raw.isdigit() else None
        row['time_class'] = by_id.get(row['id'],{}).get('time_class') or 'Geral'
    return rows


def profile(history, username):
    rows = profile_records(history or [],username)
    st.html('''<style>
    .st-key-profile_compact{max-width:1040px;margin:0 auto}.profile-heading{display:flex;justify-content:space-between;align-items:end;margin:4px 0 18px}.profile-heading h1{font:650 30px/1.2 system-ui!important;margin:0!important;letter-spacing:-.8px}.profile-heading p{font:12px system-ui;color:#9a958c;margin:7px 0 0}.profile-kicker{font:600 10px system-ui;letter-spacing:2px;color:#c3a16b;margin:0 0 9px;display:block}
    .profile-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}.profile-summary>div{padding:17px 19px;border:1px solid #38352f;border-radius:14px;background:linear-gradient(140deg,#25231f,#191918)}.profile-summary small{font:11px system-ui;color:#a6a197}.profile-summary strong{display:block;font:650 27px/1.4 system-ui;color:#eee9e0;margin-top:6px}.profile-summary em{font:11px system-ui;font-style:normal;color:#9e988c}
    .st-key-profile_compact .reference-profile-card{border-radius:16px;padding:22px;margin-bottom:16px}.profile-chart-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.profile-chart-head h3{font:600 15px system-ui!important;margin:0!important}.profile-change{font:600 12px system-ui;border-radius:20px;padding:6px 10px;background:#ffffff06}.st-key-profile_compact .reference-profile-card>img{display:block;width:100%;height:230px;object-fit:fill}.st-key-profile_compact .reference-profile-card h3{font-size:17px!important}.st-key-profile_compact .reference-profile-card th{font:10px system-ui;color:#89867e}.st-key-profile_compact .reference-profile-card td{font:13px/1.5 system-ui;padding:12px 8px;border-bottom:1px solid #ffffff0a!important}.st-key-profile_compact .reference-profile-card th{border-bottom:1px solid #ffffff10!important}
    @media(max-width:600px){.profile-summary{gap:7px}.profile-summary>div{padding:12px 10px}.profile-summary strong{font-size:22px}.profile-summary small{font-size:10px}.st-key-profile_compact .reference-profile-card{padding:14px}.st-key-profile_compact .reference-profile-card>img{height:185px}.st-key-profile_compact .reference-profile-card td{font-size:11px;padding:10px 4px}}
    </style>''')
    with st.container(key='profile_compact'):
        _profile_content(rows, username)


def _profile_content(rows, username):
    st.html('<header class="profile-heading"><div><span class="profile-kicker">SEU XADREZ EM NÚMEROS</span><h1>Perfil</h1><p>'+escape(username or 'Jogador')+'</p></div></header>')
    names={'blitz':'Blitz','rapid':'Rápidas','bullet':'Bullet','daily':'Diárias','Geral':'Geral'}
    modes=sorted({row['time_class'] for row in rows}) or ['Geral']
    default=max(modes,key=lambda mode:sum(row['time_class']==mode for row in rows))
    controls,mode_column=st.columns([2,1],vertical_alignment='bottom')
    with mode_column:
        mode=st.selectbox('Ritmo',modes,index=modes.index(default),format_func=lambda value:names.get(value,value),key='profile_time_class')
    with controls:
        period=st.segmented_control('Período',['1S','1M','3M','1A'],default='1M',label_visibility='collapsed',width='stretch') or '1M'
    start=today()-timedelta(days={'1S':7,'1M':30,'3M':90,'1A':365}[period]-1)
    filtered=[r for r in rows if r['time_class']==mode and r['outcome'] is not None and r['timestamp'] and start<=datetime.fromtimestamp(r['timestamp'],LOCAL_ZONE).date()<=today()]
    ratings=[r for r in reversed(filtered) if r['actual_rating'] is not None]
    winrate=100*sum(r['outcome']=='wins' for r in filtered)/len(filtered) if filtered else 0
    latest=ratings[-1]['actual_rating'] if ratings else '—'
    st.html('<div class="profile-summary">'+''.join('<div><small>'+label+'</small><strong>'+str(value)+'</strong><em>'+detail+'</em></div>' for label,value,detail in [('Rating',latest,names.get(mode,mode)),('Vitórias',f'{winrate:.0f}%' if filtered else '—','no período'),('Partidas',len(filtered),'histórico carregado')])+'</div>')
    chart='<p style="color:#949fa7;font:13px system-ui">Nenhum rating registrado neste período.</p>'
    if ratings:
        values=[r['actual_rating'] for r in ratings];low=min(values)-30;high=max(values)+30
        left=ratings[0]['timestamp'];span=max(1,ratings[-1]['timestamp']-left)
        points=' '.join(f'{55+((r["timestamp"]-left)/span)*770:.1f},{195-((r["actual_rating"]-low)/(high-low))*165:.1f}' for r in ratings)
        grid=''.join(f'<line x1="50" y1="{30+i*55}" x2="835" y2="{30+i*55}" stroke="#ffffff12"/><text x="0" y="{34+i*55}" fill="#8c8981" font-family="sans-serif" font-size="11">{round(high-i*(high-low)/3)}</text>' for i in range(4))
        delta=values[-1]-values[0]
        chart=f'<div class="profile-chart-head"><h3>Evolução do rating</h3><span class="profile-change" style="color:{"#89bf82" if delta>=0 else "#de837b"}">{delta:+} pontos</span></div><svg viewBox="0 0 850 230" role="img" aria-label="Evolução do rating">{grid}<polyline points="{points}" fill="none" stroke="#d7a464" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><text x="50" y="224" fill="#8c8981" font-family="sans-serif" font-size="11">{start.strftime("%d/%m")}</text><text x="835" y="224" text-anchor="end" fill="#8c8981" font-family="sans-serif" font-size="11">{today().strftime("%d/%m")}</text></svg>'
    if '<svg' in chart:
        offset = chart.index('<svg')
        chart = chart[:offset] + svg_image(chart[offset:], 'Evolução do rating')
    st.html('<section class="reference-profile-card">'+chart+'</section>')
    groups=defaultdict(list)
    for row in filtered:
        groups[(row['opening'],row['side'])].append(row)
    winrate=100*sum(r['outcome']=='wins' for r in filtered)/len(filtered) if filtered else 0
    table=[]
    for (name,side),games in sorted(groups.items(),key=lambda item:-len(item[1])):
        rate=100*sum(g['outcome']=='wins' for g in games)/len(games);delta=rate-winrate
        table.append(f'<tr><td class="rate">{rate:.0f}%</td><td>{"●" if side=="white" else "○"} {escape(name)}</td><td class="{"plus" if delta>=0 else "minus"}">{delta:+.0f}%</td><td>{len(games)}</td></tr>')
    st.html('<section class="reference-profile-card"><h3>Suas aberturas</h3>'
        '<table><thead><tr><th>Vitórias</th><th>Abertura</th><th>vs. média</th><th>Jogos</th></tr></thead><tbody>'+''.join(table[:5])+'</tbody></table>'
        + ('<p style="color:#9ca6ad">Conecte sua conta em Partidas para carregar seu histórico.</p>' if not filtered else '')+'</section>')
    if len(table)>5:
        with st.expander('Ver todas as aberturas'):
            st.html('<section class="reference-profile-card"><table><tbody>'+''.join(table)+'</tbody></table></section>')
    st.caption('Estatísticas das partidas carregadas, no período selecionado.')
