#!/usr/bin/env python3
"""Experiment 139 -- V1 sealed probe runner (Muse). Read-only vs repo.

Reads the FROZEN expectations in artifacts/fable-fix139-20260922/cases139.json
(never the live list below), one message each through a FRESH in-process loop
(build_agent139 or, pre-seal for calibration only, build_agent129b), triples
via fable_loop90_agent.notebook_triples.

Verdicts: OK / WRONG-WRITE (any stored triple outside the expectation) /
MISSED (expected write, got none). Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix139_probe.py --agent loop139 \\
    --out artifacts/fable-fix139-20260922/probe139-loop139.json
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

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix139-20260922"


def run_case(row: dict, build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp,
                             "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "text": row["text"], "expect": row["expect"],
                    "stored": [], "reply": f"BOOT-FAILED {exc!r}",
                    "verdict": "HARNESS-ERROR",
                    "seconds": round(time.time() - t0, 3)}
        try:
            reply = " ".join(loop.turn(row["text"]))
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "text": row["text"], "expect": row["expect"],
                    "stored": [], "reply": f"HARNESS-CAUGHT {exc!r}",
                    "verdict": "HARNESS-ERROR",
                    "seconds": round(time.time() - t0, 3)}
    exp = row["expect"]
    if exp == "nowrite":
        verdict = "OK" if not stored else "WRONG-WRITE"
    else:
        want = [list(exp)]
        if stored == want:
            verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"], "text": row["text"],
            "expect": exp, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 139 V1 probe")
    ap.add_argument("--agent", default="loop139",
                    choices=("loop139", "loop129b"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.agent == "loop139":
        import fable_loop139_agent as L139  # noqa: E402 (this experiment)
        cfg = copy.deepcopy(L139.DEFAULT_CONFIG139)
        build_fn = lambda c: L139.build_agent139(dict(cfg, **c))  # noqa: E731
    else:
        import fable_loop129b_agent as L129b  # noqa: E402 (base, read-only)
        cfg = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
        build_fn = lambda c: L129b.build_agent129b(dict(cfg, **c))  # noqa: E731
    cases = json.loads((ART / "cases139.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": args.agent, "wall_seconds": wall,
               "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART / f"probe139-{args.agent}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent={args.agent} n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
