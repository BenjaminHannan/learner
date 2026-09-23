#!/usr/bin/env python3
"""Exp 161 S5a driver -- bench121 new + old fresh + Fable-Edit on loop161.

Mirrors artifacts/fable-agent138-20260922/fable_loop138_bench121.py op for
op (imports run_item/classify/summarize from scripts/fable_bench121_run.py;
only the daemon class under test is swapped to Loop161Daemon) and compares
per-item verdicts AND replies against the SEALED loop138 rows (read-only,
never overwritten). Additionally records the self-path (card) routing per
item by replaying the item in-process, so every allowed move is evidenced
as a self-path turn. Outputs into artifacts/fable-selfcard161-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed + ledger P161.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop161_bench.py
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop161_agent as L161  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-selfcard161-20260922"
ART138 = ROOT / "artifacts" / "fable-agent138-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"

SPLITS = (
    ("new_121_4hop", B.DATA_NEW,
     "fable_bench121_loop138_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD,
     "fable_bench121_loop138_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", DATA134, "fable_bench121_loop138_edit200_rows.jsonl"),
)


def routed_probe(tag: str, item: dict) -> dict | None:
    """Replay one item in-process and report the self-path, if any."""
    loop = L161.build_agent161(
        {"state_dir": str(ART / "scratch-b161-route" / tag
                          / re.sub(r"[^A-Za-z0-9_-]+", "_", item["id"])),
         "sleep_threshold": 100000})
    for t in item["taught"]:
        loop.turn(str(t["sentence_en"]))
    said = loop.turn(str(item["question"]))
    if loop.last_routed is None:
        return None
    return {"intent": loop.last_routed["intent"],
            "answer": " ".join(said)}


def main() -> int:
    B.Loop121Daemon = L161.Loop161Daemon
    cfg = copy.deepcopy(L161.DEFAULT_CONFIG161)
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch-bench121-161"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    if (ART / "scratch-b161-route").exists():
        shutil.rmtree(ART / "scratch-b161-route")
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "splits": {}}
    for tag, path, sealed_name in SPLITS:
        items = [json.loads(line) for line in path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        rows = [B.run_item(it, workroot / tag, copy.deepcopy(cfg))
                for it in items]
        (ART / (f"fable_bench121_loop161_{tag}_rows.jsonl")).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        cmp = {"sealed_loop138": None, "new_wrong_vs_138": None,
               "moves": []}
        sealed = [json.loads(line) for line in
                  (ART138 / sealed_name).read_text(
                      encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in sealed}
        new_wrong = 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if (r["verdict"] != s["verdict"]
                    or r.get("reply", "") != s.get("reply", "")):
                info = {"id": r["id"], "loop138": s["verdict"],
                        "loop161": r["verdict"],
                        "reply138": s.get("reply", "")[:200],
                        "reply161": r.get("reply", "")[:200],
                        "self_path": None}
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
                cmp["moves"].append(info)
        cmp["sealed_loop138"] = {
            "correct": sum(1 for r in sealed if r["verdict"] == "correct"),
            "abstain": sum(1 for r in sealed if r["verdict"] == "abstain"),
            "wrong": sum(1 for r in sealed if r["verdict"] == "wrong")}
        cmp["new_wrong_vs_138"] = new_wrong
        for m in cmp["moves"]:
            item = next(it for it in items if it["id"] == m["id"])
            m["self_path"] = routed_probe(tag, item)
        summary["splits"][tag] = {"loop161": cell, "by_type": table,
                                  "compare": cmp}
        print(f"{tag}: loop161 {cell} sealed138={cmp['sealed_loop138']} "
              f"new_wrong={cmp['new_wrong_vs_138']} "
              f"moves={len(cmp['moves'])}", flush=True)
        for m in cmp["moves"]:
            print(f"  MOVE {m['id']}: {m['loop138']} -> {m['loop161']} "
                  f"self_path={m['self_path']}", flush=True)
    shutil.rmtree(ART / "scratch-b161-route", ignore_errors=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench121_summary_loop161.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"S5a {summary['seconds']}s -> "
          f"{ART / 'fable_bench121_summary_loop161.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
