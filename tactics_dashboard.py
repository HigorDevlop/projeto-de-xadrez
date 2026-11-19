"""Compact tactics telemetry, including a client-side resolution clock."""
import streamlit as st

DASHBOARD=st.components.v2.component('tactics_compact_stats',
    html='''<section class="tactic-data"><header><span>ESTE TREINO</span><span class="solved"></span></header><div class="pie-row"><div class="pie" role="img"><div><strong class="accuracy"></strong><small>acertos</small></div></div><div class="pie-legend"><div><i></i>Acertos <b class="hits"></b></div><div><i></i>Erros <b class="errors"></b></div></div></div><div class="data-grid"><div class="prepare-cell"><small>Preparo</small><strong class="prepare"></strong><div class="meter"><i></i></div><span class="prepare-detail"></span></div><div><small>Tempo atual</small><strong class="clock"></strong><span class="average"></span></div></div><section class="time-history" aria-label="Tempos dos últimos táticos"><small>ÚLTIMOS TÁTICOS</small><div class="recent-times"></div></section><section class="rank"><div class="rank-head"><div><small>RANK TÁTICO</small><strong class="rank-name"></strong></div><span class="rank-medal" aria-hidden="true">♞</span></div><div class="rank-detail"><b class="xp"></b><span class="next"></span></div><div class="meter rank-meter"><i></i></div></section></section>''',
    css="""
    *{box-sizing:border-box}.tactic-data{font-family:system-ui;color:#e8eee2}.tactic-data>header{display:flex;justify-content:space-between;font:600 10px system-ui;letter-spacing:1.5px;color:#a4b19b}.solved{letter-spacing:0;font-weight:400}
    .pie-row{display:flex;gap:26px;align-items:center;justify-content:center;padding:27px 0}.pie{width:138px;aspect-ratio:1;border-radius:50%;padding:12px;background:conic-gradient(#71c3a1 0deg,#394537 0deg);box-shadow:0 6px 24px #0003}.pie>div{height:100%;border-radius:50%;background:#171d17;display:flex;align-items:center;justify-content:center;flex-direction:column}.pie strong{font:600 26px system-ui;letter-spacing:-1px}.pie small{font:11px system-ui;color:#a0b09b;margin-top:4px}.pie-legend>div{display:flex;align-items:center;gap:8px;margin:14px 0;color:#aebca6;font:12px system-ui}.pie-legend i{width:6px;height:6px;border-radius:50%;background:#71c3a1}.pie-legend>div+div i{background:#db8c7e}.pie-legend b{color:#e7eee0;font-size:16px;font-variant-numeric:tabular-nums;margin-left:12px;min-width:24px;text-align:right}
    .data-grid{display:grid;grid-template-columns:1fr 1fr;border-block:1px solid #ffffff0d;padding:21px 0;gap:24px}.data-grid>div+div{border-left:1px solid #ffffff0d;padding-left:24px}.data-grid small{display:block;font:12px system-ui;color:#a1b098}.data-grid strong{display:block;font:550 30px/1.4 system-ui;font-variant-numeric:tabular-nums;letter-spacing:-1px;margin:7px 0}.data-grid span{display:block;font:10px/1.6 system-ui;color:#899b81;margin-top:7px}.meter{height:4px;border-radius:20px;background:#333f30;overflow:hidden}.meter i{display:block;height:100%;background:#79aa70;border-radius:20px;transition:width .3s}
    .time-history{padding-top:16px}.time-history>small{font:600 9px system-ui;letter-spacing:1.5px;color:#91a187}.recent-times{display:flex;gap:7px;margin-top:10px;min-height:35px;align-items:center}.recent-time{flex:1;text-align:center;border:1px solid #6a805044;border-radius:8px;padding:8px 2px;background:#263322;color:#c7dbb9;font:550 12px system-ui;font-variant-numeric:tabular-nums}.recent-time:first-child{border-color:#a5be7077;color:#e3efcf;background:#35462b}.recent-time:nth-child(2){opacity:.8}.recent-time:nth-child(3){opacity:.65}.recent-time:nth-child(4){opacity:.48}.recent-time:nth-child(5){opacity:.3}.recent-empty{font:11px system-ui;color:#84947a}.recent-time.new{animation:time-arrive .25s ease-out}@keyframes time-arrive{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
    .rank{margin-top:23px;border:1px solid #80704844;border-radius:14px;background:linear-gradient(135deg,#38301f80,#191f1760);padding:18px}.rank-head{display:flex;align-items:center;justify-content:space-between}.rank small{font:600 9px system-ui;letter-spacing:2px;color:#b8a47e}.rank-name{display:block;font:550 23px/1.7 system-ui;color:#ecdbb7}.rank-medal{font:38px Georgia;color:#d8b576}.rank-detail{display:flex;justify-content:space-between;align-items:center;margin:12px 0 10px;font:10px system-ui;color:#9c9e86}.rank-detail b{font-size:12px;color:#d7c49d}.rank-meter i{background:#c1a26b}
    @media(max-width:500px){.pie{width:120px}.pie-row{gap:20px}.data-grid{gap:16px}.data-grid>div+div{padding-left:16px}}
    @media(prefers-reduced-motion:reduce){.meter i{transition:none}.recent-time.new{animation:none}}
    
/* Coach HUD */
.tactic-data{color:#a9d8e8!important}.rank{background:linear-gradient(135deg,#063149,#031327)!important;border-color:#176f88!important;border-radius:4px!important}.rank-name,.rank-medal,.data-grid strong{color:#b5faff!important}.rank small{color:#ff9b4e!important}.rank-meter i,.meter i{background:linear-gradient(90deg,#0c88ac,#20e5e8)!important}.pie{border:1px solid #16859d!important}""",
    js='''export default function({data,parentElement}){
      const text=(selector,value)=>parentElement.querySelector(selector).textContent=value;
      const format=value=>{const seconds=Math.max(0,Math.floor(value));return String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');};
      const percent=data.attempts?Math.round(100*data.hits/data.attempts):null;
      text('.accuracy',percent===null?'—':percent+'%');text('.hits',data.hits);text('.errors',data.errors);text('.solved',data.solved+' resolvidos');
      const pie=parentElement.querySelector('.pie');pie.style.background=data.attempts?`conic-gradient(#71c3a1 ${data.hits/data.attempts*360}deg,#db8c7e 0deg)`:'#303b2d';pie.setAttribute('aria-label',`${data.hits} acertos e ${data.errors} erros`);
      text('.prepare',data.preparation+'%');text('.prepare-detail',data.known+'/'+data.goal+' exercícios diferentes');parentElement.querySelector('.prepare-cell').title='Preparo = progresso na meta de exercícios diferentes concluídos neste tema.';parentElement.querySelector('.prepare-cell .meter i').style.width=data.preparation+'%';
      text('.average',data.average===null?'Média: —':'Média: '+format(data.average));text('.rank-name',data.rank);text('.xp',data.xp+' XP');text('.next',data.next_xp===null?'Nível máximo':data.next_xp+' XP · próximo nível');parentElement.querySelector('.rank-meter i').style.width=data.rank_progress*100+'%';
      const history=parentElement.querySelector('.recent-times');
      const recent=data.recent||[];const historyKey=JSON.stringify(recent);
      if(parentElement._historyKey!==historyKey){
        const previous=parentElement._newestTime;
        history.replaceChildren();
        if(!recent.length){const empty=document.createElement('span');empty.className='recent-empty';empty.textContent='Resolva um tático para registrar seu tempo.';history.append(empty);}
        recent.forEach((item,index)=>{const cell=document.createElement('span');cell.className='recent-time'+(index===0&&item.id!==previous?' new':'');cell.textContent=format(item.seconds);cell.title=index===0?'Último tático resolvido':`${index+1}º mais recente`;history.append(cell);});
        parentElement._historyKey=historyKey;parentElement._newestTime=recent[0]?.id;
      }
      // Explicitly replace the timer on component updates, even before cleanup.
      clearInterval(parentElement._tacticTimer);
      const start=performance.now();const elapsed=Math.max(0,Number(data.elapsed)||0);
      const tick=()=>text('.clock',format(elapsed+(data.running?(performance.now()-start)/1000:0)));
      tick();const timer=data.running?setInterval(tick,100):null;parentElement._tacticTimer=timer;
      return()=>clearInterval(timer);
    }''')


def render_stats(summary,elapsed=0,running=False,clock_key=None):
    DASHBOARD(data=dict(summary,elapsed=elapsed,running=running,clock_key=clock_key),key='tactics_stats')
