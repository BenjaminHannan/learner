#!/usr/bin/env python3
"""rv-393 blind recount (independent of count/). Standard library only.

Reads run/measure-{orig,pencil,clean}-sN.rows.jsonl, train-*.json, noharm-*.json,
info-*.json and PLAN.md's marks, and prints the recount, the clauses that fire, the
verdict and the predictions. Also compares every recounted number to the run's own
measure-*-sN.json summaries.

Usage: python3 recount.py [--seed 393] [--boot 1000]
"""
import argparse
import json
import os
import random
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
RUN = os.path.join(EXP, "run")
NETS_SHA = os.path.join(os.path.dirname(EXP), "claude-rv390-20260926", "NETS-358i2.sha256.txt")

NETS = [1, 2, 3, 4]
ARMS = ["orig", "pencil", "clean"]
SETS = ["pp-grids7", "p-grids7"]
UNIT = "pp-grids7"
TESTS = ["grids6", "grids7", "sums6"]


def load_rows(arm, s):
    path = os.path.join(RUN, f"measure-{arm}-s{s}.rows.jsonl")
    states, marks = {st: [] for st in SETS}, {st: [] for st in SETS}
    other = 0
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["row"] == "state":
                states.setdefault(r["set"], []).append(r)
            elif r["row"] == "mark":
                marks.setdefault(r["set"], []).append(r)
            else:
                other += 1
    return states, marks, other


