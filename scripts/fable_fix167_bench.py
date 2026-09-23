#!/usr/bin/env python3
"""Experiment 167 -- G1 bench through loop167 vs frozen loop162b rows.

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped (same pattern as
scripts/fable_fix162b_bench.py, read-only). Compares per-item verdict AND
reply against the BASE agent's frozen rows
(artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl,
read-only): ZERO moves predicted (pre-seal exact-schema scan: no bench
teach or question matches the 167 verb frames -- lives/works/born/married
verb shapes are absent from all 600 items; married statements are declined
by design and born city-of shapes are vetoed). Any move fails G1 honestly.
Outputs go into artifacts/fable-verb167-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167_bench.py
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
import fable_loop167_agent as L167  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"
ART167 = ROOT / "artifacts" / "fable-verb167-20260922"


def main(argv=None) -> int:
    cfg = copy.deepcopy(L167.DEFAULT_CONFIG167)
    ART167.mkdir(parents=True, exist_ok=True)
    workroot = ART167 / "scratch-bench-loop167"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop167",
                 "arms": {}}
    diffs: dict = {}
    for split, path in (("edit200", B129.DATA_EDIT200),
                        ("old_s2fresh_4hop", B129.DATA_OLD),
                        ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, L167.Loop167Daemon,
                              cfg) for it in items]
        (ART167 / f"fable_bench167_loop167_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop167", {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop167 {split}: {B129.totals(table)}", flush=True)
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
    (ART167 / "fable_bench167_loop167_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
