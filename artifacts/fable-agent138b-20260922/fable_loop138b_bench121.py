#!/usr/bin/env python3
"""Exp 138b B2 driver -- bench121 new + old fresh + Fable-Edit + bench132.

Same shape as artifacts/fable-agent138-20260922/fable_loop138_bench121.py
(run_item/classify/summarize imported from scripts/fable_bench121_run.py;
only the daemon class under test is swapped). --agent loop138b runs the
stack; --agent loop138 runs the frozen base (bench132 baseline only, since
loop138 never ran bench132; the other three splits compare against the
SEALED loop138 rows read-only).

Compares per-item verdicts against loop138 rows. Outputs into
artifacts/fable-agent138b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py \\
    --agent loop138b
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop138_agent as L138  # noqa: E402 (frozen base, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-agent138b-20260922"
ART138 = ROOT / "artifacts" / "fable-agent138-20260922"
ART134 = ROOT / "artifacts" / "fable-loop134-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"

SPLITS_3 = (
    ("new_121_4hop", B.DATA_NEW, "fable_bench121_loop138_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD, "fable_bench121_loop138_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", DATA134, "fable_bench121_loop138_edit200_rows.jsonl"),
)
SPLIT_132 = ("bench132_4hop", DATA132, None)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138b B2 bench")
    ap.add_argument("--agent", default="loop138b",
                    choices=("loop138b", "loop138"))
    ap.add_argument("--only", default="all",
                    help="comma list of split tags or 'all'")
    args = ap.parse_args(argv)
    if args.agent == "loop138b":
        B.Loop121Daemon = L138b.Loop138bDaemon
        cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
        tag = "loop138b"
    else:
        B.Loop121Daemon = L138.Loop138Daemon
        cfg = copy.deepcopy(L138.DEFAULT_CONFIG138)
        tag = "loop138"
    cfg["sleep_threshold"] = 100000
    ART.mkdir(parents=True, exist_ok=True)
    want = args.only.split(",")
    splits = list(SPLITS_3) + [SPLIT_132]
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / f"scratch-bench121-{tag}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    rc = 0
    for stag, path, sealed_name in splits:
        items = load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / (f"fable_bench121_{tag}_{stag}_rows.jsonl")).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        cmp: dict = {"base": None, "new_wrong_vs_loop138": None, "moves": []}
        base_rows = None
        if args.agent == "loop138b":
            if sealed_name is not None:
                base_rows = load_rows(ART138 / sealed_name)
            else:
                base_path = ART / f"fable_bench121_loop138_{stag}_rows.jsonl"
                if base_path.exists():
                    base_rows = load_rows(base_path)
        if base_rows is not None:
            s_by_id = {r["id"]: r for r in base_rows}
            new_wrong = 0
            for r in rows:
                s = s_by_id.get(r["id"])
                if s is None:
                    continue
                if r["verdict"] != s["verdict"]:
                    cmp["moves"].append(
                        {"id": r["id"], "loop138": s["verdict"],
                         f"{tag}": r["verdict"],
                         "reply138": s.get("reply", "")[:160],
                         "reply138b": r.get("reply", "")[:160]})
                    if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                        new_wrong += 1
            cmp["base"] = {
                "correct": sum(1 for r in base_rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in base_rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in base_rows if r["verdict"] == "wrong")}
            cmp["new_wrong_vs_loop138"] = new_wrong
            if new_wrong != 0:
                rc = 1
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "compare": cmp}
        print(f"{stag}: {tag} {cell} base={cmp['base']} "
              f"new_wrong={cmp['new_wrong_vs_loop138']} "
              f"moves={len(cmp['moves'])}", flush=True)
        for m in cmp["moves"]:
            print(f"  MOVE {m['id']}: {m['loop138']} -> {m[tag]}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / f"fable_bench121_summary_{tag}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"B2 {summary['seconds']}s -> "
          f"{ART / ('fable_bench121_summary_' + tag + '.json')}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
