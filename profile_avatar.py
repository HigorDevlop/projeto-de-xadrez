"""Native browser image picker with a local square crop; only the crop is uploaded."""
import base64

import streamlit as st

from profile_photo import normalize_photo


_AVATAR = st.components.v2.component(
    "acervo_profile_avatar",
    html='''<button class="avatar" type="button" aria-label="Selecionar foto do perfil"></button>
    <input class="file" type="file" accept="image/png,image/jpeg,image/webp" hidden>
    <div class="editor" hidden><p>Arraste a foto para ajustar o corte.</p>
    <canvas width="320" height="320" aria-label="Prévia do corte quadrado"></canvas>
    <label>Zoom <input class="zoom" type="range" min="1" max="4" step="0.01" value="1"></label>
    <button class="save" type="button">Usar foto</button>
    <button class="cancel" type="button">Cancelar</button></div>
    <p class="error" role="alert"></p>''',
    css='''
    .avatar {width:128px;height:128px;padding:0;overflow:hidden;cursor:pointer;
      border:2px solid var(--st-primary-color);border-radius:12px;background:var(--st-secondary-background-color);
      color:var(--st-text-color);font:48px sans-serif}
    .avatar img {display:block;width:100%;height:100%;object-fit:cover}
    .editor {max-width:340px;color:var(--st-text-color)}
    canvas {width:100%;max-width:320px;touch-action:none;cursor:move;border-radius:8px}
    .editor label {display:block;margin:8px 0}.editor button {padding:8px;margin:4px}
    .error {color:#dc2626;font-size:14px}
    ''',
    js='''
    export default function({data,parentElement,setTriggerValue}) {
      const q=s=>parentElement.querySelector(s);
      const avatar=q('.avatar'), input=q('.file'), editor=q('.editor'), canvas=q('canvas');
      if(parentElement._cropActive)return;
      avatar.replaceChildren();
      if(data.photo){const photo=new Image();photo.src=data.photo;photo.alt='Foto do perfil';avatar.append(photo);}
      else avatar.textContent='＋';
      const ctx=canvas.getContext('2d');
      let picture=null, scale=1, x=0, y=0, drag=null, objectUrl=null;
      function draw(){
        if(!picture)return;
        const w=picture.width*scale,h=picture.height*scale;
        x=Math.min(0,Math.max(320-w,x));y=Math.min(0,Math.max(320-h,y));
        ctx.clearRect(0,0,320,320);ctx.drawImage(picture,x,y,w,h);
      }
      function close(){editor.hidden=true;input.value='';parentElement._cropActive=false;
        picture=null;if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;}
      avatar.onclick=()=>input.click();
      input.onchange=()=>{
        const file=input.files?.[0];if(!file)return;
        q('.error').textContent='';
        if(file.size>10*1024*1024){q('.error').textContent='Escolha uma imagem de até 10 MB.';input.value='';return;}
        if(objectUrl)URL.revokeObjectURL(objectUrl);
        objectUrl=URL.createObjectURL(file);const img=new Image();
        img.onerror=()=>{q('.error').textContent='Não foi possível abrir a foto.';close();};
        img.onload=()=>{
          if(img.width*img.height>20000000){q('.error').textContent='Escolha uma imagem com até 20 milhões de pixels.';close();return;}
          picture=img;scale=Math.max(320/img.width,320/img.height);
          x=(320-img.width*scale)/2;y=(320-img.height*scale)/2;
          q('.zoom').value=1;editor.hidden=false;parentElement._cropActive=true;draw();
        };img.src=objectUrl;
      };
      q('.zoom').oninput=e=>{
        if(!picture)return;
        const previous=scale;scale=Math.max(320/picture.width,320/picture.height)*Number(e.target.value);
        x=160-(160-x)*scale/previous;y=160-(160-y)*scale/previous;draw();
      };
      canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);};
      canvas.onpointermove=e=>{
        if(!drag)return;const factor=320/canvas.getBoundingClientRect().width;
        x+=(e.clientX-drag.x)*factor;y+=(e.clientY-drag.y)*factor;drag={x:e.clientX,y:e.clientY};draw();
      };
      canvas.onpointerup=canvas.onpointercancel=()=>{drag=null;};
      q('.cancel').onclick=close;
      q('.save').onclick=()=>{if(!picture)return;const photo=canvas.toDataURL('image/png');close();setTriggerValue('photo',photo);};
    }
    ''',
)


def decode_avatar(value):
    if not isinstance(value, str) or not value.startswith('data:image/png;base64,') or len(value) > 1_000_000:
        raise ValueError("Foto inválida. Selecione e recorte a imagem novamente.")
    try:
        raw = base64.b64decode(value.split(',', 1)[1], validate=True)
    except ValueError as error:
        raise ValueError("Foto inválida.") from error
    return normalize_photo(raw, square=True)


def avatar_changed():
    try:
        st.session_state.profile_bytes = decode_avatar(st.session_state.avatar_picker.photo)
        st.session_state.pop('photo_error', None)
    except ValueError as error:
        st.session_state.photo_error = str(error)


def profile_avatar(photo):
    encoded = 'data:image/png;base64,' + base64.b64encode(photo).decode() if photo else None
    return _AVATAR(data={'photo': encoded}, key='avatar_picker', on_photo_change=avatar_changed)
