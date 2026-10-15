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
    *{box-sizing:border-box}
.course-trail{font-family:"Segoe UI",sans-serif;position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:55px 20px;padding:34px 45px 50px;min-height:260px}.step{position:relative;display:flex;align-items:center;flex-direction:column;gap:13px;color:#91999f;min-height:142px}.step:nth-child(even){padding-top:45px}.node{border:0;border-radius:50%;background:#242c32;color:#4c575f;width:94px;height:94px;padding:26px;cursor:pointer}.node svg{width:100%;height:100%}.node.current{background:linear-gradient(140deg,#8a22c8,#d60024,#ff8500);color:white;outline:9px solid #dc001e;outline-offset:7px}.node.learned{background:linear-gradient(130deg,#46ce91,#23ac71);color:white}.node:disabled{cursor:default}.node:focus-visible{outline:5px solid #ff8a00;outline-offset:12px}.label{font-size:12px;text-align:center;max-width:180px}.start{position:absolute;top:-31px;left:50%;translate:-50% 0;background:white;border-radius:15px;padding:9px 14px;color:#d50016;font-size:13px;font-weight:700;white-space:nowrap}.step:nth-child(even) .start{top:14px}.start:after{content:"";position:absolute;bottom:-8px;left:calc(50% - 8px);border-left:8px solid transparent;border-right:8px solid transparent;border-top:8px solid white}@media(max-width:700px){.course-trail{grid-template-columns:repeat(2,1fr);padding:35px 20px;gap:30px 10px}.node{width:90px;height:90px}.label{font-size:11px}}''',
    js='''export default function({data,parentElement,setTriggerValue}){
const root=parentElement.querySelector('.course-trail');root.replaceChildren();let current=false;data.lines.forEach(line=>{const step=document.createElement('div');step.className='step';const button=document.createElement('button');button.className='node '+(line.learned?'learned':line.unlocked&&!current?'current':'');button.type='button';button.disabled=!line.unlocked;button.dataset.line=line.id;button.setAttribute('aria-label','Estudar linha '+line.number);button.innerHTML=data.star;button.onclick=()=>setTriggerValue('select',{id:line.id,mode:'learn',token:data.token});if(line.unlocked&&!line.learned&&!current){const flag=document.createElement('span');flag.className='start';flag.textContent='COMEÇAR';step.append(flag);current=true;}const copy=document.createElement('span');copy.className='label';copy.textContent='Linha '+line.number+(line.learned?' · Concluída':'');step.append(button,copy);root.append(step);});}''')


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
    TRAIL(data=dict(lines=course_lines(plan),star=STAR,token=plan['created']),
          key='openings_trail',on_select_change=on_select)


def celebrate(plan, kind, on_continue):
    is_streak = kind.startswith('streak')
    count = streak(plan)
    known, total = position_progress(plan) if plan else (0,0)
    target = min(total,25)
    confetti = '<div class="reference-confetti">'+''.join(
        f'<i style="--x:{(i*29+7)%97}%;--y:{(i*17+11)%89}%;--r:{i*41}deg;--c:{["#258ee1","#f61e70","#ff9d00","#9026bf"][i%4]}"></i>' for i in range(14))+'</div>'
    if is_streak:
        visual = '<div class="reference-flame">'+svg_image(FLAME)+f'<strong>{count}</strong></div>'
        days = activity_days(plan)
        week = [today()-timedelta(days=6-i) for i in range(7)]
        calendar = '<div class="reference-week">'+''.join(f'<span class="{"done" if str(day) in days else ""}">{"STQQSSD"[day.weekday()]}</span>' for day in week)+'</div>'
        body = '<h1>'+('Você salvou seu streak!' if str(today()) in days else 'Sua sequência diária')+'</h1>'+visual+'<h2>Streak diária</h2>'+calendar+'<p>Dica: Treine amanhã para não perder seu streak</p>'
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
    for row in rows:
        header = 'WhiteElo' if row['side']=='white' else 'BlackElo'
        raw = row['game'].headers.get(header,'')
        row['actual_rating'] = int(raw) if raw.isdigit() else None
    return rows


