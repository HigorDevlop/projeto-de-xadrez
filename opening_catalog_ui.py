"""Accessible, instant four-course selection with a single server confirmation."""
import chess
import chess.svg
import streamlit as st
from design_tokens import palette
from opening_repertoires import catalog


_CATALOG = st.components.v2.component(
    'opening_repertoire_catalog',
    html='''<section class="catalog" aria-label="Catálogo de repertórios">
      <header><div><span class="eyebrow">SEU REPERTÓRIO</span><h2>Prepare seu próximo lance.</h2></div>
      <p class="counter" role="status" aria-live="polite"></p></header>
      <div class="tabs" role="tablist" aria-label="Lado do tabuleiro"></div>
      <div class="cards" role="tabpanel" id="repertoire-panel"></div>
      <footer><p>Escolha até 4 aberturas. As linhas já estão organizadas para você.</p>
      <button class="confirm" type="button">Confirmar Seleção e Iniciar Trilha</button></footer>
    </section>''',
    css='''
    [hidden]{display:none!important}
    *{box-sizing:border-box}.catalog{font:15px/1.5 'Segoe UI',sans-serif;color:var(--ink)}
    header{position:sticky;top:0;z-index:2;background:var(--surface);display:flex;align-items:center;justify-content:space-between;gap:18px;padding:20px 0}
    h2{font-size:28px;letter-spacing:-.8px;font-weight:600;margin:4px 0}.eyebrow{font-size:10px;letter-spacing:2px;color:var(--muted);font-weight:700}
    .counter{white-space:nowrap;border:1px solid var(--border);border-radius:24px;padding:9px 16px;font-size:13px}
    .tabs{display:flex;gap:24px;border-bottom:1px solid var(--border);margin-bottom:28px;overflow:auto}
    .tabs button{background:none;border:0;border-bottom:2px solid transparent;border-radius:0;color:var(--muted);padding:14px 0;white-space:nowrap;font:500 13px 'Segoe UI',sans-serif;cursor:pointer}
    .tabs button[aria-selected=true]{color:var(--accent);border-color:var(--accent)}
    .cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;padding:4px;max-height:62vh;overflow:auto;scrollbar-width:thin}
    .card{position:relative;text-align:left;padding:22px;background:var(--surface);border:1px solid var(--border);border-radius:16px;color:var(--ink);font:inherit;cursor:pointer;transition:border-color .15s,opacity .15s,transform .15s}
    .card:hover{border-color:var(--accent);transform:translateY(-2px)}.card[aria-pressed=true]{border:2px solid var(--accent);padding:21px;background:var(--accent-soft)}
    .card:disabled{pointer-events:none;opacity:.45}.card:focus-visible,.tabs button:focus-visible,.confirm:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
    .preview{width:min(100%,168px);display:block;margin:2px auto 22px}.preview svg{width:100%;height:auto;display:block;border-radius:5px}
    .tag{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--muted);margin-bottom:9px}.tag svg{height:18px;width:18px;background:#F0F0E8;border-radius:50%;padding:1px}
    .title{display:block;font-weight:600;font-size:17px;line-height:1.3;margin-bottom:8px;min-height:44px}.notation{display:block;color:var(--muted);font-size:12px;min-height:36px}
    .count{display:block;font-size:12px;color:var(--muted);margin-top:14px}.check{position:absolute;right:14px;top:10px;color:var(--accent);font-weight:700}
    footer{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:28px 0 4px}footer p{color:var(--muted);font-size:12px;max-width:280px}
    .confirm{border:0;border-radius:10px;background:var(--accent);color:var(--accent-ink);padding:15px 22px;font:600 13px 'Segoe UI',sans-serif;cursor:pointer}.confirm:disabled{opacity:.45;cursor:default}
    @media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.tabs{gap:18px}}
    @media(max-width:560px){header{align-items:flex-start;flex-direction:column;gap:0}h2{font-size:24px}.counter{margin:12px 0 0}.cards{gap:12px}.card{padding:14px}.card[aria-pressed=true]{padding:13px}.title{font-size:14px}.preview{margin-bottom:14px}.tabs{margin-bottom:18px}footer{flex-direction:column;align-items:stretch}footer p{max-width:none;margin:0}.confirm{width:100%}}
    @media(prefers-reduced-motion:reduce){.card{transition:none}}
    ''',
    js='''export default function({data,parentElement,setTriggerValue}) {
      const root=parentElement.querySelector('.catalog'),host=parentElement.host??parentElement;
      Object.entries(data.colors).forEach(([k,v])=>host.style.setProperty('--'+k.replaceAll('_','-'),v));
      root.querySelector('header').hidden=Boolean(data.instant);
      root.querySelector('footer').hidden=Boolean(data.instant);
      const selected=parentElement._selected??new Set(data.selected||[]);parentElement._selected=selected;
      const groups=[['white','Brancas'],['black','Pretas']];
      let group=parentElement._group?.startsWith('black')?'black':'white';let pending=false;
      const tabs=root.querySelector('.tabs'),cards=root.querySelector('.cards'),confirm=root.querySelector('.confirm');
      tabs.replaceChildren();
      groups.forEach(([id,label],index)=>{
        const tab=document.createElement('button');tab.type='button';tab.role='tab';tab.textContent=label;tab.dataset.group=id;tab.id='tab-'+id;tab.setAttribute('aria-controls','repertoire-panel');
        tab.onclick=()=>{group=id;parentElement._group=id;paint();};
        tab.onkeydown=e=>{let next=null;if(e.key==='ArrowRight')next=(index+1)%groups.length;if(e.key==='ArrowLeft')next=(index+groups.length-1)%groups.length;if(e.key==='Home')next=0;if(e.key==='End')next=groups.length-1;if(next!==null){e.preventDefault();tabs.children[next].click();tabs.children[next].focus();}};
        tabs.append(tab);
      });
      function sync(){
        root.querySelector('.counter').textContent=`Aberturas Selecionadas: [${selected.size}/4]`;
        confirm.disabled=pending||!data.valid||selected.size<1||selected.size>4;
        cards.querySelectorAll('.card').forEach(card=>{const picked=!data.instant&&selected.has(card.dataset.id);card.setAttribute('aria-pressed',String(picked));card.disabled=pending||(data.instant?!data.valid:(!picked&&selected.size===4));card.querySelector('.check').textContent=picked?'✓':'';});
      }
      function paint(){
        tabs.querySelectorAll('button').forEach(tab=>{const active=tab.dataset.group===group;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});
        cards.setAttribute('aria-labelledby','tab-'+group);cards.replaceChildren();
        data.courses.filter(c=>c.side===group).forEach(course=>{
          const button=document.createElement('button');button.type='button';button.className='card';button.dataset.id=course.id;
          button.setAttribute('aria-label',`${course.title}, ${course.side==='white'?'brancas':'pretas'}, ${course.count} linhas`);
          // All SVG comes from python-chess, never from user supplied markup.
          button.innerHTML='<span class="check" aria-hidden="true"></span><span class="preview" aria-hidden="true">'+course.svg+'</span><span class="tag">'+course.piece+'</span><strong class="title"></strong><span class="notation"></span><span class="count"></span>';
          button.querySelector('.tag').append(document.createTextNode(course.side==='white'?'Brancas':'Pretas'));
          button.querySelector('.title').textContent=course.title;button.querySelector('.notation').textContent=course.notation;button.querySelector('.count').textContent=course.count+' linhas';
          button.onclick=()=>{if(data.instant){if(pending||!data.valid)return;pending=true;cards.querySelectorAll('button').forEach(b=>b.disabled=true);setTriggerValue('confirm',{ids:[course.id],start:data.start,end:data.end});return;}if(selected.has(course.id))selected.delete(course.id);else if(selected.size<4)selected.add(course.id);sync();};
          cards.append(button);
        });sync();
      }
      confirm.onclick=()=>{if(confirm.disabled)return;pending=true;sync();setTriggerValue('confirm',{ids:[...selected],start:data.start,end:data.end});};
      paint();
    }''',
)


@st.cache_data(show_spinner=False)
def catalog_cards():
    return [dict(id=c['id'], title=c['title'], side=c['side'], group=c['group'],
                 notation=c['notation'], count=len(c['lines']),
                 piece=chess.svg.piece(chess.Piece(chess.PAWN, c['side'] == 'white')),
                 svg=chess.svg.board(chess.Board(c['fen']), orientation=c['side'] == 'white',
                     coordinates=False, size=168,
                     colors={'square light': '#F0F0E8', 'square dark': '#8DA38B'})) for c in catalog()]


def repertoire_catalog(start, end, on_confirm, dark=False, *, instant=False):
    _CATALOG(data={'courses': catalog_cards(), 'colors': palette(dark),
                   'instant': instant, 'selected': st.session_state.get('prep_selected_openings', []),
                   'start': str(start), 'end': str(end), 'valid': start <= end and (end-start).days <= 365},
             key='prep_catalog', on_confirm_change=on_confirm)
