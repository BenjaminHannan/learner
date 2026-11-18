"""Condition W: after sleep, the hop-1 turns of the W two-hop items are deleted from the index.

Deleted turns for a W item: every user turn that mentions its hop-1 fact (the fact's ground-truth mentions), plus any user turn that
contains both the question's start name and the bridge name (a hop-1 paraphrase the mention tags did not catch). The LoRA was trained
on the whole diary BEFORE this deletion; every serve-side component (BM25, D3 round 1/2, D4's alias table) sees only the post-deletion diary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .index import Index
from .world import FROZEN, load_world, mentions_name, user_turns


def deleted_turns(turns: list[dict], w_items: list[dict]) -> set[int]:
    dele = set()
    for it in w_items:
        dele.update(it["hop1_turns"])
        for t in turns:
            if mentions_name(t, it["start"]) and mentions_name(t, it["bridge"]):
                dele.add(t["turn_id"])
    return dele


def check_deletion(turns: list[dict], w_items: list[dict], dele: set[int]) -> list[str]:
    """Problems (empty list = fine): a hop-2 turn deleted; a surviving turn that still links start and bridge; hop-2 turn gone."""
    bad = []
    alive = [t for t in turns if t["turn_id"] not in dele]
    for it in w_items:
        if set(it["hop2_turns"]) & dele:
            bad.append(f"{it['id']}: a hop-2 turn was deleted")
        if not set(it["hop2_turns"]) - dele:
            bad.append(f"{it['id']}: no hop-2 turn survives")
        for t in alive:
            if mentions_name(t, it["start"]) and mentions_name(t, it["bridge"]):
                bad.append(f"{it['id']}: turn {t['turn_id']} still links start and bridge")
                break
    return bad


def build_w_index(turns: list[dict], w_items: list[dict], path=":memory:") -> tuple[Index, set[int]]:
    dele = deleted_turns(turns, w_items)
    return Index(turns, path, exclude=dele, name="W"), dele


def main():
    ap = argparse.ArgumentParser(description="write the condition-W FTS5 index (a second sqlite file) and the deleted turn ids")
    ap.add_argument("--frozen", default=str(FROZEN))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    fr = Path(a.frozen)
    items = json.loads((fr / "items.json").read_text())
    turns = user_turns(load_world(fr / "week2.json" if (fr / "week2.json").exists() else None))
    w = [c for c in items["chains"] if c["W"]]
    out = Path(a.out or fr)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index_W.sqlite").unlink(missing_ok=True)
    idx, dele = build_w_index(turns, w, out / "index_W.sqlite")
    bad = check_deletion(turns, w, dele)
    (out / "w_deleted_turns.json").write_text(json.dumps(sorted(dele)))
    print(f"W items {len(w)}; deleted {len(dele)} of {len(turns)} turns; index_W has {len(idx)}; problems: {bad or 'none'}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
