"""Local classrooms with authenticated roles, four seats and auditable training."""
from contextlib import contextmanager
from datetime import date, timedelta
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
from pathlib import Path
import json
import os
import secrets
import sqlite3
import time

from preparation_state import today

PROFESSOR_KEY_TTL=15*60


class RegistrationPending(ValueError):
    """Registration was committed, but the creator must authorize access."""


@contextmanager
def database():
    path = Path(os.environ.get('COACH_CLASSROOM_DB', Path(__file__).parent/'data/classrooms.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS professors(id TEXT PRIMARY KEY, name TEXT UNIQUE, salt TEXT, password TEXT, approved INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS administrators(id TEXT PRIMARY KEY, name TEXT UNIQUE, salt TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT UNIQUE, salt TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS memberships(owner TEXT PRIMARY KEY, student TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS professor_invites(id TEXT PRIMARY KEY, key_hash TEXT UNIQUE, label TEXT,
            created REAL, revoked INTEGER DEFAULT 0, used_by TEXT);
        CREATE TABLE IF NOT EXISTS devices(token TEXT PRIMARY KEY, role TEXT, owner TEXT, expires REAL);
        CREATE TABLE IF NOT EXISTS students(id TEXT PRIMARY KEY, room TEXT, slot INTEGER,
            name TEXT, chesscom TEXT DEFAULT '', access_key TEXT UNIQUE, warnings INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0, UNIQUE(room,slot));
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, role TEXT, owner TEXT,
            expires REAL, last_tick REAL);
        CREATE TABLE IF NOT EXISTS routines(id INTEGER PRIMARY KEY, student TEXT, day TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, student TEXT, day TEXT,
            event_key TEXT, kind TEXT, correct INTEGER, solved INTEGER, line TEXT, states TEXT,
            UNIQUE(student,event_key));
        CREATE TABLE IF NOT EXISTS training_time(student TEXT, day TEXT, seconds REAL,
            PRIMARY KEY(student,day));
        CREATE TABLE IF NOT EXISTS presence(student TEXT PRIMARY KEY,last_tick REAL);
        CREATE TABLE IF NOT EXISTS training_visits(id TEXT PRIMARY KEY,student TEXT,day TEXT,
            started REAL,last_seen REAL,ended REAL,seconds REAL DEFAULT 0,target REAL,
            completed INTEGER DEFAULT 0,reason TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS active_training_visit ON training_visits(student) WHERE ended IS NULL;
        CREATE TABLE IF NOT EXISTS warnings(id INTEGER PRIMARY KEY, student TEXT, created REAL, reason TEXT);
        CREATE TABLE IF NOT EXISTS profile_photos(role TEXT, owner TEXT, photo BLOB NOT NULL,
            PRIMARY KEY(role,owner));
        CREATE TABLE IF NOT EXISTS account_chesscom(role TEXT, owner TEXT, username TEXT NOT NULL,
            PRIMARY KEY(role,owner));
        CREATE TABLE IF NOT EXISTS login_days(role TEXT,owner TEXT,day TEXT,PRIMARY KEY(role,owner,day));
        CREATE TABLE IF NOT EXISTS account_access(owner TEXT PRIMARY KEY,status TEXT NOT NULL DEFAULT 'active',
            created REAL,last_login REAL,last_seen REAL);
        CREATE TABLE IF NOT EXISTS room_messages(id INTEGER PRIMARY KEY,room TEXT,channel TEXT,sender TEXT,name TEXT,body TEXT,created REAL,nonce TEXT,UNIQUE(sender,nonce));
        CREATE TABLE IF NOT EXISTS room_videos(id TEXT PRIMARY KEY,room TEXT,title TEXT,url TEXT,media BLOB,mime TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS live_classes(id TEXT PRIMARY KEY,room TEXT,title TEXT,created REAL,ended REAL);
        CREATE TABLE IF NOT EXISTS live_peers(id TEXT PRIMARY KEY,class_id TEXT,actor TEXT,name TEXT,teacher INTEGER,seen REAL);
        CREATE TABLE IF NOT EXISTS live_signals(id INTEGER PRIMARY KEY,class_id TEXT,sender TEXT,target TEXT,kind TEXT,payload TEXT,created REAL,nonce TEXT,UNIQUE(sender,nonce));
    ''')
    # Accounts created by the old public signup are not trusted automatically.
    db.execute('BEGIN IMMEDIATE')
    # Access is open unless the creator explicitly blocked the account.
    # Migrate pending registrations from the superseded approval-only policy.
    db.execute("UPDATE account_access SET status='active' WHERE status='pending'")
    if 'deleted' not in {row['name'] for row in db.execute('PRAGMA table_info(professor_invites)')}:
        db.execute('ALTER TABLE professor_invites ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0')
    if 'approved' not in {row['name'] for row in db.execute('PRAGMA table_info(professors)')}:
        db.execute('ALTER TABLE professors ADD COLUMN approved INTEGER NOT NULL DEFAULT 0')
        db.execute('DELETE FROM sessions')
        db.execute('DELETE FROM devices')
    db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()


def _digest(value):
    return sha256(value.encode()).hexdigest()


def _account(db, role, owner):
    tables={'professor':'professors','student':'students','admin':'administrators','user':'users'}
    if role not in tables:
        raise PermissionError('Perfil inválido.')
    row=db.execute(f'SELECT * FROM {tables[role]} WHERE id=?',(owner,)).fetchone()
    if not row or role=='professor' and not row['approved'] or role=='student' and row['banned']:
        raise PermissionError('Acesso revogado ou não autorizado pelo criador.')
    if role=='user':
        access=db.execute('SELECT status FROM account_access WHERE owner=?',(owner,)).fetchone()
        if access and access['status']!='active':
            raise PermissionError('Conta aguardando autorização ou bloqueada pelo criador.')
    if role=='student':
        access=db.execute('SELECT status FROM memberships JOIN account_access ON account_access.owner=memberships.owner WHERE student=?',(owner,)).fetchone()
        if access and access['status']!='active':
            raise PermissionError('A conta vinculada foi bloqueada pelo criador.')
    professor_id=owner if role=='professor' else row['room'] if role=='student' else None
    admin_room=bool(role=='student' and db.execute('SELECT 1 FROM administrators WHERE id=?',(professor_id,)).fetchone())
    if professor_id and not admin_room and not db.execute('SELECT 1 FROM professor_invites WHERE used_by=? AND revoked=0',(professor_id,)).fetchone():
        raise PermissionError('A chave do Professor foi revogada ou ainda não foi emitida pelo criador.')
    if role=='student':
        professor=db.execute('SELECT approved FROM professors WHERE id=?',(row['room'],)).fetchone()
        if not admin_room and (not professor or not professor['approved']):
            raise PermissionError('O acesso do Professor desta sala foi suspenso pelo criador.')
    return row


def _identity(db, token, role=None):
    session = db.execute('SELECT * FROM sessions WHERE token=? AND expires>?', (_digest(token or ''), time.time())).fetchone()
    if not session or role and session['role'] != role:
        raise PermissionError('Entre com uma conta autorizada para continuar.')
    row = _account(db,session['role'],session['owner'])
    if session['role']=='user':
        now=time.time()
        db.execute('UPDATE account_access SET last_seen=? WHERE owner=? AND (last_seen IS NULL OR last_seen<?)',
                   (now,session['owner'],now-60))
    result = dict(row)
    for key in ('password', 'salt', 'access_key'):
        result.pop(key, None)
    preference = db.execute('SELECT username FROM account_chesscom WHERE role=? AND owner=?',
                            (session['role'], session['owner'])).fetchone()
    if preference is not None:
        result['chesscom'] = preference['username']
    return dict(result, role=session['role'])


def identity(token):
    if not token:
        return None
    with database() as db:
        try:
            return _identity(db, token)
        except PermissionError:
            return None


def save_chesscom_user(token, username):
    """Remember the public Chess.com name locally, independently of network access."""
    from chesscom import normalize_username
    username = normalize_username(username) if username.strip() else ''
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user = _identity(db, token)
        db.execute('INSERT INTO account_chesscom VALUES(?,?,?) '
                   'ON CONFLICT(role,owner) DO UPDATE SET username=excluded.username',
                   (user['role'], user['id'], username))
    return username


def save_profile_photo(token,photo):
    from profile_photo import normalize_photo
    photo=normalize_photo(photo,square=True)
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user=_identity(db,token)
        db.execute('INSERT INTO profile_photos VALUES(?,?,?) ON CONFLICT(role,owner) DO UPDATE SET photo=excluded.photo',
            (user['role'],user['id'],photo))
    return photo


def load_profile_photo(token):
    with database() as db:
        user=_identity(db,token)
        row=db.execute('SELECT photo FROM profile_photos WHERE role=? AND owner=?',(user['role'],user['id'])).fetchone()
        return bytes(row['photo']) if row else None


def _session(db, role, owner):
    token = secrets.token_urlsafe(32)
    db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)', (_digest(token), role, owner, time.time()+43200, None))
    if role=='user':
        now=time.time()
        db.execute('INSERT INTO account_access(owner,last_login,last_seen) VALUES(?,?,?) ON CONFLICT(owner) DO UPDATE SET last_login=excluded.last_login,last_seen=excluded.last_seen',
                   (owner,now,now))
    return token


def register_professor(name, password, invitation=None):
    name = name.strip().lower()
    if not 2 <= len(name) <= 50 or len(password) < 10:
        raise ValueError('Use um nome de 2 a 50 caracteres e uma senha com pelo menos 10 caracteres.')
    salt, identifier = secrets.token_hex(16), secrets.token_hex(16)
    encoded = pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 260000).hex()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        invite=db.execute('SELECT * FROM professor_invites WHERE key_hash=? AND revoked=0 AND deleted=0 AND used_by IS NULL AND created>?',
            (_digest(invitation or ''),time.time()-PROFESSOR_KEY_TTL)).fetchone()
        if not invite:
            raise ValueError('O cadastro de Professor exige uma chave especial válida emitida pelo criador.')
        try:
            db.execute('INSERT INTO professors(id,name,salt,password,approved) VALUES(?,?,?,?,1)', (identifier,name,salt,encoded))
        except sqlite3.IntegrityError:
            raise ValueError('Este nome de Professor já está cadastrado.') from None
        for slot in range(1,5):
            db.execute('INSERT INTO students(id,room,slot,name,access_key) VALUES(?,?,?,?,?)',
                (secrets.token_hex(16),identifier,slot,f'Aluno {slot}',secrets.token_urlsafe(24)))
        db.execute('UPDATE professor_invites SET used_by=? WHERE id=?',(identifier,invite['id']))
        return _session(db, 'professor', identifier)


def login_professor(name, password, invitation=None):
    if not invitation or not invitation.strip():
        raise ValueError('Informe a chave especial de Professor emitida pelo criador.')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM professors WHERE name=?', (name.strip().lower(),)).fetchone()
        salt = bytes.fromhex(row['salt']) if row else bytes(16)
        encoded = pbkdf2_hmac('sha256', password.encode(), salt, 260000).hex()
        bound=db.execute('SELECT used_by FROM professor_invites WHERE key_hash=? AND revoked=0',(_digest(invitation.strip()),)).fetchone()
        if not row or not compare_digest(encoded, row['password']) or not row['approved'] or not bound or bound['used_by']!=row['id']:
            raise ValueError('Usuário, senha ou chave de Professor inválidos.')
        return _session(db,'professor',row['id'])


def enter_professor(name,password,invitation):
    if not invitation or not invitation.strip():
        raise ValueError('Informe a chave especial de Professor emitida pelo criador.')
    with database() as db:
        exists=db.execute('SELECT 1 FROM professors WHERE name=?',(name.strip().lower(),)).fetchone()
    return login_professor(name,password,invitation) if exists else register_professor(name,password,invitation.strip())


def login_student(key):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM students WHERE access_key=? AND banned=0', (key.strip(),)).fetchone()
        if not row:
            raise ValueError('Chave inválida ou revogada.')
        if db.execute('SELECT 1 FROM memberships WHERE student=?',(row['id'],)).fetchone():
            raise ValueError('Esta vaga já está vinculada a uma conta. Entre como Usuário.')
        try:_account(db,'student',row['id'])
        except PermissionError as error:raise ValueError(str(error)) from None
        return _session(db,'student',row['id'])


def register_user(name,password,require_approval=None):
    name=name.strip().lower()
    if not 2<=len(name)<=50 or len(password)<10:
        raise ValueError('Use um usuário de 2 a 50 caracteres e senha com pelo menos 10 caracteres.')
    salt=secrets.token_hex(16);identifier=secrets.token_hex(16)
    encoded=pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),260000).hex()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if name=='superadmin' or db.execute('SELECT 1 FROM administrators WHERE name=?',(name,)).fetchone():
            raise ValueError('Este nome de usuário não está disponível.')
        try:db.execute('INSERT INTO users VALUES(?,?,?,?)',(identifier,name,salt,encoded))
        except sqlite3.IntegrityError:raise ValueError('Este usuário já está cadastrado.') from None
        db.execute('INSERT INTO account_access(owner,status,created) VALUES(?,?,?)',
                   (identifier,'active',time.time()))
        token=_session(db,'user',identifier)
    return token


def login_user(name,password):
    name=name.strip().lower()
    with database() as db:
        # The creator uses the same entry without exposing a public admin selector.
        table='administrators' if db.execute('SELECT 1 FROM administrators WHERE name=?',(name,)).fetchone() else 'users'
        row=db.execute(f'SELECT * FROM {table} WHERE name=?',(name,)).fetchone()
        salt=bytes.fromhex(row['salt']) if row else bytes(16)
        encoded=pbkdf2_hmac('sha256',password.encode(),salt,260000).hex()
        if not row or not compare_digest(encoded,row['password']):raise ValueError('Usuário ou senha inválidos.')
        if table=='users':
            _account(db,'user',row['id'])
        return _session(db,'admin' if table=='administrators' else 'user',row['id'])


def membership(token):
    with database() as db:
        user=_identity(db,token,'user')
        row=db.execute('SELECT students.id,students.banned,COALESCE(professors.name,administrators.name) AS professor FROM memberships JOIN students ON students.id=memberships.student LEFT JOIN professors ON professors.id=students.room LEFT JOIN administrators ON administrators.id=students.room WHERE owner=?',(user['id'],)).fetchone()
        return dict(row) if row else None


def join_room(token,code):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user=_identity(db,token,'user')
        student=db.execute('SELECT * FROM students WHERE access_key=? AND banned=0',(code.strip(),)).fetchone()
        if not student:raise ValueError('Código inválido ou revogado.')
        _account(db,'student',student['id'])
        existing=db.execute('SELECT * FROM memberships WHERE owner=? OR student=?',(user['id'],student['id'])).fetchall()
        if any(row['owner']!=user['id'] or row['student']!=student['id'] for row in existing):
            raise ValueError('A conta ou esta vaga já está vinculada a uma sala.')
        if not existing:
            db.execute('INSERT INTO memberships VALUES(?,?)',(user['id'],student['id']))
            db.execute('UPDATE students SET name=? WHERE id=?',(user['name'],student['id']))
            db.execute("DELETE FROM sessions WHERE role='student' AND owner=?",(student['id'],))
            db.execute("DELETE FROM devices WHERE role='student' AND owner=?",(student['id'],))
        return _session(db,'student',student['id'])


def room_session(token):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user=_identity(db,token,'user')
        row=db.execute('SELECT student FROM memberships WHERE owner=?',(user['id'],)).fetchone()
        if not row:raise ValueError('Junte-se a uma sala usando o código do Professor.')
        _account(db,'student',row['student'])
        return _session(db,'student',row['student'])


def logout(token):
    with database() as db:
        db.execute('DELETE FROM sessions WHERE token=?', (_digest(token or ''),))


def students(token):
    with database() as db:
        professor = _identity(db, token)
        if professor['role']=='admin':
            return [dict(row) for row in db.execute('SELECT students.*,COALESCE(professors.name,administrators.name) AS professor FROM students LEFT JOIN professors ON room=professors.id LEFT JOIN administrators ON room=administrators.id WHERE professors.id IS NOT NULL OR administrators.id IS NOT NULL ORDER BY professor,slot')]
        if professor['role']!='professor':
            raise PermissionError('Somente Professor ou Superadministrador.')
        return [dict(row) for row in db.execute('SELECT * FROM students WHERE room=? ORDER BY slot', (professor['id'],))]


def ensure_admin_room(token):
    """The creator can author and test without creating a professor account."""
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        actor=_identity(db,token,'admin')
        for slot in range(1,5):
            db.execute('INSERT OR IGNORE INTO students(id,room,slot,name,access_key) VALUES(?,?,?,?,?)',
                       (secrets.token_hex(16),actor['id'],slot,f'Laboratório {slot}',secrets.token_urlsafe(24)))
        return [dict(r) for r in db.execute('SELECT * FROM students WHERE room=? ORDER BY slot',(actor['id'],))]


def admin_preview_session(token,student):
    with database() as db:
        actor=_identity(db,token,'admin');seat=_owned_student(db,token,student)
        if seat['room']!=actor['id']:raise PermissionError('Use uma vaga do laboratório para testar sem alterar os dados de alunos reais.')
        return _session(db,'student',student)


def admin_maintain_student(token,student,reactivate=False):
    with database() as db:
        db.execute('BEGIN IMMEDIATE');_identity(db,token,'admin');_owned_student(db,token,student)
        db.execute('UPDATE students SET access_key=? WHERE id=?',(secrets.token_urlsafe(24),student))
        if reactivate:db.execute('UPDATE students SET banned=0,warnings=0 WHERE id=?',(student,))
        db.execute("DELETE FROM sessions WHERE role='student' AND owner=?",(student,))
        db.execute("DELETE FROM devices WHERE role='student' AND owner=?",(student,))


def _owned_student(db, token, student):
    professor = _identity(db, token)
    if professor['role']=='admin':
        row=db.execute('SELECT * FROM students WHERE id=?',(student,)).fetchone()
    elif professor['role']=='professor':
        row = db.execute('SELECT * FROM students WHERE id=? AND room=?', (student,professor['id'])).fetchone()
    else:
        raise PermissionError('Somente Professor ou Superadministrador.')
    if not row:
        raise PermissionError('Este aluno não pertence à sua sala.')
    return row


def update_student(token, student, name, chesscom=''):
    from chesscom import normalize_username
    if not name.strip():
        raise ValueError('Informe o nome do aluno.')
    chesscom = normalize_username(chesscom) if chesscom.strip() else ''
    with database() as db:
        _owned_student(db,token,student)
        db.execute('UPDATE students SET name=?,chesscom=? WHERE id=?', (name.strip()[:100],chesscom,student))


def assigned_lines(openings, count):
    from opening_repertoires import selected_courses
    courses = selected_courses(openings)
    if not isinstance(count,int) or not len(courses) <= count <= 128:
        raise ValueError('A meta de linhas deve incluir pelo menos uma linha por abertura (máximo 128).')
    # Round-robin keeps every selected opening represented.
    lines = [course['lines'][index] for index in range(max(len(c['lines']) for c in courses))
             for course in courses if index < len(course['lines'])]
    if count > len(lines):
        raise ValueError(f'Essas aberturas possuem {len(lines)} linhas disponíveis.')
    return lines[:count]


def save_routine(token, student, openings, lines, positions, tactics, minutes, weekdays, start):
    selected = assigned_lines(openings,lines)
    available = sum(len(range(0 if row['side']=='white' else 1,len(row['moves']),2)) for row in selected)
    if not 1 <= positions <= available or not 0 <= tactics <= 1000 or not 1 <= minutes <= 480:
        raise ValueError(f'Defina de 1 a {available} posições, de 0 a 1000 táticos e de 1 a 480 minutos.')
    if not weekdays or any(type(day)!=int or day not in range(7) for day in weekdays):
        raise ValueError('Selecione os dias de treino.')
    start = str(date.fromisoformat(str(start)))
    payload = dict(openings=openings,lines=lines,line_ids=[row['id'] for row in selected],
                   positions=positions,tactics=tactics,minutes=minutes,weekdays=sorted(set(weekdays)),start=start)
    with database() as db:
        row = _owned_student(db,token,student)
        if row['banned']:
            raise ValueError('A chave deste aluno foi revogada.')
        db.execute('INSERT INTO routines(student,day,payload) VALUES(?,?,?)', (student,str(today()),json.dumps(payload)))
    return payload


def _routine(db, student, day):
    row = db.execute('SELECT payload FROM routines WHERE student=? AND day<=? ORDER BY id DESC LIMIT 1', (student,day)).fetchone()
    return json.loads(row['payload']) if row else None


def routine(token, day=None):
    with database() as db:
        user = _identity(db,token,'student')
        return _routine(db,user['id'],str(day or today()))


def warn(token, student, reason):
    if not reason.strip():
        raise ValueError('Registre o motivo da advertência.')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = _owned_student(db,token,student)
        if row['banned']:
            raise ValueError('Aluno já banido da sala.')
        count = row['warnings']+1
        db.execute('INSERT INTO warnings(student,created,reason) VALUES(?,?,?)', (student,time.time(),reason.strip()))
        db.execute('UPDATE students SET warnings=?,banned=?,access_key=? WHERE id=?',
                   (count,int(count>=3),None if count>=3 else row['access_key'],student))
        if count>=3:
            db.execute("DELETE FROM sessions WHERE role='student' AND owner=?", (student,))
            db.execute("DELETE FROM devices WHERE role='student' AND owner=?", (student,))
        return count


def record(token, event_key, kind, correct=False, solved=False, line='', states=None):
    if kind not in ('opening','tactics','line'):
        raise ValueError('Atividade inválida.')
    with database() as db:
        user = _identity(db,token,'student')
        task = _routine(db,user['id'],str(today()))
        if not task or kind in ('opening','line') and line not in task['line_ids']:
            return
        db.execute('INSERT OR IGNORE INTO events(student,day,event_key,kind,correct,solved,line,states) VALUES(?,?,?,?,?,?,?,?)',
            (user['id'],str(today()),event_key,kind,int(correct),int(solved),line,json.dumps(states or {})))
        from classroom_sessions import synchronize
        synchronize(db,user['id'],time.time())


def pulse(token, active, now=None):
    """Credit only short, focused, active training intervals, never offline time."""
    now = time.time() if now is None else now
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user = _identity(db,token,'student')
        previous = db.execute('SELECT last_tick FROM presence WHERE student=?', (user['id'],)).fetchone()
        last = previous[0] if previous else None
        elapsed = now-last if last is not None else None
        seconds = min(15,max(0,elapsed)) if active and elapsed is not None and elapsed<=20 else 0
        db.execute('INSERT INTO presence VALUES(?,?) ON CONFLICT(student) DO UPDATE SET last_tick=excluded.last_tick',
                   (user['id'],now if active else None))
        db.execute('INSERT INTO training_time VALUES(?,?,?) ON CONFLICT(student,day) DO UPDATE SET seconds=seconds+excluded.seconds',
                   (user['id'],str(today(now)),seconds))


def _summary(db, student, day):
    task = _routine(db,student,day)
    events = list(db.execute('SELECT * FROM events WHERE student=? AND day=? ORDER BY id', (student,day)))
    statuses, done_lines, done_tactics = {}, set(), set()
    if task:
        for row in assigned_lines(task['openings'],task['lines']):
            for ply in range(0 if row['side']=='white' else 1,len(row['moves']),2):
                statuses[f"{row['id']}:{ply}"] = 'pending'
    for event in events:
        if task and event['line'] in task['line_ids']:
            if event['kind']=='line': done_lines.add(event['line'])
            for ply,status in json.loads(event['states']).items():
                key=f"{event['line']}:{ply}"
                if key in statuses and status in ('pending','wrong','unknown','correct'):
                    statuses[key]=status
        if event['kind']=='tactics' and event['solved']:
            done_tactics.add(event['line'])
    counts = {status:list(statuses.values()).count(status) for status in ('pending','wrong','unknown','correct')}
    accuracy = {}
    for kind in ('opening','tactics'):
        attempts=[e for e in events if e['kind']==kind]
        accuracy[kind]=100*sum(e['correct'] for e in attempts)/len(attempts) if attempts else None
    duration = db.execute('SELECT seconds FROM training_time WHERE student=? AND day=?',(student,day)).fetchone()
    seconds=duration[0] if duration else 0
    visits=list(db.execute('SELECT seconds,ended,completed FROM training_visits WHERE student=? AND day=?',(student,day)))
    seconds=max(seconds,sum(row['seconds'] for row in visits))
    scheduled = bool(task and day>=task['start'] and date.fromisoformat(day).weekday() in task['weekdays'])
    trail_complete=bool(task and len(done_lines)>=task['lines'] and counts['correct']>=task['positions'] and len(done_tactics)>=task['tactics'])
    fulfilled = bool(scheduled and trail_complete and seconds>=task['minutes']*60)
    status = 'Cumprida' if fulfilled else 'Falta / incompleta' if scheduled and day<str(today()) else 'Em andamento' if scheduled and events else 'Pendente' if scheduled else 'Sem treino previsto'
    if visits:status='Trilha concluída' if trail_complete else 'Presente · em treino' if any(row['ended'] is None for row in visits) else 'Presente · treino interrompido'
    return dict(day=day,routine=task,states=counts,lines=len(done_lines),tactics=len(done_tactics),
                seconds=seconds,accuracy=accuracy,scheduled=scheduled,fulfilled=fulfilled,status=status,trail_complete=trail_complete,present=bool(visits))


def dashboard(token, student=None, day=None):
    with database() as db:
        user = _identity(db,token)
        if user['role'] in ('professor','admin'):
            _owned_student(db,token,student)
        elif user['role']!='student':
            raise PermissionError('Abra a sala do Professor para consultar a rotina.')
        elif student not in (None,user['id']):
            raise PermissionError('Você só pode consultar seu próprio progresso.')
        else:
            student=user['id']
        result=_summary(db,student,str(day or today()))
        result['warnings']=[dict(row) for row in db.execute('SELECT created,reason FROM warnings WHERE student=? ORDER BY id', (student,))]
        return result


def attendance(token, student, days=30):
    with database() as db:
        _owned_student(db,token,student)
        return [_summary(db,student,str(today()-timedelta(days=offset))) for offset in range(min(days,366))]


def bootstrap_owner(name,password):
    """Local creator setup only. Never exposed by the web signup interface."""
    name=name.strip().lower()
    if not 2<=len(name)<=50 or len(password)<8:
        raise ValueError('Use um nome com 2 a 50 caracteres e uma senha com pelo menos 8 caracteres.')
    salt=secrets.token_hex(16);identifier=secrets.token_hex(16)
    encoded=pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),260000).hex()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM administrators').fetchone():
            raise ValueError('O Superadministrador já foi configurado. Entre com sua conta existente.')
        db.execute('INSERT INTO administrators VALUES(?,?,?,?)',(identifier,name,salt,encoded))
        return _session(db,'admin',identifier)


def login_owner(name,password):
    with database() as db:
        row=db.execute('SELECT * FROM administrators WHERE name=?',(name.strip().lower(),)).fetchone()
        salt=bytes.fromhex(row['salt']) if row else bytes(16)
        encoded=pbkdf2_hmac('sha256',password.encode(),salt,260000).hex()
        if not row or not compare_digest(encoded,row['password']):
            raise ValueError('Usuário ou senha inválidos.')
        return _session(db,'admin',row['id'])


def issue_professor_key(token,label='',professor=None):
    key=secrets.token_urlsafe(32)
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        _identity(db,token,'admin')
        label=label.strip() or f"Chave {db.execute('SELECT COUNT(*) FROM professor_invites').fetchone()[0]+1:03d}"
        if professor:
            if not db.execute('SELECT 1 FROM professors WHERE id=?',(professor,)).fetchone():
                raise ValueError('Professor não encontrado.')
            db.execute('UPDATE professor_invites SET revoked=1 WHERE used_by=?',(professor,))
            _revoke_room_sessions(db,professor)
            db.execute('UPDATE professors SET approved=1 WHERE id=?',(professor,))
        db.execute('INSERT INTO professor_invites(id,key_hash,label,created,used_by) VALUES(?,?,?,?,?)',
            (secrets.token_hex(16),_digest(key),label.strip()[:100],time.time(),professor))
    return key


def admin_overview(token):
    with database() as db:
        _identity(db,token,'admin')
        professors=[dict(row) for row in db.execute('SELECT id,name,approved FROM professors ORDER BY name')]
        invitations=[dict(row) for row in db.execute('SELECT id,label,created,revoked,used_by FROM professor_invites WHERE deleted=0 ORDER BY created DESC')]
        for invite in invitations:
            invite['expires_at']=invite['created']+PROFESSOR_KEY_TTL
            invite['expired']=not invite['used_by'] and invite['expires_at']<=time.time()
        users=[dict(row) for row in db.execute("SELECT users.id,users.name,students.name AS aluno,COALESCE(professors.name,administrators.name) AS professor,COALESCE(account_access.status,'active') AS status,account_access.created,account_access.last_login,account_access.last_seen FROM users LEFT JOIN account_access ON account_access.owner=users.id LEFT JOIN memberships ON memberships.owner=users.id LEFT JOIN students ON students.id=memberships.student LEFT JOIN professors ON professors.id=students.room LEFT JOIN administrators ON administrators.id=students.room ORDER BY users.name")]
        return dict(professors=professors,invitations=invitations,users=users)


def set_user_access(token,identifier,allowed):
    """Creator-only authorization; revoke user and linked classroom sessions."""
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        _identity(db,token,'admin')
        if not db.execute('SELECT 1 FROM users WHERE id=?',(identifier,)).fetchone():
            raise ValueError('Usuário não encontrado.')
        db.execute('INSERT INTO account_access(owner,status) VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET status=excluded.status',
                   (identifier,'active' if allowed else 'blocked'))
        owners=[identifier]+[row['student'] for row in db.execute('SELECT student FROM memberships WHERE owner=?',(identifier,))]
        for owner in owners:
            db.execute('DELETE FROM sessions WHERE owner=?',(owner,))
            db.execute('DELETE FROM devices WHERE owner=?',(owner,))


def delete_user(token,identifier):
    """Remove a player login and revoke devices, retaining training history."""
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        _identity(db,token,'admin')
        account=db.execute('SELECT name FROM users WHERE id=?',(identifier,)).fetchone()
        if not account:
            raise ValueError('Usuário não encontrado. A conta do criador não pode ser excluída aqui.')
        students=[row['student'] for row in db.execute('SELECT student FROM memberships WHERE owner=?',(identifier,))]
        for owner in [identifier]+students:
            db.execute('DELETE FROM sessions WHERE owner=?',(owner,))
            db.execute('DELETE FROM devices WHERE owner=?',(owner,))
        for student in students:
            db.execute('UPDATE students SET access_key=? WHERE id=?',(secrets.token_urlsafe(24),student))
        db.execute('DELETE FROM memberships WHERE owner=?',(identifier,))
        db.execute("DELETE FROM profile_photos WHERE role='user' AND owner=?",(identifier,))
        db.execute("DELETE FROM account_chesscom WHERE role='user' AND owner=?",(identifier,))
        db.execute('DELETE FROM account_access WHERE owner=?',(identifier,))
        db.execute('DELETE FROM users WHERE id=?',(identifier,))


def revoke_professor_key(token,identifier):
    with database() as db:
        _identity(db,token,'admin')
        row=db.execute('SELECT used_by FROM professor_invites WHERE id=?',(identifier,)).fetchone()
        if not row:raise ValueError('Chave não encontrada.')
        db.execute('UPDATE professor_invites SET revoked=1 WHERE id=?',(identifier,))
        if row['used_by']:_revoke_room_sessions(db,row['used_by'])


def delete_professor_key(token,identifier):
    """Remove a key from the manager and invalidate it, keeping its audit record."""
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        _identity(db,token,'admin')
        row=db.execute('SELECT used_by FROM professor_invites WHERE id=? AND deleted=0',(identifier,)).fetchone()
        if not row:raise ValueError('Chave não encontrada.')
        db.execute('UPDATE professor_invites SET revoked=1,deleted=1 WHERE id=?',(identifier,))
        if row['used_by']:_revoke_room_sessions(db,row['used_by'])


def _revoke_room_sessions(db,professor):
    owners=[professor]+[row['id'] for row in db.execute('SELECT id FROM students WHERE room=?',(professor,))]
    for owner in owners:
        db.execute('DELETE FROM sessions WHERE owner=?',(owner,))
        db.execute('DELETE FROM devices WHERE owner=?',(owner,))


def set_professor_access(token,professor,approved):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        _identity(db,token,'admin')
        if not db.execute('SELECT id FROM professors WHERE id=?',(professor,)).fetchone():
            raise ValueError('Professor não encontrado.')
        db.execute('UPDATE professors SET approved=? WHERE id=?',(int(bool(approved)),professor))
        _revoke_room_sessions(db,professor)


def remember_device(token):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user=_identity(db,token)
        device=secrets.token_urlsafe(40)
        # Revoked explicitly on logout/blocking; no periodic password prompt.
        db.execute('INSERT INTO devices VALUES(?,?,?,?)',(_digest(device),user['role'],user['id'],253402300799))
        return device


def restore_device(device):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM devices WHERE token=? AND expires>?',(_digest(device or ''),time.time())).fetchone()
        if not row:return None
        try:_account(db,row['role'],row['owner'])
        except PermissionError:return None
        db.execute('UPDATE devices SET expires=? WHERE token=?',(253402300799,row['token']))
        return _session(db,row['role'],row['owner'])


def forget_device(device):
    with database() as db:
        db.execute('DELETE FROM devices WHERE token=?',(_digest(device or ''),))


def revoke_remembered_access(token):
    with database() as db:
        user=_identity(db,token)
        db.execute('DELETE FROM devices WHERE owner=?',(user['id'],))
