"""Hand-built boundary tests for audit/gate_calculator.py.

Every case below is constructed by hand from the preregistration and the
ct20-v1.1 rulings.  No experiment output is used and no builder module is
imported, so these tests are written entirely before results exist.

Run:  python3.12 -B test_gate_calculator.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gate_calculator as G   # noqa: E402

RESULTS: list[dict] = []


def ok(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append({"test": name, "pass": bool(condition), "detail": detail})
    print(("PASS  " if condition else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))


def eq(name: str, got, want) -> None:
    ok(name, got == want, f"got {got!r} want {want!r}")


# =============================================================================
# 1. Ruling C9 -- the exact never_started predicate and its tolerance boundary
# =============================================================================
# r = (L_initial - L_final) / L_initial, never_started = (r < 0.10 - 1e-12) AND
# (E_fit_final >= 0.80).  All of these hold E_fit_final = 0.90 >= 0.80 so the
# improvement term alone decides.

# The float artifact the ruling names explicitly: (1.0-0.90)/1.0 evaluates to
# 0.09999999999999998, which IS < 0.10, so a naive test would call this a failed
# startup.  With the 1e-12 tolerance it is not.
r_artifact = (1.0 - 0.90) / 1.0
ok("C9 float artifact: (1.0-0.90)/1.0 really is < 0.10 in binary64",
   r_artifact < 0.10, f"r={r_artifact!r}")
eq("C9 L_initial=1.0, L_final=0.90 is NOT never_started (ruling C9 verbatim)",
   G.classify_startup(1.0, 0.90, 0.90, 0.90), "started_not_yet_learned")

THRESH = 0.10 - 1e-12


def with_improvement(r: float, E_fit: float = 0.90, E_q: float = 0.90) -> str:
    """Build losses whose exact binary64 ratio is r: L_initial=1.0, L_final=1-r."""
    return G.classify_startup(1.0, 1.0 - r, E_fit, E_q)


eq("C9 r exactly on the tolerance boundary (0.10-1e-12) is NOT never_started "
   "(strict <)", with_improvement(THRESH), "started_not_yet_learned")
eq("C9 r just INSIDE the tolerance (0.10-1e-13, i.e. below 0.10 but within 1e-12) "
   "is NOT never_started", with_improvement(0.10 - 1e-13), "started_not_yet_learned")
eq("C9 r just OUTSIDE the tolerance (0.10-1e-11) IS never_started",
   with_improvement(0.10 - 1e-11), "never_started")
eq("C9 r exactly 0.10 is NOT never_started", with_improvement(0.10),
   "started_not_yet_learned")
eq("C9 r far below (0.01) IS never_started", with_improvement(0.01), "never_started")
eq("C9 negative improvement (loss rose) IS never_started",
   G.classify_startup(1.0, 1.5, 0.90, 0.90), "never_started")

# The AND: a tiny improvement with a good fitting E is NOT never_started.
eq("C9 conjunction: r=0.01 but E_fit_final=0.79 (<0.80) is not never_started",
   with_improvement(0.01, E_fit=0.79), "started_not_yet_learned")
eq("C9 conjunction: E_fit_final exactly 0.80 with r=0.01 IS never_started "
   "(>= is inclusive)", with_improvement(0.01, E_fit=0.80), "never_started")

# No tolerance on the other E thresholds (ruling C9, last paragraph).
eq("C9 no tolerance elsewhere: E_fit_final=0.25 exactly counts as learned",
   with_improvement(0.50, E_fit=0.25, E_q=0.50), "learned_with_generalization")
eq("C9 no tolerance elsewhere: E_fit_final just above 0.25 is not learned",
   with_improvement(0.50, E_fit=0.25 + 1e-15, E_q=0.50), "started_not_yet_learned")
eq("C9 query boundary: E_fit=0.25, E_query=0.50 exactly is generalization",
   with_improvement(0.50, E_fit=0.25, E_q=0.50), "learned_with_generalization")
eq("C9 query boundary: E_query just above 0.50 fails to transfer",
   with_improvement(0.50, E_fit=0.25, E_q=0.50 + 1e-15),
   "learned_and_failed_to_transfer")

# =============================================================================
# 2. The unchanged initial-floor boundary and zero denominators
# =============================================================================
eq("initially_at_floor at exactly L_initial=1e-8",
   G.classify_startup(1e-8, 1e-9, 0.90, 0.90), "initially_at_floor")
eq("initially_at_floor just above 1e-8 falls through to the predicate",
   G.classify_startup(1e-8 + 1e-23, 1e-9, 0.10, 0.10), "learned_with_generalization")
eq("initially_at_floor is decided before the fitting-E branches",
   G.classify_startup(1e-8, 1e-9, 0.90, 0.90), "initially_at_floor")
eq("zero denominator: L_initial=0.0 is initially_at_floor, never a division",
   G.classify_startup(0.0, 0.0, 0.90, 0.90), "initially_at_floor")
ok("zero denominator never raises",
   G.classify_startup(0.0, 0.0, None, None) == "initially_at_floor",
   "and resolves without any evaluator quantity")

# =============================================================================
# 3. Failure / incomplete / pending precedence (ruling C9 + C10)
# =============================================================================
eq("numerical_failure status takes precedence over everything",
   G.classify_startup(1.0, 0.0, 0.0, 0.0, status="numerical_failure"),
   "numerical_failure")
eq("infrastructure_incomplete takes precedence",
   G.classify_startup(1.0, 0.0, 0.0, 0.0, status="infrastructure_incomplete"),
   "infrastructure_incomplete")
eq("NaN loss is invalid, never a successful startup",
   G.classify_startup(float("nan"), 0.5, 0.1, 0.1), "invalid_measurement")
eq("Inf loss is invalid, never a successful startup",
   G.classify_startup(float("inf"), 0.5, 0.1, 0.1), "invalid_measurement")
eq("NaN evaluator E is invalid, never a successful startup",
   G.classify_startup(1.0, 0.5, float("nan"), 0.1), "invalid_measurement")
eq("missing evaluator E is pending (ruling C10 accepts pending in fit output)",
   G.classify_startup(1.0, 0.5, None, None), "pending_evaluator_E")
eq("missing query E alone is still pending",
   G.classify_startup(1.0, 0.5, 0.1, None), "pending_evaluator_E")
eq("missing losses are invalid, not pending",
   G.classify_startup(None, None, 0.1, 0.1), "invalid_measurement")

# =============================================================================
# 4. Result-table builders for the calibration gate
# =============================================================================
C_WORLDS = [f"cw{i}" for i in range(4)]         # 4 validation C worlds
CTL_WORLDS = [("ow0", "o"), ("nw0", "n")]       # 1 O + 1 N validation world


def build(e32_by_arm, e512_by_arm, control_e512=0.01, e_initial=10.0,
          tier="L", integrity=None, drop=(), status_override=None,
          include_train=True):
    """A complete, valid result table unless a keyword says otherwise.

    `e32_by_arm[arm]` and `e512_by_arm[arm]` are 12-long lists, one per C case in
    world-major/seed-minor order.  `e_initial` is deliberately huge so the 25%
    relative-improvement half of the learned test passes unless E_512 is large.
    """
    cases = []
    for arm in G.ARMS:
        k = 0
        for w in C_WORLDS:
            for seed in G.SEEDS:
                e32 = e32_by_arm[arm][k]
                e512 = e512_by_arm[arm][k]
                k += 1
                if (w, seed, arm) in drop:
                    continue
                cases.append({
                    "world_public_id": w, "outer_split": "validation",
                    "family": "c", "seed": seed, "arm": arm,
                    "status": (status_override or {}).get((w, seed, arm), "complete"),
                    "E": {32: e32, 64: e32, 128: e512, 256: e512, 512: e512},
                    "E_initial": e_initial,
                    "L_initial": 1.0, "L_final": 0.1, "E_fit_final": 0.1,
                })
        for w, fam in CTL_WORLDS:
            for seed in G.SEEDS:
                v = control_e512
                if isinstance(control_e512, dict):
                    v = control_e512.get((w, seed, arm), 0.01)
                cases.append({
                    "world_public_id": w, "outer_split": "validation",
                    "family": fam, "seed": seed, "arm": arm,
                    "status": (status_override or {}).get((w, seed, arm), "complete"),
                    "E": {32: v, 64: v, 128: v, 256: v, 512: v},
                    "E_initial": e_initial,
                    "L_initial": 1.0, "L_final": 0.1, "E_fit_final": 0.1,
                })
    if include_train:      # train worlds are diagnostic only and must not decide
        for seed in G.SEEDS:
            cases.append({
                "world_public_id": "tw0", "outer_split": "train", "family": "c",
                "seed": seed, "arm": "G", "status": "complete",
                "E": {b: 0.0 for b in G.BUDGETS}, "E_initial": 10.0,
                "L_initial": 1.0, "L_final": 0.1, "E_fit_final": 0.0,
            })
    # Ruling R3: `complete_wave_valid` attests that BOTH train and validation
    # jobs ran.  Defaulted True here so the pre-existing tests keep testing what
    # they were written to test; the R3 block below tests its absence directly.
    base_integrity = {"accounting_valid": True, "audit_passed": True,
                      "timing_ok": True, "complete_wave_valid": True}
    base_integrity.update(integrity or {})
    return {"version": G.VERSION, "tier": tier,
            "integrity": base_integrity, "cases": cases}


def flat(v):
    return {"G": [v] * 12, "T": [v] * 12}


# ---- 4a. advance window --------------------------------------------------------
adv = G.evaluate_tier(build(flat(0.40), flat(0.30)))
eq("advance window: median E_32=0.40>=0.15 and median E_512=0.30<=0.50",
   adv["verdict"], "advance")
ok("advance does not escalate to H", adv["escalates_to_H"] is False)
ok("train worlds are excluded from the gate",
   adv["advance"]["median_E32_by_arm"]["G"] == 0.40,
   "a train world with E=0 would have dragged the median down")

# ---- 4b. the exact advance thresholds ------------------------------------------
eq("advance boundary: better-arm median E_32 exactly 0.15 holds (>=)",
   G.evaluate_tier(build(flat(0.15), flat(0.30)))["verdict"], "advance")
eq("advance boundary: better-arm median E_32 just below 0.15 is inconclusive",
   G.evaluate_tier(build(flat(0.15 - 1e-16), flat(0.30)))["verdict"],
   "calibration-inconclusive")
eq("advance boundary: median E_512 exactly 0.50 holds (<=)",
   G.evaluate_tier(build(flat(0.40), flat(0.50)))["verdict"], "advance")

# "better" = the LOWER median at B=32, so a good arm cannot be rescued by a bad one
mixed = build({"G": [0.05] * 12, "T": [0.90] * 12}, flat(0.30))
res_mixed = G.evaluate_tier(mixed)
eq("'better arm' is the LOWER median at B=32, so G=0.05 blocks the window",
   res_mixed["advance"]["better_arm_at_32"], "G")
ok("a low-median arm cannot be rescued by the other arm's high median",
   res_mixed["verdict"] != "advance", res_mixed["verdict"])

# ---- 4c. too easy --------------------------------------------------------------
easy = G.evaluate_tier(build(flat(0.04), flat(0.04)))
eq("too easy triggers on median E_32<=0.05, 12/12 E_32<=0.10, median E_512<=0.05",
   easy["verdict"], "too-easy")
ok("too easy NEVER escalates to H (ruling A3 step 2)",
   easy["escalates_to_H"] is False)
eq("too easy boundary: median E_32 exactly 0.05 triggers (<=)",
   G.evaluate_tier(build(flat(0.05), flat(0.05)))["verdict"], "too-easy")
# 10/12 rule: two cases above 0.10 still leaves exactly 10, but the median moves.
e32 = {"G": [0.01] * 10 + [0.5, 0.5], "T": [0.9] * 12}
eq("too easy: exactly 10/12 cases with E_32<=0.10 still triggers",
   G.evaluate_tier(build(e32, flat(0.01)))["verdict"], "too-easy")
e32b = {"G": [0.01] * 9 + [0.5, 0.5, 0.5], "T": [0.9] * 12}
ok("too easy: only 9/12 cases with E_32<=0.10 does not trigger",
   G.evaluate_tier(build(e32b, flat(0.01)))["too_easy"]["triggers"] is False)

# ---- 4d. too hard --------------------------------------------------------------
hard = G.evaluate_tier(build(flat(0.90), flat(0.90)))
eq("too hard: no learned C case in either arm", hard["verdict"], "too-hard")
ok("too hard at tier L DOES escalate to H (ruling A3 step 2)",
   hard["escalates_to_H"] is True)
# exactly 9/12 learned in one arm means NOT too hard
e512 = {"G": [0.30] * 9 + [0.90] * 3, "T": [0.90] * 12}
r9 = G.evaluate_tier(build(flat(0.40), e512))
eq("not too hard when exactly one arm has 9/12 learned C cases",
   r9["learned"]["by_arm"]["G"]["learned"], 9)
ok("9/12 learned stops the too-hard rule", r9["verdict"] != "too-hard", r9["verdict"])
e512b = {"G": [0.30] * 8 + [0.90] * 4, "T": [0.90] * 12}
eq("8/12 learned in the best arm is too hard",
   G.evaluate_tier(build(flat(0.40), e512b))["verdict"], "too-hard")

# the 25% relative-improvement half of the learned test.  E_initial=0.4 keeps
# both candidate E_512 values below the 0.50 absolute mark, so only the relative
# half of the conjunction is under test here.
learn_ok, _ = G.is_learned_case({"status": "complete", "E": {512: 0.30},
                                 "E_initial": 0.4})
ok("learned case: E_512 exactly 25% below E_initial counts (0.30 vs 0.40)", learn_ok)
learn_no, why = G.is_learned_case({"status": "complete", "E": {512: 0.32},
                                   "E_initial": 0.4})
ok("learned case: only 20% below E_initial does not count (0.32 vs 0.40)",
   not learn_no, why)
learn_edge, why2 = G.is_learned_case(
    {"status": "complete", "E": {512: 0.30000000000000004 + 1e-16},
     "E_initial": 0.4})
ok("learned case: one ulp above 0.75*E_initial does not count", not learn_edge, why2)
learn_fail, why3 = G.is_learned_case({"status": "numerical_failure",
                                      "E": {512: 0.10}, "E_initial": 10.0})
ok("learned case: a failed status is never learned, whatever its E", not learn_fail, why3)
learn_e, why_e = G.is_learned_case({"status": "complete", "E": {512: 0.50},
                                    "E_initial": 100.0})
ok("learned case: E_512 exactly 0.50 passes the absolute half", learn_e)
learn_e2, _ = G.is_learned_case({"status": "complete", "E": {512: 0.50 + 1e-16},
                                 "E_initial": 100.0})
ok("learned case: E_512 just above 0.50 fails the absolute half", not learn_e2)

# ---- 4e. control-competence prerequisite ---------------------------------------
bad_ctl = {(w, s, a): 0.9 for w, _ in CTL_WORLDS for s in G.SEEDS for a in G.ARMS}
pre = G.evaluate_tier(build(flat(0.40), flat(0.30), control_e512=bad_ctl))
eq("control prerequisite failure is calibration-invalid/startup-or-implementation",
   pre["verdict"], "calibration-invalid/startup-or-implementation")
ok("a COMPLETE, FINITE control failure escalates to H (ruling A3 step 2)",
   pre["escalates_to_H"] is True)
ok("the failing control TYPE is reported (prereg s5 item 1)",
   pre["prerequisite"]["by_arm"]["G"]["failing_by_control_type"] == {"o": 3, "n": 3},
   str(pre["prerequisite"]["by_arm"]["G"]["failing_by_control_type"]))
# exactly 5 of 6 passing is a pass; 4 of 6 is a failure
one_bad = {("ow0", 20001, a): 0.9 for a in G.ARMS}
eq("control prerequisite: exactly 5/6 passing is a PASS",
   G.evaluate_tier(build(flat(0.40), flat(0.30), control_e512=one_bad))["verdict"],
   "advance")
two_bad = {("ow0", s, a): 0.9 for s in (20001, 20002) for a in G.ARMS}
eq("control prerequisite: 4/6 passing is a FAIL",
   G.evaluate_tier(build(flat(0.40), flat(0.30), control_e512=two_bad))["verdict"],
   "calibration-invalid/startup-or-implementation")
exact_ctl = {(w, s, a): 0.10 for w, _ in CTL_WORLDS for s in G.SEEDS for a in G.ARMS}
eq("control boundary: E_512 exactly 0.10 passes (<=)",
   G.evaluate_tier(build(flat(0.40), flat(0.30), control_e512=exact_ctl))["verdict"],
   "advance")
over_ctl = {(w, s, a): 0.10 + 1e-17 for w, _ in CTL_WORLDS for s in G.SEEDS
            for a in G.ARMS}
eq("control boundary: E_512 just above 0.10 fails",
   G.evaluate_tier(build(flat(0.40), flat(0.30), control_e512=over_ctl))["verdict"],
   "calibration-invalid/startup-or-implementation")

# ---- 4f. inconclusive ----------------------------------------------------------
# Narrow middle: every C case is learned (E_512=0.30) so the too-hard rule does
# not fire, the median E_32=0.08 is above the too-easy mark but below the 0.15
# advance mark, and no other rule applies.
inc = G.evaluate_tier(build(flat(0.08), flat(0.30)))
eq("narrow middle region is inconclusive", inc["verdict"], "calibration-inconclusive")
ok("the inconclusive reason names the failing advance condition",
   any("< 0.15" in r for r in inc["reasons"]), str(inc["reasons"]))
ok("inconclusive escalates to H", inc["escalates_to_H"] is True)

# =============================================================================
# 5. Failed seed, missing arm, missing cell, timeout, bad accounting
# =============================================================================
fail_seed = {("cw0", 20002, "G"): "numerical_failure"}
nf = G.evaluate_tier(build(flat(0.40), flat(0.30), status_override=fail_seed))
eq("a single failed seed makes the whole tier calibration-invalid",
   nf["verdict"], "calibration-invalid/numerical-failure")
ok("a numerical failure NEVER escalates to H (ruling A3 step 2)",
   nf["escalates_to_H"] is False)
ok("the failed case keeps its own numerical_failure startup label",
   nf["startup_labels"]["cw0/20002/G"] == "numerical_failure")

infra = {("cw0", 20003, "T"): "infrastructure_incomplete"}
ir = G.evaluate_tier(build(flat(0.40), flat(0.30), status_override=infra))
eq("infrastructure_incomplete is a missing required result",
   ir["verdict"], "calibration-invalid/missing-required-result")
ok("infrastructure_incomplete never escalates", ir["escalates_to_H"] is False)

dropped = G.evaluate_tier(build(flat(0.40), flat(0.30), drop=[("cw1", 20001, "T")]))
eq("a dropped world x seed x arm cell is a missing required result",
   dropped["verdict"], "calibration-invalid/missing-required-result")

# missing arm: build only G by dropping every T case
no_T = build(flat(0.40), flat(0.30))
no_T["cases"] = [c for c in no_T["cases"]
                 if not (c["arm"] == "T" and c["outer_split"] == "validation")]
mres = G.evaluate_tier(no_T)
eq("a missing ARM is a missing required result", mres["verdict"],
   "calibration-invalid/missing-required-result")
eq("the missing arm is named", mres["completeness"]["missing_arms"], ["T"])

nanE = build(flat(0.40), flat(0.30))
nanE["cases"][0]["E"][512] = float("nan")
eq("a non-finite E cell is a missing required result",
   G.evaluate_tier(nanE)["verdict"], "calibration-invalid/missing-required-result")

dupe = build(flat(0.40), flat(0.30))
dupe["cases"].append(dict(dupe["cases"][0]))
eq("a duplicated world x seed x arm cell is rejected",
   G.evaluate_tier(dupe)["verdict"], "calibration-invalid/missing-required-result")

timeout = G.evaluate_tier(build(flat(0.40), flat(0.30),
                                integrity={"accounting_valid": True,
                                           "audit_passed": True, "timing_ok": False}))
eq("a schedule/timeout failure is an integrity stop", timeout["verdict"],
   "calibration-invalid/integrity-audit")
ok("a timeout never escalates to H", timeout["escalates_to_H"] is False)

acct = G.evaluate_tier(build(flat(0.40), flat(0.30),
                             integrity={"accounting_valid": False,
                                        "audit_passed": True, "timing_ok": True}))
eq("invalid accounting is its own stop", acct["verdict"],
   "calibration-invalid/accounting")
ok("invalid accounting never escalates to H", acct["escalates_to_H"] is False)

# integrity failures must be checked BEFORE the too-easy rule, so a broken run
# cannot be laundered into a "stop, too easy" conclusion
easy_but_broken = G.evaluate_tier(build(flat(0.04), flat(0.04),
                                        status_override=fail_seed))
eq("a numerical failure outranks the too-easy rule",
   easy_but_broken["verdict"], "calibration-invalid/numerical-failure")

# =============================================================================
# 6. The two-tier procedure (ruling A3 steps 2-6)
# =============================================================================
L_hard = build(flat(0.90), flat(0.90), tier="L")
H_adv = build(flat(0.40), flat(0.30), tier="H")
H_hard = build(flat(0.90), flat(0.90), tier="H")

pend = G.evaluate_two_tier(L_hard)
eq("tier L too-hard with no H table yet is awaiting-tier-H", pend["status"],
   "awaiting-tier-H")
ok("no verdict is final while H is required", pend["final_verdict"] is None)
ok("no tier is adopted while H is pending", pend["adopted_tier"] is None)
ok("the explanation forbids an intrinsic-difficulty reading at L",
   "never evidence of intrinsic task difficulty" in pend["explanation"])

esc = G.evaluate_two_tier(L_hard, H_adv)
eq("L too-hard then H advance adopts H", esc["adopted_tier"], "H")
eq("the final verdict is H's", esc["final_verdict"], "advance")
ok("the explanation says budget-limited learning at L",
   "budget-limited learning at L" in esc["explanation"], esc["explanation"])

both_hard = G.evaluate_two_tier(L_hard, H_hard)
eq("L and H both too hard gives a too-hard final verdict",
   both_hard["final_verdict"], "too-hard")
ok("no tier is adopted when H also fails", both_hard["adopted_tier"] is None)
ok("the maximum claim is 'not learned under either registered budget'",
   "EITHER registered budget" in both_hard["explanation"], both_hard["explanation"])
ok("H never escalates again -- there is no third tier",
   both_hard["tier_H"]["escalates_to_H"] is False)

L_adv = build(flat(0.40), flat(0.30), tier="L")
adopted = G.evaluate_two_tier(L_adv)
eq("L advance adopts L without running H", adopted["adopted_tier"], "L")
ok("H is not permitted after an L advance", adopted["H_permitted"] is False)
viol = G.evaluate_two_tier(L_adv, H_adv)
eq("running H after an L advance is a protocol violation", viol["status"],
   "protocol-violation")

L_easy = build(flat(0.04), flat(0.04), tier="L")
easy2 = G.evaluate_two_tier(L_easy)
eq("L too-easy stops with no H", easy2["final_verdict"], "too-easy")
ok("H is forbidden after a too-easy L", easy2["H_permitted"] is False)
eq("running H after a too-easy L is a protocol violation",
   G.evaluate_two_tier(L_easy, H_adv)["status"], "protocol-violation")

L_nf = build(flat(0.90), flat(0.90), tier="L", status_override=fail_seed)
nf2 = G.evaluate_two_tier(L_nf)
ok("a numerical failure at L forbids H even though the scores look too hard",
   nf2["H_permitted"] is False and nf2["final_verdict"]
   == "calibration-invalid/numerical-failure")

L_ctl = build(flat(0.40), flat(0.30), tier="L", control_e512=bad_ctl)
H_ctl = build(flat(0.40), flat(0.30), tier="H", control_e512=bad_ctl)
ctl2 = G.evaluate_two_tier(L_ctl, H_ctl)
eq("a control failure surviving H is calibration-invalid, not a difficulty result",
   ctl2["final_verdict"], "calibration-invalid/startup-or-implementation")

L_inc = build(flat(0.08), flat(0.30), tier="L")
H_inc = build(flat(0.08), flat(0.30), tier="H")
eq("an inconclusive result at both tiers remains inconclusive",
   G.evaluate_two_tier(L_inc, H_inc)["final_verdict"], "calibration-inconclusive")

# tier mix-ups are schema errors, not verdicts
try:
    G.evaluate_two_tier(H_adv)
    ok("passing an H table as the first tier raises", False)
except G.GateError:
    ok("passing an H table as the first tier raises", True)
try:
    G.evaluate_tier({"version": "ct20-v1", "tier": "L", "cases": []})
    ok("a ct20-v1 table is rejected by the ct20-v1.1 calculator", False)
except G.GateError:
    ok("a ct20-v1 table is rejected by the ct20-v1.1 calculator", True)

# =============================================================================
# 7. Median convention and the per-rung 5% cross-arm rule
# =============================================================================
eq("median of an even sample averages the two central values",
   G.median([1.0, 2.0, 3.0, 4.0]), 2.5)
eq("median of an odd sample is the central value", G.median([1.0, 5.0, 9.0]), 5.0)
try:
    G.median([])
    ok("median of an empty sample raises instead of inventing a value", False)
except G.GateError:
    ok("median of an empty sample raises instead of inventing a value", True)

L_alw = G.TIER_ALLOWANCE_PER_RUNG["L"]
same = {a: {b: L_alw * 0.99 for b in G.BUDGETS} for a in G.ARMS}
c_ok = G.cross_arm_rule_per_rung(same, "L")
ok("5% rule passes when both arms count the same work at every rung",
   c_ok["accounting_valid"] and all(r["within_5_percent"] for r in c_ok["rungs"]))

skew = {"G": {b: L_alw * 0.99 for b in G.BUDGETS},
        "T": {b: L_alw * 0.99 for b in G.BUDGETS}}
skew["T"][128] = L_alw * 0.90      # 9.1% below G at ONE rung only
c_bad = G.cross_arm_rule_per_rung(skew, "L")
ok("the 5% rule is applied PER RUNG, so one bad rung fails the whole ledger",
   c_bad["accounting_valid"] is False)
ok("only the offending rung is marked",
   [r["budget"] for r in c_bad["rungs"] if not r["within_5_percent"]] == [128])

edge = {"G": {b: 1.0e8 for b in G.BUDGETS}, "T": {b: 1.0e8 for b in G.BUDGETS}}
edge["T"][32] = 0.95e8             # (max-min)/max == 0.05 exactly
c_edge = G.cross_arm_rule_per_rung(edge, "L")
ok("5% boundary: a relative gap of exactly 0.05 passes (<=)",
   c_edge["rungs"][0]["within_5_percent"] is True,
   f"gap={c_edge['rungs'][0]['relative_gap']!r}")

over = {a: {b: L_alw * 0.99 for b in G.BUDGETS} for a in G.ARMS}
over["G"][512] = L_alw * 1.01
c_over = G.cross_arm_rule_per_rung(over, "L")
ok("exceeding the per-rung allowance invalidates the accounting",
   c_over["accounting_valid"] is False
   and c_over["rungs"][-1]["over_allowance"] == {"G": L_alw * 1.01})

miss = {"G": {b: 1.0e8 for b in G.BUDGETS}, "T": {32: 1.0e8}}
ok("a missing rung for one arm invalidates the accounting",
   G.cross_arm_rule_per_rung(miss, "L")["accounting_valid"] is False)

zero = {"G": {b: 0.0 for b in G.BUDGETS}, "T": {b: 0.0 for b in G.BUDGETS}}
ok("a zero-denominator cross-arm comparison is nan, not a silent pass",
   G.cross_arm_rule_per_rung(zero, "L")["accounting_valid"] is False)
try:
    G.cross_arm_gap({"G": 1.0})
    ok("cross_arm_gap needs at least two arms", False)
except G.GateError:
    ok("cross_arm_gap needs at least two arms", True)

nan_ops = {"G": {b: 1.0e8 for b in G.BUDGETS}, "T": {b: 1.0e8 for b in G.BUDGETS}}
nan_ops["T"][64] = float("nan")
ok("a NaN in the ledger is not a silent pass",
   G.cross_arm_rule_per_rung(nan_ops, "L")["accounting_valid"] is False)

ok("tier H allowance is 5x tier L per rung (ruling A2)",
   G.TIER_ALLOWANCE_PER_RUNG["H"] == 5 * G.TIER_ALLOWANCE_PER_RUNG["L"])
ok("tier H allowance is 5x tier L per fit (ruling A2)",
   G.TIER_ALLOWANCE_PER_FIT["H"] == 5 * G.TIER_ALLOWANCE_PER_FIT["L"])

# =============================================================================
# 9. RULINGS 2 (R1-R5).  Boundary tests written against the bytes of
#    design/v3/20-concept-toy-rulings-2.md, sha256 1245e46f...  NOTE: the
#    coordinator announced 8a62ef05...; the mismatch is reported in
#    PILOT-AUDIT.md.  These tests are pinned to the bytes actually read.
# =============================================================================
def _raises(fn) -> bool:
    try:
        fn()
    except G.GateError:
        return True
    return False


ok("R0 the calculator stamps the rulings-2 sha it was written against",
   G.RULINGS_2_SHA256 == "1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2")
ok("R0 the rulings-2 sha provenance is resolved, not silently dropped",
   G.RULINGS_2_SHA_PROVENANCE_RESOLVED is True
   and not hasattr(G, "RULINGS_2_SHA_MISMATCH"))
ok("R0 the unreproducible announced hash is retained as a named historical value",
   G.RULINGS_2_SHA256_ANNOUNCED_UNREPRODUCIBLE
   == "8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d"
   and G.RULINGS_2_SHA256_ANNOUNCED_UNREPRODUCIBLE != G.RULINGS_2_SHA256)
ok("R0 the overwritten first version is pinned by path and hash",
   G.RULINGS_2_FIRST_VERSION_RELAYED_SHA256
   == "fac03f785ca6b0e0a0fb3954ac2308b783629b75afda23863633e1ff3bca1269"
   and G.RULINGS_2_FIRST_VERSION_RELAYED_PATH.endswith(
       "RULINGS-2-first-version-as-relayed.md"))

# ---- R1 / A8 / A9: the learned-case rule ------------------------------------
def learned(e512, e_initial):
    return G.is_learned_case({"status": "complete", "E": {512: e512},
                              "E_initial": e_initial})[0]


ok("R1 both clauses required: E_512 exactly 0.50 with a generous initial is learned",
   learned(0.50, 10.0))
ok("R1 E_512 one ulp above 0.50 is NOT learned (exact, no tolerance)",
   not learned(math.nextafter(0.50, 1.0), 10.0))
# A binary64 artifact worth pinning: 0.40*0.75 is NOT 0.30.  The threshold the
# calculator compares against is the product, exactly as ruling R1 writes it, so
# the boundary case must be built from the product and not from the decimal
# literal a reader would expect.  My first draft of this test asserted the wrong
# thing and the calculator was right.
R1_THRESH = 0.40 * (1.0 - G.LEARNED_MIN_RELATIVE_DROP)
ok("R1 binary64: 0.75*0.40 is 0.30000000000000004, not 0.30",
   R1_THRESH != 0.30 and R1_THRESH == 0.30000000000000004, repr(R1_THRESH))
ok("R1 E_512 exactly 0.75*E_initial is learned (inclusive)",
   learned(R1_THRESH, 0.40))
ok("R1 the decimal 0.30 is BELOW that threshold, so it is also learned",
   learned(0.30, 0.40))
ok("R1 E_512 one ulp above 0.75*E_initial is NOT learned",
   not learned(math.nextafter(R1_THRESH, 1.0), 0.40))
ok("R1 the absolute clause alone is not enough (E_512=0.60 <= 0.75*100)",
   not learned(0.60, 100.0))
ok("R1 the relative clause alone is not enough (0.40 <= 0.50 but > 0.75*0.45)",
   not learned(0.40, 0.45))
ok("R1 'add no denominator floor': a tiny E_initial is NOT floored to rescue a case",
   not learned(1e-9, 1e-9))
ok("R1 a zero initial with a zero final satisfies 0 <= 0.75*0 exactly",
   learned(0.0, 0.0))
ok("R1 a missing E_initial is not learned, never assumed",
   not G.is_learned_case({"status": "complete", "E": {512: 0.01}})[0])

# R1: "O/N control competence uses its absolute E marks, not a newly imposed
# relative improvement requirement."
ctl_no_improvement = build(flat(0.30), flat(0.30), control_e512=0.01,
                           e_initial=0.011)
eq("R1 controls are judged on absolute E only: a control that barely improved "
   "still passes competence",
   G.control_prerequisite(ctl_no_improvement)["passes"], True)
ok("R1 the same near-zero improvement WOULD fail the C relative rule, proving "
   "the two rules are genuinely separate", not learned(0.010, 0.011))

# ---- R2: the median ---------------------------------------------------------
eq("R2 even count is the mean of the two central order statistics",
   G.median([4.0, 1.0, 3.0, 2.0]), 2.5)
eq("R2 odd count is the central value", G.median([3.0, 1.0, 2.0]), 2.0)
eq("R2 no rounding: the exact binary64 mean is kept",
   G.median([0.1, 0.2]), (0.1 + 0.2) / 2.0)
ok("R2 a non-finite case does NOT shorten the denominator; it invalidates",
   math.isnan(G.median([1.0, 2.0, float("nan"), 4.0])))
ok("R2 an empty sequence raises rather than inventing a value",
   _raises(lambda: G.median([])))
eq("R2 the complete registered case set is used: 12 equal values median to that value",
   G.median([0.3] * 12), 0.3)

# ---- R3: precedence and failure scope ---------------------------------------
# A control failure alongside a TRUE too-easy predicate.  C errors are tiny, so
# too_easy would fire; controls are broken, so competence must win.
prereq_and_easy = build(flat(0.001), flat(0.001),
                        control_e512={(w, s, a): 0.99
                                      for w, _f in CTL_WORLDS
                                      for s in G.SEEDS for a in G.ARMS})
res_pe = G.evaluate_tier(prereq_and_easy)
eq("R3 control competence outranks a descriptive too-easy predicate",
   res_pe["verdict"], "calibration-invalid/startup-or-implementation")
ok("R3 the too-easy predicate really was true in that table",
   res_pe["too_easy"]["triggers"] is True)
ok("R3 BOTH predicates are printed and precedence is identified",
   any("too_easy=True" in r and "takes precedence" in r for r in res_pe["reasons"]))
ok("R3 a control failure at tier L still buys the single budget check",
   res_pe["escalates_to_H"] is True)

prereq_H = build(flat(0.001), flat(0.001), tier="H",
                 control_e512={(w, s, a): 0.99
                               for w, _f in CTL_WORLDS
                               for s in G.SEEDS for a in G.ARMS})
res_pH = G.evaluate_tier(prereq_H)
eq("R3 the same precedence applies identically at tier H",
   res_pH["verdict"], "calibration-invalid/startup-or-implementation")
ok("R3 a control failure at H never buys another tier", res_pH["escalates_to_H"] is False)
two_pH = G.evaluate_two_tier(prereq_and_easy, prereq_H)
eq("R3 a remaining competence failure at H is the final verdict",
   two_pH["final_verdict"], "calibration-invalid/startup-or-implementation")
ok("R3 the explanation says the version ends and there is no third tier",
   "no third tier" in two_pH["explanation"])

# The complete-wave requirement.
train_fail = build(flat(0.30), flat(0.30))
train_fail["cases"].append({
    "world_public_id": "tw9", "outer_split": "train", "family": "c",
    "seed": 20001, "arm": "T", "status": "numerical_failure",
    "E": {b: None for b in G.BUDGETS}, "E_initial": None,
    "L_initial": None, "L_final": None, "E_fit_final": None})
res_tf = G.evaluate_tier(train_fail)
eq("R3 a numerical failure in a TRAIN world invalidates the complete wave",
   res_tf["verdict"], "calibration-invalid/numerical-failure")
ok("R3 a train-world numerical failure prevents H escalation",
   res_tf["escalates_to_H"] is False)
ok("R3 the reason names the outer requirement explicitly",
   any("outside the validation split" in r for r in res_tf["reasons"]))

train_incomplete = build(flat(0.30), flat(0.30))
train_incomplete["cases"].append({
    "world_public_id": "tw9", "outer_split": "train", "family": "c",
    "seed": 20001, "arm": "T", "status": "infrastructure_incomplete",
    "E": {b: None for b in G.BUDGETS}, "E_initial": None,
    "L_initial": None, "L_final": None, "E_fit_final": None})
eq("R3 a missing required TRAIN fit is a missing required result",
   G.evaluate_tier(train_incomplete)["verdict"],
   "calibration-invalid/missing-required-result")

# Too-hard at L: escalation depends entirely on the complete-wave attestation.
hard_attested = build(flat(0.30), flat(0.90))
ok("R3 too-hard at L with an attested complete wave DOES escalate",
   G.evaluate_tier(hard_attested)["escalates_to_H"] is True)

hard_unattested = build(flat(0.30), flat(0.90),
                        integrity={"complete_wave_valid": None})
hard_unattested["integrity"].pop("complete_wave_valid")
res_hu = G.evaluate_tier(hard_unattested)
eq("R3 an unattested complete wave leaves the descriptive verdict unchanged",
   res_hu["verdict"], "too-hard")
ok("R3 but an UNVERIFIED complete wave blocks the tier-H escalation",
   res_hu["escalates_to_H"] is False)
ok("R3 the block is reported, not silent",
   res_hu["escalation_blocked_by_complete_wave"] is True)
eq("R3 an unverified wave yields no scientific verdict at all",
   G.evaluate_two_tier(hard_unattested)["status"], "blocked-incomplete-wave")
ok("R3 and no difficulty statement is offered",
   G.evaluate_two_tier(hard_unattested)["final_verdict"] is None)

hard_denied = build(flat(0.30), flat(0.90),
                    integrity={"complete_wave_valid": False})
eq("R3 an explicit negative attestation is invalid, not merely unverified",
   G.evaluate_tier(hard_denied)["verdict"],
   "calibration-invalid/missing-required-result")

# "Train-world accuracy still never determines the difficulty window."
train_awful = build(flat(0.30), flat(0.30))
for c in train_awful["cases"]:
    if c["outer_split"] == "train":
        c["E"] = {b: 0.99 for b in G.BUDGETS}
eq("R3 train-world ACCURACY never changes the verdict",
   G.evaluate_tier(train_awful)["verdict"],
   G.evaluate_tier(build(flat(0.30), flat(0.30)))["verdict"])

# ---- R4: the cross-arm cost gap --------------------------------------------
eq("R4 the gap is (max-min)/max", G.cross_arm_gap({"G": 100.0, "T": 95.0}), 0.05)
ok("R4 exactly 0.05 is INSIDE the bound (inclusive)",
   G.cross_arm_rule_per_rung({"G": {b: 100.0 for b in G.BUDGETS},
                              "T": {b: 95.0 for b in G.BUDGETS}},
                             "L")["accounting_valid"] is True)
ok("R4 just over 0.05 is outside the bound",
   G.cross_arm_rule_per_rung({"G": {b: 100.0 for b in G.BUDGETS},
                              "T": {b: 94.9 for b in G.BUDGETS}},
                             "L")["accounting_valid"] is False)
ok("R4 a nonpositive denominator is invalid, never a silent pass",
   math.isnan(G.cross_arm_gap({"G": 0.0, "T": 0.0})))
ok("R4 a negative maximum is invalid too",
   math.isnan(G.cross_arm_gap({"G": -1.0, "T": -2.0})))
# "Apply the rule per rung as registered, not only to cumulative totals."
per_rung_only = G.cross_arm_rule_per_rung(
    {"G": {32: 100.0, 64: 100.0, 128: 100.0, 256: 100.0, 512: 60.0},
     "T": {32: 100.0, 64: 100.0, 128: 100.0, 256: 100.0, 512: 140.0}}, "L")
ok("R4 equal cumulative totals do NOT excuse an out-of-balance rung",
   per_rung_only["accounting_valid"] is False)
ok("R4 the offending rung is named",
   any(r.get("budget") == 512 and r.get("within_5_percent") is False
       for r in per_rung_only["rungs"]))

# ---- R5: ties and the advance window ---------------------------------------
tied = build({"G": [0.30] * 12, "T": [0.30] * 12}, flat(0.40))
adv_tied = G.advance_window(tied)
ok("R5 an exact tie at B=32 is reported as a tie", adv_tied["exact_tie_at_32"] is True)
eq("R5 a tie names G before T as a deterministic display ID",
   adv_tied["better_arm_at_32"], "G")
ok("R5 the tie note says the display ID does not drive the gate",
   "does not read it" in adv_tied["tie_note"])
untied = G.advance_window(build({"G": [0.30] * 12, "T": [0.31] * 12}, flat(0.40)))
eq("R5 a tie cannot change the numerical gate", adv_tied["holds"], untied["holds"])

eq("R5 the E_32 clause reads the MIN across arms, not the chosen arm",
   G.advance_window(build({"G": [0.20] * 12, "T": [0.10] * 12},
                          flat(0.40)))["condition_median_E32_at_least_0_15"],
   False)
ok("R5 min median E_32 exactly 0.15 passes (inclusive)",
   G.advance_window(build({"G": [0.15] * 12, "T": [0.15] * 12},
                          flat(0.40)))["condition_median_E32_at_least_0_15"] is True)
ok("R5 min median E_512 exactly 0.50 passes (inclusive)",
   G.advance_window(build(flat(0.30), {"G": [0.50] * 12, "T": [0.60] * 12})
                    )["condition_some_arm_median_E512_at_most_0_50"] is True)

# "The arm supplying the latter condition need not be the arm with the lower
# B=32 median."
differ = G.advance_window(build({"G": [0.20] * 12, "T": [0.60] * 12},
                                {"G": [0.90] * 12, "T": [0.40] * 12}))
ok("R5 the two clauses may be supplied by different arms", differ["holds"] is True)
eq("R5 the better arm at B=32 is G here", differ["better_arm_at_32"], "G")
eq("R5 but T is the arm supplying the E_512 clause",
   differ["arms_supplying_E512_condition"], ["T"])
ok("R5 and that split is reported explicitly",
   differ["arms_differ_across_budgets"] is True)

# "These two median clauses cannot override the registered learned-case
# requirement" -- the window is only reached after too-hard has been decided.
window_but_unlearned = build({"G": [0.20] * 12, "T": [0.20] * 12},
                             flat(0.45), e_initial=0.50)
res_wbu = G.evaluate_tier(window_but_unlearned)
ok("R5 a table inside the median window but with no learned cases is too-hard, "
   "not advance",
   res_wbu["verdict"] == "too-hard"
   and res_wbu["advance"]["condition_median_E32_at_least_0_15"] is True)

# =============================================================================
print()
n_fail = sum(not r["pass"] for r in RESULTS)
print(json.dumps({"tests": len(RESULTS), "passed": len(RESULTS) - n_fail,
                  "failed": n_fail}))
Path(__file__).with_name("gate_calculator_test_results.json").write_text(
    json.dumps(RESULTS, indent=1))
sys.exit(1 if n_fail else 0)
