"""Local, asynchronous page-to-position extraction for the book reader."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import re
from threading import Event, RLock, local

import chess
import chess.pgn


SCAN_VERSION = 3
_WORKER = local()
_CACHE_LOCK = RLock()
_FEN = re.compile(r'(?<![\w/])([prnbqkPRNBQK1-8]+(?:/[prnbqkPRNBQK1-8]+){7})'
                  r'(?:\s+([wb])\s+(-|[KQkq]+)\s+(-|[a-h][36])(?:\s+(\d+)\s+(\d+))?)?(?![\w/])')
_GLYPHS = dict(zip('♔♕♖♗♘♙♚♛♜♝♞♟', 'KQRBNPkqrbnp'))


@dataclass(frozen=True)
class BookPosition:
    fen: str
    label: str
    source: str
    pgn: str = ''
    confidence: float = 1.0
    turn_known: bool = True
    castling_known: bool = True


@dataclass(frozen=True)
class PagePositions:
    positions: tuple[BookPosition, ...] = ()
    notice: str = ''


def side_in_text(text):
    """Only explicit, unambiguous instructions establish the side to move."""
    white = bool(re.search(r'(?i)\b(?:white\s+(?:to\s+(?:move|play)|plays)|brancas\s+(?:jogam|jogam\s+e|a\s+jogar)|jogam\s+as\s+brancas)\b', text))
    black = bool(re.search(r'(?i)\b(?:black\s+(?:to\s+(?:move|play)|plays)|pretas\s+(?:jogam|a\s+jogar)|jogam\s+as\s+pretas)\b', text))
    return chess.WHITE if white and not black else chess.BLACK if black and not white else None


def _placement(placement, text=''):
    side = side_in_text(text)
    board = chess.Board(f'{placement} w - - 0 1')
    if side is None:
        checked = [color for color in (chess.WHITE, chess.BLACK)
                   if board.king(color) is not None and board.is_attacked_by(not color, board.king(color))]
        side = checked[0] if len(checked) == 1 else None
    board.turn = chess.WHITE if side is None else side
    return board, side is not None


def text_positions(text, *, pgn=False):
    positions = []
    for match in _FEN.finditer(text):
        try:
            placement, side, castling, ep, half, full = match.groups()
            if side:
                board = chess.Board(f'{placement} {side} {castling} {ep} {half or 0} {full or 1}')
                known = True
            else:
                board, known = _placement(placement, text[max(0, match.start()-160):match.end()+160])
            if board.is_valid():
                positions.append(BookPosition(board.fen(), f'Posição {len(positions)+1}', 'FEN',
                                              turn_known=known, castling_known=bool(side)))
        except ValueError:
            continue
    # Unicode chess diagrams in text/PDF text layers, including dotted empty squares.
    rows = []
    for line in text.splitlines():
        cells = ''.join(c for c in line if c in _GLYPHS or c in '.·□■◻◼')
        if len(cells) == 8:
            rows.append(cells)
            if len(rows) == 8:
                ranks = []
                for row in rows:
                    rank, empty = '', 0
                    for cell in row:
                        if cell in _GLYPHS:
                            rank += (str(empty) if empty else '') + _GLYPHS[cell]
                            empty = 0
                        else:
                            empty += 1
                    ranks.append(rank + (str(empty) if empty else ''))
                try:
                    board, known = _placement('/'.join(ranks), text)
                    if board.is_valid():
                        positions.append(BookPosition(board.fen(), f'Diagrama {len(positions)+1}', 'diagrama em texto',
                                                      turn_known=known, castling_known=False))
                except ValueError:
                    pass
                rows = []
        else:
            rows = []
    # PGN books use a complete game per reader page, including custom FEN setups.
    candidates = [text] if pgn else re.findall(r'(?m)^\s*(?:```pgn\s*\n)?(1\.(?:[^\n]|\n(?!\s*\n))+)', text)
    for candidate in candidates:
        try:
            game = chess.pgn.read_game(StringIO(candidate))
            if game is None or game.errors or (not list(game.mainline_moves()) and not game.headers.get('FEN')):
                continue
            if not game.board().is_valid():
                continue
            white, black = game.headers.get('White', '?'), game.headers.get('Black', '?')
            positions.append(BookPosition(game.board().fen(), f'{white} × {black}' if white != '?' else 'Linha do livro',
                                          'PGN', pgn=str(game)))
        except (ValueError, IndexError):
            continue
    return attach_book_lines(text, _deduplicate(positions))


def attach_book_lines(text, positions):
    """Keep only printed SAN continuations that can actually be played from a diagram."""
    starts = list(re.finditer(r'(?<![\w.])(\d+)\.(\.\.)?\s*', text))
    token = re.compile(r'\s*(?:(\d+\.(?:\.\.)?)|'
                       r'((?:O-O(?:-O)?|0-0(?:-0)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)[+#]?[!?]*))(?!\w)')
    enriched = []
    for position in positions:
        best = None
        best_count = 0
        if not position.pgn:
            for start in starts:
                board = chess.Board(position.fen)
                side = chess.BLACK if start[2] else chess.WHITE
                if position.turn_known and board.turn != side:
                    continue
                board.turn = side
                board.fullmove_number = int(start[1])
                if not board.is_valid():
                    continue
                game = chess.pgn.Game()
                game.setup(board)
                node, offset, count = game, start.end(), 0
                while match := token.match(text, offset):
                    offset = match.end()
                    if match[1]:
                        continue
                    try:
                        move = board.parse_san(match[2].rstrip('!?').replace('0', 'O'))
                    except ValueError:
                        break
                    node = node.add_variation(move)
                    board.push(move)
                    count += 1
                if count > best_count and count >= 2:
                    best, best_count = game, count
        enriched.append(replace(position, fen=best.board().fen(), pgn=str(best), turn_known=True)
                        if best else position)
    return tuple(enriched)


def _deduplicate(positions):
    found = {}
    for position in positions:
        key = tuple(position.fen.split()[:4])
        if position.source.startswith('diagrama') and any(existing[0] == key[0] for existing in found):
            continue
        if key not in found or (position.pgn and not found[key].pgn):
            found[key] = position
    return tuple(found.values())


def _pdf_page(data, index, *, high_resolution=False):
    """PDFium is serialized with the reader renderer; inference runs outside it."""
    import pypdfium2 as pdfium
    from book_reader import _PDF_LOCK
    with _PDF_LOCK, pdfium.PdfDocument(data) as document:
        page = document[index]
        try:
            textpage = page.get_textpage()
            try:
                text = textpage.get_text_range()
            finally:
                textpage.close()
            width, height = page.get_size()
            scale = min((3000 if high_resolution else 1800) / max(width, height, 1), 5 if high_resolution else 3)
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil().convert('RGB').copy()
            finally:
                bitmap.close()
            return text, image, (width, height)
        finally:
            page.close()


def _diagram_context(data, index, box, image_size, page_size):
    import pypdfium2 as pdfium
    from book_reader import _PDF_LOCK
    x, y, w, h = box
    sx, sy = page_size[0] / image_size[0], page_size[1] / image_size[1]
    with _PDF_LOCK, pdfium.PdfDocument(data) as document:
        page = document[index]
        try:
            textpage = page.get_textpage()
            try:
                return textpage.get_text_bounded(max(0, x*sx-12), max(0, page_size[1]-(y+h)*sy-65),
                                                min(page_size[0], (x+w)*sx+12), min(page_size[1], page_size[1]-y*sy+45))
            finally:
                textpage.close()
        finally:
            page.close()


def _vision():
    if not hasattr(_WORKER, 'vision'):
        from chessvision import BoardDetector, BoardPredictor
        _WORKER.vision = BoardDetector(min_size_ratio=.09), BoardPredictor()
    return _WORKER.vision


def _detect_diagrams(image, detector):
    """Retain bordered/white-page diagrams that the detector's margin snap cuts."""
    import cv2
    import numpy as np
    from chessvision import DetectedBoard
    boards = list(detector.detect(image))
    gray = np.asarray(image.convert('L'))
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    parity = (np.arange(8)[:, None] + np.arange(8)) % 2 == 0
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < max(96, min(image.size)*.09) or not .94 <= w/h <= 1.06:
            continue
        if any(min(x+w,b.box[0]+b.box[2])-max(x,b.box[0]) > min(w,b.box[2])*.6 and
               min(y+h,b.box[1]+b.box[3])-max(y,b.box[1]) > min(h,b.box[3])*.6 for b in boards):
            continue
        tiles = cv2.resize(gray[y:y+h, x:x+w], (64, 64), interpolation=cv2.INTER_AREA).reshape(8, 8, 8, 8).swapaxes(1, 2)
        medians = np.median(tiles, axis=(2, 3))
        contrast = float(abs(np.median(medians[parity])-np.median(medians[~parity])))
        if contrast < 25:
            continue
        threshold = (np.median(medians[parity])+np.median(medians[~parity]))/2
        agreement = np.mean((medians > threshold) == parity)
        if max(agreement, 1-agreement) < .78:
            continue
        boards.append(DetectedBoard(image.crop((x,y,x+w,y+h)), (x,y,w,h), contrast))
    return sorted(boards, key=lambda b:(b.box[1]//max(b.box[3]//2,1), b.box[0]))


def diagram_positions(image, context_for_box):
    from chessvision import Orientation, Turn
    detector, predictor = _vision()
    positions, uncertain = [], 0
    for index, diagram in enumerate(_detect_diagrams(image, detector), 1):
        context = context_for_box(diagram.box)
        orientation = (Orientation.BLACK if re.search(r'(?im)^\s*h\s*g\s*f\s*e\s*d\s*c\s*b\s*a\s*$', context) else
                       Orientation.WHITE if re.search(r'(?im)^\s*a\s*b\s*c\s*d\s*e\s*f\s*g\s*h\s*$', context) else Orientation.AUTO)
        prediction = predictor.predict(diagram, orientation=orientation, turn=Turn.AUTO, castling='-')
        confidence = prediction.confidence
        if confidence < .96 or min(s.confidence for s in prediction.squares.values()) < .55:
            uncertain += 1
            continue
        board, known = _placement(chess.Board(prediction.fen).board_fen(), context)
        if not board.is_valid():
            # The automatic orientation is a heuristic. Try its 180-degree alternative,
            # retaining only a legal interpretation, never a guessed set of pieces.
            rotated = chess.Board(None)
            for square, piece in board.piece_map().items():
                rotated.set_piece_at(63-square, piece)
            board, known = _placement(rotated.board_fen(), context)
        if not board.is_valid():
            uncertain += 1
            continue
        positions.append(BookPosition(board.fen(), f'Diagrama {index}', 'diagrama do PDF',
                                      confidence=confidence, turn_known=known, castling_known=False))
    return positions, uncertain


def scan_page(data, info, index, *, high_resolution=False):
    if info['kind'] != 'pdf':
        return PagePositions(text_positions(info['pages'][index], pgn=info.get('pgn', False)))
    text, image, page_size = _pdf_page(data, index, high_resolution=high_resolution)
    positions = list(text_positions(text))
    notice = ''
    try:
        diagrams, uncertain = diagram_positions(image, lambda box: _diagram_context(data, index, box, image.size, page_size))
        # A printed move list can start at move 1 while the diagram shows a
        # later position. Give the actual diagrams priority over PGN text.
        positions = [p for p in positions if p.source != 'PGN'] + diagrams + [p for p in positions if p.source == 'PGN']
        if uncertain:
            notice = 'Há diagrama nesta página cuja leitura não foi suficientemente segura.'
    except ImportError:
        notice = 'O reconhecimento de diagramas precisa das dependências atualizadas do aplicativo.'
    except Exception:
        notice = 'Não foi possível reconhecer os diagramas desta página com segurança.'
    return PagePositions(attach_book_lines(text, _deduplicate(positions)), notice)


class BookPositionService:
    """Bounded look-ahead jobs; workers never read or write Streamlit session state."""
    def __init__(self, cache_dir=None):
        self.cache_dir = Path(cache_dir or os.environ.get('COACH_BOOK_POSITION_DIR',Path(__file__).parent/'data'/'book_positions'))
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='book-pages')
        self.jobs = OrderedDict()
        self.lock = RLock()
        self.preload_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='whole-book')
        self.preloads = {}
        self.page_locks = {}

    def _scan(self, identity, data, info, index, force=False):
        with self.lock:
            page_lock = self.page_locks.setdefault((identity, index), RLock())
        with page_lock:
            return self._read_or_scan(identity, data, info, index, force)

    def _read_or_scan(self, identity, data, info, index, force=False):
        path = self.cache_dir / f'v{SCAN_VERSION}' / identity / f'{index}.json'
        cached = None
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            cached = PagePositions(tuple(BookPosition(**p) for p in payload['positions']), payload['notice'])
            if not force:
                return cached
        except (OSError, ValueError, TypeError, KeyError):
            pass
        result = scan_page(data, info, index, high_resolution=True) if force else scan_page(data, info, index)
        if force and cached is not None and cached.positions:
            result = PagePositions(_deduplicate((*cached.positions, *result.positions)), result.notice)
        if result.positions or not result.notice:
            try:
                with _CACHE_LOCK:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_suffix('.tmp')
                    temporary.write_text(json.dumps(asdict(result), ensure_ascii=False), encoding='utf-8')
                    temporary.replace(path)
            except OSError:
                pass  # A read-only disk does not prevent reading a book.
        return result

    def retry(self, entry, index):
        name, data, info = entry
        if not 0 <= index < info['count']:
            raise ValueError('Página fora do livro.')
        identity = sha256(name.encode()+b'\0'+data).hexdigest()
        with self.lock:
            key = identity, index
            if key not in self.jobs or self.jobs[key].done():
                self.jobs[key] = self.executor.submit(self._scan, identity, data, info, index, True)
        return identity

    def preload(self, entry):
        """Prepare the entire book on disk without queuing unbounded page futures."""
        name, data, info = entry
        identity = sha256(name.encode()+b'\0'+data).hexdigest()
        with self.lock:
            if identity not in self.preloads or self.preloads[identity]['stop'].is_set():
                status = {'done': 0, 'total': info['count'], 'review': 0, 'stop': Event()}
                self.preloads[identity] = status
                status['future'] = self.preload_executor.submit(self._preload, identity, data, info, status)
        return identity

    def _preload(self, identity, data, info, status):
        for index in range(info['count']):
            if status['stop'].is_set():
                break
            try:
                result = self._scan(identity, data, info, index)
                review = bool(result.notice)
            except Exception:
                review = True
            with self.lock:
                status['done'] += 1
                status['review'] += int(review)

    def preload_progress(self, identity):
        with self.lock:
            status = self.preloads.get(identity)
            return (status['done'], status['total'], status['review']) if status else (0, 0, 0)

    def cancel_preloads(self):
        with self.lock:
            for status in self.preloads.values():
                status['stop'].set()

    def close(self):
        self.cancel_preloads()
        self.preload_executor.shutdown(wait=True, cancel_futures=True)
        self.executor.shutdown(wait=True, cancel_futures=True)

    def prepare(self, entry, index, lookahead=3):
        name, data, info = entry
        identity = sha256(name.encode()+b'\0'+data).hexdigest()
        pages = [index, *range(index+1, min(info['count'], index+1+lookahead))]
        if index > 0:
            pages.append(index-1)
        with self.lock:
            wanted = {(identity, page) for page in pages}
            for key in list(self.jobs):
                future = self.jobs[key]
                if key not in wanted and not future.done() and future.cancel():
                    del self.jobs[key]
            for page in pages:
                key = identity, page
                if key not in self.jobs:
                    self.jobs[key] = self.executor.submit(self._scan, identity, data, info, page)
                self.jobs.move_to_end(key)
            for key in list(self.jobs):
                if len(self.jobs) <= 128:
                    break
                if self.jobs[key].done():
                    del self.jobs[key]
        return identity

    def result(self, identity, index):
        with self.lock:
            future = self.jobs.get((identity, index))
        if future is None or not future.done():
            return None
        try:
            return future.result()
        except Exception:
            return PagePositions(notice='Não foi possível preparar as posições desta página. Você pode continuar a leitura.')
