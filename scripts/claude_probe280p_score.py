#!/usr/bin/env python3
"""Exp 280p held-out probe: mechanical-owner score for chatweak-format runs.

  chatweak <run260> <run280b> <run281> <run282b> <run280m> <out>

Same mechanical rule as the sealed scripts/claude_join280p_score.py panel
mode: the owner of each turn is the single piece arm (280b, 281 or 282b)
whose reply, writes or store differ from 260's, or 260 if none differs.
Two or more differing pieces on one turn = overlap = FAIL.
Prints ids of misses/overlaps/writes, never item text.
"""

import json
import sys


def _differs(a, b):
    """True if reply, writes or store differ between two run rows."""
    return (a.get("reply") != b.get("reply")
            or a.get("ev") != b.get("ev")
            or a.get("triples") != b.get("triples"))


def mech_owner(r260, r280b, r281, r282b):
    """Return (owner, overlap). Owner in {260,280b,281,282b} or OVERLAP."""
    diffs = []
    if _differs(r280b, r260):
        diffs.append("280b")
    if _differs(r281, r260):
        diffs.append("281")
    if _differs(r282b, r260):
        diffs.append("282b")
    if len(diffs) == 0:
        return "260", False
    if len(diffs) == 1:
        return diffs[0], False
    return "OVERLAP", True


def main(argv):
    assert argv[1] == "chatweak", "mode must be chatweak"
    r260p, r280bp, r281p, r282bp, r280mp, outp = argv[2:8]
    runs = {}
    for tag, p in (("260", r260p), ("280b", r280bp), ("281", r281p),
                   ("282b", r282bp), ("280m", r280mp)):
        runs[tag] = {r["id"]: r for r in json.load(open(p))}
    rows = []
    for did, d260 in runs["260"].items():
        try:
            arms = {t: runs[t][did] for t in runs}
        except KeyError as e:
            print(f"SCORE-ERROR: dialog {e} missing from a run file")
            raise SystemExit(2)
        n = len(arms["280m"]["rows"])
        for i in range(n):
            r260 = arms["260"]["rows"][i]
            r280b = arms["280b"]["rows"][i]
            r281 = arms["281"]["rows"][i]
            r282b = arms["282b"]["rows"][i]
            r280m = arms["280m"]["rows"][i]
            owner, overlap = mech_owner(r260, r280b, r281, r282b)
            if overlap:
                agree = same_reply = same_ev = same_store = False
            else:
                ro = arms[owner]["rows"][i]
                same_reply = r280m["reply"] == ro["reply"]
                same_ev = r280m.get("ev") == ro.get("ev")
                same_store = r280m.get("triples") == ro.get("triples")
                agree = same_reply and same_ev and same_store
            turn = r260.get("turn", "")
            rows.append({
                "id": did, "turn_idx": i,
                "owner": owner, "overlap": overlap, "agree": agree,
                "same_reply": same_reply, "same_ev": same_ev,
                "same_store": same_store,
                "writes280m": r280m.get("ev", 0),
                "is_question": str(turn).rstrip().endswith("?"),
                "store_diff_260": (r280m.get("triples")
                                   != r260.get("triples")),
                "ev_diff_260": r280m.get("ev") != r260.get("ev"),
            })
    own_counts = {}
    for r in rows:
        own_counts.setdefault(r["owner"], 0)
        own_counts[r["owner"]] += 1
    n_all = len(rows)
    n_agree = sum(1 for r in rows if r["agree"])
    overlaps = [f"{r['id']}#{r['turn_idx']}" for r in rows if r["overlap"]]
    moved = [f"{r['id']}#{r['turn_idx']}(->{r['owner']})"
             for r in rows if not r["agree"]]
    qwrites = [f"{r['id']}#{r['turn_idx']}" for r in rows
               if r["is_question"] and r["writes280m"]]
    allwrites = [f"{r['id']}#{r['turn_idx']}" for r in rows
                 if r["writes280m"]]
    storediffs = [f"{r['id']}#{r['turn_idx']}" for r in rows
                  if r["store_diff_260"]]
    ok = n_agree == n_all and not qwrites and not overlaps
    res = {"n_dialogs": len(runs["260"]), "n_turns": n_all,
           "agree": {"n": n_agree, "denom": n_all, "moved_ids": moved},
           "overlaps": overlaps,
           "question_writes280m": qwrites,
           "all_writes280m": allwrites,
           "store_diffs_280m_vs_260": storediffs,
           "mech_owners": own_counts}
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    print(f"dialogs={len(runs['260'])} turns={n_all} agree={n_agree}/{n_all}")
    print(f"mech_owners={own_counts}")
    print(f"moved={moved}")
    print(f"overlaps={overlaps}")
    print(f"280m question writes={qwrites}; all writes={allwrites}; "
          f"store diffs vs 260={storediffs}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
