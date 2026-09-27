#!/usr/bin/env python3
"""y1t route-loss filter for GLM top-up rows (Answering-from-memory thread, 2026-09-27; ADDENDUM-4). New file.

Ben's opencode plan hit its usage limit at about 00:57 UTC on 2026-09-27. A call made after that can come back as
the route's own error text, which the helper saves like a reply. Such a row is a route loss, not a GLM try. The rule
is the Creative thread's (artifacts/claude-k1h-20260926/ADDENDUM-4-routeloss.md, 4067d1bb9), applied to "raw":
- EMPTY: "raw" is empty (a failed call);
- R1: "raw" contains one of MARKERS (case-insensitive), or starts with "Error" or "error:";
- R2: the same "raw" text (trimmed, lower-cased, runs of spaces collapsed) was given for 3 or more different dialogs.
Route-loss rows are left out of the output; counts only are printed, never text.

  python -B scripts/claude_y1t_routefilter.py filter --raw IN.jsonl --out OUT.jsonl
  python -B scripts/claude_y1t_routefilter.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import tempfile
from pathlib import Path

MARKERS = ("usage limit", "limit exceeded", "rate limit", "opencode", "> build", "api key", "providermodelnotfound",
           "insufficient credit", "insufficient balance", "unauthorized")


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def classify(rows: list[dict]) -> list[str]:
    seen = collections.defaultdict(set)
    for r in rows:
        if r.get("raw"):
            seen[_norm(r["raw"])].add(r["dialog_id"])
    out = []
    for r in rows:
        raw = r.get("raw") or ""
        if not raw.strip():
            out.append("empty")
        elif any(m in raw.lower() for m in MARKERS) or raw.lstrip().startswith(("Error", "error:")):
            out.append("r1")
        elif len(seen[_norm(raw)]) >= 3:
            out.append("r2")
        else:
            out.append("ok")
    return out


def filter_file(src: Path, dst: Path) -> dict:
    rows = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    kinds = classify(rows)
    kept = [r for r, k in zip(rows, kinds) if k == "ok"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    c = collections.Counter(kinds)
    res = {"rows": len(rows), "empty": c["empty"], "r1": c["r1"], "r2": c["r2"], "kept": len(kept)}
    print(json.dumps(res))
    return res


def selftest() -> None:
    rows = [{"dialog_id": "a", "raw": '{"turns": [1]}'}, {"dialog_id": "b", "raw": ""},
            {"dialog_id": "c", "raw": "Error: Go usage limit exceeded"}, {"dialog_id": "d", "raw": "same  text"},
            {"dialog_id": "e", "raw": "Same text "}, {"dialog_id": "f", "raw": "same text"},
            {"dialog_id": "g", "raw": '{"turns": [2]}'}, {"dialog_id": "h", "raw": "twice"}, {"dialog_id": "i", "raw": "twice"}]
    assert classify(rows) == ["ok", "empty", "r1", "r2", "r2", "r2", "ok", "ok", "ok"], classify(rows)
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "in.jsonl", Path(td) / "out.jsonl"
        src.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        res = filter_file(src, dst)
        assert res == {"rows": 9, "empty": 1, "r1": 1, "r2": 3, "kept": 4}, res
        assert [json.loads(x)["dialog_id"] for x in dst.read_text().splitlines()] == ["a", "g", "h", "i"]
    print("y1t routefilter selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("filter")
    f.add_argument("--raw", required=True, type=Path)
    f.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    filter_file(a.raw, a.out)


if __name__ == "__main__":
    main()
