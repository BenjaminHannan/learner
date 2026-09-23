#!/usr/bin/env python3
"""score_panel.py (sealed with the panel; builder uses it unchanged)."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXPECT_FAMILIES = {"have_true": 10, "have_unknown": 8, "live": 10, "work": 8,
                   "born": 6, "is_multiword": 8, "is_of_form": 6,
                   "taken_back": 6, "is_single_control": 8, "wh_control": 8,
                   "statement_control": 7}
EXPECT_LABELS = {"yes", "no", "unknown", "control"}
REQUIRED_FIELDS = {"id", "family", "setup", "question", "expect", "gold", "note"}
REQUIRED_ROW_FIELDS = {"id", "setup_replies", "question_reply", "question_stage",
                       "stored_after_setup_actual", "stored_after_question_actual",
                       "question_wrote"}


def fail(msg):
    print(f"SCHEMA-MISMATCH: {msg}")
    sys.exit(3)


def load_panel(path):
    items = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(items) != 85:
        fail(f"panel has {len(items)} items, expected 85")
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
        if it["expect"] not in EXPECT_LABELS:
            fail(f"unexpected expect {it['expect']}")
        if not isinstance(it["gold"], list):
            fail(f"{it['id']} gold not a list")
        if not isinstance(it["setup"], list) or not (1 <= len(it["setup"]) <= 4):
            fail(f"{it['id']} setup length out of range")
        if not isinstance(it["question"], str) or not it["question"]:
            fail(f"{it['id']} bad question")
        if not isinstance(it["note"], str):
            fail(f"{it['id']} bad note")
    if dict(famcount) != dict(EXPECT_FAMILIES):
        fail(f"family counts {dict(famcount)} != {dict(EXPECT_FAMILIES)}")
    expect_ids = [f"y293-{i:03d}" for i in range(1, 86)]
    if sorted(seen) != expect_ids:
        fail("id set mismatch")
    return items


def load_rows(path, panel_ids):
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(rows) != 85:
        fail(f"rows has {len(rows)} rows, expected 85")
    by_id = {}
    for r in rows:
        if set(r.keys()) != REQUIRED_ROW_FIELDS:
            fail(f"row {r.get('id')} fields {sorted(r.keys())} != {sorted(REQUIRED_ROW_FIELDS)}")
        by_id[r["id"]] = r
    if set(by_id.keys()) != set(panel_ids):
        fail("rows id set mismatch panel")
    return by_id


def starts_yes(reply):
    return reply.lstrip().lower().startswith("yes")


def starts_no(reply):
    return reply.lstrip().lower().startswith("no")


def contains_all(reply, gold):
    rl = reply.lower()
    return all(str(g).lower() in rl for g in gold)


def is_unknown_reply(reply):
    rl = reply.lower()
    has = ("don't know" in rl) or ("not that i know" in rl)
    return has and (not starts_yes(reply)) and (not starts_no(reply))


def score(items, by_id, base_by_id=None):
    per_item = []
    for it in items:
        row = by_id[it["id"]]
        reply = str(row["question_reply"])
        expect = it["expect"]
        gold = list(it["gold"])
        right = False
        if expect == "yes":
            right = starts_yes(reply) and contains_all(reply, gold)
        elif expect == "no":
            right = starts_no(reply) and contains_all(reply, gold)
        elif expect == "unknown":
            right = is_unknown_reply(reply)
        elif expect == "control":
            if base_by_id is None or row["id"] not in base_by_id:
                right = True
            else:
                b = base_by_id[row["id"]]
                right = (str(row["question_reply"]) == str(b["question_reply"])
                         and [list(x) for x in row["stored_after_setup_actual"]] == [list(x) for x in b["stored_after_setup_actual"]]
                         and [list(x) for x in row["stored_after_question_actual"]] == [list(x) for x in b["stored_after_question_actual"]])
        wrong = False
        if expect == "yes":
            wrong = starts_no(reply)
        elif expect == "no":
            wrong = starts_yes(reply)
        elif expect == "unknown":
            wrong = starts_yes(reply) or starts_no(reply)
        elif expect == "control":
            wrong = False
        per_item.append({"id": it["id"], "family": it["family"], "expect": expect,
                         "right": bool(right), "wrong": bool(wrong),
                         "question_wrote": bool(row["question_wrote"]),
                         "question_stage": str(row.get("question_stage", ""))})
    return per_item


def main(argv):
    panel = argv[1] if len(argv) > 1 else str(Path(__file__).resolve().parent / "panel.jsonl")
    rows = argv[2] if len(argv) > 2 else str(Path(__file__).resolve().parent / "base138nb.jsonl")
    out = argv[3] if len(argv) > 3 else None
    items = load_panel(panel)
    by_id = load_rows(rows, [x["id"] for x in items])
    base_by_id = None
    try:
        base_path = str(Path(__file__).resolve().parent / "base138nb.jsonl")
        if str(Path(rows).resolve()) != str(Path(base_path).resolve()):
            brows = [json.loads(x) for x in Path(base_path).read_text(encoding="utf-8").splitlines() if x.strip()]
            base_by_id = {r["id"]: r for r in brows}
    except Exception:
        base_by_id = None
    per_item = score(items, by_id, base_by_id)
    fam = defaultdict(list)
    for p in per_item:
        fam[p["family"]].append(p)
    summary = {}
    for f, lst in fam.items():
        stages = Counter(x["question_stage"] for x in lst)
        summary[f] = {"n": len(lst), "right": sum(1 for x in lst if x["right"]),
                      "wrong": sum(1 for x in lst if x["wrong"]),
                      "question_wrote": sum(1 for x in lst if x["question_wrote"]),
                      "stages": dict(stages)}
    total = {"n": len(per_item), "right": sum(1 for x in per_item if x["right"]),
             "wrong": sum(1 for x in per_item if x["wrong"]),
             "question_wrote": sum(1 for x in per_item if x["question_wrote"])}
    doc = {"per_item": per_item, "per_family": summary, "total": total}
    s = json.dumps(doc, indent=1, ensure_ascii=False)
    if out:
        Path(out).write_text(s, encoding="utf-8")
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
