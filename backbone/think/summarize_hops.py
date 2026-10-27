#!/usr/bin/env python3
"""Addendum G summary (the hops bed): reads result_{hplain,hloop,hplains,hloops}_s{seed}.json and applies the round-1 marks fixed in
PREREG-think2.md Addendum G. Kept apart from summarize.py: these rows are not village rows, and no number here is compared with a village number.

  python backbone/think/summarize_hops.py OUT/hops --data OUT/hops-data [--json]

Accuracies are percent on the hops validation rows (depth 1-10, equal counts). Differences are paired on the same rows: summarize.boot, 2,000
resamples, 95% interval. "trained" = depth 1-4; "near" = depth 5-6, the marked unseen depths (within the ~1.5x reach past the trained depth
that Shapiro 2026 found); "far" = depth 7-10 and "deep" = 5-10, reported with no mark (they also need loop counts 7-12, which no arm trains).
  pair A: hloop (br's recipe) vs hplain (plain LoRA given hloop's extra layer passes), at a fixed 6 loops.
  pair B: hloops (the positive control: injection, loops = hops, every loop graded) vs hplains (plain LoRA given hloops' extra layer passes),
          at the answer-stable halting rule (the deployable score), with r = depth (the mechanism) and the halting loop counts by depth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_hops as H  # noqa: E402
import summarize as SU  # noqa: E402

MAIN = "r6"
LOOPS = tuple(range(1, 13))  # every looped arm must have r1..r12 on validation; the answer-stable rule's "else" is 12
V1_SHALLOW, V2_NEAR, V3_TRAINED = 80.0, 70.0, 80.0  # plain >= 80 on depth 1-2; plain <= 70 on depth 5-6; hloops at r = depth >= 80 on depth 1-4
GAIN, WRONG, HARM, RISE = 5.0, 1.0, 2.0, 5.0  # near gain over plain (proved wrong below +1); trained-depth loss allowed; near S(r6) - S(r1)
RHO, RHO_LO, RHO_WRONG = 0.50, 0.30, 0.10  # pair B: Spearman(depth 1-6, halting loops) >= 0.5 with interval above 0.3; proved wrong <= 0.1
FLOOR = 100.0 / H.CHAINS  # naming a random place of the row (every row has CHAINS different places)
EPS = SU.EPS
NEXT = {  # Addendum G's decision for each pair-B outcome (printed with it, so the reading is mechanical)
    "VOID": "the bed cannot separate the arms: no claim either way; redesign the bed (a new addendum) before any more loop runs on it",
    "NOT INSTALLED": "check the wiring (|W|, step accuracy, the W = 0 lesion); if it is sound, one hloops + hplains run at 10,500 steps "
                     "(Shapiro's length); no claim about loops before that",
    "PASS": "seed-1 replicate of hloops and hplains; if it also passes, score the fresh rows once, then round 2 (hloopd, hloopi)",
    "TOLD ONLY": "a seed-1 replicate; then a trained stop signal on hloops' states (the stop rule is the gap, not the loop)",
    "TRADE-OFF": "a seed-1 replicate; then look at which trained depths lose and whether the stop rule stops them too early",
    "NOT ADAPTIVE": "a seed-1 replicate; the gain is real but the laps do not follow depth: a trained stop signal next",
    "PROVED WRONG": "one hloops + hplains run at 10,500 steps (Shapiro's length); if that also fails, stop retrofitting loops onto the 0.8B and "
                    "move the loop line to a natively looped model (Ouro-1.4B probe, needs Ben's words for remote code) or written steps",
    "NOT SHOWN": "a seed-1 replicate of both arms to narrow the intervals; no design change",
}


def masks(rows):
    d = np.array([r["depth"] for r in rows])
    return {"trained": (d >= 1) & (d <= 4), "near": (d >= 5) & (d <= 6), "far": d >= 7, "deep": d >= 5, "d1-2": d <= 2, "d1-6": d <= 6}, d


def loop_tags(res):
    v = res["eval"]["validation"]
    return sorted(int(t[1:]) for t in v if t[:1] == "r" and t[1:].isdigit())


def missing(res, arms):
    """Validation tags a pair needs but some arm lacks (an incomplete or edited result file)."""
    out = []
    for arm in arms:
        v = res[arm]["eval"]["validation"]
        out += [f"{arm}:main"] * ("main" not in v)
        if arm in ("hloop", "hloops"):
            out += [f"{arm}:r{k}" for k in LOOPS if f"r{k}" not in v]
    return out


def halted(res, rows, rule="stable"):
    """Per-row hits (0/1) and loop counts chosen by a training-free stop rule, rebuilt from the stored per-loop answers / log-probs over r = 1..12.
    stable: the first r whose answer equals the answer at r - 1, else 12. conf: the r whose answer has the highest summed log-prob (ties: fewer)."""
    v, loops = res["eval"]["validation"], LOOPS
    hits = {r: SU.decode_hits(v[f"r{r}"]["hits"]) for r in loops}
    if rule == "conf":
        lp = {r: v[f"r{r}"]["logp"] for r in loops}
        ch = [max(loops, key=lambda r: (lp[r][i], -r)) for i in range(len(rows))]
    else:
        pr = {r: v[f"r{r}"]["preds"] for r in loops}
        ch = [next((r for r in loops[1:] if pr[r][i] == pr[r - 1][i]), loops[-1]) for i in range(len(rows))]
    return np.array([hits[c][i] for i, c in enumerate(ch)]), np.array(ch)


def at_depth(res, rows):
    """Per-row hits with r = the row's depth."""
    v = res["eval"]["validation"]
    return np.array([SU.decode_hits(v[f"r{r['depth']}"]["hits"])[i] for i, r in enumerate(rows)])


