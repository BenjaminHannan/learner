#!/usr/bin/env python3
"""bank-v1-aug.json -> bank-v1-aug2.json: augment the 16 banks `PatternSource.load` filled from the fallback.

For each such bank the fallback rows (copied from `render._fallback_rows`: same ids, texts, splits, styles) are
written into the json as ordinary entries, replacing whatever partial rows bank-v1 had for that bank (the loader
already threw those away), so validation/test render exactly as before. TRAIN-only wordings are then added with
the generalize.paraphrase pipeline (mechanical-only dedup against all splits, no held-out text in any prompt).
Also tops up q.why_at, q.yn_at and q.yn_in to 24 train wordings.

  python -m generalize.paraphrase_aug2 run [--budget 4.0]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from generalize import paraphrase as PP
from learnlab.splits import SPLITS
from learnlab.village import render as R

AUG = PP.PATTERNS / "bank-v1-aug.json"
OUT2 = PP.PATTERNS / "bank-v1-aug2.json"
TOPUP = ("q.why_at", "q.yn_at", "q.yn_in")
TEACHER_ADD = 5  # new wordings per train style for t.right / t.quiz_later (1 -> 6 each)
PP.STATE = Path("/tmp/paraphrase-cache/state-aug2.json")  # keep the earlier run's resumable state intact


def embed_fallback(aug: dict) -> tuple[dict, list[str]]:
    """Copy `aug`, writing the fallback rows of every fallback-filled bank into it explicitly."""
    banks = sorted(PP.fallback_banks(AUG))
    out = json.loads(json.dumps(aug))
    styles = out["manifest"]["families"]["teacher_style"]["assignment"]
    assignment = out["manifest"]["families"]["template"]["assignment"]
    rows = [r for r in R._fallback_rows(styles) if r["bank"] in banks]
    for bank in banks:
        out["banks"][bank] = {split: [] for split in SPLITS}
    for r in rows:
        entry = {"id": r["id"], "text": r["text"], "writer": "fallback"}
        if "style" in r:
            entry["style"] = r["style"]
        out["banks"][r["bank"]][r["split"]].append(entry)
        assignment[r["id"]] = r["split"]
    for bank in banks:
        for split in SPLITS:
            out["banks"][bank][split].sort(key=lambda e: e["id"])
            out["counts"][bank][split] = len(out["banks"][bank][split])
        out["counts"][bank]["accepted"] = sum(out["counts"][bank][s] for s in SPLITS)
    return out, banks


def make_plan(base: dict, banks: list[str], target: int) -> dict:
    need = {}
    train = PP.current_train(base)
    for key, texts in train.items():
        bank = key[0] if isinstance(key, tuple) else key
        if isinstance(key, tuple):
            if bank in ("t.right", "t.quiz_later"):
                need[key] = TEACHER_ADD
        elif (bank in banks or bank in TOPUP) and len(texts) < target:
            need[key] = target - len(texts)
    return need


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--target", type=int, default=24)
    parser.add_argument("--budget", type=float, default=4.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=PP.MAX_ROUNDS)
    args = parser.parse_args(argv)
    PP.BUDGET["limit"] = args.budget
    aug = json.loads(AUG.read_text())
    base, banks = embed_fallback(aug)
    need = make_plan(base, banks, args.target)
    if args.command == "plan":
        for k, v in sorted(need.items(), key=str):
            print(k, len(PP.current_train(base)[k]), "+", v)
        return
    PP.CACHE.mkdir(parents=True, exist_ok=True)
    run = PP.Run(base, need, args.workers)
    # ids of bank-v1 rows the loader never used (now replaced by the fallback rows) stay assigned: never reuse them
    taken = set(base["manifest"]["families"]["template"]["assignment"])
    run.seen_ids |= taken
    for key in run.accepted:
        run.accepted[key] = [e for e in run.accepted[key] if e["id"] not in taken]
    try:
        for r in range(args.rounds):
            if not run.round(r):
                break
    except PP.BudgetExceeded as error:
        print("STOPPED:", error, flush=True)
    run.save()
    PP.final_dedup(base, run)
    dropped: set[str] = set()
    for _ in range(6):
        entries = [e for es in run.accepted.values() for e in es if e["id"] not in dropped]
        out = PP.assemble(base, entries)
        out["augmentation"] = {**out["augmentation"], "script": "generalize/paraphrase_aug2.py",
                               "note": "fallback rows of 16 banks written explicitly + train-only additions; validation/test unchanged",
                               "explicit_fallback_banks": banks}
        PP.write_bank(out, OUT2)
        bad = PP.leaking_ids(OUT2) - set(base["manifest"]["families"]["template"]["assignment"])
        print(f"simulated audit: {len(bad)} new ids implicated", flush=True)
        if not bad:
            break
        dropped |= bad
    PP.verify_untouched(base, out)
    R.PatternSource.load(OUT2)
    print(f"dropped by audit {len(dropped)}; wrote {OUT2}: {len(entries)} new train patterns")
    print(PP.USAGE.summary())
    print("unfilled:", {str(k): run.remaining(k) for k in need if run.remaining(k) > 0})


if __name__ == "__main__":
    main()
