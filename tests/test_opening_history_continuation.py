from copy import deepcopy
import chess
import chess.pgn
import opening_levels as levels


def record(text,white="alice",black="bob",url="one"):
    board=chess.Board();game=chess.pgn.Game();node=game
    game.headers.update(White=white,Black=black)
    for token in text.split():
        move=board.parse_san(token);node=node.add_variation(move);board.push(move)
    return dict(pgn=str(game),url=url,white={"username":white},black={"username":black})


def source_line():
    board=chess.Board();moves=[]
    for token in "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3".split():
        move=board.parse_san(token);moves.append(move.uci());board.push(move)
    return dict(id="italian-original",moves=moves,side="white",family_prefix=moves[:5],
                branch=1,lesson_moves=5,stage="foundation",course_id="italian")


def test_replies_only_include_the_selected_family_and_player_side():
    source=source_line();text="e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O"
    games=[record(text,url=str(i)) for i in range(3)]
    games += [record("e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 O-O",url="other"),
              record("e4 e6 d4 d5 Nc3",url="french"),record(text,white="bob",black="alice",url="side")]
    board=chess.Board()
    for move in source["moves"]:board.push_uci(move)
    replies=levels.historical_replies(games,"alice",source)
    assert replies[board.epd()]=={"d7d6":3,"e8g8":1}
    assert chess.Board().epd() not in replies


def test_preparation_uses_frequent_opponent_reply_without_mutating_trail(monkeypatch):
    source=source_line();plan=dict(repertoire_ids=["italian"],personal_lines=[source],phase_results={"1":{"completed":True}})
    before=deepcopy(plan)
    monkeypatch.setattr(levels,"find_engine",lambda:"test-engine")
    class Engine:
        id={"name":"Fixture engine"}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def configure(self,options):pass
        def analyse(self,board,limit):return {"pv":[next(iter(board.legal_moves))]}
    monkeypatch.setattr(levels,"analyse_options",lambda engine,board,limit:([{ "info":{"pv":[next(iter(board.legal_moves))]} }],None))
    games=[record("e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O",url=str(i)) for i in range(3)]
    result=levels.prepare_level(plan,source,7,engine_factory=lambda *a,**k:Engine(),history_games=games,account="alice")
    assert result["moves"][:9]==source["moves"]
    assert result["moves"][9]=="d7d6"
    assert result["history_reply_count"]>=1
    assert result["branch"]==1 and result["lesson_moves"]==7
    assert plan==before
