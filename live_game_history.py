"""Merge a live game feed without moving the selected analysis game."""


def identity(game):
    return game.get('url') or game.get('uuid') or game.get('pgn')


def merge(existing, incoming, selected=None, limit=200):
    selected_id=identity(existing[selected]) if type(selected) is int and 0<=selected<len(existing) else None
    games={identity(game):game for game in existing}
    games.update({identity(game):game for game in incoming if identity(game) and game.get('pgn')})
    result=sorted(games.values(),key=lambda game:game.get('end_time',0),reverse=True)
    if limit is not None:result=result[:limit]
    index=next((i for i,game in enumerate(result) if identity(game)==selected_id),None) if selected_id else None
    return result,index
