#!/usr/bin/env python3
"""Experiment 153 -- V1/V2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN dialogues from artifacts/fable-reverse153-20260922/cases153.json
(50 dialogues: 26 single-subject reverse across 8 relations x 4 frames, 12
multi-subject exact-set, 12 negatives incl. corrected-away / forgotten /
hearsay-refused / multi-hop). Each dialogue runs setup turns then ONE reverse
question through a FRESH in-process loop (build_agent153 or, pre-seal for
calibration only, build_agent139b... build_agent150).

Judgement per dialogue (every case reported, never averaged):
  OK          question reply == want exactly ("CLARIFY" rows: reply carries
              the loop's own miss text), AND 0 FACT writes on the question
              turn (mark V2 per-case).
  WRONG       reply differs (a wrong subject, an invented answer, or a lost
              answer).
  WRITE       the question turn wrote >= 1 FACT (V2 violation).
  SETUP-FAIL  a setup teach wrote nothing (harness-visible, counts as FAIL).
  HARNESS-ERROR / HARNESS-CAUGHT as labelled.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix153_probe.py --agent loop153 \\
    --out artifacts/fable-reverse153-20260922/probe153-loop153.json
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

ROOT = SCRIPTS.parent
ART153 = ROOT / "artifacts" / "fable-reverse153-20260922"

MISS_BITS = ("didn't understand", "didn't catch anything")


def fact_count(loop) -> int:
    return sum(1 for e in loop.nb.events if e.get("kind") == "FACT")


def run_dialogue(row: dict, build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"BOOT-FAILED {exc!r}", "writes": 0,
                    "seconds": round(time.time() - t0, 3)}
        try:
            setup_writes = 0
            for turn in row["setup"]:
                before = fact_count(loop)
                loop.turn(turn)
                setup_writes += fact_count(loop) - before
            # A dialogue whose setup stored nothing cannot test the question.
            teaches = [t for t in row["setup"]
                       if not t.lower().startswith(
                           ("forget", "please forget"))
                       and "i heard" not in t.lower()
                       and t.rstrip().endswith(".")]
            if teaches and setup_writes == 0:
                return {"id": row["id"], "group": row["group"],
                        "question": row["question"], "want": row["want"],
                        "reply": "", "writes": 0, "verdict": "SETUP-FAIL",
                        "seconds": round(time.time() - t0, 3)}
            before = fact_count(loop)
            reply = " ".join(loop.turn(row["question"]))
            writes = fact_count(loop) - before
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "question": row["question"], "want": row["want"],
                    "reply": f"HARNESS-CAUGHT {exc!r}", "writes": 0,
                    "verdict": "HARNESS-ERROR",
                    "seconds": round(time.time() - t0, 3)}
    want = row["want"]
    if writes > 0:
        verdict = "WRITE"
    elif want == "CLARIFY":
        verdict = ("OK" if any(b in reply for b in MISS_BITS)
                   else "WRONG")
    else:
        verdict = "OK" if reply == want else "WRONG"
    return {"id": row["id"], "group": row["group"],
            "question": row["question"], "want": want,
            "reply": reply, "writes": writes, "verdict": verdict,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 153 V1/V2 probe")
    ap.add_argument("--agent", default="loop153",
                    choices=("loop153", "loop150"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.agent == "loop153":
        import fable_loop153_agent as L153  # noqa: E402 (this experiment)
        cfg = copy.deepcopy(L153.DEFAULT_CONFIG153)
        build_fn = lambda c: L153.build_agent153(dict(cfg, **c))  # noqa: E731
    else:
        import fable_loop150_agent as L150  # noqa: E402 (base, read-only)
        cfg = copy.deepcopy(L150.DEFAULT_CONFIG150)
        build_fn = lambda c: L150.build_agent150(dict(cfg, **c))  # noqa: E731
    cases = json.loads((ART153 / "cases153.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_dialogue(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": args.agent, "cases_file": "cases153.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART153 / f"probe153-{args.agent}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent={args.agent} n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
