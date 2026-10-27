#!/usr/bin/env python3
"""Experiment 150b -- S1/S2 sealed probe runner (Muse). Read-only vs repo.

S1: reads FROZEN expectations from
    artifacts/fable-subject150b-20260922/cases150b.json (48 cases), one
    message each through a FRESH in-process loop150b, triples via
    fable_loop90_agent.notebook_triples. Judges the FULL triple.
S2: reads FROZEN artifacts/fable-fix150-20260922/cases150.json (57 cases)
    through loop150b and diffs per-case verdicts against the SEALED
    loop150 run artifacts/fable-fix150-20260922/probe150-loop150.json
    (read-only): ZERO moves predicted.

Verdicts: OK / WRONG-WRITE (any stored triple outside the expectation) /
MISSED (expected write, got none) / WRONG-REPLY (no write, but a nowrite
case got the wrong clarify kind). Every seed/case reported, never averaged.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix150b_probe.py --cases cases150b \\
    --out artifacts/fable-subject150b-20260922/probe150b-loop150b.json
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix150b_probe.py --cases cases150 \\
    --out artifacts/fable-subject150b-20260922/probe150b-s2-loop150b.json
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
ART150B = ROOT / "artifacts" / "fable-subject150b-20260922"
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
    ap = argparse.ArgumentParser(description="Exp 150b S1/S2 probe")
    ap.add_argument("--cases", default="cases150b",
                    choices=("cases150b", "cases150"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop150b_agent as L150b  # noqa: E402 (this experiment)
    cfg = copy.deepcopy(L150b.DEFAULT_CONFIG150B)
    build_fn = lambda c: L150b.build_agent150b(dict(cfg, **c))  # noqa: E731
    if args.cases == "cases150b":
        cases = json.loads((ART150B / "cases150b.json").read_text(
            encoding="utf-8"))
        default_out = ART150B / "probe150b-loop150b.json"
    else:
        cases = json.loads((ART150 / "cases150.json").read_text(
            encoding="utf-8"))
        default_out = ART150B / "probe150b-s2-loop150b.json"
    t0 = time.time()
    out = [run_case(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop150b", "cases_file": args.cases,
               "wall_seconds": wall, "counts": counts, "cases": out}
    if args.cases == "cases150":
        sealed = json.loads((ART150 / "probe150-loop150.json").read_text(
            encoding="utf-8"))
        base = {c["id"]: c.get("verdict") for c in sealed["cases"]}
        moves = [(r["id"], base.get(r["id"]), r["verdict"]) for r in out
                 if base.get(r["id"]) != r["verdict"]]
        payload["vs_loop150_moves"] = moves
        print(f"vs loop150 moves={moves}")
    dest = Path(args.out) if args.out else default_out
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"cases={args.cases} n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
