"""Session difficulty grows from clean, distinct solutions, entirely offline."""


def target_rating(state):
    hits=state.get('tactic_difficulty_hits',0) if hasattr(state,'get') else getattr(state,'tactic_difficulty_hits',0)
    return min(3000,500+100*(hits//2))


def completed(state,puzzle,clean):
    seen=state.setdefault('tactic_difficulty_seen',set())
    if clean and puzzle not in seen:
        seen.add(puzzle)
        state['tactic_difficulty_hits']=state.get('tactic_difficulty_hits',0)+1


def training_range(theme,minimum,maximum,excluded,target):
    """Use the nearest available rating band, including sparse offline themes."""
    from offline_tactics import _bank,bank_path,LocalBankExhausted
    path=bank_path();puzzles,index=_bank(str(path),path.stat().st_mtime_ns)
    ratings=[puzzles[i].rating for i in index[theme]
             if minimum<=puzzles[i].rating<=maximum and puzzles[i].id not in excluded]
    if not ratings:
        raise LocalBankExhausted(sum(minimum<=puzzles[i].rating<=maximum for i in index[theme]))
    center=min(ratings,key=lambda rating:(abs(rating-target),rating))
    return max(minimum,center-100),min(maximum,center+150)
