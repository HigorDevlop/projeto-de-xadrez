"""A shared, responsive visual language for classroom workspaces."""
from html import escape
from base64 import b64encode
import streamlit as st

ICONS={
 'target':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
 'calendar':'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18m-12 4h.1m4 0h.1m-4 3h.1"/>',
 'video':'<rect x="3" y="5" width="13" height="14" rx="3"/><path d="m16 9 5-3v12l-5-3"/>',
 'chat':'<path d="M21 11a9 9 0 0 1-9 9H4l-2 2 1-7a9 9 0 1 1 18-4Z"/><path d="M7 9h10M7 13h6"/>',
 'book':'<path d="M12 5c-3-2-6-2-10-1v16c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Zm0 0v16"/>',
 'chart':'<path d="M4 3v18h18M8 16v-4m5 4V8m5 8V5"/>',
 'shield':'<path d="m12 2 9 4v6c0 5-5 9-9 10-4-1-9-5-9-10V6Z"/><path d="M12 7v6m0 3h.1"/>',
 'play':'<path d="m9 5 11 7L9 19Z"/>',
 'users':'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-17a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5v2"/>'}


def icon(name):
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#bdd8c5" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'+ICONS.get(name,ICONS['target'])+'</svg>'
    return '<img src="data:image/svg+xml;base64,'+b64encode(svg.encode()).decode()+'" alt="" width="24" height="24" aria-hidden="true"/>'


def apply():
    st.html('<span class="prep-shell" hidden></span><style>'+STYLE+'</style>')


def hero(title,subtitle='Sua sala, em movimento.',badge='COACH / SALA'):
    st.html(f'<div class="prep-hero"><div><span class="prep-eyebrow">{escape(badge)}</span><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div><span class="prep-hero-mark">{icon("book")}</span></div>')


def section(number,title,subtitle=''):
    st.html(f'<div class="prep-section"><span>{escape(str(number))}</span><div><h3>{escape(title)}</h3>{"<p>"+escape(subtitle)+"</p>" if subtitle else ""}</div></div>')


def empty(title,description='',symbol='target'):
    st.html(f'<div class="prep-empty"><div class="prep-empty-icon">{icon(symbol)}</div><h4>{escape(title)}</h4><p>{escape(description)}</p></div>')


def summary(openings,lines,tactics,minutes,weekdays):
    items=[('book',str(openings),'aberturas'),('target',str(lines),'linhas'),('chart',str(tactics),'táticos'),('calendar',str(minutes)+' min','por sessão')]
    body=''.join(f'<div class="prep-plan-stat"><span>{icon(sym)}</span><div><strong>{escape(value)}</strong><small>{label}</small></div></div>' for sym,value,label in items)
    st.html('<div class="prep-plan"><span class="prep-eyebrow">VISÃO DA ROTINA</span><h3>Um plano para evoluir.</h3><p>Metas diárias do aluno</p>'+body+f'<div class="prep-plan-note">{len(weekdays)} dias de treino por semana</div></div>')

