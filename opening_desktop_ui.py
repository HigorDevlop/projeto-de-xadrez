"""Render lesson context using only the actual, persisted training state."""
from html import escape

import chess
import streamlit as st


def lesson_panel(line, session, message):
    mode = session['mode']
    stages = [('learn', '01 · Aprender'), ('recall', '02 · Memorizar'), ('quiz', '03 · Revisar')]
    stage_html = ''.join(f'<span class="{"active" if key == mode else ""}">{label}</span>'
                         for key, label in stages)
    st.html('<div class="lesson-eyebrow">SEU TREINO</div><div class="lesson-stages">'
            + stage_html + '</div><p class="opening-coach" role="status" aria-live="polite">'
            + escape(message) + '</p>')
    descriptions = {
        'learn': 'Siga a seta no tabuleiro. As respostas do adversário e a passagem para a próxima etapa são automáticas.',
        'recall': 'Repita a linha de memória. Se precisar, peça uma dica. Os lances difíceis voltam ao treino.',
        'quiz': 'Resolva as posições fora de ordem para fixar o repertório. As posições com erro serão repetidas.',
    }
    st.html('<p class="lesson-note">' + descriptions[mode] + '</p>')
    marks = session.get('display_marks', session.get('marks', {}))
    plies = range(0 if line['side'] == 'white' else 1, len(line['moves']), 2)
    counts = {key: sum(marks.get(str(ply), 'pending') == key for ply in plies)
              for key in ('pending', 'wrong', 'unknown', 'correct')}
    labels = {'pending': 'A fazer', 'wrong': 'Erro', 'unknown': 'Com dica', 'correct': 'Certo'}
    st.html('<div class="lesson-counters" aria-label="Posições da etapa">' + ''.join(
        f'<div class="lesson-counter {key}"><b>{count}</b><small>{labels[key]}</small></div>'
        for key, count in counts.items()) + '</div>')


def move_history(session):
    board, rows = chess.Board(), []
    for ply, uci in enumerate(session['history']):
        move = chess.Move.from_uci(uci)
        san = board.san(move)
        if ply % 2 == 0:
            rows.append(f'{ply // 2 + 1}. {san}')
        else:
            rows[-1] += '  ' + san
        board.push(move)
    # In a quiz this is the current position's history, never an answer preview.
    content = '<ol>' + ''.join('<li>' + escape(row) + '</li>' for row in rows) + '</ol>' if rows else '<p>Os lances aparecerão aqui conforme você jogar.</p>'
    st.html('<section class="lesson-history"><h4>Lances da posição</h4>' + content + '</section>')
