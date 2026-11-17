# chess-digest

chess-digest reviews your recent chess.com games. It downloads them, runs Stockfish on every move, asks Claude which
mistakes you keep repeating, and writes a short HTML report with board diagrams and links to practice material.

Project page: https://chess.ulad.net

## Setup

You need Docker Desktop, git and an Anthropic API key.

```sh
git clone https://github.com/VladKhomich/chess-digest.git
cd chess-digest
cp .env.example .env        # add ANTHROPIC_API_KEY and CHESSCOM_USER
docker compose build
docker compose run --rm digest --games 30
```

The report lands in `out/`. Engine results are cached in `out/cache/`.

## PowerShell shortcut

Add this line to your profile (`notepad $PROFILE`):

```powershell
. "C:\path\to\chess-digest\chess.ps1"
```

```powershell
chess analyse -g 10              # last 10 games
chess analyse --week             # everything from the last 7 days (also --month, -d 3)
chess analyse --week -t blitz --no-ai
chess analyse --week --publish   # analyse, then publish to GitHub Pages
chess publish                    # publish the last analysis without running it again
chess open                       # reopen the latest report
chess build                      # rebuild the image after code changes
```

A game that went into an earlier report is skipped next time (the list is in `out/seen.json`). Add `--all` to
include it again.

## Options

| flag | meaning |
|---|---|
| `--games N` | how many games (default 30, or up to 200 with `--since-days`) |
| `--since-days N` | only games from the last N days |
| `--time-class blitz` | filter by time class; repeat for several |
| `--rated-only` | skip unrated games |
| `--all` | include games from earlier reports |
| `--depth N` | Stockfish depth (default 14) |
| `--no-ai` | group mistakes by engine tags only, no API call |
| `--model ID` | Claude model (default `claude-sonnet-5-5`) |
| `--publish` | also write an anonymised copy to the `gh-pages` checkout in `.site/` |
| `--check-links` | check that the study links still work |

## How it works

1. Games come from the chess.com Published-Data API. You don't need to log in.
2. Stockfish evaluates every position. A move counts as an inaccuracy, mistake or blunder when your winning chances
   drop by 10, 20 or 30 points, the same scale Lichess uses. Simple detectors tag hung pieces, forks, missed and
   allowed mates, back-rank mates, missed tactics and time trouble.
3. The worst 80 mistakes and your stats go to Claude in one request. Opponent usernames are not sent. Claude can only
   choose theme ids and mistake ids that exist, so it can't make up links or positions.
4. Themes map to the links in `chessdigest/themes.py`. Each example shows the board with your move in red and the
   engine's move in green.

## Publishing

Published reports live on the `gh-pages` branch, never on `main`, so a fork or clone of the code doesn't carry
anyone's games. `chess analyse --publish` checks that branch out into `.site/` (a git worktree), writes the report to
`.site/digests/`, copies the project page from `site/index.html`, then commits and pushes `gh-pages`.

In a fresh fork the first publish creates an empty `gh-pages` branch. Then go to Settings → Pages, choose
"Deploy from a branch" and pick `gh-pages` / root. Published reports replace opponent usernames with
"Opponent (rating)" and carry a `noindex` tag.

## Cost

Stockfish runs locally. Each report makes one Claude Sonnet call. That's usually a few cents, and a week of games
rarely goes past 25 cents.

Not affiliated with or endorsed by Chess.com. Game data comes from the Chess.com Published-Data API.