def step_acc(res, rows):
    """hloops' mechanism read (no mark): at a fixed r below a row's depth, how often the answer names hop r of the chain (hops_path[r-1])."""
    v, out = res["eval"]["validation"], {}
    for r in loop_tags(res):
        idx = [i for i, x in enumerate(rows) if r < x["depth"]]
        if idx:
            pr = v[f"r{r}"]["preds"]
            out[f"r{r}"] = 100 * sum(pr[i] == norm(rows[i]["hops_path"][r - 1]) for i in idx) / len(idx)
    return out


def norm(s):
    s = " ".join(s.strip().lower().split())
    return s[:-1].strip() if s.endswith(".") else s


def ranks(v):
    """Average ranks (ties share the mean of their positions), as think1.spearman."""
    v = np.asarray(v, float)
    r = np.empty(len(v))
    r[np.argsort(v, kind="mergesort")] = np.arange(len(v))
    _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
    return (np.bincount(inv, weights=r) / cnt)[inv]


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    return None if rx.std() == 0 or ry.std() == 0 else float(np.corrcoef(rx, ry)[0, 1])


def spearman_ci(depth, loops, n=SU.BOOT_N, seed=SU.BOOT_SEED):
    """Spearman(depth, loops) with an n-resample row bootstrap 95% interval (a constant resample counts as 0)."""
    rho = spearman(depth, loops)
    if rho is None:
        return None, None, None
    rng, vals = np.random.default_rng(seed), []
    for _ in range(n):
        idx = rng.integers(0, len(depth), len(depth))
        x = spearman(depth[idx], loops[idx])
        vals.append(0.0 if x is None else x)
    return rho, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def ok(d, need):
    return None if d is None or d.get("lo") is None else bool(d["value"] >= need - EPS and d["lo"] > 0)


def below(d, bar=WRONG):
    return d is not None and d["value"] < bar - EPS


def validity(st, P, m):
    a = lambda sel: st.stat({"x": P}, lambda x: x["x"], sel, ci=False)["value"]
    v = {"plain_d1_2": a(m["d1-2"]), "plain_near": a(m["near"])}
    v["V1"], v["V2"] = v["plain_d1_2"] >= V1_SHALLOW - EPS, v["plain_near"] <= V2_NEAR + EPS
    v["valid"] = v["V1"] and v["V2"]
    return v


def common(res, arm, rows, st, m, depth, vec):
    r = res[arm]
    stable_h, stable_l = halted(r, rows, "stable")
    conf_h, conf_l = halted(r, rows, "conf")
    ds = sorted(set(depth.tolist()))
    acc = lambda v, sel: None if v is None else st.stat({"x": v}, lambda x: x["x"], sel, ci=False)["value"]
    pct = lambda h, sel: 100 * float(h[sel].mean())
    return {"curve": {s: {f"r{k}": acc(vec(arm, f"r{k}"), m[s]) for k in loop_tags(r)} for s in ("trained", "near", "far")},
            "stable": {"acc": 100 * float(stable_h.mean()), **{s: pct(stable_h, m[s]) for s in ("trained", "near", "far", "deep")},
                       "loops_by_depth": {str(d): float(stable_l[depth == d].mean()) for d in ds}},
            "conf": {"acc": 100 * float(conf_h.mean()), **{s: pct(conf_h, m[s]) for s in ("trained", "near", "far", "deep")},
                     "loops_by_depth": {str(d): float(conf_l[depth == d].mean()) for d in ds}},
            "_stable": (stable_h, stable_l)}


