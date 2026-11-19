"""Original vector badges shared by the board, annotations and review panels."""
from base64 import b64encode
from html import escape

PATHS={
 'brilliant':'<path d="M8 10l8-5 8 5-2 11-6 6-6-6zM8 10h16M16 5l-4 5 4 17 4-17z"/>',
 'best':'<path d="M6 11l5 4 5-8 5 8 5-4-3 12H9zM10 26h12"/><circle cx="16" cy="6" r="1"/>',
 'excellent':'<path d="M6 17l4 4 9-11M13 20l3 3 10-12"/>',
 'good':'<path d="M16 5l10 4v8c0 5-10 10-10 10S6 22 6 17V9zM11 16l4 4 7-8"/>',
 'inaccuracy':'<path d="M16 5L4 26h24zM16 12v6"/><circle cx="16" cy="22" r="1"/>',
 'mistake':'<path d="M11 5h10l6 6v10l-6 6H11l-6-6V11zM12 12l8 8m0-8l-8 8"/>',
 'blunder':'<path d="M16 4l12 12-12 12L4 16zM18 8l-6 9h7l-5 7"/>',
}

def icon_data(key,color='#a8b18a'):
    key='brilliant' if key=='great' else key
    art=PATHS.get(key,PATHS['good'])
    svg=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
         '<defs><linearGradient id="g" x2="0.6" y2="1"><stop stop-color="'+color+'"/><stop offset="1" stop-color="#101713"/></linearGradient></defs>'
         '<rect x="1" y="1" width="30" height="30" rx="10" fill="url(#g)" stroke="'+color+'"/>'
         '<g fill="none" stroke="#fff5d8" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+art+'</g></svg>')
    return 'data:image/svg+xml;base64,'+b64encode(svg.encode()).decode()

def category_icon(category):
    from chess_review import CATEGORIES
    key=next((key for key,value in CATEGORIES.items() if value==category),'good')
    return icon_data(key,category.color)

def icon_html(category):
    return '<img style="width:100%;height:100%;display:block" src="'+category_icon(category)+'" alt="'+escape(category.symbol,quote=True)+'"/>'
