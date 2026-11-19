"""Position-based comparison against account-owned, locally stored repertoires."""
from hashlib import sha256

import chess
import chess.pgn

import analysis_archive
import classroom as rooms
from chess_review import read_games
from personal_openings import storage_key, latest_history
from preparation_state import load_plan


def _identity(token):
    with rooms.database() as db:
        actor = rooms._identity(db, token)
    owner = ('classroom:' if actor['role'] == 'student' else actor['role'] + ':') + actor['id']
    return actor, owner


def _lines(plan, source):
    """Prepared personal lines are labeled separately from completed course lessons."""
    if not plan:
        return []
    from opening_training_state import lines_for
    if 'personal_lines' in plan:
        lines = plan['personal_lines']
    else:
        learned = plan.get('practice_progress', {})
        lines = [line for line in lines_for(plan).values()
                 if learned.get(line['id'], {}).get('learned') or line['id'] in plan.get('retention', {})]
    return [dict(line, source=source,
                 studied=bool(plan.get('practice_progress', {}).get(line['id'], {}).get('learned')
                              or line['id'] in plan.get('retention', {}))) for line in lines]


def load_sources(token):
    actor, owner = _identity(token)
    account = actor.get('chesscom', '').strip().lower()
    lines, games, notes = [], [], []
    if not account:
        return dict(owner=actor['id'], account='', lines=[], games=[],
                    notes=['Vincule o Chess.com desta conta para identificar o lado do jogador.'])
    key = storage_key(owner, account)
    personal = load_plan(key, namespace='openings')
    lines.extend(_lines(personal, 'Repertório pessoal'))
    history = load_plan(key+'|history', namespace='openings') or {}
    games.extend(latest_history(history.get('games', []), account))
    # Only user/student course keys have an exclusive account binding in the existing UI.
    course = load_plan(owner, namespace='openings') if actor['role'] in ('user', 'student') else None
    if course:
        library = dict(course.get('practice_library', {}))
        library['+'.join(course.get('repertoire_ids', []))] = course
        for identifier, plan in library.items():
            lines.extend(_lines(plan, 'Curso estudado: '+identifier))
    if actor['role'] in ('professor', 'admin'):
        notes.append('Cursos antigos identificados apenas por nome público foram excluídos por falta de vínculo exclusivo com a conta.')
    seen = set()
    for item in games:
        try:
            seen.add(analysis_archive.identifier(item['pgn']))
        except ValueError:
            pass  # The comparison reports malformed history records as excluded.
    for entry in analysis_archive.listing(token):
        saved = analysis_archive.load(token, entry['game'])
        if saved and entry['game'] not in seen:
            games.append(dict(pgn=saved['pgn'], archive=entry['game']))
            seen.add(entry['game'])
    return dict(owner=actor['id'], account=account, lines=lines, games=games, notes=notes)


