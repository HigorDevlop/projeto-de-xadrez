"""Train every branch at the same depth before advancing the whole course."""
from opening_achievements import QUIZ_LIMITS

PHASE_LIMIT=50


def roots_for(plan):
    from opening_training_state import lines_for
    return sorted((line for line in lines_for(plan).values() if line.get('stage')=='foundation'),key=lambda line:line['branch'])


def phase_number(plan):
    state=cycle(plan)
    return min(PHASE_LIMIT+1,state['round']*len(roots_for(plan))+len(state['completed'])+1) if state else 0


def quiz_target(plan,session=None):
    level,quota=target(plan)
    phase=(session or {}).get('course_phase') or phase_number(plan)
    return level,50 if phase and phase%5==0 else quota


def phases(plan):
    state=cycle(plan)
    if state is None: return []
    roots=roots_for(plan)
    if not roots: return []
    current=phase_number(plan)
    results=plan.get('phase_results',{})
    return [dict(number=number,boss=number%5==0,completed=number<current,
                 current=number==current,unlocked=number==current,
                 accuracy=results.get(str(number),{}).get('accuracy'),
                 branch=roots[(number-1)%len(roots)]['branch']) for number in range(1,PHASE_LIMIT+1)]


def ensure_phase_session(plan,session):
    """Expand an unfinished legacy boss quiz without discarding its answers."""
    if cycle(plan) is None or session.get('course_round')!=cycle(plan)['round'] or session.get('practice_intent') not in ('learn','practice'):
        return
    session.setdefault('course_phase',phase_number(plan))
    if session.get('mode')!='quiz' or session['course_phase']%5 or session.get('quiz_limit')==50 or session.get('phase')=='complete': return
    bank=session.get('quiz_bank')
    if not bank: return
    originals=list(bank.values())
    for index in range(len(bank),50):
        key=str(index);bank[key]=dict(originals[index%len(originals)])
        session['quiz_states'][key]='pending';session['quiz_queue'].append(index)
        session.setdefault('display_marks',{})[key]='pending'
    session.update(quiz_limit=50,quiz_size=50,revision=session['revision']+1)


def cycle(plan):
    if 'personal_lines' in plan or plan.get('classroom_line_ids') is not None:
        return None
    if 'course_cycle' not in plan:
        from opening_training_state import lines_for
        learned=plan.get('practice_progress',{})
        completed=[item['branch'] for item in lines_for(plan).values() if item.get('stage')=='foundation' and learned.get(item['id'],{}).get('learned')]
        plan['course_cycle']=dict(round=0,completed=completed)
        roots=[item for item in lines_for(plan).values() if item.get('stage')=='foundation']
        if roots and len(completed)==len(roots): plan['course_cycle'].update(round=1,completed=[])
    return plan['course_cycle']


def target(plan):
    state=cycle(plan)
    number=state['round'] if state else 0
    return 5+2*max(0,number-1),QUIZ_LIMITS[min(number,4)]


def next_lesson(plan,lessons):
    state=cycle(plan)
    if state is None: return None,None
    if phase_number(plan)>PHASE_LIMIT: return None,None
    level,_=target(plan)
    roots=sorted((line for line in lessons if line.get('stage')=='foundation'),key=lambda line:line['branch'])
    for root in roots:
        if root['branch'] in state['completed']: continue
        available=next((line for line in lessons if line.get('branch')==root['branch'] and line.get('lesson_moves')==level and not line.get('needs_preparation')),None)
        source=max((line for line in lessons if line.get('branch')==root['branch'] and line.get('lesson_moves',5)<level and not line.get('needs_preparation')),key=lambda line:line.get('lesson_moves',5),default=root)
        return available, source
    return None,None


def complete(plan,session,line):
    state=cycle(plan)
    if state is None or session.get('cycle_recorded') or session.get('practice_intent') not in ('learn','practice'): return
    level,quota=quiz_target(plan,session)
    if session.get('course_round')!=state['round'] or line.get('lesson_moves')!=level: return
    states=session.get('quiz_states',{})
    if session.get('quiz_queue') or len(states)<quota or any(value!='correct' for value in states.values()): return
    from opening_training_state import lines_for
    _,source=next_lesson(plan,list(lines_for(plan).values()))
    if not source or source['branch']!=line['branch']: return
    number=phase_number(plan)
    if session.get('course_phase',number)!=number: return
    from preparation_state import today
    first=session.get('quiz_first_answers',{})
    accuracy=round(100*sum(first.values())/len(first),1) if first else None
    plan.setdefault('phase_results',{})[str(number)]=dict(completed=True,accuracy=accuracy,
        questions=len(states),first_correct=sum(first.values()),day=str(today()),line_id=line['id'],boss=number%5==0)
    stats=plan.setdefault('achievement_progress',{})
    stats['phases']=max(stats.get('phases',0),number)
    if number%5==0:
        title=f'Guardião {number//5}'
        plan.setdefault('achievements',{}).setdefault(f'phase_{number}',dict(day=str(today()),title=title))
        session.setdefault('new_achievements',[]).append(title)
    state['completed'].append(line['branch']);session['cycle_recorded']=True
    branches={item['branch'] for item in lines_for(plan).values() if item.get('stage')=='foundation'}
    if branches and branches.issubset(state['completed']):
        state['round']+=1;state['completed']=[]
