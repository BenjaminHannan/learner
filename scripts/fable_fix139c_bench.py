#!/usr/bin/env python3
"""Experiment 139c G1 -- bench121 through loop139c vs SEALED loop138b rows.

Reuses artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py BY
IMPORT (SPLITS_3/SPLIT_132/load_rows) and scripts/fable_bench121_run.py
(run_item/scorer, read-only); only the daemon under test is swapped to
Loop139cDaemon. Compares per-item verdicts against the SEALED
fable_bench121_loop138b_*_rows.jsonl files. Bar: 0 new wrong, every move
predicted in writing before the run (PASSMARKS.md predicts 0 moves).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix139c_bench.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop139c_agent as L139c  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-tailwords139c-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def load_bench138b():
    spec = importlib.util.spec_from_file_location(
        "fable_loop138b_bench121",
        ART138B / "fable_loop138b_bench121.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 139c G1 bench")
    ap.add_argument("--only", default="all")
    args = ap.parse_args(argv)
    bench138b = load_bench138b()  # SPLITS_3/SPLIT_132/load_rows, read-only
    B.Loop121Daemon = L139c.Loop139cDaemon
    cfg = copy.deepcopy(L139c.DEFAULT_CONFIG139C)
    cfg["sleep_threshold"] = 100000
    tag = "loop139c"
    ART.mkdir(parents=True, exist_ok=True)
    want = args.only.split(",")
    splits = list(bench138b.SPLITS_3) + [bench138b.SPLIT_132]
    sealed_name = {"new_121_4hop": "fable_bench121_loop138b_new_121_4hop_rows.jsonl",
                   "old_s2fresh_4hop": "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
                   "edit200": "fable_bench121_loop138b_edit200_rows.jsonl",
                   "bench132_4hop": "fable_bench121_loop138b_bench132_4hop_rows.jsonl"}
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop139c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    rc = 0
    for stag, path, _sealed138 in splits:
        items = load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_{tag}_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        cmp: dict = {"base": "sealed loop138b rows", "new_wrong": None,
                     "moves": []}
        base_rows = load_rows(ART138B / sealed_name[stag])
        s_by_id = {r["id"]: r for r in base_rows}
        new_wrong = 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"] or \
                    r.get("reply", "") != s.get("reply", ""):
                cmp["moves"].append(
                    {"id": r["id"], "loop138b": s["verdict"],
                     "loop139c": r["verdict"],
                     "reply138b": s.get("reply", "")[:160],
                     "reply139c": r.get("reply", "")[:160]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        cmp["base_counts"] = {
            "correct": sum(1 for r in base_rows if r["verdict"] == "correct"),
            "abstain": sum(1 for r in base_rows if r["verdict"] == "abstain"),
            "wrong": sum(1 for r in base_rows if r["verdict"] == "wrong")}
        cmp["new_wrong"] = new_wrong
        if new_wrong != 0:
            rc = 1
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "compare": cmp}
        print(f"{stag}: {tag} {cell} base={cmp['base_counts']} "
              f"new_wrong={new_wrong} moves={len(cmp['moves'])}", flush=True)
        for m in cmp["moves"]:
            print(f"  MOVE {m['id']}: {m['loop138b']} -> {m['loop139c']} "
                  f"| {m['reply138b']!r} -> {m['reply139c']!r}", flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / f"fable_bench121_summary_{tag}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G1 {summary['seconds']}s -> "
          f"{ART / ('fable_bench121_summary_' + tag + '.json')}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
