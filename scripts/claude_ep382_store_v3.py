#!/usr/bin/env python3
"""ep-382 memory store, version 3 (benchmarks thread, 2026-09-26). New file only; v2 stays as it was.

Three boundary fixes from Ben's outside review (01:54 UTC), checked against v2's code first:
1. Torn last line. v2 runs json.loads on every line at start (store_v2:78-80), so a half-written last line after a
   crash stops the agent from starting at all. v3 moves a torn LAST line aside, word for word, to
   memory382/entries.torn.jsonl (appended; nothing is deleted), rewrites entries.jsonl without it atomically
   (temp file, fsync, os.replace), and goes on. A bad line anywhere else is real damage: v3 raises, as v2 does.
2. Durable append. v2's remember() is a plain append (store_v2:93-94). v3 flushes and fsyncs before returning.
3. Heard-only answers. v2's recall() searches heard and note rows alike by default (store_v2:130-132) and answer382
   calls it with no filter (claude_e2e382.py:114). rd-378 found 113 of 360 notes say things the chat did not, so
   notes are pointers, never answers. v3's default is sources={"heard"}; notes come back only when asked for.
With no note rows and no torn line (every 0.2 build today), recall() returns exactly what v2 returns: same rows,
same order, same scores. Switch it in without editing any sealed build: EP382_STORE=claude_ep382_store_v3
(claude_e2e382.py:41 reads that variable).

  python -B scripts/claude_ep382_store_v3.py selftest      (no model; the MiniLM ranking itself is v2's, unchanged)
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_ep382_store_v2 as V2  # noqa: E402

SOURCES = V2.SOURCES
embed = V2.embed
ANSWER_SOURCES = frozenset({"heard"})


def _load(path: Path) -> list[dict]:
    """Rows from entries.jsonl; a torn last line is moved aside to entries.torn.jsonl."""
    if not path.exists():
        return []
    raw = path.read_bytes()
    lines = raw.split(b"\n")
    rows, good_end = [], 0
    for n, line in enumerate(lines):
        last = n == len(lines) - 1 or all(not x.strip() for x in lines[n + 1:])
        if not line.strip():
            if not last:
                good_end += len(line) + 1
            continue
        try:
            row = json.loads(line.decode("utf-8"))
            if not isinstance(row, dict) or "source" not in row:
                raise ValueError("not a store row")
        except (ValueError, UnicodeDecodeError):
            if not last:
                raise
            torn = path.with_name("entries.torn.jsonl")
            with open(torn, "ab") as fh:
                fh.write(json.dumps({"torn_bytes": line.decode("utf-8", "replace")}, ensure_ascii=False)
                         .encode("utf-8") + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            tmp = path.with_name("entries.jsonl.tmp")
            with open(tmp, "wb") as fh:
                fh.write(raw[:good_end])
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            return rows
        rows.append(row)
        good_end += len(line) + 1
    if raw and not raw.endswith(b"\n"):          # a whole last row with no newline: add it, so appends stay clean
        with open(path, "ab") as fh:
            fh.write(b"\n")
            fh.flush()
            os.fsync(fh.fileno())
    return rows


class MemoryStore(V2.MemoryStore):
    def __init__(self, state_dir: str | Path):
        self.dir = Path(state_dir) / "memory382"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "entries.jsonl"
        self.rows = _load(self.path)
        self._emb = None
        self._n = Counter(r["source"] for r in self.rows)

    def remember(self, text: str, *, source: str, speaker: str, turn_ids: list[int], said_at: str | None,
                 logged_at: str) -> str:
        if source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}")
        self._n[source] += 1
        rid = f"{source[0]}{self._n[source]:07d}"
        row = {"id": rid, "text": text, "source": source, "speaker": speaker, "turn_ids": list(turn_ids),
               "said_at": said_at, "logged_at": logged_at}
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.rows.append(row)
        return rid

    def recall(self, query: str, *, k: int = 10, sources: set[str] | None = None, before: str | None = None,
               mode: str = "fused") -> list[dict]:
        return super().recall(query, k=k, sources=set(ANSWER_SOURCES) if sources is None else sources,
                              before=before, mode=mode)


def selftest() -> None:
    import tempfile
    ok, total = 0, 0

    def check(name: str, cond: bool) -> None:
        nonlocal ok, total
        total += 1
        ok += int(cond)
        print(f"{'PASS' if cond else 'FAIL'} {name}")

    said = [("Wren", "I moved to Harlow in May."), ("Tobin", "Wren's sister plays the cello."),
            ("Wren", "The lake trip is on Friday."), ("Tobin", "I sold my old bike to Mara.")]
    with tempfile.TemporaryDirectory() as d:
        a, b = V2.MemoryStore(Path(d) / "a"), MemoryStore(Path(d) / "b")
        for i, (sp, t) in enumerate(said, 1):
            for s in (a, b):
                s.remember(t, source="heard", speaker=sp, turn_ids=[i], said_at=None, logged_at="2026-09-26T00:00:00")
        check("same ids and rows as v2", [r["id"] for r in a.rows] == [r["id"] for r in b.rows])
        q = "Where did Wren move?"
        check("heard-only store: recall identical to v2 (bm25)",
              a.recall(q, k=4, mode="bm25") == b.recall(q, k=4, mode="bm25"))
        b.remember("Wren moved to Oslo.", source="note", speaker="", turn_ids=[1], said_at=None, logged_at="x")
        check("notes left out of answers by default", all(r["source"] == "heard" for r in b.recall(q, k=9, mode="bm25")))
        check("notes still there when asked for",
              any(r["source"] == "note" for r in b.recall(q, k=9, sources={"note"}, mode="bm25")))

        p = Path(d) / "c" / "memory382" / "entries.jsonl"
        c = MemoryStore(Path(d) / "c")
        c.remember("One.", source="heard", speaker="Wren", turn_ids=[1], said_at=None, logged_at="x")
        c.remember("Two.", source="heard", speaker="Wren", turn_ids=[2], said_at=None, logged_at="x")
        with open(p, "a", encoding="utf-8") as fh:
            fh.write('{"id": "h0000003", "text": "Thr')
        try:
            V2.MemoryStore(Path(d) / "c")
            v2_fails = False
        except ValueError:
            v2_fails = True
        check("v2 cannot start on a torn last line", v2_fails)
        c2 = MemoryStore(Path(d) / "c")
        torn = p.with_name("entries.torn.jsonl")
        check("v3 starts, keeps the 2 whole rows", len(c2.rows) == 2)
        check("torn bytes kept aside, not deleted", torn.exists() and "Thr" in torn.read_text(encoding="utf-8"))
        rid = c2.remember("Three.", source="heard", speaker="Wren", turn_ids=[3], said_at=None, logged_at="x")
        check("next row appends cleanly", rid == "h0000003" and len(MemoryStore(Path(d) / "c").rows) == 3)

        with open(p, "r+", encoding="utf-8") as fh:
            body = fh.read()
            fh.seek(0)
            fh.write(body.replace('"Two."', '"Two.', 1))
        try:
            MemoryStore(Path(d) / "c")
            raised = False
        except ValueError:
            raised = True
        check("damage in the middle still raises", raised)

        calls = []
        real = os.fsync
        os.fsync = lambda fd: calls.append(fd)
        try:
            MemoryStore(Path(d) / "e").remember("x", source="heard", speaker="W", turn_ids=[1], said_at=None,
                                                logged_at="x")
        finally:
            os.fsync = real
        check("remember fsyncs", len(calls) == 1)
    print(f"STORE-V3-SELFTEST {'PASS' if ok == total else 'FAIL'} {ok}/{total}")
    if ok != total:
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
