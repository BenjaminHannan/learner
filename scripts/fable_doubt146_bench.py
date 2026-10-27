#!/usr/bin/env python3
"""Experiment 146 bench -- per-item verdicts on the doubt loops (Muse).

D1: loop146b (doubt on top of loop139) over edit200 + old_s2fresh_4hop +
    new_121_4hop, diffed per-item vs the sealed loop139 rows
    (artifacts/fable-fix139-20260922/, read-only).
D2: loop146 (doubt on loop129b) over edit200 + old_s2fresh_4hop +
    new_121_4hop + the bench132 split, diffed per-item vs the sealed
    loop129b rows (artifacts/fable-fix129-20260922/, read-only) and, for
    bench132, vs the sealed loop121 rows
    (artifacts/fable-bench132-20260922/, read-only).

One item, one FRESH daemon directory, English only (bytes in, outbox reply
out). Teach sentences verbatim, never rewritten. Never prints item
sentences or questions -- only aggregate counts plus failure item ids.
Outputs go into artifacts/fable-doubt146-20260922/ only.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146_bench.py --agent loop146b   # D1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146_bench.py --agent loop146    # D2
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

import fable_bench121_run as B121  # noqa: E402 (scorer v2, read-only)
import fable_loop129b_agent as L129b  # noqa: E402 (evidence arm, read-only)
import fable_loop129b_bench as B129  # noqa: E402 (run_item/scorer, read-only)
import fable_loop146_agent as L146  # noqa: E402 (this experiment)
import fable_loop146b_agent as L146B  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART146 = ROOT / "artifacts" / "fable-doubt146-20260922"
ART129 = ROOT / "artifacts" / "fable-fix129-20260922"
ART139 = ROOT / "artifacts" / "fable-fix139-20260922"
ART132 = ROOT / "artifacts" / "fable-bench132-20260922"

DATA_EDIT200 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_OLD = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"
DATA_NEW = ROOT / "data" / "open" / "bench121" / "fable_edit121_4hop.jsonl"
DATA_132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"


def _daemon_for(agent: str):
    if agent == "loop146":
        return L146.Loop146Daemon, copy.deepcopy(L146.DEFAULT_CONFIG146)
    if agent == "loop146b":
        return L146B.Loop146bDaemon, copy.deepcopy(L146B.DEFAULT_CONFIG146B)
    if agent == "loop129b":
        # Pre-seal evidence arm only (base loop, never a registered run).
        return L129b.Loop129bDaemon, copy.deepcopy(L129b.DEFAULT_CONFIG129B)
    raise ValueError(f"unknown --agent {agent!r}")


def _sealed_rows139(tag: str) -> dict:
    name = {"edit200": "fable_bench139_loop139_edit200_rows.jsonl",
            "old_s2fresh_4hop":
                "fable_bench139_loop139_old_s2fresh_4hop_rows.jsonl",
            "new_121_4hop":
                "fable_bench139_loop139_new_121_4hop_rows.jsonl"}[tag]
    return {r["id"]: r for r in
            (json.loads(l) for l in
             (ART139 / name).read_text(encoding="utf-8").splitlines()
             if l.strip())}


def _sealed_rows129(tag: str) -> dict:
    name = {"edit200": "fable_bench129b_loop129b_edit200_rows.jsonl",
            "old_s2fresh_4hop":
                "fable_bench129b_loop129b_old_s2fresh_4hop_rows.jsonl",
            "new_121_4hop":
                "fable_bench129b_loop129b_new_121_4hop_rows.jsonl"}[tag]
    return {r["id"]: r for r in
            (json.loads(l) for l in
             (ART129 / name).read_text(encoding="utf-8").splitlines()
             if l.strip())}


def _sealed_rows132_loop121() -> dict:
    cands = sorted(ART132.glob("*loop121*rows*.jsonl"))
    if not cands:
        cands = sorted(ART132.glob("*rows*.jsonl"))
    path = cands[0]
    rows = [json.loads(l) for l in path.read_text(
        encoding="utf-8").splitlines() if l.strip()]
    return {r["id"]: r for r in rows}, path.name


def run_splits(agent: str, tags: list[str], outdir: Path | None = None) -> int:
    daemon_cls, cfg = _daemon_for(agent)
    outdir = Path(outdir) if outdir is not None else ART146
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
        (outdir / f"fable_bench146_{agent}_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129.summarize(rows)
        out["arms"][tag] = {"n": len(rows), "table": table,
                            "totals": B129.totals(table)}
        print(f"{agent} {tag}: {B129.totals(table)}", flush=True)
        if agent == "loop146b" and tag in (
                "edit200", "old_s2fresh_4hop", "new_121_4hop"):
            base = _sealed_rows139(tag)
        elif agent == "loop146" and tag in (
                "edit200", "old_s2fresh_4hop", "new_121_4hop"):
            base = _sealed_rows129(tag)
        elif agent == "loop146" and tag == "bench132_4hop":
            base, used = _sealed_rows132_loop121()
            print(f"  bench132 comparator: sealed {used}", flush=True)
        else:
            base = {}
        moved = [r["id"] for r in rows
                 if base.get(r["id"], {}).get("verdict") != r["verdict"]]
        worse = [i for i in moved
                 if _is_worse(base.get(i, {}).get("verdict"),
                              [r for r in rows if r["id"] == i][0]
                              ["verdict"])]
        diffs[tag] = {"verdict_moves": moved, "worse": worse}
        print(f"  vs base: verdict_moves={moved} worse={worse}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["diff_vs_base"] = diffs
    (outdir / f"fable_bench146_{agent}_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def _is_worse(before: str | None, after: str | None) -> bool:
    rank = {"correct": 2, "abstain": 1, "wrong": 0}
    return rank.get(after, -1) < rank.get(before, -1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 146 registered bench")
    ap.add_argument("--agent", default="loop146",
                    choices=("loop146", "loop146b", "loop129b"))
    ap.add_argument("--outdir", default=None,
                    help="output dir (default: artifacts/fable-doubt146-20260922)")
    ap.add_argument("--tags", default=None,
                    help="comma list subset of edit200,old_s2fresh_4hop,new_121_4hop,bench132_4hop")
    args = ap.parse_args(argv)
    outdir = Path(args.outdir) if args.outdir else None
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        return run_splits(args.agent, tags, outdir=outdir)
    if args.agent == "loop146b":
        return run_splits(args.agent,
                          ["edit200", "old_s2fresh_4hop", "new_121_4hop"],
                          outdir=outdir)
    if args.agent == "loop129b":
        return run_splits(args.agent, ["bench132_4hop"], outdir=outdir)
    return run_splits(args.agent, ["edit200", "old_s2fresh_4hop",
                                   "new_121_4hop", "bench132_4hop"],
                      outdir=outdir)


if __name__ == "__main__":
    sys.exit(main())
