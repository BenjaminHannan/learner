#!/usr/bin/env python3
"""Experiment 137d G3-143 driver -- question red team 143 through loop137d.

Reuses scripts/fable_redteam143_run.py BY IMPORT (sealed cases, judge,
markers); only the daemon factory is loop137d's. Compares per-case
verdicts against loop137c's own frozen rows
(artifacts/fable-hypo137c-20260922/redteam143-loop137c.json). Bar: 0
new WRONG vs loop137c; every other move listed (predicted: none --
pre-seal scan of all 124 cases found 0 frame-led inputs). Outputs into
artifacts/fable-frame137d-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137d_redteam143.py
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop137d_agent as L137D  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-frame137d-20260922"
ART137C = ROOT / "artifacts" / "fable-hypo137c-20260922"


def run_arm(tag: str, daemon_cls, base_cfg: dict) -> list[dict]:
    R143.Loop132Daemon = daemon_cls  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base_cfg)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / f"scratch143-{tag}"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / f"redteam143-{tag}.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    return rows


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cfg137d = copy.deepcopy(L137D.DEFAULT_CONFIG137D)
    cfg137d["sleep_threshold"] = 100000
    rows137d = run_arm("loop137d", L137D.Loop137dDaemon, cfg137d)
    base = json.loads((ART137C / "redteam143-loop137c.json").read_text(
        encoding="utf-8"))["rows"]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows137d:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "family": r.get("family"),
                          "loop137c": b["verdict"],
                          "loop137d": r["verdict"],
                          "reply137c": str(b.get("reply", ""))[:120],
                          "reply137d": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-ANSWER" and \
                    b["verdict"] != "WRONG-ANSWER":
                new_wrong += 1
    out = {"seconds": round(time.time() - t0, 1),
           "loop137c": dict(Counter(r["verdict"] for r in base)),
           "loop137d": dict(Counter(r["verdict"] for r in rows137d)),
           "new_wrong_vs_loop137c": new_wrong, "moves": moves}
    (ART / "redteam143-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3-143: loop137c {out['loop137c']} loop137d {out['loop137d']} "
          f"new_wrong={new_wrong} moves={len(moves)} in {out['seconds']}s",
          flush=True)
    for m in moves:
        print(f"  MOVE {m['id']} [{m['family']}]: "
              f"{m['loop137c']} -> {m['loop137d']}", flush=True)
    return 1 if new_wrong else 0


if __name__ == "__main__":
    sys.exit(main())
