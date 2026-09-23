export default function ({data,parentElement}) {
  if(parentElement._catScene){parentElement._catScene.resume();return parentElement._catScene.pause;}
  const canvas=parentElement.querySelector('canvas'),ctx=canvas.getContext('2d');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),atlas=new Image();
  const poses=[];
  const visit=window.__chessCatVisit ??= {elapsed:0};
  let ready=false,raf=0,running=false,lastTime=null,lastSearch=-1000,bed=null,board=null;
  canvas.dataset.view='superior';canvas.dataset.appearance='fotorrealista';
  const clamp=x=>Math.max(0,Math.min(1,x));
  const ease=x=>{x=clamp(x);return x*x*(3-2*x);};
  const mix=(a,b,t)=>a+(b-a)*t;
  function find(root,selector){
    const found=root.querySelector(selector);if(found)return found;
    for(const el of root.querySelectorAll('*'))if(el.shadowRoot){const result=find(el.shadowRoot,selector);if(result)return result;}
    return null;
  }
  function prepare(){
    // Crop each original pose once, with alpha preserved and no work per frame.
    for(let i=0;i<16;i++){
      const tile=document.createElement('canvas');tile.width=tile.height=400;
      const t=tile.getContext('2d',{willReadFrequently:true});
      const x=Math.round(i%4*atlas.width/4),y=Math.round(Math.floor(i/4)*atlas.height/4);
      const right=Math.round((i%4+1)*atlas.width/4),bottom=Math.round((Math.floor(i/4)+1)*atlas.height/4);
      t.drawImage(atlas,x,y,right-x,bottom-y,0,0,400,400);
      const pixels=t.getImageData(0,0,400,400).data;
      let l=400,u=400,r=0,b=0;
      for(let py=0;py<400;py++)for(let px=0;px<400;px++)if(pixels[(py*400+px)*4+3]>24){
        l=Math.min(l,px);r=Math.max(r,px);u=Math.min(u,py);b=Math.max(b,py);
      }
      poses.push({tile,x:l,y:u,w:r-l+1,h:b-u+1});
    }
    ready=true;resume();
  }
  function drawPose(index,alpha,angle,breath,tailTime=null){
    if(alpha<=0)return;
    const p=poses[index],scale=390/Math.max(p.w,p.h),w=p.w*scale,h=p.h*scale;
    ctx.save();ctx.globalAlpha=alpha;ctx.translate(240,240);ctx.rotate(angle);ctx.scale(1,breath);
    const x=-w/2,y=-h/2;
    if(tailTime===null){ctx.drawImage(p.tile,p.x,p.y,p.w,p.h,x,y,w,h);}
    else {
      // Only the lower tail region bends; its root remains anchored to the body.
      const cut=Math.floor(p.h*.77),tail=p.h-cut;
      ctx.drawImage(p.tile,p.x,p.y,p.w,cut,x,y,w,cut*scale);
      for(let row=0;row<tail;row++){
        const progress=row/Math.max(1,tail-1);
        const envelope=progress*progress*(3-2*progress);
        const wave=reduced.matches?0:
          (Math.sin(tailTime/920-progress*1.55)*.8+
           Math.sin(tailTime/1500-progress*.7+.6)*.2)*24*envelope;
        ctx.drawImage(p.tile,p.x,p.y+cut+row,p.w,1,x+wave,y+(cut+row)*scale,w,scale+.2);
      }
    }
    ctx.restore();
  }
  function frame(now){
    if(!running)return;raf=requestAnimationFrame(frame);
    const delta=lastTime===null?0:now-lastTime;lastTime=now;
    if(document.hidden || !ready || window.__chessIntroActive){canvas.style.display='none';return;}
    if(!bed?.isConnected || now-lastSearch>800){
      bed=find(document,'.workspace.mascot .cat-place');
      board=find(document,'.workspace.mascot .board');lastSearch=now;
    }
    const rect=bed?.getBoundingClientRect(),boardRect=board?.getBoundingClientRect();
    if(!rect || !boardRect || !rect.width || rect.bottom<0 || boardRect.top>innerHeight){canvas.style.display='none';return;}
    visit.elapsed+=delta;
    const t=reduced.matches?12000:visit.elapsed;
    const size=rect.width,edge=document.querySelector('[data-testid="stMain"]')?.getBoundingClientRect().left ?? 0;
    let x=rect.left,y=rect.top,pose='deitado';
    ctx.clearRect(0,0,480,480);
    if(t<4200){
      pose=t<1450?'espiando':t<2850?'olhando-acima':'recolhendo';
      const reveal=t<1450?ease(t/1450):t<2850?1:1-ease((t-2850)/1350);
      x=edge-size+size*.52*reveal;y=Math.max(70,Math.min(innerHeight-size,boardRect.top+boardRect.height*.22));
      // The same sitting cat leans around the left edge, nose tilted upward.
      const look=ease((t-1400)/750);
      drawPose(12,1,mix(1.45,.9,look),1);
    } else if(t<4800){pose='fora';x=innerWidth+size;}
    else if(t<7350){
      pose='entrando-direita';
      const progress=ease((t-4800)/2550);
      x=mix(innerWidth+size*.2,rect.left,progress);
      y=rect.top+Math.sin((t-4800)/145)*size*.009*Math.sin(progress*Math.PI);
      const gait=(t-4800)/145,first=Math.floor(gait)%8,fraction=gait%1;
      drawPose(first,1-fraction,-Math.PI/2,1);
      drawPose((first+1)%8,fraction,-Math.PI/2,1);
    } else if(t<8250){
      pose='sentando';const p=ease((t-7350)/900);
      drawPose(8,1-p,mix(-Math.PI/2,-.35,p),1);
      drawPose(12,p,-.35,1);
    } else if(t<10250){
      pose='observando';drawPose(12,1,-.35+Math.sin((t-8250)/900)*.035,1);
    } else if(t<11750){
      pose='deitando';const p=ease((t-10250)/1500);
      drawPose(12,1-p,-.35,1-p*.12);
      drawPose(14,p,-.1,1,0);
    } else {
      drawPose(14,1,-.1,reduced.matches?1:1+Math.sin(t/1500)*.003,t);
    }
    canvas.dataset.pose=pose;
    canvas.style.display='block';canvas.style.left=x+'px';canvas.style.top=y+'px';
    canvas.style.width=size+'px';canvas.style.height=size+'px';
  }
  function pause(){running=false;cancelAnimationFrame(raf);lastTime=null;canvas.style.display='none';}
  function resume(){if(!running && ready){running=true;lastTime=null;raf=requestAnimationFrame(frame);}}
  parentElement._catScene={resume,pause};atlas.onload=prepare;atlas.onerror=pause;atlas.src=data.atlas;
  return pause;
}
