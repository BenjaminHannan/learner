#!/usr/bin/env python3
"""Experiment 157c -- G1 bench through loop157c by import (Muse).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped to loop157c. Outputs go into
artifacts/fable-title157c-20260922/ only. Per-item verdicts AND replies
are diffed against the sealed loop157b rows
(artifacts/fable-filler157b-20260922/fable_bench157b_loop157b_*_rows.jsonl,
read-only). Predicted moves are listed in PASSMARKS.md (pre-seal scans +
base calibration); any unpredicted move fails G1 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157c_bench.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop129b_bench as B129  # noqa: E402 (runners/scorer, read-only)
import fable_loop157c_agent as L157C  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART157C = ROOT / "artifacts" / "fable-title157c-20260922"
ART157B = ROOT / "artifacts" / "fable-filler157b-20260922"


def main() -> int:
    cfg = copy.deepcopy(L157C.DEFAULT_CONFIG157C)
    ART157C.mkdir(parents=True, exist_ok=True)
    workroot = ART157C / "scratch-bench-loop157c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop157c",
                 "arms": {}}
    diffs: dict = {}
    for tag, path in (("edit200", B129.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129.DATA_OLD),
                      ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / tag, L157C.Loop157cDaemon, cfg)
                for it in items]
        (ART157C / f"fable_bench157c_loop157c_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop157c", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop157c {tag}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART157B / f"fable_bench157b_loop157b_{tag}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] == "wrong"
                     and base.get(r["id"], {}).get("verdict") != "wrong"]
        diffs[tag] = {"verdict_moves": moved, "reply_moves": reply_moves,
                      "new_wrong": new_wrong}
        print(f"  vs loop157b: verdict_moves={moved} "
              f"reply_moves={len(reply_moves)} new_wrong={new_wrong}",
              flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_loop157b"] = diffs
    (ART157C / "fable_bench157c_loop157c_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
