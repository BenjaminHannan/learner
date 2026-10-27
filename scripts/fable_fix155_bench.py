#!/usr/bin/env python3
"""Experiment 155 -- G1 bench through loop155 by import (Muse).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped to loop155. Outputs go into
artifacts/fable-inverted155-20260922/ only. Per-item verdicts AND replies
are diffed against the sealed loop150 rows
(artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl,
read-only): ZERO moves predicted (pre-seal pure-function scan: all 180
distinct firing bench teaches already yield a base non-officeholder teach,
so the mixin returns the base untouched; see PASSMARKS.md). Any move fails
G1 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix155_bench.py
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
import fable_loop155_agent as L155  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART155 = ROOT / "artifacts" / "fable-inverted155-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def main() -> int:
    cfg = copy.deepcopy(L155.DEFAULT_CONFIG155)
    ART155.mkdir(parents=True, exist_ok=True)
    workroot = ART155 / "scratch-bench-loop155"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop155",
                 "arms": {}}
    diffs: dict = {}
    for tag, path in (("edit200", B129.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129.DATA_OLD),
                      ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / tag, L155.Loop155Daemon, cfg)
                for it in items]
        (ART155 / f"fable_bench155_loop155_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop155", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop155 {tag}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART150 / f"fable_bench150_loop150_{tag}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
        teach_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("teach_replies")
                       != r["teach_replies"]]
        diffs[tag] = {"verdict_moves": moved, "reply_moves": reply_moves,
                      "teach_reply_moves": teach_moves}
        print(f"  vs loop150: verdict_moves={moved} "
              f"reply_moves={len(reply_moves)} "
              f"teach_reply_moves={len(teach_moves)}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_loop150"] = diffs
    (ART155 / "fable_bench155_loop155_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
