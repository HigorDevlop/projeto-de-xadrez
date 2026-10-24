from html import escape
import streamlit as st
from opening_achievements import collection


def medal_svg(identifier):
    """Small local vector medals, with a distinct emblem for each milestone."""
    from hashlib import sha256
    number=int(sha256(identifier.encode()).hexdigest()[:4],16)
    colors=('#d5ad69','#8abcb1','#a5abd4','#d29f8e')
    color=colors[number%len(colors)]
    emblems=(
        '<path d="m32 19 4 8 9 1-7 6 2 9-8-4-8 4 2-9-7-6 9-1Z"/>',
        '<path d="m20 25 6 5 6-10 6 10 6-5-3 16H23Z"/><path d="M24 45h16" fill="none" stroke="currentColor" stroke-width="2"/>',
        '<path d="M22 23h9v20h-9l-3 2V25Zm11 0h9l3 2v20l-3-2h-9Z"/>',
        '<path d="m32 19 12 5v9c0 8-12 13-12 13s-12-5-12-13v-9Z"/><path d="m26 32 4 4 8-9" fill="none" stroke="#27332d" stroke-width="2.5"/>')
    emblem=emblems[number%len(emblems)]
    return ('<svg xmlns="http://www.w3.org/2000/svg" class="achievement-medal" width="54" height="64" viewBox="0 0 64 76" aria-hidden="true" style="color:'+color+'">'
            '<path d="m17 45-3 28 12-7 8 8 2-29M47 45l3 28-12-7-8 8-2-29" fill="currentColor" opacity=".55"/>'
            '<circle cx="32" cy="32" r="29" fill="#1c2520" stroke="currentColor" stroke-width="2"/>'
            '<circle cx="32" cy="32" r="24" fill="currentColor" opacity=".12"/>'
            '<circle cx="32" cy="32" r="21" fill="none" stroke="currentColor" stroke-dasharray="1 4" opacity=".6"/>'
            '<g fill="currentColor">'+emblem+'</g></svg>')


def medal_image(identifier):
    # st.html sanitizes inline SVG; use the same local image approach as course badges.
    from base64 import b64encode
    source=b64encode(medal_svg(identifier).encode()).decode()
    return '<img class="achievement-medal" width="54" height="64" alt="Medalha da conquista" src="data:image/svg+xml;base64,'+source+'">'


def render_unlocks(plan, titles):
    items={item['title']:item for item in collection(plan)}
    seen=st.session_state.setdefault('openings_achievement_animations',set())
    cards=[]
    for index,title in enumerate(titles):
        item=items.get(title,dict(id=title,description='Mais um marco no seu progresso.'))
        marker=(plan.get('created'),item['id'])
        animate=marker not in seen
        seen.add(marker)
        cards.append('<article class="achievement-unlock'+(' arrive' if animate else '')+'" style="--delay:'+str(index*.14)+'s">'
            '<div class="achievement-emblem">'+medal_image(item['id'])+'</div>'
            '<div><span>CONQUISTA DESBLOQUEADA</span><h4>'+escape(title)+'</h4><p>'+escape(item['description'])+'</p></div>'
            '<i class="achievement-spark" aria-hidden="true">✦</i></article>')
    st.html('''<style>
    .achievement-unlocks{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:12px;margin:12px 0 18px}
    .achievement-unlock{position:relative;display:flex;align-items:center;gap:17px;padding:18px 22px;border:1px solid #bfa57442;border-radius:16px;background:radial-gradient(ellipse at 0 0,#9a7c3421,transparent 65%),linear-gradient(130deg,#20271f,#131a15);box-shadow:inset 0 1px #ffffff09,0 8px 22px #0003;overflow:hidden;font-family:system-ui}
    .achievement-emblem{flex:0 0 54px;filter:drop-shadow(0 4px 9px #0005)}.achievement-medal{display:block;width:54px;height:64px}
    .achievement-unlock span{font:600 9px system-ui;letter-spacing:1.7px;color:#bda674}.achievement-unlock h4{font:600 17px/1.35 system-ui!important;color:#f0e5ca!important;letter-spacing:-.3px;margin:6px 0 4px!important;padding:0!important}.achievement-unlock p{font:11px/1.6 system-ui;color:#99a68f;margin:0}.achievement-spark{margin-left:auto;color:#c4aa74;font:21px Georgia;opacity:.65}
    .achievement-unlock.arrive{animation:achievement-reveal .45s ease-out both;animation-delay:var(--delay)}.arrive .achievement-medal{animation:medal-reveal .85s cubic-bezier(.2,.7,.3,1) both;animation-delay:var(--delay)}.arrive .achievement-spark{animation:medal-spark 1.2s ease-out both;animation-delay:var(--delay)}
    @keyframes achievement-reveal{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}@keyframes medal-reveal{0%{transform:scale(.55) rotate(-20deg);opacity:0}55%{transform:scale(1.1) rotate(6deg);opacity:1}100%{transform:scale(1) rotate(0)}}@keyframes medal-spark{0%{opacity:0;transform:scale(.3) rotate(-60deg)}60%{opacity:1;transform:scale(1.3) rotate(10deg)}100%{opacity:.65;transform:none}}
    @media(prefers-reduced-motion:reduce){.achievement-unlock.arrive,.arrive .achievement-medal,.arrive .achievement-spark{animation:none}}
    </style><section class="achievement-unlocks" role="status" aria-label="Conquistas desbloqueadas">'''+''.join(cards)+'</section>')


def render_achievements(plan):
    items=collection(plan)
    earned=sum(item['earned'] for item in items)
    with st.expander(f'Conquistas · {earned}/{len(items)}',icon=':material/emoji_events:'):
        st.caption('Conquistadas pelo seu progresso e salvas neste computador.')
        columns=st.columns(2)
        for index,item in enumerate(items):
            with columns[index%2],st.container(border=True):
                if item['earned']:st.html(medal_image(item['id']))
                st.markdown(('🏆 ' if item['earned'] else '◇ ')+item['title'])
                st.caption(item['description'])
                st.progress(item['progress']/item['target'])
                st.caption('Conquistada · '+item['day'] if item['earned'] else f"{item['progress']}/{item['target']}")
