#!/usr/bin/env python3
"""Addendum G / I summary (the hops bed): reads result_{hplain,hloop,hloopi,hloopd,hplains,hloops}_s{seed}.json and applies the marks fixed in
PREREG-think2.md Addendum G (round 1) and Addendum I (round 2). Kept apart from summarize.py: these rows are not village rows, and no number here
is compared with a village number.

  python backbone/think/summarize_hops.py OUT/hops --data OUT/hops-data [--seed N] [--split validation|fresh [--validation OUT/runs]] [--json]

--split fresh reads DATA/fresh.jsonl and every eval from res["eval"]["fresh"] (the files fresh_hops.py writes): the same marks, the same functions,
recomputed on the fresh rows (Addendum I, item 4). A mark that passed on validation and fails there is reported as "did not hold on fresh rows", and no
claim rests on it; so the fresh report compares each mark with the same mark on the validation rows (--validation RUNS: the validation result files,
read with DATA/validation.jsonl, same seed) and prints one verdict per pair / arm in place of the OUTCOME and NEXT decision lines, which belong to the
validation read. Without --validation it prints plain PASS / FAIL, "no validation read", and no step follows from any of it.

Accuracies are percent on the hops validation rows (depth 1-10, equal counts). Differences are paired on the same rows: summarize.boot, 2,000
resamples, 95% interval. "trained" = depth 1-4; "near" = depth 5-6, the marked unseen depths (within the ~1.5x reach past the trained depth
that Shapiro 2026 found); "far" = depth 7-10 and "deep" = 5-10, reported with no mark (they also need loop counts 7-12, which no arm trains).
  pair A: hloop (br's recipe) vs hplain (plain LoRA given hloop's extra layer passes), at a fixed 6 loops.
  pair B: hloops (the positive control: injection, loops = hops, every loop graded) vs hplains (plain LoRA given hloops' extra layer passes),
          at the answer-stable halting rule (the deployable score), with r = depth (the mechanism) and the halting loop counts by depth.
The round-1 text comes first and is unchanged; what Addendum I adds is appended after it:
  pair A at seed 1: A1-A3 label REPLICATES; the new stop-rule marks A4-A6 (hloop under the answer-stable rule vs hplain) label STOPS ITSELF.
          At seed 0 A4-A6 are printed as values only ("read before Addendum I's marks, not a test"); at seed >= 2 as values only, with no label
          (Addendum I fixes REPLICATES and A4-A6 at seed 1; a seed-2 reading needs a new addendum).
  round 2: X = hloopi (control hplain) and X = hloopd (control hplains): V1/V2 of the control, Installed, F1/F2 (WORKS), S1-S3 (STOPS ITSELF).
  one-change readouts, no mark: hloopi - hloop, hloopd - hloopi, hloops - hloopd, each at r6 and under the answer-stable rule, near and far.
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
LOOPS = tuple(range(1, 13))  # every looped arm must have r1..r12 on the scored split; the answer-stable rule's "else" is 12
LOOPED = ("hloop", "hloopi", "hloopd", "hloops")  # = think1.HOPS_LOOPED (test_hops pins it): the arms scored at r1..r12 (not imported: think1 needs torch)
CONTROL = {"hloopi": "hplain", "hloopd": "hplains"}  # Addendum I: the reused seed-0 control of each round-2 arm
READOUTS = (("hloopi", "hloop", "injection"), ("hloopd", "hloopi", "laps tied to depth"), ("hloops", "hloopd", "graded laps"))  # Addendum I's ladder, one change each
SPLITS = ("validation", "fresh")
SEED0_NOTE = "seed 0: read before Addendum I's marks, not a test"  # A4-A6 at seed 0: values, no PASS / FAIL (Addendum I: seed 0 was seen)
STOP_SEED = 1  # Addendum I reads pair A's REPLICATES label and A4-A6 at seed 1 only
HELD, NOT_HELD = "held on fresh rows", "did not hold on fresh rows"  # Addendum I item 4: the fresh verdict of a mark that passed on validation
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
# Addendum I's decisions for the pair-A replicate (seed >= 1) and for each round-2 outcome (printed with it, so the reading is mechanical)
NEXT_A = {
    "VOID": NEXT["VOID"],
    "REPLICATES": "br's fixed-lap result holds on two seeds; the village reading of Addendum G's pair A decision stands. hloop does not stop itself "
                  "(as seed 0 showed): nothing moves into the assistant until one answer-only recipe both replicates its fixed-lap gain and stops itself "
                  "on two seeds, with fresh rows",
    "REPLICATES + STOPS ITSELF": "br's fixed-lap result holds on two seeds and hloop also stops itself (not expected from seed 0): the stop-rule "
                                 "question for hloop is reopened before anything moves to the assistant",
    "DOES NOT REPLICATE": "no claim rests on pair A; the village reading of Addendum G's pair A decision waits for a seed-2 run",
}
STOP_SIGNAL = ("a trained stop signal that needs only the answer (a halting head trained on the model's own lap-by-lap correctness, PonderNet-style), "
               "on hloop or hloopi")
NEXT2 = {
    ("hloopi", "VOID"): "the control cannot separate the arms: no claim either way; redesign the bed (a new addendum) before more loop runs on it",
    ("hloopd", "VOID"): "the control cannot separate the arms: no claim either way; redesign the bed (a new addendum) before more loop runs on it",
    ("hloopi", "NOT INSTALLED"): "not a refutation; Addendum I fixes no step for it: check the wiring (|W|, the W = 0 lesion) and write a new addendum before any claim",
    ("hloopd", "NOT INSTALLED"): "not a refutation; Addendum I fixes no step for it: check the wiring (|W|, the W = 0 lesion) and write a new addendum before any claim",
    ("hloopi", "STOPS ITSELF"): "hloopi seed 1 (and hplain seed 1, if pair A's replicate has not run it) before any claim, then its fresh rows; injection is what "
                               "br's recipe lacked, it needs no extra labels, so hloopi is the candidate for the assistant",
    ("hloopi", "WORKS ONLY"): "injection alone does not give an online stop: read hloopd (if it runs): if hloopd STOPS ITSELF, laps tied to depth give the "
                              "stop, but real data has no depth (a new addendum: a lap count the model can set without depth labels, e.g. a curriculum "
                              "that adds laps only while the answer loss still falls); if it does not (and pair B seed 1 passed), the graded laps give "
                              "the stop, and real data has no hop labels (a new addendum: " + STOP_SIGNAL + ")",
    ("hloopi", "PROVED WRONG"): "with W, br's recipe loses its fixed-lap gain on this bed (F1 below +1: injection hurts here); the stop-signal addendum runs "
                                "on hloop: " + STOP_SIGNAL,
    ("hloopi", "NOT SHOWN"): "with W, br's recipe loses its fixed-lap gain on this bed (not shown either way); the stop-signal addendum runs on hloop: "
                             + STOP_SIGNAL,
    ("hloopi", "TRADE-OFF"): "Addendum I fixes no step for it: the near fixed-lap gain held (F1 passes) but the trained depths lost more than 2 points (F2 "
                             "fails), so the stop rule's S1-S3 did not all pass either; look at which trained depths lose, then write a new addendum before any claim",
    ("hloopd", "STOPS ITSELF"): "laps tied to depth, not graded laps, give the stop, but real data has no depth: a new addendum, a lap count the model can "
                                "set without depth labels, e.g. a curriculum that adds laps only while the answer loss still falls",
    ("hloopd", "DOES NOT STOP ITSELF"): "if pair B's seed-1 replicate passed (this summary cannot see seed 1): the graded laps give the stop, and real data "
                                        "has no hop labels: a new addendum, " + STOP_SIGNAL,
}


def masks(rows):
    d = np.array([r["depth"] for r in rows])
    return {"trained": (d >= 1) & (d <= 4), "near": (d >= 5) & (d <= 6), "far": d >= 7, "deep": d >= 5, "d1-2": d <= 2, "d1-6": d <= 6}, d


def ev(res, split="validation"):
    """The result file's eval entries of one split ({} if it has none: every tag then reads as missing)."""
    return (res.get("eval") or {}).get(split) or {}


