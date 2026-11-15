"""Curated study resources. The AI picks theme ids; it never writes URLs."""

LT = "https://lichess.org/training/"
WIKI = "https://en.wikipedia.org/wiki/"

THEMES: dict[str, dict] = {
    "hanging_pieces": {
        "title": "Leaving pieces undefended",
        "tip": "Before every move, ask: what does my opponent attack after this move, and is everything defended?",
        "links": [
            ("Lichess puzzles: hanging piece", LT + "hangingPiece"),
            ("Chess.com puzzles", "https://www.chess.com/puzzles"),
        ],
    },
    "forks": {
        "title": "Forks (allowed or missed)",
        "tip": "Look for squares where one piece hits two targets, especially knight checks on the king and queen.",
        "links": [
            ("Lichess puzzles: fork", LT + "fork"),
            ("Fork (chess)", WIKI + "Fork_(chess)"),
        ],
    },
    "pins_skewers": {
        "title": "Pins and skewers",
        "tip": "Watch pieces lined up on the same file, rank or diagonal as your king or queen.",
        "links": [
            ("Lichess puzzles: pin", LT + "pin"),
            ("Lichess puzzles: skewer", LT + "skewer"),
            ("Pin (chess)", WIKI + "Pin_(chess)"),
            ("Skewer (chess)", WIKI + "Skewer_(chess)"),
        ],
    },
    "discovered_attacks": {
        "title": "Discovered attacks",
        "tip": "When a piece moves off a line, check what the piece behind it now attacks.",
        "links": [
            ("Lichess puzzles: discovered attack", LT + "discoveredAttack"),
            ("Discovered attack", WIKI + "Discovered_attack"),
        ],
    },
    "back_rank": {
        "title": "Back-rank weakness",
        "tip": "Give your king an escape square (luft) early; don't leave the back rank guarded by a single piece.",
        "links": [
            ("Lichess puzzles: back-rank mate", LT + "backRankMate"),
            ("Back-rank checkmate", WIKI + "Back-rank_checkmate"),
        ],
    },
    "missed_mates": {
        "title": "Missed checkmates",
        "tip": "Checks, captures, threats, in that order: always look at every check first.",
        "links": [
            ("Lichess puzzles: mate in 1", LT + "mateIn1"),
            ("Lichess puzzles: mate in 2", LT + "mateIn2"),
            ("Checkmate patterns", WIKI + "Checkmate_pattern"),
        ],
    },
    "king_safety": {
        "title": "King safety",
        "tip": "Castle early, avoid needless pawn moves in front of your king, and count attackers vs defenders near it.",
        "links": [
            ("Lichess puzzles: exposed king", LT + "exposedKing"),
            ("Lichess puzzles: kingside attack", LT + "kingsideAttack"),
        ],
    },
    "missed_tactics": {
        "title": "Missed tactical shots",
        "tip": "On every move, list your opponent's loose pieces and your forcing moves before choosing a plan.",
        "links": [
            ("Lichess puzzles: advantage", LT + "advantage"),
            ("Lichess Puzzle Storm", "https://lichess.org/storm"),
            ("Chess tactics", WIKI + "Chess_tactic"),
        ],
    },
    "defense": {
        "title": "Defending against threats",
        "tip": "After your opponent's move, ask what it threatens before thinking about your own plans.",
        "links": [
            ("Lichess puzzles: defensive move", LT + "defensiveMove"),
            ("Lichess puzzles: quiet move", LT + "quietMove"),
        ],
    },
    "trapped_pieces": {
        "title": "Trapped pieces",
        "tip": "Before grabbing material or going deep into enemy territory, check the piece has a way back.",
        "links": [("Lichess puzzles: trapped piece", LT + "trappedPiece")],
    },
    "opening_principles": {
        "title": "Opening principles",
        "tip": "Develop knights and bishops, control the centre, castle, and avoid moving the same piece twice early.",
        "links": [
            ("Chess opening (principles)", WIKI + "Chess_opening"),
            ("Lichess puzzles: opening", LT + "opening"),
            ("Chess.com lessons", "https://www.chess.com/lessons"),
        ],
    },
    "opening_repertoire": {
        "title": "Opening knowledge",
        "tip": "Learn the main ideas, not just the moves, of the two or three openings you play most.",
        "links": [
            ("Chess.com openings explorer", "https://www.chess.com/openings"),
            ("Lichess opening explorer", "https://lichess.org/opening"),
        ],
    },
    "pawn_endgames": {
        "title": "King and pawn endgames",
        "tip": "Learn opposition and the key squares; count tempi before trading into a pawn ending.",
        "links": [
            ("Lichess puzzles: pawn endgame", LT + "pawnEndgame"),
            ("Opposition", WIKI + "Opposition_(chess)"),
            ("King and pawn vs king", WIKI + "King_and_pawn_versus_king_endgame"),
        ],
    },
    "rook_endgames": {
        "title": "Rook endgames",
        "tip": "Know the Lucena and Philidor positions; keep your rook active and behind passed pawns.",
        "links": [
            ("Lichess puzzles: rook endgame", LT + "rookEndgame"),
            ("Lucena position", WIKI + "Lucena_position"),
            ("Philidor position", WIKI + "Philidor_position"),
        ],
    },
    "endgame_technique": {
        "title": "Endgame technique",
        "tip": "Activate your king, create a passed pawn, and trade pieces (not pawns) when ahead.",
        "links": [
            ("Lichess practice", "https://lichess.org/practice"),
            ("Lichess puzzles: endgame", LT + "endgame"),
            ("Chess endgame", WIKI + "Chess_endgame"),
        ],
    },
    "converting_advantage": {
        "title": "Converting a winning position",
        "tip": "When winning, simplify: trade pieces, remove counterplay, and don't rush.",
        "links": [
            ("Lichess puzzles: crushing", LT + "crushing"),
            ("Lichess practice", "https://lichess.org/practice"),
        ],
    },
    "promotion": {
        "title": "Passed pawns and promotion",
        "tip": "Push passed pawns with support; blockade enemy passers with a piece (ideally a knight).",
        "links": [
            ("Lichess puzzles: promotion", LT + "promotion"),
            ("Lichess puzzles: advanced pawn", LT + "advancedPawn"),
            ("Passed pawn", WIKI + "Passed_pawn"),
        ],
    },
    "time_management": {
        "title": "Time management",
        "tip": "Spend time on critical moments, play quick moves in known positions, and keep a reserve for the end.",
        "links": [
            ("Time trouble", WIKI + "Time_trouble"),
            ("Lichess Puzzle Storm (speed)", "https://lichess.org/storm"),
        ],
    },
    "calculation": {
        "title": "Calculation depth",
        "tip": "Calculate forcing lines to the end and check your opponent's best reply, not the one you hope for.",
        "links": [
            ("Lichess puzzles: long", LT + "long"),
            ("Lichess puzzles: sacrifice", LT + "sacrifice"),
        ],
    },
}

# Heuristic tag -> theme, used when running without AI.
TAG_THEME = {
    "hung_piece": "hanging_pieces",
    "allowed_fork": "forks",
    "missed_fork": "forks",
    "missed_mate": "missed_mates",
    "allowed_mate": "king_safety",
    "back_rank": "back_rank",
    "missed_tactic": "missed_tactics",
    "time_trouble": "time_management",
}
PHASE_THEME = {"opening": "opening_principles", "endgame": "endgame_technique"}

TAG_LABELS = {
    "hung_piece": "hung a piece",
    "allowed_fork": "allowed a fork",
    "missed_fork": "missed a fork",
    "missed_mate": "missed mate",
    "allowed_mate": "allowed mate",
    "back_rank": "back-rank",
    "missed_tactic": "missed tactic",
    "time_trouble": "low on time",
}
