"""SQLite FTS5 index over the diary turns (turn_id, day, text), BM25 ranking.

Queries are the OR of the query's non-stopword terms. Porter stemming so 'live' matches 'lives'.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .world import STOP, words


def fts_query(text: str) -> str | None:
    ts = []
    for w in words(text):
        if w not in STOP and w not in ts:
            ts.append(w)
    return " OR ".join(f'"{w}"' for w in ts) if ts else None


class Index:
    def __init__(self, turns: list[dict], path: str | Path = ":memory:", exclude=frozenset(), name: str = "full"):
        self.name, self.exclude = name, frozenset(exclude)
        self.db = sqlite3.connect(str(path))
        self.db.execute("DROP TABLE IF EXISTS turns")
        self.db.execute("CREATE VIRTUAL TABLE turns USING fts5(turn_id UNINDEXED, day UNINDEXED, text, tokenize='porter unicode61')")
        self.rows = {}
        for t in turns:
            if t["turn_id"] in self.exclude:
                continue
            self.rows[t["turn_id"]] = t
            self.db.execute("INSERT INTO turns(turn_id, day, text) VALUES (?,?,?)", (t["turn_id"], t["day"], t["text"]))
        self.db.commit()

    def __len__(self):
        return len(self.rows)

    def search(self, text: str, k: int = 20) -> list[int]:
        """Top-k turn_ids by BM25 for the OR-query of `text`'s terms (best first; ties by turn_id)."""
        q = fts_query(text)
        if q is None:
            return []
        cur = self.db.execute("SELECT turn_id, bm25(turns) AS s FROM turns WHERE turns MATCH ? ORDER BY s, turn_id LIMIT ?", (q, k))
        return [int(r[0]) for r in cur]

    def get(self, turn_id: int) -> dict:
        return self.rows[turn_id]

    def contains(self, turn_id: int) -> bool:
        return turn_id in self.rows


def build_index(world_turns: list[dict], path: str | Path = ":memory:", exclude=frozenset(), name="full") -> Index:
    return Index(world_turns, path, exclude, name)
