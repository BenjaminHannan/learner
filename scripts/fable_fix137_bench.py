#!/usr/bin/env python3
"""Experiment 137 -- bench arm: loop129b vs loop137 per-item diff.

Reuses scripts/fable_loop129b_bench.py by import (run_item, summarize,
totals; scorer v2 from fable_bench121_run) with only the daemon class/config
swapped. Three splits: edit200, old_s2fresh_4hop, new_121_4hop. Outputs go
only into artifacts/fable-fix137-20260922/ (never the exp-129 dir).

Writes:
  artifacts/fable-fix137-20260922/fable_bench137_<agent>_<tag>_rows.jsonl
  artifacts/fable-fix137-20260922/fable_bench137_summary.json (incl. the
    per-item verdict diff: identical / differing item ids)
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137_bench.py --run
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

import fable_loop129b_agent as L129b  # noqa: E402 (base arm, read-only)
import fable_loop129b_bench as B129b  # noqa: E402 (run_item, read-only)
import fable_loop137_agent as L137  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix137-20260922"

AGENTS = {
    "loop129b": (L129b.Loop129bDaemon, copy.deepcopy(
        L129b.DEFAULT_CONFIG129B)),
    "loop137": (L137.Loop137Daemon, copy.deepcopy(
        L137.DEFAULT_CONFIG137)),
}


def cmd_run() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch-bench137"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "arms": {}, "diff": {}}
    by_agent_tag: dict = {}
    for agent, (daemon_cls, cfg) in AGENTS.items():
        by_agent_tag[agent] = {}
        for tag, path in (("edit200", B129b.DATA_EDIT200),
                          ("old_s2fresh_4hop", B129b.DATA_OLD),
                          ("new_121_4hop", B129b.DATA_NEW)):
            items = [json.loads(l) for l in path.read_text(
                encoding="utf-8").splitlines() if l.strip()]
            rows = [B129b.run_item(it, workroot / f"{agent}-{tag}",
                                   daemon_cls, cfg) for it in items]
            (ART / f"fable_bench137_{agent}_{tag}_rows.jsonl").write_text(
                "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                           for r in rows) + "\n", encoding="utf-8")
            table = B129b.summarize(rows)
            out["arms"].setdefault(agent, {})[tag] = {
                "n": len(rows), "table": table,
                "totals": B129b.totals(table)}
            by_agent_tag[agent][tag] = {r["id"]: r["verdict"] for r in rows}
            print(f"{agent} {tag}: {B129b.totals(table)}", flush=True)
    for tag in ("edit200", "old_s2fresh_4hop", "new_121_4hop"):
        a = by_agent_tag["loop129b"][tag]
        b = by_agent_tag["loop137"][tag]
        differing = sorted(i for i in a if a[i] != b.get(i))
        out["diff"][tag] = {"n": len(a), "differing": differing,
                            "identical": not differing}
        print(f"diff {tag}: {len(differing)} differing {differing[:10]}",
              flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench137_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 137 bench (129b vs 137)")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if not args.run:
        ap.print_help()
        return 0
    return cmd_run()


if __name__ == "__main__":
    sys.exit(main())
