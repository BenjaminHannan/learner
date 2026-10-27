#!/usr/bin/env python3
"""Exp 142 S4 driver -- bench121 by import, daemon class/config swapped.

Mirrors artifacts/fable-loop134-20260922/fable_loop134_bench121.py (new file,
own prefix): imports run_item/summarize from scripts/fable_bench121_run.py
(no logic copied); only the daemon class under test and the base config are
swapped. Output goes into artifacts/fable-perf142-20260922/ -- the sealed
loop134 rows are read, never overwritten.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_perf142_bench121.py --agent loop142  # or loop134
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
ROOT = SCRIPTS.parent

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop134_agent as L134  # noqa: E402 (baseline, read-only)
import fable_loop142_agent as L142  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-perf142-20260922"

AGENTS = {
    "loop142": (L142.Loop142Daemon, copy.deepcopy(L142.DEFAULT_CONFIG142)),
    "loop134": (L134.Loop134Daemon, copy.deepcopy(L134.DEFAULT_CONFIG134)),
}


def cmd_run(which: str) -> int:
    daemon_cls, cfg = AGENTS[which]
    B.Loop121Daemon = daemon_cls  # run_item resolves the class here
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / ("scratch-bench121-%s" % which)
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "arms": {which: {}}}
    for tag, path in (("new_121_4hop", B.DATA_NEW),
                      ("old_s2fresh_4hop", B.DATA_OLD)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B.run_item(it, workroot / tag, copy.deepcopy(cfg))
                for it in items]
        (ART / ("fable_bench121_%s_%s_rows.jsonl" % (which, tag))).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        out["arms"][which][tag] = {"n": len(rows),
                                   "table": B.summarize(rows)}
        print("%s %s: items=%d" % (which, tag, len(rows)))
        for typ, cell in sorted(out["arms"][which][tag]["table"].items()):
            print("  %s: %s" % (typ, cell))
    out["seconds"] = round(time.time() - t0, 1)
    (ART / ("fable_bench121_summary_%s.json" % which)).write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("TOTAL seconds=%s" % out["seconds"])
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 142 S4 bench121 driver")
    ap.add_argument("--agent", required=True, choices=sorted(AGENTS))
    args = ap.parse_args(argv)
    return cmd_run(args.agent)


if __name__ == "__main__":
    sys.exit(main())
