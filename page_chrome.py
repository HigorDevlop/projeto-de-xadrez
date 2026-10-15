"""Recolhe a navegação apenas no celular; preserva os atalhos no desktop."""
import streamlit as st


_CHROME = st.components.v2.component(
    'chess_page_chrome', html='<span hidden></span>',
    js='''export default function(){
      if(window.__chessSidebarReady)return;
      function initialize(){
        const sidebar=document.querySelector('[data-testid="stSidebar"]');
        if(!sidebar)return false;
        if(window.matchMedia('(max-width: 768px)').matches && sidebar.getAttribute('aria-expanded')==='true'){
          const control=sidebar.querySelector('[data-testid="stSidebarCollapseButton"] button,button[data-testid="stSidebarCollapseButton"]');
          if(!control)return false;
          control.click();
        }
        window.__chessSidebarReady=true;return true;
      }
      if(initialize())return;
      const observer=new MutationObserver(()=>{if(initialize())observer.disconnect();});
      observer.observe(document.body,{childList:true,subtree:true});
      return ()=>observer.disconnect();
    }''',
)


def page_chrome():
    _CHROME(key='page_chrome', height=0)