def profile(history, username):
    rows = profile_records(history or [],username)
    st.html(title_html('Perfil',medal=False))
    period=st.segmented_control('Período',['1S','1M','3M','1A'],default='1M',label_visibility='collapsed',width='stretch') or '1M'
    start=today()-timedelta(days={'1S':7,'1M':30,'3M':90,'1A':365}[period]-1)
    filtered=[r for r in rows if r['outcome'] is not None and r['timestamp'] and start<=datetime.fromtimestamp(r['timestamp'],LOCAL_ZONE).date()<=today()]
    ratings=[r for r in reversed(filtered) if r['actual_rating'] is not None]
    chart='<p style="color:#949fa7">Nenhum rating registrado neste período.</p>'
    if ratings:
        values=[r['actual_rating'] for r in ratings];low=min(values)-30;high=max(values)+30
        left=ratings[0]['timestamp'];span=max(1,ratings[-1]['timestamp']-left)
        points=' '.join(f'{60+((r["timestamp"]-left)/span)*770:.1f},{270-((r["actual_rating"]-low)/(high-low))*215:.1f}' for r in ratings)
        grid=''.join(f'<line x1="55" y1="{55+i*54}" x2="835" y2="{55+i*54}" stroke="#626c73"/><text x="0" y="{60+i*54}" fill="#929ca4" font-size="14">{round(high-i*(high-low)/4)}</text>' for i in range(5))
        delta=values[-1]-values[0]
        chart=f'<div style="display:flex;justify-content:space-between;font-size:24px"><b>{values[-1]}</b><span style="color:{"#54ba24" if delta>=0 else "#ed514d"}">{delta:+}</span></div><svg viewBox="0 0 850 320" role="img" aria-label="Evolução do rating">{grid}<polyline points="{points}" fill="none" stroke="#ff7908" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><text x="55" y="310" fill="#929ca4" font-size="14">{start.strftime("%d.%m.%Y")}</text><text x="835" y="310" text-anchor="end" fill="#929ca4" font-size="14">{today().strftime("%d.%m.%Y")}</text></svg>'
    if '<svg' in chart:
        offset = chart.index('<svg')
        chart = chart[:offset] + svg_image(chart[offset:], 'Evolução do rating')
    st.html('<section class="reference-profile-card">'+chart+'</section>')
    groups=defaultdict(list)
    for row in filtered:
        groups[(row['opening'],row['side'])].append(row)
    winrate=100*sum(r['outcome']=='wins' for r in filtered)/len(filtered) if filtered else 0
    table=[]
    for (name,side),games in sorted(groups.items(),key=lambda item:-sum(g['outcome']=='wins' for g in item[1])/len(item[1])):
        rate=100*sum(g['outcome']=='wins' for g in games)/len(games);delta=rate-winrate
        table.append(f'<tr><td class="rate">{rate:.0f}%</td><td>{"●" if side=="white" else "○"} {escape(name)}</td><td class="{"plus" if delta>=0 else "minus"}">{delta:+.0f}%</td><td>{len(games)}</td></tr>')
    st.html('<section class="reference-profile-card"><h3>Taxa de vitórias por abertura</h3>'
        '<table><thead><tr><th>WINRATE</th><th>ABERTURA</th><th>DIF. P/ WINRATE MÉDIA</th><th>PARTIDAS</th></tr></thead><tbody>'+''.join(table)+'</tbody></table>'
        + ('<p style="color:#9ca6ad">Conecte sua conta em Partidas para carregar seu histórico.</p>' if not filtered else '')+'</section>')
    wins=[r for r in filtered if r['outcome']=='wins']
    opponent=[r['game'].headers.get('BlackElo' if r['side']=='white' else 'WhiteElo','') for r in wins]
    best=max([int(v) for v in opponent if v.isdigit()],default=0)
    st.html('<section class="reference-profile-card">'+''.join(f'<div class="stat"><span>{label}</span><strong>{value}</strong></div>' for label,value in [('Taxa de vitórias',f'{winrate:.0f}%' if filtered else '—'),('Melhor vitória',best or '—'),('Partidas jogadas',len(filtered))])+'</section>')
    st.caption('Estatísticas das partidas carregadas, no período selecionado.')
