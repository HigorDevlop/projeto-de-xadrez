"""Shared visibility and route authorization for each authenticated profile."""
COMMON_PAGES=('Partida','Análise','Tático','Estudo com livros','Aberturas')
ALL_PAGES=('Partida','Desempenho','Análise','Anotações','Estudo com livros','Tático','Preparo','Aberturas','Usuários')


def allowed_pages(role,in_classroom=False,has_videos=False):
    if role=='admin':return ALL_PAGES
    if role=='professor':return ('Partida','Desempenho','Análise','Estudo com livros','Tático','Preparo','Aberturas')
    return COMMON_PAGES+(('Preparo',) if in_classroom else ())+(('Vídeos',) if has_videos else ())
