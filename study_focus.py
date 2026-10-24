"""Browser-local immersive layout, kept across page and board reruns."""
import streamlit as st


_FOCUS = st.components.v2.component(
    'book_study_focus',
    html='<button type="button" class="start-study">Começar estudos <span>↗</span></button><small class="focus-hint" hidden>← → na área selecionada · Clique no livro para páginas ou no tabuleiro para lances · Esc para sair</small>',
    css='''button{display:flex;align-items:center;gap:18px;border:1px solid #ff920e;border-radius:10px;
    padding:11px 18px;background:#ff8500;color:#100c06;font:600 14px/1.4 system-ui;cursor:var(--club-cursor-link,pointer)}
    button:hover{background:#ffa024}button:focus-visible{outline:2px solid white;outline-offset:3px}
    small{color:#b6b6b6;font:12px/1.5 system-ui} [hidden]{display:none}''',
    js='''export default function({parentElement,data,setTriggerValue}) {
      const root=document.documentElement, button=parentElement.querySelector('button');
      const hint=parentElement.querySelector('small');
      function alignStudy(){
        const workspace=document.querySelector('.st-key-reading_workspace');
        const page=document.querySelector('.st-key-book_page_reader');
        const floor=document.querySelector('.st-key-study_position');
        if(!workspace||!page||!floor)return;
        dimensions.observe(page);dimensions.observe(floor);
        if(innerWidth<=700){workspace.style.removeProperty('--study-board-size');return;}
        const padding=getComputedStyle(floor);
        const boardWidth=floor.clientWidth-parseFloat(padding.paddingLeft)-parseFloat(padding.paddingRight);
        const size=Math.floor(boardWidth);
        const value=size+'px';
        if(size>0 && workspace.style.getPropertyValue('--study-board-size')!==value)
          workspace.style.setProperty('--study-board-size',value);
      }
      const dimensions=new ResizeObserver(alignStudy);
      let navigation=window.__bookReaderNavigation;
      if(!navigation || navigation.book!==data.book || navigation.epoch!==data.epoch){
        if(navigation)clearTimeout(navigation.timer);
        navigation={book:data.book,epoch:data.epoch,page:data.page,sequence:data.ack,
          sent:data.ack,cache:new Map(),timer:null};
        window.__bookReaderNavigation=navigation;
      }else if(navigation.sequence<=data.ack){navigation.page=data.page;}
      navigation.trigger=setTriggerValue;
      function flush(){
        if(window.__bookReaderNavigation!==navigation || !document.querySelector('.st-key-reading_workspace') ||
           navigation.sequence<=navigation.sent)return;
        navigation.sent=navigation.sequence;
        navigation.trigger('navigate',{book:navigation.book,epoch:navigation.epoch,
          page:navigation.page,sequence:navigation.sequence});
      }
      function schedule(){clearTimeout(navigation.timer);navigation.timer=setTimeout(flush,90);}
      function acknowledge(){
        document.querySelectorAll('.book-page-preloads img').forEach(img=>{
          navigation.cache.set(Number(img.dataset.page),img.src);
        });
        while(navigation.cache.size>12)navigation.cache.delete(navigation.cache.keys().next().value);
        const image=document.querySelector('.book-page-image');
        const source=navigation.cache.get(navigation.page);
        if(image && image.dataset.book===navigation.book && source && image.src!==source){
          image.src=source;image.alt='Página '+(navigation.page+1);
        }
        for(const [key,disabled] of [['previous',navigation.page===0],['next',navigation.page===data.count-1]]){
          const control=document.querySelector('.st-key-reader_'+key+' button');
          if(control && control.disabled!==disabled)control.disabled=disabled;
        }
      }
      function turn(delta){
        const page=Math.max(0,Math.min(data.count-1,navigation.page+delta));
        if(page===navigation.page)return;
        navigation.page=page;navigation.sequence++;acknowledge();schedule();
      }
      function preview(event){
        const target=event.composedPath()[0];
        const previous=target?.closest?.('.st-key-reader_previous');
        const next=target?.closest?.('.st-key-reader_next');
        if(!previous&&!next)return;
        event.preventDefault();event.stopImmediatePropagation();turn(next?1:-1);
      }
      if(navigation.sequence>navigation.sent)schedule();
      const images=new MutationObserver(()=>{
        alignStudy();
        acknowledge();
        document.querySelectorAll('.book-page-preloads img').forEach(img=>{img.decode?.().catch(()=>{});});
      });
      images.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-page','data-book','disabled']});
      acknowledge();
      alignStudy();
      function paint(){const active=root.classList.contains('book-study-focus');button.hidden=active;hint.hidden=!active;alignStudy();}
      function exit(){root.classList.remove('book-study-focus');paint();
        window.__bookFocusObserver?.disconnect();
        if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});}
      button.onclick=()=>{root.classList.add('book-study-focus');paint();
        window.__bookFocusObserver?.disconnect();
        window.__bookFocusObserver=new MutationObserver(()=>{
          if(!document.querySelector('.st-key-reading_workspace'))exit();});
        window.__bookFocusObserver.observe(document.body,{childList:true,subtree:true});
        root.requestFullscreen?.().catch(()=>{});};
      function selectArea(event){
        const path=event.composedPath();
        const workspace=document.querySelector('.st-key-reading_workspace');
        if(!workspace)return;
        if(path.some(el=>el.matches?.('.st-key-study_position')))
          workspace.dataset.keyboardArea='board';
        else if(path.some(el=>el.matches?.('.st-key-study_reading_panel')))
          workspace.dataset.keyboardArea='book';
      }
      function key(event){if(event.key==='Escape' && root.classList.contains('book-study-focus')){
        event.preventDefault();exit();return;}
        if(!['ArrowLeft','ArrowRight'].includes(event.key)||event.altKey||event.ctrlKey||event.metaKey||event.shiftKey)return;
        if(event.composedPath().some(el=>el.matches?.('input,textarea,select,[contenteditable="true"],[role="dialog"],[role="slider"],[role="combobox"],[role="listbox"],[role="radio"],[role="tab"],[data-testid="stPopoverBody"]')))return;
        const workspace=document.querySelector('.st-key-reading_workspace');
        if(!workspace || workspace.dataset.keyboardArea!=='book')return;
        event.preventDefault();event.stopImmediatePropagation();
        turn(event.key==='ArrowLeft'?-1:1);
      }
      function fullscreen(){if(!document.fullscreenElement)exit();}
      document.addEventListener('keydown',key,true);
      document.addEventListener('pointerdown',selectArea,true);
      document.addEventListener('click',selectArea,true);
      document.addEventListener('click',preview,true);
      document.addEventListener('fullscreenchange',fullscreen);
      window.addEventListener('resize',alignStudy);
      paint();
      return ()=>{document.removeEventListener('keydown',key,true);document.removeEventListener('click',preview,true);
        document.removeEventListener('pointerdown',selectArea,true);document.removeEventListener('click',selectArea,true);
        images.disconnect();dimensions.disconnect();window.removeEventListener('resize',alignStudy);
        document.removeEventListener('fullscreenchange',fullscreen);
        if(!document.querySelector('.st-key-reading_workspace'))exit();};
    }''',
)


