from __future__ import annotations

import os
import time

import requests

API = "https://api.chess.com/pub"
REPO_URL = "https://github.com/VladKhomich/chess-digest"
# chess.com asks API clients to include contact info so they can reach you before blocking.
USER_AGENT = f"chess-digest/0.2 (+{os.environ.get('CHESS_DIGEST_CONTACT', REPO_URL)})"


class FetchError(RuntimeError):
    pass


def _get(session: requests.Session, url: str) -> dict:
    for attempt in range(4):
        r = session.get(url, timeout=30)
        if r.status_code == 429:
            time.sleep(2**attempt)
            continue
        if r.status_code == 404:
            raise FetchError(f"Not found: {url}")
        r.raise_for_status()
        return r.json()
    raise FetchError(f"Rate limited by chess.com: {url}")


def game_id(game: dict) -> str:
    return game.get("uuid") or game["url"].rstrip("/").rsplit("/", 1)[-1]


def fetch_recent_games(
    username: str,
    limit: int,
    time_classes: set[str] | None = None,
    rated_only: bool = False,
    since: float | None = None,
    skip: set[str] | None = None,
) -> tuple[list[dict], int]:
    """Newest-first finished games, plus how many were skipped because they were in `skip`."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    skip = skip or set()

    archives = _get(session, f"{API}/player/{username.lower()}/games/archives")["archives"]
    games: list[dict] = []
    skipped = 0
    for url in reversed(archives):
        month = _get(session, url).get("games", [])
        if since is not None and month and max(g.get("end_time", 0) for g in month) < since:
            break
        for g in sorted(month, key=lambda g: g.get("end_time", 0), reverse=True):
            if since is not None and g.get("end_time", 0) < since:
                break
            if g.get("rules") != "chess" or "pgn" not in g:
                continue
            if time_classes and g.get("time_class") not in time_classes:
                continue
            if rated_only and not g.get("rated"):
                continue
            if game_id(g) in skip:
                skipped += 1
                continue
            games.append(g)
            if len(games) >= limit:
                return games, skipped
    return games, skipped
