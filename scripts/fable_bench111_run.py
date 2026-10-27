#!/usr/bin/env python3
"""Experiment 111 — END-TO-END benchmark of the joined-up Loop102 agent.

Every item runs through the REAL doorway only: English teach sentences are
written as bytes into a FRESH daemon mailbox (inbox/*.txt), the English
question follows as the last file, and the scored text is the daemon's
outbox reply file. No direct notebook calls, no structured frames.

Scoring uses the exp-66 scorer rules VERBATIM (imported read-only from
scripts/fable_bench66_baselines.py): exact normalised match = correct;
abstain-marker with no gold contained = abstain; anything else = wrong.
A diagnostic contains_gold column is reported alongside (NOT a mark).

Teach-turn doorway behaviour is recorded honestly: a teach reply counts as
ACCEPTED iff it starts with "Saved:" or is "I already have that." (the
bench files repeat each original sentence verbatim before its edit, so one
duplicate-ack per repeated sentence is expected). Anything else (clarify,
CONFLICT question, refusal) counts as REJECTED and is reported with counts
and verbatim examples. Sentences are NEVER rewritten.

Splits:
  A: data/open/bench65/fable_edit_200.jsonl (150 answer + 50 abstain)
  B: data/open/bench103/fable_edit103_s2fresh_4hop.jsonl (200 fresh answers)

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench111_run.py --run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_bench66_baselines import classify  # noqa: E402 (exp-66 scorer, verbatim)
from fable_loop102_agent import Loop102Daemon  # noqa: E402 (real doorway)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench111-20260921"
DATA_A = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_B = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"
CONFIG = ROOT / "artifacts" / "fable-loop102-20260921" / "loop102-config.json"

DUP_ACK = "I already have that."


def teach_accepted(reply: str) -> bool:
    r = (reply or "").strip()
    return r.startswith("Saved:") or r == DUP_ACK


def run_item(item: dict, workroot: Path, cfg: dict) -> dict:
    """One item, one FRESH daemon directory, English only."""
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = Loop102Daemon(str(ddir), cfg=dict(cfg))
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
        n_reject += 0 if teach_accepted(reply) else 1
    n += 1
    qname = f"t{n:03d}.txt"
    (ddir / "inbox" / qname).write_text(str(item["question"]) + "\n",
                                        encoding="utf-8")
    daemon.process_file(ddir / "inbox" / qname)
    reply = (ddir / "outbox" / qname).read_text(encoding="utf-8").strip()
    golds = [str(g) for g in list(item.get("gold", []))
             + list(item.get("gold_aliases", []))]
    verdict, exact, contains = classify(reply, golds)
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "expected": str(item.get("expected", "?")),
            "question": str(item.get("question", "")),
            "golds": golds, "reply": reply, "verdict": verdict,
            "exact": bool(exact), "contains_gold": bool(contains),
            "n_teach": len(teach_replies), "n_teach_reject": n_reject,
            "teach_replies": teach_replies}


def summarize(rows: list[dict]) -> dict:
    table: dict[str, dict] = {}
    for r in rows:
        cell = table.setdefault(r["type"], {"n": 0, "correct": 0, "abstain": 0,
                                            "wrong": 0, "contains_gold": 0,
                                            "teach_reject_items": 0,
                                            "teach_rejects": 0})
        cell["n"] += 1
        cell[r["verdict"]] += 1
        cell["contains_gold"] += int(r["contains_gold"])
        if r["n_teach_reject"]:
            cell["teach_reject_items"] += 1
            cell["teach_rejects"] += r["n_teach_reject"]
    return table


def cmd_run(_args) -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch111"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "splits": {}}
    for tag, path in (("fable_edit_200", DATA_A), ("s2fresh_4hop", DATA_B)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [run_item(it, workroot / tag, cfg) for it in items]
        (ART / f"fable_bench111_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        out["splits"][tag] = {"n": len(rows), "table": summarize(rows)}
        print(f"{tag}: items={len(rows)}")
        for typ, cell in sorted(out["splits"][tag]["table"].items()):
            print(f"  {typ}: {cell}")
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench111_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 111 end-to-end doorway bench")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
