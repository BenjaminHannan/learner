#!/usr/bin/env python3
"""Experiment 160c -- G1 bench through loop160c by import (Muse).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped to loop160c. Outputs go into
artifacts/fable-twohop160c-20260922/ only. Per-item verdicts AND replies are
diffed against the sealed loop160b rows
(artifacts/fable-correct160b-20260922/fable_bench160b_loop160b_*_rows.jsonl,
read-only): ZERO moves predicted (pre-seal scan: the reused
parse_bare_correction fires on no bench teach sentence over 26647 bench
strings per 160b PASSMARKS, and every bench item runs on a fresh daemon, so
no previous reply ever states a chain; see PASSMARKS.md). Any move fails G1
honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix160c_bench.py
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
import fable_loop160c_agent as L160c  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART160C = ROOT / "artifacts" / "fable-twohop160c-20260922"
ART160B = ROOT / "artifacts" / "fable-correct160b-20260922"


def main() -> int:
    cfg = copy.deepcopy(L160c.DEFAULT_CONFIG160C)
    ART160C.mkdir(parents=True, exist_ok=True)
    workroot = ART160C / "scratch-bench-loop160c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop160c",
                 "arms": {}}
    diffs: dict = {}
    for tag, path in (("edit200", B129.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129.DATA_OLD),
                      ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / tag, L160c.Loop160cDaemon, cfg)
                for it in items]
        (ART160C / f"fable_bench160c_loop160c_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop160c", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop160c {tag}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART160B / f"fable_bench160b_loop160b_{tag}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
        diffs[tag] = {"verdict_moves": moved, "reply_moves": reply_moves}
        print(f"  vs loop160b: verdict_moves={moved} "
              f"reply_moves={len(reply_moves)}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_loop160b"] = diffs
    (ART160C / "fable_bench160c_loop160c_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    n_move = sum(len(d["verdict_moves"]) + len(d["reply_moves"])
                 for d in diffs.values())
    return 0 if n_move == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
