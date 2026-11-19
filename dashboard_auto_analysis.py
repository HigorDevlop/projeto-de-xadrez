"""Persistent per-side quality reports and a newest-first automatic review queue."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import heapq
import json
import os
from pathlib import Path
import subprocess
from threading import Event,Lock
import time

import chess
import chess.engine
import streamlit as st


def _path(key,side):
    from performance_dashboard import _quality_path
    return _quality_path(key).parent/'quality'/f'{key}-{side}.json'


def load(key,side):
    from chess_review import CATEGORIES
    try:
        report=json.loads(_path(key,side).read_text(encoding='utf-8'))
        if (report.get('version')==1 and report.get('complete') is True
                and all(type(report['counts'][name]) is int and report['counts'][name]>=0 for name in CATEGORIES)
                and sum(report['counts'].values())==report['moves']):return report
    except (OSError,ValueError,KeyError,TypeError):pass
    return None


def individual_counts(key,side):
    from performance_dashboard import _quality_path
    from chess_review import CATEGORIES
    try:
        report=json.loads(_quality_path(key).read_text(encoding='utf-8'))
        if report.get('version')!=1:return None
        label='Brancas' if side=='white' else 'Pretas'
        counts={name:report['counts'][name][label] for name in CATEGORIES}
        if all(type(value) is int and value>=0 for value in counts.values()) and sum(counts.values()):return counts
    except (OSError,ValueError,KeyError,TypeError):pass
    return None


def expected_moves(record):
    board=record['game'].board();side=record['side']=='white'
    first=board.turn==side
    return sum((index%2==0)==first for index,_ in enumerate(record['game'].mainline_moves()))


def ready(record):
    from performance_dashboard import quality_key
    key=quality_key(record['game']);side=record['side'];expected=expected_moves(record)
    individual=individual_counts(key,side)
    if individual and sum(individual.values())==expected:return True
    saved=load(key,side)
    return bool(saved and saved['moves']==expected)


def analyze(record,engine_path,cancel=None,progress=None):
    """Classify every player's move with the same root comparison as manual review."""
    from tempfile import NamedTemporaryFile
    from performance_dashboard import quality_key
    from chess_review import CATEGORIES,classify,sacrifice_in_line
    from stockfish_analysis import _ENGINE_LOCK,check_cancelled,compare_move,review_chances
    import game_phase_diagnostics as diagnostics
    if ready(record):return
    cancel=cancel or Event();progress=progress or (lambda *_:None)
    board=record['game'].board();moves=list(record['game'].mainline_moves())
    counts=Counter(dict.fromkeys(CATEGORIES, 0));rows=[];done=0;total=expected_moves(record)
    limit=chess.engine.Limit(depth=16,time=.08)
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    while not _ENGINE_LOCK.acquire(timeout=.1):check_cancelled(cancel)
    try:
        if ready(record):return
        with chess.engine.SimpleEngine.popen_uci(engine_path,timeout=15,**kwargs) as engine:
            engine.configure({k:v for k,v in {'Threads':1,'Hash':64}.items() if k in engine.options})
            for ply,move in enumerate(moves,1):
                check_cancelled(cancel)
                if board.turn==(record['side']=='white'):
                    best,played,second=compare_move(engine,board,move,limit,cancel)
                    best_move=best['pv'][0]
                    played_expected=review_chances(played,board.turn)
                    best_expected=max(played_expected,review_chances(best,board.turn))
                    loss=max(0,best_expected-played_expected)
                    category=classify(in_book=False,is_best=best_move==move,
                        sacrifice=sacrifice_in_line(board,played.get('pv',[move])),
                        best_expected=best_expected,played_expected=played_expected,second_expected=second)
                    counts[category]+=1
                    cp=max(0,best['score'].pov(board.turn).score(mate_score=100000)-played['score'].pov(board.turn).score(mate_score=100000))
                    rows.append(dict(ply=ply,number=board.fullmove_number,san=board.san(move),phase=diagnostics.phase(board),
                        category=category,loss_cp=cp,loss_chances=loss,best_san=board.san(best_move),fen=board.fen()))
                    done+=1;progress(done,total)
                board.push(move)
            check_cancelled(cancel)
            key=quality_key(record['game']);side=record['side'];path=_path(key,side)
            path.parent.mkdir(parents=True,exist_ok=True)
            report=dict(version=1,complete=True,moves=done,counts=dict(counts),engine=engine.id.get('name','Stockfish'),
                        method='Comparação MultiPV · profundidade 16, verificação até 18',created=time.time())
            with NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as out:
                temporary=Path(out.name);json.dump(report,out,ensure_ascii=False)
            try:temporary.replace(path)
            finally:temporary.unlink(missing_ok=True)
            existing=diagnostics.load(key,side)
            if not existing or existing.get('method')!='Análise individual completa':
                diagnostics.save(key,side,dict(complete=True,rows=rows,engine=report['engine'],created=report['created'],
                    method='Classificação automática MultiPV · mesmos critérios da análise individual'))
    finally:_ENGINE_LOCK.release()


class AnalysisQueue:
    def __init__(self,analyzer=analyze,clock=time.monotonic):
        self.analyzer=analyzer;self.clock=clock;self.lock=Lock()
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='automatic-game-review')
        self.pending=[];self.jobs={};self.running=False;self.serial=0

    def submit(self,records,engine_path):
        from performance_dashboard import quality_key
        for record in records:
            if ready(record):continue
            key=(str(_path(quality_key(record['game']),record['side'])),record['side'])
            with self.lock:
                previous=self.jobs.get(key)
                if previous and (previous['status'] in ('queued','running') or previous.get('retry_at',0)>self.clock()):continue
                job=dict(status='queued',done=0,total=expected_moves(record),error=None,retry_at=0)
                self.jobs[key]=job;self.serial+=1
                heapq.heappush(self.pending,(-record['timestamp'],self.serial,key,record,engine_path))
                if not self.running:
                    self.running=True;self.executor.submit(self._run)

    def _run(self):
        while True:
            with self.lock:
                if not self.pending:
                    self.running=False
                    for key in [key for key,job in self.jobs.items() if job['status']=='done']:self.jobs.pop(key,None)
                    return
                _,_,key,record,engine=heapq.heappop(self.pending);job=self.jobs[key];job['status']='running'
            try:
                self.analyzer(record,engine,progress=lambda done,total,job=job:job.update(done=done,total=total))
                job['status']='done'
            except Exception as error:
                job.update(status='error',error=str(error),retry_at=self.clock()+120)

    def status(self,records):
        from performance_dashboard import quality_key
        keys={str(_path(quality_key(record['game']),record['side'])) for record in records}
        with self.lock:
            jobs=[dict(job) for key,job in self.jobs.items() if key[0] in keys]
        return dict(queued=sum(job['status']=='queued' for job in jobs),
            current=next((job for job in jobs if job['status']=='running'),None),
            errors=[job['error'] for job in jobs if job['status']=='error'])


@st.cache_resource
def queue():return AnalysisQueue()


@st.cache_data(ttl=30,max_entries=16,show_spinner=False)
def records_for(history,username,end,days=7):
    from game_phase_diagnostics import window
    return window(history,username,end,days)


def ensure(history,username,days=7):
    from preparation_state import today
    from stockfish_analysis import find_engine
    records=records_for(history,username,today(),days)
    engine=find_engine()
    if engine:queue().submit(records,engine)
    return records
