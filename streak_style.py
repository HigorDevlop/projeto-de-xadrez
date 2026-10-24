"""Consecutive authenticated login days and six original monochrome-path flames."""
from datetime import timedelta
import classroom as rooms
from preparation_state import today


def login_streak(token,record=False,day=None):
    day=day or today()
    with rooms.database() as db:
        actor=rooms._identity(db,token)
        if record:db.execute('INSERT OR IGNORE INTO login_days VALUES(?,?,?)',(actor['role'],actor['id'],str(day)))
        days={row[0] for row in db.execute('SELECT day FROM login_days WHERE role=? AND owner=?',(actor['role'],actor['id']))}
    cursor=day if str(day) in days else day-timedelta(days=1)
    count=0
    while str(cursor) in days:count+=1;cursor-=timedelta(days=1)
    return count


def flame(days):
    tier=min(5,max(0,int(days))//10)
    colors=[('#ffb146','#ed492e'),('#ffd460','#ff7625'),('#68edff','#287cf2'),('#db9dff','#8444ec'),('#e4fff9','#39cdb3'),('#fff3ad','#e6ad2e')]
    paths=[
        'M50 7C69 37 26 38 41 61C20 50 17 80 28 96C39 116 77 110 82 85C88 61 67 40 50 7Z',
        'M55 5C79 32 60 41 70 58L83 43C106 81 75 117 45 109C11 103 4 72 28 44L34 67C53 52 36 32 55 5Z',
        'M51 3L68 43L83 29L79 60L96 66L78 100L51 115L23 102L7 75L25 62L21 38L39 52Z',
        'M50 2C77 29 50 43 73 55L84 35C109 86 81 111 50 116C14 110 1 84 17 52L32 70C49 54 28 31 50 2Z',
        'M50 1L62 30L76 20L73 46L94 44L80 67L96 80L72 107L50 118L23 107L5 80L20 65L7 43L29 46L25 20L40 31Z',
        'M50 0L63 27L83 14L78 45L99 34L87 71L94 89L74 110L50 120L25 110L6 89L13 71L1 34L22 45L17 14L37 27Z']
    a,b=colors[tier]
    return f'<svg viewBox="0 0 100 124" role="img" aria-label="Chama nível {tier}, {days} dias"><defs><linearGradient id="streak-{tier}" x2="0" y2="1"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs><path d="{paths[tier]}" fill="url(#streak-{tier})"/><path d="M50 55C67 76 70 90 50 103C29 93 35 76 50 55Z" fill="white" opacity=".75"/></svg>'
