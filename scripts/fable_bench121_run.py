#!/usr/bin/env python3
"""Experiment 121 -- registered bench: loop121 on the NEW blind split + OLD fresh.

One item, one FRESH Loop121Daemon directory, English only (bytes in, outbox
reply out). Teach sentences verbatim, never rewritten; teach replies graded
ACCEPTED vs REJECTED as in exps 111/113. Scorer v2 unchanged from exp 113.

This script NEVER prints item sentences or questions -- only aggregate
counts, verdict tallies, and (for failures) item ids with reply excerpts.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench121_run.py --run
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import string
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_loop121_agent import (  # noqa: E402 (this experiment's agent)
    DEFAULT_CONFIG121, Loop121Daemon)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench121-20260922"
DATA_NEW = ROOT / "data" / "open" / "bench121" / "fable_edit121_4hop.jsonl"
DATA_OLD = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"

DUP_ACK = "I already have that."

ABSTAIN_PHRASES = (
    "i don't know",
    "i dont know",
    "was that a question",
    "i didn't understand that",
    "i did not understand",
    "i didn't catch anything",
    "i can take one fact at a time",
    "could you split that",
    "do you know that yourself",
    "i only save facts you tell me directly",
    "i can only follow",
    "please say it like",
    "i can only handle one-word names",
    "i didn't get the value",
    "which is not someone i can look up",
    "i know more than one",
    "which one do you mean",
    "please answer with",
    "please answer yes or no",
    "i wasn't waiting for an answer",
    "i couldn't read that message",
    "do you want me to change it to",
)
_ABSTAIN_RES = [re.compile(r"\b" + re.escape(p) + r"\b")
                for p in ABSTAIN_PHRASES]


def norm(s) -> str:
    s = (s or "").lower().replace("\u2019", "'")
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(t for t in s.split() if t not in ("a", "an", "the"))


def extract_answer(reply: str) -> str:
    """Answer value = text after the final ' is ' / ' are ' (v2 contract)."""
    low = (reply or "").lower()
    hits = [low.rfind(" is "), low.rfind(" are ")]
    idx = max(hits)
    tail = reply[idx + 4:] if idx >= 0 else (reply or "")
    return tail.strip().rstrip(".").strip()


def classify_v2(reply: str, golds: list[str]
                ) -> tuple[str, bool, bool]:
    """Return (verdict, exact, contains_gold)."""
    value = extract_answer(reply)
    nv = norm(value)
    ngs = [norm(g) for g in golds if norm(g)]
    exact = bool(nv) and nv in ngs
    if exact:
        return "correct", True, True
    contains = any(g in norm(reply) for g in ngs)
    low = (reply or "").lower()
    if any(rx.search(low) for rx in _ABSTAIN_RES):
        return "abstain", False, bool(contains)
    return "wrong", False, bool(contains)


def teach_accepted(reply: str) -> bool:
    r = (reply or "").strip()
    return r.startswith("Saved:") or r == DUP_ACK


def run_item(item: dict, workroot: Path, cfg: dict) -> dict:
    """One item, one FRESH daemon directory, English only."""
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = Loop121Daemon(str(ddir), cfg=dict(cfg))
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
    verdict, exact, contains = classify_v2(reply, golds)
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:
        stage = ""
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "expected": str(item.get("expected", "?")),
            "verdict": verdict,
            "exact": bool(exact), "contains_gold": bool(contains),
            "extracted": extract_answer(reply), "ears_stage": stage,
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


def cmd_run(_args) -> int:
    cfg121 = copy.deepcopy(DEFAULT_CONFIG121)
    (ART / "loop121-config.json").write_text(json.dumps(cfg121, indent=1),
                                             encoding="utf-8")
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch121"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "arms": {"loop121": {}}}
    for tag, path in (("new_121_4hop", DATA_NEW),
                      ("old_s2fresh_4hop", DATA_OLD)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [run_item(it, workroot / tag, cfg121) for it in items]
        (ART / f"fable_bench121_loop121_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        out["arms"]["loop121"][tag] = {"n": len(rows),
                                       "table": summarize(rows)}
        print(f"loop121 {tag}: items={len(rows)}")
        for typ, cell in sorted(out["arms"]["loop121"][tag]["table"].items()):
            print(f"  {typ}: {cell}")
        for r in rows:
            if r["verdict"] == "wrong" or r["n_teach_reject"]:
                print(f"  FLAG {r['id']}: verdict={r['verdict']} "
                      f"rejects={r['n_teach_reject']} "
                      f"extracted={r['extracted'][:60]!r} "
                      f"stage={r['ears_stage']}")
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench121_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 121 registered bench")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
