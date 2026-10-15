"""Personal preparation material from archived games and bounded Stockfish searches.

The module has no Streamlit state or network access. Results are JSON serializable;
callers can persist a completed batch and resume lessons without running the engine.
"""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import CancelledError
from contextlib import contextmanager
import csv
from functools import lru_cache
from hashlib import sha256
from io import StringIO
import math
import os
from pathlib import Path
import re
import subprocess
from threading import Event
from urllib.parse import unquote, urlparse

import chess
import chess.engine
import chess.pgn

from stockfish_analysis import _ENGINE_LOCK, analyse_with_books
from strategy import phase
from tutor import move_ideas


_ROOT = Path(__file__).resolve().parent
_DRAW_RESULTS = {'agreed', 'repetition', 'stalemate', 'insufficient', '50move',
                 'timevsinsufficient', 'draw'}
_LOSS_RESULTS = {'checkmated', 'resigned', 'timeout', 'lose', 'abandoned',
                 'kingofthehill', 'threecheck', 'bughousepartnerlose'}
_PHASES = {'abertura': 'opening', 'meio-jogo': 'middlegame', 'final': 'endgame'}
_PHASE_LABELS = {'opening': 'Abertura', 'middlegame': 'Meio-jogo', 'endgame': 'Final'}

_OPENING_FAMILIES = (
    ('siciliana', 'Defesa Siciliana', '1.e4 c5', 'e4 c5'),
    ('ruy_lopez', 'Ruy Lopez', '1.e4 e5 2.Nf3 Nc6 3.Bb5', 'e4 e5 Nf3 Nc6 Bb5'),
    ('gambito_dama', 'Gambito da Dama', '1.d4 d5 2.c4', 'd4 d5 c4'),
    ('francesa', 'Defesa Francesa', '1.e4 e6', 'e4 e6'),
    ('caro_kann', 'Defesa Caro-Kann', '1.e4 c6', 'e4 c6'),
    ('italiana', 'Abertura Italiana', '1.e4 e5 2.Nf3 Nc6 3.Bc4', 'e4 e5 Nf3 Nc6 Bc4'),
)


def opening_family(name, eco=''):
    text = re.sub(r'[^a-z0-9]+', ' ', str(name or '').casefold()).strip()
    code = str(eco or '').upper()
    match = re.match(r'^[A-E](\d{2})$', code)
    number = int(match.group(1)) if match else -1
    if 'sicilian' in text or code.startswith('B') and 20 <= number <= 99:
        return 'siciliana'
    if 'ruy lopez' in text or 'spanish' in text or code.startswith('C') and 60 <= number <= 99:
        return 'ruy_lopez'
    if ('queen gambit' in text or 'queens gambit' in text or 'gambito da dama' in text
            or code.startswith('D') and 6 <= number <= 69):
        return 'gambito_dama'
    if 'french' in text or 'francesa' in text or code.startswith('C') and 0 <= number <= 19:
        return 'francesa'
    if 'caro kann' in text or code.startswith('B') and 10 <= number <= 19:
        return 'caro_kann'
    if 'italian' in text or 'italiana' in text or code.startswith('C') and 50 <= number <= 59:
        return 'italiana'
    return None
def _id(text):
    return sha256(text.encode('utf-8')).hexdigest()[:20]


def _cancelled(cancel):
    if cancel.is_set():
        raise CancelledError()


@lru_cache(maxsize=1)
def _catalog():
    """Index the vendored catalogue once; no downloaded or invented openings."""
    paths = sorted((_ROOT / 'data' / 'openings').glob('*.tsv'))
    if (_ROOT / 'data' / 'openings.tsv').is_file():
        paths.append(_ROOT / 'data' / 'openings.tsv')
    rows = []
    for path in paths:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                game = chess.pgn.read_game(StringIO(row.get('pgn', '')))
                if game is None or game.errors:
                    continue
                moves = tuple(move.uci() for move in game.mainline_moves())
                if moves:
                    rows.append({'eco': row.get('eco', ''), 'name': row.get('name', ''),
                                 'moves': moves, 'pgn': row.get('pgn', '')})
    return tuple(rows)


