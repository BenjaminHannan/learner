#!/usr/bin/env python3
"""Merge 138n -- 239 conversation panel: changes file (NOT a grader).
Compares two transcripts written by scripts/claude_convpanel239_run.py and
writes the same format as
artifacts/claude-convpanel239-138m-20260922/changes-138m-vs-138l.json.
Prints counts only.

usage: claude_138n_conv239_changes.py BASE.jsonl NEW.jsonl base_label new_label OUT.json
"""
import json
import sys


def load(p):
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def main(a):
    base, new = load(a[0]), load(a[1])
    assert len(base) == len(new), (len(base), len(new))
    turns, by = [], {}
    prev = {}
    tot = {"changed": 0, "turns": 0, "reply_changed": 0,
           "stored_after_changed": 0, "stored_before_changed": 0}
    for i, (b, n) in enumerate(zip(base, new)):
        assert (b["id"], b["turn"]) == (n["id"], n["turn"])
        cid = b["id"]
        pb, pn = prev.get(cid, ([], []))
        rc = b["reply"] != n["reply"]
        sa = sorted(map(tuple, b["triples"] or [])) != sorted(map(tuple, n["triples"] or []))
        sb = sorted(map(tuple, pb)) != sorted(map(tuple, pn))
        ch = rc or sa or sb
        prev[cid] = (b["triples"] or [], n["triples"] or [])
        turns.append({"turn_number": i, "conv_id": cid, "turn_index": b["turn"],
                      "intent": b.get("intent"), "reply_changed": rc,
                      "stored_after_changed": sa, "stored_before_changed": sb,
                      "changed": ch})
        tot["turns"] += 1
        tot["changed"] += ch
        tot["reply_changed"] += rc
        tot["stored_after_changed"] += sa
        tot["stored_before_changed"] += sb
        f = by.setdefault(b.get("intent"), {"changed": 0, "turns": 0})
        f["changed"] += ch
        f["turns"] += 1
    tot["by_intent"] = {k: by[k] for k in sorted(by, key=str)}
    out = {"base": a[2], "new": a[3],
           "numbering": f"0..{len(base) - 1} in panel file order (conversation order, then turn order)",
           "stored_before_definition": "stored triples after the previous turn of the same conversation (empty for the first turn)",
           "totals": tot, "turns": turns}
    json.dump(out, open(a[4], "w", encoding="utf-8"), indent=1)
    print(json.dumps(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