def lesion(res, arm, st, m, vec):
    """Injection arms: r6 vs r6 with W = 0, all rows and near (no mark), and |W|."""
    if "r6_w0" not in res[arm]["eval"]["validation"]:
        return None
    acc = lambda tag, sel: st.stat({"x": vec(arm, tag)}, lambda x: x["x"], sel, ci=False)["value"]
    return {"r6": acc("r6", None), "r6_w0": acc("r6_w0", None), "r6_near": acc("r6", m["near"]), "r6_w0_near": acc("r6_w0", m["near"]),
            "weight_norm": (res[arm].get("inject") or {}).get("weight_norm")}


def outcome_B(b):
    v = b["validity"]
    if not v["valid"]:
        return "VOID", "VOID (" + ", ".join(k for k in ("V1", "V2") if not v[k]) + ")"
    if not b["pass_V3"]:
        return "NOT INSTALLED", "NOT INSTALLED (V3: hloops at r = depth on the trained depths below 80): the recipe did not fit even the trained " \
                                "depths at this budget, or the code is wrong; not a refutation"
    seed = f" (seed {b['seed']} only: a seed-1 replicate must pass before this counts)"
    budget = f" at this budget ({b['steps']} steps, seed {b['seed']})"
    if b["pass_B1"] and b["pass_B2"] and b["pass_B4"]:
        return "PASS", "PASS: the published loop recipe, choosing its own lap count, beats plain training on unseen chain lengths" + seed
    if b["pass_B3"] and not b["pass_B1"]:
        return "TOLD ONLY", "the loop works when told how many laps (r = depth), but the answer-stable stop rule does not deliver it" + seed
    if b["pass_B1"] and not b["pass_B2"]:
        return "TRADE-OFF", "the loop gains on unseen depths but loses more than 2 points on the trained ones" + seed
    if b["pass_B1"] and b["pass_B2"]:
        return "NOT ADAPTIVE", "the loop gains, but its lap counts do not follow depth (B4)" + seed
    if below(b["B1"]) and below(b["B3"]):
        return "PROVED WRONG", "PROVED WRONG" + budget + ": B1 below +1 and r = depth (B3) below +1 too"
    return "NOT SHOWN", "not shown (between the bars)" + (": " + "; ".join(b["wrong"]) if b["wrong"] else "")


