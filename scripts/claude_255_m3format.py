#!/usr/bin/env python3
"""Exp 255 M3: changes file in the 239 panel format (as in
artifacts/claude-convpanel239-138m-20260922/changes-138m-vs-138l.json).
Written after the seal (driver-only addition; reported). Ungraded.

usage: claude_255_m3format.py <base.jsonl> <new.jsonl> <out.json> <base_label> <new_label>
"""
import json
import sys
from collections import OrderedDict


def load(p):
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def main(a):
    base, new = load(a[0]), load(a[1])
    assert [(r["id"], r["turn"]) for r in base] == \
        [(r["id"], r["turn"]) for r in new]
    turns, by = [], {}
    prev_b = prev_n = None
    for i, (b, n) in enumerate(zip(base, new)):
        if n["turn"] == 0:
            prev_b = prev_n = []
        rc = b["reply"] != n["reply"] or b["error"] != n["error"]
        sa = b["triples"] != n["triples"]
        sb = prev_b != prev_n
        ch = rc or sa or sb
        turns.append({"turn_number": i, "conv_id": n["id"],
                      "turn_index": n["turn"], "intent": n["intent"],
                      "reply_changed": rc, "stored_after_changed": sa,
                      "stored_before_changed": sb, "changed": ch})
        e = by.setdefault(n["intent"], {"changed": 0, "turns": 0})
        e["turns"] += 1
        e["changed"] += int(ch)
        prev_b, prev_n = b["triples"], n["triples"]
    out = OrderedDict(
        base=a[3], new=a[4],
        numbering="0..%d in panel file order (conversation order, then "
                  "turn order)" % (len(turns) - 1),
        stored_before_definition="stored triples after the previous turn of "
                                 "the same conversation (empty for the first "
                                 "turn)",
        totals={"changed": sum(t["changed"] for t in turns),
                "turns": len(turns),
                "reply_changed": sum(t["reply_changed"] for t in turns),
                "stored_after_changed": sum(t["stored_after_changed"]
                                            for t in turns),
                "stored_before_changed": sum(t["stored_before_changed"]
                                             for t in turns),
                "by_intent": dict(sorted(by.items()))},
        turns=turns)
    json.dump(out, open(a[2], "w"), indent=1)
    print(json.dumps(out["totals"]))


if __name__ == "__main__":
    main(sys.argv[1:])