@lru_cache(maxsize=1)
def _catalog_by_moves():
    return {row['moves']: row for row in _catalog()}


def _matched_opening(game):
    moves = tuple(move.uci() for move in game.mainline_moves())
    catalog = _catalog_by_moves()
    for length in range(min(len(moves), 60), 0, -1):
        if moves[:length] in catalog:
            return catalog[moves[:length]]
    return None


def _opening(game, item):
    headers = game.headers
    eco = headers.get('ECO', '')
    name = headers.get('Opening', '').strip()
    if name:
        variation = headers.get('Variation', '').strip()
        if variation and variation.casefold() not in name.casefold():
            name += ': ' + variation
        return name, eco
    url = headers.get('ECOUrl', '') or item.get('eco', '')
    if isinstance(url, str) and '/openings/' in url:
        slug = unquote(urlparse(url).path.rstrip('/').rsplit('/', 1)[-1])
        # Chess.com may append the concrete move sequence to its opening slug.
        slug = re.split(r'-\d+(?:\.|-|$)', slug, maxsplit=1)[0]
        name = slug.replace('-', ' ').strip()
    if not name:
        matched = _matched_opening(game)
        if matched:
            return matched['name'], eco or matched['eco']
    return name or (f'Abertura {eco}' if eco else 'Abertura não identificada'), eco


def _outcome(game, item, side):
    result = game.headers.get('Result', '*')
    if result == '1/2-1/2':
        return 'draws'
    if result in ('1-0', '0-1'):
        winner = 'white' if result == '1-0' else 'black'
        return 'wins' if winner == side else 'losses'
    code = str((item.get(side) or {}).get('result', '')).lower()
    if code == 'win':
        return 'wins'
    if code in _DRAW_RESULTS:
        return 'draws'
    if code in _LOSS_RESULTS:
        return 'losses'
    return None


def _records(history, username):
    username = str(username or '').strip().casefold()
    if not username:
        return []
    records, seen = [], set()
    for item in history or ():
        if not isinstance(item, dict) or not isinstance(item.get('pgn'), str):
            continue
        if item.get('rules', 'chess') != 'chess':
            continue
        pgn = item['pgn']
        identifier = item.get('url') or _id(pgn)
        if identifier in seen:
            continue
        game = chess.pgn.read_game(StringIO(pgn))
        if (game is None or game.errors or not game.variations or not game.board().is_valid()
                or game.headers.get('Variant', 'Standard') not in {'Standard', 'Chess', 'Normal'}):
            continue
        side = next((color for color, header in [('white', 'White'), ('black', 'Black')]
                     if str((item.get(color) or {}).get('username') or game.headers.get(header, '')).casefold()
                     == username), None)
        if side is None:
            continue
        name, eco = _opening(game, item)
        seen.add(identifier)
        timestamp = item.get('end_time', 0)
        records.append({'game': game, 'pgn': pgn, 'id': identifier, 'side': side,
                        'opening': name, 'eco': eco, 'outcome': _outcome(game, item, side),
                        'timestamp': timestamp if isinstance(timestamp, (int, float)) else 0,
                        'rating': (item.get(side) or {}).get('rating', 1500)})
    return sorted(records, key=lambda record: record['timestamp'], reverse=True)


def opening_stats(history, username):
    """Completed games only, with win rates on a 0–100 scale and explicit sample sizes.

    A result of ``*`` without a Chess.com result is excluded from the denominator.
    Colors remain separate so playing an opening with Black is not confused with
    meeting it with White. Duplicate archives and unrelated accounts are ignored.
    """
    groups = {}
    for record in _records(history, username):
        if record['outcome'] is None:
            continue
        key = record['opening'], record['eco'], record['side']
        group = groups.setdefault(key, {'opening': key[0], 'eco': key[1], 'color': key[2],
                                       'games': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                                       'win_rate': 0.0, 'game_ids': []})
        group['games'] += 1
        group[record['outcome']] += 1
        group['game_ids'].append(record['id'])
    for group in groups.values():
        group['win_rate'] = round(group['wins'] * 100 / group['games'], 1)
    return sorted(groups.values(), key=lambda row: (-row['games'], row['opening'], row['color']))


