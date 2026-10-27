#!/usr/bin/env python3
"""ep-382 memory store, version 4 (Trustworthy notes thread, 2026-09-26). New file only; v3 stays as it was.

The one change: notes are searched as pointers to the raw lines. rd-378L (PASS, artifacts/claude-rd378L-20260926/
VERIFY.md): the rd-378 writer's notes, ranked together with the heard rows and resolved to the lines they cite, put the
evidence line in a top 10 for 583 of 759 LoCoMo practice questions vs 496 heard-only (on v3's ranking, report only:
+8.0 points at the same number of lines shown).
Brain picture (hippocampal indexing): a small index points at the whole episode; a cue can match the index or the
episode, and what comes back is the episode itself. A note is an index entry; the answer only ever reads the raw line.

recall(query, k) with no sources ranks heard AND note rows together (v2's ranking, unchanged), then walks that ranking
and replaces each note by the heard rows its turn_ids point to (latest first), keeping each heard row once, until k
heard rows are collected. It returns heard rows only, so a note is never an answer. A row reached through a note
carries "via": <note id> and the note's score. before= filters the rows reached through notes the same way.
With no note rows it returns exactly what v3 returns (same rows, order, scores, keys).
recall(..., sources=...) is v3's recall unchanged (explicit sources, no pointer step).

  python -B scripts/claude_ep382_store_v4.py selftest      (no model: BM25 mode)
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_ep382_store_v2 as V2  # noqa: E402
import claude_ep382_store_v3 as V3  # noqa: E402

SOURCES = V3.SOURCES


class MemoryStore(V3.MemoryStore):
    def recall(self, query: str, *, k: int = 10, sources: set[str] | None = None, before: str | None = None,
               mode: str = "fused") -> list[dict]:
        if sources is not None:
            return super().recall(query, k=k, sources=sources, before=before, mode=mode)
        heard_at = {}
        for r in self.rows:
            if r["source"] == "heard":
                for t in r["turn_ids"]:
                    heard_at.setdefault(t, r)
        hits = super().recall(query, k=len(self.rows), sources={"heard", "note"}, before=before, mode=mode)
        out, seen = [], set()
        for h in hits:
            if h["source"] == "heard":
                reached = [(h, None)]
            else:
                reached = [(heard_at[t], h["id"]) for t in sorted(h["turn_ids"], reverse=True) if t in heard_at]
            for row, via in reached:
                if row["id"] in seen:
                    continue
                if via is not None and before is not None and V2._iso(row["said_at"]) and row["said_at"] >= before:
                    continue
                seen.add(row["id"])
                got = dict(row, score=h["score"]) if via is None else dict(row, score=h["score"], via=via)
                out.append(got)
                if len(out) == k:
                    return out
        return out


def selftest() -> None:
    import tempfile
    ok = {}
    said = [("Wren", "I moved to Oakvale in May."), ("Tobin", "Nice, my dog Pip loves the beach."),
            ("Wren", "The library there hired me."), ("Tobin", "We should meet at the harbour cafe.")]
    with tempfile.TemporaryDirectory() as d:
        v3 = V3.MemoryStore(Path(d) / "a")
        v4 = MemoryStore(Path(d) / "b")
        for i, (sp, t) in enumerate(said, 1):
            for s in (v3, v4):
                s.remember(t, source="heard", speaker=sp, turn_ids=[i], said_at=f"2023-05-0{i}", logged_at="x")
        q = "Where does Wren work now?"
        ok["no notes: identical to v3"] = v4.recall(q, k=3, mode="bm25") == v3.recall(q, k=3, mode="bm25")
        v4.remember("Wren works at the Oakvale library.", source="note", speaker="Wren", turn_ids=[3, 1],
                    said_at="2023-05-03", logged_at="x")
        got = v4.recall(q, k=2, mode="bm25")
        ok["notes never returned"] = all(r["source"] == "heard" for r in v4.recall(q, k=9, mode="bm25"))
        ok["note resolves to its lines, latest first"] = [r["turn_ids"] for r in got] == [[3], [1]] and \
            all(r.get("via") == "n0000001" for r in got)
        ok["each line once"] = len({r["id"] for r in v4.recall(q, k=9, mode="bm25")}) == \
            len(v4.recall(q, k=9, mode="bm25")) == 4
        ok["explicit sources = v3"] = v4.recall(q, k=9, sources={"note"}, mode="bm25")[0]["source"] == "note"
        v4.remember("Wren works at the Oakvale library.", source="note", speaker="Wren", turn_ids=[3],
                    said_at="2023-05-01", logged_at="x")
        early = v4.recall(q, k=9, before="2023-05-02", mode="bm25")
        ok["before filters lines reached by a note"] = [r["turn_ids"] for r in early] == [[1]]
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print("EP382-V4-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    if not all(ok.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
