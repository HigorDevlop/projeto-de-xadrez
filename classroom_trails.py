"""Persistent teacher drafts, atomic publication and server-enforced trail gates."""
import json
import secrets
import time
import classroom as rooms
import classroom_materials as materials


def tables(db):
    materials.tables(db)
    db.execute("CREATE TABLE IF NOT EXISTS lesson_trail_drafts(student TEXT PRIMARY KEY,room TEXT,payload TEXT,revision INTEGER NOT NULL DEFAULT 0)")
    db.execute('CREATE TABLE IF NOT EXISTS lesson_trail_titles(student TEXT PRIMARY KEY,title TEXT)')


def _draft(db,token,student):
    seat=rooms._owned_student(db,token,student)
    row=db.execute('SELECT payload,revision FROM lesson_trail_drafts WHERE student=?',(student,)).fetchone()
    if row:return seat,json.loads(row['payload']),row['revision']
    from classroom_schedule import releases
    schedule=releases(db)
    steps=[]
    for step in db.execute('SELECT * FROM lesson_trail_steps WHERE student=? ORDER BY position',(student,)).fetchall():
        items=[]
        for item in db.execute('SELECT m.* FROM lesson_trail_items i JOIN lesson_materials m ON m.id=i.material WHERE i.step=? ORDER BY i.position',(step['id'],)).fetchall():
            items.append(dict(id=item['id'],title=item['title'],kind=item['kind'],payload=json.loads(item['payload']),reviewed=True))
        note=db.execute('SELECT notes FROM lesson_trail_notes WHERE step=?',(step['id'],)).fetchone()
        steps.append(dict(id=step['id'],title=step['title'],locked=bool(step['locked']),release_at=schedule.get(step['id']),notes=note['notes'] if note else '',items=items))
    title=db.execute('SELECT title FROM lesson_trail_titles WHERE student=?',(student,)).fetchone()
    return seat,dict(title=title['title'] if title else 'Minha trilha',steps=steps),0


def load_draft(token,student):
    with rooms.database() as db:
        tables(db);_,draft,revision=_draft(db,token,student)
        return dict(draft,revision=revision)


def video_catalog(token,student):
    import classroom_community as community
    with rooms.database() as db:seat=rooms._owned_student(db,token,student)
    return seat['room'],community.videos(token,seat['room'])


def _title(value):
    if not isinstance(value,str) or not value.strip() or len(value)>150:raise ValueError('Use um nome de 1 a 150 caracteres.')
    return value.strip()


def _check_video(db,payload,room):
    if not db.execute("SELECT 1 FROM room_videos WHERE id=? AND room=?",(payload['video_id'],room)).fetchone():
        raise PermissionError('Este vídeo não pertence à sala selecionada.')