def loop_tags(res, split="validation"):
    v = ev(res, split)
    return sorted(int(t[1:]) for t in v if t[:1] == "r" and t[1:].isdigit())


def missing(res, arms, split="validation"):
    """Tags of the scored split a pair needs but some arm lacks (an incomplete or edited result file); every looped arm needs r1..r12 with the
    answers and log-probs the stop rules are rebuilt from."""
    out = []
    for arm in arms:
        v = ev(res[arm], split)
        out += [f"{arm}:main"] * ("main" not in v)
        if arm in LOOPED:
            out += [f"{arm}:r{k}" for k in LOOPS if not {"hits", "preds", "logp"} <= set(v.get(f"r{k}") or ())]
    return out


def halted(res, rows, rule="stable", split="validation"):
    """Per-row hits (0/1) and loop counts chosen by a training-free stop rule, rebuilt from the stored per-loop answers / log-probs over r = 1..12.
    stable: the first r whose answer equals the answer at r - 1, else 12. conf: the r whose answer has the highest summed log-prob (ties: fewer)."""
    v, loops = ev(res, split), LOOPS
    hits = {r: SU.decode_hits(v[f"r{r}"]["hits"]) for r in loops}
    if rule == "conf":
        lp = {r: v[f"r{r}"]["logp"] for r in loops}
        ch = [max(loops, key=lambda r: (lp[r][i], -r)) for i in range(len(rows))]
    else:
        pr = {r: v[f"r{r}"]["preds"] for r in loops}
        ch = [next((r for r in loops[1:] if pr[r][i] == pr[r - 1][i]), loops[-1]) for i in range(len(rows))]
    return np.array([hits[c][i] for i, c in enumerate(ch)]), np.array(ch)


def at_depth(res, rows, split="validation"):
    """Per-row hits with r = the row's depth."""
    v = ev(res, split)
    return np.array([SU.decode_hits(v[f"r{r['depth']}"]["hits"])[i] for i, r in enumerate(rows)])


def step_acc(res, rows, split="validation"):
    """hloops' mechanism read (no mark): at a fixed r below a row's depth, how often the answer names hop r of the chain (hops_path[r-1])."""
    v, out = ev(res, split), {}
    for r in loop_tags(res, split):
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


