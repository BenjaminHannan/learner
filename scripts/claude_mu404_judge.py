#!/usr/bin/env python3
"""mu-403 / mu-404 judging: blind packets, then counts and marks ("Making things up about you", 2026-09-26).
Marks: artifacts/claude-mu403-20260926/PASSMARKS.md (fixed before the run). New file only; reuses mu-402's helpers
read-only and mu-402's judge texts unchanged (artifacts/claude-mu402-20260926/JUDGE-claims.md, JUDGE-pair.md).

Arms: R (control), F (no notebook facts in 1B prompts, mu-404), P (R + the mu-403 fix), T (plain 1B, report and M4).

  prep   --panel-dir P --runs RUNS --out J
         Claims packets: one per (arm, conversation), each shown to two judges (arms mixed and shuffled, seeds
         4041/4042, batches of 60). Pair packets: P vs R per conversation (order shuffled per conversation, seeds
         4043/4044) for two pair judges. Keys go to J/keys/ (judges never see them).
  count  --panel-dir P --runs RUNS --out J [--logs DIR]
         Reads J/out/claims_j*.jsonl and J/out/pair_p*.jsonl, writes J/marks.json, prints counts only.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_mu402_judge as J402  # noqa: E402

ARMS = ("R", "F", "P", "T")
BATCH = 60
SEEDS_CLAIMS = (4041, 4042)
SEEDS_PAIR = (4043, 4044)
DIFF, RATIO, SIGN_P, PAIR_MARGIN = 10, 0.67, 0.05, 16
V404_MIN_WITH_FACTS = 40
V403_MIN_TOP_CHANGED = 0.15


def prep(a):
    items, cv = J402.convos(a.panel_dir, a.runs, list(ARMS))
    j = Path(a.out)
    (j / "keys").mkdir(parents=True, exist_ok=True)
    (j / "packets").mkdir(parents=True, exist_ok=True)
    keys = sorted(cv)
    ids = random.Random(4040).sample(range(1000, 10000), len(keys))
    pid = {k: f"m404-{n}" for k, n in zip(keys, ids)}
    (j / "keys" / "claims_key.json").write_text(
        json.dumps({pid[k]: {"arm": k[0], "item_id": k[1]} for k in keys}, indent=1, sort_keys=True), encoding="utf-8")
    nb = 0
    for seed in SEEDS_CLAIMS:
        order = list(keys)
        random.Random(seed).shuffle(order)
        for s in range(0, len(order), BATCH):
            nb += 1
            J402.write_jsonl(j / "packets" / f"claims_j{nb}.jsonl",
                             [{"pid": pid[k], "conversation": [{"user": t["user"], "assistant": t["assistant"]}
                                                               for t in cv[k]]} for k in order[s:s + BATCH]])
    for n, seed in enumerate(SEEDS_PAIR, 1):
        rng = random.Random(seed)
        pk, pkey = [], {}
        for iid in sorted(items):
            if ("P", iid) not in cv or ("R", iid) not in cv:
                continue
            pair = ["P", "R"]
            rng.shuffle(pair)
            p = f"p404-{n}-{iid[-2:]}"
            pkey[p] = {"item_id": iid, "1": pair[0], "2": pair[1]}
            pk.append({"pid": p, **{f"conversation_{i}": [{"user": t["user"], "assistant": t["assistant"]}
                                                          for t in cv[(arm, iid)]] for i, arm in ((1, pair[0]),
                                                                                                  (2, pair[1]))}})
        order = list(range(len(pk)))
        rng.shuffle(order)
        J402.write_jsonl(j / "packets" / f"pair_p{n}.jsonl", [pk[i] for i in order])
        (j / "keys" / f"pair_key_p{n}.json").write_text(json.dumps(pkey, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({"claims_packets": len(keys), "claims_batches": nb, "pair_packets_per_judge": len(pk)}))


def _cut(c_ctrl, c_new):
    return c_ctrl - c_new >= DIFF and c_new <= RATIO * c_ctrl


def _sign(per_conv, ctrl, new):
    more = sum(1 for d in per_conv.values() if d.get(ctrl, 0) > d.get(new, 0))
    fewer = sum(1 for d in per_conv.values() if d.get(ctrl, 0) < d.get(new, 0))
    p = J402.binom_one_sided(more, more + fewer)
    return {f"{ctrl}_more": more, f"{ctrl}_fewer": fewer, "p_one_sided": round(p, 4), "pass": p <= SIGN_P}


def _log_line(logs, arm, pat):
    if not logs:
        return None
    f = Path(logs) / f"log{arm}.txt"
    if not f.exists():
        return None
    hits = [ln for ln in f.read_text(encoding="utf-8", errors="replace").splitlines() if ln.startswith(pat)]
    return hits[-1] if hits else None


def count(a):
    items, cv = J402.convos(a.panel_dir, a.runs, [x for x in ARMS if (Path(a.runs) / f"chat_{x}.jsonl").exists()])
    j = Path(a.out)
    key = json.loads((j / "keys" / "claims_key.json").read_text(encoding="utf-8"))
    judged = defaultdict(list)
    bad = 0
    for f in sorted((j / "out").glob("claims_j*.jsonl")):
        for r in J402.load(f):
            k = key[r["pid"]]
            fl = [1 if int(x) else 0 for x in r["flags"]]
            if len(fl) != len(cv[(k["arm"], k["item_id"])]):
                bad += 1
                continue
            judged[(k["arm"], k["item_id"])].append(fl)
    res = {"bad_packets": bad, "arms": {}}
    per_conv = defaultdict(dict)
    for arm in [x for x in ARMS if any(k[0] == x for k in cv)]:
        c_sum = both = either = 0
        by_kind, n_judged = Counter(), Counter()
        for (x, iid), lists in judged.items():
            if x != arm:
                continue
            n_judged[len(lists)] += 1
            s = [sum(col) for col in zip(*lists)]
            c_sum += sum(s)
            both += sum(1 for v in s if v == len(lists))
            either += sum(1 for v in s if v > 0)
            for t, v in zip(cv[(x, iid)], s):
                by_kind[t["kind"]] += v
            per_conv[iid][arm] = sum(s)
        res["arms"][arm] = {"C_sum_two_judges": c_sum, "replies_flagged_by_both": both,
                            "replies_flagged_by_either": either, "flags_by_kind": dict(by_kind),
                            "conversations_by_judge_count": dict(n_judged),
                            "replies": sum(len(t) for (x, _), t in cv.items() if x == arm)}
    C = {x: v["C_sum_two_judges"] for x, v in res["arms"].items()}
    marks = {}
    # mu-404: F vs R (diagnosis)
    if "R" in C and "F" in C:
        facts_line = _log_line(a.logs, "R", "mu404: facts")
        wf = None
        if facts_line:
            m = re.search(r"'with_facts': (\d+)", facts_line)
            wf = int(m.group(1)) if m else None
        v404 = wf is not None and wf >= V404_MIN_WITH_FACTS
        n1 = {"C_R": C["R"], "C_F": C["F"], "pass": _cut(C["R"], C["F"])}
        n2 = _sign(per_conv, "R", "F")
        marks["mu404"] = {"V404_R_calls_with_facts": wf, "V404": v404, "N1": n1, "N2": n2,
                          "proved_wrong": C["F"] >= C["R"],
                          "verdict": ("INCONCLUSIVE" if not v404 else
                                      "PASS" if n1["pass"] and n2["pass"] else "FAIL")}
    # mu-403: P vs R (fix)
    if "R" in C and "P" in C:
        m1 = {"C_R": C["R"], "C_P": C["P"], "pass": _cut(C["R"], C["P"])}
        m2 = _sign(per_conv, "R", "P")
        wins = losses = ties = 0
        for n in (1, 2):
            kf, of = j / "keys" / f"pair_key_p{n}.json", j / "out" / f"pair_p{n}.jsonl"
            if not (kf.exists() and of.exists()):
                continue
            pkey = json.loads(kf.read_text(encoding="utf-8"))
            for r in J402.load(of):
                w = str(r["winner"]).strip().lower()
                if w == "tie":
                    ties += 1
                elif pkey[r["pid"]].get(w) == "P":
                    wins += 1
                elif pkey[r["pid"]].get(w) == "R":
                    losses += 1
        m3 = {"P_wins": wins, "P_losses": losses, "ties": ties, "pass": losses - wins <= PAIR_MARGIN}
        m4 = {"C_P": C["P"], "C_T": C.get("T"), "pass": "T" in C and C["P"] <= C["T"]}
        diff = sum(1 for (x, iid), t in cv.items() if x == "P" and ("R", iid) in cv
                   for u, v in zip(t, cv[("R", iid)]) if u["assistant"] != v["assistant"])
        pick_line = _log_line(a.logs, "P", "mu403: pick totals")
        v403 = {"replies_differing_P_R": diff, "pick_totals_line": pick_line}
        if pick_line:
            sc = re.search(r"'scored': (\d+)", pick_line)
            tc = re.search(r"'top_changed': (\d+)", pick_line)
            if sc and tc and int(sc.group(1)):
                v403["top_changed_share"] = round(int(tc.group(1)) / int(sc.group(1)), 3)
                v403["pass"] = v403["top_changed_share"] >= V403_MIN_TOP_CHANGED
        else:
            v403["pass"] = diff * 3 >= res["arms"]["P"]["replies"]          # sysline: >= a third of replies differ
        marks["mu403"] = {"V403": v403, "M1": m1, "M2": m2, "M3": m3, "M4": m4,
                          "proved_wrong": C["P"] >= C["R"],
                          "verdict": ("INCONCLUSIVE" if not v403.get("pass") else
                                      "PASS" if all(x["pass"] for x in (m1, m2, m3, m4)) else "FAIL")}
    res["marks"] = marks
    (j / "marks.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prep", "count"])
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--logs")
    a = ap.parse_args()
    (prep if a.cmd == "prep" else count)(a)


if __name__ == "__main__":
    main()
