#!/usr/bin/env python3
"""Experiment 163 -- G1 bench through loop163 by import (Muse).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped to loop163. Outputs go into
artifacts/fable-lowercase163-20260922/ only. Per-item verdicts AND replies
are diffed against the sealed loop150 rows
(artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl,
read-only): ZERO moves predicted (pre-seal pure-function scan of all 600
bench items: no teach subject is all-lowercase, no teach value under a
person relation is all-lowercase, no question owner span is all-lowercase;
see PASSMARKS.md). Any move fails G1 honestly. 0 new wrong.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix163_bench.py
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
import fable_loop163_agent as L163  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART163 = ROOT / "artifacts" / "fable-lowercase163-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"

REF_TAGS = {"edit200": "edit200", "new_121_4hop": "new_121_4hop",
            "old_s2fresh_4hop": "old_s2fresh_4hop"}


def main() -> int:
    cfg = copy.deepcopy(L163.DEFAULT_CONFIG163)
    ART163.mkdir(parents=True, exist_ok=True)
    workroot = ART163 / "scratch-bench-loop163"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop163",
                 "arms": {}}
    diffs: dict = {}
    new_wrong: dict = {}
    for tag, path in (("edit200", B129.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129.DATA_OLD),
                      ("new_121_4hop", B129.DATA_NEW)):
        ref_tag = REF_TAGS[tag] if tag != "old_s2fresh_4hop" else \
            "old_s2fresh_4hop"
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / tag, L163.Loop163Daemon, cfg)
                for it in items]
        (ART163 / f"fable_bench163_loop163_{ref_tag}_rows.jsonl"
         ).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop163", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop163 {tag}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART150 / f"fable_bench150_loop150_{ref_tag}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
        wrong = [r["id"] for r in rows
                 if r["verdict"] == "wrong"
                 and base.get(r["id"], {}).get("verdict") != "wrong"]
        diffs[tag] = {"verdict_moves": moved, "reply_moves": reply_moves}
        new_wrong[tag] = wrong
        print(f"  vs loop150: verdict_moves={moved} "
              f"reply_moves={reply_moves} new_wrong={wrong}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_loop150"] = diffs
    out["new_wrong"] = new_wrong
    (ART163 / "fable_bench163_loop163_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
