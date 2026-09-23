#!/usr/bin/env python3
"""Sealed scorer for chainpanel266 (builders use it unchanged).

Loads artifacts/claude-chainpanel266-20260923/panel.jsonl + base138m.jsonl,
checks the panel schema first (SCHEMA-MISMATCH, exit 3, no verdict when the
schema is off), then scores per item and per family.

Verdicts:
- gold families (chain_verb, chain_verb_three, chain_possessive) and
  plain_control: RIGHT iff every gold string appears in the reply
  (case-insensitive substring). Else ABSTAIN if the reply is an abstain,
  else WRONG if the reply names a taught value not in gold, else OTHER.
- broken_chain: RIGHT iff the reply is an abstain ("I don't know" or
  "I couldn't", case-insensitive) and names no value that is not taught
  for that chain (taught = stored subjects/values after setup plus words
  in the setup and question; candidates = every value seen anywhere in
  the panel). Else WRONG/OTHER by the same reply rules (gold is []).
- statement_control: RIGHT iff the stored facts after the turn equal the
  stored facts after setup (no new writes); else WRONG.
question_wrote is reported per item and per family.
"""
import json
import re
import sys
from pathlib import Path

ART = Path(__file__).resolve().parent
PANEL = ART / "panel.jsonl"
ROWS = ART / "base138m.jsonl"

FAMILIES = {"chain_verb": 30, "chain_verb_three": 6, "chain_possessive": 10,
            "broken_chain": 12, "plain_control": 14, "statement_control": 8}
GOLD_FAMS = {"chain_verb", "chain_verb_three", "chain_possessive",
             "plain_control"}
ROW_FIELDS = {"id", "setup_replies", "question_reply",
              "stored_after_setup_actual", "stored_after_question_actual",
              "question_wrote"}

ABSTAIN_RE = re.compile(r"(i don'?t know|i couldn'?t)", re.I)


def bad_schema(msg):
    print(f"SCHEMA-MISMATCH: {msg}")
    return 3


def norm(s):
    return " ".join(str(s).lower().replace("\u2019", "'").split())


def whole_word(hay, needle):
    n = norm(needle)
    if not n:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])",
                     norm(hay)) is not None


def main():
    try:
        plines = [l for l in PANEL.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
        rlines = [l for l in ROWS.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
    except FileNotFoundError as e:
        return bad_schema(f"missing file {e.filename}")
    items = [json.loads(l) for l in plines]
    rows = {json.loads(l)["id"]: json.loads(l) for l in rlines}
    if len(items) != 80:
        return bad_schema(f"panel has {len(items)} items, want 80")
    if len(rows) != 80:
        return bad_schema(f"rows file has {len(rows)} rows, want 80")
    want_ids = [f"c266-{i:03d}" for i in range(1, 81)]
    if [it.get("id") for it in items] != want_ids:
        return bad_schema("item ids are not c266-001..080 in order")
    if set(rows) != set(want_ids):
        return bad_schema("row ids do not match panel ids")
    counts = {}
    for it in items:
        if set(it) != {"id", "family", "setup", "question", "gold", "note"}:
            return bad_schema(f"{it.get('id')}: fields {sorted(it)}")
        if it["family"] not in FAMILIES:
            return bad_schema(f"{it['id']}: family {it['family']!r}")
        if not isinstance(it["gold"], list):
            return bad_schema(f"{it['id']}: gold is not a list")
        if not (isinstance(it["setup"], list) and 1 <= len(it["setup"]) <= 4):
            return bad_schema(f"{it['id']}: setup length off")
        counts[it["family"]] = counts.get(it["family"], 0) + 1
    if counts != FAMILIES:
        return bad_schema(f"family counts {counts}")
    for rid, r in rows.items():
        if set(r) != ROW_FIELDS:
            return bad_schema(f"row {rid}: fields {sorted(r)}")
    # global value vocabulary for the broken-chain untaught check
    vocab = set()
    for it in items:
        for g in it["gold"]:
            vocab.add(norm(g))
    for r in rows.values():
        for t in r["stored_after_setup_actual"]:
            vocab.add(norm(t[0]))
            vocab.add(norm(t[2]))
    vocab.discard("")
    fam = {f: {"n": 0, "right": 0, "wrong": 0, "abstain": 0, "other": 0,
               "question_wrote": 0} for f in FAMILIES}
    print("id family verdict question_wrote reply-head")
    for it in items:
        r = rows[it["id"]]
        reply = r["question_reply"]
        abst = ABSTAIN_RE.search(reply) is not None
        stored = r["stored_after_setup_actual"]
        taught = {norm(t[0]) for t in stored} | {norm(t[2]) for t in stored}
        taught -= {""}
        text_words = norm(" ".join(it["setup"]) + " " + it["question"])
        gold = it["gold"]
        if it["family"] == "statement_control":
            verdict = ("RIGHT" if r["stored_after_question_actual"] == stored
                       and not r["question_wrote"] else "WRONG")
        elif it["family"] == "broken_chain":
            untaught = [v for v in vocab
                        if v not in taught and v not in text_words
                        and whole_word(reply, v)]
            if abst and not untaught:
                verdict = "RIGHT"
            elif not abst and any(whole_word(reply, t) for t in taught):
                verdict = "WRONG"
            else:
                verdict = "OTHER" if not abst else "ABSTAIN"
        else:
            if all(norm(g) in norm(reply) for g in gold):
                verdict = "RIGHT"
            elif abst:
                verdict = "ABSTAIN"
            elif any(whole_word(reply, t) for t in taught
                     if not any(norm(t) == norm(g) for g in gold)):
                verdict = "WRONG"
            else:
                verdict = "OTHER"
        F = fam[it["family"]]
        F["n"] += 1
        F[{"RIGHT": "right", "WRONG": "wrong", "ABSTAIN": "abstain",
           "OTHER": "other"}[verdict]] += 1
        F["question_wrote"] += int(bool(r["question_wrote"]))
        print(f"{it['id']} {it['family']} {verdict} "
              f"{int(bool(r['question_wrote']))} {reply[:60]!r}")
    print("family n right wrong abstain other question_wrote")
    tot = {"n": 0, "right": 0, "wrong": 0, "abstain": 0, "other": 0,
           "question_wrote": 0}
    for f in FAMILIES:
        F = fam[f]
        print(f"{f} {F['n']} {F['right']} {F['wrong']} {F['abstain']} "
              f"{F['other']} {F['question_wrote']}")
        for k in tot:
            tot[k] += F[k]
    print(f"TOTAL {tot['n']} {tot['right']} {tot['wrong']} {tot['abstain']} "
          f"{tot['other']} {tot['question_wrote']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
