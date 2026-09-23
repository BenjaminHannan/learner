#!/usr/bin/env python3
"""Experiment 150 -- S1/S2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations from artifacts/fable-fix150-20260922/cases150.json
(57 cases), one message each through a FRESH in-process loop (build_agent150
or, pre-seal for calibration only, build_agent139b), triples via
fable_loop90_agent.notebook_triples. Judges the FULL triple.

Verdicts: OK / WRONG-WRITE (any stored triple outside the expectation) /
MISSED (expected write, got none) / WRONG-REPLY (no write, but a nowrite
case got the wrong clarify kind). Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix150_probe.py --agent loop150 \\
    --out artifacts/fable-fix150-20260922/probe150-loop150.json
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
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"

SPLIT_MARK = "one fact at a time"
HEARSAY_MARK = "hear it somewhere"


def reply_ok(kind: str | None, reply: str) -> bool:
    if kind in (None, "any"):
        return True
    if kind == "split":
        return SPLIT_MARK in reply
    if kind == "hearsay":
        return HEARSAY_MARK in reply
    return True


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
    want_reply = row.get("reply", "any")
    if exp == "nowrite":
        if stored:
            verdict = "WRONG-WRITE"
        elif reply_ok(want_reply, reply):
            verdict = "OK"
        else:
            verdict = "WRONG-REPLY"
    else:
        want = [list(exp)]
        if stored == want:
            verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"],
            "director": bool(row.get("director", False)),
            "text": row["text"], "expect": exp, "want_reply": want_reply,
            "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 150 S1/S2 probe")
    ap.add_argument("--agent", default="loop150",
                    choices=("loop150", "loop139b"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.agent == "loop150":
        import fable_loop150_agent as L150  # noqa: E402 (this experiment)
        cfg = copy.deepcopy(L150.DEFAULT_CONFIG150)
        build_fn = lambda c: L150.build_agent150(dict(cfg, **c))  # noqa: E731
    else:
        import fable_loop139b_agent as L139b  # noqa: E402 (base, read-only)
        cfg = copy.deepcopy(L139b.DEFAULT_CONFIG139B)
        build_fn = lambda c: L139b.build_agent139b(dict(cfg, **c))  # noqa: E731
    cases = json.loads((ART150 / "cases150.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": args.agent, "cases_file": "cases150.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART150 / f"probe150-{args.agent}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent={args.agent} n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
