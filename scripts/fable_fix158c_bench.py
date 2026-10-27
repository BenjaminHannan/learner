#!/usr/bin/env python3
"""Exp 158c G1 driver -- bench121 splits through loop158c vs sealed loop158b.

Reuses artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py BY
IMPORT (split table, row loader -- the same driver the base used) and
scripts/fable_bench121_run.py BY IMPORT (run_item/scorer); only the daemon
under test is swapped to Loop158cDaemon. Compares per-item verdicts
against the sealed fable_bench121_loop158b_*_rows.jsonl files in
artifacts/fable-whrel158b-20260922/. Bar: 0 new wrong, every move
listed (prediction: none). Outputs into
artifacts/fable-whcity158c-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158c_bench.py
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
ART138B = SCRIPTS.parent / "artifacts" / "fable-agent138b-20260922"
if str(ART138B) not in sys.path:
    sys.path.insert(0, str(ART138B))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop138b_bench121 as BB  # noqa: E402 (splits/loader, read-only)
import fable_loop158c_agent as L158c  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-whcity158c-20260922"
ART158B = ROOT / "artifacts" / "fable-whrel158b-20260922"

SEALED = {
    "new_121_4hop": "fable_bench121_loop158b_new_121_4hop_rows.jsonl",
    "old_s2fresh_4hop": "fable_bench121_loop158b_old_s2fresh_4hop_rows.jsonl",
    "edit200": "fable_bench121_loop158b_edit200_rows.jsonl",
    "bench132_4hop": "fable_bench121_loop158b_bench132_4hop_rows.jsonl",
}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    B.Loop121Daemon = L158c.Loop158cDaemon
    cfg = copy.deepcopy(L158c.DEFAULT_CONFIG158C)
    cfg["sleep_threshold"] = 100000
    workroot = ART / "scratch-bench121-loop158c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "agent": "loop158c", "splits": {}}
    rc = 0
    for stag, path, _sealed in list(BB.SPLITS_3) + [BB.SPLIT_132]:
        items = BB.load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_loop158c_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        base_rows = BB.load_rows(ART158B / SEALED[stag])
        s_by_id = {r["id"]: r for r in base_rows}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop158b": s["verdict"],
                              "loop158c": r["verdict"],
                              "reply158b": str(s.get("reply", ""))[:160],
                              "reply158c": str(r.get("reply", ""))[:160]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        if new_wrong:
            rc = 1
        summary["splits"][stag] = {"loop158c": cell, "moves": moves,
                                   "new_wrong_vs_loop158b": new_wrong}
        print(f"G1 {stag}: {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
        for m in moves:
            print(f"  MOVE {m['id']}: {m['loop158b']} -> {m['loop158c']}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / "bench158c-summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G1 {summary['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
