"""Top activity palette and a pre-drawn, editable classroom trail."""
import streamlit as st
import classroom_trails as trails

BOARD=st.components.v2.component('classroom_trail_canvas',
 html='<section class="trail-builder"><div class="palette"></div><div class="map-panel"><header><h3>Sua trilha</h3><input aria-label="Nome da trilha" maxlength="150"/></header><p class="hint">Arraste uma opção para adicionar uma linha. Clique em uma linha para abrir e editar.</p><div class="track"></div><p class="status" role="status"></p></div></section>',
 css="""
 *{box-sizing:border-box}button,input{font:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible{outline:2px solid #e2c486;outline-offset:4px}.trail-builder{font:14px/1.5 system-ui;color:#e7ebdd}.palette{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin-bottom:22px}.tool{padding:16px 9px;border:1px solid #87956855;border-radius:14px;background:linear-gradient(145deg,#2c372a,#1b241b);box-shadow:inset 0 1px #fff1,0 5px 13px #0004;text-align:center;cursor:grab;touch-action:none}.tool .symbol{display:block;color:#e1c387;font-size:28px;line-height:1.3}.tool strong{display:block;font-size:13px;margin:8px 0}.tool button{color:#c4d1b8;background:transparent;border:0;padding:4px;font-size:11px;cursor:pointer}.map-panel{padding:23px;border:1px solid #74875a44;border-radius:18px;background:radial-gradient(ellipse at top left,#a78b3810,transparent 65%),linear-gradient(145deg,#1c281e,#101a13);box-shadow:inset 0 1px #ffffff0c,0 10px 25px #0004}header{display:flex;align-items:center;justify-content:space-between;gap:16px}h3{font-size:19px;margin:0}header input{min-width:0;width:250px;border:1px solid #68775066;border-radius:10px;padding:10px 13px;background:#111a10;color:#f1e5c8}.hint,.status{font-size:12px;color:#a5b797;margin:12px 0}.track{padding:18px 0}.row{display:flex;justify-content:space-around;position:relative;gap:10px;padding:14px 0 22px;min-height:140px}.row.reverse{flex-direction:row-reverse}.row:before{content:'';position:absolute;left:10%;right:10%;top:46px;height:2px;background:linear-gradient(90deg,#536443,#a08a4b55,#536443)}.row:not(:last-child):after{content:'';position:absolute;top:46px;height:100%;width:1px;background:#536443;right:10%}.row.reverse:not(:last-child):after{right:auto;left:10%}.node-wrap{position:relative;z-index:1;flex:1;min-width:0;max-width:150px;text-align:center}.node{position:relative;width:64px;height:64px;border-radius:50%;border:1px solid #cdb173;background:linear-gradient(145deg,#c1a05c,#7f612e);box-shadow:inset 0 1px #fff4,0 5px 0 #4a391c,0 8px 17px #0004;color:#fff3d5;font-size:20px;font-weight:700;cursor:grab;touch-action:none}.node.blocked{background:linear-gradient(145deg,#515046,#2b3028);border-color:#8f8769;color:#ddd4b8}.node.ghost{background:#1d2b1e;box-shadow:inset 0 1px #ffffff08;border:1px dashed #6b805550;color:#677f57;cursor:pointer;font-weight:400}.node.next{border-color:#d3bc7b88;color:#d4bf85;background:#2c3b25}.node:hover{filter:brightness(1.13)}.node-label{font-size:12px;margin:12px 2px 3px;color:#d0dac5;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow-wrap:anywhere}.summary{font-size:10px;color:#90a582}.lock{position:absolute;bottom:-4px;right:-4px;font-size:12px;background:#1d281b;padding:2px 4px;border-radius:50%;border:1px solid #766d50}.pending{display:block;font-size:10px;color:#ddbe7e}.dragover .node,.node.dragover,.map-panel.dragover{outline:2px solid #f0d294;outline-offset:5px}.touch-ghost{position:fixed;z-index:99999;padding:12px 18px;background:#3b482d;color:#f0dfb8;border:1px solid #dbbe82;border-radius:10px;box-shadow:0 10px 30px #0006;pointer-events:none}
 @media(max-width:800px){.palette{grid-template-columns:repeat(3,minmax(0,1fr))}.tool{padding:12px 6px}}
 @media(max-width:500px){.map-panel{padding:14px}header{align-items:start;flex-direction:column}header input{width:100%}.node{width:45px;height:45px;font-size:16px}.row{gap:2px;min-height:116px}.row:before,.row:not(:last-child):after{top:37px}.node-label{font-size:10px}.summary{font-size:9px}.lock{font-size:9px}.tool strong{font-size:12px}}
 @media(prefers-reduced-motion:no-preference){.node,.tool{transition:filter .15s,transform .15s}.tool:hover{transform:translateY(-2px)}}
 """,
 js="""export default function({data,parentElement,setTriggerValue}){
 const root=parentElement.querySelector('.trail-builder'),doc=parentElement.ownerDocument,palette=root.querySelector('.palette'),track=root.querySelector('.track'),map=root.querySelector('.map-panel');let pending=false,drag=null;const zones=[];
 const make=(tag,cls,text)=>{const e=doc.createElement(tag);e.className=cls||'';if(text!==undefined)e.textContent=text;return e;};
 const emit=event=>{if(pending)return;pending=true;root.querySelector('.status').textContent='Salvando…';setTriggerValue('action',{...event,revision:data.draft.revision,nonce:crypto.randomUUID()});};
 const button=(label,action,cls='')=>{const b=make('button',cls,label);b.type='button';b.onclick=action;return b;};
 palette.replaceChildren();track.replaceChildren();const name=root.querySelector('header input');name.value=data.draft.title;name.onchange=()=>emit({action:'title',title:name.value});name.onkeydown=e=>{if(e.key==='Enter')name.blur();};root.querySelector('.status').textContent='Montagem salva automaticamente. Conteúdos pendentes são revisados dentro da linha.';
 const drop=(value,target)=>{if(value.type==='tool')emit({action:'add_event',kind:value.kind,step:target||null});else if(value.type==='step'&&value.id!==target){const order=data.draft.steps.map(s=>s.id).filter(id=>id!==value.id);const index=target?order.indexOf(target):order.length;if(index<0)return;order.splice(index,0,value.id);emit({action:'order',order});}};
 const bindDrop=(zone,target)=>{zone.dataset.drop=target||'';zones.push(zone);zone.ondragover=e=>{e.preventDefault();e.stopPropagation();zone.classList.add('dragover');};zone.ondragleave=()=>zone.classList.remove('dragover');zone.ondrop=e=>{e.preventDefault();e.stopPropagation();zone.classList.remove('dragover');try{drop(drag||JSON.parse(e.dataTransfer.getData('text/plain')),target);}catch{}};};
 const bindDrag=(element,value)=>{element.draggable=true;element.ondragstart=e=>{drag=value;e.dataTransfer.setData('text/plain',JSON.stringify(value));e.dataTransfer.effectAllowed=value.type==='tool'?'copy':'move';};element.ondragend=()=>{drag=null;zones.forEach(z=>z.classList.remove('dragover'));};element.onpointerdown=e=>{if(e.pointerType==='mouse'||e.target.closest('input'))return;let moved=false,ghost=null;const x=e.clientX,y=e.clientY;
 const move=event=>{if(!moved&&Math.hypot(event.clientX-x,event.clientY-y)<8)return;moved=true;event.preventDefault();if(!ghost){ghost=make('div','touch-ghost',value.type==='tool'?data.labels[value.kind]:'Mover linha');root.append(ghost);}ghost.style.left=(event.clientX-60)+'px';ghost.style.top=(event.clientY-25)+'px';zones.forEach(z=>{const r=z.getBoundingClientRect();z.classList.toggle('dragover',event.clientX>=r.left&&event.clientX<=r.right&&event.clientY>=r.top&&event.clientY<=r.bottom);});};
 const finish=event=>{doc.removeEventListener('pointermove',move);doc.removeEventListener('pointerup',finish);doc.removeEventListener('pointercancel',cancel);if(ghost)ghost.remove();const zone=[...zones].reverse().find(z=>z.classList.contains('dragover'));zones.forEach(z=>z.classList.remove('dragover'));if(moved&&zone)drop(value,zone.dataset.drop);};const cancel=()=>{doc.removeEventListener('pointermove',move);doc.removeEventListener('pointerup',finish);doc.removeEventListener('pointercancel',cancel);if(ghost)ghost.remove();zones.forEach(z=>z.classList.remove('dragover'));};doc.addEventListener('pointermove',move,{passive:false});doc.addEventListener('pointerup',finish);doc.addEventListener('pointercancel',cancel);};};
 const symbols={line:'♞',tactic:'♟',video:'▷',exam:'?',game:'♜',note:'✎'};
 for(const kind of ['line','tactic','video','exam','game','note']){const tool=make('div','tool');tool.dataset.kind=kind;tool.append(make('span','symbol',symbols[kind]),make('strong','',data.labels[kind]));tool.append(button('＋ Adicionar',()=>emit({action:'add_event',kind,open:true})));bindDrag(tool,{type:'tool',kind});palette.append(tool);}
 bindDrop(map,'');const size=Math.min(50,Math.max(10,Math.ceil((data.draft.steps.length+1)/5)*5));let blocked=false;
 for(let base=0;base<size;base+=5){const row=make('div','row'+((base/5)%2?' reverse':''));track.append(row);for(let i=base;i<base+5;i++){const step=data.draft.steps[i],wrap=make('div','node-wrap');if(step){blocked=blocked||step.locked;const node=button(String(i+1),()=>emit({action:'open',step:step.id}),'node'+(blocked?' blocked':''));node.dataset.step=step.id;node.setAttribute('aria-label','Abrir linha '+(i+1)+' · '+step.title);bindDrag(node,{type:'step',id:step.id});bindDrop(wrap,step.id);if(step.locked)node.append(make('span','lock','🔒'));wrap.append(node,make('div','node-label',step.title),make('small','summary',step.items.length+' atividades'));if(step.items.some(item=>!item.reviewed))wrap.append(make('span','pending','Configurar'));}
 else{const next=i===data.draft.steps.length;const node=button(next?'＋':'·',()=>emit({action:'create_step',open:true}),'node ghost'+(next?' next':''));node.setAttribute('aria-label','Adicionar linha '+(data.draft.steps.length+1));if(!next)node.tabIndex=-1;wrap.append(node);bindDrop(wrap,'');if(next)wrap.append(make('div','node-label','Arraste aqui'));}row.append(wrap);}}
} """)