def opening_families(history, username):
    """Aggregate played opening variants under the six trunk families."""
    groups = {}
    for record in _records(history, username):
        if record['outcome'] is None:
            continue
        family = opening_family(record['opening'], record['eco'])
        if family is None:
            continue
        label = next(row[1] for row in _OPENING_FAMILIES if row[0] == family)
        group = groups.setdefault(family, {'family': family, 'opening': label, 'games': 0,
            'wins': 0, 'draws': 0, 'losses': 0, 'win_rate': 0.0, 'game_ids': []})
        group['games'] += 1
        group[record['outcome']] += 1
        group['game_ids'].append(record['id'])
    for group in groups.values():
        group['win_rate'] = round(group['wins'] * 100 / group['games'], 1)
    return sorted(groups.values(), key=lambda row: (-row['games'], row['opening']))


def _selected(record, selections):
    for selection in selections:
        if isinstance(selection, str) and selection == record['opening']:
            return True
        if isinstance(selection, dict):
            if selection.get('family') and opening_family(record['opening'], record['eco']) == selection['family']:
                return True
            if selection.get('opening') != record['opening']:
                continue
            if selection.get('color', selection.get('side', record['side'])) != record['side']:
                continue
            if selection.get('eco', record['eco']) != record['eco']:
                continue
            return True
    return False


@contextmanager
def _training_engine(path, cancel):
    while not _ENGINE_LOCK.acquire(timeout=.1):
        _cancelled(cancel)
    try:
        _cancelled(cancel)
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        with chess.engine.SimpleEngine.popen_uci(path, timeout=15, **kwargs) as engine:
            if 'Stockfish' not in engine.id.get('name', ''):
                raise ValueError('O executável configurado deve ser o Stockfish.')
            engine.configure({'Threads': 1, 'Hash': 64})
            yield engine
    except (chess.engine.EngineError, OSError, TimeoutError) as error:
        raise ValueError('Não foi possível preparar as aulas com o Stockfish.') from error
    finally:
        _ENGINE_LOCK.release()


def _search(engine, board, cancel, *, multipv=1, root=None):
    _cancelled(cancel)
    kwargs = {'multipv': min(multipv, board.legal_moves.count())}
    if root is not None:
        kwargs['root_moves'] = [root]
    if not kwargs['multipv'] or board.is_game_over():
        return []
    results = engine.analyse(board, chess.engine.Limit(depth=12, time=.06), **kwargs)
    _cancelled(cancel)
    if isinstance(results, dict):
        results = [results]
    clean = []
    for result in results:
        probe, legal = board.copy(), []
        for move in result.get('pv', ())[:12]:
            if move not in probe.legal_moves or probe.is_game_over():
                break
            legal.append(move)
            probe.push(move)
        if legal and (root is None or legal[0] == root):
            clean.append(legal)
    return clean


def _seed(record):
    """Begin at a real position after the shortest recognized opening stem."""
    game = record['game']
    played = tuple(move.uci() for move in game.mainline_moves())
    name = re.sub(r'[^a-z0-9]+', ' ', record['opening'].casefold()).strip()
    matches = []
    for row in _catalog():
        row_name = re.sub(r'[^a-z0-9]+', ' ', row['name'].casefold()).strip()
        same_family = (name.startswith(row_name) or row_name.startswith(name))
        if ((same_family or (record['eco'] and record['eco'] == row['eco']))
                and played[:len(row['moves'])] == row['moves']):
            matches.append(row)
    length = min((len(row['moves']) for row in matches), default=0)
    board = game.board()
    for uci in played[:length]:
        board.push_uci(uci)
    color = record['side'] == 'white'
    if board.turn != color:
        if length >= len(played):
            return None
        board.push_uci(played[length])
    return board if not board.is_game_over() else None


def _explain(board, move, pv, *, actual=None, loss=None):
    facts = move_ideas(board, move)['facts'][:3]
    lead = (f'Na sua partida você jogou {actual}; a alternativa calculada pelo Stockfish é '
            f'{board.san(move)}. A análise estima perda de {loss:.1%} dos pontos esperados. '
            if actual is not None else f'O Stockfish recomenda {board.san(move)} nesta posição. ')
    text = lead + '. '.join(sentence.rstrip('.') for sentence in facts) + '.'
    if len(pv) > 1:
        text += ' Continuação para comparar: ' + board.variation_san(pv[:6]) + '.'
    return text


