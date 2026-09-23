#!/usr/bin/env python3
"""Merge 292 blind panel: sealed scorer (builders use it unchanged).

Usage: score_panel.py [--panel panel.jsonl] [--rows rows.jsonl]
                       [--base base291.jsonl]
Defaults resolve under artifacts/claude-mixpanel292-20260923/.

Schema check first: exact ids m292-001..080, exact family counts
(chain_verb 12, backwards_bug 10, yesno 14, mixed 12, broken_chain 8,
forward_control 10, statement_control 8, correction_control 6), required
fields (id, family, setup 1-4 turns, question, expect, gold list, note)
and family-consistent expect labels
(chain_verb=value, backwards_bug=value, yesno in yes/no/unknown,
mixed in value/yes/no/unknown, broken_chain=unknown,
forward_control=control, statement_control=control,
correction_control=value).
Any violation prints SCHEMA-MISMATCH and exits 3 (VOID, not FAIL).

Rules (case-insensitive text match; curly apostrophes folded):
- value:   RIGHT iff every gold string appears in the reply.
- yes/no:  RIGHT iff the reply starts with Yes/No (matching expect) and
  contains every gold string.
- unknown: RIGHT iff the reply holds "don't know", "couldn't" or
  "not that I know" and does not start with Yes or No.
- control: RIGHT iff the row reply is identical to the base291 row reply.
- wrong: a yes/no reply with the opposite answer (or any Yes/No-start
  reply to an unknown-expect item), or a non-abstain value/unknown reply
  that names a taught subject/value not in gold while missing gold.
  Abstains are never wrong. Anything else is a miss.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAMILIES = {"chain_verb": 12, "backwards_bug": 10, "yesno": 14, "mixed": 12,
            "broken_chain": 8, "forward_control": 10, "statement_control": 8,
            "correction_control": 6}
EXPECTS = {"chain_verb": {"value"}, "backwards_bug": {"value"},
           "yesno": {"yes", "no", "unknown"},
           "mixed": {"value", "yes", "no", "unknown"},
           "broken_chain": {"unknown"}, "forward_control": {"control"},
           "statement_control": {"control"}, "correction_control": {"value"}}
YN_START = re.compile(r"\s*(Yes|No)\b")


def fold(s: str) -> str:
    return str(s).replace("\u2019", "'").replace("\u2018", "'").lower()


def yn_start(reply: str) -> str | None:
    m = YN_START.match(reply)
    return m.group(1) if m else None


def is_abstain(reply: str) -> bool:
    low = fold(reply)
    return ("don't know" in low or "couldn't" in low
            or "not that i know" in low)


def taught_names(row: dict) -> list[str]:
    out = []
    for tbl in ("stored_after_setup_actual", "stored_after_question_actual"):
        for tri in row.get(tbl) or []:
            for cell in tri:
                s = str(cell).strip()
                if s and s not in out:
                    out.append(s)
    return out


def schema_check(items: list[dict]) -> str | None:
    if len(items) != 80:
        return f"want 80 items, got {len(items)}"
    ids = [it.get("id") for it in items]
    if ids != [f"m292-{i:03d}" for i in range(1, 81)]:
        return "ids must be m292-001..080 in order"
    counts: dict[str, int] = {}
    for it in items:
        if set(it) != {"id", "family", "setup", "question", "expect",
                       "gold", "note"}:
            return f"{it.get('id')}: bad fields {sorted(set(it))}"
        fam = it.get("family")
        if fam not in FAMILIES:
            return f"{it.get('id')}: bad family {fam!r}"
        counts[fam] = counts.get(fam, 0) + 1
        if not isinstance(it.get("setup"), list) or not 1 <= len(it["setup"]) <= 4:
            return f"{it.get('id')}: setup must list 1-4 turns"
        if it.get("expect") not in EXPECTS[fam]:
            return (f"{it.get('id')}: expect {it.get('expect')!r} "
                    f"not allowed for {fam}")
        if not isinstance(it.get("gold"), list):
            return f"{it.get('id')}: gold must be a list"
    if counts != FAMILIES:
        return f"bad family counts {counts}"
    return None


def grade(item: dict, row: dict, base_by_id: dict) -> str:
    reply = str(row.get("question_reply", ""))
    low = fold(reply)
    expect = item["expect"]
    gold = [str(g) for g in item.get("gold", [])]
    yn = yn_start(reply)
    if expect == "control":
        b = base_by_id.get(item["id"], {})
        return "right" if reply == str(b.get("question_reply", "")) else "wrong"
    if expect in ("yes", "no"):
        want = "Yes" if expect == "yes" else "No"
        opp = "No" if expect == "yes" else "Yes"
        if yn == opp:
            return "wrong"
        if yn == want and all(fold(g) in low for g in gold):
            return "right"
        return "miss"
    if expect == "unknown":
        if is_abstain(reply) and yn is None:
            return "right"
        if yn is not None:
            return "wrong"
        if is_abstain(reply):
            return "miss"
        names = taught_names(row)
        if any(fold(n) and fold(n) in low for n in names):
            return "wrong"
        return "miss"
    # expect == "value"
    if all(fold(g) in low for g in gold):
        return "right"
    if is_abstain(reply):
        return "miss"
    names = taught_names(row)
    gl = [fold(g) for g in gold]
    if any(fold(n) and fold(n) in low and fold(n) not in gl for n in names):
        return "wrong"
    return "miss"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sealed scorer for mixpanel292")
    ap.add_argument("--panel", default=str(HERE / "panel.jsonl"))
    ap.add_argument("--rows", default=str(HERE / "base291.jsonl"))
    ap.add_argument("--base", default=str(HERE / "base291.jsonl"))
    args = ap.parse_args(argv)
    items = [json.loads(x) for x in Path(args.panel).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    bad = schema_check(items)
    if bad is not None:
        print(f"SCHEMA-MISMATCH: {bad}")
        return 3
    rows = [json.loads(x) for x in Path(args.rows).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    base = [json.loads(x) for x in Path(args.base).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    base_by_id = {r.get("id"): r for r in base}
    row_by_id = {r.get("id"): r for r in rows}
    if set(row_by_id) != {it["id"] for it in items}:
        print("SCHEMA-MISMATCH: row ids do not match panel ids")
        return 3
    tot = {"right": 0, "wrong": 0, "miss": 0}
    print("family n right wrong miss writes stages")
    for fam in FAMILIES:
        fam_items = [it for it in items if it["family"] == fam]
        marks = {"right": 0, "wrong": 0, "miss": 0}
        writes = 0
        stages: dict[str, int] = {}
        for it in fam_items:
            row = row_by_id[it["id"]]
            m = grade(it, row, base_by_id)
            marks[m] += 1
            tot[m] += 1
            if row.get("question_wrote"):
                writes += 1
            st = str(row.get("question_stage", ""))
            stages[st] = stages.get(st, 0) + 1
        stxt = ",".join(f"{k}={v}" for k, v in sorted(stages.items()))
        print(f"{fam} {len(fam_items)} {marks['right']} {marks['wrong']} "
              f"{marks['miss']} {writes} {stxt}")
    print(f"TOTAL 80 {tot['right']} {tot['wrong']} {tot['miss']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