def rho_marks(depth, laps, m):
    """B4, A6 and S3 are this one function: Spearman(depth 1-6, laps chosen by the stop rule) with its 2,000-resample row-bootstrap interval; passes at
    >= 0.5 with the interval above 0.3, is proved wrong at <= 0.1 (a constant side counts as wrong); depth 1-10 is reported with no mark."""
    s = m["d1-6"]
    rho, lo, hi = spearman_ci(depth[s], laps[s])
    return {"rho": rho, "rho_lo": lo, "rho_hi": hi, "rho_d1_10": spearman(depth, laps),
            "pass_rho": rho is not None and rho >= RHO - EPS and lo > RHO_LO, "wrong_rho": rho is None or rho <= RHO_WRONG + EPS}


def common(res, arm, rows, st, m, depth, vec, split="validation"):
    r = res[arm]
    stable_h, stable_l = halted(r, rows, "stable", split)
    conf_h, conf_l = halted(r, rows, "conf", split)
    ds = sorted(set(depth.tolist()))
    acc = lambda v, sel: None if v is None else st.stat({"x": v}, lambda x: x["x"], sel, ci=False)["value"]
    pct = lambda h, sel: 100 * float(h[sel].mean())
    return {"curve": {s: {f"r{k}": acc(vec(arm, f"r{k}"), m[s]) for k in loop_tags(r, split)} for s in ("trained", "near", "far")},
            "stable": {"acc": 100 * float(stable_h.mean()), **{s: pct(stable_h, m[s]) for s in ("trained", "near", "far", "deep")},
                       "loops_by_depth": {str(d): float(stable_l[depth == d].mean()) for d in ds}},
            "conf": {"acc": 100 * float(conf_h.mean()), **{s: pct(conf_h, m[s]) for s in ("trained", "near", "far", "deep")},
                     "loops_by_depth": {str(d): float(conf_l[depth == d].mean()) for d in ds}},
            "_stable": (stable_h, stable_l)}


def lesion(res, arm, st, m, vec, split="validation"):
    """Injection arms: r6 vs r6 with W = 0, all rows and near (no mark), and |W|. (Only validation is scored with W = 0: fresh_hops.py does not.)"""
    if "r6_w0" not in ev(res[arm], split):
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


def outcome_A(a):
    """Pair A: the replicate label at seed 1 (REPLICATES = A1, A2 and A3 pass), Addendum G's seed-0 wording at seed 0 (kept as it was), no label at seed >= 2."""
    v, seed = a["validity"], a["seed"]
    if not v["valid"]:
        return "VOID", "VOID (" + ", ".join(k for k in ("V1", "V2") if not v[k]) + ")"
    ok_ = a["pass_A1"] and a["pass_A2"] and a["pass_A3"]
    if seed == 0:
        return ("PASS", f"PASS: br's recipe beats plain on unseen chain lengths (seed {seed} only: needs a seed-1 replicate)") if ok_ else \
               ("FAILS", "FAILS, PROVED WRONG (" + "; ".join(a["wrong"]) + ")" if a["wrong"] else "FAILS, not shown either way (between the bars)")
    if seed != STOP_SEED:  # Addendum I defines REPLICATES as A1, A2 and A3 at seed 1; any other seed needs a new addendum
        return "NO LABEL", f"no label fixed for seed {seed}: Addendum I reads REPLICATES at seed 1 only (a seed-{seed} reading needs a new addendum)"
    return ("REPLICATES", f"REPLICATES: br's fixed-lap result holds at seed {seed} (A1, A2 and A3 pass)") if ok_ else \
           ("DOES NOT REPLICATE", "DOES NOT REPLICATE, PROVED WRONG (" + "; ".join(a["wrong"]) + ")" if a["wrong"] else
            "DOES NOT REPLICATE, not shown either way (between the bars)")


def outcome_A_stop(a):
    """Pair A at seed 1: STOPS ITSELF = A4, A5 and A6 pass (Addendum I)."""
    v = a["validity"]
    if not v["valid"]:
        return "VOID", "VOID (" + ", ".join(k for k in ("V1", "V2") if not v[k]) + ")"
    if a["stops_itself"]:
        return "STOPS ITSELF", f"STOPS ITSELF: hloop's answer-stable rule picks its own laps (A4, A5 and A6 pass at seed {a['seed']}; not expected from seed 0)"
    return "DOES NOT STOP ITSELF", "does not stop itself" + (f" (PROVED WRONG: {'; '.join(a['stop_wrong'])})" if a["stop_wrong"] else " (not shown either way)")


