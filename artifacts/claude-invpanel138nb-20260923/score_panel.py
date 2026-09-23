#!/usr/bin/env python3
"""score_panel.py (sealed with the panel; builder uses it unchanged)."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXPECT_FAMILIES = {"whose_R": 14, "lives_born": 10, "has_as": 6, "verb_backwards": 10,
                   "my_backwards": 4, "no_match": 8, "unknown_value": 4,
                   "forward_control": 10, "teach_control": 4}
BACKWARDS_SCORED = {"whose_R", "lives_born", "has_as", "verb_backwards", "my_backwards"}
REQUIRED_FIELDS = {"id", "family", "setup", "question", "gold", "backwards", "stored_after_setup", "note"}
REQUIRED_ROW_FIELDS = {"id", "setup_replies", "question_reply", "stored_after_setup_actual",
                       "stored_after_question_actual", "question_wrote"}


def fail(msg):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def load_panel(path):
    items = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(items) != 70:
        fail(f"panel has {len(items)} items, expected 70")
    seen = set()
    famcount = Counter()
    for i, it in enumerate(items):
        if set(it.keys()) != REQUIRED_FIELDS:
            fail(f"item {i} fields {sorted(it.keys())} != {sorted(REQUIRED_FIELDS)}")
        if it["id"] in seen:
            fail(f"duplicate id {it['id']}")
        seen.add(it["id"])
        if it["family"] not in EXPECT_FAMILIES:
            fail(f"unexpected family {it['family']}")
        famcount[it["family"]] += 1
        if not isinstance(it["gold"], list):
            fail(f"{it['id']} gold not a list")
        if not isinstance(it["setup"], list) or not (1 <= len(it["setup"]) <= 3):
            fail(f"{it['id']} setup length out of range")
        if not isinstance(it["question"], str) or not it["question"]:
            fail(f"{it['id']} bad question")
        if not isinstance(it["backwards"], bool):
            fail(f"{it['id']} backwards not bool")
        if not isinstance(it["stored_after_setup"], list):
            fail(f"{it['id']} stored_after_setup not a list")
    if dict(famcount) != dict(EXPECT_FAMILIES):
        fail(f"family counts {dict(famcount)} != {dict(EXPECT_FAMILIES)}")
    expect_ids = [f"i138nb-{i:03d}" for i in range(1, 71)]
    if sorted(seen) != expect_ids:
        fail("id set mismatch")
    return items


def load_rows(path, panel_ids):
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    by_id = {}
    for r in rows:
        if set(r.keys()) != REQUIRED_ROW_FIELDS:
            fail(f"row {r.get('id')} fields {sorted(r.keys())} != {sorted(REQUIRED_ROW_FIELDS)}")
        by_id[r["id"]] = r
    if set(by_id.keys()) != set(panel_ids):
        fail("rows id set mismatch panel")
    return by_id


def is_abstain(reply):
    t = reply.lower()
    return ("i don't know" in t) or ("i couldn" in t)


def names_taught_in_reply(reply, taught_names, gold):
    t = reply.lower()
    for n in taught_names:
        nl = str(n).lower()
        if not nl or nl in ("you", "user"):
            continue
        if nl in t and not all(g.lower() in t for g in gold):
            return True
    return False


def taught_names_for_item(it):
    names = set()
    for s, r, v in it["stored_after_setup"]:
        names.add(str(s))
        names.add(str(v))
    return names


def parse_question_triple(q):
    # Teach-shaped question turn "X's R is Y." -> [X, R, Y]; None if not parseable.
    import re
    m = re.match(r"^\s*(.+?)'s\s+([A-Za-z]+)\s+is\s+(.+?)\.\s*$", q)
    if not m:
        return None
    return [m.group(1).strip(), m.group(2).strip(), m.group(3).strip()]


def score(items, by_id):
    per_item = []
    for it in items:
        row = by_id[it["id"]]
        reply = str(row["question_reply"])
        rl = reply.lower()
        fam = it["family"]
        gold = list(it["gold"])
        taught = taught_names_for_item(it)
        right = False
        right_names = None
        if fam in BACKWARDS_SCORED:
            names_ok = all(g.lower() in rl for g in gold)
            right_names = bool(names_ok)
            label_ok = "(worked out backwards)" in rl
            if names_ok and label_ok:
                if fam == "my_backwards":
                    right = ("your" in rl) or ("you" in rl)
                else:
                    right = True
        elif fam == "forward_control":
            right = all(g.lower() in rl for g in gold)
        elif fam in ("no_match", "unknown_value"):
            taught_subjects = {str(s) for s, _r, _v in it["stored_after_setup"]}
            right = is_abstain(reply) and not any(
                s.lower() in rl for s in taught_subjects if str(s).lower() not in ("you", "user"))
        elif fam == "teach_control":
            qt = parse_question_triple(it["question"])
            actual = [list(x) for x in row["stored_after_question_actual"]]
            setup = [list(x) for x in it["stored_after_setup"]]
            if qt is None:
                right = False
            else:
                right = (len(actual) == len(setup) + 1 and qt in actual
                         and all(s in actual for s in setup))
        wrong = False
        if gold or fam in ("no_match", "unknown_value"):
            gives_all = all(g.lower() in rl for g in gold) if gold else False
            if not gives_all and not is_abstain(reply):
                t = rl
                for n in taught:
                    nl = str(n).lower()
                    if nl in ("you", "user", ""):
                        continue
                    if nl in t and nl not in [g.lower() for g in gold]:
                        wrong = True
                        break
        per_item.append({"id": it["id"], "family": fam, "right": bool(right),
                         "right_names": right_names, "wrong": bool(wrong),
                         "question_wrote": bool(row["question_wrote"]),
                         "question_reply": reply})
    return per_item


def main(argv):
    panel = argv[1] if len(argv) > 1 else str(Path(__file__).resolve().parent / "panel.jsonl")
    rows = argv[2] if len(argv) > 2 else str(Path(__file__).resolve().parent / "base138n.jsonl")
    out = argv[3] if len(argv) > 3 else None
    items = load_panel(panel)
    by_id = load_rows(rows, [x["id"] for x in items])
    per_item = score(items, by_id)
    fam = defaultdict(list)
    for p in per_item:
        fam[p["family"]].append(p)
    summary = {}
    for f, lst in fam.items():
        summary[f] = {"n": len(lst), "right": sum(1 for x in lst if x["right"]),
                      "right_names": sum(1 for x in lst if x["right_names"]),
                      "wrong": sum(1 for x in lst if x["wrong"]),
                      "question_wrote": sum(1 for x in lst if x["question_wrote"])}
    doc = {"per_item": per_item, "per_family": summary,
           "total": {"n": len(per_item), "right": sum(1 for x in per_item if x["right"]),
                     "wrong": sum(1 for x in per_item if x["wrong"]),
                     "question_wrote": sum(1 for x in per_item if x["question_wrote"])}}
    s = json.dumps(doc, indent=1, ensure_ascii=False)
    if out:
        Path(out).write_text(s, encoding="utf-8")
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