def _opening_line(engine, record, seed, branch, cancel):
    board, steps = seed.copy(), []
    for index in range(5):
        choices = _search(engine, board, cancel)
        if not choices:
            break
        pv, fen = choices[0], board.fen()
        move = pv[0]
        step = {'fen': fen, 'uci': move.uci(), 'san': board.san(move),
                'explanation': _explain(board, move, pv)}
        board.push(move)
        if index < 4 and not board.is_game_over():
            replies = _search(engine, board, cancel, multipv=2 if index == 0 else 1)
            if replies:
                reply = replies[min(branch if index == 0 else 0, len(replies) - 1)][0]
                step['reply'] = reply.uci()
                board.push(reply)
        steps.append(step)
        if board.is_game_over() or board.turn != (record['side'] == 'white'):
            break
    if not steps:
        return None
    signature = '|'.join(step['fen'] + ':' + step['uci'] for step in steps)
    return {'id': _id(record['side'] + signature), 'label': record['opening'],
            'opening': record['opening'], 'side': record['side'],
            'source_pgn': record['pgn'], 'steps': steps}


def _theme(board, move):
    if board.gives_check(move):
        after = board.copy()
        after.push(move)
        return 'Mate' if after.is_checkmate() else 'Xeque e iniciativa'
    if board.is_check():
        return 'Defesa do rei'
    if board.is_capture(move):
        return 'Capturas e trocas'
    if board.is_castling(move):
        return 'Segurança do rei'
    piece = board.piece_at(move.from_square)
    if piece.piece_type in (chess.KNIGHT, chess.BISHOP) and chess.square_rank(move.from_square) == (0 if piece.color else 7):
        return 'Desenvolvimento'
    return 'Escolha de plano e atividade'


def _weaknesses(errors, sample_moves):
    groups = defaultdict(list)
    for error in errors:
        groups[(error['phase'], error['theme'])].append(error['expected_loss'])
    output = []
    for (stage, theme), losses in groups.items():
        count = len(losses)
        output.append({'phase': stage, 'theme': theme, 'count': count,
                       'sample_moves': sample_moves, 'mean_loss': round(sum(losses) / count, 4),
                       'description': (f'{_PHASE_LABELS[stage]} · {theme}: {count} '
                                       f'{"erro encontrado" if count == 1 else "erros encontrados"} '
                                       f'em {sample_moves} lances seus analisados. '
                                       'Tema da alternativa sugerida; a amostra não representa todas as suas partidas.')})
    return sorted(output, key=lambda item: (-item['count'], -item['mean_loss'], item['theme']))


