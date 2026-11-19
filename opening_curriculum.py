"""Up to five branches, each with progressively deeper continuations."""
from hashlib import sha256


def build_curriculum(course):
    prefix = course['family_prefix']
    paths = [line for line in course['lines'] if line['moves'][:len(prefix)]==prefix]
    side = course['side']
    roots, seen = [], set()
    target_length=9 if side=='white' else 10
    candidates=sorted(paths,key=lambda line:len(line['moves'])<target_length)
    for line in candidates:
        length = min(len(line['moves']),9 if side=='white' else 10)
        if length % 2 == (0 if side=='white' else 1):
            length -= 1
        moves = line['moves'][:length]
        if len(moves)<target_length and any(root[:len(moves)]==moves for root,_ in roots):
            continue
        if tuple(moves) in seen or len(moves)<len(prefix):
            continue
        seen.add(tuple(moves))
        roots.append((moves,line))
        if len(roots)==5:
            break
    result=[]
    def append(moves, source, branch, stage, context=0):
        identifier=course['id']+'-'+sha256(' '.join(moves).encode()).hexdigest()[:12]
        if any(line['id']==identifier for line in result):
            return
        result.append(dict(source,id=identifier,moves=list(moves),opening=course['title'],
            family_prefix=list(prefix),branch=branch,stage=stage,context_plies=context,
            lesson_moves=5 if stage=='foundation' else (len(moves)+1)//2,
            needs_preparation=stage=='foundation' and len(moves)<(9 if side=='white' else 10),
            variation=f'Linha {branch} · '+('5 lances · Fundamentos' if stage=='foundation' else f'{(len(moves)+1)//2} lances · Aprofundamento')))
        result[-1].pop('context_plies',None)
    for branch,(moves,source) in enumerate(roots,1):
        append(moves,source,branch,'foundation')
    for branch,(root,_source) in enumerate(roots,1):
        continuations=[line for line in paths if line['moves'][:len(root)]==root]
        staged={}
        for line in continuations:
            for length in range((13 if side=='white' else 14),len(line['moves'])+1,4):
                moves=line['moves'][:length]
                staged.setdefault(tuple(moves),line)
        for moves,line in sorted(staged.items(),key=lambda item:(len(item[0]),item[0])):
            # Retain the full line so each round repeats it from the start.
            append(list(moves),line,branch,'depth')
    course.update(lines=result,foundation_count=len(roots),curriculum_version=3)
    return course
