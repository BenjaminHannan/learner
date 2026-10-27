#!/usr/bin/env python3
"""Exp 170 G1 driver -- bench121 new + old + Fable-Edit + bench132 on loop170.

Mirrors scripts/fable_loop138d_bench121.py (run_item/classify/summarize from
scripts/fable_bench121_run.py BY IMPORT; only the daemon class swapped to
Loop170Daemon). Compares per-item against the SEALED loop138d rows
(read-only) and counts new-wrong vs loop138b. Bar: 0 moves vs loop138d, 0
new wrong vs loop138b. Outputs into artifacts/fable-speed170-20260922/.
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
import fable_loop170_agent as L170  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-speed170-20260922"
ART138D = ROOT / "artifacts" / "fable-agent138d-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"

SPLITS = (
    ("new_121_4hop", B.DATA_NEW, "fable_bench121_loop138d_new_121_4hop_rows.jsonl",
     "fable_bench121_loop138b_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD, "fable_bench121_loop138d_old_s2fresh_4hop_rows.jsonl",
     "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", DATA134, "fable_bench121_loop138d_edit200_rows.jsonl",
     "fable_bench121_loop138b_edit200_rows.jsonl"),
    ("bench132_4hop", DATA132, "fable_bench121_loop138d_bench132_4hop_rows.jsonl",
     "fable_bench121_loop138b_bench132_4hop_rows.jsonl"),
)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 170 G1 bench")
    ap.add_argument("--only", default="all")
    args = ap.parse_args(argv)
    B.Loop121Daemon = L170.Loop170Daemon
    cfg = copy.deepcopy(L170.DEFAULT_CONFIG170)
    cfg["sleep_threshold"] = 100000
    tag = "loop170"
    ART.mkdir(parents=True, exist_ok=True)
    want = args.only.split(",")
    splits = list(SPLITS)
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop170"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    rc = 0
    for stag, path, sealed138d, sealed138b in splits:
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
        d_rows = load_rows(ART138D / sealed138d)
        d_by_id = {r["id"]: r for r in d_rows}
        moves138d = []
        for r in rows:
            s = d_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"] or r.get("reply", "") != s.get(
                    "reply", ""):
                moves138d.append({"id": r["id"],
                                  "loop138d": s["verdict"],
                                  tag: r["verdict"]})
        b_rows = load_rows(ART138B / sealed138b)
        b_by_id = {r["id"]: r for r in b_rows}
        new_wrong = 0
        for r in rows:
            s = b_by_id.get(r["id"])
            if s is None:
                continue
            if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                new_wrong += 1
        if moves138d or new_wrong != 0:
            rc = 1
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "moves_vs_138d": moves138d,
                                   "new_wrong_vs_loop138b": new_wrong}
        print(f"{stag}: {tag} {cell} moves138d={len(moves138d)} "
              f"new_wrong={new_wrong}", flush=True)
        for m in moves138d:
            print(f"  MOVE {m['id']}: {m['loop138d']} -> {m[tag]}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / f"fable_bench121_summary_{tag}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
