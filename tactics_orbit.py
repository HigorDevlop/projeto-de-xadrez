"""A draggable, keyboard accessible orbit of offline tactics themes."""
import streamlit as st
from tactics import THEMES
from tactic_art import theme_symbol

ORBIT=st.components.v2.component('tactics_theme_orbit',
    html='''<section class="orbit"><div class="orbit-heading"><small>LABORATÓRIO TÁTICO</small><h1>Encontre seu próximo desafio.</h1><p>Segure e gire para escolher.</p></div><div class="orbit-stage" aria-label="Temas táticos"></div><div class="orbit-selection"><span class="orbit-index"></span><h2></h2><button class="orbit-start" type="button" aria-label="Começar">Começar <span aria-hidden="true">↗</span></button></div><div class="orbit-controls"><button type="button" class="orbit-prev" aria-label="Tema anterior">←</button><div class="orbit-dots"></div><button type="button" class="orbit-next" aria-label="Próximo tema">→</button></div></section>''',
    css='''
    *{box-sizing:border-box}.orbit{font-family:system-ui;color:#eee9df;max-width:1250px;margin:auto;overflow:hidden;min-height:620px;--accent:#dbb474}.orbit-heading{text-align:center;padding:35px 16px 0}.orbit-heading small{color:#c5a272;font:650 10px system-ui;letter-spacing:3px}.orbit-heading h1{font:550 clamp(26px,4vw,44px)/1.2 system-ui;letter-spacing:-1.4px;margin:15px 0 10px}.orbit-heading p{color:#8e938b;font-size:13px;margin:0}
    .orbit-stage{height:320px;position:relative;touch-action:pan-y;cursor:grab;user-select:none;isolation:isolate}.orbit-stage:before{content:'';position:absolute;inset:15% 0 0;background:radial-gradient(ellipse at center,#b5924422,transparent 60%);pointer-events:none}.orbit-stage.dragging{cursor:grabbing;touch-action:none}
    .orb{position:absolute;left:50%;top:52%;border:1px solid #ffffff24;border-radius:50%;width:148px;height:148px;display:grid;place-items:center;padding:0;color:#f5e7ce;background:radial-gradient(circle at 30% 23%,#bdaa84 0,#66573e 26%,#28281f 63%,#0c100e 95%);box-shadow:inset -14px -18px 32px #0009,inset 2px 3px 7px #ffffff40,0 26px 35px -18px #000c;font:600 64px/1 Georgia,serif;cursor:inherit;will-change:transform,opacity;outline-offset:6px}.orb-diagram{display:block;width:72%;aspect-ratio:1;overflow:visible;border:0;filter:drop-shadow(0 3px 3px #0007);pointer-events:none;line-height:0;background:transparent}.orb-diagram>svg{display:block;width:100%;height:100%;pointer-events:none}.orb:after{content:'';position:absolute;inset:8px;border:1px solid #e4c99725;border-radius:50%}.orb.selected{border-color:#e8c68b;box-shadow:inset -14px -18px 32px #0009,inset 2px 3px 7px #ffffff40,0 0 48px #e3ba6130,0 26px 35px -18px #000c}.orb:focus-visible{outline:3px solid #dbb474}
    .orbit-selection{text-align:center;position:relative;margin-top:-5px}.orbit-index{color:#a89679;font:11px system-ui;letter-spacing:3px}.orbit-selection h2{font:550 25px/1.3 system-ui;margin:10px 0 20px}.orbit-start{position:relative;isolation:isolate;overflow:hidden;display:inline-flex;align-items:center;justify-content:space-between;gap:38px;min-width:190px;padding:9px 10px 9px 25px;border:1px solid #e4c89488;border-radius:16px;background:linear-gradient(125deg,#edd5a7,#c8a261);color:#25291f;font:650 14px system-ui;letter-spacing:.1px;box-shadow:inset 0 1px #fff6,0 5px 0 #695432,0 12px 25px #c8a26118;cursor:pointer;transition:transform .18s,box-shadow .18s,filter .18s}.orbit-start span{display:grid;place-items:center;width:34px;height:34px;margin:0;border-radius:10px;border:1px solid #352c2520;background:#352c2510;font-size:19px;transition:transform .2s,background .2s}.orbit-start:before{content:'';position:absolute;inset:0;background:linear-gradient(110deg,transparent 25%,#fff5 48%,transparent 70%);transform:translateX(-120%);pointer-events:none}.orbit-start:hover{transform:translateY(-2px);filter:brightness(1.06);box-shadow:inset 0 1px #fff7,0 7px 0 #695432,0 16px 30px #c8a26124}.orbit-start:hover:before{animation:orbit-button-shine .65s ease-out}.orbit-start:hover span{transform:translate(1px,-1px);background:#352c2520}.orbit-start:active{transform:translateY(3px);box-shadow:inset 0 1px #fff4,0 2px 0 #695432}.orbit-start:focus-visible{outline:3px solid #f2d6a2;outline-offset:6px}@keyframes orbit-button-shine{to{transform:translateX(120%)}}.orbit-controls{display:flex;align-items:center;justify-content:center;gap:20px;margin:30px 0}.orbit-controls>button{border:1px solid #3e443a;border-radius:50%;width:36px;height:36px;background:#161b16;color:#b4c0ae;cursor:pointer}.orbit-dots{display:flex;gap:5px}.orbit-dots i{width:4px;height:4px;border-radius:50%;background:#3f463a}.orbit-dots i.active{background:#d9b77f;width:16px;border-radius:5px}
    @media(max-width:600px){.orbit{min-height:540px}.orbit-heading{padding-top:20px}.orbit-stage{height:280px}.orb{width:116px;height:116px;font-size:52px}.orbit-selection h2{font-size:21px}.orbit-controls{gap:12px}.orbit-dots{gap:4px}}
    @media(prefers-reduced-motion:reduce){.orb{will-change:auto}.orbit-start,.orbit-start span{transition:none}.orbit-start:hover:before{animation:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}){
      const stage=parentElement.querySelector('.orbit-stage'),dots=parentElement.querySelector('.orbit-dots');
      const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
      stage.replaceChildren();dots.replaceChildren();
      let index=0,offset=0,pointer=null,startX=0,startOffset=0,moved=false,raf=null,disposed=false,pressed=null;
      const count=data.themes.length;
      const buttons=data.themes.map((theme,i)=>{const button=document.createElement('button');button.type='button';button.className='orb';const art=document.createElement('span');art.className='orb-diagram';art.setAttribute('aria-hidden','true');art.innerHTML=theme.art||'';button.append(art);button.dataset.theme=theme.id;button.setAttribute('aria-label',theme.label);button.title=theme.label;stage.append(button);const dot=document.createElement('i');dots.append(dot);button.onclick=()=>{if(moved){moved=false;return;}offset=i;paint();choose();};return button;});
      function paint(){
        index=((Math.round(offset)%count)+count)%count;
        const spacing=Math.min(205,stage.clientWidth*.32);
        buttons.forEach((button,i)=>{let d=i-offset;d=((d+count/2)%count+count)%count-count/2;const depth=Math.abs(d),scale=Math.max(.48,1-depth*.16);button.style.transform=`translate(calc(-50% + ${d*spacing}px),calc(-50% + ${Math.min(depth,3)*17}px)) scale(${scale}) rotate(${d*9}deg)`;button.style.opacity=depth<3.1?String(Math.max(.12,1-depth*.32)):'0';button.style.visibility=depth<3.1?'visible':'hidden';button.style.zIndex=String(100-Math.round(depth*10));button.classList.toggle('selected',i===index);button.tabIndex=i===index?0:-1;dots.children[i].classList.toggle('active',i===index);});
        parentElement.querySelector('.orbit-index').textContent=String(index+1).padStart(2,'0')+' / '+count;
        parentElement.querySelector('.orbit-selection h2').textContent=data.themes[index].label;
      }
      function snap(target){cancelAnimationFrame(raf);const source=offset,started=performance.now();function tick(now){if(disposed)return;const t=reduced?1:Math.min(1,(now-started)/220);offset=source+(target-source)*(1-Math.pow(1-t,3));paint();if(t<1)raf=requestAnimationFrame(tick);}raf=requestAnimationFrame(tick);}
      function choose(){
        if(window._coachTacticsCurtain)return;
        const curtain=document.createElement('div');curtain.setAttribute('role','status');curtain.setAttribute('aria-label','Carregando treino');
        Object.assign(curtain.style,{position:'fixed',inset:'0',background:'#050705',zIndex:'99999',display:'grid',placeContent:'center',color:'#b8c3ad',font:'12px system-ui',letterSpacing:'3px'});
        curtain.textContent='PREPARANDO SEU TREINO';document.body.append(curtain);window._coachTacticsCurtain=curtain;
        clearTimeout(window._coachTacticsCurtainTimer);window._coachTacticsCurtainTimer=setTimeout(()=>{curtain.remove();if(window._coachTacticsCurtain===curtain)window._coachTacticsCurtain=null;},15000);
        setTriggerValue('select',{theme:data.themes[index].id,token:data.token});
      }
      stage.onpointerdown=e=>{if(e.button!==0)return;cancelAnimationFrame(raf);pressed=e.target.closest('.orb');pointer=e.pointerId;startX=e.clientX;startOffset=offset;moved=false;stage.setPointerCapture(e.pointerId);stage.classList.add('dragging');};
      stage.onpointermove=e=>{if(pointer!==e.pointerId)return;const dx=e.clientX-startX;if(Math.abs(dx)>6)moved=true;if(moved){offset=startOffset-dx/Math.min(205,stage.clientWidth*.32);paint();}};
      function release(e,cancel=false){if(pointer!==e.pointerId)return;pointer=null;stage.classList.remove('dragging');if(stage.hasPointerCapture(e.pointerId))stage.releasePointerCapture(e.pointerId);if(moved||cancel)snap(Math.round(offset));else if(pressed){offset=buttons.indexOf(pressed);paint();choose();}}
      stage.onpointerup=e=>release(e);stage.onpointercancel=e=>release(e,true);
      stage.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();snap(Math.round(offset)+(e.key==='ArrowRight'?1:-1));}if(e.key==='Enter'){e.preventDefault();choose();}};
      parentElement.querySelector('.orbit-prev').onclick=()=>snap(Math.round(offset)-1);parentElement.querySelector('.orbit-next').onclick=()=>snap(Math.round(offset)+1);parentElement.querySelector('.orbit-start').onclick=choose;
      const observer=new ResizeObserver(paint);observer.observe(stage);paint();
      return()=>{disposed=true;cancelAnimationFrame(raf);observer.disconnect();};
    }''')


def render_orbit(choose_theme,token):
    def selected():
        event=st.session_state.tactics_orbit.select
        if isinstance(event,dict) and event.get('token')==token and event.get('theme') in THEMES.values():choose_theme(event['theme'])
    ORBIT(data=dict(themes=[dict(id=value,label=label,art=theme_symbol(value)) for label,value in THEMES.items()],token=token),key='tactics_orbit',on_select_change=selected)
