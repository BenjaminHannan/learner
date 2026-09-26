#!/usr/bin/env python3
"""lis-320 extra counts and verdict (reading thread, 2026-09-26). Marks: artifacts/claude-lis320-20260926/PASSMARKS.md.

extra:   python claude_lis320_score.py extra --panel P --reads R --out X.json
         saves = claude_lis319_fullclaim.saved_facts at T 0.995 (unchanged compiler). Counts only:
         former_as_current  a save whose owner and value match a "former" item of its row and no current fact (lis-319f);
         wrong_person       on backref rows (kind "backref" or a gold fact with needs_history), a save whose value equals a
                            gold fact's value while the owner is not that fact's owner, and which matches no gold fact
                            (owner + value); relation names are ignored;
         ambiguous_saves    saves on lookalike rows with reason "ambiguous";
         panel counts for validity: correction_gold, backref_rows, former_items, ambiguous_rows.
verdict: python claude_lis320_score.py verdict --old-k OK.json --new-k NK.json --old-x OX.json --new-x NX.json
         (K = claude_lis319k_score.py final on each reader's reads, same pairs and verdicts; X = extra)
selftest: python claude_lis320_score.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis317_gates import e2e_match, n  # noqa: E402
from claude_lis319_fullclaim import load, saved_facts  # noqa: E402

T = 0.995


def is_backref(row):
    return row.get("kind") == "backref" or any(g.get("needs_history") for g in row.get("facts") or [])


def extra_counts(panel, reads):
    rd = {r["id"]: r for r in reads}
    c = Counter({k: 0 for k in ("rows", "missing_rows", "correction_gold", "backref_rows", "former_items",
                                "ambiguous_rows", "former_as_current", "wrong_person", "ambiguous_saves")})
    for row in panel:
        gold, former = row.get("facts") or [], row.get("former") or []
        amb = row.get("kind") == "lookalike" and row.get("reason") == "ambiguous"
        c["rows"] += 1
        c["correction_gold"] += sum(bool(g.get("correction")) for g in gold)
        c["backref_rows"] += is_backref(row)
        c["former_items"] += len(former)
        c["ambiguous_rows"] += amb
        r = rd.get(row["id"])
        if r is None:
            c["missing_rows"] += 1
            continue
        for f in saved_facts(row, r, T):
            right = any(e2e_match(f, g) for g in gold)
            c["former_as_current"] += any(e2e_match(f, g) for g in former) and not right
            c["wrong_person"] += (is_backref(row) and not right
                                  and any(n(g["value"]) == n(f.get("value")) for g in gold))
            c["ambiguous_saves"] += amb
    return dict(c)


def extra(a):
    out = extra_counts(load(a.panel), load(a.reads)) | {"threshold": T}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out))


def decide(ok, nk, ox, nx):
    m = {"R1": nk["saved_right_full"] >= math.floor(0.95 * ok["saved_right_full"]),
         "R2": nk["wrong_turns_full"] <= ok["wrong_turns_full"] + 2,
         "R3": nk["correction_right"] >= ok["correction_right"] - 2,
         "R4": nx["former_as_current"] <= max(1, ox["former_as_current"]),
         "R5": nx["wrong_person"] <= ox["wrong_person"] + 1,
         "R6": nx["ambiguous_saves"] <= ox["ambiguous_saves"] and nk["lookalike_saves"] <= ok["lookalike_saves"] + 2}
    valid = (ox["correction_gold"] >= 40 and ox["backref_rows"] >= 50 and ox["former_items"] >= 30
             and ox["ambiguous_rows"] >= 10 and ok["saved_right_full"] >= 60)
    wrong = nk["saved_right_full"] < 0.90 * ok["saved_right_full"] or nk["wrong_turns_full"] > ok["wrong_turns_full"] + 5
    v = "INCONCLUSIVE" if not valid else ("PASS" if all(m.values()) else "FAIL")
    return {"verdict": v, "valid": valid, "proved_wrong": valid and wrong, **m}


def verdict(a):
    ok, nk, ox, nx = (json.loads(Path(p).read_text()) for p in (a.old_k, a.new_k, a.old_x, a.new_x))
    keys_k = ("saved_right_full", "wrong_turns_full", "saved_wrong_full", "correction_right", "correction_gold",
              "stale_saves", "lookalike_saves")
    keys_x = ("former_as_current", "wrong_person", "ambiguous_saves", "backref_rows", "former_items", "ambiguous_rows")
    print(json.dumps(decide(ok, nk, ox, nx) | {k: [ok[k], nk[k]] for k in keys_k} | {k: [ox[k], nx[k]] for k in keys_x},
                     indent=1))


def selftest(_a):
    panel = [
        {"id": "d1-t0", "kind": "ordinary", "turn": "my sister Lenka is 19 and my friend Tamsin is 20", "prev_reply": "",
         "facts": [{"owner": "Lenka", "relation": "age", "value": "19"}], "former": [], "replaced": []},
        {"id": "d1-t1", "kind": "backref", "turn": "oh and she works at Pellwood now", "prev_reply": "",
         "facts": [{"owner": "Lenka", "relation": "works_at", "value": "Pellwood", "needs_history": True}],
         "former": [], "replaced": []},
        {"id": "d1-t2", "kind": "former", "turn": "i used to live in Garrow, now Tolby", "prev_reply": "",
         "facts": [{"owner": "USER", "relation": "lives_in", "value": "Tolby"}],
         "former": [{"owner": "USER", "relation": "lives_in", "value": "Garrow"}], "replaced": []},
        {"id": "d1-t3", "kind": "lookalike", "reason": "ambiguous", "turn": "she's 21 now", "prev_reply": "",
         "facts": [], "former": [], "replaced": []}]

    def rd(i, facts):
        return {"id": i, "frame": {"facts": facts}, "conf": [1.0] * len(facts)}
    reads = [rd("d1-t1", [{"owner": "Tamsin", "rel": "employer", "value": "Pellwood", "mode": "ASSERT"}]),
             rd("d1-t2", [{"owner": "me", "rel": "city", "value": "Garrow", "mode": "ASSERT"},
                          {"owner": "me", "rel": "city", "value": "Tolby", "mode": "ASSERT"}]),
             rd("d1-t3", [{"owner": "Tamsin", "rel": "age", "value": "21", "mode": "ASSERT"}])]
    import claude_lis300_compiler as CMP
    orig = CMP.check_fact
    CMP.check_fact = lambda f, t, p: None   # the compiler is not under test here
    try:
        x = extra_counts(panel, reads)
    finally:
        CMP.check_fact = orig
    ok = [x["wrong_person"] == 1, x["former_as_current"] == 1, x["ambiguous_saves"] == 1, x["backref_rows"] == 1,
          x["former_items"] == 1, x["ambiguous_rows"] == 1]
    base = {"saved_right_full": 100, "wrong_turns_full": 5, "correction_right": 20, "lookalike_saves": 1}
    bx = {"former_as_current": 0, "wrong_person": 2, "ambiguous_saves": 0, "correction_gold": 50, "backref_rows": 60,
          "former_items": 40, "ambiguous_rows": 10}
    ok.append(decide(base, dict(base, saved_right_full=95), bx, bx)["verdict"] == "PASS")
    ok.append(decide(base, dict(base, saved_right_full=94), bx, bx)["verdict"] == "FAIL")
    ok.append(decide(base, base, bx, dict(bx, wrong_person=4))["R5"] is False)
    ok.append(decide(base, base, bx, dict(bx, ambiguous_saves=1))["R6"] is False)
    ok.append(decide(base, base, bx, dict(bx, former_as_current=1))["R4"] is True)
    ok.append(decide(base, base, dict(bx, ambiguous_rows=9), bx)["verdict"] == "INCONCLUSIVE")
    ok.append(decide(base, dict(base, saved_right_full=89), bx, bx)["proved_wrong"] is True)
    print(json.dumps(x))
    print("LIS320-SCORE-SELFTEST " + ("PASS" if all(ok) else "FAIL " + str(ok)))
    return 0 if all(ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extra", "verdict", "selftest"])
    for k in ("--panel", "--reads", "--out", "--old-k", "--new-k", "--old-x", "--new-x"):
        ap.add_argument(k)
    a = ap.parse_args()
    return {"extra": extra, "verdict": verdict, "selftest": selftest}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