def outcome_X(x, r):
    """Round 2 (Addendum I), checked in this order: VOID (the control fails V1 or V2), NOT INSTALLED, STOPS ITSELF (S1, S2, S3), then WORKS (F1, F2).
    hloopi with F1 passing and F2 failing is TRADE-OFF (Addendum I fixes no decision for it: the near gain held, the trained depths lost)."""
    v, ctl = r["validity"], r["control"]
    lead = " (seed 0 only: a lead until seed 1 agrees)" if r["seed"] == 0 else f" (seed {r['seed']}: a round-2 pass counts once the seeds agree)"
    if not v["valid"]:
        return "VOID", f"VOID ({', '.join(k for k in ('V1', 'V2') if not v[k])} of {ctl}): no claim either way"
    if not r["pass_installed"]:
        return "NOT INSTALLED", f"NOT INSTALLED ({x} {r['installed_rule']} on the trained depths below {V3_TRAINED:.0f}): the recipe did not fit even the " \
                                "trained depths at this budget, or the code is wrong; not a refutation"
    if r["stops_itself"]:
        return "STOPS ITSELF", f"{x} STOPS ITSELF (S1, S2 and S3 pass)" + (", and WORKS at fixed laps (F1 and F2)" if r["works"] else "; at fixed laps it does not WORK (F1 or F2 fails)") + lead
    bad_s = "; ".join(r["wrong_S"]) or "S1, S2 or S3 not met"
    if x == "hloopd":
        return "DOES NOT STOP ITSELF", f"{x} does not stop itself ({bad_s})" + ("; it WORKS at fixed laps (F1 and F2)" if r["works"] else "; it does not WORK at fixed laps either") + lead
    if r["works"]:
        return "WORKS ONLY", f"{x} WORKS (F1 and F2 pass) but does not stop itself ({bad_s})" + lead
    if below(r["F1"]):
        return "PROVED WRONG", f"{x} does not WORK, PROVED WRONG (F1 below +{WRONG:.0f}): injection hurts br's recipe on this bed" + lead
    if r["pass_F1"]:  # the near gain held and the trained depths lost more than 2 points (F2): Addendum I fixes no decision for it
        return "TRADE-OFF", f"{x} gains at fixed laps on the near depths (F1 passes) but loses more than 2 points on the trained depths (F2 fails)" \
                            f"; not WORKS, and it does not stop itself ({bad_s}); Addendum I fixes no step for it" + lead
    return "NOT SHOWN", f"{x} does not WORK, not shown (F1 between the bars)" + lead


def analyse_X(x, res, rows, st, m, depth, vec, seed, split):
    """Addendum I's marks for one round-2 arm X against its control: Installed, F1 / F2 (WORKS), S1 / S2 / S3 (STOPS ITSELF), and the no-mark lines."""
    ctl = CONTROL[x]
    P = vec(ctl, "main")
    v = validity(st, P, m)
    c = common(res, x, rows, st, m, depth, vec, split)
    sh, sl = c.pop("_stable")
    Hv, S6, od = (0, sh), vec(x, MAIN), (0, at_depth(res[x], rows, split))
    inst_rule, inst_vec = ("at r6", S6) if x == "hloopi" else ("at r = depth", od)  # hloopi is installed at its fixed 6 laps, hloopd at the laps it was trained with
    inst = st.stat({"x": inst_vec}, lambda q: q["x"], m["trained"], ci=False)["value"]
    r = {"arm": x, "control": ctl, "seed": seed, "validity": v, "installed_rule": inst_rule, "installed": inst, "pass_installed": inst >= V3_TRAINED - EPS,
         "F1": st.diff(S6, P, m["near"]), "F2": st.diff(S6, P, m["trained"], ci=False),
         "S1": st.diff(Hv, P, m["near"]), "S2": st.diff(Hv, P, m["trained"], ci=False), **rho_marks(depth, sl, m),
         "far_r6_minus_control": st.diff(S6, P, m["far"], ci=False), "far_stop_minus_control": st.diff(Hv, P, m["far"], ci=False),
         "lesion": lesion(res, x, st, m, vec, split), **c}
    if x == "hloopd":  # no mark: the mechanism read, hloopd at the laps it was trained with (as pair B's B3)
        r |= {"near_depth_minus_control": st.diff(od, P, m["near"]), "far_depth_minus_control": st.diff(od, P, m["far"], ci=False)}
    r["S3"] = {"value": r["rho"], "lo": r["rho_lo"], "hi": r["rho_hi"]}
    r["pass_F1"], r["pass_S1"], r["pass_S3"] = ok(r["F1"], GAIN), ok(r["S1"], GAIN), r["pass_rho"]
    r["pass_F2"], r["pass_S2"] = (r[k]["value"] >= -HARM - EPS for k in ("F2", "S2"))
    r["works"] = bool(r["pass_F1"] and r["pass_F2"])
    r["stops_itself"] = bool(r["pass_S1"] and r["pass_S2"] and r["pass_S3"])
    r["wrong_F"] = [w for w, c_ in (("F1: near r6 gain over the control below +1", below(r["F1"])),) if c_]
    r["wrong_S"] = [w for w, c_ in (("S1: near stop-rule gain over the control below +1", below(r["S1"])),
                                    ("S3: Spearman(depth 1-6, laps) <= 0.1", r["wrong_rho"])) if c_]
    r["key"], r["outcome"] = outcome_X(x, r)
    r["next"] = NEXT2[(x, r["key"])]
    return r


def readout(x, y, res, rows, st, m, depth, vec, split):
    """One-change readout x - y (no mark): paired differences on the same rows at r6 and under the answer-stable rule, near and far, with each arm's
    Spearman(depth 1-6, answer-stable laps)."""
    (hx, lx), (hy, ly) = halted(res[x], rows, "stable", split), halted(res[y], rows, "stable", split)
    diffs = lambda a, b: {s: st.diff(a, b, m[s]) for s in ("near", "far")}
    return {"what": next(w for a, b, w in READOUTS if (a, b) == (x, y)), "r6": diffs(vec(x, MAIN), vec(y, MAIN)), "stable": diffs((0, hx), (0, hy)),
            "rho": {x: rho_marks(depth, lx, m), y: rho_marks(depth, ly, m)}}


