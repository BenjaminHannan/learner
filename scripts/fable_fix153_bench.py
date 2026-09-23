#!/usr/bin/env python3
"""Experiment 153 -- G1 bench through loop153 by import (Muse).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped to loop153. Outputs go into
artifacts/fable-reverse153-20260922/ only. Per-item verdicts are diffed
against the sealed loop150 rows (artifacts/fable-fix150-20260922/
fable_bench150_loop150_*_rows.jsonl, read-only): ZERO moves predicted (the
reverse stage fires only on a forward miss matching a closed frame; the
full gate fires nowhere on all 600 bench questions -- see PASSMARKS.md). Any
move fails G1 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix153_bench.py
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
import fable_loop153_agent as L153  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART153 = ROOT / "artifacts" / "fable-reverse153-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def main() -> int:
    cfg = copy.deepcopy(L153.DEFAULT_CONFIG153)
    ART153.mkdir(parents=True, exist_ok=True)
    workroot = ART153 / "scratch-bench-loop153"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop153",
                 "arms": {}}
    diffs: dict = {}
    for tag in ("edit200", "old_s2fresh_4hop", "new_121_4hop"):
        path = {"edit200": B129.DATA_EDIT200,
                "old_s2fresh_4hop": B129.DATA_OLD,
                "new_121_4hop": B129.DATA_NEW}[tag]
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / tag, L153.Loop153Daemon, cfg)
                for it in items]
        (ART153 / f"fable_bench153_loop153_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault("loop153", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"loop153 {tag}: {B129.totals(table)}", flush=True)
        sealed = [json.loads(l) for l in
                  (ART150 / f"fable_bench150_loop150_{tag}_rows.jsonl"
                   ).read_text(encoding="utf-8").splitlines() if l.strip()]
        base = {r["id"]: r for r in sealed}
        moved = [r["id"] for r in rows
                 if (r["id"] not in base
                     or (r.get("verdict"), r.get("reply")) !=
                     (base[r["id"]].get("verdict"),
                      base[r["id"]].get("reply")))]
        diffs[tag] = moved
        print(f"  moves vs loop150: {len(moved)} {moved[:10]}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["moves_vs_loop150"] = diffs
    (ART153 / "fable_bench153_loop153_summary.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wrote summary, {out['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
