#!/usr/bin/env python3
"""Experiment 164 -- G1 bench through loop164 by import (Muse).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped to loop164. Outputs go into
artifacts/fable-about164-20260922/ only. Per-item verdicts AND replies are
diffed against the sealed loop150 rows (artifacts/fable-fix150-20260922/
fable_bench150_loop150_*_rows.jsonl, read-only): ZERO moves predicted
(pre-seal scan: match_about fires on 0/4375 bench turn texts; the stage only
claims full-turn about/summary shapes, bench turns are teaches and
possessive asks; see PASSMARKS.md). 0 new wrong. Any move fails G1 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix164_bench.py
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
import fable_loop164_agent as L164  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART164 = ROOT / "artifacts" / "fable-about164-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def main() -> int:
    cfg = copy.deepcopy(L164.DEFAULT_CONFIG164)
    ART164.mkdir(parents=True, exist_ok=True)
    workroot = ART164 / "scratch-bench-loop164"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop164",
                 "arms": {}}
    diffs: dict = {}
    for tag, path in (("edit200", B129.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129.DATA_OLD),
                      ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(line) for line in path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        rows = [B129.run_item(it, workroot / tag, L164.Loop164Daemon, cfg)
                for it in items]
        (ART164 / f"fable_bench164_loop164_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop164", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop164 {tag}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(line) for line in
                  (ART150 / f"fable_bench150_loop150_{tag}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if line.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN-OK", "ok",
                                             base.get(r["id"], {}).get(
                                                 "verdict"))]
        diffs[tag] = {"verdict_moves": moved, "reply_moves": reply_moves,
                      "new_wrong": new_wrong}
        print(f"  vs loop150: verdict_moves={moved} "
              f"reply_moves={len(reply_moves)} new_wrong={new_wrong}",
              flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_loop150"] = diffs
    (ART164 / "fable_bench164_loop164_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    n_move = sum(len(d["verdict_moves"]) + len(d["reply_moves"])
                 + len(d["new_wrong"]) for d in diffs.values())
    return 0 if n_move == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
