from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from .analyze import analyze_games
from .coach import SERIOUS, aggregate, ai_review, heuristic_review
from .fetch import FetchError, fetch_recent_games
from .report import render
from .seen import add_seen, load_seen
from .site import publish
from .themes import THEMES


def check_links() -> int:
    import requests

    bad = 0
    for theme in THEMES.values():
        for _, url in theme["links"]:
            try:
                code = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).status_code
            except requests.RequestException as e:
                code = type(e).__name__
            bad += code != 200
            print(f"{'ok ' if code == 200 else 'BAD'} {code} {url}")
    return 1 if bad else 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="chessdigest", description="Review your recent chess.com games")
    p.add_argument("--user", default=os.environ.get("CHESSCOM_USER"), help="chess.com username (or CHESSCOM_USER)")
    p.add_argument("--games", type=int, help="number of games (default 30, or up to 200 with --since-days)")
    p.add_argument("--since-days", type=float, help="only games from the last N days")
    p.add_argument("--time-class", action="append", choices=["bullet", "blitz", "rapid", "daily"],
                   help="only these time classes (repeatable)")
    p.add_argument("--rated-only", action="store_true")
    p.add_argument("--all", action="store_true", help="include games that earlier digests already covered")
    p.add_argument("--depth", type=int, default=14, help="Stockfish depth (default 14)")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--model", default=os.environ.get("CHESS_DIGEST_MODEL", "claude-sonnet-5-5"))
    p.add_argument("--no-ai", action="store_true", help="skip Claude and group mistakes by engine tags only")
    p.add_argument("--publish", action="store_true", help="also write an anonymised copy to the Pages folder")
    p.add_argument("--publish-last", action="store_true", help="publish the previous run without re-analysing")
    p.add_argument("--out", default=os.environ.get("CHESS_DIGEST_OUT", "out"))
    p.add_argument("--site", default=os.environ.get("CHESS_DIGEST_SITE", ".site"),
                   help="checkout of the gh-pages branch")
    p.add_argument("--check-links", action="store_true", help="check the study links and exit")
    return p.parse_args(argv)


def run_review(a: argparse.Namespace, results: list[dict], stats: dict) -> dict:
    if a.no_ai:
        return heuristic_review(results, stats)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("ANTHROPIC_API_KEY is not set, using engine tags only.", file=sys.stderr)
        return heuristic_review(results, stats)

    import anthropic

    print(f"Asking {a.model} for a review...")
    try:
        return ai_review(results, stats, a.model)
    except (anthropic.APIError, RuntimeError, ValueError) as e:
        print(f"AI review failed ({e}), using engine tags only.", file=sys.stderr)
        return heuristic_review(results, stats)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    if a.check_links:
        return check_links()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    last_run = out / "last-run.json"

    if a.publish_last:
        if not last_run.exists():
            print("Nothing to publish yet. Run an analysis first.", file=sys.stderr)
            return 1
        saved = json.loads(last_run.read_text(encoding="utf-8"))
        results = saved["results"]
        page = publish(Path(a.site), saved["user"], results, aggregate(results), saved["review"])
        print(f"Published {page}")
        return 0

    if not a.user:
        print("Set CHESSCOM_USER in .env or pass --user.", file=sys.stderr)
        return 2

    if a.games is None:
        a.games = 200 if a.since_days else 30
    since = time.time() - a.since_days * 86400 if a.since_days else None
    seen_path = out / "seen.json"
    skip = set() if a.all else load_seen(seen_path, a.user)

    window = f" from the last {a.since_days:g} days" if since else ""
    print(f"Fetching up to {a.games} games of {a.user}{window}...")
    try:
        games, skipped = fetch_recent_games(
            a.user, a.games, set(a.time_class or []), a.rated_only, since, skip
        )
    except FetchError as e:
        print(e, file=sys.stderr)
        return 1
    if skipped:
        print(f"Skipped {skipped} games already covered by earlier digests (use --all to include them).")
    if not games:
        print("No new games to analyse.")
        return 0

    print(f"Analysing {len(games)} games with Stockfish (depth {a.depth}, {a.workers} workers)...")

    def progress(k: int, n: int, r: dict) -> None:
        errors = sum(1 for e in r["errors"] if e["kind"] in SERIOUS)
        print(f"  [{k}/{n}] {r['date']} vs {r['opponent']}: {r['result']}, accuracy {r['accuracy']}, "
              f"{errors} mistakes or blunders")

    results = analyze_games(games, a.user, a.depth, out / "cache", a.workers, progress)
    stats = aggregate(results)
    review = run_review(a, results, stats)

    suffix = "" if review.get("model") else "-engine"
    path = out / f"digest-{a.user.lower()}-{datetime.now():%Y%m%d-%H%M%S}{suffix}.html"
    path.write_text(render(a.user, results, stats, review), encoding="utf-8")
    last_run.write_text(json.dumps({"user": a.user, "results": results, "review": review}), encoding="utf-8")
    add_seen(seen_path, a.user, [r["id"] for r in results])
    print(f"Digest written to {path}")

    if a.publish:
        print(f"Published {publish(Path(a.site), a.user, results, stats, review)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
