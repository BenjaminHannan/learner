#!/usr/bin/env python3
"""Exp 138f G1 driver -- bench121 new + old + Fable-Edit + bench132 on loop138f.

Same shape as scripts/fable_loop138d_bench121.py (run_item/classify/
summarize from scripts/fable_bench121_run.py; only the daemon class under
test is Loop138fDaemon); compares per-item verdicts against the SEALED
loop138b rows (read-only). Bar: 0 new wrong vs loop138b; every move
predicted in PASSMARKS.md, every extra move listed. Outputs into
artifacts/fable-agent138f-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138f_bench.py
"""

from __future__ import annotations

import argparse
import copy
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
import fable_loop138f_agent as L138f  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-agent138f-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART138 = ROOT / "artifacts" / "fable-agent138-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"

SPLITS = (
    ("new_121_4hop", B.DATA_NEW,
     "fable_bench121_loop138b_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD,
     "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", DATA134, "fable_bench121_loop138b_edit200_rows.jsonl"),
    ("bench132_4hop", DATA132,
     "fable_bench121_loop138b_bench132_4hop_rows.jsonl"),
)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138f G1 bench")
    ap.add_argument("--only", default="all",
                    help="comma list of split tags or 'all'")
    args = ap.parse_args(argv)
    B.Loop121Daemon = L138f.Loop138fDaemon
    cfg = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
    cfg["sleep_threshold"] = 100000
    tag = "loop138f"
    ART.mkdir(parents=True, exist_ok=True)
    want = args.only.split(",")
    splits = list(SPLITS)
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop138f"
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
        (ART / f"fable_bench121_{tag}_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        cmp: dict = {"base": None, "new_wrong_vs_loop138b": None,
                     "moves": []}
        base_rows = load_rows(ART138B / sealed_name)
        s_by_id = {r["id"]: r for r in base_rows}
        new_wrong = 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                cmp["moves"].append(
                    {"id": r["id"], "loop138b": s["verdict"],
                     tag: r["verdict"],
                     "reply138b": s.get("reply", "")[:160],
                     "reply138f": r.get("reply", "")[:160]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        cmp["base"] = {
            "correct": sum(1 for r in base_rows if r["verdict"] == "correct"),
            "abstain": sum(1 for r in base_rows if r["verdict"] == "abstain"),
            "wrong": sum(1 for r in base_rows if r["verdict"] == "wrong")}
        cmp["new_wrong_vs_loop138b"] = new_wrong
        if new_wrong != 0:
            rc = 1
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "compare": cmp}
        print(f"{stag}: {tag} {cell} base={cmp['base']} "
              f"new_wrong={cmp['new_wrong_vs_loop138b']} "
              f"moves={len(cmp['moves'])}", flush=True)
        for m in cmp["moves"]:
            print(f"  MOVE {m['id']}: {m['loop138b']} -> {m[tag]}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / f"fable_bench121_summary_{tag}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G1 {summary['seconds']}s -> "
          f"{ART / ('fable_bench121_summary_' + tag + '.json')}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
