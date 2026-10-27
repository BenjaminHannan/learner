#!/usr/bin/env python3
"""Experiment 137c G1 driver -- bench121 splits through loop137c.

Reuses scripts/fable_bench121_run.py BY IMPORT (run_item/scorer, the same
module the loop137b bench driver imports); only the daemon class under
test is loop137c's. Compares per-item verdicts AND replies against
loop137b's own frozen rows in artifacts/fable-discourse137b-20260922/
(fable_bench121_loop137b_*_rows.jsonl). Bar: 0 new wrong, every move
predicted in writing before the run. Outputs into
artifacts/fable-hypo137c-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137c_bench.py
"""

from __future__ import annotations

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
import fable_loop137c_agent as L137C  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-hypo137c-20260922"
ART137B = ROOT / "artifacts" / "fable-discourse137b-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"

SPLITS = (
    ("new_121_4hop", B.DATA_NEW,
     "fable_bench121_loop137b_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD,
     "fable_bench121_loop137b_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", DATA134, "fable_bench121_loop137b_edit200_rows.jsonl"),
    ("bench132_4hop", DATA132,
     "fable_bench121_loop137b_bench132_4hop_rows.jsonl"),
)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    B.Loop121Daemon = L137C.Loop137cDaemon
    cfg = copy.deepcopy(L137C.DEFAULT_CONFIG137C)
    cfg["sleep_threshold"] = 100000
    workroot = ART / "scratch-bench121-loop137c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop137c",
                     "splits": {}}
    rc = 0
    for stag, path, sealed_name in SPLITS:
        items = load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_loop137c_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        base_rows = load_rows(ART137B / sealed_name)
        s_by_id = {r["id"]: r for r in base_rows}
        moves, reply_moves, new_wrong = [], [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop137b": s["verdict"],
                              "loop137c": r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
            elif r.get("reply", "") != s.get("reply", ""):
                reply_moves.append({"id": r["id"]})
        if new_wrong != 0:
            rc = 1
        summary["splits"][stag] = {"loop137c": cell, "by_type": table,
                                   "moves": moves,
                                   "reply_moves": reply_moves,
                                   "new_wrong_vs_loop137b": new_wrong}
        print(f"{stag}: loop137c {cell} moves={len(moves)} "
              f"reply_moves={len(reply_moves)} new_wrong={new_wrong}",
              flush=True)
        for m in moves + reply_moves:
            print(f"  MOVE {m}", flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench121_summary_loop137c.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G1 {summary['seconds']}s -> fable_bench121_summary_loop137c.json "
          f"rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
