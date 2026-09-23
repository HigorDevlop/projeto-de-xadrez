export default function ({parentElement}) {
  // Keep one scene alive across Streamlit reruns; navigation must not restart the lap.
  if (parentElement._catScene) { parentElement._catScene.resume(); return parentElement._catScene.pause; }
  const canvas=parentElement.querySelector('canvas');
  const gl=canvas.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:false});
  if(!gl) {canvas.hidden=true;return;}
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  const vertex=`attribute vec3 position;attribute vec3 normal;uniform mat4 model;uniform mat4 camera;
    uniform mat3 normals;varying vec3 n;void main(){n=normalize(normals*normal);gl_Position=camera*model*vec4(position,1.0);}`;
  const fragment=`precision mediump float;varying vec3 n;uniform vec3 color;
    void main(){float light=.48+.52*max(dot(normalize(n),normalize(vec3(-.3,1.0,1.5))),0.0);gl_FragColor=vec4(color*light,1.0);}`;
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error('Não foi possível preparar o mascote 3D.');return s;}
  const program=gl.createProgram();
  const shaders=[shader(gl.VERTEX_SHADER,vertex),shader(gl.FRAGMENT_SHADER,fragment)];
  for(const s of shaders)gl.attachShader(program,s);
  gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS)){canvas.hidden=true;return;}
  gl.useProgram(program);gl.enable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);
  const loc={};for(const name of ['model','camera','normals','color'])loc[name]=gl.getUniformLocation(program,name);
  const pos=gl.getAttribLocation(program,'position'),normal=gl.getAttribLocation(program,'normal');
  function identity(){return [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];}
  function multiply(a,b){const m=new Array(16).fill(0);for(let c=0;c<4;c++)for(let r=0;r<4;r++)
    for(let k=0;k<4;k++)m[c*4+r]+=a[k*4+r]*b[c*4+k];return m;}
  function translate(x,y,z){const m=identity();m[12]=x;m[13]=y;m[14]=z;return m;}
  function rotateY(a){const c=Math.cos(a),s=Math.sin(a);return [c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1];}
  function rotateX(a){const c=Math.cos(a),s=Math.sin(a);return [1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1];}
  // Orthographic camera directly above the floor: the cat's back is visible.
  const projection=[.48,0,0,0,0,.48,0,0,0,0,-.1,0,0,0,0,1];
  gl.uniformMatrix4fv(loc.camera,false,multiply(projection,rotateX(Math.PI/2)));
  canvas.dataset.view='superior';
  function mesh(cone=false){
    const vertices=[],normals=[],indices=[],rows=cone?1:14,cols=24;
    for(let i=0;i<=rows;i++)for(let j=0;j<=cols;j++){
      const theta=j*2*Math.PI/cols,phi=i*Math.PI/rows;
      const x=cone?(i?Math.cos(theta):0):Math.sin(phi)*Math.cos(theta);
      const y=cone?(i?0:1):Math.cos(phi),z=cone?(i?Math.sin(theta):0):Math.sin(phi)*Math.sin(theta);
      vertices.push(x,y,z);normals.push(cone?Math.cos(theta):x,cone ? .5 : y,cone?Math.sin(theta):z);
      if(i<rows&&j<cols){const a=i*(cols+1)+j,b=a+cols+1;indices.push(a,b,a+1,b,b+1,a+1);}
    }
    const buffers=[gl.createBuffer(),gl.createBuffer(),gl.createBuffer()];
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers[0]);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers[1]);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(normals),gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers[2]);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
    return {buffers,count:indices.length};
  }
  const ball=mesh(),ear=mesh(true),fur=[.94,.55,.23],cream=[1,.89,.7],stripe=[.38,.19,.08];
  let heading=0;
  function part(x,y,z,sx,sy,sz,color,shape=ball){
    const m=multiply(rotateY(heading),translate(x,y,z));
    for(let r=0;r<3;r++){m[r]*=sx;m[4+r]*=sy;m[8+r]*=sz;}
    const n=[m[0]/(sx*sx),m[1]/(sx*sx),m[2]/(sx*sx),m[4]/(sy*sy),m[5]/(sy*sy),m[6]/(sy*sy),m[8]/(sz*sz),m[9]/(sz*sz),m[10]/(sz*sz)];
    gl.uniformMatrix4fv(loc.model,false,m);gl.uniformMatrix3fv(loc.normals,false,n);gl.uniform3fv(loc.color,color);
    gl.bindBuffer(gl.ARRAY_BUFFER,shape.buffers[0]);gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,3,gl.FLOAT,false,0,0);
    gl.bindBuffer(gl.ARRAY_BUFFER,shape.buffers[1]);gl.enableVertexAttribArray(normal);gl.vertexAttribPointer(normal,3,gl.FLOAT,false,0,0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,shape.buffers[2]);gl.drawElements(gl.TRIANGLES,shape.count,gl.UNSIGNED_SHORT,0);
  }
  function draw(seconds,rest){
    gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    const bob=rest?0:Math.sin(seconds*12)*.04,bodyY=.95-.48*rest+bob,headY=1.35-.55*rest+bob;
    part(0,bodyY,0,.91,.47,.43,fur);
    for(const x of [-.57,.55])for(const z of [-.27,.27]){
      const step=(1-rest)*Math.sin(seconds*12+(x*z>0?Math.PI:0))*.17;
      part(x+step+.12*rest,.45-.26*rest,z,.14+.15*rest,.43-.3*rest,.15,fur);
      part(x+step+.16*rest,.12,z,.2+.12*rest,.12,.17,cream);
    }
    part(.77,headY,0,.48,.43,.4,fur);
    for(const z of [-.24,.24]){
      part(.66,headY+.28,z,.22,.43,.2,fur,ear);
      part(.73,headY+.31,z,.1,.27,.12,[.91,.57,.48],ear);
      part(1.08,headY-.1,z*.65,.21,.15,.17,cream);
      part(1.12,headY+.11,z,.085,.105,.075,[.5,.78,.32]);
      part(1.18,headY+.11,z,.022,.08,.038,[.03,.04,.035]);
    }
    part(1.26,headY-.04,0,.06,.05,.08,[.38,.16,.13]);
    for(const x of [-.45,-.05,.35])part(x,bodyY+.36,-.04,.065,.095,.36,stripe);
    // Once lying down, every part above is fixed. Only these tail joints move.
    const swish=reduced.matches?0:Math.sin(seconds*2.2)*.5;
    for(let i=0;i<10;i++){
      const u=i/9;
      part(-.8-u*.9,bodyY+.05+Math.sin(u*2)*(.35-.2*rest),Math.sin(u*1.7+swish)*u*.65,
        .14-u*.035,.12-u*.025,.12-u*.025,i>7?cream:fur);
    }
  }
  function findBoard(root){
    const found=root.querySelector('.board');if(found)return found;
    for(const el of root.querySelectorAll('*'))if(el.shadowRoot){const b=findBoard(el.shadowRoot);if(b)return b;}
    return null;
  }
  let board=null,started=null,elapsed=0,last=0,raf=0,running=false,lastSearch=0;
  function frame(now){
    if(!running)return;
    raf=requestAnimationFrame(frame);
    if(document.hidden||now-last<32)return;
    last=now;
    if(!board?.isConnected && now-lastSearch>250){board=findBoard(document);lastSearch=now;}
    if(!board){canvas.style.display='none';return;}
    const rect=board.getBoundingClientRect();
    if(!rect.width||rect.bottom<0||rect.top>innerHeight){canvas.style.display='none';return;}
    canvas.style.display='block';
    if(started===null)started=now;
    elapsed=(now-started)/1000;
    const walk=reduced.matches?1:Math.min(1,elapsed/8),rest=reduced.matches?1:Math.max(0,Math.min(1,(elapsed-8)/.9));
    const floor=board.closest('.board-floor');
    const gutter=floor ? parseFloat(getComputedStyle(floor).paddingLeft) : 100;
    const size=Math.max(128,Math.min(230,(gutter || 100)*2.3)),gap=(gutter || 100)/2;
    canvas.style.width=size+'px';canvas.style.height=size+'px';
    // The reserved transparent floor belongs to the page background. The cat's
    // body stays outside the board on all four sides, even in split/mobile layouts.
    const left=rect.left-gap,right=rect.right+gap,top=rect.top-gap,bottom=rect.bottom+gap;
    const w=right-left,h=bottom-top,perimeter=2*(w+h),distance=walk*perimeter;
    let x,y;
    if(distance<w){x=right-distance;y=bottom;heading=Math.PI;}
    else if(distance<w+h){x=left;y=bottom-(distance-w);heading=Math.PI/2;}
    else if(distance<2*w+h){x=left+(distance-w-h);y=top;heading=0;}
    else{x=right;y=top+(distance-2*w-h);heading=-Math.PI/2;}
    // Rest at the end of the lap; keep the body fixed and swish only the tail.
    canvas.style.left=(x-size/2)+'px';canvas.style.top=(y-size/2)+'px';
    canvas.dataset.pose=rest===1?'deitado':walk===1?'deitando':'caminhando';
    canvas.dataset.laps=walk===1?'1':'0';
    draw(elapsed,rest);
    if(reduced.matches){cancelAnimationFrame(raf);running=false;}
  }
  function resume(){
    window.addEventListener('scroll',resume,true);window.addEventListener('resize',resume);
    if(!running){running=true;raf=requestAnimationFrame(frame);}
  }
  function pause(){running=false;cancelAnimationFrame(raf);
    window.removeEventListener('scroll',resume,true);window.removeEventListener('resize',resume);}
  parentElement._catScene={resume,pause};resume();
  return pause;
}
