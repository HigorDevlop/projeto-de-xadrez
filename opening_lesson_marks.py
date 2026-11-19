"""Shared opening and classroom answer indicators."""
import streamlit as st
from opening_repetition import learner_plies


def lesson_marks(line,session):
    marks=session.get('quiz_states',{}) if session['mode']=='quiz' else session.get('display_marks',session.get('marks',{}))
    labels={'pending':'A fazer','wrong':'Erro','unknown':'Não sei','correct':'Certo'}
    plies=list(session['quiz_states']) if session.get('quiz_bank') and session['mode']=='quiz' else list(learner_plies(line))
    if session['mode']=='quiz':
        colors={'pending':('#42a7ef','#359feb','✦'),'wrong':('#c73d50','#b92236','×'),
                'unknown':('#f3ae20','#855900','?'),'correct':('#66bc24','#52c10c','✓')}
        cells=[]
        for key in labels:
            count=sum(marks.get(str(ply),'pending')==key for ply in plies)
            tone,fill,symbol=colors[key]
            if count==0: fill={'pending':'#255e89','wrong':'#641c2a','unknown':'#825800','correct':'#286415'}[key]
            cells.append(f'<div class="reference-counter {key}" style="--tone:{tone};--fill:{fill}"><small>{labels[key]}</small><div><i>{symbol}</i>{count}</div></div>')
        st.html('<div class="reference-counters" aria-label="A fazer, erro, não sei e certo">'+''.join(cells)+'</div>')
    else:
        cells=[]
        for number,ply in enumerate(plies,1):
            mark=marks.get(str(ply),'pending')
            # Older saved retries may still carry a red mark from the previous
            # pass. Only show feedback for attempts made in this pass.
            if mark=='wrong' and str(ply) not in session.get('marks',{}):
                mark='pending'
            cells.append(f'<span class="opening-mark {mark}" role="img" aria-label="Lance {number}: {labels[mark]}"></span>')
        st.html('<div class="opening-marks" role="group" aria-label="Acertos e erros da linha">'+''.join(cells)+'</div>')

