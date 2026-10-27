#!/usr/bin/env python3
"""Exp 129 F4 -- loop129b bench (scorer v2, unchanged from exp 113/121).

One item, one FRESH daemon directory, English only (bytes in, outbox reply
out). Teach sentences verbatim, never rewritten. Three splits:

  edit200      data/open/bench65/fable_edit_200.jsonl (200 items)
  old_s2fresh  data/open/bench103/fable_edit103_s2fresh_4hop.jsonl (200)
  new_121      data/open/bench121/fable_edit121_4hop.jsonl (200, blind)

Scorer, abstain list, and teach-accepted rule are imported unchanged from
scripts/fable_bench121_run.py (scorer v2). This script NEVER prints item
sentences or questions -- only aggregate counts plus failure item ids.

F4 bars (loop129b): edit200 200/200; old_s2fresh >= 157 correct and
0 wrong; new_121 >= 136 correct and <= 1 wrong.

--agent loop121 selects the loop121 base arm (pre-seal calibration only;
the registered F4 run is --agent loop129b).

Writes: artifacts/fable-fix129-20260922/fable_bench129b_*_rows.jsonl +
fable_bench129b_summary.json.
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop129b_bench.py --run --agent loop129b
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
import fable_fix129_common as C129  # noqa: E402 (this experiment)
import fable_loop121_agent as L121  # noqa: E402 (calibration arm, read-only)
import fable_loop129b_agent as L129b  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = C129.ART129
DATA_EDIT200 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_OLD = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"
DATA_NEW = ROOT / "data" / "open" / "bench121" / "fable_edit121_4hop.jsonl"


def run_item(item: dict, workroot: Path, daemon_cls, cfg: dict) -> dict:
    """One item, one FRESH daemon directory, English only."""
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = daemon_cls(str(ddir), cfg=dict(cfg))
    teach_replies: list[str] = []
    n_reject = 0
    n = 0
    for t in item["taught"]:
        n += 1
        name = f"t{n:03d}.txt"
        (ddir / "inbox" / name).write_text(str(t["sentence_en"]) + "\n",
                                           encoding="utf-8")
        daemon.process_file(ddir / "inbox" / name)
        reply = (ddir / "outbox" / name).read_text(encoding="utf-8").strip()
        teach_replies.append(reply)
        n_reject += 0 if B121.teach_accepted(reply) else 1
    n += 1
    qname = f"t{n:03d}.txt"
    (ddir / "inbox" / qname).write_text(str(item["question"]) + "\n",
                                        encoding="utf-8")
    daemon.process_file(ddir / "inbox" / qname)
    reply = (ddir / "outbox" / qname).read_text(encoding="utf-8").strip()
    golds = [str(g) for g in list(item.get("gold", []))
             + list(item.get("gold_aliases", []))]
    verdict, exact, contains = B121.classify_v2(reply, golds)
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:
        stage = ""
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "expected": str(item.get("expected", "?")),
            "verdict": verdict,
            "exact": bool(exact), "contains_gold": bool(contains),
            "extracted": B121.extract_answer(reply), "ears_stage": stage,
            "n_teach": len(teach_replies), "n_teach_reject": n_reject,
            "teach_replies": teach_replies, "reply": reply}


def summarize(rows: list[dict]) -> dict:
    table: dict[str, dict] = {}
    for r in rows:
        cell = table.setdefault(r["type"], {"n": 0, "correct": 0,
                                            "abstain": 0, "wrong": 0,
                                            "contains_gold": 0,
                                            "teach_reject_items": 0,
                                            "teach_rejects": 0})
        cell["n"] += 1
        cell[r["verdict"]] += 1
        cell["contains_gold"] += int(r["contains_gold"])
        if r["n_teach_reject"]:
            cell["teach_reject_items"] += 1
            cell["teach_rejects"] += r["n_teach_reject"]
    return table


def totals(table: dict) -> dict:
    out = {"n": 0, "correct": 0, "abstain": 0, "wrong": 0,
           "contains_gold": 0, "teach_reject_items": 0}
    for cell in table.values():
        for k in out:
            out[k] += cell[k]
    return out


def cmd_run(agent: str) -> int:
    if agent == "loop129b":
        daemon_cls, cfg = L129b.Loop129bDaemon, copy.deepcopy(
            L129b.DEFAULT_CONFIG129B)
    elif agent == "loop121":
        daemon_cls, cfg = L121.Loop121Daemon, copy.deepcopy(
            L121.DEFAULT_CONFIG121)
    else:
        print(f"unknown --agent {agent!r}")
        return 2
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / f"scratch-bench-{agent}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": agent, "arms": {}}
    for tag, path in (("edit200", DATA_EDIT200),
                      ("old_s2fresh_4hop", DATA_OLD),
                      ("new_121_4hop", DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [run_item(it, workroot / tag, daemon_cls, cfg)
                for it in items]
        (ART / f"fable_bench129b_{agent}_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = summarize(rows)
        out["arms"][agent] = out["arms"].get(agent, {})
        out["arms"][agent][tag] = {"n": len(rows), "table": table,
                                   "totals": totals(table)}
        print(f"{agent} {tag}: {totals(table)}")
        for r in rows:
            if r["verdict"] == "wrong" or r["n_teach_reject"]:
                print(f"  FLAG {r['id']}: verdict={r['verdict']} "
                      f"rejects={r['n_teach_reject']} "
                      f"extracted={r['extracted'][:60]!r} "
                      f"stage={r['ears_stage']}")
    out["seconds"] = round(time.time() - t0, 1)
    (ART / f"fable_bench129b_{agent}_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 129b registered bench")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--agent", default="loop129b",
                    choices=("loop129b", "loop121"))
    args = ap.parse_args()
    if args.run:
        return cmd_run(args.agent)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
