#!/usr/bin/env python3
"""Experiment 190 -- V3 bench driver (Muse, descriptive + 0-new-wrong bar).

Runs bench121's 4 splits (new_121_4hop, old_s2fresh_4hop, edit200,
bench132_4hop) through loop190 exactly as scripts/fable_fix138g_suites.py
run_bench does (same scorer, read-only), and compares per-item verdicts
against the SEALED loop138g rows (read-only). Also scans every bench
question with the sealed 190 parser and reports the reversal rows
(descriptive, no bar): pre-seal scan found 0 matches.

Outputs into artifacts/fable-reverse190-20260922/ only.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix190_bench.py --bench-only all
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

import fable_fix190_reverse as R190  # noqa: E402 (parser, read-only)
import fable_loop190_agent as L190  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190-20260922"
ART138G = ROOT / "artifacts" / "fable-agent138g-20260922"


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    B.Loop121Daemon = L190.Loop190Daemon
    cfg = copy.deepcopy(L190.DEFAULT_CONFIG190)
    cfg["sleep_threshold"] = 100000
    tag = "loop190"
    DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop138g_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop138g_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134, "fable_bench121_loop138g_edit200_rows.jsonl"),
        ("bench132_4hop", DATA132,
         "fable_bench121_loop138g_bench132_4hop_rows.jsonl"),
    )
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop190"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        rev_rows = [it.get("id", "?") for it in items
                    if R190.parse_reverse190(
                        it.get("question", it.get("text", ""))) is not None]
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
        base_rows_l = [json.loads(line) for line in
                       (ART138G / sealed_name).read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_rows_l}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138g": s["verdict"],
                              tag: r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        rev_report = [{"id": r["id"], "verdict": r["verdict"],
                       "reply": str(r.get("reply", ""))[:120]}
                      for r in rows if r["id"] in set(rev_rows)]
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "moves_vs_138g": moves,
                                   "new_wrong_vs_138g": new_wrong,
                                   "reversal_rows_n": len(rev_rows),
                                   "reversal_rows": rev_report}
        print(f"{stag}: {tag} {cell} new_wrong={new_wrong} "
              f"moves={len(moves)} reversal_rows={len(rev_rows)}",
              flush=True)
        for m in moves:
            print(f"  MOVE {m}", flush=True)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 190 V3 bench")
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out = run_bench(args.bench_only)
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench121_summary_loop190.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"V3 bench done in {out['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