def analyse(res, rows, seed=0):
    res = {a: r for (a, s), r in res.items() if s == seed}
    aborted = sorted(a for a, r in res.items() if r.get("aborted"))
    res = {a: r for a, r in res.items() if not r.get("aborted")}
    st = SU.Stats(None, rows)
    m, depth = masks(rows)
    R = SU.Runs({(a, seed): r for a, r in res.items()})
    vec = lambda arm, tag: R.vec(arm, seed, "validation", tag)
    out = {"seed": seed, "n": len(rows), "arms": sorted(res), "aborted": aborted, "floor": FLOOR, "by_depth": {}, "not_computed": {}}
    for d in sorted(set(depth.tolist())):
        sel = depth == d
        out["by_depth"][str(d)] = {"n": int(sel.sum()), **{a: st.stat({"x": vec(a, "main")}, lambda x: x["x"], sel, ci=False)["value"] for a in res if vec(a, "main") is not None}}
    for pair, arms in (("A", ("hloop", "hplain")), ("B", ("hloops", "hplains"))):
        gone = [a for a in arms if a not in res]
        miss = [] if gone else missing(res, arms)
        if gone or miss:
            out["not_computed"][pair] = ", ".join([f"{a} {'aborted' if a in aborted else 'missing'}" for a in gone] + miss)
    if "A" not in out["not_computed"]:  # pair A
        P, S6, S1 = vec("hplain", "main"), vec("hloop", MAIN), vec("hloop", "r1")
        v = validity(st, P, m)
        a = {"validity": v, "A1": st.diff(S6, P, m["near"]), "A2": st.diff(S6, P, m["trained"], ci=False), "A3": st.diff(S6, S1, m["near"]),
             "far_r6_minus_plain": st.diff(S6, P, m["far"], ci=False)}
        a |= {k: v_ for k, v_ in common(res, "hloop", rows, st, m, depth, vec).items() if k[0] != "_"}
        a["pass_A1"], a["pass_A3"] = ok(a["A1"], GAIN), ok(a["A3"], RISE)
        a["pass_A2"] = a["A2"]["value"] >= -HARM - EPS
        a["wrong"] = [w for w, c in (("A1: near gain over hplain below +1", below(a["A1"])), ("A3: near r6 - r1 below +1", below(a["A3"]))) if c]
        a["outcome"] = ("VOID (" + ", ".join(k for k in ("V1", "V2") if not v[k]) + ")" if not v["valid"] else
                        f"PASS: br's recipe beats plain on unseen chain lengths (seed {seed} only: needs a seed-1 replicate)"
                        if a["pass_A1"] and a["pass_A2"] and a["pass_A3"] else
                        "FAILS, PROVED WRONG (" + "; ".join(a["wrong"]) + ")" if a["wrong"] else "FAILS, not shown either way (between the bars)")
        out["A"] = a
    if "B" not in out["not_computed"]:  # pair B
        P = vec("hplains", "main")
        v = validity(st, P, m)
        c = common(res, "hloops", rows, st, m, depth, vec)
        sh, sl = c.pop("_stable")
        Hv, od = (0, sh), (0, at_depth(res["hloops"], rows))
        v3 = st.stat({"x": od}, lambda x: x["x"], m["trained"], ci=False)["value"]
        rho, lo, hi = spearman_ci(depth[m["d1-6"]], sl[m["d1-6"]])
        b = {"validity": v, "seed": seed, "steps": res["hloops"].get("steps_stage1"), "V3_trained_at_depth": v3, "pass_V3": v3 >= V3_TRAINED - EPS,
             "B1": st.diff(Hv, P, m["near"]), "B2": st.diff(Hv, P, m["trained"], ci=False), "B3": st.diff(od, P, m["near"]),
             "rho": rho, "rho_lo": lo, "rho_hi": hi, "rho_d1_10": spearman(depth, sl),
             "far_halting_minus_plain": st.diff(Hv, P, m["far"], ci=False), "far_depth_minus_plain": st.diff(od, P, m["far"], ci=False),
             "step_acc": step_acc(res["hloops"], rows), "lesion": lesion(res, "hloops", st, m, vec), **c}
        b["pass_B1"], b["pass_B3"] = ok(b["B1"], GAIN), ok(b["B3"], GAIN)
        b["pass_B2"] = b["B2"]["value"] >= -HARM - EPS
        b["pass_B4"] = rho is not None and rho >= RHO - EPS and lo > RHO_LO
        b["wrong"] = [w for w, c_ in (("B1: near halting gain over hplains below +1", below(b["B1"])),
                                      ("B3: near r = depth gain below +1", below(b["B3"])),
                                      ("B4: Spearman(depth 1-6, loops) <= 0.1", rho is None or rho <= RHO_WRONG + EPS)) if c_]
        b["key"], b["outcome"] = outcome_B(b)
        b["next"] = NEXT[b["key"]]
        out["B"] = b
    return out


