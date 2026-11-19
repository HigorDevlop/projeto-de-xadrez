"""A fictional Fischer teaching avatar reads only the professor's own commentary."""
import base64
from pathlib import Path
import streamlit as st

COACH=st.components.v2.component('classroom_fischer_instructor',
 html='''<section class="fischer-coach" aria-label="Bobby Fischer, personagem virtual">
 <div class="portrait"><img alt="Representação artística realista de Bobby Fischer explicando uma ideia"/><div class="equalizer" aria-hidden="true"><i></i><i></i><i></i><i></i></div></div>
 <div class="explanation"><header><span>SEU ESTUDO, LANCE A LANCE</span><h4>Bobby Fischer <small>personagem virtual</small></h4></header>
 <div class="commentary"></div><div class="voice-controls"><button class="listen" type="button">▶ Ouvir explicação</button><button class="stop" type="button" disabled>■ Parar</button></div>
 <label class="automatic"><input type="checkbox"/> Ler automaticamente</label><p class="voice-status" role="status" aria-live="polite"></p></div></section>''',
 css='''*{box-sizing:border-box}.fischer-coach{display:grid;grid-template-columns:132px minmax(0,1fr);gap:18px;border:1px solid #a48a4b4d;border-radius:16px;overflow:hidden;background:radial-gradient(ellipse at top left,#80633322,transparent 65%),linear-gradient(145deg,#20241e,#121711);color:#f1f1e9;font:13px/1.6 system-ui;box-shadow:inset 0 1px #fff1,0 7px 22px #0003;margin-top:12px}.portrait{position:relative;overflow:hidden;background:#11120f;min-height:232px}.portrait img{width:100%;height:100%;position:absolute;inset:0;object-fit:cover;object-position:50% 24%;transform-origin:50% 75%}.portrait:after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent 75%,#191e1688),linear-gradient(0deg,#10150e99,transparent 40%);pointer-events:none}.explanation{padding:18px 16px 16px 0;min-width:0}header>span{font-size:8px;color:#c6aa71;letter-spacing:1.6px}h4{margin:3px 0 12px;font-size:18px;font-weight:650}h4 small{display:block;font-size:10px;font-weight:400;color:#a8b39e}.commentary p{margin:3px 0 12px;overflow-wrap:anywhere;font-size:13px;color:#e4eadc}.commentary .move-label{font-size:10px;color:#c6aa71}.voice-controls{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px}button{font:600 11px/1.4 system-ui;color:#f0dfbc;border:1px solid #bc9e5e66;background:linear-gradient(#414331,#2a3023);box-shadow:inset 0 1px #fff1,0 3px 7px #0003;border-radius:9px;padding:9px 11px;cursor:pointer}button:hover:not(:disabled){filter:brightness(1.2)}button:focus-visible,input:focus-visible{outline:2px solid #efd294;outline-offset:3px}button:disabled{opacity:.45;cursor:default}.automatic{display:flex;align-items:center;gap:7px;color:#aebaa2;font-size:10px;margin-top:12px}.automatic input{accent-color:#c4a262;margin:0}.voice-status{font-size:10px;line-height:1.5;color:#a1af96;margin:6px 0 0;min-height:15px}.equalizer{display:none;position:absolute;bottom:17px;left:20px;z-index:2;gap:4px;height:18px;align-items:center}.equalizer i{width:3px;height:8px;background:#ddbd7d;border-radius:2px}.speaking .equalizer{display:flex}.speaking .voice-status{color:#e2c78c}
 @media(prefers-reduced-motion:no-preference){.speaking .portrait img{animation:coach-breathe 5s ease-in-out infinite}.speaking .equalizer i{animation:coach-wave .7s ease-in-out infinite alternate}.equalizer i:nth-child(2){animation-delay:.2s}.equalizer i:nth-child(3){animation-delay:.45s}.equalizer i:nth-child(4){animation-delay:.1s}@keyframes coach-breathe{50%{transform:scale(1.022) rotate(.25deg)}}@keyframes coach-wave{to{height:18px}}}
 @media(max-width:430px){.fischer-coach{grid-template-columns:100px minmax(0,1fr);gap:12px}.explanation{padding-right:10px}h4{font-size:16px}.portrait{min-height:224px}}
 ''',
 js='''export default function({data,parentElement}){
 const root=parentElement.querySelector('.fischer-coach'),host=parentElement.host??parentElement;
 const image=root.querySelector('img'),body=root.querySelector('.commentary'),listen=root.querySelector('.listen'),stop=root.querySelector('.stop'),automatic=root.querySelector('input'),status=root.querySelector('.voice-status');
 if(image.getAttribute('src')!==data.image)image.src=data.image;
 const synth=window.speechSynthesis,available=Boolean(synth&&window.SpeechSynthesisUtterance);
 const state=parentElement._fischerCoach??={identity:'',speaking:false,run:0,voice:null,notes:[],auto:false};
 if(!state.loaded){try{state.auto=localStorage.getItem('coach-commentary-auto')==='true';}catch{}state.loaded=true;}
 const identity=JSON.stringify(data.notes||[]),changed=state.identity!==identity;state.notes=data.notes||[];
 const paint=()=>{root.classList.toggle('speaking',state.speaking);listen.disabled=!state.voice||!state.notes.length;stop.disabled=!state.speaking;automatic.disabled=!state.voice;automatic.checked=state.auto;status.textContent=state.speaking?'Lendo o comentário do professor…':state.voice?'Voz do dispositivo · português':available?'Sem voz local em português disponível neste dispositivo.':'Leitura em voz alta indisponível neste dispositivo.';};
 const stopReading=()=>{state.run++;if(window.__coachCommentSpeaker===state){synth?.cancel();window.__coachCommentSpeaker=null;}state.speaking=false;paint();};state.stop=stopReading;
 const start=()=>{
  if(!state.voice||!state.notes.length)return;state.wantsAuto=false;
  window.__coachCommentSpeaker?.stop();stopReading();window.__coachCommentSpeaker=state;
  const run=++state.run;state.speaking=true;paint();
  const text=state.notes.map(n=>n.text).join(' ');
  // Short utterances avoid the Chromium long-text cutoff; the wording stays unchanged.
  const chunks=text.match(/[^.!?]{1,220}(?:[.!?]+|$)|[^.!?]{1,220}/g)||[text];let at=0;
  const next=()=>{if(run!==state.run)return;if(at>=chunks.length){state.speaking=false;window.__coachCommentSpeaker=null;paint();return;}
   const utterance=new SpeechSynthesisUtterance(chunks[at++]);state.utterance=utterance;utterance.voice=state.voice;utterance.lang=state.voice.lang;utterance.rate=.94;utterance.pitch=1;
   utterance.onend=next;utterance.onerror=()=>{if(run===state.run){state.speaking=false;paint();status.textContent='Não foi possível ler. O comentário continua disponível acima.';}};synth.speak(utterance);};next();
 };
 if(changed){stopReading();state.identity=identity;state.wantsAuto=state.auto;body.replaceChildren();
  if(state.notes.length){for(const note of state.notes){const label=document.createElement('div');label.className='move-label';label.textContent=note.label;const text=document.createElement('p');text.textContent=note.text;body.append(label,text);}}
  else{const hint=document.createElement('p');hint.textContent='Escreva uma instrução para preparar a explicação deste lance.';body.append(hint);}}
 const voices=()=>{const local=available?synth.getVoices().filter(v=>v.localService&&/^pt(?:-|_)/i.test(v.lang)):[];state.voice=local.find(v=>/^pt[-_]BR$/i.test(v.lang))||local[0]||null;paint();if(state.wantsAuto&&state.voice&&state.notes.length)start();};
 voices();listen.onclick=start;stop.onclick=stopReading;
 automatic.onchange=()=>{state.auto=automatic.checked;state.wantsAuto=false;try{localStorage.setItem('coach-commentary-auto',String(state.auto));}catch{}if(state.auto)start();else stopReading();};
 if(available)synth.addEventListener('voiceschanged',voices);

 return ()=>{if(available)synth.removeEventListener('voiceschanged',voices);setTimeout(()=>{if(!host.isConnected)stopReading();},0);};
 }''')

@st.cache_data(max_entries=1,show_spinner=False)
def portrait_source(path,modified):
    return 'data:image/webp;base64,'+base64.b64encode(Path(path).read_bytes()).decode()


def render_instructor(notes,key):
    path=Path(__file__).parent/'assets/bobby-fischer-instructor.webp'
    if not path.is_file():
        for note in notes:st.info(note['text'])
        return
    COACH(data=dict(notes=[dict(label=str(note['label']),text=str(note['text'])) for note in notes if str(note['text']).strip()],
                    image=portrait_source(str(path),path.stat().st_mtime_ns)),key=key)
