from __future__ import annotations

import json
from collections import Counter, defaultdict

from .themes import PHASE_THEME, TAG_THEME, THEMES

SERIOUS = ("mistake", "blunder")
MAX_EXAMPLES_PER_ISSUE = 2
RECURRING_MIN_GAMES = 3


def error_id(gi: int, e: dict) -> str:
    return f"g{gi}-p{e['ply']}"


def all_errors(results: list[dict]):
    for gi, g in enumerate(results):
        for e in g["errors"]:
            yield gi, g, e


def _serious(g: dict) -> int:
    return sum(1 for e in g["errors"] if e["kind"] in SERIOUS)


def _group_summary(games: list[dict]) -> dict:
    n = len(games) or 1
    accs = [g["accuracy"] for g in games if g["accuracy"] is not None]
    results = Counter(g["result"] for g in games)
    return {
        "games": len(games),
        "win": results.get("win", 0),
        "draw": results.get("draw", 0),
        "loss": results.get("loss", 0),
        "accuracy": round(sum(accs) / len(accs), 1) if accs else None,
        "errors_per_game": round(sum(_serious(g) for g in games) / n, 2),
        "blunders_per_game": round(sum(1 for g in games for e in g["errors"] if e["kind"] == "blunder") / n, 2),
        "losses_on_time": sum(1 for g in games if g["result"] == "loss" and g["reason"] == "timeout"),
    }


def aggregate(results: list[dict]) -> dict:
    serious = [(gi, g, e) for gi, g, e in all_errors(results) if e["kind"] in SERIOUS]
    kinds = Counter(e["kind"] for _, _, e in all_errors(results))
    n = len(results) or 1

    by_class: dict[str, list[dict]] = defaultdict(list)
    for g in results:
        by_class[g["time_class"]].append(g)

    tag_games: dict[str, set[int]] = defaultdict(set)
    tag_count: Counter = Counter()
    for gi, _, e in serious:
        for t in e["tags"]:
            tag_count[t] += 1
            tag_games[t].add(gi)

    openings: dict[str, dict] = defaultdict(
        lambda: {"games": 0, "points": 0.0, "opening_errors": 0, "later_errors": 0, "url": ""}
    )
    for g in results:
        o = openings[g["opening"]]
        o["games"] += 1
        o["points"] += {"win": 1, "draw": 0.5}.get(g["result"], 0)
        for e in g["errors"]:
            if e["kind"] in SERIOUS:
                o["opening_errors" if e["phase"] == "opening" else "later_errors"] += 1
        o["url"] = g["eco_url"]

    accs = [g["accuracy"] for g in results if g["accuracy"] is not None]
    dates = sorted(g["date"] for g in results)
    return {
        "games": len(results),
        "from": dates[0] if dates else None,
        "to": dates[-1] if dates else None,
        "results": Counter(g["result"] for g in results),
        "loss_reasons": Counter(g["reason"] for g in results if g["result"] == "loss"),
        "accuracy": round(sum(accs) / len(accs), 1) if accs else None,
        "kinds": kinds,
        "per_game": {k: round(kinds[k] / n, 2) for k in ("inaccuracy", "mistake", "blunder")},
        "by_time_class": {tc: _group_summary(gs) for tc, gs in sorted(by_class.items(), key=lambda kv: -len(kv[1]))},
        "phases": Counter(e["phase"] for _, _, e in serious),
        "tag_stats": {t: {"count": c, "games": len(tag_games[t])} for t, c in tag_count.most_common()},
        "openings": dict(sorted(openings.items(), key=lambda kv: -kv[1]["games"])),
    }


def history_entries(stats: dict) -> list[dict]:
    """One comparable row per time class, stored in out/history.json after each run."""
    return [
        {"from": stats["from"], "to": stats["to"], "time_class": tc, **summary}
        for tc, summary in stats["by_time_class"].items()
    ]


def select_errors(results: list[dict], limit: int = 200) -> list[tuple[str, int, dict, dict]]:
    picked = [(error_id(gi, e), gi, g, e) for gi, g, e in all_errors(results) if e["kind"] in SERIOUS]
    picked.sort(key=lambda x: -x[3]["drop"])
    return picked[:limit]


