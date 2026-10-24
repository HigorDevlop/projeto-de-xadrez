"""Private, offline room assignments and authoritative exam correction."""
from io import StringIO
import json
import re
import secrets
import time
import unicodedata
import chess
import chess.pgn
import classroom as rooms

KINDS=('line','tactic','game','exam')


def tables(db):
    db.execute('''CREATE TABLE IF NOT EXISTS lesson_materials(id TEXT PRIMARY KEY,student TEXT,room TEXT,
        title TEXT,kind TEXT,payload TEXT,published INTEGER,created REAL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS lesson_results(material TEXT,student TEXT,payload TEXT,updated REAL,
        PRIMARY KEY(material,student))''')
    db.execute('''CREATE TABLE IF NOT EXISTS lesson_training(material TEXT,student TEXT,completed INTEGER,errors INTEGER,
        updated REAL,progress INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(material,student))''')
    if 'progress' not in {r['name'] for r in db.execute('PRAGMA table_info(lesson_training)')}:
        db.execute('ALTER TABLE lesson_training ADD COLUMN progress INTEGER NOT NULL DEFAULT 0')


def parse_pgn(text):
    if not isinstance(text,str) or not text.strip() or len(text)>500_000:
        raise ValueError('Informe uma partida ou linha PGN de até 500 mil caracteres.')
    game=chess.pgn.read_game(StringIO(text))
    if not game or game.errors or not list(game.mainline_moves()) or not game.board().is_valid():
        raise ValueError('PGN inválido ou sem lances. Confira também a posição inicial.')
    return game


def validate(kind,payload):
    if kind not in KINDS or not isinstance(payload,dict):raise ValueError('Material inválido.')
    if kind in ('line','game'):
        game=parse_pgn(payload.get('pgn',''))
        if payload.get('side','white') not in ('white','black'):raise ValueError('Escolha o lado do aluno.')
        if kind=='line':
            board=game.board();has_decision=False
            for move in game.mainline_moves():
                has_decision=has_decision or board.turn==(payload.get('side','white')=='white')
                board.push(move)
            if not has_decision:raise ValueError('A linha precisa conter pelo menos um lance do lado escolhido para o aluno.')
        return dict(pgn=str(game),side=payload.get('side','white'),instructions=str(payload.get('instructions',''))[:5000])
    if kind=='tactic':
        try:
            board=chess.Board(payload['fen'])
            if not board.is_valid():raise ValueError()
            moves=payload['solution']
            if not isinstance(moves,list) or not 1<=len(moves)<=200:raise ValueError()
            for move in moves:board.push_uci(move)
        except (KeyError,TypeError,ValueError):raise ValueError('Confira o FEN e a sequência de lances UCI do tático.') from None
        return dict(fen=chess.Board(payload['fen']).fen(),solution=moves,source=str(payload.get('source','Professor'))[:100],instructions=str(payload.get('instructions',''))[:5000])
    questions=payload.get('questions')
    if not isinstance(questions,list) or not 1<=len(questions)<=50:raise ValueError('Crie de 1 a 50 perguntas.')
    checked=[]
    for index,q in enumerate(questions):
        if not isinstance(q,dict) or q.get('kind') not in ('open','closed') or not str(q.get('prompt','')).strip():raise ValueError(f'Confira a pergunta {index+1}.')
        weight=q.get('weight',1)
        if type(weight) not in (int,float) or not 0<weight<=100:raise ValueError('O peso deve estar entre 0 e 100.')
        answer=q.get('answer','')
        options=q.get('options',[])
        if q['kind']=='closed':
            if (not isinstance(options,list) or not 2<=len(options)<=8 or any(not isinstance(o,str) or not o.strip() or len(o)>1000 for o in options)
                    or len(set(options))!=len(options) or type(answer) is not int or not 0<=answer<len(options)):
                raise ValueError('Perguntas fechadas precisam de 2 a 8 alternativas distintas e uma resposta correta.')
        elif not isinstance(answer,str) or len(answer)>10_000:raise ValueError('Gabarito aberto inválido.')
        checked.append(dict(kind=q['kind'],prompt=str(q['prompt'])[:5000],weight=weight,options=options if q['kind']=='closed' else [],answer=answer))
    return dict(questions=checked,instructions=str(payload.get('instructions',''))[:5000])


