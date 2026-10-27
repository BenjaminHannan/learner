#!/usr/bin/env python3
"""Exp 150d G2 compare -- diff marks150d vs loop138b's frozen marks138b.

Per-case verdict/reply equality on every suite; bar: identical everywhere
(predicted moves: none -- zero hedge-led inputs across all G2 suites).
Run after: scripts/fable_marks123_all.py --agent
scripts/fable_loop150d_agent.py --config
artifacts/fable-hedgecase150d-20260922/loop150d-config.json --out
artifacts/fable-hedgecase150d-20260922/marks150d --workers 4
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M138 = ROOT / "artifacts" / "fable-agent138b-20260922" / "marks138b"
M150 = ROOT / "artifacts" / "fable-hedgecase150d-20260922" / "marks150d"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def rows_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(
        encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    fails, moves = 0, []

    def note(suite: str, cid: str, a: str, b: str) -> None:
        moves.append(f"{suite} {cid}: 138b={a} -> 150d={b}")

    # p2 / rt110 / q1 / p4 / rt81: per-row verdict compare
    for suite, key in (("p2-report.json", "rows"),
                       ("rt110-report.json", "rows"),
                       ("q1-report.json", None),
                       ("p4-report.json", "rows"),
                       ("rt81-report.json", "cases")):
        a = load(M138 / suite)
        b = load(M150 / suite)
        if key is None:  # q1: scalar flags + replies
            for k in ("f5_ok", "m5_ok", "f5_reply", "m5_reply"):
                if a.get(k) != b.get(k):
                    note(suite, k, str(a.get(k))[:60],
                         str(b.get(k))[:60])
                    fails += 1
            continue
        ba = {r.get("id", str(i)): r for i, r in enumerate(a[key])}
        bb = {r.get("id", str(i)): r for i, r in enumerate(b[key])}
        assert set(ba) == set(bb), f"{suite} id mismatch"
        for cid, r in bb.items():
            c = ba[cid]
            va = c.get("agent_verdict", c.get("verdict", c.get("pass")))
            vb = r.get("agent_verdict", r.get("verdict", r.get("pass")))
            if va != vb:
                note(suite, cid, str(va), str(vb))
                fails += 1
    # bench rows: per-item verdict compare (both splits)
    for name in ("bench-rows-fable_edit_200.jsonl",
                 "bench-rows-s2fresh_4hop.jsonl"):
        ba = {r["id"]: r for r in rows_jsonl(M138 / name)}
        bb = {r["id"]: r for r in rows_jsonl(M150 / name)}
        assert set(ba) == set(bb), f"{name} id mismatch"
        for cid, r in bb.items():
            if r["verdict"] != ba[cid]["verdict"]:
                note(name, cid, ba[cid]["verdict"], r["verdict"])
                if ba[cid]["verdict"] != "wrong" \
                        and r["verdict"] == "wrong":
                    fails += 1
                else:
                    fails += 1  # G2 allows no moves at all
    # p3: per-level pass flags (runners report pass/seconds per level)
    pa, pb = load(M138 / "p3-report.json"), load(M150 / "p3-report.json")
    for lvl in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
        if pa["marks"][lvl]["pass"] != pb["marks"][lvl]["pass"]:
            note("p3", lvl, str(pa["marks"][lvl]["pass"]),
                 str(pb["marks"][lvl]["pass"]))
            fails += 1
    # q4 + sleep: pass/skip flags
    for suite in ("q4-report.json", "sleep-report.json"):
        if load(M138 / suite).get("pass") != load(M150 / suite).get("pass"):
            note(suite, "pass", "diff", "diff")
            fails += 1
    # soak: scalar counters must match exactly
    for k in ("lost", "wrong", "doubled_replies", "audit_lost_pairs",
              "audit_dup_pairs", "audit_wrong_pairs"):
        if load(M138 / "soak-report.json").get(k) != \
                load(M150 / "soak-report.json").get(k):
            note("soak", k, "diff", "diff")
            fails += 1
    print(f"G2-compare: moves={len(moves)} fails={fails}", flush=True)
    for m in moves:
        print(f"  MOVE {m}", flush=True)
    ok = (fails == 0 and not moves)
    print(f"G2 {'PASS' if ok else 'FAIL'} (predicted: identical everywhere)",
          flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