SYSTEM = """You write a personal digest that a club chess player reads after a playing session.
It answers: what happened, what mattered, and what to watch for in the next game. It is selective, but it must
represent the whole session, not just its most dramatic blunders.
You get Stockfish-annotated mistakes, per-time-control statistics, pattern counts, targets for how much to write,
and sometimes earlier sessions.

Write these parts:
- takeaways: exactly three short findings, most important first, one or two sentences each. Together they
  cover the session: results by time control, where the serious errors concentrate, and what stands out.
  Say when a sample is too small to support a conclusion. Leave pattern counts out; the report shows them.
- issues: targets.issues distinct issues (fewer if the evidence does not support that many), most important
  first. An issue is a distinct mechanism: missing your own mate, allowing mate, leaving the queen capturable,
  allowing a knight fork, an endgame technique problem, an opening habit, clock trouble. Do not merge different
  mechanisms into one broad issue, and do not split one mechanism into two.
  - evidence_ids: every flagged mistake that fits this issue, not just the examples.
  - examples: one main example; add a second only when it shows a different situation or mechanism.
    Across all issues, use about targets.positions distinct positions and never reuse a position.
  - explanation: what goes wrong and when it tends to happen, with at most two short game references. The report
    prints a verified count ("N mistakes in M games") above it, so do not state counts or totals.
  - Call an issue a pattern only if it shows up in at least 3 different games; otherwise it is a notable mistake.
- Each example has a headline (under 10 words) and one or two plain sentences: what was overlooked and what it
  cost. Do not recite the engine line; it is shown next to your text.
- reminder: one concrete thing to watch for in the next game, specific to these games, under 25 words.
  No generic advice such as "do more puzzles".
- positive: one positive finding the data supports, or an empty string.
- history_note: if history has rows for the same time control, one or two sentences comparing them, with the
  number of games on each side. Do not call a trend from small samples. Otherwise an empty string.

Coverage when choosing issues and examples:
- Cover the phases where errors actually happened. If the endgame has a meaningful share, include an endgame
  issue or at least an instructive endgame example.
- Include a rapid or daily example when it adds a finding that blitz does not already explain.
- Include errors from games you won (game_result "win"); opponents not punishing a mistake does not make it fine.
- Prefer a clear example over a dramatic one, and avoid two examples that teach the same thing.

Rules:
- Every evaluation is from the player's side: positive is good for the player.
- game_went is what was actually played after the mistake. refutation is the engine's best reply line.
  Never say the opponent played the refutation unless game_went shows it.
- The low_clock tag means at most 10% of the starting time was left. It is context, not a diagnosis. Treat time
  management as an issue only with losses on time or low-clock errors in at least 3 games.
- Keep time controls apart. One long rapid game must not drive conclusions about blitz.
- For openings, separate errors made in the opening phase from errors later in games that began with it.
- Address the player as "you". Refer to a game by date, time control and opponent rating, and to a move by
  number and notation (e.g. "in the Nov 15 blitz game against a 1450, 22. b3"). Never mention internal ids.
- Plain language, no URLs, no headings or markdown."""


def targets(serious_errors: int) -> dict:
    """How much to write, scaled to the session: a 5-game session gets 2 issues and 3 positions."""
    return {
        "issues": max(2, min(7, round(serious_errors / 18) + 1)),
        "positions": max(3, min(12, round(serious_errors / 10))),
    }


def _schema(ids: list[str]) -> dict:
    example = {
        "type": "object",
        "properties": {
            "mistake_id": {"type": "string", "enum": ids},
            "headline": {"type": "string"},
            "explanation": {"type": "string"},
        },
        "required": ["mistake_id", "headline", "explanation"],
        "additionalProperties": False,
    }
    issue = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "theme_id": {"type": "string", "enum": list(THEMES)},
            "evidence_ids": {"type": "array", "items": {"type": "string", "enum": ids}},
            "explanation": {"type": "string"},
            "examples": {"type": "array", "items": example},
        },
        "required": ["title", "theme_id", "evidence_ids", "explanation", "examples"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "takeaways": {"type": "array", "items": {"type": "string"}},
            "issues": {"type": "array", "items": issue},
            "reminder": {"type": "string"},
            "positive": {"type": "string"},
            "history_note": {"type": "string"},
        },
        "required": ["takeaways", "issues", "reminder", "positive", "history_note"],
        "additionalProperties": False,
    }


