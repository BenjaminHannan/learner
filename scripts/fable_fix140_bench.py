#!/usr/bin/env python3
"""Exp 140 T3b -- benchmarks via fable_loop129b_bench by import, loop140 arm.

Same 3 splits + scorer v2 as scripts/fable_loop129b_bench.py (run_item,
summarize, totals imported, never copied); only the daemon class/config are
swapped to loop140. Outputs (rows + summary) go into
artifacts/fable-fix140-20260922/ only; sealed bench artifacts never written.

Per-item identity vs loop129b is diffed afterwards from the two row files.
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix140_bench.py --run
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop129b_bench as B129b  # noqa: E402 (runners, read-only)
import fable_loop140_agent as L140  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix140-20260922"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 140 bench (loop140 arm)")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if not args.run:
        ap.print_help()
        return 0
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch-bench-loop140"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    cfg = copy.deepcopy(L140.DEFAULT_CONFIG140)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop140", "arms": {}}
    for tag, path in (("edit200", B129b.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129b.DATA_OLD),
                      ("new_121_4hop", B129b.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129b.run_item(it, workroot / tag, L140.Loop140Daemon, cfg)
                for it in items]
        (ART / f"fable_bench140_loop140_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129b.summarize(rows)
        out["arms"].setdefault("loop140", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129b.totals(table)}
        print(f"loop140 {tag}: {B129b.totals(table)}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench140_loop140_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