def render_focus_button(count):
    st.html('''<style>
    .st-key-reading_workspace{margin-top:12px!important;padding-top:0!important;border-top:0!important}
    .st-key-book_workspace_refresh{display:none!important}
    .st-key-reading_workspace [data-stale="true"]{opacity:1!important}
    .st-key-study_reading_panel,.st-key-study_position{padding:14px!important;border-radius:14px!important}
    .st-key-reader_heading,.st-key-study_board_heading{height:48px!important;min-height:48px!important;max-height:48px!important;align-items:center}
    .st-key-reader_heading{display:flex;justify-content:center}
    .st-key-reader_heading .reader-title{margin:0!important}
    .st-key-reading_workspace .book-page-image{width:100%;height:var(--study-board-size,auto);object-fit:contain}
    .st-key-study_position .board{max-width:100%}
    .book-study-focus .st-key-reading_workspace{position:fixed!important;inset:0!important;z-index:999999;
      background:#080909;padding:16px 24px!important;margin:0!important;overflow:auto;height:100dvh;box-sizing:border-box}
    .book-study-focus [data-testid="stSidebar"],.book-study-focus [data-testid="stHeader"],
    .book-study-focus .st-key-question_launcher{display:none!important}
    .book-study-focus [data-baseweb="popover"]{z-index:1000001!important}
    .book-study-focus .st-key-study_position .board-floor{padding:0!important}
    .book-study-focus .st-key-study_position .workspace{gap:8px}
    .book-study-focus .st-key-study_position nav{margin-top:8px}
    .book-study-focus .st-key-study_position .cat-place{display:none}
    @media(max-width:700px){.book-study-focus .st-key-reading_workspace{padding:12px!important}}
    </style>''')
    from book_reader import navigate_reader
    state = st.session_state
    _FOCUS(key='study_focus_control', height='content',
           data={'book': state.reader_book, 'page': state.reader_page, 'count': count,
                 'epoch': state.get('reader_epoch', 0), 'ack': state.get('reader_navigation_ack', 0)},
           on_navigate_change=lambda: navigate_reader(count))
