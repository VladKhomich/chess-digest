from __future__ import annotations

import re
from datetime import datetime
from html import escape

import chess
import chess.svg

from .coach import SERIOUS, error_id
from .themes import TAG_LABELS, THEMES

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600'
    '&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'
)

CSS = """
:root{--bg:#f6f3ec;--card:#fffdf8;--sunken:#efe9dc;--ink:#1b1a17;--muted:#6d675c;--line:#e4dccb;--accent:#2f6f4f;
--bad:#c4363a;--warn:#b7791f;--chip:#efe9dc;--shadow:0 1px 2px rgba(40,30,10,.05),0 8px 24px rgba(40,30,10,.07)}
@media (prefers-color-scheme:dark){:root{--bg:#121311;--card:#1b1c19;--sunken:#161714;--ink:#ecebe6;--muted:#a29d92;
--line:#2c2d29;--accent:#6fcf9b;--bad:#f0656a;--warn:#e3a849;--chip:#262723;--shadow:0 1px 2px rgba(0,0,0,.3),0 10px 28px rgba(0,0,0,.35)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15.5px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
-webkit-font-smoothing:antialiased;overflow-x:clip}
main{max-width:1000px;margin:0 auto;padding:36px 16px 72px}
h1,h2,h3{font-family:Fraunces,Georgia,serif;font-weight:600;letter-spacing:-.01em;line-height:1.2}
h1{font-size:34px;margin:0 0 6px}h2{font-size:24px;margin:48px 0 14px}h3{font-size:19px;margin:0 0 8px}
.muted{color:var(--muted)}a{color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;margin:14px 0;box-shadow:var(--shadow)}
.sub{color:var(--muted);margin-bottom:22px}
.takeaway{font-size:17.5px;margin:0 0 16px}
.reminder{display:flex;gap:12px;align-items:flex-start;background:color-mix(in srgb,var(--accent) 11%,transparent);
border-radius:10px;padding:12px 14px;margin:0 0 14px}
.reminder b{flex:none;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);padding-top:3px}
.note{margin:10px 0 0;color:var(--muted)}.note b{color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.table-wrap{overflow-x:auto}
.badge{display:inline-block;font:600 11px/1 Inter,sans-serif;letter-spacing:.06em;text-transform:uppercase;border-radius:999px;
padding:5px 9px;margin-bottom:10px}
.badge.recurring{background:color-mix(in srgb,var(--bad) 15%,transparent);color:var(--bad)}
.badge.notable{background:var(--chip);color:var(--muted)}
.evidence{color:var(--muted);font-size:14px;margin:-2px 0 10px}
.obs p{margin:0 0 10px}
.obs-foot{font-size:14px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 14px}
.obs-foot a{text-decoration:none;font-weight:600}
.moment{display:grid;grid-template-columns:280px minmax(0,1fr);gap:22px}
.moment .board svg{width:100%;height:auto;border-radius:8px;display:block}
@media (max-width:700px){.moment{grid-template-columns:minmax(0,1fr)}.moment .board{max-width:340px}}
.moment-top{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;font-size:13px;color:var(--muted);margin-bottom:8px}
.num-badge{display:inline-grid;place-items:center;min-width:26px;height:26px;border-radius:50%;background:var(--ink);
color:var(--bg);font:600 13px Inter,sans-serif}
.kind-blunder{color:var(--bad);font-weight:600}.kind-mistake{color:var(--warn);font-weight:600}
.explain{margin:0 0 14px}
.facts{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:6px 14px;margin:0 0 12px;font-size:14px}
.facts dt{color:var(--muted)}.facts dd{margin:0}
.move{font-weight:600}.bad{color:var(--bad)}.good{color:var(--accent)}
.chip{display:inline-block;background:var(--chip);border-radius:5px;padding:1px 7px;font-size:12px;color:var(--muted)}
details{font-size:14px;margin:0 0 10px}summary{cursor:pointer;color:var(--muted)}
details > div{margin:8px 0 0}
.game-links{font-size:13px;color:var(--muted)}
html{scroll-behavior:smooth}
[id]{scroll-margin-top:64px}
.toc{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);
border-bottom:1px solid var(--line)}
.toc ul{max-width:1000px;margin:0 auto;padding:0 16px;display:flex;gap:4px;list-style:none;overflow-x:auto;scrollbar-width:none}
.toc a{display:block;white-space:nowrap;padding:12px 10px;font-size:14px;color:var(--muted);text-decoration:none;
border-bottom:2px solid transparent}
.toc a:hover{color:var(--ink)}.toc a.active{color:var(--ink);border-bottom-color:var(--accent)}
.line{display:inline-flex;flex-wrap:wrap;gap:3px 4px;align-items:center;vertical-align:middle}
.mn{color:var(--muted);font:12px ui-monospace,Consolas,monospace}
.step{font:13px ui-monospace,Consolas,monospace;color:var(--ink);background:var(--chip);border:1px solid transparent;
border-radius:5px;padding:1px 6px;cursor:pointer}
.step:hover{border-color:var(--line)}
.step.on{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 18%,var(--chip))}
.replay{font:inherit;background:none;border:0;padding:0;cursor:pointer;text-decoration:underline dotted;text-underline-offset:3px}
code{font-family:ui-monospace,Consolas,monospace;font-size:13px}
.method{font-size:14px;color:var(--muted)}.method li{margin:4px 0}
.takeaways{margin:0 0 16px;padding-left:22px;font-size:16.5px}.takeaways li{margin:0 0 8px;padding-left:4px}
.takeaways li::marker{font-family:Fraunces,Georgia,serif;font-weight:600;color:var(--accent)}
.coverage{font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px;margin:14px 0 6px}
.issue-index{padding:16px 22px 16px 44px;margin:0 0 26px}.issue-index li{margin:5px 0}
.issue-index a{font-weight:600;text-decoration:none}.issue-index span{color:var(--muted);font-size:13px}
.issue{margin:0 0 38px}
.issue-top{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.issue-top .badge{margin:0}
.issue-no{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:9px;background:var(--accent);
color:var(--bg);font:600 15px Fraunces,Georgia,serif}
.issue-body{margin-left:14px;padding-left:18px;border-left:3px solid var(--line)}
@media (max-width:600px){.issue-body{margin-left:4px;padding-left:10px}}
.more summary{font-weight:600;color:var(--ink)}.more table{margin-top:10px;font-size:13px}
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


def _short_date(iso: str | None) -> str:
    if not iso:
        return ""
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d:%b} {d.day}"


def _moment(n: int, m: dict, g: dict, e: dict, public: bool) -> str:
    dots = "." if g["color"] == "white" else "..."
    start = chess.Board(e["fen"])
    after = start.copy(stack=False)
    after.push(chess.Move.from_uci(e["played_uci"]))
    analysis = "https://lichess.org/analysis/" + e["fen"].replace(" ", "_")
    clock = f"{e['clock']:.0f}s left" if e["clock"] is not None else ""
    tags = "".join(f'<span class="chip">{escape(TAG_LABELS.get(t, t))}</span>' for t in e["tags"])
    headline = m.get("headline") or f"{e['move_no']}{dots} {e['played_san']}"
    explanation = f'<p class="explain">{escape(m["explanation"])}</p>' if m.get("explanation") else ""

    facts = [
        ("You played", f'{e["move_no"]}{dots} <button type="button" class="replay move bad" '
                       f'title="Back to the position">{escape(e["played_san"])}</button>'),
        ("Eval for you", f'{escape(e["eval_before"])} → {escape(e["eval_after"])}'),
    ]
    if e["best_san"]:
        facts.append(("Better", f'<span class="move good">{escape(e["best_san"])}</span>'))
    if e.get("game_went"):
        facts.append(("The game went", _line(after, e["game_went"])))
    facts_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)

    engine = []
    if e["best_line"]:
        engine.append(f"<div>Best line: {_line(start, e['best_line'])}</div>")
    if e["refutation"]:
        engine.append(f"<div>Engine's reply to {escape(e['played_san'])}: {_line(after, e['refutation'])}</div>")
    engine_html = f"<details><summary>Engine lines</summary>{''.join(engine)}</details>" if engine else ""

    meta = " · ".join(
        x for x in (escape(e["phase"]), escape(g["time_class"]), f"vs {escape(_opponent(g, public))}",
                    _short_date(g["date"]), clock) if x
    )
    return f"""
