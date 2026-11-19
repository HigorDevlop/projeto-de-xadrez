"""Scoped classroom styling, including overrides for the global neon theme."""

STYLE = '''
body .stApp.stApp:has(.prep-shell){background:radial-gradient(ellipse at 10% 0%,#12314a66,transparent 55%),#080f1d!important}
body .stApp.stApp:has(.prep-shell) .prep-hero{padding:12px 0 24px}
body .stApp.stApp:has(.prep-shell) .prep-hero h2{font-family:'Segoe UI',sans-serif!important;font-size:36px!important;letter-spacing:-1.2px!important;color:#f0f5ff!important}
body .stApp.stApp:has(.prep-shell) .prep-eyebrow{color:#77dcca!important}
body .stApp.stApp:has(.prep-shell) .prep-hero-mark{background:#122c3a!important;border-color:#2a5060!important;border-radius:20px!important;width:64px;height:64px;transform:rotate(-5deg)}
body .stApp.stApp:has(.prep-shell) .prep-profile{background:linear-gradient(100deg,#152b3b,#101c2e)!important;border:1px solid #294356!important;border-radius:16px!important;padding:16px 20px}
body .stApp.stApp:has(.prep-shell) .prep-profile-tag{color:#a8c9d6;background:#102333;border-color:#304c5e}
body .stApp.stApp:has(.prep-shell) [role=tablist]{background:#101b2c!important;border:1px solid #26374d!important;border-radius:16px!important;padding:7px;gap:4px}
body .stApp.stApp:has(.prep-shell) [role=tab]{border-radius:10px!important;padding:12px 16px!important}
body .stApp.stApp:has(.prep-shell) [role=tab][aria-selected=true]{background:#204153!important;color:#e6fffa!important;box-shadow:inset 0 0 0 1px #3b6974!important}
body .stApp.stApp:has(.prep-shell) .prep-section h3{color:#e6edf8!important;font-family:'Segoe UI',sans-serif!important;letter-spacing:-.3px}
.roster-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:0 0 8px}
.roster-stat{position:relative;overflow:hidden;display:flex;flex-direction:column;gap:9px;padding:21px 23px;border:1px solid #293d53;border-radius:18px;background:linear-gradient(135deg,#172a3d,#111c2d)}
.roster-stat:after{content:'';position:absolute;width:70px;height:70px;border:15px solid #70d9cd09;border-radius:50%;right:-20px;bottom:-25px}
.roster-stat>span{font-size:12px;color:#b1c2d5;font-weight:600}.roster-stat>strong{font:650 33px/1.1 'Segoe UI',sans-serif;letter-spacing:-1px;color:#e9f2ff}.roster-stat>small{font-size:11px;color:#92a7bc}
.roster-stat.linked>strong{color:#83dfc1}.roster-stat.waiting>strong{color:#f1ce8c}.roster-stat.revoked>strong{color:#eda9b3}
body .stApp.stApp:has(.prep-shell) .st-key-roster_tools [data-baseweb=input],body .stApp.stApp:has(.prep-shell) .st-key-roster_tools [data-baseweb=select]>div{background:#111f31!important;border-color:#30465e!important;border-radius:12px!important;min-height:46px}
body .stApp.stApp:has(.prep-shell) .st-key-roster_tools input{background:transparent!important}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_]{background:radial-gradient(ellipse at top left,#1d3546,#121e30 80%)!important;border:1px solid #30465a!important;border-radius:20px!important;padding:23px!important;box-shadow:0 10px 25px #0002!important;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_]:hover{transform:translateY(-3px);border-color:#578c9a!important;box-shadow:0 14px 30px #0004!important}
body .stApp.stApp:has(.prep-shell) .roster-avatar{background:linear-gradient(145deg,#31566b,#203b4b)!important;border:1px solid #497284!important;border-radius:16px!important;color:#b7f4e5!important;width:50px;height:50px}
.roster-card-top{margin:0 0 2px}.roster-seat{color:#a2b7cb}.roster-status{padding:4px 8px;border-radius:20px;background:#ffffff06}.roster-status.waiting{color:#e1c68d}.roster-status.linked{color:#8fdfc2}.roster-status.revoked{color:#f4aab7}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-prep_student_open_] button{background:transparent!important;border:0!important;box-shadow:none!important;padding:0!important;justify-content:flex-start!important}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-prep_student_open_] button p{color:#eef5ff!important;font:650 23px/1.4 'Segoe UI',sans-serif!important}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_] button[kind]{border-radius:11px!important}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-roster_record_] button{background:#285466!important;border-color:#457d87!important;color:#e4fff7!important}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-roster_training_] button{background:#192c40!important;border-color:#39516b!important;color:#c7d9ed!important}
body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_] [data-testid=stExpander] details,body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_] [data-testid=stExpander] summary{background:#101c2c!important;border-color:#2d4057!important;border-radius:11px!important}
.roster-card-footer{color:#a8bacd;border-color:#ffffff0e;padding:10px 0;margin-top:0}.roster-warning-dots{display:flex;gap:5px;align-items:center}.roster-warning-dots i{width:7px;height:7px;border-radius:50%;background:#34475d}.roster-warning-dots i.filled{background:#f0b776}
@media(max-width:700px){.roster-stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.roster-stat{padding:15px}.roster-stat>strong{font-size:28px}.roster-stat>small{font-size:10px}body .stApp.stApp:has(.prep-shell) .prep-hero h2{font-size:29px!important}body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_]{padding:18px!important}body .stApp.stApp:has(.prep-shell) [role=tab]{padding:10px 12px!important}}
@media(prefers-reduced-motion:reduce){body .stApp.stApp:has(.prep-shell) div[class*=st-key-seat_]{transition:none;transform:none}}
'''
