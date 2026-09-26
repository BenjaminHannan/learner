#!/usr/bin/env python3
"""Format and mix check for a chat panel in the 382 format (everyday-chat thread, 2026-09-26). New file only.

Checks a folder of part files (part*.jsonl) or one items.jsonl written from design/v3/30-modes/382-panels-spec.md:
keys, ids, 4 to 7 turns per conversation, kind mix, teach/ask limits, ask_known gold in an earlier turn, think
gold. Prints counts and ids only, never turn text, so it can be run on a TEST-ONLY panel by its writer or auditor.

usage: python3 scripts/claude_chatdev_check.py FOLDER [--first-letter-range A-M] [--expect N]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

KINDS = ("smalltalk", "advice", "explain", "feelings", "followup", "think", "teach", "ask_known", "ask_unknown")
TARGET = {"smalltalk": 15, "advice": 25, "explain": 20, "feelings": 10, "followup": 15, "think": 10}
TURN_KEYS = {"text", "kind", "facts", "gold", "gold_number"}


def load(folder: Path) -> list[dict]:
    files = sorted(folder.glob("part*.jsonl")) or [folder / "items.jsonl"]
    rows = []
    for f in files:
        rows += [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--first-letter-range", default="")
    ap.add_argument("--expect", type=int, default=60)
    a = ap.parse_args()
    rows = load(Path(a.folder))
    bad = collections.Counter()
    ids = [r.get("item_id") for r in rows]
    if len(set(ids)) != len(ids):
        bad["duplicate_ids"] += 1
    kinds = collections.Counter()
    conv_teach = conv_known = conv_unknown = 0
    names = collections.Counter()
    for r in rows:
        if set(r) != {"item_id", "turns"}:
            bad["conv_keys:" + str(r.get("item_id"))] += 1
            continue
        t = r["turns"]
        if not 4 <= len(t) <= 7:
            bad["turn_count:" + r["item_id"]] += 1
        ck = collections.Counter()
        for i, x in enumerate(t):
            if set(x) != TURN_KEYS:
                bad["turn_keys:" + r["item_id"]] += 1
                continue
            k = x["kind"]
            if k not in KINDS:
                bad["kind:" + r["item_id"]] += 1
                continue
            kinds[k] += 1
            ck[k] += 1
            if k == "teach" and not x["facts"]:
                bad["teach_no_facts:" + r["item_id"]] += 1
            if k != "teach" and x["facts"]:
                bad["facts_not_teach:" + r["item_id"]] += 1
            if k == "ask_known":
                g = (x["gold"] or "").lower()
                if not g or not any(g in y["text"].lower() for y in t[:i]):
                    bad["gold_not_earlier:" + r["item_id"]] += 1
            elif k == "think":
                if not x["gold"]:
                    bad["think_no_gold:" + r["item_id"]] += 1
                if x["gold_number"] is not None and str(x["gold_number"]).rstrip("0").rstrip(".") not in \
                        re.sub(r"[,$]", "", x["gold"]):
                    bad["gold_number_not_in_gold:" + r["item_id"]] += 1
            elif x["gold"] is not None or x["gold_number"] is not None:
                bad["gold_on_wrong_kind:" + r["item_id"]] += 1
            for f in x["facts"] or []:
                v = str(f.get("value", ""))
                if v[:1].isupper():
                    names[v.split()[0]] += 1
        for k in ("teach", "ask_known", "ask_unknown"):
            if ck[k] > 1:
                bad[k + "_twice:" + r["item_id"]] += 1
        conv_teach += ck["teach"] > 0
        conv_known += ck["ask_known"] > 0
        conv_unknown += ck["ask_unknown"] > 0
    n = sum(kinds.values())
    share = {k: round(100 * kinds[k] / n, 1) for k in KINDS} if n else {}
    for k, want in TARGET.items():
        if n and abs(share[k] - want) > 5:
            bad["mix:" + k] += 1
    scale = a.expect / 60
    if conv_teach > round(15 * scale) or conv_known > round(8 * scale) or conv_unknown > round(6 * scale):
        bad["teach_ask_limits"] += 1
    if a.first_letter_range:
        lo, hi = a.first_letter_range.split("-")
        for nm in names:
            if not lo <= nm[0] <= hi:
                bad["name_letter"] += 1
    if len(rows) != a.expect:
        bad["conversation_count"] += 1
    print(json.dumps({"conversations": len(rows), "turns": n, "kinds": dict(kinds), "share": share,
                      "conv_teach": conv_teach, "conv_ask_known": conv_known, "conv_ask_unknown": conv_unknown,
                      "problems": dict(bad)}))
    print("CHECK", "OK" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