def auc(pos, neg):
    """P(pos > neg) + 0.5 P(pos == neg), via midranks (Mann-Whitney)."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranksum_pos = 0.0
    i = 0
    n = len(allv)
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        mid = (i + j) / 2.0 + 1.0  # 1-based midrank
        npos = sum(1 for t in range(i, j + 1) if allv[t][1] == 1)
        ranksum_pos += mid * npos
        i = j + 1
        del npos
    n1, n0 = len(pos), len(neg)
    u = ranksum_pos - n1 * (n1 + 1) / 2.0
    return u / (n1 * n0)


def auc_brute(pos, neg):
    """Direct pairwise check, used once per cell to confirm auc()."""
    if not pos or not neg:
        return None
    t = 0.0
    for a in pos:
        for b in neg:
            t += 1.0 if a > b else (0.5 if a == b else 0.0)
    return t / (len(pos) * len(neg))


def state_auc(states, field):
    pos = [st[field] for st in states if st["dead"] == 1]
    neg = [st[field] for st in states if st["dead"] == 0]
    return auc(pos, neg)


def mark_counts(marks):
    wj = sum(1 for m in marks if m["right"] == 0)
    wo = sum(1 for m in marks if m["right"] == 0 and m["over"] == 1)
    rj = sum(1 for m in marks if m["right"] == 1)
    ro = sum(1 for m in marks if m["right"] == 1 and m["over"] == 1)
    return wj, wo, rj, ro


def rate(a, b):
    return F(a, b) if b else None


def fmt(x, nd=3):
    if x is None:
        return "n/a"
    return f"{float(x):.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=393)
    ap.add_argument("--boot", type=int, default=1000)
    args = ap.parse_args()

    out = {"nets": {}, "checks": [], "diffs": []}

    # ---------------- recount from rows ----------------
    R = {}   # R[(arm, s, set)] = dict of numbers
    RAW = {}  # RAW[(arm, s, set)] = (states, marks)
    for s in NETS:
        for arm in ARMS:
            states, marks, other = load_rows(arm, s)
            if other:
                out["checks"].append(f"{arm} s{s}: {other} rows with unknown 'row' type")
            for st in SETS:
                S, M = states.get(st, []), marks.get(st, [])
                RAW[(arm, s, st)] = (S, M)
                wj, wo, rj, ro = mark_counts(M)
                a = state_auc(S, "score")
                ak = state_auc(S, "k")
                d = sum(1 for x in S if x["dead"] == 1)
                R[(arm, s, st)] = dict(
                    states=len(S), dead=d, live=len(S) - d,
                    wrong_judged=wj, wrong_over=wo, right_judged=rj, right_over=ro,
                    wrong_over_rate=rate(wo, wj), right_over_rate=rate(ro, rj),
                    auc=a, auc_count_only=ak,
                    items_with_states=len({x["item"] for x in S}),
                    items_with_marks=len({x["item"] for x in M}),
                )
                # ---- internal consistency checks on the rows ----
                # brute-force AUC agrees with the rank AUC
                pos = [x["score"] for x in S if x["dead"] == 1]
                neg = [x["score"] for x in S if x["dead"] == 0]
                b = auc_brute(pos, neg)
                if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                    out["checks"].append(f"{arm} s{s} {st}: rank AUC {a} != brute AUC {b}")
                posk = [x["k"] for x in S if x["dead"] == 1]
                negk = [x["k"] for x in S if x["dead"] == 0]
                bk = auc_brute(posk, negk)
                if (ak is None) != (bk is None) or (ak is not None and abs(ak - bk) > 1e-9):
                    out["checks"].append(f"{arm} s{s} {st}: rank count AUC {ak} != brute {bk}")
                # duplicate keys
                sk = [(x["item"], x["check"]) for x in S]
                if len(sk) != len(set(sk)):
                    out["checks"].append(f"{arm} s{s} {st}: {len(sk)-len(set(sk))} duplicate state (item,check) keys")
                mk = [(x["item"], x["check"]) for x in M]
                if len(mk) != len(set(mk)):
                    out["checks"].append(f"{arm} s{s} {st}: {len(mk)-len(set(mk))} duplicate mark (item,check) keys")
                # state rows: k>=1, dead in {0,1}, score in [0,1]
                bad = [x for x in S if x["k"] < 1 or x["dead"] not in (0, 1) or not (0.0 <= x["score"] <= 1.0)]
                if bad:
                    out["checks"].append(f"{arm} s{s} {st}: {len(bad)} state rows with k<1, bad dead or score out of [0,1]")
                badm = [x for x in M if x["right"] not in (0, 1) or x["over"] not in (0, 1)]
                if badm:
                    out["checks"].append(f"{arm} s{s} {st}: {len(badm)} mark rows with bad right/over")
                # state rows carry their own wrong/right fields: k == wrong+right, dead == (wrong>0)
                inc = [x for x in S if "wrong" in x and (x["k"] != x["wrong"] + x["right"] or x["dead"] != (1 if x["wrong"] > 0 else 0))]
                if inc:
                    out["checks"].append(f"{arm} s{s} {st}: {len(inc)} state rows where k != wrong+right or dead != (wrong>0)")
                # judged marks vs pages: for each item, marks judged == max k over its states?
                maxk = {}
                for x in S:
                    maxk[x["item"]] = max(maxk.get(x["item"], 0), x["k"])
                nm = {}
                for x in M:
                    nm[x["item"]] = nm.get(x["item"], 0) + 1
                mism = sum(1 for it in set(maxk) | set(nm) if maxk.get(it, 0) != nm.get(it, 0))
                R[(arm, s, st)]["items_marks_ne_maxk"] = mism
                R[(arm, s, st)]["sum_maxk"] = sum(maxk.values())
                # a judged mark at check c should be on the page at check c: the state at (item,c) exists
                skset = set(sk)
                orphan = sum(1 for key in mk if key not in skset)
                R[(arm, s, st)]["marks_without_state"] = orphan
                # dead state from marks: page at check c is dead iff some mark judged at or before c is wrong
                wrong_by_item = {}
                for x in M:
                    if x["right"] == 0:
                        wrong_by_item.setdefault(x["item"], []).append(x["check"])
                dd = 0
                for x in S:
                    w = wrong_by_item.get(x["item"], [])
                    pred = 1 if any(c <= x["check"] for c in w) else 0
                    if pred != x["dead"]:
                        dd += 1
                R[(arm, s, st)]["dead_vs_marks_mismatch"] = dd
                # state-row own overrule tallies vs mark rows (the state rows carry wrong_over/right_over)
                if S and "wrong_over" in S[0]:
                    # per item, the last state's tallies
                    last = {}
                    for x in S:
                        if x["item"] not in last or x["check"] > last[x["item"]]["check"]:
                            last[x["item"]] = x
                    R[(arm, s, st)]["laststate_wrong"] = sum(v["wrong"] for v in last.values())
                    R[(arm, s, st)]["laststate_right"] = sum(v["right"] for v in last.values())

    # ---------------- compare with the run's summaries ----------------
    keys = ["states", "dead", "wrong_judged", "wrong_over", "right_judged", "right_over",
            "wrong_over_rate", "right_over_rate", "auc", "auc_count_only"]
    for s in NETS:
        for arm in ARMS:
            with open(os.path.join(RUN, f"measure-{arm}-s{s}.json")) as fh:
                summ = json.load(fh)
            for st in SETS:
                sm = summ["sets"][st]
                mine = R[(arm, s, st)]
                for k in keys:
                    m = mine[k]
                    t = sm.get(k)
                    if k in ("wrong_over_rate", "right_over_rate", "auc", "auc_count_only"):
                        if m is None or t is None:
                            if not (m is None and t in (None, 0, 0.0)):
                                out["diffs"].append(f"{arm} s{s} {st} {k}: mine {m} vs summary {t}")
                            continue
                        # summaries are rounded to 4 decimals
                        if abs(float(m) - float(t)) > 0.00005 + 1e-12:
                            out["diffs"].append(f"{arm} s{s} {st} {k}: mine {float(m):.6f} vs summary {t}")
                    else:
                        if m != t:
                            out["diffs"].append(f"{arm} s{s} {st} {k}: mine {m} vs summary {t}")
                mine["summary_unjudged"] = sm.get("unjudged")
                mine["summary_unfinished"] = sm.get("unfinished")
                mine["summary_pencil_solved"] = sm.get("pencil_solved")
                mine["summary_day_right"] = sm.get("day_right")

    # ---------------- VALID ----------------
    nograd = {}
    for arm in ["pencil", "clean"]:
        for s in NETS:
            with open(os.path.join(RUN, f"train-{arm}-s{s}.json")) as fh:
                t = json.load(fh)
            v = t.get("steps_block_nograd")
            # the per-100-step train log too
            logmax = 0
            with open(os.path.join(RUN, f"trainlog-{arm}-s{s}.jsonl")) as fh:
                for line in fh:
                    if line.strip():
                        logmax = max(logmax, json.loads(line).get("steps_block_nograd", 0))
            nograd[(arm, s)] = (v, logmax, t.get("steps"))
    valid = all(v == 0 for (v, _, _) in nograd.values()) and len(nograd) == 8

    # ---------------- sha256 ----------------
    ref = {}
    with open(NETS_SHA) as fh:
        for line in fh:
            p = line.split()
            if len(p) >= 2:
                ref[p[1]] = p[0]
    sha = {}
    for s in NETS:
        with open(os.path.join(RUN, f"info-s{s}.json")) as fh:
            info = json.load(fh)
        exp = ref.get(f"loop-s{s}/final.pt")
        sha[s] = (info.get("sha256"), exp, info.get("sha256") == exp, info.get("seed"))

    # ---------------- NO HARM ----------------
    nh = {}
    for s in NETS:
        with open(os.path.join(RUN, f"noharm-s{s}.json")) as fh:
            nh[s] = json.load(fh)
    nh_mean = {}
    for t in TESTS:
        nh_mean[t] = {
            "pencil-orig": F(sum(nh[s]["pencil"][t] - nh[s]["orig"][t] for s in NETS), len(NETS)),
            "clean-orig": F(sum(nh[s]["clean"][t] - nh[s]["orig"][t] for s in NETS), len(NETS)),
        }
    no_harm = all(nh_mean[t]["pencil-orig"] >= -5 for t in TESTS)

    # ---------------- marks ----------------
    P = {s: R[("pencil", s, UNIT)] for s in NETS}
    C = {s: R[("clean", s, UNIT)] for s in NETS}
    O = {s: R[("orig", s, UNIT)] for s in NETS}
    counts = {s: P[s]["wrong_judged"] >= 30 for s in NETS}
    counted = [s for s in NETS if counts[s]]

    c1 = {}
    for s in NETS:
        p, c = P[s], C[s]
        a = p["wrong_over_rate"] is not None and p["wrong_over_rate"] >= F(60, 100)
        b = p["right_over_rate"] is not None and p["right_over_rate"] <= F(10, 100)
        cc = (p["wrong_over_rate"] is not None and c["wrong_over_rate"] is not None
              and p["wrong_over_rate"] - c["wrong_over_rate"] >= F(20, 100))
        c1[s] = dict(counts=counts[s], wrong60=a, right10=b, beats_clean20=cc,
                     all3=counts[s] and a and b and cc)
    clause1 = sum(1 for s in NETS if c1[s]["all3"]) >= 3

    mean_auc = sum(P[s]["auc"] for s in NETS) / len(NETS)
    mean_cnt = sum(P[s]["auc_count_only"] for s in NETS) / len(NETS)
    margin = mean_auc - mean_cnt
    clause2 = margin >= 0.05
    works = clause1 and clause2

    pw_a_n = sum(1 for s in counted if P[s]["wrong_over_rate"] < F(30, 100))
    pw_b_n = sum(1 for s in counted if P[s]["wrong_over_rate"] <= (C[s]["wrong_over_rate"] or F(0)))
    pw_a = pw_a_n >= 3
    pw_b = pw_b_n >= 3
    pw_c = mean_auc <= mean_cnt
    proved_wrong = pw_a or pw_b or pw_c

    if works and not no_harm:
        verdict = "WORKS BUT HARMS"
    elif works:
        verdict = "WORKS"
    elif proved_wrong:
        verdict = "PROVED WRONG"
    else:
        verdict = "NO CLEAR RESULT"
    if not valid:
        verdict = "NOT VALID (rerun); would-be: " + verdict

    # ---------------- pooled count-only AUC over the 4 nets' PENCIL states ----------------
    pooled_states = []
    for s in NETS:
        pooled_states += RAW[("pencil", s, UNIT)][0]
    pooled_cnt = state_auc(pooled_states, "k")
    pooled_score = state_auc(pooled_states, "score")

    # ---------------- puzzle-level bootstrap of the per-net-mean margin ----------------
    rng = random.Random(args.seed)
    by_item = {}
    for s in NETS:
        d = {}
        for x in RAW[("pencil", s, UNIT)][0]:
            d.setdefault(x["item"], []).append(x)
        by_item[s] = (sorted(d), d)
    boots = []
    undefined = 0
    for _ in range(args.boot):
        net_margins = []
        ok = True
        for s in NETS:
            items, d = by_item[s]
            draw = [items[rng.randrange(len(items))] for _ in range(len(items))]
            S = []
            for it in draw:
                S.extend(d[it])
            a = state_auc(S, "score")
            k = state_auc(S, "k")
            if a is None or k is None:
                ok = False
                break
            net_margins.append(a - k)
        if not ok:
            undefined += 1
            continue
        boots.append(sum(net_margins) / len(net_margins))
    boots.sort()
    nb = len(boots)

    def pct_interp(q):
        # linear interpolation between order statistics (numpy default "linear")
        h = (nb - 1) * q
        lo = int(h)
        hi = min(lo + 1, nb - 1)
        return boots[lo] + (h - lo) * (boots[hi] - boots[lo])

    def pct_rank(q):
        # nearest rank: the ceil(q*n)-th smallest
        import math
        r = max(1, math.ceil(q * nb))
        return boots[r - 1]

    frac_ge_005 = sum(1 for b in boots if b >= 0.05) / nb if nb else None
    frac_le_0 = sum(1 for b in boots if b <= 0) / nb if nb else None

    # ---------------- predictions ----------------
    p1 = verdict == "WORKS"
    orig_lt30 = {s: (O[s]["wrong_over_rate"] is not None and O[s]["wrong_over_rate"] < F(30, 100)) for s in NETS}
    p2 = sum(orig_lt30.values()) >= 3
    # P393.3: CLEAN overrules more wrong marks than ORIG, but less than PENCIL.
    p3_net = {}
    for s in NETS:
        cr, orr, pr = C[s]["wrong_over_rate"], O[s]["wrong_over_rate"], P[s]["wrong_over_rate"]
        p3_net[s] = (cr > orr) and (cr < pr)
    pooled_rate = {}
    for arm, D in (("orig", O), ("pencil", P), ("clean", C)):
        wj = sum(D[s]["wrong_judged"] for s in NETS)
        wo = sum(D[s]["wrong_over"] for s in NETS)
        pooled_rate[arm] = (wo, wj, F(wo, wj))
    mean_rate = {arm: sum(D[s]["wrong_over_rate"] for s in NETS) / 4 for arm, D in (("orig", O), ("pencil", P), ("clean", C))}
    p3_pooled = pooled_rate["clean"][2] > pooled_rate["orig"][2] and pooled_rate["clean"][2] < pooled_rate["pencil"][2]
    p3_mean = mean_rate["clean"] > mean_rate["orig"] and mean_rate["clean"] < mean_rate["pencil"]
    p3_majority = sum(p3_net.values()) >= 3

    # ---------------- report-only: ORIG/CLEAN on clause 1's first two thresholds ----------------
    ro = {}
    for arm, D in (("orig", O), ("clean", C), ("pencil", P)):
        ro[arm] = {s: (D[s]["wrong_over_rate"] is not None and D[s]["wrong_over_rate"] >= F(60, 100),
                       D[s]["right_over_rate"] is not None and D[s]["right_over_rate"] <= F(10, 100)) for s in NETS}

    # ---------------- print ----------------
    P_ = print
    P_("=" * 78)
    P_(f"VERDICT: {verdict}")
    P_(f"  VALID={valid}  clause1={clause1}  clause2={clause2}  WORKS={works}  NO_HARM={no_harm}  PROVED_WRONG={proved_wrong}")
    P_("=" * 78)
    P_("\nVALID: steps_block_nograd per fine-tune (train json, max over trainlog, steps)")
    for (arm, s), v in sorted(nograd.items()):
        P_(f"  {arm:6s} s{s}: {v[0]}  (trainlog max {v[1]}, steps {v[2]})")
    P_("\nNet sha256 vs NETS-358i2.sha256.txt")
    for s in NETS:
        P_(f"  s{s}: {sha[s][0]}  match={sha[s][2]}  (info seed {sha[s][3]})")

    for st in SETS:
        P_(f"\n---- {st} {'(UNIT)' if st == UNIT else '(report-only)'} ----")
        P_(f"  {'net':4s}{'arm':7s}{'states':>7s}{'dead':>6s}{'live':>6s}{'wrongJ':>7s}{'wrongO':>7s}{'wRate':>7s}"
           f"{'rightJ':>7s}{'rightO':>7s}{'rRate':>7s}{'AUC':>7s}{'cntAUC':>7s}{'items':>6s}")
        for s in NETS:
            for arm in ARMS:
                r = R[(arm, s, st)]
                P_(f"  s{s:<3d}{arm:7s}{r['states']:7d}{r['dead']:6d}{r['live']:6d}{r['wrong_judged']:7d}{r['wrong_over']:7d}"
                   f"{fmt(r['wrong_over_rate']):>7s}{r['right_judged']:7d}{r['right_over']:7d}{fmt(r['right_over_rate']):>7s}"
                   f"{fmt(r['auc']):>7s}{fmt(r['auc_count_only']):>7s}{r['items_with_states']:6d}")
        P_("  consistency: items where #judged marks != max k | judged marks with no state at same (item,check) | dead flag != derived from marks")
        for s in NETS:
            for arm in ARMS:
                r = R[(arm, s, st)]
                P_(f"    s{s} {arm:6s}: {r['items_marks_ne_maxk']}  {r['marks_without_state']}  {r['dead_vs_marks_mismatch']}"
                   f"   (sum max k {r['sum_maxk']}, judged {r['wrong_judged'] + r['right_judged']}, summary unjudged {r['summary_unjudged']})")

    P_("\nClause 1 per net (PENCIL, pp-grids7): counts(>=30 wrong judged) | wrong>=60% | right<=10% | beats CLEAN by >=20pp")
    for s in NETS:
        c = c1[s]
        diff = P[s]["wrong_over_rate"] - C[s]["wrong_over_rate"]
        P_(f"  s{s}: {c['counts']} ({P[s]['wrong_judged']}) | {c['wrong60']} ({fmt(P[s]['wrong_over_rate'],4)}) | "
           f"{c['right10']} ({fmt(P[s]['right_over_rate'],4)}) | {c['beats_clean20']} (diff {fmt(diff,4)}) -> all3 {c['all3']}")
    P_(f"  nets meeting all three: {sum(1 for s in NETS if c1[s]['all3'])} of 4 (need >=3) -> clause 1 {clause1}")
    P_(f"\nClause 2: mean PENCIL AUC {mean_auc:.6f} - mean PENCIL count-only AUC {mean_cnt:.6f} = {margin:.6f} (need >= 0.05) -> {clause2}")
    P_(f"  per net AUC - countAUC: " + ", ".join(f"s{s} {P[s]['auc'] - P[s]['auc_count_only']:+.4f}" for s in NETS))
    P_(f"  pooled count-only AUC over 4 nets' PENCIL states: {pooled_cnt:.6f}  (pooled score AUC {pooled_score:.6f}, n={len(pooled_states)})")
    P_(f"  bootstrap (seed {args.seed}, {args.boot} resamples, {undefined} undefined dropped, n={nb}): "
       f"mean {sum(boots)/nb:.6f}, 2.5% {pct_interp(0.025):.6f}, 97.5% {pct_interp(0.975):.6f} (linear); "
       f"nearest-rank 2.5% {pct_rank(0.025):.6f}, 97.5% {pct_rank(0.975):.6f}")
    P_(f"  share of resamples with margin >= 0.05: {frac_ge_005:.3f}; with margin <= 0: {frac_le_0:.3f}")

    P_("\nNO HARM (right of 300)")
    P_(f"  {'net':4s}" + "".join(f"{a+'-'+t:>14s}" for a in ARMS for t in TESTS))
    for s in NETS:
        P_(f"  s{s:<3d}" + "".join(f"{nh[s][a][t]:14d}" for a in ARMS for t in TESTS))
    for t in TESTS:
        P_(f"  {t}: mean PENCIL-ORIG {float(nh_mean[t]['pencil-orig']):+.2f} ({nh_mean[t]['pencil-orig']}), "
           f"mean CLEAN-ORIG {float(nh_mean[t]['clean-orig']):+.2f}; per net PENCIL-ORIG "
           + ", ".join(f"{nh[s]['pencil'][t]-nh[s]['orig'][t]:+d}" for s in NETS))
    P_(f"  NO HARM (each mean >= -5): {no_harm}")

    P_(f"\nPROVED WRONG clauses (counted nets: {counted})")
    P_(f"  (a) PENCIL wrong-overrule < 30% in >=3 counted nets: {pw_a_n} nets -> {pw_a}")
    P_(f"  (b) PENCIL wrong-overrule <= CLEAN's in >=3 counted nets: {pw_b_n} nets -> {pw_b}")
    P_(f"  (c) mean AUC <= mean count-only AUC: {pw_c}")

    P_("\nReport-only: arm meets clause 1's first two thresholds (wrong>=60%, right<=10%) per net")
    for arm in ("orig", "clean", "pencil"):
        P_(f"  {arm}: " + ", ".join(f"s{s} {ro[arm][s][0] and ro[arm][s][1]} (w{ro[arm][s][0]}/r{ro[arm][s][1]})" for s in NETS))

    P_("\nPredictions")
    P_(f"  P393.1 (WORKS): {'RIGHT' if p1 else 'WRONG'}")
    P_(f"  P393.2 (ORIG wrong-overrule < 30% in >=3 of 4): per net {[fmt(O[s]['wrong_over_rate'],4) for s in NETS]} "
       f"-> {sum(orig_lt30.values())} nets -> {'RIGHT' if p2 else 'WRONG'}")
    P_(f"  P393.3 (ORIG < CLEAN < PENCIL on wrong-overrule rate): per net {p3_net}; >=3 nets {p3_majority}; "
       f"pooled {dict((a, (v[0], v[1], fmt(v[2],4))) for a, v in pooled_rate.items())} -> {p3_pooled}; "
       f"mean-of-rates {dict((a, fmt(v,4)) for a, v in mean_rate.items())} -> {p3_mean}")

    P_("\nChecks on the rows")
    P_("  " + ("none failed" if not out["checks"] else "\n  ".join(out["checks"])))
    P_("\nRecount vs run summaries (measure-*-sN.json)")
    P_("  " + ("no differences (counts exact; rates and AUCs within summary rounding 5e-5)" if not out["diffs"] else "\n  ".join(out["diffs"])))


if __name__ == "__main__":
    main()
