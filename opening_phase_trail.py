"""A numbered course map, with ten boss milestones and saved precision."""
import streamlit as st

TRAIL=st.components.v2.component('opening_phase_map',
    html='<div class="course-trail" role="group" aria-label="Trilha de 50 fases"></div>',
    css='''
    *{box-sizing:border-box}.course-trail{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:36px 16px;padding:30px 16px 40px;max-width:1100px;margin:auto;font-family:system-ui}
    .step{display:flex;justify-content:center;position:relative;min-width:0;padding:8px 0}
    .step:before{content:'';position:absolute;left:-50%;right:50%;top:50%;height:2px;background:#30332e;z-index:0}.step:nth-child(5n+1):before{display:none}
    .node{position:relative;z-index:1;width:76px;height:76px;border-radius:50%;border:1px solid #44483e;color:#858d80;background:linear-gradient(145deg,#282c25,#171b17);box-shadow:inset 0 2px #ffffff09,0 7px 0 #10130f;font:650 23px/1 system-ui;cursor:pointer;font-variant-numeric:tabular-nums;transition:transform .16s,box-shadow .16s}
    .node.current{color:#fff6df;background:linear-gradient(145deg,#b78639,#886022);border-color:#e1b76a;outline:3px solid #b78c4e44;outline-offset:6px;box-shadow:inset 0 2px #fff2,0 7px 0 #543a18,0 0 28px #ca9b3420}
    .node.learned{background:linear-gradient(145deg,#287c60,#185441);border-color:#4f9a7b;color:#eefaf3;box-shadow:inset 0 2px #ffffff15,0 7px 0 #103d2f}
    .node.boss{border:3px double #a88453;outline:2px solid #a8845333;outline-offset:5px;border-radius:26px;background:linear-gradient(145deg,#3b2b46,#211b29);color:#ad98ba}
    .node.boss.current{background:linear-gradient(145deg,#81436b,#4e294e);border-color:#f3bc81;color:#fff;outline-color:#da9b5766;box-shadow:inset 0 2px #fff2,0 7px 0 #382036,0 0 30px #d18c3025}
    .node.boss.learned{background:linear-gradient(145deg,#9c7739,#65502c);border-color:#e5c686;color:#fff6dc;box-shadow:inset 0 2px #fff2,0 7px 0 #46361e}
    .done{position:absolute;right:-3px;bottom:-3px;display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#dfece1;color:#1e6148;border:3px solid #0a0a0a;font:800 13px system-ui}
    .phase-detail{position:absolute;top:calc(100% + 9px);left:50%;transform:translateX(-50%);width:210px;max-width:80vw;padding:12px;border:1px solid #69715a;border-radius:10px;background:#22291f;color:#e4eddc;box-shadow:0 8px 24px #0006;z-index:5;font:12px/1.5 system-ui;text-align:center}.step:nth-child(5n+1) .phase-detail{left:0;transform:none}.step:nth-child(5n) .phase-detail{left:auto;right:0;transform:none}
    .node:disabled{cursor:default}.node:not(:disabled):hover{transform:translateY(-3px)}.node:focus-visible{outline:3px solid #f3d293;outline-offset:6px}
    @media(max-width:600px){.course-trail{gap:25px 6px;padding:20px 6px}.node{width:49px;height:49px;font-size:17px}.node.boss{border-radius:18px}.done{width:20px;height:20px;font-size:10px}}
    @media(prefers-reduced-motion:reduce){.node{transition:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}){
      const root=parentElement.querySelector('.course-trail');root.replaceChildren();
      for(const phase of data.phases){
        const step=document.createElement('div');step.className='step';
        const button=document.createElement('button');button.type='button';button.className='node'+(phase.boss?' boss':'')+(phase.completed?' learned':phase.current?' current':'');
        button.textContent=phase.number;button.dataset.phase=phase.number;button.disabled=!phase.unlocked&&!phase.completed;
        const precision=phase.accuracy===null?'Precisão não registrada':`Precisão: ${phase.accuracy.toFixed(1).replace('.',',')}%`;
        const description=`Fase ${phase.number}${phase.boss?' · Boss · 50 desafios':''}${phase.completed?' · Concluída · '+precision:phase.current?' · Disponível':' · Bloqueada'}`;
        button.setAttribute('aria-label',description);button.title=description;
        if(phase.current)button.setAttribute('aria-current','step');
        if(phase.completed){const check=document.createElement('span');check.className='done';check.textContent='✓';check.setAttribute('aria-hidden','true');button.append(check);}
        button.onclick=()=>{
          const opened=step.querySelector('.phase-detail');root.querySelectorAll('.phase-detail').forEach(item=>item.remove());
          if(phase.completed){if(!opened){const detail=document.createElement('div');detail.className='phase-detail';detail.setAttribute('role','status');detail.textContent=description;step.append(detail);}return;}
          setTriggerValue('select',{id:data.currentLine,phase:phase.number,mode:'learn',token:data.token});
        };
        step.append(button);root.append(step);
      }
    }''')
