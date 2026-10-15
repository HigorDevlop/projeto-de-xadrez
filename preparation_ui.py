"""Trilha acessível de dias e estilos do preparo em foco."""
from datetime import date, timedelta
import streamlit as st
from design_tokens import palette
from preparation_state import STAGES, today


_ROADMAP = st.components.v2.component(
    'preparation_roadmap',
    html='<section class="trail" aria-label="Trilha de treino"><div class="path"><svg aria-hidden="true"></svg><div class="days"></div></div></section>',
    css='''
    .trail{max-height:490px;overflow:auto;padding:20px 12px;scrollbar-width:thin;background:var(--soft);border-radius:20px}
    .path{position:relative;margin:auto}.path>svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}
    .days{display:grid;position:relative;gap:32px 24px;justify-items:center}
    .day{appearance:none;box-sizing:border-box;width:100%;max-width:104px;aspect-ratio:1;border:2px solid var(--border);border-radius:16px;background:var(--surface);color:var(--ink);font:600 16px/1.3 'Segoe UI',sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;cursor:pointer;box-shadow:0 5px 0 var(--border)}
    .day small{font-size:11px;font-weight:500}.day strong{font-size:24px}.day:disabled{cursor:default;color:var(--muted)}
    .day.current{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);box-shadow:0 5px 0 var(--border),0 0 0 6px var(--surface)}
    .day.done{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
    .day:focus-visible{outline:3px solid var(--gold);outline-offset:5px}.day:not(:disabled):hover{filter:brightness(1.08)}
    .trail.repertoire{background:#081219;max-height:600px;padding:36px 24px}
    .repertoire .path{max-width:420px}.repertoire .days{gap:36px}
    .repertoire .path>svg{opacity:.18}
    .repertoire .day{width:100px;max-width:100px;border-radius:50%;background:#232c32;color:#8c979e;border:0;box-shadow:none}
    .repertoire .day.current{background:linear-gradient(140deg,#d74600,#fc8400);color:#fff;box-shadow:0 0 0 7px #081219,0 0 0 13px #f17719}
    .repertoire .day.done{background:#a879cc;color:white}
    .repertoire .day strong{font-size:30px}.repertoire .day small{font-size:10px}
    .repertoire .day strong svg{width:38px;height:38px;display:block;fill:currentColor}
    @media(prefers-reduced-motion:reduce){.day{transition:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}) {
      const host=parentElement.host??parentElement, trail=parentElement.querySelector('.trail');
      const grid=parentElement.querySelector('.days'),svg=parentElement.querySelector('svg');
      trail.classList.toggle('repertoire',Boolean(data.repertoire));
      Object.entries(data.colors).forEach(([key,value])=>host.style.setProperty('--'+key.replaceAll('_','-'),value));
      let previousCols=0;
      function paint(){
        const columns=data.repertoire?1:Math.min(data.days.length,trail.clientWidth<520?3:5);
        if(columns===previousCols && grid.children.length)return;
        previousCols=columns;grid.replaceChildren();grid.style.gridTemplateColumns=`repeat(${columns},minmax(0,1fr))`;
        data.days.forEach((day,index)=>{
          const row=Math.floor(index/columns),col=row%2?columns-index%columns:index%columns+1;
          const button=document.createElement('button');button.type='button';button.className='day '+day.status;
          button.style.gridRow=row+1;button.style.gridColumn=col;button.disabled=!day.enabled;
          if(data.repertoire)button.style.transform=`translateX(${[0,55,0,-55][index%4]}px)`;
          button.dataset.date=day.date;button.setAttribute('aria-label',day.label+' · '+day.description);
          if(day.current)button.setAttribute('aria-current','date');
          const title=document.createElement('span');title.textContent=data.repertoire?'':'Dia';
          const number=document.createElement('strong');number.textContent=data.repertoire?(day.status==='done'?'✓':index%2?'▶':'▣'):day.number;
          if(data.repertoire && day.status!=='done' && index%2===0){
            number.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5.5C8.8 3.4 5 3.5 2 4.4v14c3-.9 6.8-1 10 1.1 3.2-2.1 7-2 10-1.1v-14c-3-.9-6.8-1-10 1.1Zm-1 11.3c-2.4-1-4.7-1.1-7-.7V6c2.3-.4 4.6-.3 7 .9v9.9Zm9-.7c-2.3-.4-4.6-.3-7 .7V6.9c2.4-1.2 4.7-1.3 7-.9v10.1Z"/></svg>';
          }
          const month=document.createElement('small');month.textContent=(data.repertoire?day.number+' ':'')+day.month;
          const status=document.createElement('small');status.textContent=day.description;
          button.append(title,number,month,status);
          button.onclick=()=>{button.disabled=true;setTriggerValue('select',{day:day.date,plan:data.plan});};
          grid.append(button);
        });
        requestAnimationFrame(draw);
      }
      function draw(){
        const bounds=grid.getBoundingClientRect(),points=[...grid.children].map(el=>{const r=el.getBoundingClientRect();return [r.x-bounds.x+r.width/2,r.y-bounds.y+r.height/2]});
        svg.setAttribute('viewBox',`0 0 ${bounds.width} ${bounds.height}`);svg.replaceChildren();
        const path=document.createElementNS('http://www.w3.org/2000/svg','polyline');
        path.setAttribute('points',points.map(p=>p.join(',')).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke',data.colors.border);path.setAttribute('stroke-width','12');path.setAttribute('stroke-linejoin','round');svg.append(path);
        if(!parentElement._scrolled){const current=grid.querySelector('[aria-current]');if(current)trail.scrollTop=Math.max(0,current.offsetTop-120);parentElement._scrolled=true;}
      }
      const observer=new ResizeObserver(()=>{paint();requestAnimationFrame(draw)});observer.observe(trail);paint();
      return()=>observer.disconnect();
    }''',
)


