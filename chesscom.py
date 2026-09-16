"""Read-only Chess.com public archives. Requests are sequential and bounded."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://api.chess.com/pub/player/"


def normalize_username(username: str) -> str:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]{2,50}", username):
        raise ValueError("Informe apenas o nome de usuário do Chess.com, sem o endereço do site.")
    return username


def get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "AcervoChess/1.0 (personal chess study)",
                                    "Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            data = response.read(20_000_001)
        if len(data) > 20_000_000:
            raise ValueError("O arquivo mensal excedeu o limite de 20 MB.")
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError("Resposta inesperada do Chess.com.")
        return result
    except HTTPError as error:
        messages = {404: "Usuário ou mês não encontrado no Chess.com.",
                    429: "O Chess.com limitou as consultas. Aguarde e tente novamente.",
                    403: "O Chess.com recusou a consulta. Tente novamente mais tarde."}
        raise ValueError(messages.get(error.code, f"Chess.com indisponível (HTTP {error.code}).")) from error
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise ValueError("Não foi possível consultar o Chess.com. Verifique sua conexão e tente novamente.") from error


def fetch_archives(username: str) -> list[str]:
    user = normalize_username(username)
    prefix = f"{API}{user}/games/"
    # Only return validated months; never fetch an arbitrary URL from a response.
    return sorted({url[len(prefix):] for url in get_json(prefix + "archives").get("archives", [])
                   if isinstance(url, str) and url.startswith(prefix)
                   and re.fullmatch(r"\d{4}/(0[1-9]|1[0-2])", url[len(prefix):])}, reverse=True)


def fetch_games(username: str, month: str) -> list[dict]:
    user = normalize_username(username)
    if not re.fullmatch(r"\d{4}/(0[1-9]|1[0-2])", month):
        raise ValueError("Mês inválido.")
    games = get_json(f"{API}{user}/games/{month}").get("games", [])
    return sorted([g for g in games if isinstance(g, dict) and g.get("rules") == "chess" and g.get("pgn")],
                  key=lambda g: g.get("end_time", 0), reverse=True)


def fetch_recent_games(username: str, limit: int = 100, max_months: int = 12) -> list[dict]:
    """Fill one recent-games picker across months, without parallel API requests."""
    user = normalize_username(username)
    games, seen = [], set()
    for month in fetch_archives(user)[:max_months]:
        for game in fetch_games(user, month):
            identity = game.get("url") or game["pgn"]
            if identity not in seen:
                seen.add(identity)
                games.append(game)
        if len(games) >= limit:
            break
    return sorted(games, key=lambda game: game.get("end_time", 0), reverse=True)[:limit]
