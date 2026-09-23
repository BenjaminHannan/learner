#!/usr/bin/env python3
"""Experiment 172b -- bench driver under protocol v3 ("confirming user").

Reuses by import (read-only, nothing edited):
  * scripts/fable_bench121_run.py (DATA paths, classify_v2 scorer,
    extract_answer, teach_accepted) -- the 154c bench121 driver pattern.
  * scripts/fable_loop154c_agent.py / scripts/fable_loop172_agent.py
    (agents under test; only the daemon class is swapped).

Protocol v3: teach turns verbatim, in order. After any bench edit
(taught-sentence) turn whose reply is the agent's change-prompt naming
that edit's new value (CONFLICT template "Do you want me to change it
to <new>?" with <new> named in the taught sentence), the driver sends
exactly one extra turn "yes" and continues. No other extra turns; the
question turns are unchanged. Confirms counted per split.

Row schema = B.run_item's keys + confirms/yes_replies/teach_first_replies
so per-item verdicts compare directly with the frozen rows.

Modes:
  --arm loop154c --proto v3 | --arm loop172 --proto v3 | --arm loop172 --proto old
Outputs (under artifacts/fable-copula172b-20260922/):
  fable_bench172b_<arm>_<proto>_<split>_rows.jsonl + bench172b_<arm>_<proto>_summary.json
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

import fable_bench121_run as B  # noqa: E402 (scorer + paths, read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (read-only)
import fable_loop172_agent as L172  # noqa: E402 (read-only)

ART = ROOT / "artifacts" / "fable-copula172b-20260922"
CONFIG = ART / "loop172b-config.json"

NEEDLE = "Do you want me to change it to"

SPLITS = (
    ("new_121_4hop", B.DATA_NEW),
    ("old_s2fresh_4hop", B.DATA_OLD),
    ("edit200", ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"),
    ("bench132_4hop",
     ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"),
)

DAEMONS = {"loop154c": L154c.Loop154cDaemon, "loop172": L172.Loop172Daemon}


def confirm_value(reply: str) -> str:
    """The <new> value named by a change-prompt, else ''."""
    if NEEDLE not in (reply or ""):
        return ""
    tail = (reply or "").split(NEEDLE, 1)[1].strip()
    return tail.rstrip("?.!. ").strip()


def run_item_v3(item: dict, workroot: Path, cfg: dict,
                daemon_cls, proto: str) -> dict:
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = daemon_cls(str(ddir), cfg=dict(cfg), idle_seconds=30.0)
    teach_replies: list[str] = []
    yes_replies: list[str] = []
    confirms = 0
    n_reject = 0
    n = 0
    for t in item["taught"]:
        n += 1
        sent = str(t["sentence_en"])
        name = f"t{n:03d}.txt"
        (ddir / "inbox" / name).write_text(sent + "\n", encoding="utf-8")
        daemon.process_file(ddir / "inbox" / name)
        reply = (ddir / "outbox" / name).read_text(encoding="utf-8").strip()
        teach_replies.append(reply)
        n_reject += 0 if B.teach_accepted(reply) else 1
        if proto == "v3":
            new_val = confirm_value(reply)
            # The prompt after an edit turn names that edit's new value
            # (pending is always clean: every earlier prompt was just
            # confirmed). Confirm only when the named value occurs in
            # the taught sentence -- otherwise no extra turn.
            if new_val and new_val in sent:
                n += 1
                yname = f"t{n:03d}.txt"
                (ddir / "inbox" / yname).write_text("yes\n",
                                                   encoding="utf-8")
                daemon.process_file(ddir / "inbox" / yname)
                yreply = (ddir / "outbox" / yname).read_text(
                    encoding="utf-8").strip()
                yes_replies.append(yreply)
                confirms += 1
    n += 1
    qname = f"t{n:03d}.txt"
    (ddir / "inbox" / qname).write_text(str(item["question"]) + "\n",
                                        encoding="utf-8")
    daemon.process_file(ddir / "inbox" / qname)
    reply = (ddir / "outbox" / qname).read_text(encoding="utf-8").strip()
    golds = [str(g) for g in list(item.get("gold", []))
             + list(item.get("gold_aliases", []))]
    verdict, exact, contains = B.classify_v2(reply, golds)
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:
        stage = ""
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "expected": str(item.get("expected", "?")),
            "verdict": verdict,
            "exact": bool(exact), "contains_gold": bool(contains),
            "extracted": B.extract_answer(reply), "ears_stage": stage,
            "n_teach": len(teach_replies), "n_teach_reject": n_reject,
            "teach_replies": teach_replies, "reply": reply,
            "confirms": confirms, "yes_replies": yes_replies}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 172b bench-v3 driver")
    ap.add_argument("--arm", required=True,
                    choices=["loop154c", "loop172"])
    ap.add_argument("--proto", required=True, choices=["v3", "old"])
    ap.add_argument("--only", default="all")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    daemon_cls = DAEMONS[args.arm]
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg["sleep_threshold"] = 100000
    want = args.only.split(",")
    splits = [s for s in SPLITS if want == ["all"] or s[0] in want]
    workroot = outdir / f"scratch-bench172b-{args.arm}-{args.proto}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "arm": args.arm, "proto": args.proto,
                     "splits": {}}
    for stag, path in splits:
        items = [json.loads(l) for l in Path(str(path)).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [run_item_v3(it, workroot / stag, copy.deepcopy(cfg),
                            daemon_cls, args.proto) for it in items]
        (outdir / f"fable_bench172b_{args.arm}_{args.proto}_{stag}_"
                   f"rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table: dict[str, dict] = {}
        for r in rows:
            cell = table.setdefault(r["verdict"], 0)
            table[r["verdict"]] = cell + 1
        summary["splits"][stag] = {
            "n": len(rows), "verdicts": table,
            "confirms": sum(r["confirms"] for r in rows),
            "teach_reject_items": sum(1 for r in rows
                                      if r["n_teach_reject"])}
        print(f"{args.arm}/{args.proto} {stag}: n={len(rows)} "
              f"verdicts={table} "
              f"confirms={summary['splits'][stag]['confirms']}",
              flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (outdir / f"bench172b_{args.arm}_{args.proto}_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
