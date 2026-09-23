#!/usr/bin/env python3
"""Experiment 159 -- H1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN dialogues from artifacts/fable-hop159-20260922/cases159.json
(48 dialogues: 26 chains + 11 nobody + 11 traps). Each dialogue runs through
a FRESH in-process loop159 (build_agent159): every teach must reply
"Saved", the question turn must write nothing, then:

  expect "answer" -> want (case-insensitive) in the reply  => OK else WRONG
  expect "broken" -> old BROKEN_CHAIN reply
     ("not someone I can look up") and no write            => OK else WRONG

Every seed/case reported, never averaged. 0 wrong answers over all 48.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix159_probe.py \\
    --out artifacts/fable-hop159-20260922/probe159-loop159.json
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

import fable_loop159_agent as L159  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART159 = ROOT / "artifacts" / "fable-hop159-20260922"

BROKEN_MARK = "not someone I can look up"


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
                    "reply": f"BOOT-FAILED {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
        try:
            teach_replies = []
            for sent in row["teaches"]:
                teach_replies.append(" ".join(loop.turn(sent)))
            if not all("Saved" in r for r in teach_replies):
                return {"id": row["id"], "group": row["group"],
                        "teaches": row["teaches"], "teach_replies": teach_replies,
                        "question": row["question"], "expect": row["expect"],
                        "want": row.get("want"), "reply": "",
                        "verdict": "TEACH-FAIL",
                        "seconds": round(time.time() - t0, 3)}
            before = fact_count(loop)
            reply = " ".join(loop.turn(row["question"]))
            wrote = fact_count(loop) - before
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"HARNESS-CAUGHT {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
    if wrote > 0:
        verdict = "WRONG-WRITE"
    elif row["expect"] == "answer":
        verdict = ("OK" if row["want"].lower() in reply.lower()
                   else "WRONG")
    else:
        verdict = "OK" if BROKEN_MARK in reply else "WRONG"
    return {"id": row["id"], "group": row["group"],
            "teaches": row["teaches"], "teach_replies": teach_replies,
            "question": row["question"], "expect": row["expect"],
            "want": row.get("want"), "reply": reply,
            "question_writes": wrote, "verdict": verdict,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 159 H1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(L159.DEFAULT_CONFIG159)
    build_fn = lambda c: L159.build_agent159(dict(cfg, **c))  # noqa: E731
    cases = json.loads((ART159 / "cases159.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_dialogue(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop159", "cases_file": "cases159.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART159 / "probe159-loop159.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop159 n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
