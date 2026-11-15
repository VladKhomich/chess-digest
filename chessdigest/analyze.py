from __future__ import annotations

import io
import json
import math
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import chess
import chess.engine
import chess.pgn

from .fetch import game_id

VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
DRAW_RESULTS = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}
MATE = 10000

# Thresholds on the drop in winning chances (percentage points), same idea as Lichess.
INACCURACY, MISTAKE, BLUNDER = 10, 20, 30


def find_stockfish() -> str:
    path = os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish")
    if not path and Path("/usr/games/stockfish").exists():
        path = "/usr/games/stockfish"
    if not path:
        raise SystemExit("Stockfish not found: install it or set STOCKFISH_PATH")
    return path


def win_pct(cp: int) -> float:
    cp = max(-2000, min(2000, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def move_accuracy(drop: float) -> float:
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * drop) - 3.1669))


def fmt_eval(cp: int) -> str:
    if abs(cp) < MATE - 500:
        return f"{cp / 100:+.2f}"
    n = MATE - abs(cp)
    if n == 0:
        return "mate"
    return f"#{n}" if cp > 0 else f"-#{n}"


def classify(drop: float) -> str | None:
    if drop >= BLUNDER:
        return "blunder"
    if drop >= MISTAKE:
        return "mistake"
    if drop >= INACCURACY:
        return "inaccuracy"
    return None


def game_phase(board: chess.Board) -> str:
    non_pawn = sum(
        VALUES[p.piece_type] for p in board.piece_map().values() if p.piece_type not in (chess.PAWN, chess.KING)
    )
    if non_pawn <= 26:
        return "endgame"
    if board.fullmove_number <= 12:
        return "opening"
    return "middlegame"


def _base_seconds(time_control: str) -> int | None:
    if not time_control or "/" in time_control:
        return None
    try:
        return int(time_control.split("+")[0])
    except ValueError:
        return None


def _evaluate_positions(engine, start: chess.Board, moves: list[chess.Move], depth: int):
    """White-POV centipawns and PV for every position from start to end of game."""
    board = start.copy()
    out: list[tuple[int, list[chess.Move]]] = []
    for i in range(len(moves) + 1):
        if board.is_game_over():
            if board.is_checkmate():
                cp = -MATE if board.turn == chess.WHITE else MATE
            else:
                cp = 0
            out.append((cp, []))
        else:
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            out.append((info["score"].white().score(mate_score=MATE), info.get("pv", [])))
        if i < len(moves):
            board.push(moves[i])
    return out


def _fork_targets(board: chess.Board, move: chess.Move) -> list[int]:
    b = board.copy(stack=False)
    b.push(move)
    piece = b.piece_at(move.to_square)
    if piece is None:
        return []
    enemy = not piece.color
    targets = []
    for sq in b.attacks(move.to_square):
        t = b.piece_at(sq)
        if not t or t.color != enemy or t.piece_type == chess.PAWN:
            continue
        if (
            t.piece_type == chess.KING
            or VALUES[t.piece_type] > VALUES[piece.piece_type]
            or not b.is_attacked_by(enemy, sq)
        ):
            targets.append(sq)
    return targets if len(targets) >= 2 else []


def _wins_material(board: chess.Board, move: chess.Move) -> bool:
    if not board.is_capture(move) or board.is_en_passant(move):
        return False
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim is None or attacker is None or VALUES[victim.piece_type] < 3:
        return False
    defended = board.is_attacked_by(victim.color, move.to_square)
    return not defended or VALUES[victim.piece_type] > VALUES[attacker.piece_type]


def _back_rank_mate(board: chess.Board, pv: list[chess.Move], victim: chess.Color) -> bool:
    b = board.copy(stack=False)
    for m in pv[:7]:
        b.push(m)
        if b.is_checkmate():
            break
    if not b.is_checkmate() or b.turn != victim:
        return False
    king = b.king(victim)
    back = 0 if victim == chess.WHITE else 7
    if king is None or chess.square_rank(king) != back:
        return False
    return any(
        b.piece_type_at(sq) in (chess.ROOK, chess.QUEEN) and chess.square_rank(sq) == back for sq in b.checkers()
    )


def _is_mate(cp: int) -> bool:
    return abs(cp) >= MATE - 500


def _tags(
    board: chess.Board,
    move: chess.Move,
    pv_before: list[chess.Move],
    pv_after: list[chess.Move],
    cp_before: int,
    cp_after: int,
    drop: float,
) -> list[str]:
    """Pattern tags for one of the player's moves. Evals are from the player's side."""
    tags = []
    after = board.copy(stack=False)
    after.push(move)
    best = pv_before[0] if pv_before else None
    reply = pv_after[0] if pv_after else None

    if _is_mate(cp_before) and cp_before > 0 and not (_is_mate(cp_after) and cp_after > 0):
        tags.append("missed_mate")
    if _is_mate(cp_after) and cp_after < 0:
        tags.append("allowed_mate")
        if _back_rank_mate(after, pv_after, board.turn):
            tags.append("back_rank")
    if reply is not None:
        if _wins_material(after, reply):
            tags.append("hung_piece")
        if _fork_targets(after, reply):
            tags.append("allowed_fork")
    if best is not None:
        if _fork_targets(board, best):
            tags.append("missed_fork")
        forcing = board.is_capture(best) or board.gives_check(best)
        if forcing and drop >= MISTAKE and "missed_mate" not in tags:
            tags.append("missed_tactic")
    return tags


