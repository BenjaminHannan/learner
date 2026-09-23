#!/usr/bin/env python3
"""Experiment 167d -- G1 bench through loop167d vs frozen loop167b AND loop162b rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped (same pattern as
scripts/fable_fix167b_bench.py, read-only). Compares per-item verdict AND
reply against BOTH the base loop167b's rows
(artifacts/fable-verb167b-20260922/fable_bench167b_loop167b_*_rows.jsonl,
read-only) and loop162b's frozen rows
(artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl,
read-only): ZERO moves predicted (the pre-seal exact-schema scan found
no added-frame hit -- no "works at" / "speaks" / "Where does X work" /
"What language(s) does X speak" shape -- in any of the 600 bench
teaches+questions, so no bench item can reach the added stage; every
other shape takes the loop167b code path literally). Any move fails G1
honestly. Outputs go into artifacts/fable-verb167d-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167d_bench.py
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
import fable_loop167d_agent as L167D  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"
ART167D = ROOT / "artifacts" / "fable-verb167d-20260922"


def _moves(rows, sealed, keys=("verdict", "reply", "teach_replies")):
    base = {r["id"]: r for r in sealed}
    return {k: [r["id"] for r in rows
                if base.get(r["id"], {}).get(k) != r[k]]
            for k in keys}


def main(argv=None) -> int:
    cfg = copy.deepcopy(L167D.DEFAULT_CONFIG167D)
    ART167D.mkdir(parents=True, exist_ok=True)
    workroot = ART167D / "scratch-bench-loop167d"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop167d",
                 "arms": {}}
    diffs: dict = {}
    for split, path, f167b, f162 in (
            ("edit200", B129.DATA_EDIT200,
             "fable_bench167b_loop167b_edit200_rows.jsonl",
             "fable_bench162b_loop162b_edit200_rows.jsonl"),
            ("old_s2fresh_4hop", B129.DATA_OLD,
             "fable_bench167b_loop167b_old_s2fresh_4hop_rows.jsonl",
             "fable_bench162b_loop162b_old_s2fresh_4hop_rows.jsonl"),
            ("new_121_4hop", B129.DATA_NEW,
             "fable_bench167b_loop167b_new_121_4hop_rows.jsonl",
             "fable_bench162b_loop162b_new_121_4hop_rows.jsonl")):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L167D.Loop167dDaemon,
                              cfg) for it in items]
        (ART167D / f"fable_bench167d_loop167d_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop167d", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop167d {split}: {B129.totals(table)}", flush=True)
        sealed167b = [json.loads(l) for l in
                      (ART167B / f167b).read_text(
                          encoding="utf-8").splitlines() if l.strip()]
        sealed162 = [json.loads(l) for l in
                     (ART162B / f162).read_text(
                         encoding="utf-8").splitlines() if l.strip()]
        m167b = _moves(rows, sealed167b)
        m162 = _moves(rows, sealed162)
        base167b = {r["id"]: r for r in sealed167b}
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN")
                     and base167b.get(r["id"], {}).get("verdict") in ("OK",)]
        diffs[split] = {"vs_loop167b": m167b, "vs_loop162b": m162,
                        "new_wrong_vs167b": new_wrong}
        print(f"  vs loop167b: verdict_moves={m167b['verdict']} "
              f"reply_moves={len(m167b['reply'])}", flush=True)
        print(f"  vs loop162b: verdict_moves={m162['verdict']} "
              f"reply_moves={len(m162['reply'])} new_wrong={new_wrong}",
              flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_bases"] = diffs
    (ART167D / "fable_bench167d_loop167d_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