STYLE='''
.stApp:has(.prep-shell){background:#0c0f12}.stApp:has(.prep-shell) .stMainBlockContainer{max-width:1360px;padding:2.6rem 2.7rem 3rem}
.prep-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:2px 0 16px}.prep-eyebrow{font:700 10px/1.4 "Segoe UI",sans-serif;letter-spacing:2px;color:#d7b67a}.prep-hero h2{font-size:33px!important;font-weight:700!important;letter-spacing:-1.3px!important;margin:10px 0 6px!important;padding:0!important}.prep-hero p{color:#939fa8;font-size:14px;margin:0}.prep-hero-mark{display:grid;place-items:center;width:60px;height:60px;border-radius:18px;border:1px solid #38413b;color:#bfe0cf;background:linear-gradient(145deg,#23372e,#17231e)}.prep-hero-mark img{width:30px;height:30px}
.stApp:has(.prep-shell) [role=tablist]{gap:6px;background:#141a1f;border:1px solid #29333a;padding:6px;border-radius:15px;margin:4px 0 24px;overflow-x:auto;scrollbar-width:thin}.stApp:has(.prep-shell) [role=tab]{border-radius:10px!important;padding:11px 15px!important;color:#9ba7b0;white-space:nowrap;height:auto;min-height:42px}.stApp:has(.prep-shell) [role=tab][aria-selected=true]{background:#263a31;color:#d7f0df;box-shadow:inset 0 0 0 1px #3b5748}.stApp:has(.prep-shell) [data-baseweb=tab-highlight],.stApp:has(.prep-shell) [data-baseweb=tab-border]{display:none}
.stApp:has(.prep-shell) [data-testid=stVerticalBlockBorderWrapper]{border-color:#29343c!important;border-radius:18px!important}.stApp:has(.prep-shell) [data-testid=stForm],.stApp:has(.prep-shell) details{border-radius:16px!important;background:#141b20!important}.stApp:has(.prep-shell) [data-testid=stMetric]{background:linear-gradient(140deg,#182229,#12191f)!important;border:1px solid #2b3942!important;border-radius:16px;padding:18px!important}.stApp:has(.prep-shell) [data-testid=stMetricLabel] p{font-size:12px;color:#a2b0ba}.stApp:has(.prep-shell) [data-testid=stMetricValue]{font-size:29px;letter-spacing:-1px}
.stApp:has(.prep-shell) [data-baseweb=select]>div,.stApp:has(.prep-shell) [data-baseweb=input]{background:#10171c!important;border-color:#303e47!important;border-radius:11px!important}.stApp:has(.prep-shell) [data-baseweb=tag]{background:#294337!important;color:#d4eddb!important;border-radius:8px}.stApp:has(.prep-shell) button[kind=primary]{background:#cfaa68!important;border-color:#cfaa68!important;color:#101711!important;border-radius:12px!important}.stApp:has(.prep-shell) button[kind=primary] p{color:#101711!important;font-weight:700;background:transparent!important}.stApp:has(.prep-shell) button[kind=secondary]{border-color:#34434d;border-radius:11px;background:#192229}.stApp:has(.prep-shell) [data-testid=stCaptionContainer] p{font-size:12px}
.prep-profile{display:flex;align-items:center;gap:12px;padding:14px 18px;border:1px solid #2b373f;border-radius:15px;background:#131c22;margin:0 0 10px}.prep-avatar{width:40px;height:40px;border-radius:13px;background:#2b4237;color:#d1e8d8;display:grid;place-items:center;font-weight:700}.prep-profile strong{display:block;font-size:14px}.prep-profile small{display:block;font-size:11px;color:#90a29f;margin-top:3px}.prep-profile-tag{margin-left:auto;border:1px solid #3f5246;border-radius:20px;padding:5px 10px;color:#bdd2bf;font-size:11px}
.prep-section{display:flex;gap:12px;align-items:center;margin:4px 0 18px}.prep-section>span{width:31px;height:31px;display:grid;place-items:center;background:#24362e;color:#cae1ce;border:1px solid #3b5042;border-radius:10px;font-size:11px;font-weight:700}.prep-section h3{font-size:18px!important;font-weight:650!important;margin:0!important;padding:0!important}.prep-section p{font-size:12px;color:#8d9ca6;margin:4px 0 0}.st-key-routine_editor{background:#141c22!important;padding:22px!important}
.prep-plan{background:radial-gradient(ellipse at top right,#2a3d2e,#15201e 60%);border:1px solid #3a4d3d;border-radius:20px;padding:25px;position:sticky;top:85px}.prep-plan h3{font-size:25px!important;line-height:1.2!important;font-weight:650!important;margin:13px 0 8px;padding:0}.prep-plan>p{color:#a0b3a6;font-size:12px}.prep-plan-stat{display:flex;align-items:center;gap:12px;border-bottom:1px solid #34453b;padding:15px 0}.prep-plan-stat>span{width:38px;height:38px;background:#2a3c30;border:1px solid #405441;border-radius:12px;display:grid;place-items:center;color:#c4d6b2}.prep-plan-stat img{width:20px;height:20px}.prep-plan-stat strong{font-size:21px;display:block;color:#eff4e8}.prep-plan-stat small{color:#9eb09d;font-size:12px;display:block}.prep-plan-note{color:#c5d1bd;font-size:12px;padding-top:20px}
.prep-empty{border:1px dashed #36434d;border-radius:18px;background:radial-gradient(ellipse at top,#1c2a2c,#141b21 75%);padding:30px 20px;text-align:center;margin:8px 0 18px}.prep-empty-icon{height:50px;width:50px;display:grid;place-items:center;margin:0 auto 15px;border:1px solid #3a4c44;border-radius:16px;background:#24372f;color:#b6d6c1}.prep-empty-icon img{width:25px;height:25px}.prep-empty h4{font-size:17px!important;font-weight:600!important;margin:0 0 7px;padding:0}.prep-empty p{font-size:12px;color:#8fa2ad;max-width:420px;margin:auto;line-height:1.6}.st-key-prep_chat_room{max-width:940px;margin:auto}.prep-live-cover{display:flex;align-items:center;justify-content:space-between;gap:24px;background:radial-gradient(ellipse at right,#283f34,#151f24 65%);border:1px solid #354d40;border-radius:20px;padding:26px}.prep-live-cover h3{font-size:25px!important;font-weight:650!important;margin:10px 0!important;padding:0}.prep-live-cover p{font-size:13px;color:#9eb3aa;max-width:430px;margin:0}.prep-live-cover>span{display:grid;place-items:center;border:1px solid #466449;border-radius:24px;width:92px;height:92px;background:#283f32;color:#bbd7c0;flex:none}.prep-live-cover>span img{width:43px;height:43px}.prep-video-cover{height:100px;display:grid;place-items:center;border-radius:12px;background:radial-gradient(ellipse at center,#2e4439,#1a252c);color:#c7dccc;margin-bottom:12px}.prep-video-cover img{width:35px;height:35px}
.st-key-prep_live_controls{background:linear-gradient(120deg,#172621,#141c24)!important;padding:16px!important}.st-key-prep_live_controls .prep-live-cover{border:0;background:none;padding:8px}.st-key-prep_chat_room [data-testid=stChatInput]{border:1px solid #334a41;border-radius:16px;background:#17231e}.st-key-prep_warning_card{padding:18px}.stApp:has(.prep-shell) [data-testid=stHeadingWithActionElements]>a{display:none}
.stApp:has(.prep-shell) .prep-hero p,.stApp:has(.prep-shell) .prep-section p,.stApp:has(.prep-shell) .prep-empty p,.stApp:has(.prep-shell) .prep-live-cover p{color:#97a9b3!important}.stApp:has(.prep-shell) .prep-plan>p{color:#a0b3a6!important}.stApp:has(.prep-shell) .prep-profile small{color:#9bacb0!important}.st-key-routine_editor button[aria-checked=true],.st-key-routine_editor button[aria-pressed=true]{background:#2b4637!important;border-color:#4a6852!important;color:#d7edd9!important}
.stApp:has(.prep-shell) [data-testid=stSegmentedControl] [aria-checked=true]{background:#294336!important;color:#d9eddd!important;border-color:#4d6b54!important}
@media(max-width:700px){.prep-profile{display:none}.prep-hero p{display:none}.prep-hero{padding-bottom:6px}.stApp:has(.prep-shell) .stMainBlockContainer{padding:2.5rem 14px 2rem!important}.prep-hero{padding-bottom:18px;gap:12px}.prep-hero h2{font-size:28px!important}.prep-hero p{font-size:12px}.prep-hero-mark{width:48px;height:48px;border-radius:14px}.prep-hero-mark img{width:24px;height:24px}.stApp:has(.prep-shell) [role=tablist]{padding:5px;margin-bottom:18px}.stApp:has(.prep-shell) [role=tab]{font-size:12px;padding:9px 11px!important;min-height:38px}.prep-profile{padding:11px 12px}.prep-profile-tag{font-size:10px}.prep-plan{padding:18px;position:static}.prep-plan-stat{padding:10px 0}.prep-plan h3{font-size:22px!important}.prep-empty{padding:24px 16px}.st-key-routine_editor{padding:16px!important}.prep-live-cover{padding:20px}.prep-live-cover h3{font-size:21px!important}.prep-live-cover>span{width:60px;height:60px;border-radius:18px}.prep-live-cover>span img{width:30px;height:30px}.stApp:has(.prep-shell) [data-testid=stMetric]{padding:13px!important}}
'''