def roadmap(plan, on_select, dark=False):
    first, last = date.fromisoformat(plan['start']), date.fromisoformat(plan['end'])
    current, days = today(), []
    months = ('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez')
    for index in range((last-first).days+1):
        day = first + timedelta(days=index)
        progress = plan['days'].get(str(day), {})
        if plan.get('repertoire_mode'):
            record = plan.get('training_days', {}).get(str(day), {})
            done = record.get('phase') == 'complete'
        else:
            done = all(progress.get(stage, {}).get('done', False) for stage in STAGES)
        enabled = day == current and not done and not plan.get('finished')
        status = 'done' if done else 'current' if enabled else 'locked'
        description = 'Concluído' if done else 'Treinar' if enabled else 'Encerrado' if day < current else 'Bloqueado'
        days.append(dict(date=str(day), number=day.day, month=f'{months[day.month-1]} {day.year}',
                         label=f'Dia {day.day}', description=description, enabled=enabled,
                         status=status, current=day == current))
    _ROADMAP(data={'days': days, 'plan': plan['created'], 'colors': palette(dark),
                   'repertoire': bool(plan.get('repertoire_mode'))},
             key='prep_roadmap', on_select_change=on_select)


STYLE = '''
.st-key-prep_repetition_board{width:min(100%,780px)!important;margin-inline:auto}

.prep-steps{display:flex;gap:8px;margin:12px 0 20px}.prep-step{display:grid;place-items:center;width:32px;height:32px;border-radius:8px;background:var(--chess-soft);color:var(--chess-ink);border:1px solid var(--chess-border)}
.prep-step.correct{background:#176B4A;color:#fff}.prep-step.wrong{background:#B7273F;color:#fff}.prep-phase{color:var(--chess-accent);font-size:13px;font-weight:600}
[class*="st-key-prep_opening_card_"]{background:var(--chess-surface);border:1px solid var(--chess-border);border-radius:14px;padding:16px!important}
[class*="st-key-prep_opening_card_"]:has(button[kind="primary"]){border:2px solid var(--chess-accent);background:var(--chess-accent-soft)}
[class*="st-key-prep_opening_card_"] button{width:100%;min-height:68px;white-space:normal}[class*="st-key-prep_opening_card_"] button p{white-space:normal!important}
.prep-card-art{height:48px;display:flex;align-items:center;gap:12px;color:var(--chess-accent);font:38px Georgia,serif}.prep-card-art small{font:12px 'Segoe UI',sans-serif;color:var(--chess-muted)}
.st-key-prep_day_card{margin:24px auto;max-width:760px;padding:24px;background:var(--chess-surface);border:1px solid var(--chess-border);border-radius:18px}
.prep-day-image{max-width:220px;margin:auto}.prep-day-image svg{width:100%;height:auto;border-radius:8px}
.prep-status{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.prep-status span{border-radius:7px;padding:7px 10px;background:var(--chess-soft);color:var(--chess-muted);font-size:12px}.prep-status .done{background:var(--chess-accent-soft);color:var(--chess-accent)}
.stApp:has(.prep-plan-mode) .st-key-page_heading,.stApp:has(.prep-plan-mode) .st-key-workspace_identity{display:none}
.stApp:has(.prep-plan-mode) .st-key-question_launcher,.stApp:has(.prep-plan-mode) .st-key-navigation_back{display:none!important}
.stApp:has(.prep-focus-mode) [data-testid="stSidebar"],.stApp:has(.prep-focus-mode) [data-testid="stHeader"],.stApp:has(.prep-focus-mode) .st-key-question_launcher,.stApp:has(.prep-focus-mode) .st-key-navigation_back{display:none!important}
.stApp:has(.prep-focus-mode) .stMainBlockContainer{padding-top:110px;max-width:1320px}
.st-key-prep_clock{position:fixed;top:0;left:0;right:0;width:100%!important;z-index:99999;background:var(--chess-surface);border-bottom:1px solid var(--chess-border);padding:14px max(20px,calc((100vw - 1170px)/2));align-items:center;gap:16px}
.prep-clock{font:600 24px/1.2 'Segoe UI',sans-serif;font-variant-numeric:tabular-nums;color:var(--chess-ink)}.prep-clock small{display:block;font-size:11px;font-weight:500;letter-spacing:.06em;color:var(--chess-muted);margin-bottom:5px}
body:has(.prep-finished-mode) [data-testid="stAppViewContainer"]{filter:blur(8px);pointer-events:none;user-select:none}
body:has(.prep-finished-mode) [data-testid="stDialog"]{backdrop-filter:blur(8px)}
body:has(.prep-finished-mode) [data-testid="stDialog"] [role="dialog"]{position:fixed!important;top:50%!important;left:50%!important;transform:translate(-50%,-50%);margin:0!important;width:min(500px,calc(100vw - 32px));max-height:calc(100dvh - 48px);overflow:auto}
@media(max-width:640px){.st-key-prep_clock{padding:12px 16px}.prep-clock{font-size:21px}.st-key-prep_clock button{font-size:12px}.st-key-prep_day_card{padding:16px}.stApp:has(.prep-focus-mode) .stMainBlockContainer{padding-top:110px}}
'''
