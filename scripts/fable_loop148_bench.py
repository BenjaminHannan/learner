#!/usr/bin/env python3
"""Exp 148 Q3 -- benches per-item identical to the loop134 base.

Four splits via scripts/fable_loop129b_bench.py by import (run_item,
summarize, totals; scorer v2): edit200, old_s2fresh_4hop, new_121_4hop,
new_132_4hop. Each split runs once under Loop134Daemon (base) and once
under Loop148Daemon, fresh daemon dir per item, outputs into
artifacts/fable-screen148-20260922/ only; sealed bench artifacts never
written. Per-item verdict + reply diffs base-vs-148 are reported; only the
PASSMARKS-predicted items may differ.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop148_bench.py --run
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
import fable_loop134_agent as L134  # noqa: E402 (base arm, read-only)
import fable_loop148_agent as L148  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-screen148-20260922"

SPLITS = (
    ("edit200", ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"),
    ("old_s2fresh_4hop", ROOT / "data" / "open" / "bench103"
     / "fable_edit103_s2fresh_4hop.jsonl"),
    ("new_121_4hop", ROOT / "data" / "open" / "bench121"
     / "fable_edit121_4hop.jsonl"),
    ("new_132_4hop", ROOT / "data" / "open" / "bench132"
     / "fable_edit132_4hop.jsonl"),
)


def run_split(tag: str, path: Path, workroot: Path, daemon_cls,
              cfg: dict, outname: str) -> tuple[list[dict], dict]:
    items = [json.loads(l) for l in path.read_text(
        encoding="utf-8").splitlines() if l.strip()]
    rows = [B129b.run_item(it, workroot / tag, daemon_cls, cfg)
            for it in items]
    (ART / outname).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    table = B129b.summarize(rows)
    return rows, {"n": len(rows), "table": table,
                  "totals": B129b.totals(table)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 148 bench (base + 148)")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if not args.run:
        ap.print_help()
        return 0
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch-bench"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2-via-fable_loop129b_bench",
                     "splits": {}}
    for tag, path in SPLITS:
        rb, tb = run_split(tag, path, workroot / "base",
                           L134.Loop134Daemon, L134.DEFAULT_CONFIG134,
                           f"fable_bench148_loop134_{tag}_rows.jsonl")
        rn, tn = run_split(tag, path, workroot / "new148",
                           L148.Loop148Daemon, L148.DEFAULT_CONFIG148,
                           f"fable_bench148_loop148_{tag}_rows.jsonl")
        vb = {r["id"]: r["verdict"] for r in rb}
        vn = {r["id"]: r["verdict"] for r in rn}
        vdiff = sorted(i for i in vb if vb[i] != vn.get(i))
        rbmap = {r["id"]: r["reply"] for r in rb}
        rnmap = {r["id"]: r["reply"] for r in rn}
        rdiff = sorted(i for i in rbmap if rbmap[i] != rnmap.get(i))
        summary["splits"][tag] = {
            "base": tb["totals"], "loop148": tn["totals"],
            "verdict_diffs": vdiff, "reply_diffs": rdiff}
        print(f"{tag}: base={tb['totals']} new148={tn['totals']} "
              f"vdiff={vdiff} rdiff={len(rdiff)}", flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench148_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={summary['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