def mark_flags(o):
    """{group: {mark: passes}} of one analysis: pair A (V1, V2, A1-A3, and A4-A6 where they are marked), pair B (V1, V2, V3, B1-B4) and each round-2 arm
    (V1, V2, Installed, F1, F2, S1-S3). A mark whose interval could not be built counts as not passing."""
    out = {}
    if "A" in o:
        a, v = o["A"], o["A"]["validity"]
        out["A"] = {"V1": v["V1"], "V2": v["V2"], "A1": a["pass_A1"], "A2": a["pass_A2"], "A3": a["pass_A3"],
                    **({"A4": a["pass_A4"], "A5": a["pass_A5"], "A6": a["pass_A6"]} if a["stop_marked"] else {})}
    if "B" in o:
        b, v = o["B"], o["B"]["validity"]
        out["B"] = {"V1": v["V1"], "V2": v["V2"], "V3": b["pass_V3"], "B1": b["pass_B1"], "B2": b["pass_B2"], "B3": b["pass_B3"], "B4": b["pass_B4"]}
    for x, r in o.get("R2", {}).items():
        v = r["validity"]
        out[x] = {"V1": v["V1"], "V2": v["V2"], "Installed": r["pass_installed"], "F1": r["pass_F1"], "F2": r["pass_F2"],
                  "S1": r["pass_S1"], "S2": r["pass_S2"], "S3": r["pass_S3"]}
    return {g: {k: bool(x) for k, x in f.items()} for g, f in out.items()}


def compare_fresh(fresh, ref=None):
    """Addendum I, item 4: every mark of a fresh-row analysis against the same mark on the validation rows (ref: the validation analysis, same seed). A mark
    that passed on validation is "held on fresh rows" if it passes there and "did not hold on fresh rows" if it fails there, and no claim rests on it; a mark
    that did not pass on validation says nothing either way. Without ref nothing is called held or not held. Per group (A, B, each round-2 arm):
    {"marks": {mark: {"validation": bool | None, "fresh": bool, "status": str}}, "held": [...], "not_held": [...], "summary": str}."""
    rf, out = mark_flags(ref) if ref is not None else {}, {}
    for g, ff in mark_flags(fresh).items():
        vf, marks = rf.get(g), {}
        for k, fv in ff.items():
            vv = None if vf is None else vf.get(k)
            marks[k] = {"validation": vv, "fresh": fv, "status": "no validation read to compare with" if vv is None else
                        (HELD if fv else NOT_HELD) if vv else "did not pass on validation: no claim either way"}
        held, not_held = ([k for k, m in marks.items() if m["status"] == s] for s in (HELD, NOT_HELD))
        if vf is None:
            summary = "no validation read of this group was given (--validation): no mark is called held or not held, and no step follows from these values"
        elif not_held:
            summary = f"{', '.join(not_held)} {NOT_HELD}; no claim rests on it" + (f" ({', '.join(held)} held)" if held else "")
        elif held:
            summary = f"every mark that passed on validation {HELD} ({', '.join(held)}); this is a check on the validation read, not a new decision"
        else:
            summary = "no mark passed on validation: nothing for the fresh rows to confirm"
        out[g] = {"marks": marks, "held": held, "not_held": not_held, "summary": summary}
    return out


