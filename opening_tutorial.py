"""A short, local tutorial that leads directly into opening practice."""
import streamlit as st


_TUTORIAL = st.components.v2.component(
    'opening_quick_tutorial',
    html='''<section class="tutorial" aria-label="Tutorial de aberturas">
      <div class="visual" aria-hidden="true"><div class="tiles"><span>♟</span></div>
      <div class="xp"><span></span></div></div>
      <div class="copy"><small class="step"></small><h2></h2>
      <p class="description" aria-live="polite"></p><p class="detail"></p>
      <div class="actions"><button class="next" type="button">Próximo</button>
      <button class="skip" type="button">Jogar agora</button></div></div>
    </section>''',
    css='''
    .tutorial{display:flex;align-items:center;gap:24px;padding:22px;border:1px solid #354149;border-radius:14px;background:#101d25;color:#f5f5f5;font-family:'Segoe UI',sans-serif}
    .visual{width:104px;flex:none}.tiles{height:104px;border-radius:10px;position:relative;background:conic-gradient(#577368 25%,#b9cabb 0 50%,#577368 0 75%,#b9cabb 0);background-size:52px 52px;overflow:hidden}
    .tiles span{position:absolute;left:28px;bottom:0;font-size:45px;line-height:52px;color:#fff;text-shadow:0 2px 3px #000;animation:move-piece 1.8s ease-in-out 2}
    .xp{height:6px;margin-top:12px;background:#354149;border-radius:4px;overflow:hidden}.xp span{display:block;height:100%;width:70%;background:#8ee4b4;animation:fill-xp 1.8s ease-out}
    .copy{flex:1;min-width:0}.step{color:#8ee4b4;font-size:12px}.copy h2{font-size:21px;margin:6px 0 8px}.copy p{font-size:15px;line-height:1.5;margin:0}.copy .detail{color:#aeb8bd;font-size:13px;margin-top:6px;min-height:40px}
    .actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}button{font:600 14px 'Segoe UI',sans-serif;cursor:pointer;min-height:42px;padding:10px 16px;border-radius:9px;border:1px solid #354149}.next{background:#8ee4b4;color:#081219}.skip{background:transparent;color:#ced8dd}button:focus-visible{outline:3px solid #ffbd69;outline-offset:3px}button:disabled{opacity:.6;cursor:default}
    @keyframes move-piece{0%,20%{transform:translateY(0)}65%,100%{transform:translateY(-52px)}}
    @keyframes fill-xp{from{width:0}to{width:70%}}
    @media(max-width:520px){.tutorial{padding:16px;gap:14px;align-items:flex-start}.visual{width:64px}.tiles{height:104px}.tiles span{left:6px}.copy h2{font-size:18px}.actions{gap:8px}button{padding:10px 12px}}
    @media(prefers-reduced-motion:reduce){.tiles span,.xp span{animation:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}) {
      const root=parentElement.querySelector('.tutorial');
      const steps=[
        ['Veja a dica e jogue','Aprenda os lances, repita de memória e resolva o quiz.',
         'Toque na peça e na casa de destino, ou arraste.'],
        ['Conclua o treino e ganhe pontos','Sem erro: 2 pontos · Com erro: 1 ponto · Com dica: 0,5 ponto.',
         'Os pontos chegam ao concluir a linha. Demonstração e exploração não pontuam.'],
        ['Suba no seu ritmo','100 pontos por nível. Cinco níveis por faixa. Cada abertura tem seu próprio progresso.',
         'Após 7 dias sem concluir treinos: −1 ponto por dia extra. Sua faixa é preservada.']
      ];
      let step=parentElement._tutorialStep || 0, pending=false;
      const next=root.querySelector('.next'),skip=root.querySelector('.skip');
      const play=()=>{if(pending)return;pending=true;next.disabled=skip.disabled=true;
        setTriggerValue('select',{id:data.id,intent:'learn'});};
      const paint=()=>{
        parentElement._tutorialStep=step;
        root.querySelector('.step').textContent='GUIA RÁPIDO · '+(step+1)+' / 3';
        root.querySelector('h2').textContent=steps[step][0];
        root.querySelector('.description').textContent=steps[step][1];
        root.querySelector('.detail').textContent=steps[step][2];
        next.textContent=step===2?'Começar a jogar':'Próximo';
        skip.textContent='Jogar agora · '+data.title;
        skip.hidden=step===2;
      };
      next.onclick=()=>{if(step<2){step++;paint();}else play();};
      skip.onclick=play;
      paint();
    }''',
)


def opening_tutorial(identifier, title, on_select):
    def play():
        event = st.session_state.openings_tutorial.select
        if isinstance(event, dict):
            on_select(event)
    _TUTORIAL(data=dict(id=identifier, title=title), key='openings_tutorial',
              on_select_change=play)
