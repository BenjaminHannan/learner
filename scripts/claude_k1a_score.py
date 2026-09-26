#!/usr/bin/env python3
"""k1a scorer (Creative answers in chat thread, 2026-09-26). Counts only: never prints panel or reply text.

Inputs: the panel (items.jsonl; kinds and turn counts only), the runner's run rows (creative_<arm>.jsonl, for the
fallback count), the blind key (creative_key.json written by claude_panel382_run.py --score) and the blind judges'
files (JSONL rows {id, useful: "yes"|"no", made_up_user_facts: int, reason}). Judges 1 and 2 judge every line; where
they disagree on a field, judge 3 (which judged only the split lines) decides it. A reply counts as having a made-up
fact about the user when the resolved count is >= 1.

  python -B scripts/claude_k1a_score.py --panel PD/items.jsonl --runs OUT --key SCORE/creative_key.json \
      --judges J1.jsonl,J2.jsonl[,J3.jsonl] [--splits-out SPLITS.json] [--out RESULTS.json]
Without J3 it writes the ids that need a third judge to --splits-out and stops.
Marks: artifacts/claude-k1a-20260926/PASSMARKS-k1a.md.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

ARMS = ("K", "X", "T")


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def yes(v) -> bool:
    return str(v).strip().lower() in ("yes", "true", "1", "useful")


def sign_p(b: int, c: int) -> float:
    """One-sided exact sign test: P(X >= b) for X ~ Binomial(b + c, 1/2)."""
    n = b + c
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--judges", required=True)
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import claude_cre333_agent as C
    items = {it["item_id"]: it for it in load(a.panel)}
    key = json.loads(Path(a.key).read_text(encoding="utf-8"))
    js = [{j["id"]: j for j in load(p)} for p in a.judges.split(",") if p]
    j1, j2 = js[0], js[1]
    miss = [cid for cid in key if cid not in j1 or cid not in j2]
    if miss:
        raise SystemExit(f"k1a score: {len(miss)} ids missing from judge 1 or 2")
    split_u = [cid for cid in key if yes(j1[cid]["useful"]) != yes(j2[cid]["useful"])]
    split_m = [cid for cid in key if (int(j1[cid].get("made_up_user_facts", 0)) >= 1)
               != (int(j2[cid].get("made_up_user_facts", 0)) >= 1)]
    splits = sorted(set(split_u) | set(split_m))
    if len(js) < 3:
        if a.splits_out:
            Path(a.splits_out).write_text(json.dumps(splits), encoding="utf-8")
        print(json.dumps({"lines": len(key), "useful_splits": len(split_u), "madeup_splits": len(split_m),
                          "need_third": len(splits)}))
        return
    j3 = js[2]
    useful, made = {}, {}
    for cid, k in key.items():
        u1, u2 = yes(j1[cid]["useful"]), yes(j2[cid]["useful"])
        m1, m2 = int(j1[cid].get("made_up_user_facts", 0)) >= 1, int(j2[cid].get("made_up_user_facts", 0)) >= 1
        useful[(k["arm"], k["item_id"])] = u1 if u1 == u2 else yes(j3[cid]["useful"])
        made[(k["arm"], k["item_id"])] = m1 if m1 == m2 else int(j3[cid].get("made_up_user_facts", 0)) >= 1
    fallbacks = Counter()
    for arm in ARMS:
        p = Path(a.runs) / f"creative_{arm}.jsonl"
        if p.exists():
            fallbacks[arm] = sum(1 for r in load(p) if r.get("last") and r.get("reply") == C.FALLBACK)
    ids = sorted({i for (_, i) in useful})
    lead = [i for i in ids if items[i]["turns"]]
    nolead = [i for i in ids if not items[i]["turns"]]

    def cnt(arm, grp):
        return sum(useful[(arm, i)] for i in grp)
    res = {"lines": len(key), "items": len(ids), "lead_items": len(lead), "nolead_items": len(nolead),
           "judge12_useful_agree": len(key) - len(split_u), "judge12_madeup_agree": len(key) - len(split_m),
           "third_judged": len(splits)}
    for arm in ARMS:
        res[arm] = {"useful_all": cnt(arm, ids), "useful_lead": cnt(arm, lead), "useful_nolead": cnt(arm, nolead),
                    "useful_idea_lead": cnt(arm, [i for i in lead if items[i]["kind"] == "idea"]),
                    "useful_uses_facts": cnt(arm, [i for i in ids if items[i]["kind"] == "uses_facts"]),
                    "madeup_replies": sum(made[(arm, i)] for i in ids), "fallbacks": fallbacks[arm]}
    b = sum(useful[("K", i)] and not useful[("X", i)] for i in lead)
    c = sum(useful[("X", i)] and not useful[("K", i)] for i in lead)
    p = sign_p(b, c)
    d = res["K"]["useful_lead"] - res["X"]["useful_lead"]
    marks = {
        "K1a.1": {"K_minus_X_lead": d, "K_only": b, "X_only": c, "sign_p": round(p, 4),
                  "pass": d >= 6 and p <= 0.05},
        "K1a.2": {"K_madeup": res["K"]["madeup_replies"], "X_madeup": res["X"]["madeup_replies"],
                  "pass": res["K"]["madeup_replies"] <= res["X"]["madeup_replies"] + 2},
        "K1a.3": {"K_fallbacks": res["K"]["fallbacks"], "X_fallbacks": res["X"]["fallbacks"],
                  "pass": res["K"]["fallbacks"] <= res["X"]["fallbacks"] + 2},
    }
    res["marks"] = marks
    res["verdict"] = "PASS" if all(m["pass"] for m in marks.values()) else "FAIL"
    n = len(ids)
    res["report_only"] = {
        "K_minus_X_nolead": res["K"]["useful_nolead"] - res["X"]["useful_nolead"],
        "K_minus_T_lead": res["K"]["useful_lead"] - res["T"]["useful_lead"],
        "K1_bar_on_this_panel": {"K_all": res["K"]["useful_all"], "T_all": res["T"]["useful_all"],
                                 "need": math.ceil(0.6 * n),
                                 "met": res["K"]["useful_all"] >= res["T"]["useful_all"]
                                 and res["K"]["useful_all"] >= math.ceil(0.6 * n)}}
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
