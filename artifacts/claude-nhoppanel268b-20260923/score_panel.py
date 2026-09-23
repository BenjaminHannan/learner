#!/usr/bin/env python3
"""score_panel.py (sealed with the panel; builders use it unchanged).

Schema-checked scorer for nhoppanel268b. Any schema problem prints
SCHEMA-MISMATCH and exits 3 with no verdict (VOID, not FAIL).

Scoring on base138nb rows:
- right: every gold string appears (case-insensitive); bug /
  reverse_nochain / uncued_reverse also need "(worked out backwards)".
  abstain: reply contains "I don't know" or "I couldn't" and names no
  taught person. forward families: every gold string appears.
- right_names: every gold string appears, label or not (None for abstain
  and forward families).
- wrong: names a taught value or person not in gold, does not contain
  every gold string, and is not an abstain.
- question_wrote: passthrough from the row.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXPECT_FAMILIES = {"bug": 16, "reverse_nochain": 10, "forward_chain": 12,
                   "forward_1hop": 10, "uncued_reverse": 6, "abstain": 6}
LABEL_FAMILIES = {"bug", "reverse_nochain", "uncued_reverse"}
REQUIRED_FIELDS = {"id", "family", "setup", "question", "gold", "note"}
REQUIRED_ROW_FIELDS = {"id", "setup_replies", "question_reply", "question_stage",
                       "stored_after_setup_actual",
                       "stored_after_question_actual", "question_wrote"}
LABEL = "(worked out backwards)"


def fail(msg):
    print("SCHEMA-MISMATCH: %s" % msg)
    sys.exit(3)


def load_panel(path):
    items = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines()
             if x.strip()]
    if len(items) != 60:
        fail("panel has %d items, expected 60" % len(items))
    seen = set()
    famcount = Counter()
    for i, it in enumerate(items):
        if set(it.keys()) != REQUIRED_FIELDS:
            fail("item %d fields %s != %s"
                 % (i, sorted(it.keys()), sorted(REQUIRED_FIELDS)))
        if it["id"] in seen:
            fail("duplicate id %s" % it["id"])
        seen.add(it["id"])
        if it["family"] not in EXPECT_FAMILIES:
            fail("unexpected family %s" % it["family"])
        famcount[it["family"]] += 1
        if not isinstance(it["gold"], list):
            fail("%s gold not a list" % it["id"])
        if not isinstance(it["setup"], list) or not (2 <= len(it["setup"]) <= 4):
            fail("%s setup length out of range" % it["id"])
        if not isinstance(it["question"], str) or not it["question"]:
            fail("%s bad question" % it["id"])
    if dict(famcount) != dict(EXPECT_FAMILIES):
        fail("family counts %s != %s" % (dict(famcount), dict(EXPECT_FAMILIES)))
    if sorted(seen) != ["n268b-%03d" % i for i in range(1, 61)]:
        fail("id set mismatch")
    return items


def load_rows(path, panel_ids):
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines()
            if x.strip()]
    by_id = {}
    for r in rows:
        if set(r.keys()) != REQUIRED_ROW_FIELDS:
            fail("row %s fields %s != %s"
                 % (r.get("id"), sorted(r.keys()), sorted(REQUIRED_ROW_FIELDS)))
        by_id[r["id"]] = r
    if set(by_id.keys()) != set(panel_ids):
        fail("rows id set mismatch panel")
    return by_id


def taught_names(row):
    names = set()
    for t in row["stored_after_setup_actual"]:
        s, _r, v = t
        names.add(str(s))
        names.add(str(v))
    return {n for n in names if n.lower() not in ("you", "user", "")}


def is_abstain(reply, taught):
    t = reply.lower()
    if ("i don't know" not in t) and ("i couldn" not in t):
        return False
    return not any(n.lower() in t for n in taught)


def score(items, by_id):
    per_item = []
    for it in items:
        row = by_id[it["id"]]
        reply = str(row["question_reply"])
        rl = reply.lower()
        fam = it["family"]
        gold = list(it["gold"])
        taught = taught_names(row)
        gives_all = all(g.lower() in rl for g in gold)
        abst = is_abstain(reply, taught)
        right = False
        right_names = None
        if fam in LABEL_FAMILIES:
            right_names = bool(gives_all)
            right = bool(gives_all and LABEL in rl)
        elif fam in ("forward_chain", "forward_1hop"):
            right = bool(gives_all)
        elif fam == "abstain":
            right = bool(abst)
        wrong = False
        if not gives_all and not abst:
            for n in taught:
                nl = n.lower()
                if nl in rl and nl not in [g.lower() for g in gold]:
                    wrong = True
                    break
        per_item.append({"id": it["id"], "family": fam, "right": bool(right),
                         "right_names": right_names, "wrong": bool(wrong),
                         "question_wrote": bool(row["question_wrote"]),
                         "question_stage": str(row["question_stage"]),
                         "question_reply": reply})
    return per_item


def main(argv):
    panel = argv[1] if len(argv) > 1 else str(Path(__file__).resolve().parent / "panel.jsonl")
    rows = argv[2] if len(argv) > 2 else str(Path(__file__).resolve().parent / "base138nb.jsonl")
    out = argv[3] if len(argv) > 3 else None
    items = load_panel(panel)
    by_id = load_rows(rows, [x["id"] for x in items])
    per_item = score(items, by_id)
    fam = defaultdict(list)
    for p in per_item:
        fam[p["family"]].append(p)
    summary = {}
    for f, lst in fam.items():
        stages = Counter(x["question_stage"] for x in lst)
        summary[f] = {"n": len(lst),
                      "right": sum(1 for x in lst if x["right"]),
                      "right_names": sum(1 for x in lst if x["right_names"]),
                      "wrong": sum(1 for x in lst if x["wrong"]),
                      "question_wrote": sum(1 for x in lst if x["question_wrote"]),
                      "stages": dict(stages)}
    doc = {"per_item": per_item, "per_family": summary,
           "total": {"n": len(per_item),
                     "right": sum(1 for x in per_item if x["right"]),
                     "wrong": sum(1 for x in per_item if x["wrong"]),
                     "question_wrote": sum(1 for x in per_item if x["question_wrote"])}}
    s = json.dumps(doc, indent=1, ensure_ascii=False)
    if out:
        Path(out).write_text(s, encoding="utf-8")
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