def _payload(results: list[dict], stats: dict, picked, history: list[dict]) -> str:
    """Game data for Claude. Opponent usernames are left out on purpose; ratings are enough."""
    games = [
        {
            "game": f"g{gi}",
            "date": g["date"],
            "time_class": g["time_class"],
            "time_control": g["time_control"],
            "color": g["color"],
            "result": g["result"],
            "reason": g["reason"],
            "opening": g["opening"],
            "accuracy": g["accuracy"],
            "rating": g["user_rating"],
            "opponent_rating": g["opponent_rating"],
            "serious_errors": _serious(g),
        }
        for gi, g in enumerate(results)
    ]
    mistakes = [
        {
            "id": mid,
            "game": f"g{gi}",
            "date": g["date"],
            "time_class": g["time_class"],
            "game_result": g["result"],
            "opponent_rating": g["opponent_rating"],
            "color": g["color"],
            "move": f"{e['move_no']}{'.' if g['color'] == 'white' else '...'} {e['played_san']}",
            "best": e["best_san"],
            "best_line": e["best_line"],
            "refutation": e["refutation"],
            "game_went": e.get("game_went", ""),
            "eval_for_player": f"{e['eval_before']} -> {e['eval_after']}",
            "win_chance_drop": e["drop"],
            "kind": e["kind"],
            "phase": e["phase"],
            "clock_s": e["clock"],
            "tags": e["tags"],
            "fen": e["fen"],
        }
        for mid, gi, g, e in picked
    ]
    stats_out = {k: v for k, v in stats.items() if k not in ("openings", "tag_stats")}
    stats_out["tag_stats"] = stats["tag_stats"]
    stats_out["openings"] = {
        k: {kk: vv for kk, vv in v.items() if kk != "url"} for k, v in list(stats["openings"].items())[:12]
    }
    return json.dumps(
        {
            "targets": targets(len(picked)),
            "stats": stats_out,
            "history": history,
            "games": games,
            "mistakes": mistakes,
        },
        ensure_ascii=False,
    )


def finalize(review: dict, results: list[dict]) -> dict:
    """Verify ids, keep every position unique across issues, and attach evidence counts."""
    index = {error_id(gi, e): (gi, g, e) for gi, g, e in all_errors(results)}
    used: set[str] = set()
    for issue in review.get("issues", []):
        examples = []
        for x in issue.get("examples", []):
            if x["mistake_id"] in index and x["mistake_id"] not in used and len(examples) < MAX_EXAMPLES_PER_ISSUE:
                used.add(x["mistake_id"])
                examples.append(x)
        issue["examples"] = examples
        ids = [i for i in dict.fromkeys(issue["evidence_ids"] + [x["mistake_id"] for x in examples]) if i in index]
        issue["evidence_ids"] = ids
        issue["count"] = len(ids)
        issue["games"] = len({index[i][0] for i in ids})
        issue["by_class"] = dict(Counter(index[i][1]["time_class"] for i in ids))
        issue["recurring"] = issue["games"] >= RECURRING_MIN_GAMES
        shown = {x["mistake_id"] for x in examples}
        issue["more"] = sorted((i for i in ids if i not in shown), key=lambda i: -index[i][2]["drop"])
    review["positions"] = len(used)
    return review


def ai_review(results: list[dict], stats: dict, model: str, history: list[dict]) -> dict:
    import anthropic

    picked = select_errors(results)
    if not picked:
        return {"takeaways": ["No mistakes or blunders in these games."], "issues": [], "reminder": "",
                "positive": "", "history_note": "", "positions": 0, "model": None}

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=model,
        max_tokens=20000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        messages=[{"role": "user", "content": _payload(results, stats, picked, history)}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": _schema([p[0] for p in picked])}},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude's response was cut off (max_tokens)")
    text = next(b.text for b in response.content if b.type == "text")
    review = json.loads(text)
    review["model"] = response.model
    return finalize(review, results)


def heuristic_review(results: list[dict], stats: dict) -> dict:
    """Issues from engine tags only, used with --no-ai."""
    picked = select_errors(results, limit=1000)
    by_theme: dict[str, list[str]] = defaultdict(list)
    for mid, _, _, e in picked:
        themes = {TAG_THEME[t] for t in e["tags"] if t in TAG_THEME}
        if not themes and e["phase"] in PHASE_THEME:
            themes = {PHASE_THEME[e["phase"]]}
        for t in themes:
            by_theme[t].append(mid)
    goal = targets(len(picked))
    ranked = sorted(by_theme.items(), key=lambda kv: -len(kv[1]))[: goal["issues"]]
    used: set[str] = set()
    issues = []
    for tid, ids in ranked:
        first = next((i for i in ids if i not in used), None)
        if first:
            used.add(first)
        issues.append({
            "title": THEMES[tid]["title"],
            "theme_id": tid,
            "evidence_ids": ids,
            "explanation": THEMES[tid]["tip"],
            "examples": [{"mistake_id": first, "headline": "", "explanation": ""}] if first else [],
        })
    review = {
        "takeaways": [],
        "issues": issues,
        "reminder": "",
        "positive": "",
        "history_note": "",
        "model": None,
    }
    return finalize(review, results)
