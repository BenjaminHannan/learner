#!/usr/bin/env python3
"""Experiment 167b -- G1 bench through loop167b vs frozen loop167 AND loop162b rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped (same pattern as
scripts/fable_fix167_bench.py, read-only). Compares per-item verdict AND
reply against BOTH the base loop167's rows
(artifacts/fable-verb167-20260922/fable_bench167_loop167_*_rows.jsonl,
read-only) and loop162b's frozen rows
(artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl,
read-only): ZERO moves predicted (the 167b screen only narrows 167's
claims, and 167's pre-seal exact-schema scan found no verb-frame hit in
any of the 600 bench teaches+questions, so no bench item can reach the
screen; married statements stay declined and born city-of shapes stay
vetoed exactly as in 167). Any move fails G1 honestly. Outputs go into
artifacts/fable-verb167b-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167b_bench.py
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
import fable_loop167b_agent as L167B  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"
ART167 = ROOT / "artifacts" / "fable-verb167-20260922"
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"


def _moves(rows, sealed, keys=("verdict", "reply", "teach_replies")):
    base = {r["id"]: r for r in sealed}
    return {k: [r["id"] for r in rows
                if base.get(r["id"], {}).get(k) != r[k]]
            for k in keys}


def main(argv=None) -> int:
    cfg = copy.deepcopy(L167B.DEFAULT_CONFIG167B)
    ART167B.mkdir(parents=True, exist_ok=True)
    workroot = ART167B / "scratch-bench-loop167b"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop167b",
                 "arms": {}}
    diffs: dict = {}
    for split, path, f167, f162 in (
            ("edit200", B129.DATA_EDIT200,
             "fable_bench167_loop167_edit200_rows.jsonl",
             "fable_bench162b_loop162b_edit200_rows.jsonl"),
            ("old_s2fresh_4hop", B129.DATA_OLD,
             "fable_bench167_loop167_old_s2fresh_4hop_rows.jsonl",
             "fable_bench162b_loop162b_old_s2fresh_4hop_rows.jsonl"),
            ("new_121_4hop", B129.DATA_NEW,
             "fable_bench167_loop167_new_121_4hop_rows.jsonl",
             "fable_bench162b_loop162b_new_121_4hop_rows.jsonl")):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L167B.Loop167bDaemon,
                              cfg) for it in items]
        (ART167B / f"fable_bench167b_loop167b_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop167b", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop167b {split}: {B129.totals(table)}", flush=True)
        sealed167 = [json.loads(l) for l in
                     (ART167 / f167).read_text(
                         encoding="utf-8").splitlines() if l.strip()]
        sealed162 = [json.loads(l) for l in
                     (ART162B / f162).read_text(
                         encoding="utf-8").splitlines() if l.strip()]
        m167 = _moves(rows, sealed167)
        m162 = _moves(rows, sealed162)
        base162 = {r["id"]: r for r in sealed162}
        new_wrong = [r["id"] for r in rows
                     if r["verdict"] not in ("OK", "ABSTAIN")
                     and base162.get(r["id"], {}).get("verdict") in ("OK",)]
        diffs[split] = {"vs_loop167": m167, "vs_loop162b": m162,
                        "new_wrong_vs162b": new_wrong}
        print(f"  vs loop167: verdict_moves={m167['verdict']} "
              f"reply_moves={len(m167['reply'])}", flush=True)
        print(f"  vs loop162b: verdict_moves={m162['verdict']} "
              f"reply_moves={len(m162['reply'])} new_wrong={new_wrong}",
              flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_bases"] = diffs
    (ART167B / "fable_bench167b_loop167b_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