<article class="card example moment" id="moment-{n}">
  <div class="board" data-flip="{int(g['color'] == 'black')}">{_board_svg(e, g["color"])}</div>
  <div>
    <div class="moment-top"><span class="num-badge">{n}</span>
      <span class="kind-{e['kind']}">{e['kind'].capitalize()}</span><span>{meta}</span>{tags}</div>
    <h3>{escape(headline)}</h3>
    {explanation}
    <dl class="facts">{facts_html}</dl>
    {engine_html}
    <div class="game-links"><a href="{escape(g['url'])}">Game on chess.com</a> ·
      <a href="{escape(analysis)}">Analyse position</a></div>
  </div>
</article>"""


def _more_row(g: dict, e: dict, public: bool) -> str:
    dots = "." if g["color"] == "white" else "..."
    analysis = "https://lichess.org/analysis/" + e["fen"].replace(" ", "_")
    tags = " ".join(f'<span class="chip">{escape(TAG_LABELS.get(t, t))}</span>' for t in e["tags"])
    better = f" (better {escape(e['best_san'])})" if e["best_san"] else ""
    return (
        f'<tr><td>{_short_date(g["date"])}</td><td>{escape(g["time_class"])}</td>'
        f'<td>{escape(_opponent(g, public))}, {escape(g["result"])}</td>'
        f'<td><span class="move">{e["move_no"]}{dots} {escape(e["played_san"])}</span>{better}</td>'
        f'<td class="num">{escape(e["eval_before"])} → {escape(e["eval_after"])}</td>'
        f'<td>{escape(e["phase"])} {tags}</td>'
        f'<td><a href="{escape(g["url"])}">game</a> · <a href="{escape(analysis)}">position</a></td></tr>'
    )


def _issue(k: int, issue: dict, index: dict, numbers: dict, total_games: int, public: bool) -> str:
    meta = THEMES.get(issue["theme_id"], {})
    badge = ("recurring", "Recurring") if issue.get("recurring") else ("notable", "Notable")
    per_class = ", ".join(f"{tc} {n}" for tc, n in issue.get("by_class", {}).items())
    count = issue.get("count", 0)
    evidence = (
        f'{count} flagged {"mistake" if count == 1 else "mistakes"} in {issue.get("games", 0)} of {total_games} games'
        + (f" ({per_class})" if per_class else "")
    )
    practice = ""
    if meta.get("links"):
        label, url = meta["links"][0]
        practice = f'<div class="obs-foot"><span>Practice: <a href="{escape(url)}">{escape(label)}</a></span></div>'
    boards = "".join(
        _moment(numbers[x["mistake_id"]], x, *index[x["mistake_id"]], public) for x in issue["examples"]
    )
    more_ids = issue.get("more", [])
    more = ""
    if more_ids:
        rows = "".join(_more_row(*index[i], public) for i in more_ids)
        word = "example" if len(more_ids) == 1 else "examples"
        more = (
            f'<details class="card more"><summary>{len(more_ids)} more {word} of this issue</summary>'
            '<div class="table-wrap"><table><thead><tr><th>Date</th><th>Type</th><th>Opponent</th><th>Move</th>'
            f'<th class="num">eval for you</th><th>Phase</th><th></th></tr></thead><tbody>{rows}</tbody></table></div></details>'
        )
    return f"""
