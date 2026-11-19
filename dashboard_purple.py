"""Purple analytics layout inspired by the supplied dashboard reference."""
from base64 import b64encode
from html import escape
from math import pi

COLORS=('#11e5ff','#69ff24','#fff500','#ff745f','#ff27c3')


def _image(svg,label,classes=''):
    return '<img class="purple-ring '+classes+'" alt="'+escape(label)+'" src="data:image/svg+xml;base64,'+b64encode(svg.encode()).decode()+'"/>'


def ring(value,label,colors=COLORS,multi=None):
    arcs=[]
    values=multi if multi is not None else [value]*len(colors)
    for index,(amount,color) in enumerate(zip(values,colors)):
        radius=90-index*9;length=2*pi*radius
        arcs.append(f'<circle cx="110" cy="110" r="{radius}" fill="none" stroke="#ffffff15" stroke-width="6"/>')
        if amount is not None:
            arcs.append(f'<circle cx="110" cy="110" r="{radius}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-dasharray="{length*max(0,min(100,amount))/100:.3f} {length:.3f}" transform="rotate(-180 110 110)"/>')
    text='—' if value is None else f'{value:.0f}%'
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">'+''.join(arcs)+f'<text x="110" y="120" text-anchor="middle" fill="white" font-family="Bahnschrift,Arial,sans-serif" font-weight="600" font-size="32">{text}</text></svg>'
    return _image(svg,label+': '+text)


def console(data,diagnostics,counts,analyzed,status):
    total=data['total'];wins=100*data['totals'].get('wins',0)/max(1,total)
    coverage=100*analyzed/max(1,total);classified=sum(counts.values())
    solid=100*sum(counts[key] for key in ('brilliant','best','excellent','good'))/classified if classified else None
    days=list(dict.fromkeys(row['Dia'] for row in data['daily']))
    phase_coverage=100*diagnostics['analyzed']/max(1,diagnostics['total'])
    active=sum(any(row['Dia']==day and row['Partidas'] for row in data['daily']) for day in days)
    legend=''.join(f'<span><i style="background:{color}"></i>{label}<b>{value}</b></span>' for color,label,value in zip(COLORS,('Análises concluídas','Vitórias','Lances sólidos','Dias ativos','Diagnóstico'),(f'{coverage:.0f}%',f'{wins:.0f}%',f'{solid:.0f}%' if solid is not None else '—',str(active),f'{phase_coverage:.0f}%')))
    phases={row['phase']:row for row in diagnostics['phases']}
    mini=[]
    for index,row in enumerate(data['sides']):
        mini.append('<div>'+ring(row['Vitória (%)'] if row['Partidas'] else None,row['Cor'],(COLORS[index],COLORS[index+2]))+'<small>Vitórias · '+row['Cor']+'</small></div>')
    for name,color in [('Abertura',COLORS[1]),('Final',COLORS[2])]:
        row=phases[name];mini.append('<div>'+ring(row['rate'] if row['moves'] else None,name,(color,COLORS[4]))+'<small>Erros · '+name.lower()+'</small></div>')
    bars=[];peak=max((sum(row['Partidas'] for row in data['daily'] if row['Dia']==day) for day in days),default=1)
    for day in days[-7:]:
        pieces='';n=0
        for result,color in zip(('Vitórias','Derrotas','Empates'),(COLORS[0],COLORS[4],COLORS[2])):
            count=sum(row['Partidas'] for row in data['daily'] if row['Dia']==day and row['Resultado']==result);n+=count
            if count:pieces+=f'<i style="width:{100*count/max(1,peak):.4f}%;background:{color}"></i>'
        bars.append('<div class="purple-day"><small>'+day+'</small><div>'+pieces+'</div><b>'+str(n)+'</b></div>')
    state='Analisando partidas' if status.get('current') or status.get('queued') else 'Análises atualizadas' if analyzed==total else 'Análise parcial'
    return '<div class="hud-console"><div class="purple-telemetry"><span>'+str(total)+' partidas</span><span>'+str(data['moves'])+' lances seus</span><span>'+str(active)+' dias ativos</span><span class="purple-sync">'+state+'</span></div><div class="dash-kpis"><div class="hud-main-gauge"><h4>Cobertura da análise</h4>'+ring(coverage,'Cobertura',multi=[coverage,wins,solid,100*active/max(1,len(days)),phase_coverage])+'<small>'+str(analyzed)+' de '+str(total)+' partidas</small></div><div><h4>Taxa de vitória</h4>'+ring(wins,'Taxa de vitória',('#69ff24','#ff27c3'))+'<div class="purple-legend">'+legend+'</div></div><div><h4>Seu jogo em números</h4><div class="purple-mini">'+''.join(mini)+'</div></div><div><h4>Partidas por dia</h4><div class="purple-bars">'+''.join(bars)+'</div><small>Ciano: vitórias · Rosa: derrotas · Amarelo: empates</small></div></div></div>'