def save_material(token,student,title,kind,payload,published=True):
    if not isinstance(title,str) or not title.strip() or len(title)>150:raise ValueError('Informe um título de até 150 caracteres.')
    payload=validate(kind,payload)
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        seat=rooms._owned_student(db,token,student)
        if seat['banned']:raise ValueError('A chave deste aluno foi revogada.')
        identifier=secrets.token_hex(16)
        db.execute('INSERT INTO lesson_materials VALUES(?,?,?,?,?,?,?,?)',
                   (identifier,student,seat['room'],title.strip(),kind,json.dumps(payload),int(bool(published)),time.time()))
    return identifier


def _get(db,token,identifier,teacher=False):
    tables(db);actor=rooms._identity(db,token)
    row=db.execute('SELECT * FROM lesson_materials WHERE id=?',(identifier,)).fetchone()
    if not row:raise PermissionError('Material não disponível nesta sala.')
    if actor['role'] in ('professor','admin'):
        rooms._owned_student(db,token,row['student'])
    elif teacher or actor['role']!='student' or actor['id']!=row['student'] or actor['room']!=row['room'] or not row['published']:
        raise PermissionError('Entre com a chave da sala que recebeu este material.')
    return row,actor


def list_materials(token,student=None):
    with rooms.database() as db:
        tables(db);actor=rooms._identity(db,token)
        if actor['role'] in ('professor','admin'):
            rooms._owned_student(db,token,student);teacher=True
        elif actor['role']=='student' and student in (None,actor['id']):student=actor['id'];teacher=False
        else:raise PermissionError('Abra a sala do Professor com sua chave de acesso.')
        rows=db.execute('SELECT * FROM lesson_materials WHERE student=? ORDER BY created DESC',(student,)).fetchall()
        result=[]
        for row in rows:
            if not teacher and not row['published']:continue
            item=dict(row);item['payload']=json.loads(row['payload'])
            if not teacher and row['kind']=='exam':
                for question in item['payload']['questions']:question.pop('answer',None)
            grade=db.execute('SELECT payload FROM lesson_results WHERE material=? AND student=?',(row['id'],student)).fetchone()
            item['result']=json.loads(grade['payload']) if grade else None
            progress=db.execute('SELECT completed,errors,progress FROM lesson_training WHERE material=? AND student=?',(row['id'],student)).fetchone()
            item['progress']=dict(progress) if progress else None
            result.append(item)
        return result


def set_published(token,identifier,published):
    with rooms.database() as db:
        _get(db,token,identifier,teacher=True)
        db.execute('UPDATE lesson_materials SET published=? WHERE id=?',(int(bool(published)),identifier))


def normalize_answer(text):
    return ' '.join(re.sub(r'[^\w\s]',' ',''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))).split())


def _score(rows):
    maximum=sum(row['weight'] for row in rows)
    pending=sum(row['score'] is None for row in rows)
    earned=sum(row['score'] or 0 for row in rows)
    return dict(questions=rows,score=earned,maximum=maximum,percent=round(100*earned/maximum,1),pending=pending)


def submit_exam(token,identifier,answers):
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        row,actor=_get(db,token,identifier)
        if actor['role']!='student' or row['kind']!='exam':raise PermissionError('Somente o aluno pode responder sua prova.')
        previous=db.execute('SELECT payload FROM lesson_results WHERE material=? AND student=?',(identifier,actor['id'])).fetchone()
        if previous:return json.loads(previous['payload'])
        questions=json.loads(row['payload'])['questions']
        if not isinstance(answers,list) or len(answers)!=len(questions):raise ValueError('Responda todas as perguntas antes de enviar.')
        results=[]
        for q,answer in zip(questions,answers):
            if q['kind']=='closed':
                if type(answer) is not int or not 0<=answer<len(q['options']):raise ValueError('Escolha uma alternativa em cada pergunta fechada.')
                score=q['weight'] if answer==q['answer'] else 0
            else:
                if not isinstance(answer,str) or not answer.strip() or len(answer)>10_000:raise ValueError('Preencha as respostas abertas (até 10 mil caracteres cada).')
                accepted=[normalize_answer(v) for v in q['answer'].split('|') if normalize_answer(v)]
                score=(q['weight'] if normalize_answer(answer) in accepted else 0) if accepted else None
            results.append(dict(answer=answer,score=score,weight=q['weight'],feedback=''))
        result=_score(results)
        db.execute('INSERT INTO lesson_results VALUES(?,?,?,?)',(identifier,actor['id'],json.dumps(result),time.time()))
        return result


