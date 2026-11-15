from __future__ import annotations

import re
from datetime import date
from html import escape

import chess
import chess.svg

from .coach import SERIOUS, error_id
from .themes import TAG_LABELS, THEMES

CSS = """
:root{--bg:#f7f6f3;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--accent:#2f6f4f;
--bad:#c4363a;--warn:#b7791f;--chip:#efede8}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d20;--ink:#ececee;--muted:#9a9aa1;
--line:#2c2c31;--accent:#5fbf8d;--bad:#f0656a;--warn:#e3a849;--chip:#2a2a2f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:20px;margin:40px 0 12px}h3{font-size:17px;margin:0 0 6px}
.muted{color:var(--muted)}a{color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:20px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:14px 0}
.theme-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:baseline}
.freq{color:var(--muted);font-size:13px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 4px;padding:0;list-style:none}
.links a{display:inline-block;background:var(--chip);border-radius:999px;padding:4px 12px;text-decoration:none;font-size:13px}
.example{display:grid;grid-template-columns:260px 1fr;gap:18px;border-top:1px solid var(--line);padding-top:16px;margin-top:16px}
.example svg{width:100%;height:auto;border-radius:6px}
@media (max-width:640px){.example{grid-template-columns:1fr}.example .board{max-width:320px}}
.move{font-weight:600}.bad{color:var(--bad)}.good{color:var(--accent)}
.tag{display:inline-block;background:var(--chip);border-radius:4px;padding:1px 7px;font-size:12px;margin-right:4px}
.kind-blunder{color:var(--bad)}.kind-mistake{color:var(--warn)}
code{font-family:ui-monospace,Consolas,monospace;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.table-wrap{overflow-x:auto}
ul.plain{padding-left:18px;margin:6px 0}
html{scroll-behavior:smooth}
[id]{scroll-margin-top:64px}
.toc{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);
border-bottom:1px solid var(--line)}
.toc ul{max-width:980px;margin:0 auto;padding:0 16px;display:flex;gap:4px;list-style:none;overflow-x:auto;scrollbar-width:none}
.toc a{display:block;white-space:nowrap;padding:12px 10px;font-size:14px;color:var(--muted);text-decoration:none;
border-bottom:2px solid transparent}
.toc a:hover{color:var(--ink)}.toc a.active{color:var(--ink);border-bottom-color:var(--accent)}
.glance{border-left:4px solid var(--accent)}
.glance p{margin:0 0 12px}
.glance ol{margin:0;padding-left:22px}.glance li{margin:6px 0}
.glance li a{font-weight:600;text-decoration:none}.glance li span{color:var(--muted);font-size:13px}
.glance .start{margin:14px 0 0;padding-top:12px;border-top:1px solid var(--line)}
.num-badge{display:inline-grid;place-items:center;min-width:26px;height:26px;border-radius:50%;background:var(--chip);
font-size:13px;font-weight:600;margin-right:8px}
.theme-head h3{display:flex;align-items:center}
.line{display:inline-flex;flex-wrap:wrap;gap:3px 4px;align-items:center;vertical-align:middle}
.mn{color:var(--muted);font:12px ui-monospace,Consolas,monospace}
.step{font:13px ui-monospace,Consolas,monospace;color:var(--ink);background:var(--chip);border:1px solid transparent;
border-radius:5px;padding:1px 6px;cursor:pointer}
.step:hover{border-color:var(--line)}
.step.on{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 18%,var(--chip))}
.replay{font:inherit;background:none;border:0;padding:0;cursor:pointer;text-decoration:underline dotted;text-underline-offset:3px}
"""

TOC_SCRIPT = """<script>
(() => {
  const links = [...document.querySelectorAll('.toc a')];
  const targets = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id));
    });
  }, {rootMargin: '-70px 0px -70% 0px'});
  targets.forEach(t => obs.observe(t));
})();
</script>"""