def report(o):
    L = []
    P = L.append
    f2, sg, ci = SU.f2, SU.sg, SU.ci_txt
    mk = lambda x: SU.ND if x is None else "PASS" if x else "FAIL"
    P("ADDENDUM G, ROUND 1: THE HOPS BED (percent; trained = depth 1-4; near = depth 5-6, the marked unseen depths; far = depth 7-10, no mark;")
    P("not comparable with any village number)")
    P(f"seed {o['seed']}, {o['n']} validation rows; arms: {', '.join(o['arms'])}" + (f"; ABORTED: {', '.join(o['aborted'])}" if o["aborted"] else ""))
    P(f"floor: naming a random place of the row scores {o['floor']:.1f} at every depth")

    def curves(x):
        for s in ("trained", "near", "far"):
            P(f"   {s} accuracy by fixed loop count: " + "  ".join(f"{k} {f2(v)}" for k, v in x["curve"][s].items()))
        for name in ("stable", "conf"):
            h = x[name]
            P(f"   halting ({'answer-stable' if name == 'stable' else 'max confidence, no mark'}): {f2(h['acc'])} all, {f2(h['trained'])} trained, "
              f"{f2(h['near'])} near, {f2(h['far'])} far; loops by depth " + " ".join(f"d{d}:{v:.2f}" for d, v in h["loops_by_depth"].items()))

    for pair, name in (("A", "hloop (br's recipe) vs hplain"), ("B", "hloops (positive control) vs hplains")):
        if pair in o["not_computed"]:
            P(f"-- pair {pair}: {name}: NOT COMPUTED ({o['not_computed'][pair]})")
            P(f"   OUTCOME {pair}: not computed")
    if "A" in o:
        a, v = o["A"], o["A"]["validity"]
        P("-- pair A: hloop (br's recipe) vs hplain, at 6 loops")
        P(f"   {mk(v['V1'])} V1 hplain depth 1-2 = {f2(v['plain_d1_2'])} (>= {V1_SHALLOW:.0f});  {mk(v['V2'])} V2 hplain near = {f2(v['plain_near'])} (<= {V2_NEAR:.0f})")
        P(f"   {mk(a['pass_A1'])} A1 near S(r6) - hplain = {sg(a['A1']['value'])}{ci(a['A1'])} (>= +{GAIN:.0f}, interval above 0; proved wrong below +{WRONG:.0f})")
        P(f"   {mk(a['pass_A2'])} A2 trained S(r6) - hplain = {sg(a['A2']['value'])} (>= -{HARM:.0f})")
        P(f"   {mk(a['pass_A3'])} A3 near S(r6) - S(r1) = {sg(a['A3']['value'])}{ci(a['A3'])} (>= +{RISE:.0f}, interval above 0; proved wrong below +{WRONG:.0f})")
        P(f"   no mark: far S(r6) - hplain = {sg(a['far_r6_minus_plain']['value'])}")
        curves(a)
        P(f"   OUTCOME A: {a['outcome']}")
    if "B" in o:
        b, v = o["B"], o["B"]["validity"]
        P("-- pair B: hloops (positive control) vs hplains, at the answer-stable stop rule")
        P(f"   {mk(v['V1'])} V1 hplains depth 1-2 = {f2(v['plain_d1_2'])} (>= {V1_SHALLOW:.0f});  {mk(v['V2'])} V2 hplains near = {f2(v['plain_near'])} (<= {V2_NEAR:.0f})")
        P(f"   {mk(b['pass_V3'])} V3 hloops at r = depth, trained depths = {f2(b['V3_trained_at_depth'])} (>= {V3_TRAINED:.0f}: the loop is installed)")
        P(f"   {mk(b['pass_B1'])} B1 near halting - hplains = {sg(b['B1']['value'])}{ci(b['B1'])} (>= +{GAIN:.0f}, interval above 0; proved wrong below +{WRONG:.0f})")
        P(f"   {mk(b['pass_B2'])} B2 trained halting - hplains = {sg(b['B2']['value'])} (>= -{HARM:.0f})")
        P(f"   {mk(b['pass_B3'])} B3 (mechanism, no deploy claim) near r = depth - hplains = {sg(b['B3']['value'])}{ci(b['B3'])} (>= +{GAIN:.0f}, interval above 0)")
        P(f"   {mk(b['pass_B4'])} B4 Spearman(depth 1-6, halting loops) = {f2(b['rho'])} [{f2(b['rho_lo'])}, {f2(b['rho_hi'])}] (>= {RHO}, interval above {RHO_LO}; "
          f"proved wrong <= {RHO_WRONG}); depth 1-10, no mark: {f2(b['rho_d1_10'])}")
        P(f"   no mark: far halting - hplains = {sg(b['far_halting_minus_plain']['value'])}; far r = depth - hplains = {sg(b['far_depth_minus_plain']['value'])}")
        if b["lesion"]:
            ls = b["lesion"]
            P(f"   no mark: W = 0 lesion: r6 {f2(ls['r6'])} -> {f2(ls['r6_w0'])} (near {f2(ls['r6_near'])} -> {f2(ls['r6_w0_near'])}); |W| = {f2(ls['weight_norm'])}")
        P("   step accuracy (answer at loop r names hop r, rows deeper than r): " + "  ".join(f"{k} {f2(x)}" for k, x in b["step_acc"].items()))
        curves(b)
        P(f"   OUTCOME B: {b['outcome']}")
        P(f"   NEXT (fixed in Addendum G): {b['next']}")
    P("accuracy by depth (each arm's main tag): " + "  ".join(f"d{d}: " + ",".join(f"{a} {f2(x.get(a))}" for a in o["arms"] if a in x) for d, x in o["by_depth"].items()))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--data", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res, _ = SU.load_results(a.out)
    res = {k: r for k, r in res.items() if k[0] in ("hplain", "hloop", "hplains", "hloops", "hloopi", "hloopd")}
    rows = SU.load_rows(Path(a.data) / "validation.jsonl")
    o = analyse(res, rows, a.seed)
    print(json.dumps(o, indent=1, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x)) if a.json else report(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
