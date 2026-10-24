"""Small native SVG cursors, inherited by the app and its component hosts."""
from urllib.parse import quote


def _cursor(paths, hotspot, fallback):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
           '<g fill="#faf8f2" stroke="#191919" stroke-width="1.7" stroke-linecap="round" '
           'stroke-linejoin="round">' + paths + '</g></svg>')
    return f'url("data:image/svg+xml,{quote(svg, safe="")}") {hotspot}, {fallback}'


CURSORS = {
    'default': _cursor('<path d="M5 3 5 25 10.5 19.5 15 28 19 26 14.5 18 23 17Z"/>'
                       '<path d="m8 9 10 6-7 1Z" fill="#ff9b45" stroke="none"/>', '5 3', 'default'),
    'link': _cursor('<path d="M12 16V5a2.5 2.5 0 0 1 5 0v8-2a2.5 2.5 0 0 1 5 0v3-1a2 2 0 0 1 4 0v4'
                    'a2 2 0 0 1 4 0v5c0 4-2 6-3 8H14c-1-4-5-7-7-10-2-3 1-5 3-3l3 3"/>'
                    '<path d="M16 27h9" stroke="#e98732"/>', '14 4', 'pointer'),
    'grab': _cursor('<path d="m9 17-3-5a2 2 0 0 1 3-2l3 5-1-9a2 2 0 0 1 4 0l1 8V4a2 2 0 0 1 4 0v10'
                    'l2-8a2 2 0 0 1 4 1l-2 10 2-4a2 2 0 0 1 4 2l-3 9-3 5H13l-3-5-5-5a2 2 0 0 1 3-3l4 4"/>'
                    '<path d="M15 26h8" stroke="#e98732"/>', '16 16', 'grab'),
    'grabbing': _cursor('<path d="M9 19v-7a2.5 2.5 0 0 1 5 0v-2a2.5 2.5 0 0 1 5 0v1a2.5 2.5 0 0 1 5 0v2'
                        'a2.5 2.5 0 0 1 5 0v7l-4 9H13l-7-10a2.5 2.5 0 0 1 4-3l3 4"/>'
                        '<path d="M15 26h8" stroke="#e98732"/>', '16 16', 'grabbing'),
    'crosshair': _cursor('<circle cx="16" cy="16" r="6" fill="none" stroke="#faf8f2" stroke-width="3"/>'
                         '<circle cx="16" cy="16" r="6" fill="none" stroke="#191919" stroke-width="1"/>'
                         '<path d="M16 4v7m0 10v7M4 16h7m10 0h7" stroke="#ff9b45" stroke-width="2"/>'
                         '<circle cx="16" cy="16" r="1.5" stroke="none"/>', '16 16', 'crosshair'),
}

CURSOR_STYLE = ':root{' + ''.join(f'--club-cursor-{name}:{value};' for name, value in CURSORS.items()) + '''}
@media (pointer:fine) {
  .stApp {cursor:var(--club-cursor-default,default)}
  .stApp :is(button,a,summary,[role="button"],[role="tab"],[role="radio"],
    [role="checkbox"],[role="switch"],[role="option"],select,[data-baseweb="select"]) {
    cursor:var(--club-cursor-link,pointer);
  }
  .stApp :is(button,a,summary,[role="button"]) :is(span,p,svg,div) {cursor:inherit}
  .stApp :is(input,textarea,[contenteditable="true"]) {cursor:text}
  .stApp :is(button:disabled,[aria-disabled="true"]) {cursor:not-allowed}
}
'''