def analyse(res, rows, seed=0, split="validation", ref=None):
    """ref (fresh split only): the validation analysis of the same seed, the reference the fresh marks are held against (compare_fresh)."""
    allres = {a: r for (a, s), r in res.items() if s == seed}
    aborted = sorted(a for a, r in allres.items() if r.get("aborted"))
    res = {a: r for a, r in allres.items() if not r.get("aborted")}
    st = SU.Stats(None, rows)
    m, depth = masks(rows)
    R = SU.Runs({(a, seed): r for a, r in res.items()})
    vec = lambda arm, tag: R.vec(arm, seed, split, tag)
    out = {"seed": seed, "split": split, "n": len(rows), "arms": sorted(res), "aborted": aborted, "floor": FLOOR, "by_depth": {}, "not_computed": {}}
    for d in sorted(set(depth.tolist())):
        sel = depth == d
        out["by_depth"][str(d)] = {"n": int(sel.sum()), **{a: st.stat({"x": vec(a, "main")}, lambda x: x["x"], sel, ci=False)["value"] for a in res if vec(a, "main") is not None}}

    def gap(arms):  # why a comparison cannot be made: an arm that is gone (missing or aborted), else the tags it lacks ("" if it can be made)
        gone = [a for a in arms if a not in res]
        return ", ".join([f"{a} {'aborted' if a in aborted else 'missing'}" for a in gone] + ([] if gone else missing(res, arms, split)))

    for pair, arms in (("A", ("hloop", "hplain")), ("B", ("hloops", "hplains"))):
        if gap(arms):
            out["not_computed"][pair] = gap(arms)
    if "A" not in out["not_computed"]:  # pair A
        P, S6, S1 = vec("hplain", "main"), vec("hloop", MAIN), vec("hloop", "r1")
        v = validity(st, P, m)
        a = {"seed": seed, "validity": v, "A1": st.diff(S6, P, m["near"]), "A2": st.diff(S6, P, m["trained"], ci=False), "A3": st.diff(S6, S1, m["near"]),
             "far_r6_minus_plain": st.diff(S6, P, m["far"], ci=False)}
        c = common(res, "hloop", rows, st, m, depth, vec, split)
        sh, sl = c.pop("_stable")
        a |= c
        a["pass_A1"], a["pass_A3"] = ok(a["A1"], GAIN), ok(a["A3"], RISE)
        a["pass_A2"] = a["A2"]["value"] >= -HARM - EPS
        a["wrong"] = [w for w, c in (("A1: near gain over hplain below +1", below(a["A1"])), ("A3: near r6 - r1 below +1", below(a["A3"]))) if c]
        a["key"], a["outcome"] = outcome_A(a)
        # Addendum I's stop-rule marks for hloop (the answer-stable rule over r = 1-12 against hplain): marks at seed 1 only. Seed 0 was seen before they were
        # fixed, and no seed >= 2 reading is fixed: those values are reported, never marked (and carry no PASS / FAIL flag, not even in --json).
        Hv, rm = (0, sh), rho_marks(depth, sl, m)
        a |= {"A4": st.diff(Hv, P, m["near"]), "A5": st.diff(Hv, P, m["trained"], ci=False), "stop_marked": seed == STOP_SEED,
              **{k: rm[k] for k in ("rho", "rho_lo", "rho_hi", "rho_d1_10")}}  # values only, until the seed is the one the marks are read at
        a["A6"] = {"value": a["rho"], "lo": a["rho_lo"], "hi": a["rho_hi"]}
        if a["stop_marked"]:
            a |= {"pass_rho": rm["pass_rho"], "wrong_rho": rm["wrong_rho"]}  # a verdict-shaped flag exists only where the mark is read
            a["pass_A4"], a["pass_A5"], a["pass_A6"] = ok(a["A4"], GAIN), a["A5"]["value"] >= -HARM - EPS, a["pass_rho"]
            a["replicates"] = a["key"] == "REPLICATES"
            a["stops_itself"] = bool(v["valid"] and a["pass_A4"] and a["pass_A5"] and a["pass_A6"])
            a["stop_wrong"] = [w for w, c in (("A4: near halting gain over hplain below +1", below(a["A4"])), ("A6: Spearman(depth 1-6, laps) <= 0.1", a["wrong_rho"])) if c]
            a["stop_key"], a["stop_outcome"] = outcome_A_stop(a)
            a["next"] = NEXT_A["VOID" if a["key"] == "VOID" else "DOES NOT REPLICATE" if not a["replicates"] else
                               "REPLICATES + STOPS ITSELF" if a["stops_itself"] else "REPLICATES"]
        out["A"] = a
    if "B" not in out["not_computed"]:  # pair B
        P = vec("hplains", "main")
        v = validity(st, P, m)
        c = common(res, "hloops", rows, st, m, depth, vec, split)
        sh, sl = c.pop("_stable")
        Hv, od = (0, sh), (0, at_depth(res["hloops"], rows, split))
        v3 = st.stat({"x": od}, lambda x: x["x"], m["trained"], ci=False)["value"]
        rm = rho_marks(depth, sl, m)
        b = {"validity": v, "seed": seed, "steps": res["hloops"].get("steps_stage1"), "V3_trained_at_depth": v3, "pass_V3": v3 >= V3_TRAINED - EPS,
             "B1": st.diff(Hv, P, m["near"]), "B2": st.diff(Hv, P, m["trained"], ci=False), "B3": st.diff(od, P, m["near"]),
             **{k: rm[k] for k in ("rho", "rho_lo", "rho_hi", "rho_d1_10")},
             "far_halting_minus_plain": st.diff(Hv, P, m["far"], ci=False), "far_depth_minus_plain": st.diff(od, P, m["far"], ci=False),
             "step_acc": step_acc(res["hloops"], rows, split), "lesion": lesion(res, "hloops", st, m, vec, split), **c}
        b["pass_B1"], b["pass_B3"] = ok(b["B1"], GAIN), ok(b["B3"], GAIN)
        b["pass_B2"] = b["B2"]["value"] >= -HARM - EPS
        b["pass_B4"] = rm["pass_rho"]
        b["wrong"] = [w for w, c_ in (("B1: near halting gain over hplains below +1", below(b["B1"])),
                                      ("B3: near r = depth gain below +1", below(b["B3"])),
                                      ("B4: Spearman(depth 1-6, loops) <= 0.1", rm["wrong_rho"])) if c_]
        b["key"], b["outcome"] = outcome_B(b)
        b["next"] = NEXT[b["key"]]
        out["B"] = b
    out["R2"], out["readouts"] = {}, {}  # Addendum I: round 2 (only for an arm that exists at this seed), then the one-change readouts
    for x, ctl in CONTROL.items():
        if x in allres:
            if gap((x, ctl)):
                out["not_computed"][x] = gap((x, ctl))
            else:
                out["R2"][x] = analyse_X(x, res, rows, st, m, depth, vec, seed, split)
    for x, y, _ in READOUTS:
        if x in allres and y in allres:
            if gap((x, y)):
                out["not_computed"][f"{x} - {y}"] = gap((x, y))
            else:
                out["readouts"][f"{x} - {y}"] = readout(x, y, res, rows, st, m, depth, vec, split)
    if split == "fresh":  # the decision steps belong to the validation read: no step follows from the fresh rows, only a held / did not hold verdict per mark
        for g in (out.get("A"), out.get("B"), *out["R2"].values()):
            if g and "next" in g:
                g["next"] = None
        out["held"] = compare_fresh(out, ref)
    return out