def render_builder(token,student,candidates=None,reviewed=False,labels=None):
    draft=trails.load_draft(token,student)
    from classroom_session_ui import controls,student_progress
    controls(token,student,draft)
    student_progress(token,student)
    labels=labels or dict(line='Linha de treino',tactic='Tático',video='Vídeo',exam='Desafio',game='Partida estudada',note='Anotação')
    key='prep_trail_composer_'+student
    selected_key=key+'_selected'
    render_key=key+'_render';st.session_state[render_key]=st.session_state.get(render_key,0)+1
    from classroom_schedule import is_locked
    visible=dict(title=draft['title'],revision=draft['revision'],steps=[dict(id=step['id'],title=step['title'],locked=is_locked(step['locked'],step.get('release_at')),items=[{field:item[field] for field in ('id','title','kind','reviewed')} for item in step['items']]) for step in draft['steps']])
    result=BOARD(data=dict(draft=visible,render=st.session_state[render_key],labels=labels),key=key,on_action_change=lambda:None)
    event=getattr(result,'action',None)
    if isinstance(event,dict) and event.get('nonce') and st.session_state.get(key+'_handled')!=event['nonce']:
        st.session_state[key+'_handled']=event['nonce']
        try:
            if event.get('action')=='open':
                if not any(step['id']==event.get('step') for step in draft['steps']):raise ValueError('Linha não encontrada.')
                st.session_state[selected_key]=event['step']
                st.session_state['prep_line_editor_'+student+'_'+event['step']+'_view']='home'
            else:
                updated=trails.edit_draft(token,student,event.get('revision'),event)
                if event.get('open'):
                    target=event.get('step') or updated['steps'][-1]['id'];st.session_state[selected_key]=target
                    st.session_state.pop('prep_line_editor_'+student+'_'+target+'_view',None)
            st.session_state.pop(key+'_error',None)
        except (ValueError,PermissionError) as error:st.session_state[key+'_error']=str(error)
        st.rerun()
    if error:=st.session_state.get(key+'_error'):st.error(error)
    if selected:=st.session_state.get(selected_key):
        from classroom_trail_editor import show_step_editor
        show_step_editor(token,student,selected,selected_key,labels)
    st.caption('Disponibilize a trilha para aplicar alterações. Cadeados de linhas já publicadas mudam imediatamente.')
    if st.button('Disponibilizar trilha ao aluno',type='primary',key='prep_trail_publish_'+student,disabled=not draft['steps']):
        try:
            count=trails.publish(token,student,draft['revision']);st.success(f'Trilha disponível · {count} atividades. O progresso anterior foi preservado.')
        except (ValueError,PermissionError) as error:st.error(error)