CSS='''<style>
body .stApp.stApp:has(.st-key-performance_dashboard){background:radial-gradient(ellipse at 0 0,#3b276d,transparent 70%),#251448!important}
body .stApp.stApp:has(.st-key-performance_dashboard) [data-testid=stSidebar]{background:linear-gradient(180deg,#210835,#170429)!important;border-color:#61218c!important}
body .stApp.stApp:has(.st-key-performance_dashboard) [data-testid=stHeader]{background:#20092e!important;border-color:#67218e!important}
body .stApp.stApp:has(.st-key-performance_dashboard) [data-testid=stSidebar] a,body .stApp.stApp:has(.st-key-performance_dashboard) [data-testid=stSidebar] button{background:#2a0d45!important;border-color:#71339a!important}
body .stApp.stApp:has(.st-key-performance_dashboard) [data-testid=stSidebar] a[aria-current=page]{background:#6932a1!important;box-shadow:inset 3px 0 #0fe5ff!important}
body .stApp.stApp .st-key-performance_dashboard{background:linear-gradient(165deg,#55088b,#4c067c 65%,#3a086b)!important;border:1px solid #7131a8!important;border-radius:2px!important;padding:24px 28px!important;box-shadow:0 18px 45px #13062266!important;position:relative}
.st-key-performance_dashboard:before{display:none!important}
body .stApp.stApp .st-key-performance_dashboard h1{font:600 28px/1.2 'Segoe UI',sans-serif!important;letter-spacing:0!important;color:white!important}
body .stApp.stApp .st-key-performance_dashboard h3{font:500 16px/1.4 'Segoe UI',sans-serif!important;color:white!important;letter-spacing:0!important}
body .stApp.stApp .st-key-performance_dashboard [class*=st-key-dash_card]{background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important;padding:12px 0!important}
.st-key-performance_dashboard [class*=st-key-dash_card]:before{display:none!important}
body .stApp.stApp .st-key-performance_dashboard .dash-eyebrow,body .stApp.stApp .st-key-performance_dashboard .diag-eyebrow{font:10px/1.4 'Segoe UI',sans-serif!important;color:#e6aaff!important;letter-spacing:1.5px!important}
body .stApp.stApp .st-key-performance_dashboard [data-testid=stCaptionContainer] p{color:#e3c3f1!important}
.hud-console{margin:0 0 14px;padding:0;border:0;display:block}
.purple-telemetry{display:flex;align-items:center;flex-wrap:wrap;gap:25px;border-top:1px solid #c970f04a;padding:14px 0;color:#edc9fa;font:11px/1.5 'Segoe UI',sans-serif}.purple-sync{margin-left:auto;color:#68f8f4}
.st-key-performance_dashboard .dash-kpis{display:grid;grid-template-columns:1fr 1fr 1.1fr 1.45fr;gap:28px;margin:8px 0 12px}
.st-key-performance_dashboard .dash-kpis>div{border:0!important;background:transparent!important;padding:0!important;box-shadow:none!important;overflow:visible!important;min-width:0;text-align:center}.dash-kpis>div:before{display:none!important}.dash-kpis h4{font:500 16px/1.5 'Segoe UI',sans-serif;color:white;text-align:left;margin:0 0 12px}.purple-ring{display:block;width:175px;max-width:100%;aspect-ratio:1;margin:0 auto}.dash-kpis small{font:10px/1.5 'Segoe UI',sans-serif!important;color:#ead3f8!important}.purple-legend{display:grid;gap:5px;text-align:left;margin:6px auto;max-width:240px;font:10px/1.5 'Segoe UI',sans-serif;color:#efdafa}.purple-legend span{display:flex;align-items:center;gap:6px}.purple-legend i{width:5px;height:5px;border-radius:50%;flex:none}.purple-legend b{margin-left:auto;font-weight:500}.purple-mini{display:grid;grid-template-columns:1fr 1fr;gap:4px}.purple-mini .purple-ring{width:92px}.purple-mini small{display:block;margin-top:-4px;white-space:nowrap}.purple-bars{display:grid;gap:10px;margin:24px 0 18px}.purple-day{display:grid;grid-template-columns:34px 1fr 18px;gap:8px;align-items:center}.purple-day>div{display:flex;background:#2b0348;min-height:11px}.purple-day i{display:block;height:11px}.purple-day small{font-size:9px!important}.purple-day b{font:10px 'Segoe UI',sans-serif;color:#f4e6ff}
body .stApp.stApp .st-key-performance_dashboard [role=radio]{background:#3c0867!important;border-color:#ca84ef!important;color:#fff!important;border-radius:2px!important}body .stApp.stApp .st-key-performance_dashboard [role=radio][aria-checked=true]{background:#20ddd8!important;color:#280747!important;border-color:#51fff3!important}
body .stApp.stApp .st-key-performance_dashboard [data-baseweb=select]>div,body .stApp.stApp .st-key-performance_dashboard [role=combobox],body .stApp.stApp .st-key-performance_dashboard [data-testid=stExpander] details,body .stApp.stApp .st-key-performance_dashboard [data-testid=stExpander] summary{background:#3c0867!important;border-color:#9c4fcc!important;border-radius:2px!important;color:#faeaff!important}
body .stApp.stApp .st-key-performance_dashboard button[kind=primary]{background:linear-gradient(100deg,#e429d2,#8c2ee5)!important;border-color:#e98cfa!important;color:white!important}
.diag-insights{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0}.diag-insights>div{border:1px solid #aa55d84d!important;background:#41086c66!important;border-radius:2px!important;padding:16px!important}.diag-insights small{display:block;color:#d4a1ef!important;font:10px 'Segoe UI',sans-serif;letter-spacing:1px}.diag-insights strong{display:block;color:#f6ff3d!important;font:600 25px/1.8 'Segoe UI',sans-serif!important}.diag-insights span{color:#e8c9f6!important;font-size:12px}.hud-review{display:flex;gap:20px;align-items:center;flex-wrap:wrap;padding:16px 0;border-block:1px solid #bc64e844;margin:12px 0}.hud-review small{display:block;color:#dda9f7;font-size:10px}.hud-review strong{display:block;color:#ffff30;font-size:24px}.hud-review-phase{color:#e1b8f4;font-size:12px}.hud-best{margin-left:auto}.dash-rates{display:flex;justify-content:space-between;color:#e7c4f7;font-size:11px}.dash-rates strong{display:block;color:white;font-size:19px}.dash-side,.dash-details{display:flex;flex-wrap:wrap;gap:16px;color:#dfb7f5;font-size:11px}.dash-details{margin-top:16px}.dash-footer{margin-top:18px;color:#c78be8;font:10px/1.5 'Segoe UI',sans-serif;text-align:right}
@media(max-width:1000px){.st-key-performance_dashboard .dash-kpis{grid-template-columns:1fr 1fr;gap:22px}.purple-ring{width:160px}.purple-mini .purple-ring{width:94px}}
@media(max-width:600px){body .stApp.stApp .st-key-performance_dashboard{padding:16px!important}.st-key-performance_dashboard .dash-kpis{gap:20px 12px}.dash-kpis h4{font-size:13px}.purple-ring{width:130px}.purple-mini .purple-ring{width:65px}.purple-mini small{font-size:8px!important}.purple-telemetry{gap:10px;font-size:10px}.purple-sync{margin-left:0}.purple-bars{gap:8px;margin-top:12px}.purple-day{grid-template-columns:27px 1fr 13px;gap:4px}.purple-day small{font-size:8px!important}.diag-insights{grid-template-columns:1fr}.hud-best{margin-left:0}}
</style>'''