def edit_draft(token,student,revision,event,candidates=()):
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE');seat,draft,current=_draft(db,token,student)
        if current!=revision:raise ValueError('A montagem mudou. Confira a versão atual e tente novamente.')
        action=event.get('action');steps=draft['steps']
        step=next((s for s in steps if s['id']==event.get('step')),None)
        if action in ('create_step','add_event'):
            if event.get('step') and step is None:raise ValueError('Linha não encontrada.')
            if step is None:
                if len(steps)>=50:raise ValueError('A trilha aceita até 50 linhas.')
                step=dict(id=secrets.token_hex(16),title='Linha '+str(len(steps)+1),notes='',locked=False,items=[]);steps.append(step)
            if action=='add_event':
                kind=event.get('kind')
                if kind not in materials.KINDS:raise ValueError('Escolha um tipo de atividade válido.')
                if len(step['items'])>=60 or sum(len(s['items']) for s in steps)>=200:raise ValueError('Limite de atividades da trilha atingido.')
                labels=dict(line='Linha de treino',tactic='Tático',game='Partida estudada',exam='Desafio',video='Vídeo',note='Anotação')
                step['items'].append(dict(id=secrets.token_hex(16),title=labels[kind],kind=kind,payload={},reviewed=False))
        elif action=='update_step':
            if step is None:raise ValueError('Linha não encontrada.')
            notes=event.get('notes','')
            if not isinstance(notes,str) or len(notes)>10000:raise ValueError('Use até 10 mil caracteres nas anotações.')
            step.update(title=_title(event.get('title')),notes=notes)
        elif action in ('save_item','item_order'):
            if step is None:raise ValueError('Linha não encontrada.')
            if action=='item_order':
                order=event.get('order')
                if not isinstance(order,list) or any(not isinstance(k,str) for k in order) or len(order)!=len(step['items']) or set(order)!={item['id'] for item in step['items']}:raise ValueError('Ordem de atividades inválida.')
                step['items']=[next(item for item in step['items'] if item['id']==identifier) for identifier in order]
            else:
                item=next((item for item in step['items'] if item['id']==event.get('item')),None)
                if item is None:raise ValueError('Atividade não encontrada.')
                if event.get('reviewed') is not True:raise ValueError('Revise a atividade antes de salvar.')
                payload=materials.validate(item['kind'],event.get('payload'))
                if item['kind']=='line' and payload.get('continuation'):
                    from classroom_line_segments import previous_line,segment
                    before=previous_line(draft,step['id'],item['id'])
                    if not before:raise ValueError('Configure e salve uma linha anterior antes de criar a continuação.')
                    segment(payload['source_pgn'],payload['start_ply'],payload['move_count'],payload['side'],previous=before['payload'])
                if item['kind']=='video':_check_video(db,payload,seat['room'])
                title=_title(event.get('title'))
                previous=db.execute('SELECT payload FROM lesson_materials WHERE id=?',(item['id'],)).fetchone()
                if previous and json.loads(previous['payload'])!=payload:item['id']=secrets.token_hex(16)
                item.update(title=title,payload=payload,reviewed=True)
        elif action=='add':
            if not candidates or len(candidates)>50:raise ValueError('Revise um conteúdo antes de adicionar.')
            items=[]
            for candidate in candidates:
                if candidate.get('reviewed') is not True:raise ValueError('Marque o conteúdo como revisado antes de adicionar.')
                payload=materials.validate(candidate['kind'],candidate['payload'])
                if candidate['kind']=='video':_check_video(db,payload,seat['room'])
                items.append(dict(id=secrets.token_hex(16),title=_title(candidate['title']),kind=candidate['kind'],payload=payload,reviewed=True))
            if event.get('step') and step is None:raise ValueError('Etapa não encontrada.')
            if step is None:
                if len(steps)>=50:raise ValueError('A trilha aceita até 50 etapas.')
                step=dict(id=secrets.token_hex(16),title=items[0]['title'],locked=False,items=[]);steps.append(step)
            if len(step['items'])+len(items)>60 or sum(len(s['items']) for s in steps)+len(items)>200:
                raise ValueError('Use até 60 atividades por etapa e 200 por trilha.')
            step['items'].extend(items)
        elif action=='title':draft['title']=_title(event.get('title'))
        elif action=='order':
            order=event.get('order')
            if not isinstance(order,list) or any(not isinstance(identifier,str) for identifier in order) or len(order)!=len(steps) or set(order)!={s['id'] for s in steps}:raise ValueError('Ordem de etapas inválida.')
            draft['steps']=[next(s for s in steps if s['id']==identifier) for identifier in order]
        elif action in ('rename','lock','remove','remove_item'):
            if step is None:raise ValueError('Etapa não encontrada.')
            if action=='rename':step['title']=_title(event.get('title'))
            elif action=='lock':
                from classroom_schedule import release_time
                step['locked']=event.get('locked',not step['locked'])
                if type(step['locked']) is not bool:raise ValueError('Bloqueio inválido.')
                step['release_at']=release_time(event.get('release_at')) if step['locked'] else None
                db.execute('DELETE FROM lesson_trail_schedule WHERE step=?',(step['id'],))
                if step['release_at'] is not None:db.execute('INSERT INTO lesson_trail_schedule VALUES(?,?)',(step['id'],step['release_at']))
                db.execute('UPDATE lesson_trail_steps SET locked=? WHERE id=? AND student=?',(int(step['locked']),step['id'],student))
            elif action=='remove':draft['steps']=[s for s in steps if s['id']!=step['id']]
            else:
                step['items']=[item for item in step['items'] if item['id']!=event.get('item')]
        else:raise ValueError('Ação desconhecida.')
        current+=1
        db.execute('INSERT INTO lesson_trail_drafts VALUES(?,?,?,?) ON CONFLICT(student) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',
                   (student,seat['room'],json.dumps(draft),current))
        return dict(draft,revision=current)