def build_training_material(history, username, selected_openings, engine_path, cancel=None, progress=None):
    """Analyse at most 12 recent relevant games and produce replayable exercises.

    ``progress`` receives readable status strings. ``source_ply`` is the one-based
    ply of the actual mistake. ``line`` is a legal engine PV beginning with ``uci``.
    Losses are probabilities (0–1), not centipawns; no exercise is synthesized if
    there is no engine, no selected game, or no verified loss of at least .05.
    Opening lessons use up to five player decisions, with an optional opponent
    ``reply`` after each decision. Reusing them never launches a new engine.
    """
    result = {'opening_lines': [], 'middlegame': [], 'tactics': [], 'weaknesses': [], 'analyzed_games': 0}
    cancel = cancel or Event()
    _cancelled(cancel)
    report = progress if callable(progress) else lambda message: None
    if not engine_path or not Path(engine_path).is_file():
        report('Instale ou configure o Stockfish para preparar aulas a partir das suas partidas.')
        return result
    records = [record for record in _records(history, username)
               if _selected(record, selected_openings or ())][:12]
    if not records:
        report('Não há partidas suas nas aberturas selecionadas para preparar exercícios.')
        return result
    candidates, sample_moves = [], 0
    for index, record in enumerate(records, 1):
        _cancelled(cancel)
        report(f'Analisando partida {index} de {len(records)} · {record["opening"]}…')
        rating = record['rating']
        rating = rating if isinstance(rating, (int, float)) and math.isfinite(rating) else 1500
        analysis = analyse_with_books(record['game'], engine_path, rating=rating,
                                      quality='Rápida', cancel=cancel)
        result['analyzed_games'] += 1
        board = record['game'].board()
        for ply, played in enumerate(record['game'].mainline_moves(), 1):
            _cancelled(cancel)
            review = analysis.get('reviews', {}).get(ply)
            if board.turn == (record['side'] == 'white') and review is not None:
                sample_moves += 1
                loss = getattr(review, 'expected_loss', 0)
                if isinstance(loss, (int, float)) and math.isfinite(loss) and .05 <= loss <= 1:
                    try:
                        best = board.parse_san(review.best_san)
                    except (ValueError, TypeError):
                        best = None
                    if best is not None and best != played:
                        candidates.append({'record': record, 'board': board.copy(), 'ply': ply,
                                           'played': board.san(played), 'move': best, 'loss': float(loss)})
            board.push(played)
    candidates.sort(key=lambda item: -item['loss'])
    # Describe all verified errors in the analysed sample, including recurring
    # mistakes. The smaller exercise bank below is intentionally deduplicated.
    result['weaknesses'] = _weaknesses([
        {'phase': _PHASES[phase(item['board'])], 'theme': _theme(item['board'], item['move']),
         'expected_loss': item['loss']} for item in candidates
    ], sample_moves)
    verified, identities = [], set()
    report('Montando as linhas de abertura e verificando as soluções dos seus erros…')
    with _training_engine(engine_path, cancel) as engine:
        seeds, line_ids = [], set()
        for record in records:
            seed = _seed(record)
            if seed is not None and (seed.fen(), record['side']) not in {key for key, _, _ in seeds}:
                seeds.append(((seed.fen(), record['side']), record, seed))
        # Two different best-response branches per position, up to 12 lessons.
        for _, record, seed in seeds:
            for branch in (0, 1):
                line = _opening_line(engine, record, seed, branch, cancel)
                if line is not None and line['id'] not in line_ids:
                    line_ids.add(line['id'])
                    line['label'] += f' · linha {len(result["opening_lines"]) + 1}'
                    result['opening_lines'].append(line)
                if len(result['opening_lines']) >= 12:
                    break
            if len(result['opening_lines']) >= 12:
                break
        tactical_count = middle_count = 0
        for candidate in candidates:
            _cancelled(cancel)
            record, board, move = candidate['record'], candidate['board'], candidate['move']
            identity = (board.fen(), move.uci())
            if identity in identities:
                continue
            stage = _PHASES[phase(board)]
            # A large collection of opening errors must not hide the player's
            # available middlegame errors from that separate training phase.
            if tactical_count >= 30 and (stage != 'middlegame' or middle_count >= 30):
                continue
            solutions = _search(engine, board, cancel, root=move)
            if not solutions:
                continue
            pv = solutions[0]
            exercise = {'id': _id(record['id'] + ':' + str(candidate['ply'])),
                        'fen': board.fen(), 'uci': move.uci(), 'san': board.san(move),
                        'line': [step.uci() for step in pv],
                        'explanation': _explain(board, move, pv, actual=candidate['played'], loss=candidate['loss']),
                        'source_pgn': record['pgn'], 'source_ply': candidate['ply'],
                        'opening': record['opening'], 'side': record['side'],
                        'expected_loss': candidate['loss'], 'phase': stage,
                        'theme': _theme(board, move)}
            verified.append(exercise)
            identities.add(identity)
            tactical_count += 1
            middle_count += stage == 'middlegame'
            if tactical_count >= 30 and middle_count >= 30:
                break
    result['tactics'] = verified[:30]
    result['middlegame'] = [exercise.copy() for exercise in verified if exercise['phase'] == 'middlegame'][:30]
    _cancelled(cancel)
    report(f'Preparo pronto: {len(result["opening_lines"])} linhas e {len(verified)} erros para revisar '
           f'em {result["analyzed_games"]} partidas analisadas.')
    return result
