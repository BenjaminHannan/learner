#!/usr/bin/env python3
"""Exp 148 Q1 -- sealed 143 cases re-run on the loop132+148 variant.

Reuses the SEALED 143 runner by import (read-only): the case file, verdict
logic, and abstain markers are untouched; only the daemon class (swapped to
Loop148Daemon132) and the ART output path (redirected to this experiment's
artifact dir) differ. Compares per-case verdicts against the sealed loop132
results (artifacts/fable-redteam143-20260922/fable_redteam143_results.json).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop148_q1.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop148_agent as L148  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (sealed runner, read-only)

ROOT = SCRIPTS.parent
ART148 = ROOT / "artifacts" / "fable-screen148-20260922"
ART143 = ROOT / "artifacts" / "fable-redteam143-20260922"

TARGETS = {"N1", "N2", "N3", "N4", "N5", "T1", "T5", "B1"}


def main() -> int:
    ART148.mkdir(parents=True, exist_ok=True)
    # Redirect the sealed runner's outputs to this experiment's dir only.
    R143.ART = ART148
    R143.CASES_PATH = ART143 / "fable_redteam143_cases.json"
    R143.Loop132Daemon = L148.Loop148Daemon132  # type: ignore[attr-defined]
    t0 = time.time()
    rc = R143.main()
    seconds = round(time.time() - t0, 1)
    out = ART148 / "fable_redteam143_results.json"
    if out.exists():
        out.rename(ART148 / "fable_q1_143_on132plus148_results.json")
    rows = json.loads((ART148 / "fable_q1_143_on132plus148_results.json")
                      .read_text(encoding="utf-8"))["rows"]
    sealed = {r["id"]: r for r in json.loads(
        (ART143 / "fable_redteam143_results.json").read_text(
            encoding="utf-8"))["rows"]}
    targets = [r for r in rows if r["id"] in TARGETS]
    n_target_abstain = sum(1 for r in targets if r["verdict"] != "WRONG-ANSWER")
    others = [r for r in rows if r["id"] not in TARGETS]
    worse = [r["id"] for r in others
             if _worse_than(sealed[r["id"]]["verdict"], r["verdict"])]
    rep = {"seconds": seconds, "targets": sorted(TARGETS),
           "n_target_no_confident_answer": n_target_abstain,
           "target_rows": {r["id"]: {"verdict": r["verdict"],
                                     "reply": r["reply"][:160]}
                           for r in targets},
           "n_other": len(others), "worse_ids": worse,
           "counts": _counts(rows)}
    (ART148 / "fable_q1_summary.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Q1: targets no-confident {n_target_abstain}/8, "
          f"worse {worse} in {seconds} s")
    return rc


def _counts(rows: list[dict]) -> dict:
    from collections import Counter
    return dict(Counter(r["verdict"] for r in rows))


def _worse_than(old: str, new: str) -> bool:
    """OK < MISSED < WRONG-ANSWER; HARNESS-ERROR always counts as worse."""
    if new == "HARNESS-ERROR" and old != "HARNESS-ERROR":
        return True
    order = {"OK": 0, "MISSED": 1, "WRONG-ANSWER": 2, "HARNESS-ERROR": 3}
    return order.get(new, 3) > order.get(old, 3)


if __name__ == "__main__":
    sys.exit(main())
