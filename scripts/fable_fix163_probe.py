#!/usr/bin/env python3
"""Experiment 163 -- T1/T2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN dialogues from artifacts/fable-lowercase163-20260922/cases163.json
(53 cases: 26 lowerQ + 12 lowerTeach + 8 innerCaps + 7 noMerge), each dialogue
through a FRESH in-process loop163 (build_agent163), triples via
fable_loop90_agent.notebook_triples (sorted). Judges the FULL stored triple
set plus the EXACT last reply.

Verdicts: OK / WRONG-WRITE (any stored triple outside the expectation) /
MISSED (expected write, got none) / WRONG-REPLY (triples right, last reply
differs). Every seed/case reported, never averaged. T1 bar: >= 25 lowerQ
exact, >= 10 lowerTeach exact, 8/8 innerCaps exact, 7/7 noMerge with 0 wrong
writes and 0 wrong answers. T2 bar: >= 95% of the 53 must-cases exact
(>= 51/53).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix163_probe.py \\
    --out artifacts/fable-lowercase163-20260922/probe163-loop163.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop163_agent as L163  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART163 = ROOT / "artifacts" / "fable-lowercase163-20260922"


def run_case(row: dict, build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "turns": row["turns"], "expect": row["expect_stored"],
                    "stored": [], "reply": f"BOOT-FAILED {exc!r}",
                    "verdict": "HARNESS-ERROR",
                    "seconds": round(time.time() - t0, 3)}
        try:
            replies = []
            for turn in row["turns"]:
                replies.append(" ".join(loop.turn(turn)))
            stored = sorted([list(t) for t in L90.notebook_triples(loop.nb)])
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "turns": row["turns"], "expect": row["expect_stored"],
                    "stored": [], "reply": f"HARNESS-CAUGHT {exc!r}",
                    "verdict": "HARNESS-ERROR",
                    "seconds": round(time.time() - t0, 3)}
    want = sorted([list(t) for t in row["expect_stored"]])
    reply = replies[-1] if replies else ""
    if stored != want:
        verdict = "MISSED" if not stored else "WRONG-WRITE"
    elif reply != row["expect_reply"]:
        verdict = "WRONG-REPLY"
    else:
        verdict = "OK"
    return {"id": row["id"], "group": row["group"], "turns": row["turns"],
            "expect": want, "want_reply": row["expect_reply"],
            "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 163 T1/T2 probe")
    ap.add_argument("--out", default=None)
    ap.add_argument("--cases", default="cases163.json",
                    help="case file in artifacts/fable-lowercase163-20260922 "
                    "(open re-runs may use cases163-open.json)")
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(L163.DEFAULT_CONFIG163)
    build_fn = lambda c: L163.build_agent163(dict(cfg, **c))  # noqa: E731
    cases = json.loads((ART163 / args.cases).read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    groups: dict[str, dict[str, int]] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        g = groups.setdefault(r["group"], {})
        g[r["verdict"]] = g.get(r["verdict"], 0) + 1
    payload = {"agent": "loop163", "cases_file": args.cases,
               "wall_seconds": wall, "counts": counts, "groups": groups,
               "cases": out}
    dest = Path(args.out) if args.out else ART163 / "probe163-loop163.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop163 n={len(out)} counts={counts} wall={wall}s")
    print(f"groups={groups}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
