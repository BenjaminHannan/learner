#!/usr/bin/env python3
"""lis-320 raw-row route check (reading thread, 2026-09-26; ADDENDUM-4). New file.

Every GLM row that may reach lis-320's training data must come from Ben's opencode route (ADDENDUM-2): model
"opencode-go/glm-5.3-flash" and temperature null. claude_lis320_glm resumes by dialog_id only, and seed 322 re-creates the
dialog ids of the stopped OpenRouter run, so an OpenRouter row in a resume file would otherwise be kept silently.
Run before claude_lis320_check.py and before DATA.md is written. Prints counts only; exits 1 on any other row.
    python -B scripts/claude_lis320_rawcheck.py --raw raw.jsonl [--seeds seeds.jsonl]
    python -B scripts/claude_lis320_rawcheck.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

MODEL = "opencode-go/glm-5.3-flash"


def check(raw_rows, seed_ids=None):
    c = Counter(rows=len(raw_rows))
    ids = [r.get("dialog_id") for r in raw_rows]
    c["duplicate_ids"] = len(ids) - len(set(ids))
    for r in raw_rows:
        c["model_ok" if r.get("model") == MODEL else "model_other"] += 1
        c["temperature_null" if r.get("temperature") is None else "temperature_set"] += 1
    if seed_ids is not None:
        c["not_in_seeds"] = len(set(ids) - set(seed_ids))
    ok = (c["model_other"] == 0 and c["temperature_set"] == 0 and c["duplicate_ids"] == 0
          and c.get("not_in_seeds", 0) == 0)
    return ok, dict(c)


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def selftest():
    good = [{"dialog_id": "a", "model": MODEL, "temperature": None}, {"dialog_id": "b", "model": MODEL, "temperature": None}]
    assert check(good, ["a", "b", "c"])[0]
    assert not check(good + [{"dialog_id": "c", "model": "z-ai/glm-5.3-flash", "temperature": 1.0}])[0]
    assert not check(good + [dict(good[0])])[0]
    assert not check(good, ["a"])[0]
    print("lis320 rawcheck selftest 4/4 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw")
    ap.add_argument("--seeds")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    seed_ids = [d["dialog_id"] for d in load(a.seeds)] if a.seeds else None
    ok, c = check(load(a.raw), seed_ids)
    print(json.dumps({"rawcheck": "OK" if ok else "ROUTE-MISMATCH", **c}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
