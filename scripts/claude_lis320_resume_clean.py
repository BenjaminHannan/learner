#!/usr/bin/env python3
"""lis-320 Luna full run: clean the assembled raw rows before a chunk resumes (reading thread, 2026-09-27; ADDENDUM-11).
New file. Standard library only; makes no call.

Each full-run chunk pushes only its own new rows. The next chunk joins every earlier chunk's rows in chunk order and runs
this before resuming, so a failed dialog is worded again instead of being skipped for good (the runner skips any dialog id
already in its --out file). A row is dropped here, and its dialog is worded again by the next chunk, when its reply is:
- empty (a failed call),
- error-like (claude_luna_codex.looks_like_error: short and error/limit-like), or
- a text found in 3 or more rows (every row with that text is dropped).
When one dialog id has more than one row left (an earlier bad row, then a good one), the last row is kept. Unparsed but
non-empty, non-error replies are kept as they are (counted as unparsed; not retried). Prints counts only.
    python -B scripts/claude_lis320_resume_clean.py --raw joined.jsonl --out raw.jsonl
    python -B scripts/claude_lis320_resume_clean.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_luna_codex import looks_like_error  # noqa: E402  (pure function; no call is made)


def clean(rows):
    c = Counter(rows_in=len(rows))
    texts = Counter((r.get("raw") or "").strip() for r in rows)
    keep = {}
    for r in rows:
        t = (r.get("raw") or "").strip()
        if not t:
            c["drop_empty"] += 1
            continue
        if looks_like_error(t):
            c["drop_errlike"] += 1
            continue
        if texts[t] >= 3:
            c["drop_dup3"] += 1
            continue
        if r.get("dialog_id") in keep:
            c["replaced_earlier_row"] += 1
        keep[r.get("dialog_id")] = r
    out = list(keep.values())
    c["rows_out"] = len(out)
    c["unparsed_kept"] = sum(1 for r in out if r.get("parsed") is None)
    return out, dict(c)


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def selftest():
    ok = {"turns": [{"n": 1, "reply_before": "", "user": "hi"}]}
    rows = [
        {"dialog_id": "a", "raw": "", "parsed": None},                       # failed call -> retried
        {"dialog_id": "b", "raw": json.dumps(ok) + " b", "parsed": ok},
        {"dialog_id": "c", "raw": "Rate limit exceeded", "parsed": None},    # error-like -> retried
        {"dialog_id": "d", "raw": "same", "parsed": None},
        {"dialog_id": "e", "raw": "same", "parsed": None},
        {"dialog_id": "f", "raw": "same", "parsed": None},                   # 3x text -> all three retried
        {"dialog_id": "g", "raw": "not json but long enough to be a real reply", "parsed": None},
        {"dialog_id": "a", "raw": json.dumps(ok) + " a", "parsed": ok},      # later chunk re-worded a
    ]
    out, c = clean(rows)
    ids = [r["dialog_id"] for r in out]
    assert sorted(ids) == ["a", "b", "g"], ids
    assert c["drop_empty"] == 1 and c["drop_errlike"] == 1 and c["drop_dup3"] == 3 and c["unparsed_kept"] == 1, c
    out2, c2 = clean(rows[1:2] + [dict(rows[1], raw=json.dumps(ok) + " b2")])
    assert len(out2) == 1 and out2[0]["raw"].endswith("b2") and c2["replaced_earlier_row"] == 1, (out2, c2)
    print("lis320 resume_clean selftest ok (empty, error-like and 3x rows dropped; last row per id kept; no network)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    out, c = clean(load(a.raw))
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"resume_clean": c}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
