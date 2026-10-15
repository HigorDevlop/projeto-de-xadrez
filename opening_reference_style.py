"""Shared visual language from the supplied mobile reference screens."""
from html import escape
from base64 import b64encode


def svg_image(svg, label=''):
    """Keep vector artwork intact in Streamlit's sanitized HTML elements."""
    source = b64encode(svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1).encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{source}" alt="{escape(label)}"/>'


def badge(color='#34bb7b', stars=1):
    star = '<path d="m50 31 7 14 16 2-12 11 3 16-14-8-14 8 3-16-12-11 16-2z" fill="#ffc62f" stroke="#ffdb66" stroke-width="2"/>' if stars else ''
    return f'<svg viewBox="0 0 100 112" aria-hidden="true"><path d="M50 5 91 17V80L50 106 9 80V17Z" fill="{color}" stroke="#ffd052" stroke-width="7"/><path d="M50 13 83 23V75L50 97 17 75V23Z" fill="none" stroke="#fff0ba" stroke-width="3"/>{star}</svg>'


FLAME = '''<svg viewBox="0 0 100 128" aria-hidden="true"><defs><linearGradient id="fire" x1="0" y1="1" x2=".8" y2="0"><stop stop-color="#9a36e3"/><stop offset=".5" stop-color="#e00029"/><stop offset="1" stop-color="#ff8500"/></linearGradient></defs><path d="M53 3C37-7 47 28 49 38S37 60 31 44C9 58 1 78 9 99c11 31 63 33 80 2C109 63 76 17 53 3Z" fill="url(#fire)"/></svg>'''
STAR = '<svg viewBox="0 0 100 100" aria-hidden="true"><path d="m50 8 13 27 30 4-22 21 5 31-26-14-26 14 5-31L7 39l30-4Z" fill="currentColor" stroke="currentColor" stroke-linejoin="round" stroke-width="4"/></svg>'

