#!/usr/bin/env python3
"""Experiment 113d D3-121: new bench121 split, loop113c (before) vs loop113d.

Same protocol as scripts/fable_bench121_run.py with ONLY the daemon class
swapped (as the exp-113d brief allows): one item, one FRESH daemon
directory, English only (bytes in, outbox reply out). Teach sentences
verbatim, never rewritten; scorer v2 unchanged from exp 113.

This script NEVER prints item sentences or questions -- only aggregate
counts, verdict tallies, and (for failures) item ids with reply excerpts.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench113d_121.py --run
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

import fable_bench121_run as B121  # noqa: E402 (scorer+protocol, read-only)
from fable_loop113c_agent import (  # noqa: E402 (before arm)
    DEFAULT_CONFIG113C, Loop113cDaemon)
from fable_loop113d_agent import (  # noqa: E402 (after arm)
    DEFAULT_CONFIG113D, Loop113dDaemon)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113d-20260922"
DATA_NEW = ROOT / "data" / "open" / "bench121" / "fable_edit121_4hop.jsonl"


def run_item(item: dict, workroot: Path, cfg: dict, factory) -> dict:
    """One item, one FRESH daemon directory, English only."""
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = factory(str(ddir), cfg=dict(cfg))
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


def cmd_run(_args) -> int:
    cfg113c = copy.deepcopy(DEFAULT_CONFIG113C)
    cfg113d = copy.deepcopy(DEFAULT_CONFIG113D)
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch121"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "arms": {}}
    arms = (("loop113c", Loop113cDaemon, cfg113c),
            ("loop113d", Loop113dDaemon, cfg113d))
    items = [json.loads(l) for l in DATA_NEW.read_text(
        encoding="utf-8").splitlines() if l.strip()]
    for arm, factory, cfg in arms:
        rows = [run_item(it, workroot / arm, cfg, factory) for it in items]
        (ART / f"fable_bench113d_{arm}_bench121_4hop_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        out["arms"][arm] = {"n": len(rows), "table": B121.summarize(rows)}
        print(f"{arm} new_121_4hop: items={len(rows)}")
        for typ, cell in sorted(out["arms"][arm]["table"].items()):
            print(f"  {typ}: {cell}")
        for r in rows:
            if r["verdict"] == "wrong" or r["n_teach_reject"]:
                print(f"  FLAG {r['id']}: verdict={r['verdict']} "
                      f"rejects={r['n_teach_reject']} "
                      f"extracted={r['extracted'][:60]!r} "
                      f"stage={r['ears_stage']}")
    # Exact movement before -> after, by item id.
    b_rows = {json.loads(l)["id"]: json.loads(l) for l in (
        ART / "fable_bench113d_loop113c_bench121_4hop_rows.jsonl"
    ).read_text(encoding="utf-8").splitlines() if l.strip()}
    a_rows = {json.loads(l)["id"]: json.loads(l) for l in (
        ART / "fable_bench113d_loop113d_bench121_4hop_rows.jsonl"
    ).read_text(encoding="utf-8").splitlines() if l.strip()}
    moved = [{"id": k, "before": b_rows[k]["verdict"],
              "after": a_rows[k]["verdict"],
              "before_stage": b_rows[k]["ears_stage"],
              "after_stage": a_rows[k]["ears_stage"],
              "before_extracted": b_rows[k]["extracted"][:80],
              "after_extracted": a_rows[k]["extracted"][:80]}
             for k in sorted(b_rows) if b_rows[k]["verdict"] != a_rows[k][
                 "verdict"]]
    out["moved"] = moved
    print(f"MOVED {len(moved)} items:")
    for m in moved:
        print(f"  {m['id']}: {m['before']}->{m['after']} "
              f"{m['before_stage']}->{m['after_stage']} "
              f"{m['before_extracted']!r}->{m['after_extracted']!r}")
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench113d_121_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 113d bench121 before/after")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
