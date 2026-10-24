export default function({data,parentElement,setStateValue}){
 const root=parentElement;
 if(root._live){root._live.data=data;root._live.emit=setStateValue;return;}
 const c={data,emit:setStateValue,peers:new Map(),queue:[],after:0,seen:new Set(),stream:null,busy:false};root._live=c;
 const status=root.querySelector('.live-status'),video=root.querySelector('video');
 const send=(target,kind,payload)=>c.queue.push({target,kind,payload,nonce:crypto.randomUUID()});
 const make=(id)=>{
  if(c.peers.has(id))return c.peers.get(id);
  const pc=new RTCPeerConnection({iceServers:c.data.iceServers});pc.pending=[];c.peers.set(id,pc);
  pc.onicecandidate=e=>{if(e.candidate)send(id,'ice',e.candidate.toJSON());};
  pc.onconnectionstatechange=()=>{status.textContent=pc.connectionState==='connected'?'Ao vivo':pc.connectionState==='failed'?'Conexão indisponível. Saia e entre novamente.':'Conectando…';};
  pc.ontrack=e=>{video.srcObject=e.streams[0];video.play().catch(()=>{});};
  if(c.stream)c.stream.getTracks().forEach(track=>pc.addTrack(track,c.stream));
  return pc;
 };
 const stop=()=>{c.stream?.getTracks().forEach(t=>t.stop());c.stream=null;c.peers.forEach(pc=>pc.close());c.peers.clear();};
 root.querySelector('.broadcast').hidden=!data.teacher;
 root.querySelector('.broadcast').onclick=async()=>{
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw new Error('Para usar câmera e microfone, abra a aula em HTTPS ou neste computador em localhost.');
   c.stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:960},height:{ideal:540}},audio:true});
   video.srcObject=c.stream;video.muted=true;await video.play();status.textContent='Câmera pronta · aguardando alunos';
   root.querySelector('.broadcast').disabled=true;root.querySelector('.mic').hidden=false;root.querySelector('.camera').hidden=false;
  }catch(e){status.textContent=e.message||'Não foi possível abrir a câmera.';}
 };
 root.querySelector('.mic').onclick=e=>{const track=c.stream?.getAudioTracks()[0];if(track){track.enabled=!track.enabled;e.target.textContent=track.enabled?'Microfone ligado':'Microfone desligado';}};
 root.querySelector('.camera').onclick=e=>{const track=c.stream?.getVideoTracks()[0];if(track){track.enabled=!track.enabled;e.target.textContent=track.enabled?'Câmera ligada':'Câmera desligada';}};
 root.querySelector('.sound').hidden=data.teacher;
 root.querySelector('.sound').onclick=()=>{video.muted=false;video.play().catch(()=>{});};
 video.muted=!data.teacher;video.autoplay=true;
 const cycle=async()=>{
  if(!(root.host??root).isConnected){clearInterval(timer);stop();return;}
  if(c.busy)return;c.busy=true;
  try{
   c.queue=c.queue.filter(event=>!(c.data.acked||[]).includes(event.nonce));
   for(const signal of c.data.signals||[]){
    if(c.seen.has(signal.id))continue;
    const pc=make(signal.sender);
    if(signal.kind==='offer'){
     await pc.setRemoteDescription(signal.payload);
     for(const candidate of pc.pending)await pc.addIceCandidate(candidate);pc.pending=[];
     await pc.setLocalDescription(await pc.createAnswer());send(signal.sender,'answer',pc.localDescription.toJSON());
    }else if(signal.kind==='answer'){
     await pc.setRemoteDescription(signal.payload);
     for(const candidate of pc.pending)await pc.addIceCandidate(candidate);pc.pending=[];
    }else if(pc.remoteDescription)await pc.addIceCandidate(signal.payload);else pc.pending.push(signal.payload);
    c.seen.add(signal.id);c.after=Math.max(c.after,signal.id);
   }
   if(c.data.teacher&&c.stream){
    for(const peer of c.data.peers||[]){if(peer.teacher||c.peers.has(peer.id))continue;
     const pc=make(peer.id);await pc.setLocalDescription(await pc.createOffer());send(peer.id,'offer',pc.localDescription.toJSON());
    }
   }
   const active=new Set((c.data.peers||[]).map(p=>p.id));c.peers.forEach((pc,id)=>{if(!active.has(id)){pc.close();c.peers.delete(id);}});
   c.emit('exchange',{outbox:c.queue.slice(0,100),after:c.after,nonce:Date.now()});
  }catch(e){status.textContent='Falha na conexão: '+e.message;}finally{c.busy=false;}
 };
 const timer=setInterval(cycle,1500);cycle();
}