STEP_SCRIPT = """<script>
(() => {
  const SQ = 45, NS = 'http://www.w3.org/2000/svg';
  const NAMES = {p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king'};
  const el = (tag, attrs) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  };
  const xy = (sq, flip) => {
    const f = sq.charCodeAt(0) - 97, r = +sq[1] - 1;
    return flip ? [(7 - f) * SQ, r * SQ] : [f * SQ, (7 - r) * SQ];
  };
  let current = null;

  function show(btn) {
    const ex = btn.closest('.example'), board = ex.querySelector('.board');
    if (!board.dataset.orig) board.dataset.orig = board.innerHTML;
    ex.querySelectorAll('.step.on').forEach(b => b.classList.remove('on'));
    current = btn;
    if (!btn.classList.contains('step')) { board.innerHTML = board.dataset.orig; return; }
    btn.classList.add('on');
    const flip = board.dataset.flip === '1';
    board.innerHTML = board.dataset.orig;
    const svg = board.querySelector('svg');
    svg.querySelectorAll('use, g, .dyn').forEach(n => n.remove());
    const bg = svg.querySelector('rect');
    const mark = (sq, fill, op) => {
      const [x, y] = xy(sq, flip);
      bg.after(el('rect', {x, y, width: SQ, height: SQ, fill, opacity: op}));
    };
    const uci = btn.dataset.uci;
    mark(uci.slice(0, 2), '#f6e05e', .45);
    mark(uci.slice(2, 4), '#f6e05e', .55);
    if (btn.dataset.check) mark(btn.dataset.check, '#e5484d', .55);
    btn.dataset.fen.split(' ')[0].split('/').forEach((row, i) => {
      let f = 0;
      for (const c of row) {
        if (/\\d/.test(c)) { f += +c; continue; }
        const [x, y] = xy(String.fromCharCode(97 + f) + (8 - i), flip);
        const color = c === c.toUpperCase() ? 'white' : 'black';
        svg.append(el('use', {href: `#${color}-${NAMES[c.toLowerCase()]}`, x, y}));
        f++;
      }
    });
  }

  document.addEventListener('click', e => {
    const btn = e.target.closest('.step, .replay');
    if (btn) show(btn);
  });
  document.addEventListener('keydown', e => {
    if (!current || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
    const ex = current.closest('.example');
    if (current.classList.contains('replay')) {
      const first = ex.querySelector('.line .step');
      if (e.key === 'ArrowRight' && first) { e.preventDefault(); show(first); }
      return;
    }
    const steps = [...current.closest('.line').querySelectorAll('.step')];
    const i = steps.indexOf(current) + (e.key === 'ArrowRight' ? 1 : -1);
    e.preventDefault();
    show(i < 0 ? ex.querySelector('.replay') : steps[Math.min(i, steps.length - 1)]);
  });
})();
</script>"""


SQ = 45  # python-chess piece drawings are 45x45
LIGHT, DARK = "#f0d9b5", "#b58863"

# Shared once per page; every board references these ids.
BOARD_DEFS = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
    + "".join(chess.svg.PIECES.values())
    + f'<pattern id="cb" width="{2 * SQ}" height="{2 * SQ}" patternUnits="userSpaceOnUse">'
    f'<rect width="{2 * SQ}" height="{2 * SQ}" fill="{LIGHT}"/>'
    f'<rect x="{SQ}" width="{SQ}" height="{SQ}" fill="{DARK}"/><rect y="{SQ}" width="{SQ}" height="{SQ}" fill="{DARK}"/>'
    "</pattern></defs></svg>"
)
PIECE_ID = {
    p: f"{'white' if p.isupper() else 'black'}-{chess.piece_name(chess.Piece.from_symbol(p).piece_type)}"
    for p in "pnbrqkPNBRQK"
}


def _xy(square: int, flip: bool) -> tuple[int, int]:
    f, r = chess.square_file(square), chess.square_rank(square)
    return ((7 - f) * SQ, r * SQ) if flip else (f * SQ, (7 - r) * SQ)


