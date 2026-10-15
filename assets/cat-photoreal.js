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
  function restingLayers(p){
    // Warp a small patch around the free tip, continuously fading displacement
    // to zero at its attachment. The torso pixels remain untouched.
    const left=Math.max(0,p.x-12),top=Math.floor(p.y+p.h*.68);
    const width=Math.ceil(p.x+p.w*.46-left),height=Math.min(400,p.y+p.h+12)-top;
    const tile=document.createElement('canvas');tile.width=tile.height=400;
    const output=tile.getContext('2d');output.drawImage(p.tile,0,0);
    return {tile,output,left,top,width,height,patch:output.createImageData(width,height),
      pixels:p.tile.getContext('2d').getImageData(0,0,400,400).data,
      pivot:{x:p.x+p.w*.43,y:p.y+p.h*.94}};
  }
  function restingFrame(p,sway){
    const layer=p.resting ??= restingLayers(p),{left,top,width,height,pixels,patch,pivot}=layer;
    for(let row=0;row<height;row++)for(let col=0;col<width;col++){
      const x=left+col,y=top+row;let sx=x,sy=y;
      // Inverse mapping with bilinear sampling avoids triangular seams and gaps.
      for(let step=0;step<2;step++){
        const weight=ease((.46-(sx-p.x)/p.w)/.28)*ease(((sy-p.y)/p.h-.70)/.16);
        const angle=sway*weight,cos=Math.cos(angle),sin=Math.sin(angle);
        sx=pivot.x+(x-pivot.x)*cos+(y-pivot.y)*sin;
        sy=pivot.y-(x-pivot.x)*sin+(y-pivot.y)*cos;
      }
      sx=Math.max(0,Math.min(398.999,sx));sy=Math.max(0,Math.min(398.999,sy));
      const ix=Math.floor(sx),iy=Math.floor(sy),fx=sx-ix,fy=sy-iy;
      const a=(iy*400+ix)*4,b=a+4,c=a+1600,d=c+4,out=(row*width+col)*4;
      for(let channel=0;channel<4;channel++)patch.data[out+channel]=
        mix(mix(pixels[a+channel],pixels[b+channel],fx),mix(pixels[c+channel],pixels[d+channel],fx),fy);
    }
    layer.output.putImageData(patch,left,top);return layer.tile;
  }
  function drawPose(index,alpha,angle,breath,tailTime=null){
    if(alpha<=0)return;
    const p=poses[index];
    // Constant cell scale: tail length must not make the entire animal grow/shrink.
    const scale=1.06;
    ctx.save();ctx.globalAlpha=alpha;ctx.globalCompositeOperation='lighter';ctx.translate(240,240);ctx.rotate(angle);
    ctx.translate(-200*scale,-200*scale);ctx.scale(scale,scale);
    if(tailTime===null){ctx.drawImage(p.tile,0,0);}
    else {
      const seconds=tailTime/1000;
      const sway=reduced.matches?0:(Math.sin(seconds*1.35)*.08+Math.sin(seconds*.61+.4)*.025);
      ctx.drawImage(sway===0?p.tile:restingFrame(p,sway),0,0);
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
      drawPose(12,1,mix(1.10,.92,look),1);
    } else if(t<4800){pose='fora';x=innerWidth+size;}
    else if(t<7350){
      pose='entrando-direita';
      const progress=ease((t-4800)/2550);
      x=mix(innerWidth+size*.2,rect.left,progress);
      y=rect.top+Math.sin((t-4800)/145)*size*.009*Math.sin(progress*Math.PI);
      const distance=(innerWidth+size*.2-rect.left)*progress;
      const gait=distance/(size*.32)*8,first=Math.floor(gait)%8,fraction=gait%1;
      const heading=mix(-Math.PI/2,-.35,ease((progress-.60)/.40));
      drawPose(first,1-fraction,heading,1);
      drawPose((first+1)%8,fraction,heading,1);
    } else if(t<8250){
      pose='sentando';const p=ease((t-7350)/900);
      const gait=(innerWidth+size*.2-rect.left)/(size*.32)*8,first=Math.floor(gait)%8,fraction=gait%1;
      drawPose(first,(1-fraction)*(1-p),-.35,1);
      drawPose((first+1)%8,fraction*(1-p),-.35,1);
      drawPose(12,p,-.35,1);
    } else if(t<10250){
      pose='observando';drawPose(12,1,-.35,1);
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
