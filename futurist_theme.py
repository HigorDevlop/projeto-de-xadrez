"""Shared HUD skin for native screens; board colors remain user configurable."""
CSS='''
:root{--club-panel:linear-gradient(140deg,#073149,#031327);--club-relief:inset 0 1px #2deafa12,0 7px 22px #0003;--club-display:Bahnschrift,'Segoe UI',sans-serif;--club-ui:'Segoe UI',system-ui,sans-serif}
body .stApp.stApp{background:repeating-linear-gradient(0deg,#0088c405 0 1px,transparent 1px 4px),radial-gradient(ellipse at 12% 0,#06496955,transparent 55%),#020d20!important;color:#d9f5ff}
body [data-testid=stHeader]{background:#020d20ed!important;border-bottom:1px solid #14516b!important}
body .stApp.stApp [data-testid=stSidebar]{background:linear-gradient(160deg,#06213a,#020d20 75%)!important;border-right:1px solid #16718b!important}
body .stApp.stApp h1,body .stApp.stApp h2,body .stApp.stApp h3{font-family:Bahnschrift,'Segoe UI',sans-serif!important;color:#d9faff!important;letter-spacing:.02em}
body .stApp.stApp h3{color:#55e7f0!important}
body .stApp.stApp .section-overline,body .stApp.stApp .prep-eyebrow{color:#ff9b4e!important;font-family:Consolas,monospace!important;letter-spacing:2px}
body .stApp.stApp .st-key-page_heading{border-bottom:1px solid #145871;position:relative;padding-bottom:20px}
body .stApp.stApp .st-key-page_heading:after{content:'';position:absolute;bottom:-1px;left:0;width:105px;border-bottom:2px solid #ff8737}
body .stApp.stApp [data-testid=stForm],body .stApp.stApp [data-testid=stExpander] details,body .stApp.stApp [data-testid=stVerticalBlockBorderWrapper],body .stApp.stApp [data-testid=stMetric]{background:linear-gradient(135deg,#07253dcc,#031227ed)!important;border:1px solid #17617b!important;border-radius:4px!important;box-shadow:inset 0 1px #38ecff0c,0 8px 24px #0002!important}
body .stApp.stApp [data-testid=stMetric]{padding:16px!important;border-top:2px solid #16cfe4!important}
body .stApp.stApp [data-testid=stMetricValue]{font-family:Consolas,monospace!important;color:#a6f7ff!important}
body .stApp.stApp [data-testid=stExpander] summary{background:#07263b!important;color:#71e4ef!important;border-radius:3px!important}
body .stApp.stApp [data-baseweb=input],body .stApp.stApp [data-baseweb=base-input],body .stApp.stApp [data-baseweb=select]>div,body .stApp.stApp textarea,body .stApp.stApp input,body .stApp.stApp [data-testid=stCode],body .stApp.stApp [data-testid=stFileUploaderDropzone]{background:#04192d!important;border-color:#186680!important;border-radius:3px!important;color:#ddf8ff!important;-webkit-text-fill-color:#ddf8ff!important}
body .stApp.stApp [data-testid=stCode] pre{background:transparent!important}
body .stApp.stApp input::placeholder,body .stApp.stApp textarea::placeholder{color:#7fa4b9!important;-webkit-text-fill-color:#7fa4b9!important}
body .stApp.stApp button[kind],body .stApp.stApp a[data-testid=stBaseLinkButton-secondary]{border:1px solid #16738c!important;border-radius:3px!important;background:linear-gradient(110deg,#08334c,#041b30)!important;color:#a6f3fc!important;box-shadow:inset 0 1px #8bfaff14!important}
body .stApp.stApp button[kind] p{background:transparent!important;color:inherit!important}
body .stApp.stApp button[kind^=primary]{background:linear-gradient(110deg,#0ec4d9,#0b809c)!important;border-color:#32ddeb!important;color:#001421!important}
body .stApp.stApp button[kind]:hover{border-color:#55e7f0!important;box-shadow:0 0 12px #00d9f41c!important}
body .stApp.stApp button:focus-visible,body .stApp.stApp input:focus-visible{outline:2px solid #ff9b4e!important;outline-offset:2px!important}
body .stApp.stApp [role=tablist]{background:#041b30!important;border:1px solid #155871!important;border-radius:4px!important;padding:6px;gap:5px}
body .stApp.stApp [role=tab]{border-radius:2px!important;color:#91b7cc!important}
body .stApp.stApp [role=tab][aria-selected=true]{background:#084057!important;color:#c9fcff!important;box-shadow:inset 0 -2px #ff8737!important}
body .stApp.stApp [role=radio]{background:#062038!important;border-color:#186680!important;border-radius:3px!important}
body .stApp.stApp [role=radio][aria-checked=true]{background:#08465c!important;border-color:#ff8737!important;color:#dcfcff!important}
body .stApp.stApp [data-testid=stSidebar] [data-testid=stPageLink] a{border:1px solid #10445c!important;border-radius:3px!important;background:#04192d!important;box-shadow:none!important;color:#9ec3d5!important;transform:none!important}
body .stApp.stApp [data-testid=stSidebar] a[aria-current=page]{background:linear-gradient(90deg,#094960,#06263b)!important;border-color:#1c9bb0!important;color:#b6fbff!important;box-shadow:inset 3px 0 #ff8737!important}
body .stApp.stApp [data-testid=stAlert]{background:#05283c!important;border-color:#18758c!important;border-radius:4px!important}
body .stApp.stApp [data-testid=stCaptionContainer] p{color:#90b2c8!important}
body [role=dialog]{background:linear-gradient(145deg,#06273d,#020f24)!important;border:1px solid #16859e!important;border-radius:5px!important}
body .stApp.stApp .prep-plan,body .stApp.stApp .prep-empty,body .stApp.stApp .roster-overview,body .stApp.stApp .prep-hero-mark,body .stApp.stApp .roster-avatar,body .stApp.stApp .st-key-classroom_join_panel{background:linear-gradient(130deg,#073149,#04172c)!important;border:1px solid #18748e!important;border-radius:4px!important;color:#9ac9d8!important}
body .stApp.stApp [class*=st-key-prep_student_card],body .stApp.stApp .st-key-analysis_toolbar,body .stApp.stApp .st-key-analysis_source{background:linear-gradient(130deg,#073149,#04172c)!important;border-color:#18748e!important;border-radius:4px!important}
body .stApp.stApp .club-brand{padding-bottom:15px;border-bottom:1px solid #14516b}
body .stApp.stApp .club-brand strong{color:#d5fbff!important;font-family:Bahnschrift,sans-serif!important;letter-spacing:.04em}
body .stApp.stApp .club-brand small{color:#ff9b4e!important}
@media(prefers-reduced-motion:reduce){body .stApp.stApp *{scroll-behavior:auto!important}}

body .stApp.stApp .opening-progress-card,body .stApp.stApp .opening-progress-medal,body .stApp.stApp .prep-plan-note{background:linear-gradient(130deg,#073149,#04172c)!important;border-color:#18748e!important;border-radius:4px!important}.opening-progress-track i{background:linear-gradient(90deg,#0b809c,#16d9e5)!important}body .stApp.stApp .opening-progress-heading small{color:#ff9b4e!important}

body .stApp.stApp :is(.st-key-sidebar_account_card,.st-key-study_library,.st-key-study_reading_panel,.st-key-study_position,.reference-rank,.reference-profile-card,.quality-accuracy,.prep-profile){border-color:#17617b!important;border-radius:4px!important}
body .stApp.stApp .st-key-analysis_progress_overlay{background:linear-gradient(135deg,#073149,#031327)!important;border-color:#168ba3!important;border-radius:5px!important}
'''