def _arrow(move: chess.Move, flip: bool, color: str) -> str:
    (x1, y1), (x2, y2) = (_xy(s, flip) for s in (move.from_square, move.to_square))
    x1, y1, x2, y2 = x1 + SQ / 2, y1 + SQ / 2, x2 + SQ / 2, y2 + SQ / 2
    length = max(1e-6, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    bx, by = x2 - ux * 18, y2 - uy * 18
    px, py = -uy * 11, ux * 11
    return (
        f'<g fill="{color}" stroke="{color}" opacity=".8">'
        f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{bx:.0f}" y2="{by:.0f}" stroke-width="8" stroke-linecap="round"/>'
        f'<polygon points="{x2:.0f},{y2:.0f} {bx + px:.0f},{by + py:.0f} {bx - px:.0f},{by - py:.0f}"/></g>'
    )


def _board_svg(e: dict, color: str) -> str:
    board = chess.Board(e["fen"])
    flip = color == "black"
    parts = [
        f'<svg viewBox="0 0 {8 * SQ} {8 * SQ}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Position before {escape(e["played_san"])}">',
        f'<rect width="{8 * SQ}" height="{8 * SQ}" fill="url(#cb)"/>',
    ]
    if board.is_check():
        x, y = _xy(board.king(board.turn), flip)
        parts.append(f'<rect class="dyn" x="{x}" y="{y}" width="{SQ}" height="{SQ}" fill="#e5484d" opacity=".55"/>')
    for i in range(8):
        file_label = chess.FILE_NAMES[7 - i if flip else i]
        rank_label = chess.RANK_NAMES[i if flip else 7 - i]
        fill = LIGHT if i % 2 == 0 else DARK
        parts.append(f'<text x="{i * SQ + SQ - 3}" y="{8 * SQ - 3}" font-size="9" text-anchor="end" fill="{fill}">{file_label}</text>')
        parts.append(f'<text x="2" y="{i * SQ + 10}" font-size="9" fill="{LIGHT if i % 2 else DARK}">{rank_label}</text>')
    for square, piece in board.piece_map().items():
        x, y = _xy(square, flip)
        parts.append(f'<use href="#{PIECE_ID[piece.symbol()]}" x="{x}" y="{y}"/>')
    parts.append(_arrow(chess.Move.from_uci(e["played_uci"]), flip, "#d6454a"))
    if e["best_uci"]:
        parts.append(_arrow(chess.Move.from_uci(e["best_uci"]), flip, "#2f9e6a"))
    parts.append("</svg>")
    return "".join(parts)


def _opponent(g: dict, public: bool) -> str:
    rating = g["opponent_rating"]
    return f"Opponent ({rating})" if public else f"{g['opponent']} ({rating})"


def _line(board: chess.Board, san_line: str) -> str:
    """Turn a SAN line into buttons that carry the position after each move."""
    board = board.copy(stack=False)
    out = []
    tokens = re.sub(r"(\d+\.+)", r"\1 ", san_line).split()
    for i, tok in enumerate(tokens):
        if tok.rstrip(".").isdigit():
            out.append(f'<span class="mn">{escape(tok)}</span>')
            continue
        try:
            move = board.push_san(tok)
        except ValueError:
            out.append(f'<code>{escape(" ".join(tokens[i:]))}</code>')
            break
        check = f' data-check="{chess.square_name(board.king(board.turn))}"' if board.is_check() else ""
        out.append(
            f'<button type="button" class="step" data-fen="{escape(board.fen())}" '
            f'data-uci="{move.uci()}"{check}>{escape(tok)}</button>'
        )
    return f'<span class="line">{"".join(out)}</span>'


def _example(g: dict, e: dict, comment: str, public: bool) -> str:
    dots = "." if g["color"] == "white" else "..."
    analysis = "https://lichess.org/analysis/" + e["fen"].replace(" ", "_")
    clock = f" · {e['clock']:.0f}s left" if e["clock"] is not None else ""
    tags = "".join(f'<span class="tag">{escape(TAG_LABELS.get(t, t))}</span>' for t in e["tags"])
    start = chess.Board(e["fen"])
    after = start.copy(stack=False)
    after.push(chess.Move.from_uci(e["played_uci"]))
    best = (
        f'Best was <span class="move good">{escape(e["best_san"])}</span>'
        f'<div>{_line(start, e["best_line"])}</div>'
        if e["best_san"]
        else ""
    )
    refutation = (
        f'<div style="margin-top:6px">Punishment: {_line(after, e["refutation"])}</div>' if e["refutation"] else ""
    )
    return f"""
<div class="example">
  <div class="board" data-flip="{int(g['color'] == 'black')}">{_board_svg(e, g["color"])}</div>
  <div>
    <div><span class="kind-{e['kind']}">{e['kind'].capitalize()}</span> · {escape(e['phase'])}{clock}</div>
    <h3>{e['move_no']}{dots} <button type="button" class="replay move bad" title="Back to the position">{escape(e['played_san'])}</button>
      <span class="muted">({escape(e['eval_before'])} → {escape(e['eval_after'])})</span></h3>
    {best}
    {refutation}
    <p>{escape(comment)}</p>
    <div>{tags}</div>
    <p class="muted" style="font-size:13px">vs {escape(_opponent(g, public))} ·
      {escape(g['date'])} · {escape(g['time_class'])} · {escape(g['result'])} ·
      <a href="{escape(g['url'])}">game on chess.com</a> ·
      <a href="{escape(analysis)}">analyse position</a></p>
  </div>
</div>"""


def _theme_card(n: int, t: dict, index: dict, public: bool) -> str:
    meta = THEMES[t["theme_id"]]
    links = "".join(f'<li><a href="{escape(u)}">{escape(label)}</a></li>' for label, u in meta["links"])
    drills = "".join(f"<li>{escape(d)}</li>" for d in t.get("drills", []))
    examples = "".join(
        _example(*index[x["mistake_id"]], x["comment"], public) for x in t["examples"] if x["mistake_id"] in index
    )
    diagnosis = f"<p>{escape(t['diagnosis'])}</p>" if t.get("diagnosis") else ""
    return f"""
<section class="card" id="problem-{n}">
  <div class="theme-head"><h3><span class="num-badge">{n}</span>{escape(t['title'])}</h3>
    <span class="freq">{escape(t['frequency'])}</span></div>
  {diagnosis}
  <p><b>How to fix:</b> {escape(t['how_to_fix'])}</p>
  {f'<ul class="plain">{drills}</ul>' if drills else ''}
  <ul class="links">{links}</ul>
  {examples}
</section>"""


DISCLAIMER = (
    "Game data from the Chess.com Published-Data API. "
    "Not affiliated with or endorsed by Chess.com."
)


def render(username: str, results: list[dict], stats: dict, review: dict, public: bool = False) -> str:
    index = {error_id(gi, e): (g, e) for gi, g in enumerate(results) for e in g["errors"]}
    r = stats["results"]
    kpis = [
        (stats["games"], "games"),
        (f"{r.get('win', 0)} / {r.get('draw', 0)} / {r.get('loss', 0)}", "win / draw / loss"),
        (stats["accuracy"] if stats["accuracy"] is not None else "-", "avg accuracy*"),
        (stats["per_game"]["blunder"], "blunders / game"),
        (stats["per_game"]["mistake"], "mistakes / game"),
        (stats["loss_reasons"].get("timeout", 0), "losses on time"),
    ]
    kpi_html = "".join(f'<div class="kpi"><b>{escape(str(v))}</b><span>{escape(k)}</span></div>' for v, k in kpis)

    shown = [t for t in review["themes"] if t["theme_id"] in THEMES]
    themes = "".join(_theme_card(n, t, index, public) for n, t in enumerate(shown, 1))
    problem_list = "".join(
        f'<li><a href="#problem-{n}">{escape(t["title"])}</a> <span>{escape(t["frequency"])}</span></li>'
        for n, t in enumerate(shown, 1)
    )
    start = (
        f'<p class="start"><b>Start with:</b> {escape(review["training_plan"][0])}</p>'
        if review.get("training_plan")
        else ""
    )
    summary_text = f'<p>{escape(review["summary"])}</p>' if review.get("summary") else ""
    glance = (
        f'<h2 id="summary">At a glance</h2><section class="card glance">{summary_text}'
        f'{f"<ol>{problem_list}</ol>" if problem_list else ""}{start}</section>'
        if summary_text or problem_list
        else ""
    )
    strengths = (
        '<h2 id="strengths">What you do well</h2><section class="card"><ul class="plain">'
        + "".join(f"<li>{escape(s)}</li>" for s in review["strengths"])
        + "</ul></section>"
        if review.get("strengths")
        else ""
    )
    plan = (
        '<h2 id="plan">Training plan</h2><section class="card"><ol>'
        + "".join(f"<li>{escape(s)}</li>" for s in review["training_plan"])
        + "</ol></section>"
        if review.get("training_plan")
        else ""
    )
    nav_items = [("summary", "Summary", glance), ("problems", "Problems", True), ("strengths", "Strengths", strengths),
                 ("plan", "Training plan", plan), ("stats", "Statistics", True), ("openings", "Openings", True),
                 ("games", "Games", True)]
    toc = "".join(f'<li><a href="#{i}">{label}</a></li>' for i, label, present in nav_items if present)

    phase_rows = "".join(
        f'<tr><td>{escape(p)}</td><td class="num">{stats["phases"].get(p, 0)}</td></tr>'
        for p in ("opening", "middlegame", "endgame")
    )
    tag_rows = "".join(
        f'<tr><td>{escape(TAG_LABELS.get(t, t))}</td><td class="num">{n}</td></tr>' for t, n in stats["tags"].most_common()
    )
    def opening_cell(name: str, url: str) -> str:
        return f'<a href="{escape(url)}">{escape(name)}</a>' if url else escape(name)

    open_rows = "".join(
        f'<tr><td>{opening_cell(name, o["url"])}</td>'
        f'<td class="num">{o["games"]}</td><td class="num">{round(100 * o["points"] / o["games"])}%</td>'
        f'<td class="num">{o["errors"] / o["games"]:.1f}</td></tr>'
        for name, o in list(stats["openings"].items())[:12]
    )
    game_rows = "".join(
        f'<tr><td>{escape(g["date"])}</td><td>{escape(g["time_class"])}</td><td>{escape(g["color"])}</td>'
        f'<td>{escape(_opponent(g, public))}</td><td>{escape(g["result"])} ({escape(g["reason"])})</td>'
        f'<td class="num">{g["accuracy"] if g["accuracy"] is not None else "-"}</td>'
        f'<td class="num">{sum(1 for e in g["errors"] if e["kind"] in SERIOUS)}</td>'
        f'<td><a href="{escape(g["url"])}">open</a></td></tr>'
        for g in results
    )
    by = f"AI review by {escape(review['model'])}" if review.get("model") else "Engine-only review (no AI)"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{'<meta name="robots" content="noindex">' if public else ''}
<title>Chess digest: {escape(username)}</title><style>{CSS}</style></head>
<body>{BOARD_DEFS}
<nav class="toc" aria-label="Sections"><ul>{toc}</ul></nav>
<main>
<h1>Chess digest for {escape(username)}</h1>
<div class="muted">{date.today().isoformat()} · last {stats['games']} games · {by}</div>
<div class="kpis">{kpi_html}</div>
{glance}
<h2 id="problems">Recurring problems</h2>
{themes or '<p class="muted">No recurring problems found.</p>'}
{strengths}
{plan}
<h2 id="stats">Statistics</h2>
<section class="card"><div class="table-wrap">
<table><thead><tr><th>Mistakes + blunders by phase</th><th class="num">count</th></tr></thead><tbody>{phase_rows}</tbody></table>
<br><table><thead><tr><th>Engine-detected pattern</th><th class="num">count</th></tr></thead><tbody>{tag_rows}</tbody></table>
</div></section>
<h2 id="openings">Openings</h2>
<section class="card"><div class="table-wrap"><table><thead><tr><th>Opening</th><th class="num">games</th>
<th class="num">score</th><th class="num">errors/game</th></tr></thead><tbody>{open_rows}</tbody></table></div></section>
<h2 id="games">Games</h2>
<section class="card"><div class="table-wrap"><table><thead><tr><th>Date</th><th>Type</th><th>Color</th><th>Opponent</th>
<th>Result</th><th class="num">Acc.</th><th class="num">Errors</th><th></th></tr></thead><tbody>{game_rows}</tbody></table></div></section>
<p class="muted" style="font-size:13px">*Accuracy uses the Lichess win-chance formula on Stockfish evaluations, so it
will differ from chess.com's CAPS score. Red arrow = your move, green arrow = engine's best move.
Click any move in a line to see that position (← → step through it); click your move to go back.</p>
<p class="muted" style="font-size:13px">{DISCLAIMER}</p>
</main>{TOC_SCRIPT}{STEP_SCRIPT}</body></html>"""