def _low_on_time(clock: float | None, base: int | None) -> bool:
    if clock is None:
        return False
    return clock < max(15, 0.1 * base) if base else clock < 15


def analyze_game(engine, g: dict, username: str, depth: int) -> dict:
    game = chess.pgn.read_game(io.StringIO(g["pgn"]))
    user_white = g["white"]["username"].lower() == username.lower()
    color = chess.WHITE if user_white else chess.BLACK
    me = g["white" if user_white else "black"]
    opp = g["black" if user_white else "white"]
    sign = 1 if user_white else -1

    nodes = list(game.mainline())
    moves = [n.move for n in nodes]
    evals = _evaluate_positions(engine, game.board(), moves, depth)
    base = _base_seconds(g.get("time_control", ""))

    board = game.board()
    errors, accs = [], []
    for i, node in enumerate(nodes):
        move = node.move
        if board.turn == color:
            cp_b, cp_a = sign * evals[i][0], sign * evals[i + 1][0]
            drop = max(0.0, win_pct(cp_b) - win_pct(cp_a))
            accs.append(move_accuracy(drop))
            pv_before, pv_after = evals[i][1], evals[i + 1][1]
            best = pv_before[0] if pv_before else None
            kind = classify(drop)
            if kind and best != move:
                after = board.copy(stack=False)
                after.push(move)
                clock = node.clock()
                tags = _tags(board, move, pv_before, pv_after, cp_b, cp_a, drop)
                if _low_on_time(clock, base):
                    tags.append("time_trouble")
                errors.append(
                    {
                        "ply": i,
                        "move_no": board.fullmove_number,
                        "fen": board.fen(),
                        "played_san": board.san(move),
                        "played_uci": move.uci(),
                        "best_san": board.san(best) if best else None,
                        "best_uci": best.uci() if best else None,
                        "best_line": board.variation_san(pv_before[:6]) if pv_before else "",
                        "refutation": after.variation_san(pv_after[:6]) if pv_after else "",
                        "eval_before": fmt_eval(cp_b),
                        "eval_after": fmt_eval(cp_a),
                        "drop": round(drop, 1),
                        "kind": kind,
                        "phase": game_phase(board),
                        "clock": clock,
                        "tags": tags,
                    }
                )
        board.push(move)

    raw = me.get("result", "")
    result = "win" if raw == "win" else "draw" if raw in DRAW_RESULTS else "loss"
    # chess.com stores "win" for the winner; the way the game ended is on the loser's side.
    reason = opp.get("result", "") if result == "win" else raw
    eco_url = game.headers.get("ECOUrl", "")
    opening = eco_url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ") if eco_url else game.headers.get("ECO", "Unknown")

    return {
        "id": game_id(g),
        "url": g.get("url", ""),
        "date": datetime.fromtimestamp(g.get("end_time", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
        "time_class": g.get("time_class", ""),
        "time_control": g.get("time_control", ""),
        "rated": g.get("rated", False),
        "color": "white" if user_white else "black",
        "user_rating": me.get("rating"),
        "opponent": opp.get("username"),
        "opponent_rating": opp.get("rating"),
        "result": result,
        "reason": reason,
        "opening": opening,
        "eco_url": eco_url,
        "moves": len(accs),
        "accuracy": round(sum(accs) / len(accs), 1) if accs else None,
        "errors": errors,
    }


def analyze_games(
    games: list[dict],
    username: str,
    depth: int,
    cache_dir: Path,
    workers: int,
    progress: Callable[[int, int, dict], None] = lambda *_: None,
) -> list[dict]:
    path = find_stockfish()
    cache_dir.mkdir(parents=True, exist_ok=True)
    local = threading.local()
    engines: list[chess.engine.SimpleEngine] = []
    lock = threading.Lock()

    def engine():
        if not hasattr(local, "e"):
            e = chess.engine.SimpleEngine.popen_uci(path)
            e.configure({"Threads": 1, "Hash": 64})
            local.e = e
            with lock:
                engines.append(e)
        return local.e

    def work(g: dict) -> dict:
        cache = cache_dir / f"{username.lower()}_{game_id(g)}_d{depth}.json"
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
        res = analyze_game(engine(), g, username, depth)
        cache.write_text(json.dumps(res), encoding="utf-8")
        return res

    results = []
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for k, r in enumerate(ex.map(work, games), 1):
                progress(k, len(games), r)
                results.append(r)
    finally:
        for e in engines:
            e.quit()
    return results
