#!/usr/bin/env python3
"""Exp 138 A2 driver -- bench121 new + old fresh + Fable-Edit by import.

Imports run_item/classify/summarize from scripts/fable_bench121_run.py
(no logic copied); only the daemon class under test is swapped to
Loop138Daemon. Compares per-item verdicts against the SEALED loop134 rows
(read-only, never overwritten). Outputs into
artifacts/fable-agent138-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B artifacts/fable-agent138-20260922/fable_loop138_bench121.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop138_agent as L138  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-agent138-20260922"
ART134 = ROOT / "artifacts" / "fable-loop134-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"

SPLITS = (
    ("new_121_4hop", B.DATA_NEW, "fable_bench121_loop134_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD, "fable_bench121_loop134_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", DATA134, None),
)


def main() -> int:
    B.Loop121Daemon = L138.Loop138Daemon
    cfg = copy.deepcopy(L138.DEFAULT_CONFIG138)
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch-bench121-138"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "splits": {}}
    rc = 0
    for tag, path, sealed_name in SPLITS:
        items = [json.loads(line) for line in path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        rows = [B.run_item(it, workroot / tag, copy.deepcopy(cfg))
                for it in items]
        (ART / (f"fable_bench121_loop138_{tag}_rows.jsonl")).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        cmp = {"sealed_loop134": None, "new_wrong_vs_134": None,
               "moves": []}
        if sealed_name is not None:
            sealed = [json.loads(line) for line in
                      (ART134 / sealed_name).read_text(
                          encoding="utf-8").splitlines() if line.strip()]
            s_by_id = {r["id"]: r for r in sealed}
            new_wrong = 0
            for r in rows:
                s = s_by_id.get(r["id"])
                if s is None:
                    continue
                if r["verdict"] != s["verdict"]:
                    cmp["moves"].append(
                        {"id": r["id"], "loop134": s["verdict"],
                         "loop138": r["verdict"],
                         "reply134": s.get("reply", "")[:160],
                         "reply138": r.get("reply", "")[:160]})
                    if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                        new_wrong += 1
            cmp["sealed_loop134"] = {
                "correct": sum(1 for r in sealed if r["verdict"] == "correct"),
                "abstain": sum(1 for r in sealed if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in sealed if r["verdict"] == "wrong")}
            cmp["new_wrong_vs_134"] = new_wrong
            if new_wrong != 0:
                rc = 1
        summary["splits"][tag] = {"loop138": cell, "by_type": table,
                                  "compare": cmp}
        print(f"{tag}: loop138 {cell} sealed134={cmp['sealed_loop134']} "
              f"new_wrong={cmp['new_wrong_vs_134']} moves={len(cmp['moves'])}",
              flush=True)
        for m in cmp["moves"]:
            print(f"  MOVE {m['id']}: {m['loop134']} -> {m['loop138']}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench121_summary_loop138.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"A2 {summary['seconds']}s -> "
          f"{ART / 'fable_bench121_summary_loop138.json'}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
