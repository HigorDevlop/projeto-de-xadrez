"""Authoritative tactical-block scoring and progression gates, entirely local."""
import hashlib
import json
import time
import chess


def puzzles(payload):
    return payload.get('puzzles') or [payload]


def puzzle_id(puzzle):
    return hashlib.sha256((puzzle['fen']+'|'+' '.join(puzzle['solution'])).encode()).hexdigest()[:32]


def tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS lesson_tactic_blocks(material TEXT,student TEXT,payload TEXT,updated REAL,PRIMARY KEY(material,student))')


def initial(passed=False,history=None):
    return dict(index=0,ply=0,failed=False,results=[],errors=0,passed=bool(passed),history=history or [])


def load(db,identifier,student):
    tables(db)
    row=db.execute('SELECT payload FROM lesson_tactic_blocks WHERE material=? AND student=?',(identifier,student)).fetchone()
    return json.loads(row['payload']) if row else initial()


def persist(db,identifier,student,state):
    db.execute('INSERT INTO lesson_tactic_blocks VALUES(?,?,?,?) ON CONFLICT(material,student) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(identifier,student,json.dumps(state),time.time()))


def summary(payload,state):
    total=len(puzzles(payload));clean=sum(state['results']);done=state['index']>=total
    finished=len(state['results'])
    return dict(total=total,finished=finished,clean=clean,percent=100*clean/total,accuracy=100*clean/finished if finished else 0,done=done,current_pass=done and clean*100>=90*total,passed=state['passed'])


def position(payload,state):
    group=puzzles(payload);index=min(state['index'],len(group)-1);puzzle=group[index]
    board=chess.Board(puzzle['fen'])
    for move in puzzle['solution'][:state['ply']]:board.push_uci(move)
    return board,puzzle['solution'],chess.Board(puzzle['fen']).turn


def finish(payload,state):
    state['results'].append(not state['failed']);state['index']+=1;state['ply']=0;state['failed']=False
    if state['index']==len(puzzles(payload)):
        clean=sum(state['results']);total=len(state['results'])
        state['passed']=state['passed'] or clean*100>=90*total
        state['history']=(state.get('history',[])+[dict(clean=clean,total=total,percent=100*clean/total)])[-20:]
    return state


def attempt(payload,state,index,ply,uci,fen):
    state=json.loads(json.dumps(state))
    if index!=state['index'] or ply!=state['ply']:raise ValueError('O exercício mudou. Tente novamente na posição atual.')
    if state['index']>=len(puzzles(payload)):raise ValueError('Esta rodada terminou.')
    board,moves,side=position(payload,state)
    if board.fen()!=fen:raise ValueError('O tabuleiro mudou. Reabra o bloco.')
    if board.turn!=side:raise ValueError('Aguarde a resposta do adversário.')
    correct=uci==moves[ply]
    if correct:
        board.push_uci(uci);state['ply']+=1
        if state['ply']<len(moves) and board.turn!=side:
            board.push_uci(moves[state['ply']]);state['ply']+=1
        if state['ply']==len(moves):finish(payload,state)
    else:state['failed']=True;state['errors']+=1
    return state,correct


def advance_without_credit(payload,state,index,ply):
    state=json.loads(json.dumps(state))
    if index!=state['index'] or ply!=state['ply'] or index>=len(puzzles(payload)):raise ValueError('O exercício mudou.')
    state['failed']=True;state['errors']+=1
    return finish(payload,state)


def get_state(token,identifier):
    import classroom as rooms
    import classroom_materials as materials
    with rooms.database() as db:
        row,actor=materials._get(db,token,identifier)
        payload=json.loads(row['payload'])
        if row['kind']!='tactic' or 'puzzles' not in payload:raise ValueError('Bloco de táticos inválido.')
        return payload,load(db,identifier,actor['id'])


def act(token,identifier,index,ply,uci=None,fen=None,action='move'):
    import classroom as rooms
    import classroom_materials as materials
    with rooms.database() as db:
        materials.tables(db);tables(db);db.execute('BEGIN IMMEDIATE')
        row,actor=materials._get(db,token,identifier)
        if actor['role']!='student':raise PermissionError('Use a simulação particular do professor.')
        payload=json.loads(row['payload']);state=load(db,identifier,actor['id'])
        if row['kind']!='tactic' or 'puzzles' not in payload:raise ValueError('Bloco inválido.')
        correct=None
        if action=='restart':state=initial(state['passed'],state.get('history',[]))
        elif action=='skip':state=advance_without_credit(payload,state,index,ply)
        elif action=='move':state,correct=attempt(payload,state,index,ply,uci,fen)
        else:raise ValueError('Ação inválida.')
        persist(db,identifier,actor['id'],state)
        return state,correct


def passed(db,identifier,student):
    return load(db,identifier,student)['passed']


def activity_blocks(db,student):
    """Read the ordered plan once; large puzzle payloads never cross this query."""
    rows=db.execute("SELECT m.id,s.id AS step,s.locked,json_type(m.payload,'$.puzzles') AS pack FROM lesson_trail_steps s JOIN lesson_trail_items i ON i.step=s.id JOIN lesson_materials m ON m.id=i.material WHERE s.student=? AND m.published=1 ORDER BY s.position,i.position",(student,)).fetchall()
    from classroom_schedule import releases,is_locked
    schedule=releases(db)
    result={};manual=False;waiting=False
    for row in rows:
        manual=manual or is_locked(row['locked'],schedule.get(row['step']))
        result[row['id']]='teacher' if manual else 'tactics' if waiting else ''
        if row['pack']=='array' and not passed(db,row['id'],student):waiting=True
    return result