def report(o):
    L = []
    P = L.append
    f2, sg, ci = SU.f2, SU.sg, SU.ci_txt
    mk = lambda x: SU.ND if x is None else "PASS" if x else "FAIL"
    fresh = o["split"] != "validation"
    if fresh:
        P(f"SPLIT: {o['split']} rows, scored once (Addendum I, item 4): the same marks, the same functions. A mark that passed on validation and fails here "
          "did not hold on fresh rows, and no claim rests on it. The decision lines of the validation read (its outcome and next step) are not printed here: "
          "each pair / arm gets a verdict per mark instead, and no step follows from it.")

    def verdict(g, tag):  # fresh rows: what replaces OUTCOME / NEXT (Addendum I, item 4)
        h = o["held"][g]
        P(f"   OUTCOME {tag} (fresh rows): {h['summary']}")
        for k, mk_ in h["marks"].items():
            P(f"      {k}: " + ("validation " + mk(mk_["validation"]) + ", " if mk_["validation"] is not None else "") + f"fresh {mk(mk_['fresh'])}: {mk_['status']}")
    P("ADDENDUM G, ROUND 1: THE HOPS BED (percent; trained = depth 1-4; near = depth 5-6, the marked unseen depths; far = depth 7-10, no mark;")
    P("not comparable with any village number)")
    P(f"seed {o['seed']}, {o['n']} {o['split']} rows; arms: {', '.join(o['arms'])}" + (f"; ABORTED: {', '.join(o['aborted'])}" if o["aborted"] else ""))
    P(f"floor: naming a random place of the row scores {o['floor']:.1f} at every depth")

    def curves(x):
        for s in ("trained", "near", "far"):
            P(f"   {s} accuracy by fixed loop count: " + "  ".join(f"{k} {f2(v)}" for k, v in x["curve"][s].items()))
        for name in ("stable", "conf"):
            h = x[name]
            P(f"   halting ({'answer-stable' if name == 'stable' else 'max confidence, no mark'}): {f2(h['acc'])} all, {f2(h['trained'])} trained, "
              f"{f2(h['near'])} near, {f2(h['far'])} far; loops by depth " + " ".join(f"d{d}:{v:.2f}" for d, v in h["loops_by_depth"].items()))

    def lesion_line(ls):
        P(f"   no mark: W = 0 lesion: r6 {f2(ls['r6'])} -> {f2(ls['r6_w0'])} (near {f2(ls['r6_near'])} -> {f2(ls['r6_w0_near'])}); |W| = {f2(ls['weight_norm'])}")

    def rho_line(tag, x, bars):
        P(f"   {tag} Spearman(depth 1-6, halting loops) = {f2(x['rho'])} [{f2(x['rho_lo'])}, {f2(x['rho_hi'])}]{bars}; depth 1-10, no mark: {f2(x['rho_d1_10'])}")

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
        if not fresh:
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
            lesion_line(b["lesion"])
        P("   step accuracy (answer at loop r names hop r, rows deeper than r): " + "  ".join(f"{k} {f2(x)}" for k, x in b["step_acc"].items()))
        curves(b)
        if fresh:
            verdict("B", "B")
        else:
            P(f"   OUTCOME B: {b['outcome']}")
            P(f"   NEXT (fixed in Addendum G): {b['next']}")
    P("accuracy by depth (each arm's main tag): " + "  ".join(f"d{d}: " + ",".join(f"{a} {f2(x.get(a))}" for a in o["arms"] if a in x) for d, x in o["by_depth"].items()))
    # ---- Addendum I, appended after the round-1 text (which stays as Addendum G fixed it)
    if "A" in o:
        a = o["A"]
        P("-- pair A, Addendum I's stop-rule marks: hloop under the answer-stable stop rule vs hplain")
        if not a["stop_marked"]:  # seed 0 was seen before the marks were fixed, no other seed but 1 is fixed: values only
            why = SEED0_NOTE if a["seed"] == 0 else f"no mark fixed for seed {a['seed']}: Addendum I reads A4-A6 at seed {STOP_SEED} only"
            note = f"  ({why})"
            P(f"   A4 near halting - hplain = {sg(a['A4']['value'])}{ci(a['A4'])}{note}")
            P(f"   A5 trained halting - hplain = {sg(a['A5']['value'])}{note}")
            rho_line("A6", a, note)
        else:
            P(f"   {mk(a['pass_A4'])} A4 near halting - hplain = {sg(a['A4']['value'])}{ci(a['A4'])} (>= +{GAIN:.0f}, interval above 0; proved wrong below +{WRONG:.0f})")
            P(f"   {mk(a['pass_A5'])} A5 trained halting - hplain = {sg(a['A5']['value'])} (>= -{HARM:.0f})")
            rho_line(f"{mk(a['pass_A6'])} A6", a, f" (>= {RHO}, interval above {RHO_LO}; proved wrong <= {RHO_WRONG})")
            if not fresh:
                P(f"   OUTCOME A (stop rule): {a['stop_outcome']}")
                P(f"   NEXT (fixed in Addendum I): {a['next']}")
        if fresh:
            verdict("A", "A")
    for x, ctl in CONTROL.items():
        if x in o["not_computed"]:
            P(f"-- round 2: {x} vs {ctl}: not computed ({o['not_computed'][x]})")
            P(f"   OUTCOME {x}: not computed")
        if x not in o["R2"]:
            continue
        r, v, xs = o["R2"][x], o["R2"][x]["validity"], f"{x}(r6)"
        P(f"-- round 2 (Addendum I): {x} ({'hloop + re-injection' if x == 'hloopi' else 'hloopi with laps tied to depth'}) vs {ctl}; one seed: a pass is a lead until seed 1 agrees")
        P(f"   {mk(v['V1'])} V1 {ctl} depth 1-2 = {f2(v['plain_d1_2'])} (>= {V1_SHALLOW:.0f});  {mk(v['V2'])} V2 {ctl} near = {f2(v['plain_near'])} (<= {V2_NEAR:.0f})")
        P(f"   {mk(r['pass_installed'])} Installed: {x} {r['installed_rule']}, trained depths = {f2(r['installed'])} (>= {V3_TRAINED:.0f})")
        P(f"   {mk(r['pass_F1'])} F1 near {xs} - {ctl} = {sg(r['F1']['value'])}{ci(r['F1'])} (>= +{GAIN:.0f}, interval above 0; proved wrong below +{WRONG:.0f})")
        P(f"   {mk(r['pass_F2'])} F2 trained {xs} - {ctl} = {sg(r['F2']['value'])} (>= -{HARM:.0f})")
        P(f"   {mk(r['pass_S1'])} S1 near {x} halting - {ctl} = {sg(r['S1']['value'])}{ci(r['S1'])} (>= +{GAIN:.0f}, interval above 0; proved wrong below +{WRONG:.0f})")
        P(f"   {mk(r['pass_S2'])} S2 trained {x} halting - {ctl} = {sg(r['S2']['value'])} (>= -{HARM:.0f})")
        rho_line(f"{mk(r['pass_S3'])} S3", r, f" (>= {RHO}, interval above {RHO_LO}; proved wrong <= {RHO_WRONG})")
        P(f"   WORKS (F1 and F2): {mk(r['works'])};  STOPS ITSELF (S1, S2 and S3): {mk(r['stops_itself'])}")
        P(f"   no mark: far {xs} - {ctl} = {sg(r['far_r6_minus_control']['value'])}; far halting - {ctl} = {sg(r['far_stop_minus_control']['value'])}")
        if x == "hloopd":
            P(f"   no mark: near r = depth - {ctl} = {sg(r['near_depth_minus_control']['value'])}{ci(r['near_depth_minus_control'])}; "
              f"far r = depth - {ctl} = {sg(r['far_depth_minus_control']['value'])}")
        if r["lesion"]:
            lesion_line(r["lesion"])
        curves(r)
        if fresh:
            verdict(x, x)
        else:
            P(f"   OUTCOME {x}: {r['outcome']}")
            P(f"   NEXT (fixed in Addendum I): {r['next']}")
    if o["readouts"] or any(" - " in k for k in o["not_computed"]):
        P("-- one-change readouts, Addendum I (no mark; paired 95% intervals on the same rows; the arms share a batch stream but are not compute-matched to each other)")
        for x, y, what in READOUTS:
            k = f"{x} - {y}"
            if k in o["not_computed"]:
                P(f"   {k} ({what}): not computed ({o['not_computed'][k]})")
            if k not in o["readouts"]:
                continue
            d = o["readouts"][k]
            fmt = lambda t, s: f"{s} {sg(d[t][s]['value'])}{ci(d[t][s])}"
            P(f"   {k} ({what}): at r6: {fmt('r6', 'near')}, {fmt('r6', 'far')}; answer-stable: {fmt('stable', 'near')}, {fmt('stable', 'far')}")
            P("      Spearman(depth 1-6, answer-stable laps): " + ", ".join(f"{n} {f2(q['rho'])} [{f2(q['rho_lo'])}, {f2(q['rho_hi'])}]" for n, q in d["rho"].items()))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--data", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--split", choices=SPLITS, default="validation", help="rows from DATA/<split>.jsonl and evals from res['eval'][split] (fresh: fresh_hops.py's files)")
    ap.add_argument("--validation", help="with --split fresh: the validation runs (result files, as OUT/runs) whose marks the fresh marks are held against; "
                                         "their rows are DATA/validation.jsonl, at the same --seed")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.validation and a.split != "fresh":
        ap.error("--validation only goes with --split fresh")
    load = lambda d: {k: r for k, r in SU.load_results(d)[0].items() if k[0] in ("hplain", "hloop", "hplains", "hloops", "hloopi", "hloopd")}
    rows = SU.load_rows(Path(a.data) / f"{a.split}.jsonl")
    if rows is None:
        ap.error(f"{Path(a.data) / (a.split + '.jsonl')} not found")
    ref = None
    if a.validation:  # the validation read of the same seed: the reference for "held on fresh rows"
        vrows = SU.load_rows(Path(a.data) / "validation.jsonl")
        if vrows is None:
            ap.error(f"{Path(a.data) / 'validation.jsonl'} not found (--validation needs the validation rows)")
        ref = analyse(load(a.validation), vrows, a.seed, "validation")
    o = analyse(load(a.out), rows, a.seed, a.split, ref)
    conv = lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else bool(x) if isinstance(x, np.bool_) else str(x)
    print(json.dumps(o, indent=1, default=conv) if a.json else report(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
