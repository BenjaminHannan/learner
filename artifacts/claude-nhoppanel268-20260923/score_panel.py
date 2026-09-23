#!/usr/bin/env python3
"""Score nhoppanel268 rows against the panel (sealed; builders use unchanged).

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-nhoppanel268-20260923/score_panel.py \
    <panel.jsonl> <rows.jsonl> [out.json]

Schema gate (panel schema contract): before scoring anything, check the
panel has exactly the files/fields/families/labels below. On any mismatch
print SCHEMA-MISMATCH and exit 3 with no verdict (that run is VOID).

Expected schema:
- panel items: keys {id, family, setup, question, gold, note};
  id n268-001..n268-070 in order; family in
  {reverse_chain, reverse_nochain, uncued_reverse, forward_chain,
   forward_1hop, abstain} with counts {24, 10, 8, 12, 10, 6};
  setup a list of 1-4 strings; question a non-empty string;
  gold a JSON list of strings ([] = abstain item).
- row items: keys {id, setup_replies, question_reply, question_stage,
  stored_after_setup_actual, stored_after_question_actual, question_wrote};
  same ids in the same order as the panel.

Scoring (per item):
- taught names: subject/value strings parsed from each setup teach of the
  form "A's R is B." (split on the first "'s ", value = text after "is ",
  trailing period stripped).
- non-abstain family: right = every gold string appears in question_reply
  (case-insensitive). wrong = the reply names a taught subject/value not in
  gold AND misses some gold string AND the reply is not an abstain-form
  reply (no "i don't know" / "couldn").
- abstain family: right = the reply has abstain form ("i don't know" or
  "couldn", case-insensitive) AND names no taught subject/value.
  wrong = not right AND the reply names a taught subject/value.
- question_wrote: straight from the row.

Output: per-item lines plus per-family right / wrong / question_wrote
counts; optional out.json with the same. Category level only: never prints
item text.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

FAMILIES = ["reverse_chain", "reverse_nochain", "uncued_reverse",
            "forward_chain", "forward_1hop", "abstain"]
EXPECT_COUNTS = {"reverse_chain": 24, "reverse_nochain": 10,
                 "uncued_reverse": 8, "forward_chain": 12,
                 "forward_1hop": 10, "abstain": 6}
ITEM_KEYS = {"id", "family", "setup", "question", "gold", "note"}
ROW_KEYS = {"id", "setup_replies", "question_reply", "question_stage",
            "stored_after_setup_actual", "stored_after_question_actual",
            "question_wrote"}


def mismatch(reason: str) -> int:
    print(f"SCHEMA-MISMATCH: {reason}")
    return 3


def parse_teach(teach: str) -> tuple[str, str]:
    """Parse "A's R is B." -> (A, B). Raises ValueError when unparseable."""
    if "'s " not in teach:
        raise ValueError(f"no possessive in {teach!r}")
    subj, rest = teach.split("'s ", 1)
    subj = subj.strip()
    if " is " not in rest:
        raise ValueError(f"no ' is ' in {teach!r}")
    val = rest.split(" is ", 1)[1].strip().rstrip(".").strip()
    if not subj or not val:
        raise ValueError(f"empty side in {teach!r}")
    return subj, val


def is_abstain_form(reply: str) -> bool:
    r = reply.lower()
    return ("i don't know" in r) or ("couldn" in r)


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(__doc__)
        return 2
    panel_path, rows_path = Path(argv[1]), Path(argv[2])
    out_path = Path(argv[3]) if len(argv) == 4 else None
    try:
        panel = [json.loads(line) for line in
                 panel_path.read_text(encoding="utf-8").splitlines()
                 if line.strip()]
        rows = [json.loads(line) for line in
                rows_path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    except (OSError, ValueError) as e:
        return mismatch(str(e))
    if len(panel) != 70:
        return mismatch(f"panel has {len(panel)} items, want 70")
    if [it.get("id") for it in panel] != [f"n268-{i:03d}"
                                          for i in range(1, 71)]:
        return mismatch("panel ids are not n268-001..n268-070 in order")
    for it in panel:
        if set(it) != ITEM_KEYS:
            return mismatch(f"{it.get('id')}: keys {sorted(set(it))}")
        if it["family"] not in FAMILIES:
            return mismatch(f"{it['id']}: family {it['family']!r}")
        if (not isinstance(it["setup"], list) or
                not 1 <= len(it["setup"]) <= 4 or
                not all(isinstance(s, str) for s in it["setup"])):
            return mismatch(f"{it['id']}: bad setup")
        if not isinstance(it["question"], str) or not it["question"]:
            return mismatch(f"{it['id']}: bad question")
        if (not isinstance(it["gold"], list) or
                not all(isinstance(g, str) for g in it["gold"])):
            return mismatch(f"{it['id']}: gold is not a JSON list of strings")
        try:
            for teach in it["setup"]:
                parse_teach(teach)
        except ValueError as e:
            return mismatch(f"{it['id']}: {e}")
    if Counter(it["family"] for it in panel) != Counter(EXPECT_COUNTS):
        return mismatch(
            f"family counts {dict(Counter(it['family'] for it in panel))}")
    if len(rows) != 70:
        return mismatch(f"rows has {len(rows)} rows, want 70")
    if [r.get("id") for r in rows] != [it["id"] for it in panel]:
        return mismatch("row ids do not match panel ids in order")
    for r in rows:
        if set(r) != ROW_KEYS:
            return mismatch(f"{r.get('id')}: row keys {sorted(set(r))}")

    per_item = []
    for it, r in zip(panel, rows):
        reply = r["question_reply"] or ""
        low = reply.lower()
        taught: list[str] = []
        for teach in it["setup"]:
            a, b = parse_teach(teach)
            taught += [a, b]
        gold = it["gold"]
        if it["family"] == "abstain":
            names_taught = any(t.lower() in low for t in taught)
            right = is_abstain_form(reply) and not names_taught
            wrong = (not right) and names_taught
        else:
            right = all(g.lower() in low for g in gold)
            names_other = any(t.lower() in low and
                              all(t.lower() != g.lower() for g in gold)
                              for t in taught)
            misses = any(g.lower() not in low for g in gold)
            wrong = names_other and misses and not is_abstain_form(reply)
        per_item.append({"id": it["id"], "family": it["family"],
                         "right": right, "wrong": wrong,
                         "question_wrote": bool(r["question_wrote"]),
                         "question_stage": r["question_stage"]})

    fam_right: Counter = Counter()
    fam_wrong: Counter = Counter()
    fam_wrote: Counter = Counter()
    fam_n: Counter = Counter()
    for e in per_item:
        fam_n[e["family"]] += 1
        fam_right[e["family"]] += int(e["right"])
        fam_wrong[e["family"]] += int(e["wrong"])
        fam_wrote[e["family"]] += int(e["question_wrote"])
    total_right = sum(fam_right.values())
    total_wrong = sum(fam_wrong.values())
    total_wrote = sum(fam_wrote.values())

    lines = ["nhoppanel268 score (category level only):"]
    for fam in FAMILIES:
        lines.append(f"{fam}: n={fam_n[fam]} right={fam_right[fam]} "
                     f"wrong={fam_wrong[fam]} "
                     f"question_wrote={fam_wrote[fam]}")
    lines.append(f"TOTAL: n=70 right={total_right} wrong={total_wrong} "
                 f"question_wrote={total_wrote}")
    report = "\n".join(lines)
    print(report)
    if out_path is not None:
        out_path.write_text(json.dumps(
            {"per_item": per_item,
             "per_family": {fam: {"n": fam_n[fam],
                                  "right": fam_right[fam],
                                  "wrong": fam_wrong[fam],
                                  "question_wrote": fam_wrote[fam]}
                            for fam in FAMILIES},
             "total": {"n": 70, "right": total_right,
                       "wrong": total_wrong,
                       "question_wrote": total_wrote}},
            indent=1), encoding="utf-8")
        print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
