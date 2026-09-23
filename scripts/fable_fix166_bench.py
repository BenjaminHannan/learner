#!/usr/bin/env python3
"""Experiment 166 -- G1 bench through loop166 vs frozen loop162b rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
(the bench121-lineage driver the base folder's own bench used) with only the
daemon class/config swapped. Compares per-item verdict AND reply against the
BASE agent's frozen rows
(artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl,
read-only): ZERO moves predicted (pre-seal pure-function scan: no bench
teach matches the "my <R> is <V>" frame and no bench question matches the
"my <chain>?" frame -- the me frames fire only on first-person possessives,
absent from bench inputs; the reply rewrite only fires on me-claimed turns).
Any move fails G1 honestly. Outputs go into
artifacts/fable-me166-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166_bench.py
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
import fable_loop166_agent as L166  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"
ART166 = ROOT / "artifacts" / "fable-me166-20260922"


def main(argv=None) -> int:
    cfg = copy.deepcopy(L166.DEFAULT_CONFIG166)
    ART166.mkdir(parents=True, exist_ok=True)
    workroot = ART166 / "scratch-bench-loop166"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop166",
                 "arms": {}}
    diffs: dict = {}
    for split, path in (("edit200", B129.DATA_EDIT200),
                        ("old_s2fresh_4hop", B129.DATA_OLD),
                        ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L166.Loop166Daemon,
                              cfg) for it in items]
        (ART166 / f"fable_bench166_loop166_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop166", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop166 {split}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART162B / f"fable_bench162b_loop162b_{split}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        reply_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("reply") != r["reply"]]
        teach_moves = [r["id"] for r in rows
                       if base.get(r["id"], {}).get("teach_replies")
                       != r["teach_replies"]]
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN")
                     and base.get(r["id"], {}).get("verdict") in ("OK",)]
        diffs[split] = {"verdict_moves": moved,
                        "reply_moves": reply_moves,
                        "teach_reply_moves": teach_moves,
                        "new_wrong": new_wrong}
        print(f"  vs loop162b: verdict_moves={moved} "
              f"reply_moves={len(reply_moves)} "
              f"teach_reply_moves={len(teach_moves)} "
              f"new_wrong={new_wrong}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_loop162b"] = diffs
    (ART166 / "fable_bench166_loop166_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
