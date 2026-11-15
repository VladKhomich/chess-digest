from __future__ import annotations

import json
from collections import Counter, defaultdict

from .themes import PHASE_THEME, TAG_THEME, THEMES

SERIOUS = ("mistake", "blunder")


def error_id(gi: int, e: dict) -> str:
    return f"g{gi}-p{e['ply']}"


def all_errors(results: list[dict]):
    for gi, g in enumerate(results):
        for e in g["errors"]:
            yield gi, g, e


def aggregate(results: list[dict]) -> dict:
    serious = [(gi, g, e) for gi, g, e in all_errors(results) if e["kind"] in SERIOUS]
    kinds = Counter(e["kind"] for _, _, e in all_errors(results))
    openings: dict[str, dict] = defaultdict(lambda: {"games": 0, "points": 0.0, "errors": 0, "url": ""})
    for g in results:
        o = openings[g["opening"]]
        o["games"] += 1
        o["points"] += {"win": 1, "draw": 0.5}.get(g["result"], 0)
        o["errors"] += sum(1 for e in g["errors"] if e["kind"] in SERIOUS)
        o["url"] = g["eco_url"]
    accs = [g["accuracy"] for g in results if g["accuracy"] is not None]
    n = len(results) or 1
    return {
        "games": len(results),
        "results": Counter(g["result"] for g in results),
        "loss_reasons": Counter(g["reason"] for g in results if g["result"] == "loss"),
        "time_classes": Counter(g["time_class"] for g in results),
        "accuracy": round(sum(accs) / len(accs), 1) if accs else None,
        "kinds": kinds,
        "per_game": {k: round(kinds[k] / n, 2) for k in ("inaccuracy", "mistake", "blunder")},
        "phases": Counter(e["phase"] for _, _, e in serious),
        "tags": Counter(t for _, _, e in serious for t in e["tags"]),
        "openings": dict(sorted(openings.items(), key=lambda kv: -kv[1]["games"])),
    }


def select_errors(results: list[dict], limit: int = 80) -> list[tuple[str, int, dict, dict]]:
    picked = [(error_id(gi, e), gi, g, e) for gi, g, e in all_errors(results) if e["kind"] in SERIOUS]
    picked.sort(key=lambda x: -x[3]["drop"])
    return picked[:limit]


SYSTEM = """You are an experienced chess coach reviewing a club player's recent games.
You receive Stockfish-annotated mistakes and aggregate statistics. Find the player's RECURRING problems,
not one-off accidents, and explain them so the player can fix them.

Rules:
- Ground every explanation in the engine data given (played move, best move, best line, refutation line,
  tags). Never invent variations or claim tactics that the lines do not show. If unsure why a move is bad,
  describe it at the level the data supports.
- Pick 3-5 themes ranked by practical impact (how often x how costly). Use only theme ids from the schema.
- For each theme pick up to 3 of the clearest example mistake ids.
- Be concrete and direct; write for a player, not an engine. Short paragraphs.
- Address the player as "you". Never mention internal ids (like g3 or g3-p40) in text. Refer to a game
  by date, time control and opponent rating, and to a move by number and notation
  (e.g. "in the Nov 15 blitz game against a 1450, 22. b3").
- Do not output URLs; links are added separately."""


def _schema(ids: list[str]) -> dict:
    example = {
        "type": "object",
        "properties": {"mistake_id": {"type": "string", "enum": ids}, "comment": {"type": "string"}},
        "required": ["mistake_id", "comment"],
        "additionalProperties": False,
    }
    theme = {
        "type": "object",
        "properties": {
            "theme_id": {"type": "string", "enum": list(THEMES)},
            "title": {"type": "string"},
            "frequency": {"type": "string"},
            "diagnosis": {"type": "string"},
            "how_to_fix": {"type": "string"},
            "drills": {"type": "array", "items": {"type": "string"}},
            "examples": {"type": "array", "items": example},
        },
        "required": ["theme_id", "title", "frequency", "diagnosis", "how_to_fix", "drills", "examples"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "themes": {"type": "array", "items": theme},
            "training_plan": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "strengths", "themes", "training_plan"],
        "additionalProperties": False,
    }


def _payload(results: list[dict], stats: dict, picked) -> str:
    """Game data for Claude. Opponent usernames are left out on purpose; ratings are enough."""
    games = [
        {
            "game": f"g{gi}",
            "date": g["date"],
            "color": g["color"],
            "result": g["result"],
            "reason": g["reason"],
            "time_class": g["time_class"],
            "opening": g["opening"],
            "accuracy": g["accuracy"],
            "rating": g["user_rating"],
            "opponent_rating": g["opponent_rating"],
        }
        for gi, g in enumerate(results)
    ]
    mistakes = [
        {
            "id": mid,
            "game": f"g{gi}",
            "date": g["date"],
            "time_class": g["time_class"],
            "opponent_rating": g["opponent_rating"],
            "color": g["color"],
            "move": f"{e['move_no']}{'.' if g['color'] == 'white' else '...'} {e['played_san']}",
            "best": e["best_san"],
            "best_line": e["best_line"],
            "refutation": e["refutation"],
            "eval": f"{e['eval_before']} -> {e['eval_after']}",
            "win_chance_drop": e["drop"],
            "kind": e["kind"],
            "phase": e["phase"],
            "clock_s": e["clock"],
            "tags": e["tags"],
            "fen": e["fen"],
        }
        for mid, gi, g, e in picked
    ]
    stats_out = {k: v for k, v in stats.items() if k != "openings"}
    stats_out["openings"] = {
        k: {kk: vv for kk, vv in v.items() if kk != "url"} for k, v in list(stats["openings"].items())[:12]
    }
    return json.dumps({"stats": stats_out, "games": games, "mistakes": mistakes}, ensure_ascii=False)


def ai_review(results: list[dict], stats: dict, model: str) -> dict:
    import anthropic

    picked = select_errors(results)
    if not picked:
        return {
            "summary": "No mistakes or blunders in these games.",
            "strengths": [],
            "themes": [],
            "training_plan": [],
            "model": None,
        }

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        messages=[{"role": "user", "content": _payload(results, stats, picked)}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": _schema([p[0] for p in picked])}},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude's response was cut off (max_tokens)")
    text = next(b.text for b in response.content if b.type == "text")
    review = json.loads(text)
    review["model"] = response.model
    return review


def heuristic_review(results: list[dict], stats: dict) -> dict:
    """Theme grouping from engine tags only, used with --no-ai."""
    picked = select_errors(results, limit=1000)
    by_theme: dict[str, list] = defaultdict(list)
    for mid, _, _, e in picked:
        themes ={TAG_THEME[t] for t in e["tags"] if t in TAG_THEME}
        if not themes and e["phase"] in PHASE_THEME:
            themes = {PHASE_THEME[e["phase"]]}
        for t in themes:
            by_theme[t].append((mid, e))
    ranked = sorted(by_theme.items(), key=lambda kv: -sum(e["drop"] for _, e in kv[1]))[:5]
    shown: set[str] = set()
    themes = []
    for tid, items in ranked:
        examples = [mid for mid, _ in items if mid not in shown][:3]
        shown.update(examples)
        themes.append(
            {
                "theme_id": tid,
                "title": THEMES[tid]["title"],
                "frequency": f"{len(items)} mistakes/blunders",
                "diagnosis": "",
                "how_to_fix": THEMES[tid]["tip"],
                "drills": [],
                "examples": [{"mistake_id": mid, "comment": ""} for mid in examples],
            }
        )
    return {"summary": "", "strengths": [], "themes": themes, "training_plan": [], "model": None}
