"""Offline progress, bounded review rounds and earned achievements."""
from hashlib import sha256
import chess
from preparation_state import today

QUIZ_LIMITS = (5, 10, 20, 40, 50)
ACHIEVEMENTS = (
    ('first_line','Primeiro passo','Conclua sua primeira linha.', 'lines',1),
    ('foundations','Base sólida','Conclua quatro fundamentos de uma abertura.', 'foundations',4),
    ('depth_7','Além do início','Conclua uma linha de 7 lances.', 'depth',7),
    ('depth_9','Visão de jogo','Conclua uma linha de 9 lances.', 'depth',9),
    ('depth_11','Plano em ação','Conclua uma linha de 11 lances.', 'depth',11),
    ('depth_13','Repertório profundo','Conclua uma linha de 13 lances.', 'depth',13),
    ('quiz_5','Memória em treino','Conclua um quiz de 5 posições.', 'quiz',5),
    ('quiz_10','Memória firme','Conclua um quiz de 10 posições.', 'quiz',10),
    ('quiz_20','Memória afiada','Conclua um quiz de 20 posições.', 'quiz',20),
    ('quiz_40','Grande revisão','Conclua um quiz de 40 posições.', 'quiz',40),
    ('quiz_50','Memória de mestre','Conclua um quiz de 50 posições.', 'quiz',50),
)
ACHIEVEMENTS += tuple((f'phase_{number}',f'Guardião {number//5}',
    f'Conclua a fase {number} e seu desafio de 50 perguntas.','phases',number) for number in range(5,51,5))


def quiz_limit(level):
    return QUIZ_LIMITS[min(4,max(0,(level-5)//2))]


def position_key(line, ply):
    board=chess.Board()
    for move in line['moves'][:ply]: board.push_uci(move)
    return sha256((line['side']+' '+board.epd()).encode()).hexdigest()[:24]


def record_achievements(plan, session, line):
    states=session.get('quiz_states',{})
    if (session.get('achievements_recorded') or session.get('practice_intent')=='explore' or session.get('mode')!='quiz'
            or session.get('quiz_queue') or not states or any(value!='correct' for value in states.values())):
        return []
    stats=plan.setdefault('achievement_progress',{})
    progress=plan.get('practice_progress',{})
    from opening_training_state import lines_for
    lessons=lines_for(plan)
    stats['lines']=sum(bool(progress.get(key,{}).get('learned')) for key in lessons)
    foundations={}
    for item in lessons.values():
        if item.get('stage')=='foundation' and progress.get(item['id'],{}).get('learned'):
            course=item.get('course_id') or item['id'].rsplit('-',1)[0]
            foundations[course]=foundations.get(course,0)+1
    stats['foundations']=max(stats.get('foundations',0),max(foundations.values(),default=0))
    stats['depth']=max(stats.get('depth',0),line.get('lesson_moves',0))
    stats['quiz']=max(stats.get('quiz',0),len(states))
    seen=plan.setdefault('quiz_seen',{})
    for key in states:
        item=(session.get('quiz_bank') or {}).get(key,dict(line=line,ply=int(key)))
        position=position_key(item['line'],item['ply'])
        seen[position]=seen.get(position,0)+1
    earned=plan.setdefault('achievements',{})
    new=[]
    for identifier,title,description,metric,target in ACHIEVEMENTS:
        if stats.get(metric,0)>=target and identifier not in earned:
            earned[identifier]=dict(day=str(today()),title=title)
            new.append(title)
    session['new_achievements']=new
    session['achievements_recorded']=True
    return new


def collection(plan):
    plans=[plan] + list((plan or {}).get('practice_library',{}).values()) if plan else []
    earned,stats={},{}
    for saved in plans:
        earned.update(saved.get('achievements',{}))
        for key,value in saved.get('achievement_progress',{}).items(): stats[key]=max(stats.get(key,0),value)
    return [dict(id=identifier,title=title,description=description,earned=identifier in earned,
                 day=earned.get(identifier,{}).get('day'),progress=min(target,stats.get(metric,0)),target=target)
            for identifier,title,description,metric,target in ACHIEVEMENTS]