def publish(token,student,revision):
    with rooms.database() as db:
        tables(db);db.execute('BEGIN IMMEDIATE');seat,draft,current=_draft(db,token,student)
        if current!=revision:raise ValueError('A montagem mudou. Confira antes de disponibilizar.')
        if seat['banned']:raise ValueError('Reative a vaga antes de disponibilizar a trilha.')
        if not draft['steps'] or any(not s['items'] for s in draft['steps']):raise ValueError('Adicione ao menos uma atividade em cada etapa.')
        for step in draft['steps']:
            if any(item.get('reviewed') is not True for item in step['items']):raise ValueError('Abra '+step['title']+' e revise as atividades pendentes antes de disponibilizar.')
            for item in step['items']:
                if item['kind']=='line' and item['payload'].get('continuation'):
                    from classroom_line_segments import previous_line,segment
                    before=previous_line(draft,step['id'],item['id'])
                    if not before:raise ValueError('A continuação precisa vir depois de sua linha anterior.')
                    payload=item['payload']
                    segment(payload['source_pgn'],payload['start_ply'],payload['move_count'],payload['side'],previous=before['payload'])
        from classroom_training_sessions import archive_before_publish
        archive_before_publish(db,student)
        db.execute('INSERT INTO lesson_trail_titles VALUES(?,?) ON CONFLICT(student) DO UPDATE SET title=excluded.title',(student,draft['title']))
        old=[row['material'] for row in db.execute('SELECT i.material FROM lesson_trail_items i JOIN lesson_trail_steps s ON s.id=i.step WHERE s.student=?',(student,))]
        for identifier in old:db.execute('UPDATE lesson_materials SET published=0 WHERE id=?',(identifier,))
        db.execute('DELETE FROM lesson_trail_notes WHERE step IN (SELECT id FROM lesson_trail_steps WHERE student=?)',(student,))
        db.execute('DELETE FROM lesson_trail_items WHERE step IN (SELECT id FROM lesson_trail_steps WHERE student=?)',(student,))
        db.execute('DELETE FROM lesson_trail_schedule WHERE step IN (SELECT id FROM lesson_trail_steps WHERE student=?)',(student,))
        db.execute('DELETE FROM lesson_trail_steps WHERE student=?',(student,))
        count=0
        for index,step in enumerate(draft['steps']):
            db.execute('INSERT INTO lesson_trail_steps VALUES(?,?,?,?,?,?)',(step['id'],student,seat['room'],step['title'],index,int(step['locked'])))
            if step.get('release_at') is not None:
                db.execute('INSERT OR REPLACE INTO lesson_trail_schedule VALUES(?,?)',(step['id'],step['release_at']))
            db.execute('INSERT INTO lesson_trail_notes VALUES(?,?)',(step['id'],step.get('notes','')))
            for position,item in enumerate(step['items']):
                if item.get('reviewed') is not True:raise ValueError('Revise todas as atividades.')
                payload=materials.validate(item['kind'],item['payload'])
                if item['kind']=='video':_check_video(db,payload,seat['room'])
                previous=db.execute('SELECT student,kind,payload FROM lesson_materials WHERE id=?',(item['id'],)).fetchone()
                if previous and (previous['student']!=student or previous['kind']!=item['kind'] or json.loads(previous['payload'])!=payload):
                    raise ValueError('O conteúdo publicado foi alterado. Adicione uma nova atividade para preservar as respostas anteriores.')
                db.execute('INSERT INTO lesson_materials VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,published=1',
                    (item['id'],student,seat['room'],item['title'],item['kind'],json.dumps(payload),1,time.time()))
                db.execute('INSERT INTO lesson_trail_items VALUES(?,?,?)',(item['id'],step['id'],position));count+=1
                db.execute('INSERT OR IGNORE INTO lesson_trail_history VALUES(?,?)',(item['id'],student))
        return count


def student_trail(token):
    with rooms.database() as db:
        tables(db);actor=rooms._identity(db,token)
        if actor['role']!='student':raise PermissionError('Abra sua sala com a chave do Professor.')
        from classroom_tactic_blocks import activity_blocks
        access=activity_blocks(db,actor['id'])
        from classroom_schedule import releases,is_locked
        schedule=releases(db)
        result=[];blocked=False
        rows=db.execute('SELECT * FROM lesson_trail_steps s WHERE student=? AND room=? AND EXISTS (SELECT 1 FROM lesson_trail_items i JOIN lesson_materials m ON m.id=i.material WHERE i.step=s.id AND m.published=1) ORDER BY position',(actor['id'],actor['room'])).fetchall()
        for row in rows:
            locked=is_locked(row['locked'],schedule.get(row['id']))
            blocked=blocked or locked
            items=[r['material'] for r in db.execute('SELECT material FROM lesson_trail_items WHERE step=? ORDER BY position',(row['id'],))]
            accessible=[identifier for identifier in items if identifier in access and not access[identifier]] if not blocked else []
            gated=not blocked and bool(items) and not accessible
            notes=db.execute('SELECT notes FROM lesson_trail_notes WHERE step=?',(row['id'],)).fetchone()
            result.append(dict(id=row['id'],title=row['title'],locked=locked,release_at=schedule.get(row['id']),blocked=blocked or gated,reason='tactics' if gated else 'teacher' if blocked else '',notes='' if blocked or gated or not notes else notes['notes'],materials=accessible))
        return result
