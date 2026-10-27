#!/usr/bin/env python3
"""Experiment 113b -- BEFORE/AFTER bench with SCORER v2 (registered one change).

Loop113 (before) vs loop113b = loop113 + fallback to the exact loop102
chain when BOTH composers return None (after), same two splits as exp 113,
each item in a FRESH daemon dir via the mailbox (process_file: bytes in,
outbox reply file out). Teach sentences verbatim, never rewritten; teach
replies graded ACCEPTED vs REJECTED as in exp 113.

SCORER v2 (identical to exp 113, registered before any run):
  1. Mouth-framing: extract the ANSWER VALUE from the loop's reply
     sentence (text after the final " is " / " are ", stripped of the
     trailing period), exact normalised match vs gold+aliases = correct.
  2. Word-boundary: abstain = the loop's own decline / clarify /
     "I don't know" forms matched on WORD boundaries. Else wrong.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench113b_run.py --run
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

from fable_loop113_agent import (  # noqa: E402 (before arm)
    DEFAULT_CONFIG113, Loop113Daemon)
from fable_loop113b_agent import (  # noqa: E402 (after arm)
    DEFAULT_CONFIG113B, Loop113bDaemon)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113b-20260922"
DATA_A = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_B = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"

DUP_ACK = "I already have that."

# The loop's own decline / clarify / "I don't know" forms (from
# fable_agent_loop FakeEars/FakeMouth, fable_earsguard91, loop102 hearsay/F5,
# notebook-contract TEMPLATES, ChainEars miss text). Matched on WORD
# boundaries so "notable" never counts as "not".
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
            "question": str(item.get("question", "")),
            "golds": golds, "reply": reply, "verdict": verdict,
            "exact": bool(exact), "contains_gold": bool(contains),
            "extracted": extract_answer(reply), "ears_stage": stage,
            "n_teach": len(teach_replies), "n_teach_reject": n_reject,
            "teach_replies": teach_replies}


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
    cfg113 = copy.deepcopy(DEFAULT_CONFIG113)
    cfg113b = copy.deepcopy(DEFAULT_CONFIG113B)
    (ART / "loop113b-config.json").write_text(json.dumps(cfg113b, indent=1),
                                              encoding="utf-8")
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch113b"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "arms": {}}
    arms = (("loop113", Loop113Daemon, cfg113),
            ("loop113b", Loop113bDaemon, cfg113b))
    splits = (("fable_edit_200", DATA_A), ("s2fresh_4hop", DATA_B))
    for arm, factory, cfg in arms:
        out["arms"][arm] = {}
        for tag, path in splits:
            items = [json.loads(l) for l in path.read_text(
                encoding="utf-8").splitlines() if l.strip()]
            rows = [run_item(it, workroot / arm / tag, cfg, factory)
                    for it in items]
            (ART / f"fable_bench113b_{arm}_{tag}_rows.jsonl").write_text(
                "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                           for r in rows) + "\n", encoding="utf-8")
            out["arms"][arm][tag] = {"n": len(rows), "table": summarize(rows)}
            print(f"{arm} {tag}: items={len(rows)}")
            for typ, cell in sorted(out["arms"][arm][tag]["table"].items()):
                print(f"  {typ}: {cell}")
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench113b_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 113b before/after bench")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
