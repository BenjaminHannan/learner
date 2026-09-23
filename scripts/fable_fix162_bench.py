#!/usr/bin/env python3
"""Experiment 162 -- G1 bench through loop162 (and the loop150x135 reference).

Reuses scripts/fable_loop129b_bench.py run_item/summarize/totals by import
with only the daemon class/config swapped. Outputs go into
artifacts/fable-thename162-20260922/ only.

--variant loop150x135: the G1 reference (loop150 + 135 guard, no 162 stage).
  Run FIRST, before the seal; its rows are frozen and sealed in PASSMARKS.
--variant loop162: the registered run; per-item verdicts AND replies are
  diffed against the frozen reference rows. ZERO moves predicted (pre-seal
  pure-function scan: no bench teach matches the The-name teach frame with
  an allowed relation, and no bench/suite question matches the The-name ask
  frame with a resolvable entity; see PASSMARKS.md). Any move fails G1
  honestly.

Registered runs (Mac CPU, offline; reference BEFORE sealing, loop162 AFTER):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix162_bench.py --variant loop150x135
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix162_bench.py --variant loop162
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

import fable_loop129b_bench as B129  # noqa: E402 (runners/scorer, read-only)
import fable_loop162_agent as L162  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART162 = ROOT / "artifacts" / "fable-thename162-20260922"

VARIANTS = {
    "loop162": (L162.Loop162Daemon, L162.DEFAULT_CONFIG162, "loop162"),
    "loop150x135": (L162.Loop150x135Daemon, L162.DEFAULT_CONFIG150X135,
                    "loop150x135"),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 162 G1 bench")
    ap.add_argument("--variant", default="loop162",
                    choices=("loop162", "loop150x135"))
    args = ap.parse_args(argv)
    daemon_cls, default_cfg, tag = VARIANTS[args.variant]
    cfg = copy.deepcopy(default_cfg)
    ART162.mkdir(parents=True, exist_ok=True)
    workroot = ART162 / f"scratch-bench-{tag}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag, "arms": {}}
    diffs: dict = {}
    for split, path in (("edit200", B129.DATA_EDIT200),
                        ("old_s2fresh_4hop", B129.DATA_OLD),
                        ("new_121_4hop", B129.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / split, daemon_cls, cfg)
                for it in items]
        (ART162 / f"fable_bench162_{tag}_{split}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"].setdefault(tag, {})[split] = {
            "n": len(rows), "table": table, "totals": B129.totals(table)}
        print(f"{tag} {split}: {B129.totals(table)}", flush=True)
        if args.variant == "loop162":
            sealed = [json.loads(l) for l in
                      (ART162 / f"fable_bench162_loop150x135_{split}_rows.jsonl"
                       ).read_text(encoding="utf-8").splitlines()
                      if l.strip()]
            base = {r["id"]: r for r in sealed}
            moved = [r["id"] for r in rows
                     if base.get(r["id"], {}).get("verdict") != r["verdict"]]
            reply_moves = [r["id"] for r in rows
                           if base.get(r["id"], {}).get("reply") != r["reply"]]
            teach_moves = [r["id"] for r in rows
                           if base.get(r["id"], {}).get("teach_replies")
                           != r["teach_replies"]]
            diffs[split] = {"verdict_moves": moved,
                            "reply_moves": reply_moves,
                            "teach_reply_moves": teach_moves}
            print(f"  vs loop150x135: verdict_moves={moved} "
                  f"reply_moves={len(reply_moves)} "
                  f"teach_reply_moves={len(teach_moves)}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    if diffs:
        out["diff_vs_loop150x135"] = diffs
    (ART162 / f"fable_bench162_{tag}_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