CSS = '''
.stApp:has(.opening-course-mode){background:#071219!important;--chess-background:#071219;--chess-ink:#f5f5f5;--chess-muted:#8b9297;--chess-surface:#242c32;--chess-border:#353e44;--chess-soft:#242c32;--chess-accent:#ff8000;--chess-accent-soft:#48280f;--chess-accent-ink:#fff}
.stApp:has(.opening-course-mode) [data-testid="stHeader"]{background:#071219!important}
.stApp:has(.opening-course-mode) [data-testid="stSidebar"],.stApp:has(.opening-course-mode) [data-testid="stSidebarCollapsedControl"],.stApp:has(.opening-course-mode) .st-key-page_heading,.stApp:has(.opening-course-mode) .st-key-workspace_identity,.stApp:has(.opening-course-mode) .st-key-navigation_back{display:none!important}
.stApp:has(.opening-course-mode) .stMainBlockContainer{max-width:1240px;padding:2rem 2.2rem 2rem}
.stApp:has(.opening-course-mode){font-family:"Segoe UI",sans-serif}.stApp:has(.opening-course-mode) h1,.stApp:has(.opening-course-mode) h2,.stApp:has(.opening-course-mode) h3,.stApp:has(.opening-course-mode) h4{font-family:'Segoe UI',sans-serif!important;color:#f5f5f5!important}
.stApp:has(.opening-course-mode) button{font-family:'Segoe UI',sans-serif!important}
.stApp:has(.opening-course-mode) button[kind="primary"]{background:linear-gradient(100deg,#cd4400,#ff8700)!important;color:white!important;border:0!important;border-radius:18px!important;min-height:56px;font-size:18px;font-weight:700}
.stApp:has(.opening-course-mode) button[kind="primary"] p{color:white!important;font-size:18px!important;font-weight:700!important}
.stApp:has(.opening-course-mode) [data-testid="stSegmentedControl"] button{background:#242c32;border-radius:16px;color:#8c9398}
.stApp:has(.opening-course-mode) [data-testid="stSegmentedControl"] button[aria-checked="true"]{background:#555d62;color:white}
.reference-title{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:68px;margin-bottom:14px;color:#f5f5f5}.reference-title h1{font-size:27px!important;font-weight:600;margin:0;padding:0;text-align:center;flex:1}.reference-title small{font-size:15px;color:#818a91;display:block;text-align:center}.reference-title .emblem{width:54px;flex:none}.reference-title .emblem img{width:100%;height:54px}
.reference-rank{border-radius:26px;background:#242c32;padding:24px 30px;margin:8px 0 22px}.reference-rank-labels{display:flex;justify-content:space-between;color:#adb3b6;font-size:16px}.reference-rank-labels strong{display:block;color:#f4f4f4;font-size:23px}.reference-rank-labels>div:last-child{opacity:.45;text-align:right}.reference-rank-path{display:flex;gap:14px;align-items:center;margin:20px 0 4px}.reference-rank-path .medal{width:72px;height:72px;padding:12px;border-radius:50%;background:#ff7900;flex:none}.reference-rank-path .future{background:#323b41;opacity:.5}.reference-rank-path .medal img{width:100%;height:100%}.reference-rank-path .path{height:4px;background:#3c454c;flex:1}.reference-rank-path .square{width:28px;height:28px;background:#343e44;border-radius:10px}.reference-rank-caption{color:#9ba3a9;font-size:12px;text-align:center;margin:12px 0 0}
.reference-banner{background:linear-gradient(108deg,#7926c5,#c90018 55%,#ff8700);padding:22px 28px;border-radius:23px;color:white;margin:10px 0 20px}.reference-banner small{font-size:17px;color:#ecc5e1!important}.reference-banner h3{font-size:25px!important;font-weight:700!important;padding:6px 0 0!important;margin:0!important}
.st-key-opening_course{max-width:1040px;margin:auto}.st-key-opening_lesson{max-width:1100px;margin:auto}.st-key-opening_lesson_toolbar{margin-bottom:8px}
.st-key-opening_lesson_board{width:min(100%,660px,calc(100dvh - 240px));margin:auto}.st-key-opening_lesson_board [data-testid="stVerticalBlock"]{gap:0!important}
.reference-meter{height:8px;background:#302016;overflow:hidden}.reference-meter>span{display:block;height:100%;background:linear-gradient(90deg,#d94c00,#ff8900)}
.reference-evaluation{font:18px 'Segoe UI',sans-serif;color:white;min-height:48px;display:flex;align-items:center;justify-content:space-between;padding:12px 16px}.reference-evaluation small{color:#9aa3a8;font-size:12px}
.reference-feedback{background:#242c32;color:white;text-align:center;padding:18px 12px;font-size:18px;font-weight:700;min-height:60px;display:flex;align-items:center;justify-content:center;margin:0}.reference-feedback.success{background:#419c16}.reference-feedback.error{color:#fff}.reference-feedback .red{background:#ff354f;border-radius:50%;margin-right:12px;padding:4px 9px}
.opening-marks{display:flex;justify-content:center;gap:12px;padding:26px 0}.opening-mark{display:block;width:32px;height:32px;border-radius:8px;background:#242c32;font-size:0!important;color:transparent}.opening-mark.correct{background:linear-gradient(#64ac23,#499a18)}.opening-mark.wrong{background:#c43c55}.opening-mark.unknown{background:#f07800}.opening-mark.pending{background:#242c32}
.reference-counters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:22px 12px 18px}.reference-counter{text-align:center;color:var(--tone)}.reference-counter small{color:var(--tone)!important;font-size:11px;display:block;text-transform:uppercase;font-weight:700;margin-bottom:8px}.reference-counter div{border-radius:14px;background:var(--fill);padding:16px 6px;font-size:22px;color:white;box-shadow:0 7px 0 color-mix(in srgb,var(--fill) 80%,#000)}.reference-counter i{font-style:normal;border-radius:50%;background:#f4f4f4;color:var(--fill);display:inline-grid;place-items:center;width:26px;height:26px;font-size:19px;font-weight:700;margin-right:6px}
.st-key-opening_lesson_side{padding:20px 0 12px;min-width:0}.reference-side-label{font-size:14px;color:#89939a;line-height:1.6;text-align:center;margin:4px 0 28px}.st-key-reference_hint button{background:#48280f!important;color:#bd5e08!important;border:0;border-radius:18px!important;min-height:56px}
.reference-celebration{position:relative;max-width:640px;margin:20px auto;text-align:center;color:#f5f5f5;overflow:hidden;padding:30px 20px}.reference-celebration h1{font:700 36px 'Segoe UI',sans-serif!important;margin:12px}.reference-celebration h2{font:600 29px 'Segoe UI',sans-serif!important}.reference-celebration p{font-size:19px;color:#b6bdc1;line-height:1.6}.reference-award{position:relative;width:260px;margin:36px auto 20px}.reference-award>img{width:100%}.reference-award .medal{position:absolute;inset:40px 65px 55px}.reference-award .medal img{width:100%;height:100%}.reference-award strong{position:absolute;bottom:14px;left:0;right:0;color:#37bc7e;font-size:23px}.reference-flame{width:150px;position:relative;margin:34px auto}.reference-flame img{width:100%}.reference-flame strong{position:absolute;bottom:-8px;left:0;right:0;font-size:58px;font-weight:800;color:#071219;-webkit-text-stroke:3px white}.reference-week{display:flex;justify-content:space-around;margin:28px 0 10px;color:#cf001e;font-weight:700}.reference-week span{padding:10px;border-radius:24px}.reference-week .done{color:white;background:linear-gradient(130deg,#a626bd,#ff8700)}.reference-confetti{position:absolute;inset:0;pointer-events:none}.reference-confetti i{position:absolute;width:9px;height:22px;background:var(--c);left:var(--x);top:var(--y);transform:rotate(var(--r));animation:confetti-fall 2.5s ease-out both}@keyframes confetti-fall{from{translate:0 -100px;opacity:0}30%{opacity:1}to{translate:0 20px}}
.reference-profile-card{background:#242c32;border-radius:24px;padding:26px;margin-bottom:22px}.reference-profile-card h3{font-size:23px!important;margin:0 0 22px}.reference-profile-card table{border-collapse:collapse;width:100%;border:0}.reference-profile-card td,.reference-profile-card th{border:0!important;border-bottom:2px dashed #364047!important;padding:14px 8px;text-align:left;color:white;font-size:15px}.reference-profile-card th{font-size:10px;font-weight:400;color:#848d94}.reference-profile-card .rate{color:#ff7b06}.reference-profile-card .plus{color:#56b162}.reference-profile-card .minus{color:#f34c45}.reference-profile-card .stat{display:flex;justify-content:space-between;border-bottom:2px dashed #364047;padding:16px 0;font-size:18px}.reference-profile-card .stat strong{color:#ff7b06}
.st-key-reference_footer{border-top:1px solid #333d44;margin-top:30px;padding-top:14px}.st-key-reference_footer button{border:0!important;background:transparent!important;color:#899198!important;min-height:60px}.st-key-reference_footer button p{font-size:15px!important}.st-key-reference_footer button[kind="primary"]{background:transparent!important;color:white!important}.st-key-reference_footer button[kind="primary"] p{font-size:15px!important}
.reference-profile-card>img{width:100%;height:auto}
.stApp:has(.opening-course-mode) [data-testid="stHeader"]{display:none!important}
.stApp:has(.opening-course-mode) button[kind="tertiary"]{background:transparent;border:0}
.stApp:has(.opening-course-mode) .st-key-opening_course [data-variant="segmented_control"]{border:0!important;border-bottom:3px solid transparent!important;border-radius:0!important;background:transparent!important;min-height:60px;color:#858d94!important}
.stApp:has(.opening-course-mode) .st-key-opening_course [data-variant="segmented_control"][aria-checked="true"]{border-bottom-color:white!important;color:white!important}
.stApp:has(.opening-course-mode) .st-key-opening_course [data-variant="segmented_control"] p{color:inherit!important;font-size:18px}
.st-key-reference_footer button>div{flex-direction:column;gap:7px}.st-key-reference_footer [data-testid="stIconMaterial"]{font-size:28px}
.stApp:has(.opening-course-mode) button[kind="primary"] p{background:transparent!important}
.st-key-reference_reward_streak,.st-key-reference_reward_award{width:100%;max-width:640px;margin:auto}
.stApp:has(.opening-course-mode) .st-key-reference_reward_streak button[kind="primary"]{background:linear-gradient(100deg,#8125bf,#ce001b,#ff8500)!important}
.stApp:has(.opening-course-mode) .st-key-reference_reward_award button[kind="primary"]{background:#34bb7b!important}
.reference-title .emblem{border:5px solid #27323a;border-radius:50%;padding:6px;width:65px;height:65px}.reference-title .emblem img{width:100%;height:100%}
.stApp:has(.opening-course-mode) .st-key-question_launcher{display:none!important}
.st-key-reference_footer button{display:flex;flex-direction:column;gap:8px;min-width:70px;padding:6px}
.st-key-reference_footer button:before{display:block;height:34px;font:34px/1 "Segoe UI Symbol",sans-serif;color:#858e95}
.st-key-reference_nav_Finais button:before{content:"♚"}
.st-key-reference_nav_Aberturas button:before{content:"♞";background:linear-gradient(20deg,#8b26d1,#e00029,#ff8500);background-clip:text;color:transparent}
.st-key-reference_nav_Partida button:before{content:"VS";font-size:28px;font-style:italic;font-weight:800}
.st-key-reference_nav_Tático button:before{content:"✚";font-size:34px;transform:rotate(35deg)}
@media(max-width:800px){.stApp:has(.opening-course-mode) .stMainBlockContainer{padding:2rem 14px 1rem}.reference-title h1{font-size:22px!important}.st-key-opening_lesson_columns [data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important;min-width:0!important}.st-key-opening_lesson_board{width:100%;max-width:660px}.st-key-opening_lesson_side{padding-top:0}.reference-rank{padding:20px}.reference-banner{padding:20px}.reference-banner h3{font-size:22px!important}.reference-profile-card{padding:18px}.reference-profile-card td{font-size:12px}.reference-counter div{font-size:20px}.reference-counter small{color:var(--tone)!important;font-size:10px}.opening-mark{width:28px;height:28px}}
@media(prefers-reduced-motion:reduce){.reference-confetti i{animation:none}}
'''


def title_html(title, subtitle='', medal=True):
    return ('<div class="reference-title"><div style="width:54px"></div><div style="flex:1">'
            f'<h1>{escape(title)}</h1><small>{escape(subtitle)}</small></div>'
            + ('<span class="emblem">' + svg_image(badge(), 'Medalha do curso') + '</span>' if medal else '<span style="width:54px"></span>') + '</div>')
