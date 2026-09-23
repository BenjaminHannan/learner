#!/usr/bin/env python3
"""Experiment 146b bench -- per-item verdicts on the hearsay-exempt loops.

H4a: loop146c (146b doubt on loop129b) over edit200 + old_s2fresh_4hop +
     new_121_4hop + bench132_4hop, diffed per-item vs the SEALED 146 rows
     (artifacts/fable-doubt146-20260922/fable_bench146_loop146_*,
     read-only): predicted identical.
H4b: loop146d (146b doubt on loop139b) over edit200 + old_s2fresh_4hop +
     new_121_4hop, diffed per-item vs the SEALED loop139b rows
     (artifacts/fable-fix139b-20260922/, read-only): predicted 0 new
     wrong, 0 correct lost, 069 wrong->abstain.

One item, one FRESH daemon directory, English only (bytes in, outbox
reply out). Teach sentences verbatim, never rewritten. Never prints item
sentences or questions -- only aggregate counts plus failure item ids.
Outputs go into artifacts/fable-doubt146b-20260922/ only.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146b_bench.py --agent loop146c
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146b_bench.py --agent loop146d
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

import fable_loop129b_bench as B129  # noqa: E402 (run_item/scorer, read-only)
import fable_loop146c_agent as L146C  # noqa: E402 (this experiment)
import fable_loop146d_agent as L146D  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART146 = ROOT / "artifacts" / "fable-doubt146-20260922"
ART146B = ROOT / "artifacts" / "fable-doubt146b-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"

DATA_EDIT200 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_OLD = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"
DATA_NEW = ROOT / "data" / "open" / "bench121" / "fable_edit121_4hop.jsonl"
DATA_132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"


def _daemon_for(agent: str):
    if agent == "loop146c":
        return L146C.Loop146cDaemon, copy.deepcopy(
            L146C.DEFAULT_CONFIG146C)
    if agent == "loop146d":
        return L146D.Loop146dDaemon, copy.deepcopy(
            L146D.DEFAULT_CONFIG146D)
    raise ValueError(f"unknown --agent {agent!r}")


def _sealed_rows146(agent146: str, tag: str) -> dict:
    name = f"fable_bench146_{agent146}_{tag}_rows.jsonl"
    return {r["id"]: r for r in
            (json.loads(l) for l in
             (ART146 / name).read_text(encoding="utf-8").splitlines()
             if l.strip())}


def _sealed_rows139b(tag: str) -> dict:
    name = {"edit200": "fable_bench139b_loop139b_edit200_rows.jsonl",
            "old_s2fresh_4hop":
                "fable_bench139b_loop139b_old_s2fresh_4hop_rows.jsonl",
            "new_121_4hop":
                "fable_bench139b_loop139b_new_121_4hop_rows.jsonl"}[tag]
    return {r["id"]: r for r in
            (json.loads(l) for l in
             (ART139B / name).read_text(encoding="utf-8").splitlines()
             if l.strip())}


def _is_worse(before: str | None, after: str | None) -> bool:
    rank = {"correct": 2, "abstain": 1, "wrong": 0}
    return rank.get(after, -1) < rank.get(before, -1)


def _is_lost(before: str | None, after: str | None) -> bool:
    return before == "correct" and after != "correct"


def run_splits(agent: str, tags: list[str]) -> int:
    daemon_cls, cfg = _daemon_for(agent)
    outdir = ART146B
    outdir.mkdir(parents=True, exist_ok=True)
    workroot = outdir / f"scratch-bench-{agent}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    tag2path = {"edit200": DATA_EDIT200, "old_s2fresh_4hop": DATA_OLD,
                "new_121_4hop": DATA_NEW, "bench132_4hop": DATA_132}
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": agent, "arms": {}}
    diffs: dict = {}
    for tag in tags:
        path = tag2path[tag]
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129.run_item(it, workroot / tag, daemon_cls, cfg)
                for it in items]
        (outdir / f"fable_bench146b_{agent}_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"][tag] = {"n": len(rows), "table": table,
                            "totals": B129.totals(table)}
        print(f"{agent} {tag}: {B129.totals(table)}", flush=True)
        if agent == "loop146c":
            base = _sealed_rows146("loop146", tag)
        elif agent == "loop146d":
            base = _sealed_rows139b(tag)
        else:
            base = {}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        by_id = {r["id"]: r for r in rows}
        worse = [i for i in moved
                 if _is_worse(base.get(i, {}).get("verdict"),
                              by_id[i]["verdict"])]
        lost = [i for i in moved
                if _is_lost(base.get(i, {}).get("verdict"),
                            by_id[i]["verdict"])]
        diffs[tag] = {"verdict_moves": moved, "worse": worse,
                      "correct_lost": lost}
        print(f"  vs base: verdict_moves={moved} worse={worse} "
              f"correct_lost={lost}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_base"] = diffs
    (outdir / f"fable_bench146b_{agent}_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 146b registered bench")
    ap.add_argument("--agent", default="loop146c",
                    choices=("loop146c", "loop146d"))
    ap.add_argument("--tags", default=None,
                    help="comma list subset of edit200,old_s2fresh_4hop,"
                    "new_121_4hop,bench132_4hop")
    args = ap.parse_args(argv)
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        return run_splits(args.agent, tags)
    if args.agent == "loop146d":
        return run_splits(args.agent,
                          ["edit200", "old_s2fresh_4hop", "new_121_4hop"])
    return run_splits(args.agent, ["edit200", "old_s2fresh_4hop",
                                   "new_121_4hop", "bench132_4hop"])


if __name__ == "__main__":
    sys.exit(main())