<section class="issue" id="issue-{k}">
  <div class="card obs">
    <div class="issue-top"><span class="issue-no">{k}</span><span class="badge {badge[0]}">{badge[1]}</span></div>
    <h3>{escape(issue['title'])}</h3>
    <p class="evidence">{escape(evidence)}</p>
    <p>{escape(issue['explanation'])}</p>
    {practice}
  </div>
  <div class="issue-body">{boards}{more}</div>
</section>"""


DISCLAIMER = (
    "Game data from the Chess.com Published-Data API. "
    "Not affiliated with or endorsed by Chess.com."
)


def render(username: str, results: list[dict], stats: dict, review: dict, public: bool = False) -> str:
    index = {error_id(gi, e): (g, e) for gi, g in enumerate(results) for e in g["errors"]}
    issues = review.get("issues", [])
    for issue in issues:
        issue["examples"] = [x for x in issue.get("examples", []) if x["mistake_id"] in index]
    numbers: dict[str, int] = {}
    for issue in issues:
        for x in issue["examples"]:
            numbers.setdefault(x["mistake_id"], len(numbers) + 1)
    serious = sum(1 for g in results for e in g["errors"] if e["kind"] in SERIOUS)

    classes = stats["by_time_class"]
    class_line = ", ".join(f"{tc} {s['games']}" for tc, s in classes.items())
    period = f"{_short_date(stats['from'])} to {_short_date(stats['to'])}" if stats["from"] != stats["to"] \
        else _short_date(stats["from"])
    by = f"AI review by {escape(review['model'])}" if review.get("model") else "Engine-only review"

    class_rows = "".join(
        f'<tr><td>{escape(tc)}</td><td class="num">{s["games"]}</td>'
        f'<td class="num">{s["win"]} / {s["draw"]} / {s["loss"]}</td>'
        f'<td class="num">{s["accuracy"] if s["accuracy"] is not None else "-"}</td>'
        f'<td class="num">{s["errors_per_game"]}</td><td class="num">{s["blunders_per_game"]}</td>'
        f'<td class="num">{s["losses_on_time"]}</td></tr>'
        for tc, s in classes.items()
    )
    class_table = (
        '<div class="table-wrap"><table><thead><tr><th>Time control</th><th class="num">games</th>'
        '<th class="num">W / D / L</th><th class="num">accuracy*</th><th class="num">errors / game</th>'
        f'<th class="num">blunders / game</th><th class="num">lost on time</th></tr></thead><tbody>{class_rows}'
        "</tbody></table></div>"
    )

    summary_parts = []
    if review.get("takeaways"):
        items = "".join(f"<li>{escape(t)}</li>" for t in review["takeaways"])
        summary_parts.append(f'<ol class="takeaways">{items}</ol>')
    if review.get("reminder"):
        summary_parts.append(f'<div class="reminder"><b>Next game</b><span>{escape(review["reminder"])}</span></div>')
    if review.get("positive"):
        summary_parts.append(f'<p class="note"><b>Went well:</b> {escape(review["positive"])}</p>')
    if review.get("history_note"):
        summary_parts.append(f'<p class="note"><b>Compared with earlier:</b> {escape(review["history_note"])}</p>')
    if issues:
        summary_parts.append(
            f'<p class="coverage">{serious} flagged errors across {stats["games"]} games. This digest highlights '
            f'{len(issues)} {"issue" if len(issues) == 1 else "issues"} and {len(numbers)} representative '
            f'{"position" if len(numbers) == 1 else "positions"}; the rest are listed under each issue.</p>'
        )
    summary_html = "".join(summary_parts)
    issue_links = "".join(
        f'<li><a href="#issue-{k}">{escape(i["title"])}</a> <span>{"Recurring" if i.get("recurring") else "Notable"}'
        f', {i.get("games", 0)} games</span></li>'
        for k, i in enumerate(issues, 1)
    )
    issues_html = "".join(_issue(k, i, index, numbers, stats["games"], public) for k, i in enumerate(issues, 1))

    phase_rows = "".join(
        f'<tr><td>{escape(p)}</td><td class="num">{stats["phases"].get(p, 0)}</td></tr>'
        for p in ("opening", "middlegame", "endgame")
    )
    tag_rows = "".join(
        f'<tr><td>{escape(TAG_LABELS.get(t, t))}</td><td class="num">{s["count"]}</td><td class="num">{s["games"]}</td></tr>'
        for t, s in stats["tag_stats"].items()
    )

    def opening_cell(name: str, url: str) -> str:
        return f'<a href="{escape(url)}">{escape(name)}</a>' if url else escape(name)

    open_rows = "".join(
        f'<tr><td>{opening_cell(name, o["url"])}</td>'
        f'<td class="num">{o["games"]}</td><td class="num">{round(100 * o["points"] / o["games"])}%</td>'
        f'<td class="num">{o["opening_errors"] / o["games"]:.1f}</td>'
        f'<td class="num">{o["later_errors"] / o["games"]:.1f}</td></tr>'
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

    nav = [("summary", "Summary"), ("issues", "Issues", issues), ("stats", "Statistics"), ("openings", "Openings"),
           ("games", "Games")]
    toc = "".join(f'<li><a href="#{n[0]}">{n[1]}</a></li>' for n in nav if len(n) == 2 or n[2])

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{'<meta name="robots" content="noindex">' if public else ''}
<title>Chess digest: {escape(username)}</title>{FONTS}<style>{CSS}</style></head>
<body>{BOARD_DEFS}
<nav class="toc" aria-label="Sections"><ul>{toc}</ul></nav>
<main>
<h1>Chess digest for {escape(username)}</h1>
<div class="sub">{period} · {stats['games']} games ({escape(class_line)}) · {by}</div>

<section class="card" id="summary">
{summary_html}
{class_table}
</section>

{f'<h2 id="issues">Issues</h2><ol class="issue-index card">{issue_links}</ol>{issues_html}' if issues else ''}

<h2 id="stats">Supporting statistics</h2>
<section class="card"><div class="table-wrap">
<table><thead><tr><th>Mistakes and blunders by phase</th><th class="num">count</th></tr></thead><tbody>{phase_rows}</tbody></table>
</div></section>
<section class="card"><div class="table-wrap">
<table><thead><tr><th>Engine-detected pattern</th><th class="num">times</th><th class="num">games</th></tr></thead>
<tbody>{tag_rows}</tbody></table>
</div></section>
<h2 id="openings">Openings</h2>
<section class="card"><div class="table-wrap"><table><thead><tr><th>Opening</th><th class="num">games</th>
<th class="num">score</th><th class="num">errors in opening / game</th><th class="num">errors later / game</th></tr></thead>
<tbody>{open_rows}</tbody></table></div></section>
<h2 id="games">Games</h2>
<section class="card"><div class="table-wrap"><table><thead><tr><th>Date</th><th>Type</th><th>Color</th><th>Opponent</th>
<th>Result</th><th class="num">Acc.</th><th class="num">Errors</th><th></th></tr></thead><tbody>{game_rows}</tbody></table></div></section>

<details class="method"><summary>How this report is made</summary><ul>
<li>Stockfish evaluates every position. Evaluations are always from your side: positive is good for you.</li>
<li>A move is a mistake when your winning chances drop by 20 points or more, and a blunder at 30.</li>
<li>"Recurring" means the same kind of mistake in at least 3 different games. Anything less is marked "Notable".</li>
<li>"Under 10% clock" means at most a tenth of the starting time was left. It is context, not a verdict.</li>
<li>"The game went" is what was actually played. Engine lines are what Stockfish would play.</li>
<li>*Accuracy uses the Lichess win-chance formula, so it differs from chess.com's CAPS score.</li>
<li>Red arrow: your move. Green arrow: the engine's move. Click a move in any line to see that position
(← → step through it); click your move to go back.</li>
</ul></details>
<p class="muted" style="font-size:13px">{DISCLAIMER}</p>
</main>{TOC_SCRIPT}{STEP_SCRIPT}</body></html>"""