def grade_exam(token,identifier,scores,feedback):
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        row,_=_get(db,token,identifier,teacher=True)
        saved=db.execute('SELECT payload FROM lesson_results WHERE material=? AND student=?',(identifier,row['student'])).fetchone()
        if not saved or row['kind']!='exam':raise ValueError('Esta prova ainda não foi enviada pelo aluno.')
        questions=json.loads(saved['payload'])['questions']
        if len(scores)!=len(questions) or len(feedback)!=len(questions):raise ValueError('Confira a correção de todas as perguntas.')
        for q,score,note in zip(questions,scores,feedback):
            if type(score) not in (int,float) or not 0<=score<=q['weight']:raise ValueError('Nota fora do peso da pergunta.')
            q.update(score=score,feedback=str(note)[:5000])
        result=_score(questions)
        db.execute('UPDATE lesson_results SET payload=?,updated=? WHERE material=? AND student=?',(json.dumps(result),time.time(),identifier,row['student']))
        return result


def training_moves(payload,kind):
    if kind=='tactic':return chess.Board(payload['fen']),list(payload['solution'])
    game=parse_pgn(payload['pgn'])
    return game.board(),[move.uci() for move in game.mainline_moves()]


def check_training(token,identifier,progress,uci,fen):
    """Each student move is checked against the stored line, including the source position."""
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE')
        row,actor=_get(db,token,identifier)
        if actor['role']!='student' or row['kind'] not in ('line','tactic'):raise PermissionError('Treino não disponível.')
        payload=json.loads(row['payload']);board,moves=training_moves(payload,row['kind'])
        expected_side=board.turn if row['kind']=='tactic' else payload['side']=='white'
        initial=1 if board.turn!=expected_side else 0
        previous=db.execute('SELECT completed,errors,progress FROM lesson_training WHERE material=? AND student=?',(identifier,actor['id'])).fetchone()
        expected_progress=previous['progress'] if previous else initial
        if progress!=expected_progress:raise ValueError('O progresso mudou. Reabra ou reinicie o treino.')
        if type(progress) is not int or not 0<=progress<len(moves):raise ValueError('Posição do treino inválida.')
        for move in moves[:progress]:board.push_uci(move)
        if board.fen()!=fen:raise ValueError('O tabuleiro mudou. Reabra este exercício.')
        if board.turn!=expected_side:raise ValueError('Aguarde a resposta do adversário.')
        correct=uci==moves[progress]
        if correct:
            board.push_uci(uci);progress+=1
            if progress<len(moves) and board.turn!=expected_side:board.push_uci(moves[progress]);progress+=1
        completed=progress==len(moves)
        errors=(previous['errors'] if previous else 0)+int(not correct)
        db.execute('INSERT INTO lesson_training VALUES(?,?,?,?,?,?) ON CONFLICT(material,student) DO UPDATE SET completed=MAX(completed,excluded.completed),errors=excluded.errors,updated=excluded.updated,progress=excluded.progress',
                   (identifier,actor['id'],int(completed),errors,time.time(),progress))
        return dict(progress=progress,correct=correct,completed=completed)


def restart_training(token,identifier):
    with rooms.database() as db:
        row,actor=_get(db,token,identifier)
        if actor['role']!='student' or row['kind'] not in ('line','tactic'):raise PermissionError('Treino não disponível.')
        payload=json.loads(row['payload']);board,_=training_moves(payload,row['kind'])
        side=board.turn if row['kind']=='tactic' else payload['side']=='white'
        initial=1 if board.turn!=side else 0
        db.execute('UPDATE lesson_training SET progress=? WHERE material=? AND student=?',(initial,identifier,actor['id']))
        return initial


def local_puzzles(theme,minimum=0,maximum=4000):
    from offline_tactics import _bank,bank_path
    path=bank_path();puzzles,index=_bank(str(path),path.stat().st_mtime_ns)
    return [puzzles[i] for i in index[theme] if minimum<=puzzles[i].rating<=maximum]