def compare(games, account, lines):
    """Only compare a decision after reaching an identical stored position.

    Clocks are ignored. python-chess EPD includes turn, castling and legal en
    passant rights. Later exact positions establish reentry, not move quality.
    """
    decisions, valid, skipped_lines = {}, {}, 0
    for line in lines:
        try:
            if line['side'] not in ('white', 'black'):
                raise ValueError('Lado inválido')
            board = chess.Board()
            positions, moves = [board.epd()], []
            for uci in line['moves']:
                move = board.parse_uci(uci)
                if not move or move not in board.legal_moves:
                    raise ValueError('Lance inválido')
                moves.append(move)
                board.push(move)
                positions.append(board.epd())
            context = line.get('context_plies', 0)
            if type(context) is not int or not 0 <= context < len(moves):
                raise ValueError('Contexto inválido')
            identity = sha256((line.get('source', '')+'|'+line['side']+'|'+str(context)+'|'+' '.join(line['moves'])).encode()).hexdigest()
            if identity in valid:
                continue
            prepared = dict(line, key=identity, positions=positions,
                            san=chess.Board().variation_san(moves))
            valid[identity] = prepared
            for index in range(context, len(moves)):
                if (index % 2 == 0) == (line['side'] == 'white'):
                    decisions.setdefault((line['side'], positions[index]), []).append((prepared, index))
        except (ValueError, KeyError, TypeError, AttributeError):
            skipped_lines += 1
    reports, skipped_games, seen = [], 0, set()
    for item in games:
        try:
            game = read_games(item['pgn'])[0]
            colors = [color for color, header in (('white', 'White'), ('black', 'Black'))
                      if game.headers.get(header, '').strip().casefold() == account.strip().casefold()]
            if len(colors) != 1:
                skipped_games += 1
                continue
            color = colors[0]
            # Reject a saved public-history record whose metadata contradicts its PGN.
            if any(item.get(side, {}).get('username') and
                   item[side]['username'].casefold() != game.headers.get(header, '').casefold()
                   for side, header in (('white', 'White'), ('black', 'Black'))):
                skipped_games += 1
                continue
            key = item.get('url') or analysis_archive.identifier(item['pgn'])
            if key in seen:
                continue
            seen.add(key)
            moves = list(game.mainline_moves())
            board = game.board()
            boards = [board.copy()]
            for move in moves:
                board.push(move)
                boards.append(board.copy(stack=False))
            findings, covered = [], 0
            for index, move in enumerate(moves):
                before = boards[index]
                if before.turn != (color == 'white'):
                    continue
                candidates = decisions.get((color, before.epd()), [])
                if not candidates:
                    continue
                covered += 1
                if move.uci() in {line['moves'][at] for line, at in candidates}:
                    continue  # Any selected repertoire alternative is a match.
                options = []
                for line, at in candidates:
                    expected = chess.Move.from_uci(line['moves'][at])
                    reentry = next((later for later in range(index+1, len(boards))
                                    if boards[later].epd() in line['positions'][at+1:]), None)
                    options.append(dict(line=line['key'], source=line.get('source', 'Repertório'),
                        title=line.get('opening', line['id']), studied=line.get('studied', False),
                        expected=expected.uci(), expected_san=before.san(expected),
                        reference_ply=at+1, full_line=line['san'],
                        continuation=before.variation_san([chess.Move.from_uci(u) for u in line['moves'][at:]]),
                        reentry=reentry))
                reentries = [option['reentry'] for option in options if option['reentry'] is not None]
                findings.append(dict(id=sha256((str(key)+'|'+str(index)).encode()).hexdigest(),
                    ply=index+1, fen=before.fen(), played=before.san(move), uci=move.uci(), options=options,
                    status='reentry' if reentries else 'divergence', reentry=min(reentries) if reentries else None))
            reports.append(dict(id=key, pgn=item['pgn'],
                title=f"{game.headers.get('White', '?')} × {game.headers.get('Black', '?')} · {game.headers.get('Date', '?')}",
                covered=covered, findings=findings,
                status='no_match' if not covered else 'findings' if findings else 'matched'))
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            skipped_games += 1
    return dict(games=reports, skipped_games=skipped_games, skipped_lines=skipped_lines, lines=len(valid))


def report(token):
    sources = load_sources(token)
    return dict(compare(sources['games'], sources['account'], sources['lines']),
                owner=sources['owner'], notes=sources['notes'])


def open_position(token, state, finding_id, *, line=None, exercise=False):
    """Re-resolve source IDs against the current account before navigation or writes."""
    data = report(token)
    primary = rooms.identity(state.get('classroom_token'))
    if not primary or primary['id'] != data['owner']:
        raise PermissionError('Abra o perfil proprietário das partidas para estudar esta posição.')
    match = next(((game, finding) for game in data['games'] for finding in game['findings']
                  if finding['id'] == finding_id), None)
    if not match:
        raise ValueError('Comparação não encontrada nesta conta. Atualize os dados locais.')
    game, finding = match
    if exercise:
        option = next((option for option in finding['options'] if option['line'] == line), None)
        if not option:
            raise ValueError('Escolha uma das linhas usadas na comparação.')
        from analysis_training import _save_exercise
        board = chess.Board(finding['fen'])
        key = sha256(('repertoire|'+board.epd()+'|'+option['expected']).encode()).hexdigest()
        payload = dict(fen=board.fen(), uci=option['expected'], best_san=option['expected_san'],
            best_line=option['continuation'], played=finding['played'], ply=finding['ply'], game=game['id'],
            category='repertoire', source='repertoire', engine=option['source'],
            explanation=f"Linha de referência: {option['title']}. Treino de memória do repertório; "
                        'a divergência não é uma classificação de erro nem uma avaliação de motor.')
        _save_exercise(token, key, payload)
        state['analysis_training_' + data['owner'] + '_choice'] = key
        state['analysis_training_open'] = True
    state['dashboard_review_request'] = dict(pgn=game['pgn'], ply=finding['ply']-1)
    state['requested_page'] = 'Análise'
