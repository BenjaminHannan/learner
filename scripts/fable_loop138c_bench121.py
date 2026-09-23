#!/usr/bin/env python3
"""Exp 138c B1 driver -- bench121 new + old fresh + Fable-Edit by import.

Same shape as artifacts/fable-agent138-20260922/fable_loop138_bench121.py
(no logic copied from sealed files; imports run_item/classify/summarize
from scripts/fable_bench121_run.py read-only); only the daemon class under
test is swapped to Loop138cDaemon with DEFAULT_CONFIG138C. Compares
per-item verdicts AND reply texts against the SEALED loop134 rows
(read-only, never overwritten) for new/old, and against the sealed
loop138 edit200 rows for Fable-Edit (no sealed loop134 edit200 rows file
exists; loop138's A2 edit200 rows were verdict-identical to loop134's
A1 bench counts 150/50/0, so identity with loop138's rows carries the
same bar -- stated in PASSMARKS.md).

Outputs into --out (default artifacts/fable-self138c-20260922/). Run
(Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138c_bench121.py [--out DIR]
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop138c_agent as L138C  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-self138c-20260922"
ART134 = ROOT / "artifacts" / "fable-loop134-20260922"
ART138 = ROOT / "artifacts" / "fable-agent138-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 138c B1 bench driver")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args()
    out = Path(args.out)
    B.Loop121Daemon = L138C.Loop138cDaemon
    cfg = copy.deepcopy(L138C.DEFAULT_CONFIG138C)
    out.mkdir(parents=True, exist_ok=True)
    workroot = out / "scratch-bench121-138c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         ART134 / "fable_bench121_loop134_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         ART134 / "fable_bench121_loop134_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134,
         ART138 / "fable_bench121_loop138_edit200_rows.jsonl"),
    )
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "splits": {}}
    rc = 0
    for tag, path, sealed_path in splits:
        items = [json.loads(line) for line in path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        rows = [B.run_item(it, workroot / tag, copy.deepcopy(cfg))
                for it in items]
        (out / f"fable_bench121_loop138c_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        sealed = [json.loads(line) for line in sealed_path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in sealed}
        new_wrong, moves, reply_moves = 0, [], []
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append(
                    {"id": r["id"], "ref": s["verdict"],
                     "loop138c": r["verdict"],
                     "reply_ref": s.get("reply", "")[:160],
                     "reply138c": r.get("reply", "")[:160]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
            elif r.get("reply", "") != s.get("reply", ""):
                reply_moves.append(r["id"])
        ref_cell = {
            "correct": sum(1 for r in sealed if r["verdict"] == "correct"),
            "abstain": sum(1 for r in sealed if r["verdict"] == "abstain"),
            "wrong": sum(1 for r in sealed if r["verdict"] == "wrong")}
        if new_wrong != 0 or moves or reply_moves:
            rc = 1
        summary["splits"][tag] = {
            "loop138c": cell, "by_type": table,
            "compare": {"ref": ref_cell, "new_wrong_vs_ref": new_wrong,
                        "moves": moves, "reply_moves": reply_moves}}
        print(f"{tag}: loop138c {cell} ref={ref_cell} "
              f"new_wrong={new_wrong} moves={len(moves)} "
              f"reply_moves={len(reply_moves)}", flush=True)
        for m in moves:
            print(f"  MOVE {m['id']}: {m['ref']} -> {m['loop138c']}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (out / "fable_bench121_summary_loop138c.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"B1 {summary['seconds']}s -> "
          f"{out / 'fable_bench121_summary_loop138c.json'}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
