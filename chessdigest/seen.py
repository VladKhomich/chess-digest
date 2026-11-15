from __future__ import annotations

import json
from pathlib import Path


def load_seen(path: Path, username: str) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get(username.lower(), []))


def add_seen(path: Path, username: str, ids: list[str]) -> None:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    known = set(data.get(username.lower(), []))
    data[username.lower()] = sorted(known | set(ids))
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
