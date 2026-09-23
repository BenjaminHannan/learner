#!/usr/bin/env python3
"""Score chainpanel266b rows (sealed; builders use it unchanged).

Loads panel.jsonl + base266.jsonl (default: the sealed siblings of this
script; override with argv: score_panel.py <panel> <rows>).

Schema gate (runs before any scoring): panel items need fields
id/family/setup/question/gold/note with the exact family counts
multiword_chain 24, three_link 8, oneword_chain 8, my_live 4,
broken_chain 12, plain_control 8, statement_control 6; rows need fields
id/setup_replies/question_reply/stored_after_setup_actual/
stored_after_question_actual/question_wrote with matching ids.
Anything missing or unexpected -> prints SCHEMA-MISMATCH, exit 3, no verdict.

Rules per item (reply = question_reply, lowercased for matching):
- gold families (multiword_chain, three_link, oneword_chain, my_live,
  plain_control): right = every gold string appears in the reply.
- broken_chain: right = abstain ("i don't know" or "i couldn't" in reply)
  naming no setup literal (no value stored under a non-person relation
  appears in the reply; echoing a taught person name is allowed).
- statement_control: right = stored facts after the turn equal stored
  facts after the setup (no new writes).
- wrong = the reply names a taught value (subject or value from the
  stored setup triples) that is not in gold, does not contain every gold
  string, and is not an abstain. (statement_control never counts wrong.)
- question_wrote = stored_after_question_actual != stored_after_setup_actual.

Usage (run from the repo root):
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-chainpanel266b-20260923/score_panel.py
"""

import json
import sys
from pathlib import Path

HERE = Path("artifacts/claude-chainpanel266b-20260923")
EXPECTED = {
    "multiword_chain": 24,
    "three_link": 8,
    "oneword_chain": 8,
    "my_live": 4,
    "broken_chain": 12,
    "plain_control": 8,
    "statement_control": 6,
}
GOLD_FAMS = {"multiword_chain", "three_link", "oneword_chain", "my_live", "plain_control"}
# Relations whose object is a person (the brief's first-link list). Any
# stored value under another relation (city, employer) is a literal.
PERSON_REL = {"boss", "mother", "father", "sister", "brother", "friend",
              "neighbour", "dentist", "coach", "wife", "husband"}
ITEM_FIELDS = {"id", "family", "setup", "question", "gold", "note"}
ROW_FIELDS = {"id", "setup_replies", "question_reply", "stored_after_setup_actual",
              "stored_after_question_actual", "question_wrote"}


def mismatch(msg):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def load(panel_path, rows_path):
    try:
        items = [json.loads(l) for l in Path(panel_path).read_text(encoding="utf-8").splitlines()
                 if l.strip()]
        rows = [json.loads(l) for l in Path(rows_path).read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except FileNotFoundError as e:
        mismatch(f"missing file {e.filename}")
    for it in items:
        if set(it.keys()) != ITEM_FIELDS:
            mismatch(f"item {it.get('id', '?')} fields {sorted(it.keys())}")
        if not isinstance(it["gold"], list) or not isinstance(it["setup"], list):
            mismatch(f"item {it['id']} gold/setup not lists")
        if it["family"] not in EXPECTED:
            mismatch(f"item {it['id']} unexpected family {it['family']!r}")
    counts = {}
    for it in items:
        counts[it["family"]] = counts.get(it["family"], 0) + 1
    if counts != EXPECTED:
        mismatch(f"family counts {counts} != {EXPECTED}")
    ids = [it["id"] for it in items]
    if len(set(ids)) != len(ids):
        mismatch("duplicate item ids")
    rmap = {}
    for r in rows:
        if set(r.keys()) != ROW_FIELDS:
            mismatch(f"row {r.get('id', '?')} fields {sorted(r.keys())}")
        rmap[r["id"]] = r
    if set(rmap) != set(ids):
        mismatch("row ids do not match panel ids")
    return items, rmap


def abstains(reply):
    r = reply.lower()
    return ("i don't know" in r) or ("i couldn't" in r)


def taught(row):
    subs, vals = set(), set()
    for s, r, v in row["stored_after_setup_actual"]:
        subs.add(str(s).lower())
        vals.add(str(v).lower())
    return subs, vals


def literals(row):
    # Values stored under non-person relations (city, employer, ...) are
    # place/company literals; values stored under person relations are
    # person names, which an honest abstain may echo ("I don't know Ivo's
    # mother."). The relation is in the stored triple, so no guessing.
    return {str(v).lower() for s, r, v in row["stored_after_setup_actual"]
            if str(r).lower() not in PERSON_REL}


def score(items, rmap):
    per_item = []
    for it in items:
        row = rmap[it["id"]]
        reply = str(row["question_reply"])
        rl = reply.lower()
        gold = [str(g).lower() for g in it["gold"]]
        subs, vals = taught(row)
        taught_all = subs | vals
        ab = abstains(reply)
        wrote = bool(row["question_wrote"])
        fam = it["family"]
        if fam in GOLD_FAMS:
            right = bool(gold) and all(g in rl for g in gold)
        elif fam == "broken_chain":
            lit = literals(row)
            right = ab and not any(v in rl for v in lit)
        elif fam == "statement_control":
            right = (row["stored_after_question_actual"]
                     == row["stored_after_setup_actual"])
        else:  # unreachable (schema gate)
            right = False
        if fam == "statement_control":
            wrong = False
        else:
            names_untaught = any((t in rl) and (t not in gold) for t in taught_all)
            wrong = (not right) and names_untaught and not all(g in rl for g in gold) and (not ab)
        per_item.append({"id": it["id"], "family": fam, "right": right,
                         "wrong": wrong, "question_wrote": wrote, "reply": reply})
    return per_item


def main():
    panel_path = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "panel.jsonl")
    rows_path = sys.argv[2] if len(sys.argv) > 2 else str(HERE / "base266.jsonl")
    items, rmap = load(panel_path, rows_path)
    per_item = score(items, rmap)
    print("id family right wrong wrote :: reply")
    for p in per_item:
        print(f"{p['id']} {p['family']} {int(p['right'])} {int(p['wrong'])} "
              f"{int(p['question_wrote'])} :: {p['reply']}")
    print("---- per family: N right wrong wrote other ----")
    for fam, n in EXPECTED.items():
        ps = [p for p in per_item if p["family"] == fam]
        r = sum(p["right"] for p in ps)
        w = sum(p["wrong"] for p in ps)
        q = sum(p["question_wrote"] for p in ps)
        print(f"{fam}: {n} {r} {w} {q} {n - r - w}")
    print(f"TOTAL: {len(per_item)} {sum(p['right'] for p in per_item)} "
          f"{sum(p['wrong'] for p in per_item)} {sum(p['question_wrote'] for p in per_item)}")


if __name__ == "__main__":
    main()
