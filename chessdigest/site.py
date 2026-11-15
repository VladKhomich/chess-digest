from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

from .report import CSS, DISCLAIMER, render


def publish(site_dir: Path, username: str, results: list[dict], stats: dict, review: dict) -> Path:
    """Write the public (anonymised) digest into the Pages folder and refresh the digest list."""
    digests = site_dir / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    page = digests / f"{username.lower()}-{now:%Y%m%d-%H%M%S}.html"
    page.write_text(render(username, results, stats, review, public=True), encoding="utf-8")

    manifest_path = digests / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    dates = sorted(g["date"] for g in results)
    r = stats["results"]
    manifest.insert(
        0,
        {
            "file": page.name,
            "published": now.strftime("%Y-%m-%d %H:%M"),
            "user": username,
            "from": dates[0],
            "to": dates[-1],
            "games": stats["games"],
            "record": f"{r.get('win', 0)}/{r.get('draw', 0)}/{r.get('loss', 0)}",
            "accuracy": stats["accuracy"],
            "blunders_per_game": stats["per_game"]["blunder"],
            "ai": bool(review.get("model")),
        },
    )
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (digests / "index.html").write_text(render_index(manifest), encoding="utf-8")
    return page


def render_index(manifest: list[dict]) -> str:
    rows = "".join(
        f'<tr><td><a href="{escape(m["file"])}">{escape(m["from"])} to {escape(m["to"])}</a></td>'
        f'<td>{escape(m["user"])}</td><td class="num">{m["games"]}</td><td class="num">{escape(m["record"])}</td>'
        f'<td class="num">{m["accuracy"] if m["accuracy"] is not None else "-"}</td>'
        f'<td class="num">{m["blunders_per_game"]}</td></tr>'
        for m in manifest
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Chess digests</title><style>{CSS}</style></head>
<body><main>
<p><a href="../">chess-digest</a></p>
<h1>Published digests</h1>
<section class="card"><div class="table-wrap"><table>
<thead><tr><th>Games played</th><th>Player</th><th class="num">games</th><th class="num">W/D/L</th>
<th class="num">accuracy</th><th class="num">blunders/game</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
<p class="muted" style="font-size:13px">{DISCLAIMER}</p>
</main></body></html>"""
