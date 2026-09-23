#!/usr/bin/env python3
"""Experiment 154e -- regression runner (bench G1 + marks G2, registered).

Same pattern as scripts/fable_fix154c_regress.py with the daemon class
swapped to Loop154eDaemon. Compares against the FROZEN loop154c rows in
artifacts/fable-multival154c-20260922/ (bench rows) and marks154c
(marks123 per-case). Outputs under artifacts/fable-lang154e-20260922/.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop154e_agent as L154e  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-lang154e-20260922"
ART154C = ROOT / "artifacts" / "fable-multival154c-20260922"
AGENT = str(SCRIPTS / "fable_loop154e_agent.py")
CONFIG = str(ART / "loop154e-config.json")

SPLITS_3 = (
    ("new_121_4hop", B.DATA_NEW,
     "fable_bench121_loop154c_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD,
     "fable_bench121_loop154c_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl",
     "fable_bench121_loop154c_edit200_rows.jsonl"),
)
SPLIT_132 = (("bench132_4hop",
              ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl",
              "fable_bench121_loop154c_bench132_4hop_rows.jsonl"))


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def run_bench(only: str, outdir: Path) -> dict:
    B.Loop121Daemon = L154e.Loop154eDaemon
    cfg = json.loads(Path(CONFIG).read_text(encoding="utf-8"))
    cfg["sleep_threshold"] = 100000
    want = only.split(",")
    splits = list(SPLITS_3) + [SPLIT_132]
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = outdir / "scratch-bench121-loop154e"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "agent": "loop154e", "splits": {}}
    diffs: list[dict] = []
    for stag, path, sealed_name in splits:
        items = load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (outdir / f"fable_bench121_loop154e_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        frozen = {r.get("id", i): r for i, r in
                  enumerate(load_rows(ART154C / sealed_name))}
        new_wrong, moves = 0, []
        for i, row in enumerate(rows):
            old = frozen.get(row.get("id", i), {})
            if row.get("verdict") != old.get("verdict") or \
                    row.get("reply", "") != old.get("reply", ""):
                moves.append({"id": row.get("id", i),
                              "was": old.get("verdict"),
                              "now": row.get("verdict"),
                              "was_reply": (old.get("reply", "") or "")[:160],
                              "now_reply": (row.get("reply", "") or "")[:160]})
            if row.get("verdict") == "wrong" and old.get("verdict") != "wrong":
                new_wrong += 1
        summary["splits"][stag] = {"n": len(rows), "new_wrong": new_wrong,
                                   "moves": len(moves)}
        diffs.extend([dict(d, split=stag) for d in moves])
    summary["seconds"] = round(time.time() - t0, 1)
    summary["new_wrong_total"] = sum(
        v["new_wrong"] for v in summary["splits"].values())
    (outdir / "bench154e_diff.json").write_text(
        json.dumps({"summary": summary, "moves": diffs}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    return summary


def run_marks(suites: str, outdir: Path, workers: int) -> dict:
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    cmd = [sys.executable, "-B", str(SCRIPTS / "fable_marks123_all.py"),
           "--agent", AGENT, "--config", CONFIG,
           "--out", str(outdir / "marks154e"),
           "--suites", suites, "--workers", str(workers)]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return {"rc": proc.returncode, "seconds": round(time.time() - t0, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 154e regression runner")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--marks", default=None,
                    help="comma suites for marks123 (e.g. p2,rt110,rt81)")
    ap.add_argument("--only", default="all")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rc = 0
    if args.bench:
        summary = run_bench(args.only, outdir)
        print(json.dumps({"bench154e": summary}, indent=1))
        rc = rc or int(summary["new_wrong_total"] > 0)
    if args.marks:
        rep = run_marks(args.marks, outdir, args.workers)
        print(json.dumps({"marks154e": rep}, indent=1))
        rc = rc or int(rep["rc"] != 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
