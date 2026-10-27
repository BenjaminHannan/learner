#!/usr/bin/env python3
"""lis-320 raw-row route check with the allowed writer ids as an argument (reading thread, 2026-09-27; ADDENDUM-9).
New file; claude_lis320_rawcheck.py (GLM id only) stays as sealed.

Same checks as rawcheck (allowed model, temperature null, no duplicate ids, ids in seeds) plus two route checks from the
Director's 03:16 UTC warning that a helper can return an error or limit message as if it were text:
- errlike_rows: a non-empty reply that claude_luna_codex.looks_like_error flags (short and error/limit-like);
- dup3_texts: one non-empty reply text found in 3 or more rows.
Empty replies are failed calls (unparsed rows) and are counted, not flagged. Prints counts only; exits 1 on any problem.
    python -B scripts/claude_lis320_rawcheck2.py --raw raw.jsonl --models gpt-6-luna[,opencode-go/glm-5.3-flash] [--seeds S]
    python -B scripts/claude_lis320_rawcheck2.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_luna_codex import looks_like_error  # noqa: E402  (pure function; no call is made)


def check(raw_rows, models, seed_ids=None):
    c = Counter(rows=len(raw_rows))
    ids = [r.get("dialog_id") for r in raw_rows]
    c["duplicate_ids"] = len(ids) - len(set(ids))
    texts = Counter()
    for r in raw_rows:
        c["model_ok" if r.get("model") in models else "model_other"] += 1
        c["temperature_null" if r.get("temperature") is None else "temperature_set"] += 1
        t = (r.get("raw") or "").strip()
        if not t:
            c["empty_replies"] += 1
            continue
        texts[t] += 1
        if looks_like_error(t):
            c["errlike_rows"] += 1
    c["dup3_texts"] = sum(1 for n in texts.values() if n >= 3)
    if seed_ids is not None:
        c["not_in_seeds"] = len(set(ids) - set(seed_ids))
    ok = all(c.get(k, 0) == 0 for k in ("model_other", "temperature_set", "duplicate_ids", "not_in_seeds",
                                        "errlike_rows", "dup3_texts"))
    return ok, dict(c)


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def selftest():
    L = "gpt-6-luna"
    row = lambda i, raw="{}", m=L, t=None: {"dialog_id": i, "model": m, "temperature": t, "raw": raw}  # noqa: E731
    good = [row("a", '{"turns": [1]}'), row("b", '{"turns": [2]}'), row("c", "")]
    ok, c = check(good, {L}, ["a", "b", "c"])
    assert ok and c["empty_replies"] == 1, c
    assert not check(good + [row("d", m="opencode-go/glm-5.3-flash")], {L})[0]
    assert check(good + [row("d", '{"x": 1}', m="opencode-go/glm-5.3-flash")], {L, "opencode-go/glm-5.3-flash"})[0]
    assert not check(good + [row("d", "Error: Go usage limit exceeded")], {L})[0]
    assert not check([row(i, "same text") for i in "xyz"], {L})[0]
    assert not check(good + [row("a")], {L})[0]
    assert not check(good, {L}, ["a"])[0]
    print("lis320 rawcheck2 selftest 7/7 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw")
    ap.add_argument("--models", default="gpt-6-luna")
    ap.add_argument("--seeds")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    seed_ids = [d["dialog_id"] for d in load(a.seeds)] if a.seeds else None
    ok, c = check(load(a.raw), set(a.models.split(",")), seed_ids)
    print(json.dumps({"rawcheck2": "OK" if ok else "ROUTE-FAIL", "models": a.models, **c}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
