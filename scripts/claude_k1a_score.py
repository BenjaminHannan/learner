#!/usr/bin/env python3
"""k1a scorer (Creative answers in chat thread, 2026-09-26). Counts only: never prints panel or reply text.

Inputs: the panel (items.jsonl; kinds and turn counts only), the runner's run rows (creative_<arm>.jsonl, for the
fallback and bare-list-ending counts), the blind key and the blind judges' files (JSONL rows {id, useful: "yes"|"no",
made_up_user_facts: int, reason}). Judges 1 and 2 judge every line; where they disagree on a field, judge 3 (which
judged only the split lines) decides it. A reply counts as having a made-up fact about the user when the resolved
count is >= 1.

Step 1, one verdict per distinct reply (arms that wrote the same reply to the same item get the same verdict, so
judge noise can't split them):
  python -B scripts/claude_k1a_score.py --dedupe SCORE     (reads SCORE/creative_judge.jsonl + creative_key.json from
      claude_panel382_run.py --score; writes SCORE/creative_judge_u.jsonl, ids U0000.., shuffled with seed 3823, and
      SCORE/creative_key_u.json {uid: [{arm, item_id}, ...]}; prints counts only)
Step 2, after judges 1 and 2 (and 3 on the splits) judged creative_judge_u.jsonl:
  python -B scripts/claude_k1a_score.py --panel PD/items.jsonl --runs OUT --key SCORE/creative_key_u.json \
      --judges J1.jsonl,J2.jsonl[,J3.jsonl] [--splits-out SPLITS.json] [--out RESULTS.json]
Without J3 it writes the ids that need a third judge to --splits-out and stops.
Arms: K (k1a), X (0.2c's writer), B (k1b), KB and KB0 (report only), T (plain 1B). Missing arms are skipped, except
that K, X and T are required and B is required for the K1b marks.
Marks: artifacts/claude-k1a-20260926/PASSMARKS-k1a.md.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

ARMS = ("K", "X", "B", "KB", "KB0", "T")
BARE_END = re.compile(r"(?:^|\n)\s*\d+[.)]\s*$")   # reply ends on a list number with nothing after it


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


def dedupe(score_dir: str) -> None:
    d = Path(score_dir)
    rows = load(d / "creative_judge.jsonl")
    key = json.loads((d / "creative_key.json").read_text(encoding="utf-8"))
    groups: dict = {}
    for r in rows:
        k = key[r["id"]]
        body = {f: r[f] for f in r if f != "id"}
        g = groups.setdefault((k["item_id"], r["reply"]), {"body": body, "who": []})
        g["who"].append({"arm": k["arm"], "item_id": k["item_id"]})
    pool = sorted(groups.values(), key=lambda g: (g["who"][0]["item_id"], sorted(w["arm"] for w in g["who"])))
    random.Random(3823).shuffle(pool)
    ukey = {}
    with open(d / "creative_judge_u.jsonl", "w", encoding="utf-8") as fh:
        for n, g in enumerate(pool):
            uid = f"U{n:04d}"
            ukey[uid] = g["who"]
            fh.write(json.dumps(dict(id=uid, **g["body"]), ensure_ascii=False) + "\n")
    (d / "creative_key_u.json").write_text(json.dumps(ukey, indent=1), encoding="utf-8")
    print(json.dumps({"lines": len(rows), "distinct_lines": len(pool),
                      "shared_by_2plus_arms": sum(len(g["who"]) > 1 for g in pool)}))


def pair_mark(useful, a1, a2, grp):
    b = sum(useful[(a1, i)] and not useful[(a2, i)] for i in grp)
    c = sum(useful[(a2, i)] and not useful[(a1, i)] for i in grp)
    return b, c, sign_p(b, c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dedupe", default="")
    ap.add_argument("--panel")
    ap.add_argument("--runs")
    ap.add_argument("--key")
    ap.add_argument("--judges")
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.dedupe:
        dedupe(a.dedupe)
        return
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import claude_cre333_agent as C
    items = {it["item_id"]: it for it in load(a.panel)}
    key = json.loads(Path(a.key).read_text(encoding="utf-8"))
    key = {cid: (v if isinstance(v, list) else [v]) for cid, v in key.items()}
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
    miss3 = [cid for cid in splits if cid not in j3]
    if miss3:
        raise SystemExit(f"k1a score: {len(miss3)} split ids missing from judge 3")
    useful, made = {}, {}
    for cid, who in key.items():
        u1, u2 = yes(j1[cid]["useful"]), yes(j2[cid]["useful"])
        m1, m2 = int(j1[cid].get("made_up_user_facts", 0)) >= 1, int(j2[cid].get("made_up_user_facts", 0)) >= 1
        u = u1 if u1 == u2 else yes(j3[cid]["useful"])
        m = m1 if m1 == m2 else int(j3[cid].get("made_up_user_facts", 0)) >= 1
        for k in who:
            useful[(k["arm"], k["item_id"])] = u
            made[(k["arm"], k["item_id"])] = m
    arms = [x for x in ARMS if any(k[0] == x for k in useful)]
    for need in ("K", "X", "T"):
        if need not in arms:
            raise SystemExit(f"k1a score: arm {need} missing")
    ids = sorted({i for (_, i) in useful})
    for x in arms:
        if any((x, i) not in useful for i in ids):
            raise SystemExit(f"k1a score: arm {x} lacks some items")
    fallbacks, bare = Counter(), Counter()
    for x in arms:
        p = Path(a.runs) / f"creative_{x}.jsonl"
        if p.exists():
            last = [r for r in load(p) if r.get("last")]
            fallbacks[x] = sum(1 for r in last if r.get("reply") == C.FALLBACK)
            bare[x] = sum(1 for r in last if BARE_END.search(r.get("reply") or ""))
    lead = [i for i in ids if items[i]["turns"]]
    nolead = [i for i in ids if not items[i]["turns"]]

    def cnt(arm, grp):
        return sum(useful[(arm, i)] for i in grp)
    res = {"lines": len(key), "items": len(ids), "lead_items": len(lead), "nolead_items": len(nolead),
           "judge12_useful_agree": len(key) - len(split_u), "judge12_madeup_agree": len(key) - len(split_m),
           "third_judged": len(splits)}
    for x in arms:
        res[x] = {"useful_all": cnt(x, ids), "useful_lead": cnt(x, lead), "useful_nolead": cnt(x, nolead),
                  "useful_idea_lead": cnt(x, [i for i in lead if items[i]["kind"] == "idea"]),
                  "useful_uses_facts": cnt(x, [i for i in ids if items[i]["kind"] == "uses_facts"]),
                  "madeup_replies": sum(made[(x, i)] for i in ids), "fallbacks": fallbacks[x],
                  "bare_list_endings": bare[x]}
    b, c, p = pair_mark(useful, "K", "X", lead)
    d = res["K"]["useful_lead"] - res["X"]["useful_lead"]
    marks = {
        "K1a.1": {"K_minus_X_lead": d, "K_only": b, "X_only": c, "sign_p": round(p, 4),
                  "pass": d >= 6 and p <= 0.05},
        "K1a.2": {"K_madeup": res["K"]["madeup_replies"], "X_madeup": res["X"]["madeup_replies"],
                  "pass": res["K"]["madeup_replies"] <= res["X"]["madeup_replies"] + 2},
        "K1a.3": {"K_fallbacks": res["K"]["fallbacks"], "X_fallbacks": res["X"]["fallbacks"],
                  "pass": res["K"]["fallbacks"] <= res["X"]["fallbacks"] + 2},
    }
    res["marks_k1a"] = marks
    res["verdict_k1a"] = "PASS" if all(m["pass"] for m in marks.values()) else "FAIL"
    if "B" in arms:
        bb, bc, bp = pair_mark(useful, "B", "X", ids)
        mb = {
            "K1b.1": {"B_bare_list_endings": bare["B"], "X_bare_list_endings": bare["X"],
                      "pass": bare["B"] == 0 or bare["B"] < bare["X"] / 4},
            "K1b.2": {"B_useful_all": res["B"]["useful_all"], "X_useful_all": res["X"]["useful_all"],
                      "B_only": bb, "X_only": bc, "sign_p_B_over_X": round(bp, 4),
                      "pass": res["B"]["useful_all"] >= res["X"]["useful_all"]},
            "K1b.3": {"B_madeup": res["B"]["madeup_replies"], "X_madeup": res["X"]["madeup_replies"],
                      "B_fallbacks": res["B"]["fallbacks"], "X_fallbacks": res["X"]["fallbacks"],
                      "pass": res["B"]["madeup_replies"] <= res["X"]["madeup_replies"] + 2
                      and res["B"]["fallbacks"] <= res["X"]["fallbacks"] + 2},
        }
        res["marks_k1b"] = mb
        res["verdict_k1b"] = "PASS" if all(m["pass"] for m in mb.values()) else "FAIL"
    n = len(ids)
    need = math.ceil(0.6 * n)
    ro = {"K_minus_X_nolead": res["K"]["useful_nolead"] - res["X"]["useful_nolead"],
          "K_minus_T_lead": res["K"]["useful_lead"] - res["T"]["useful_lead"],
          "K1_bar_need": need}
    for x in [y for y in arms if y != "T"]:
        ro[f"K1_bar_{x}"] = {"useful_all": res[x]["useful_all"], "T_all": res["T"]["useful_all"],
                             "met": res[x]["useful_all"] >= res["T"]["useful_all"] and res[x]["useful_all"] >= need}
    if "KB" in arms and "KB0" in arms:
        kb, k0, kp = pair_mark(useful, "KB", "KB0", ids)
        ro["KB_minus_KB0_adapter"] = {"diff": res["KB"]["useful_all"] - res["KB0"]["useful_all"],
                                      "KB_only": kb, "KB0_only": k0}
    res["report_only"] = ro
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
