"""Tests for scripts/premonition_teacher_delay_report.py (Claude/Opus, 2026-09-19).

Plain script, no pytest, pure standard library.  Builds synthetic plan/result/eval
fixtures in a temporary directory and exercises every rule the A3-teacher-delay-v2
contract puts on the reporting adapter.  Exits non-zero on the first failing check and
prints "ALL N CHECKS PASSED" otherwise.

    PY -B tests/test_premonition_teacher_delay_report.py
    PY -B tests/test_premonition_teacher_delay_report.py --timing   # + full-size bootstrap
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "premonition_teacher_delay_report.py"
_spec = importlib.util.spec_from_file_location("premonition_teacher_delay_report", SCRIPT)
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

FAILURES = []
CHECKS = 0


def check(name, cond):
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        FAILURES.append(name)


def close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


# ======================================================================================
# fixture builders
# ======================================================================================
B = R.B
UNITS = R.UNITS
FAST = 300                     # bootstrap resamples used by the roster-level fixtures


def units(n, correct):
    """Deterministic per-unit vector: the first `correct` units are right."""
    correct = max(0, min(n, correct))
    return [1] * correct + [0] * (n - correct)


def counts_for(*, l_train=True, g_pair=False, stuck=False, **over):
    """c1/c2 drive L_train and stuck; c3 is what keeps G_pair at zero by default.

    c3 sits one unit under its 1876 cutoff, so flipping G_pair on moves the c3 accuracy by a
    single world unit: a G_pair flip must not smuggle a continuous-safeguard shock into the
    fixture."""
    c = {"c1": 2000, "c2": 2000, "c3": 1875, "c4": 1000, "c5": 1000, "c6": 1000, "reads": 500}
    if not l_train:
        c["c2"] = 1900                       # 1900 < 1969 -> L_train fails on c2 only
    if g_pair:
        c["c3"] = 1876                       # 1876 >= 1876 -> all six cutoffs met
    if stuck:
        c["c1"] = 1400                       # 1400 < 1536 -> stuck (and L_train fails)
    c.update(over)
    return c


def default_curve(cross_flops=None, *, cross_step=150, cross_value=0.5, extra=()):
    curve = [{"step": 50, "flops": 0.10 * B, "phase": "gold", "p_own": 0.0,
              "gold_recall_at_4": 0.95},
             {"step": 100, "flops": 0.30 * B, "phase": "teacher", "p_own": 0.0,
              "gold_recall_at_4": 0.10}]
    if cross_flops is not None:
        curve.append({"step": cross_step, "flops": cross_flops, "phase": "ramp",
                      "p_own": 0.3, "gold_recall_at_4": cross_value})
    curve.extend(extra)
    return curve


def arm_spec(**over):
    # "flop budget" is the frozen trainer's literal stop string (archive .../premonition/train.py)
    spec = {"present": True, "status": "complete", "stop": "flop budget", "budget_ok": True,
            "eval_present": True, "eval_status": "complete", "counts": counts_for(),
            "init": None, "batches": None, "curve": None, "selector_policy": "not_applicable",
            "steps": 6470, "seconds_train": 900.0, "n_override": None,
            "per_unit_override": None, "declared_override": None}
    spec.update(over)
    return spec


def write_fixture(root: Path, pair_specs, *, experiment_id=R.EXPERIMENT_ID, budget=B,
                  n_pairs=R.N_PAIRS, resource_worksheet=None):
    root.mkdir(parents=True, exist_ok=True)
    jobs_root = root / "jobs"
    jobs_root.mkdir(exist_ok=True)
    plan_pairs = []
    for pid in range(n_pairs):
        spec = pair_specs[pid]
        jobs = {}
        for arm in ("control", "delayed"):
            jid = f"p{pid:03d}-{arm}"
            jobs[arm] = {"job_id": jid,
                         "teacher_until": R.SCHEDULE[arm]["teacher_until"],
                         "ramp_until": R.SCHEDULE[arm]["ramp_until"]}
            a = spec[arm]
            if not a["present"]:
                continue
            jd = jobs_root / jid
            jd.mkdir(parents=True, exist_ok=True)
            curve = a["curve"]
            if curve is None:
                curve = default_curve(0.55 * B)
            result = {"job_id": jid, "pair_id": pid, "arm": arm, "status": a["status"],
                      "report": {"stop": a["stop"], "budget_ok": a["budget_ok"],
                                 "flops": budget, "flop_budget": budget, "steps": a["steps"]},
                      "phases": {"gold_until": 0.2,
                                 "teacher_until": R.SCHEDULE[arm]["teacher_until"],
                                 "ramp_until": R.SCHEDULE[arm]["ramp_until"]},
                      "curve": curve,
                      "parameters": 79748,
                      "init_state_sha256": a["init"] or f"init-{pid:03d}",
                      "first_batches_sha256": a["batches"] or f"batch-{pid:03d}",
                      "seconds_train": a["seconds_train"], "seconds_total": 1000.0}
            (jd / "result.json").write_text(json.dumps(result))
            if not a["eval_present"]:
                continue
            counts = a["counts"]
            sizes = dict(UNITS)
            if a["n_override"]:
                sizes.update(a["n_override"])
            per_unit = {c: units(sizes[c], counts[c]) for c in R.SAFEGUARD_CELLS}
            if a["per_unit_override"]:
                per_unit.update(a["per_unit_override"])
            recomputed = {
                "L_train": counts["c1"] >= 1969 and counts["c2"] >= 1969,
                "G_pair": all(counts[c] >= R.CUTOFF[c] for c in R.G_PAIR_CELLS),
                "c1_stuck": counts["c1"] < 1536}
            if a["declared_override"]:
                recomputed.update(a["declared_override"])
            ev = {"job_id": jid, "pair_id": pid, "arm": arm, "status": a["eval_status"],
                  "selector_policy": a["selector_policy"], "counts": dict(counts),
                  "n": sizes, "per_unit": per_unit,
                  "c1_stuck": recomputed["c1_stuck"], "L_train": recomputed["L_train"],
                  "G_pair": recomputed["G_pair"],
                  "diagnostics": {}, "integrity": {"weights_unchanged": True}}
            (jd / "eval.json").write_text(json.dumps(ev))
        plan_pairs.append({"pair_id": pid, "init_seed": 1000 + pid, "data_seed": 2000 + pid,
                           "eval_seed": 3000 + pid, "jobs": jobs})
    plan = {"experiment_id": experiment_id, "B": budget, "pairs": plan_pairs}
    if resource_worksheet is not None:
        plan["resource_worksheet"] = resource_worksheet
    (root / "plan.json").write_text(json.dumps(plan))
    return root / "plan.json", jobs_root


def baseline_pairs(gains=0, losses=0, **_):
    """48 pairs; `gains` control-fail/delayed-pass and `losses` the reverse on L_train.
    G_pair is zero everywhere; nobody is stuck; every other cell is identical per unit."""
    out = []
    for pid in range(R.N_PAIRS):
        if pid < gains:
            c, d = counts_for(l_train=False), counts_for(l_train=True)
        elif pid < gains + losses:
            c, d = counts_for(l_train=True), counts_for(l_train=False)
        else:
            c, d = counts_for(l_train=True), counts_for(l_train=True)
        out.append({"control": arm_spec(counts=c), "delayed": arm_spec(counts=d)})
    return out


def report_for(pairs, tmp, name, **kw):
    root = Path(tmp) / name
    plan, jobs = write_fixture(root, pairs, **kw)
    return R.build_report(plan, jobs, resamples=FAST)


# ======================================================================================
# 1. exact primary test
# ======================================================================================
def test_exact():
    print("[exact paired test]")
    check("n=48 g=5 l=0 passes the primary", R.primary_pass(5, 0, 48))
    check("n=48 g=4 l=0 fails the primary", not R.primary_pass(4, 0, 48))
    check("n=48 g=10 l=8 fails the primary", not R.primary_pass(10, 8, 48))
    check("n=48 g=7 l=0 passes the primary", R.primary_pass(7, 0, 48))
    check("d=0 gives p_exact = 1", R.exact_p(0, 0) == 1.0)
    check("d=0 cannot pass", not R.primary_pass(0, 0, 48))
    # losses enter the exact tail
    check("g=10 l=8 tail > .05", R.exact_p(10, 8) > 0.05)
    check("g=10 l=0 tail <= .05", R.exact_p(10, 0) <= 0.05)
    check("g=10 l=8 also fails the net-gain floor", not R.net_gain_ok(10, 8, 48))
    check("losses enter the exact tail (10 gains alone would clear it)",
          R.exact_p(10, 0) <= 0.05 and R.exact_p(10, 8) > 0.05)
    check("losses enter the net-gain floor (10 gains alone would clear it)",
          R.net_gain_ok(10, 0, 48) and not R.net_gain_ok(10, 8, 48))
    # the floor can bind on its own: n=200, g=59, l=41 clears the tail but not (g-l)/n >= .10
    check("the net-gain floor can block a result the exact tail would allow",
          R.exact_p(59, 41) <= 0.05 and not R.net_gain_ok(59, 41, 200)
          and not R.primary_pass(59, 41, 200))
    # the floor is exactly (g-l)/48 >= .10  ->  g-l >= 5 (4.8 rounds up)
    check("net gain floor needs g-l >= 5 at n=48", R.net_gain_ok(5, 0, 48)
          and not R.net_gain_ok(4, 0, 48))
    check("g=14 l=4 passes both inequalities", R.primary_pass(14, 4, 48))
    check("g=13 l=8 fails the exact tail", R.exact_p(13, 8) > 0.05
          and not R.primary_pass(13, 8, 48))
    check("exact_p(5,0) == 1/32", R.exact_p(5, 0) == 1.0 / 32.0)
    check("exact_p(4,0) == 1/16", R.exact_p(4, 0) == 1.0 / 16.0)


# ======================================================================================
# 2. planning power
# ======================================================================================
def test_power():
    print("[exact planning power]")
    for a, b, n, want in [(0.26125, 0.03625, 48, 0.8916),
                          (0.275, 0.050, 48, 0.8569),
                          (0.2475, 0.0725, 48, 0.6334),
                          (0.240625, 0.090625, 48, 0.4872),
                          (0.26125, 0.03625, 16, 0.2753)]:
        got = R.exact_power(a, b, n)
        check(f"power n={n} a={a} b={b} -> {want}", close(got, want, 5e-4))
    check("power with a=0 is 0", R.exact_power(0.0, 0.1, 48) == 0.0)
    # the contract's n=16 "at least five susceptible controls" arithmetic
    check("n=16 a=.175 b=0 -> 0.133132", close(R.exact_power(0.175, 0.0, 16), 0.133132, 5e-6))
    check("n=16 learned-gate a=.275 b=0 -> 0.460639",
          close(R.exact_power(0.275, 0.0, 16), 0.460639, 5e-6))


# ======================================================================================
# 3. resources
# ======================================================================================
def test_resources():
    print("[resource worksheet]")
    w = R.resource_worksheet(96, 96, 2.9e10, 200.0, 100.0)
    per_job = B / 2.9e10
    check("C=96 gives one wave", w["waves"] == 1)
    check("per-job training seconds = B/rate", close(w["per_job_training_seconds"],
                                                     per_job, 1e-9))
    check("per-job training within the 1200s cap", w["per_job_training_within_1200s_cap"])
    check("T = s + 1*(B/rate + e)", close(w["T_seconds"], 100.0 + per_job + 200.0, 1e-9))
    check("T <= 1500s target", w["T_within_1500s_target"] and w["T_seconds"] < 1500.0)
    check("T <= 1800s ceiling", w["T_within_1800s_ceiling"])
    check("rate floor is B/1200 = 2.838567926e10",
          close(w["required_rate_floor_flops_per_second"], 2.838567926e10, 1.0))
    check("2.9e10 meets the floor", w["rate_meets_floor"])
    check("nominal roster FLOPs = 96*B", close(w["nominal_training_flops_total"], 96 * B, 1.0))
    check("no price -> no cost", w["cost_usd"] is None)

    w5 = R.resource_worksheet(96, 5, 2.9e10, 200.0, 100.0)
    check("C=5 -> ceil(96/5) = 20 waves", w5["waves"] == 20)
    check("C=5 T = 100 + 20*(B/rate+200)",
          close(w5["T_seconds"], 100.0 + 20 * (per_job + 200.0), 1e-6))
    check("C=5 blows the 1500s target", not w5["T_within_1500s_target"])
    check("C=5 blows the 1800s ceiling", not w5["T_within_1800s_ceiling"])

    slow = R.resource_worksheet(96, 96, 2.0e10, 200.0, 100.0)
    check("a rate below the floor fails the per-job 1200s cap",
          not slow["per_job_training_within_1200s_cap"] and not slow["rate_meets_floor"])

    priced = R.resource_worksheet(96, 96, 2.9e10, 200.0, 100.0, price_per_hour=0.40, machines=2)
    check("cost = machines * price/h * T/3600",
          close(priced["cost_usd"], 2 * 0.40 * priced["T_seconds"] / 3600.0, 1e-12))
    check("cost note says billing minimums are excluded",
          "minimum" in priced["cost_note"].lower())
    check("ceil behaviour: 96/7 -> 14 waves", R.resource_worksheet(
        96, 7, 2.9e10, 0.0, 0.0)["waves"] == 14)


# ======================================================================================
# 4. secondary escape timing
# ======================================================================================
def test_escape():
    print("[secondary escape timing]")
    horizon = 0.8 * B

    e = R.escape_timing(default_curve(0.55 * B), B)
    check("a non-gold log above .3 is an event", e["event"] and not e["censored"])
    check("event time = flops - .2B", close(e["restricted_time"], 0.55 * B - 0.2 * B, 1e-3))
    check("event step recorded", e["event_step"] == 150)

    tie = [{"step": 100, "flops": 0.5 * B, "phase": "ramp", "gold_recall_at_4": 0.3}]
    check("exactly .3 is NOT an event (strictly greater)", R.escape_timing(tie, B)["event"]
          is False)
    tie2 = [{"step": 100, "flops": 0.5 * B, "phase": "ramp", "gold_recall_at_4": 0.3},
            {"step": 150, "flops": 0.6 * B, "phase": "ramp", "gold_recall_at_4": 0.30000001}]
    e2 = R.escape_timing(tie2, B)
    check("the first strictly-greater log wins the tie", e2["event"] and e2["event_step"] == 150)

    goldy = [{"step": 20, "flops": 0.05 * B, "phase": "gold", "gold_recall_at_4": 0.99},
             {"step": 40, "flops": 0.15 * B, "phase": "gold", "gold_recall_at_4": 0.99}]
    g = R.escape_timing(goldy, B)
    check("gold-phase logs never count as escapes", (not g["event"]) and g["censored"])
    check("censored restricted time = .8B", close(g["restricted_time"], horizon, 1e-6))

    late = [{"step": 20, "flops": 0.05 * B, "phase": "gold", "gold_recall_at_4": 0.99},
            {"step": 900, "flops": 1.02 * B, "phase": "own", "gold_recall_at_4": 0.7}]
    ln = R.escape_timing(late, B)
    check("a crossing beyond nominal B is censored on the common horizon", ln["censored"])
    check("the beyond-B crossing is still kept raw", ln["raw_first_crossing_step"] == 900)
    check("logs beyond B are counted", ln["logs_beyond_nominal_budget"] == 1)
    check("restricted time is the .8B horizon", close(ln["restricted_time"], horizon, 1e-6))

    atB = [{"step": 400, "flops": 1.0 * B, "phase": "own", "gold_recall_at_4": 0.9}]
    a = R.escape_timing(atB, B)
    check("a crossing exactly at B is an event clamped to .8B",
          a["event"] and close(a["restricted_time"], horizon, 1e-6))

    never = [{"step": 100, "flops": 0.5 * B, "phase": "ramp", "gold_recall_at_4": 0.1}]
    n = R.escape_timing(never, B)
    check("no crossing -> censored with raw_censored_at_run_end",
          n["censored"] and n["raw_censored_at_run_end"])
    check("empty curve is censored", R.escape_timing([], B)["censored"])


# ======================================================================================
# 5. bootstrap
# ======================================================================================
def spec_from(n, n_plus, n_minus):
    """Build the per-pair spec through diff_spec itself, from two real per-unit vectors."""
    control = [0] * n_plus + [1] * n_minus + [0] * (n - n_plus - n_minus)
    delayed = [1] * n_plus + [0] * n_minus + [0] * (n - n_plus - n_minus)
    return R.diff_spec(control, delayed)


def test_bootstrap():
    print("[paired hierarchical bootstrap]")
    ident = [(1024, 0, 0, tuple([0] * 1024)) for _ in range(48)]
    a = R.bootstrap_lower_bound("c4", ident, resamples=2000)
    check("identical arms -> point estimate exactly 0", a["point_estimate"] == 0.0)
    check("identical arms -> lower bound exactly 0", a["lower_bound"] == 0.0)
    check("identical arms pass the -.02 margin", a["passes"])

    k = 51
    d = k / 1024.0                                   # exactly +4.98 points per pair
    const = [spec_from(1024, k, 0) for _ in range(48)]
    c = R.bootstrap_lower_bound("c5", const, resamples=4000)
    check("constant +5pt improvement: point estimate = +51/1024",
          close(c["point_estimate"], d, 1e-12))
    check("constant +5pt improvement: lower bound near +d",
          close(c["lower_bound"], d, 0.006) and c["lower_bound"] < d)
    check("constant +5pt improvement passes", c["passes"])

    harm = [spec_from(1024, 0, k) for _ in range(48)]
    h = R.bootstrap_lower_bound("c5", harm, resamples=4000)
    check("constant -5pt harm: lower bound near -d", close(h["lower_bound"], -d, 0.006))
    check("constant -5pt harm is BLOCKED by the -.02 margin", not h["passes"])

    # determinism given the seed
    x1 = R.bootstrap_lower_bound("c3", const, resamples=1500)["lower_bound"]
    x2 = R.bootstrap_lower_bound("c3", const, resamples=1500)["lower_bound"]
    check("bootstrap is deterministic given the cell seed", x1 == x2)
    y = R.bootstrap_lower_bound("c6", const, resamples=1500)["lower_bound"]
    check("different cells use different RNG streams", y != x1)
    check("seed comes from SHA-256 of the manifest string",
          R.bootstrap_seed("c1") != R.bootstrap_seed("c2"))

    # the order statistic is the floor(.05*R)-th, 1-indexed
    r = R.bootstrap_lower_bound("c1", const, resamples=100_00)
    check("order statistic = floor(.05*R), 1-indexed", r["order_statistic"] == 500)
    check("R=100000 would use the 5,000th",
          math.floor(0.05 * 100000) == 5000)

    # twin units stay single units: diff_spec refuses ragged arms
    try:
        R.diff_spec([1, 0, 1], [1, 0])
        ok = False
    except ValueError:
        ok = True
    check("diff_spec rejects arms with different unit counts", ok)
    ds = R.diff_spec([1, 1, 0, 0], [1, 0, 1, 0])
    check("diff_spec counts one unit per twin pair", ds[0] == 4 and ds[1] == 1 and ds[2] == 1)


def test_bootstrap_equivalence():
    print("[multinomial shortcut == unit resampling]")
    # small fixture with a mix of +1 / -1 / 0 differences and unequal pairs
    specs = [spec_from(8, 3, 1), spec_from(8, 0, 2), spec_from(8, 5, 0), spec_from(8, 1, 1)]
    reps = 60000
    rnd_m = random.Random(R.bootstrap_seed("equiv-m"))
    rnd_u = random.Random(R.bootstrap_seed("equiv-u"))
    dm = R._resample_multinomial(rnd_m, specs, len(specs), reps)
    du = R._resample_units(rnd_u, specs, len(specs), reps)
    mm, mu = statistics.fmean(dm), statistics.fmean(du)
    sm, su = statistics.pstdev(dm), statistics.pstdev(du)
    se = math.sqrt(sm * sm / reps + su * su / reps)
    check(f"means agree ({mm:.6f} vs {mu:.6f}) within 4 SE", abs(mm - mu) <= 4 * se)
    check(f"sds agree ({sm:.6f} vs {su:.6f}) within 3%", abs(sm - su) <= 0.03 * su)
    dm.sort()
    du.sort()
    worst = 0.0
    for q in (0.05, 0.25, 0.50, 0.75, 0.95):
        i = max(1, math.floor(q * reps)) - 1
        worst = max(worst, abs(dm[i] - du[i]))
    check(f"5/25/50/75/95 quantiles agree within Monte-Carlo error (max gap {worst:.5f})",
          worst <= 0.02)
    exact_point = statistics.fmean([(s[1] - s[2]) / s[0] for s in specs])
    check("both methods centre on the exact point estimate",
          abs(mm - exact_point) <= 4 * se + 1e-12 and abs(mu - exact_point) <= 4 * se + 1e-12)


# ======================================================================================
# 6. roster / stage decision
# ======================================================================================
def test_stage_acceptance(tmp):
    print("[stage acceptance: L_train improves, G_pair zero in both arms]")
    rep = report_for(baseline_pairs(gains=12, losses=1), tmp, "accept")
    t = rep["primary"]["table"]
    check("g=12", t["g"] == 12)
    check("l=1", t["l"] == 1)
    check("n stays at the registered 48", t["n"] == 48)
    check("primary passes", t["primary_pass"])
    check("all 96 jobs complete-eval",
          rep["roster"]["job_status_counts"]["complete-eval"] == 96)
    check("no integrity failures", rep["integrity_failures"] == [])
    check("G_pair is zero in BOTH arms",
          rep["statuses"]["g_pair_outcomes"]["both_rosters_all_zero"])
    check("all seven safeguards pass", rep["safeguards_all_pass"])
    for cell in R.SAFEGUARD_CELLS:
        s = rep["safeguards"][cell]
        check(f"  safeguard {cell}: LB {s['lower_bound']:+.5f} > -0.02", s["passes"])
        check(f"  safeguard {cell} uses all 48 pairs", s["pairs_used"] == 48)
    check("stuck count does not increase", rep["stuck"]["no_increase"])
    check("STATUS stage-accepted", rep["statuses"]["stage_accepted"]["state"] == "stage-accepted")
    check("exact contract label emitted",
          rep["statuses"]["stage_accepted"]["label"] ==
          "accepted plateau-stage background: A3-teacher-delay-v2 at B=34062815112683.242")
    check("NOT labelled a G_pair advancement",
          rep["statuses"]["stage_accepted"]["is_g_pair_advancement"] is False)
    check("NOT labelled G_cert", rep["statuses"]["stage_accepted"]["is_g_cert"] is False)
    check("statement says not a G_pair advancement and not G_cert",
          "NOT a G_pair advancement" in rep["statuses"]["stage_accepted"]["statement"]
          and "NOT G_cert" in rep["statuses"]["stage_accepted"]["statement"])
    check("all-zero G_pair rosters do not block acceptance",
          rep["statuses"]["g_pair_outcomes"]["blocks_stage_acceptance_by_being_zero"] is False)
    check("statuses are distinct keys, never conflated",
          set(rep["statuses"]) == {"specified", "admitted", "complete", "stage_accepted",
                                   "g_pair_outcomes"})
    check("specified is its own status", rep["statuses"]["specified"]["state"] == "specified")
    check("admitted is PENDING without a resource worksheet",
          rep["statuses"]["admitted"]["state"] == "pending")
    check("complete is its own status", rep["statuses"]["complete"]["state"] == "complete")
    check("no endpoint switching flag", rep["primary"]["endpoint_switching"] is False
          and rep["primary"]["selective_omission"] is False
          and rep["primary"]["sample_enlargement"] is False
          and rep["primary"]["early_efficacy_stopping"] is False)
    check("secondary is not an input to the primary",
          rep["primary"]["secondary_used_in_primary"] is False)
    check("secondary has no pass mark",
          rep["secondary_escape_timing"]["has_pass_mark"] is False)

    text = R.render_text(rep)
    check("report text prints the exact acceptance label",
          "accepted plateau-stage background: A3-teacher-delay-v2 at B=34062815112683.242"
          in text)
    check("report text prints the complete 2x2", "control FAIL" in text and "p_exact" in text)
    check("report text states the 48 denominator",
          "denominator is always the registered 48" in text)
    return rep


def test_primary_below_floor(tmp):
    print("[primary fails when the net gain is below the floor]")
    rep = report_for(baseline_pairs(gains=4, losses=0), tmp, "floor")
    check("g=4 l=0 -> primary fails", not rep["primary"]["table"]["primary_pass"])
    check("g=4 l=0 -> not stage-accepted",
          rep["statuses"]["stage_accepted"]["state"] == "not-stage-accepted")
    check("blocking reason names the primary",
          "1_primary_L_train_passes" in rep["statuses"]["stage_accepted"]["blocking_reasons"])


def test_roster_missing_and_incomplete(tmp):
    print("[roster: a missing job and an incomplete job]")
    pairs = baseline_pairs(gains=12, losses=1)
    # pair 20: control result.json entirely absent, delayed passes L_train
    pairs[20]["control"] = arm_spec(present=False)
    # pair 21: control training incomplete (wall-clock cap stop), delayed passes L_train
    pairs[21]["control"] = arm_spec(status="incomplete", stop="max_seconds", budget_ok=False)
    rep = report_for(pairs, tmp, "roster")
    t = rep["primary"]["table"]
    check("the roster is still 48 pairs", t["n"] == 48)
    check("the roster is still 96 jobs", len(rep["roster"]["jobs"]) == 96)
    check("the missing job is counted missing",
          rep["roster"]["job_status_counts"]["missing"] == 1)
    check("the incomplete job is counted incomplete",
          rep["roster"]["job_status_counts"]["incomplete"] == 1)
    rows = {r["pair_id"]: r for r in rep["roster"]["pairs"]}
    check("the missing control scores as a FAILED L_train outcome",
          rows[20]["L_train"]["control"] is False)
    check("the incomplete control scores as a FAILED L_train outcome",
          rows[21]["L_train"]["control"] is False)
    check("the missing control is scored as stuck (no demonstrated escape)",
          rows[20]["c1_stuck"]["control"] is True)
    check("completion status is incomplete",
          rep["statuses"]["complete"]["state"] == "incomplete")
    check("stage acceptance is BLOCKED",
          rep["statuses"]["stage_accepted"]["state"] == "not-stage-accepted")
    check("blocking names the incomplete records",
          "1b_all_96_records_valid_and_complete"
          in rep["statuses"]["stage_accepted"]["blocking_reasons"])
    check("the two broken pairs show up as gains in the table (never hidden)",
          t["g"] == 14)
    check("those gains are flagged as having a non-complete control",
          sorted(rep["primary"]["gains_with_non_complete_control_pairs"]) == [20, 21])
    check("the manufactured gains still cannot produce an acceptance",
          rep["statuses"]["stage_accepted"]["state"] != "stage-accepted")

    # the pathological case: ONLY missing controls would 'gain'
    pairs2 = baseline_pairs(gains=0, losses=0)
    for pid in range(8):
        pairs2[pid]["control"] = arm_spec(present=False)
    rep2 = report_for(pairs2, tmp, "roster2")
    check("8 missing controls produce g=8 in the table", rep2["primary"]["table"]["g"] == 8)
    check("...which would pass the arithmetic on its own",
          rep2["primary"]["table"]["primary_pass"])
    check("...but acceptance is blocked regardless",
          rep2["statuses"]["stage_accepted"]["state"] == "not-stage-accepted")
    check("...and every such gain is flagged",
          sorted(rep2["primary"]["gains_with_non_complete_control_pairs"]) == list(range(8)))

    # completion predicate: FLOP-budget stop AND budget_ok, matching the frozen trainer's
    # literal stop strings.  A time/step stop, or a checkpoint alone, is incomplete.
    check("'flop budget' is a budget stop", R.is_budget_stop("flop budget"))
    check("'flop budget (the next batch would pass the tolerance)' is a budget stop",
          R.is_budget_stop("flop budget (the next batch would pass the tolerance)"))
    check("'max_seconds' is not a budget stop", not R.is_budget_stop("max_seconds"))
    check("'max_steps' is not a budget stop", not R.is_budget_stop("max_steps"))
    check("'stream ended' is not a budget stop", not R.is_budget_stop("stream ended"))
    check("an empty stop is not a budget stop", not R.is_budget_stop(None))

    pairs4 = baseline_pairs(gains=12, losses=1)
    pairs4[31]["delayed"] = arm_spec(status="complete", stop="max_steps", budget_ok=False)
    rep4 = report_for(pairs4, tmp, "roster4")
    check("status=complete with a max_steps stop is downgraded to incomplete",
          rep4["roster"]["job_status_counts"]["incomplete"] == 1)
    pairs5 = baseline_pairs(gains=12, losses=1)
    pairs5[32]["delayed"] = arm_spec(status="complete", stop="flop budget", budget_ok=False)
    rep5 = report_for(pairs5, tmp, "roster5")
    check("status=complete with budget_ok=false is downgraded to incomplete",
          rep5["roster"]["job_status_counts"]["incomplete"] == 1)
    pairs6 = baseline_pairs(gains=12, losses=1)
    pairs6[33]["delayed"] = arm_spec(
        stop="flop budget (the next batch would pass the tolerance)")
    rep6 = report_for(pairs6, tmp, "roster6")
    check("the tolerance-variant budget stop still counts as complete",
          rep6["roster"]["job_status_counts"]["complete-eval"] == 96)

    # a failed evaluation leaves training complete but the job not complete-eval
    pairs3 = baseline_pairs(gains=12, losses=1)
    pairs3[30]["delayed"] = arm_spec(eval_status="failed")
    rep3 = report_for(pairs3, tmp, "roster3")
    check("a failed evaluation yields complete-train, not complete-eval",
          rep3["roster"]["job_status_counts"]["complete-train"] == 1)
    check("a failed evaluation scores its arm as FAILED",
          {r["pair_id"]: r for r in rep3["roster"]["pairs"]}[30]["L_train"]["delayed"] is False)
    check("a failed evaluation blocks acceptance",
          rep3["statuses"]["stage_accepted"]["state"] == "not-stage-accepted")


def test_recompute_disagreement(tmp):
    print("[recomputed endpoints override the eval.json booleans]")
    pairs = baseline_pairs(gains=12, losses=1)
    pairs[5]["delayed"] = arm_spec(counts=counts_for(l_train=False),
                                   declared_override={"L_train": True})
    rep = report_for(pairs, tmp, "recompute")
    msgs = " ".join(rep["integrity_failures"])
    check("a lying L_train boolean is flagged", "L_train: eval.json says True" in msgs)
    check("the recomputed (failing) value is used",
          {r["pair_id"]: r for r in rep["roster"]["pairs"]}[5]["L_train"]["delayed"] is False)
    check("the disagreement blocks acceptance",
          "5_integrity_records_clean" in rep["statuses"]["stage_accepted"]["blocking_reasons"])

    pairs2 = baseline_pairs(gains=12, losses=1)
    pairs2[6]["control"] = arm_spec(counts=counts_for(g_pair=True))
    rep2 = report_for(pairs2, tmp, "recompute2")
    check("G_pair is recomputed from all six cutoffs",
          {r["pair_id"]: r for r in rep2["roster"]["pairs"]}[6]["G_pair"]["control"] is True)


def test_stuck_increase_blocks(tmp):
    print("[blocked by a stuck-count increase]")
    pairs = baseline_pairs(gains=12, losses=1)
    # pair 40: control healthy, delayed newly stuck  ->  stuck count rises 0 -> 1
    pairs[40]["delayed"] = arm_spec(counts=counts_for(stuck=True))
    rep = report_for(pairs, tmp, "stuck")
    check("control stuck count 0", rep["stuck"]["control_count"] == 0)
    check("delayed stuck count 1", rep["stuck"]["delayed_count"] == 1)
    check("the stuck safeguard fails", not rep["stuck"]["no_increase"])
    check("acceptance is BLOCKED by the stuck increase",
          "2_no_increase_in_fresh_c1_stuck_count"
          in rep["statuses"]["stage_accepted"]["blocking_reasons"])
    check("still not stage-accepted",
          rep["statuses"]["stage_accepted"]["state"] == "not-stage-accepted")
    check("the not-stuck 2x2 is reported", rep["not_stuck_table"]["n"] == 48)

    # an equal stuck count in both arms is NOT an increase
    pairs2 = baseline_pairs(gains=12, losses=1)
    pairs2[41]["control"] = arm_spec(counts=counts_for(stuck=True))
    pairs2[41]["delayed"] = arm_spec(counts=counts_for(stuck=True))
    rep2 = report_for(pairs2, tmp, "stuck2")
    check("an equal stuck count in both arms does not block", rep2["stuck"]["no_increase"])


def test_harm_blocks(tmp):
    print("[blocked by a continuous no-harm lower bound at or below -.02]")
    pairs = baseline_pairs(gains=12, losses=1)
    for pid in range(R.N_PAIRS):
        # c4: control 1000/1024, delayed 949/1024  ->  a clear -5 point harm everywhere
        pairs[pid]["control"] = arm_spec(counts=counts_for(
            l_train=pairs[pid]["control"]["counts"]["c2"] >= 1969, c4=1000))
        pairs[pid]["delayed"] = arm_spec(counts=counts_for(
            l_train=pairs[pid]["delayed"]["counts"]["c2"] >= 1969, c4=949))
    rep = report_for(pairs, tmp, "harm")
    s = rep["safeguards"]["c4"]
    check("c4 point estimate is about -5 points",
          close(s["point_estimate"], -51.0 / 1024.0, 1e-9))
    check(f"c4 lower bound {s['lower_bound']:+.5f} <= -0.02", s["lower_bound"] <= -0.02)
    check("the c4 safeguard is BLOCKED", not s["passes"])
    check("the other six safeguards still pass",
          all(rep["safeguards"][c]["passes"] for c in R.SAFEGUARD_CELLS if c != "c4"))
    check("one failing bound blocks the whole safeguard group",
          not rep["safeguards_all_pass"])
    check("acceptance is BLOCKED by the lower bound",
          "3_all_seven_lower_bounds_above_margin"
          in rep["statuses"]["stage_accepted"]["blocking_reasons"])
    check("the primary itself is unaffected", rep["primary"]["table"]["primary_pass"])

    # a tiny harm that stays above the margin does not block
    pairs2 = baseline_pairs(gains=12, losses=1)
    for pid in range(R.N_PAIRS):
        base_c = pairs2[pid]["control"]["counts"]
        base_d = pairs2[pid]["delayed"]["counts"]
        base_c["c5"], base_d["c5"] = 1000, 998          # -2/1024 = -0.00195
    rep2 = report_for(pairs2, tmp, "harm2")
    check("a 0.2-point dip stays above the -.02 margin", rep2["safeguards"]["c5"]["passes"])
    check("...and does not block acceptance",
          rep2["statuses"]["stage_accepted"]["state"] == "stage-accepted")


def test_gpair_decrease_blocks(tmp):
    print("[blocked by a G_pair pass-count decrease]")
    pairs = baseline_pairs(gains=12, losses=1)
    pairs[45]["control"] = arm_spec(counts=counts_for(g_pair=True))     # control passes G_pair
    rep = report_for(pairs, tmp, "gpair")
    check("control G_pair pass count 1",
          rep["statuses"]["g_pair_outcomes"]["control_pass_count"] == 1)
    check("delayed G_pair pass count 0",
          rep["statuses"]["g_pair_outcomes"]["delayed_pass_count"] == 0)
    check("the G_pair count safeguard fails",
          not rep["statuses"]["g_pair_outcomes"]["does_not_decrease"])
    check("acceptance is BLOCKED by the G_pair decrease",
          "4_G_pair_pass_count_does_not_decrease"
          in rep["statuses"]["stage_accepted"]["blocking_reasons"])
    check("the G_pair 2x2 is published", rep["g_pair_table"]["n"] == 48
          and rep["g_pair_table"]["l"] == 1)

    # an individual G_pair loss offset by a gain is NOT a veto
    pairs2 = baseline_pairs(gains=12, losses=1)
    pairs2[44]["control"] = arm_spec(counts=counts_for(g_pair=True))
    pairs2[43]["delayed"] = arm_spec(counts=counts_for(g_pair=True))
    rep2 = report_for(pairs2, tmp, "gpair2")
    check("1 gain and 1 loss keeps the count equal",
          rep2["statuses"]["g_pair_outcomes"]["does_not_decrease"])
    check("individual G_pair losses are not a zero-loss veto",
          rep2["statuses"]["stage_accepted"]["state"] == "stage-accepted")


def test_digest_mismatch_blocks(tmp):
    print("[blocked by a within-pair init digest mismatch]")
    pairs = baseline_pairs(gains=12, losses=1)
    pairs[7]["delayed"] = arm_spec(init="a-different-initial-state")
    rep = report_for(pairs, tmp, "digest")
    msgs = " ".join(rep["integrity_failures"])
    check("the init_state_sha256 mismatch is reported",
          "init_state_sha256 differs between arms" in msgs)
    check("acceptance is BLOCKED by the integrity failure",
          "5_integrity_records_clean" in rep["statuses"]["stage_accepted"]["blocking_reasons"])

    pairs2 = baseline_pairs(gains=12, losses=1)
    pairs2[8]["control"] = arm_spec(batches="other-batches")
    rep2 = report_for(pairs2, tmp, "digest2")
    check("the first_batches_sha256 mismatch is reported",
          "first_batches_sha256 differs between arms" in " ".join(rep2["integrity_failures"]))
    check("...and blocks acceptance",
          rep2["statuses"]["stage_accepted"]["state"] == "not-stage-accepted")


def test_unit_and_policy_integrity(tmp):
    print("[unit counts, twin units and the legacy selector policy]")
    pairs = baseline_pairs(gains=12, losses=1)
    # a c1 panel that split twins into 2 x 2048 units instead of 2048 scoring units
    pairs[9]["delayed"] = arm_spec(per_unit_override={"c1": [1] * 4096})
    rep = report_for(pairs, tmp, "units")
    msgs = " ".join(rep["integrity_failures"])
    check("per_unit with split twins is rejected",
          "ONE scoring/resampling unit" in msgs)
    check("that pair drops out of the c1 bootstrap",
          rep["safeguards"]["c1"]["pairs_used"] == 47)
    check("an incomplete safeguard roster blocks acceptance",
          "3_all_seven_lower_bounds_above_margin"
          in rep["statuses"]["stage_accepted"]["blocking_reasons"])

    pairs2 = baseline_pairs(gains=12, losses=1)
    pairs2[10]["control"] = arm_spec(selector_policy="pooled")
    rep2 = report_for(pairs2, tmp, "policy")
    check("a non-legacy selector policy is an integrity failure",
          "is not 'not_applicable'" in " ".join(rep2["integrity_failures"]))

    pairs3 = baseline_pairs(gains=12, losses=1)
    pairs3[11]["control"] = arm_spec(n_override={"reads": 256})
    rep3 = report_for(pairs3, tmp, "panelsize")
    check("a short READS panel is an integrity failure",
          "512 scoring units" in " ".join(rep3["integrity_failures"]))


def test_plan_integrity(tmp):
    print("[plan-level specification checks]")
    pairs = baseline_pairs(gains=12, losses=1)
    rep = report_for(pairs, tmp, "planbad", experiment_id="A3-teacher-delay-v1")
    check("a wrong experiment_id is a specification failure",
          rep["statuses"]["specified"]["state"] == "specification-invalid")
    rep2 = report_for(pairs, tmp, "planbadB", budget=B / 2)
    check("a recomputed / wrong B is a specification failure",
          any("is not the frozen" in m for m in rep2["integrity_failures"]))
    rep3 = report_for(pairs[:47], tmp, "planbadN", n_pairs=47)
    check("fewer than 48 registered pairs is a specification failure",
          any("contract requires 48" in m for m in rep3["integrity_failures"]))


def test_secondary_cannot_move_primary(tmp):
    print("[no secondary statistic changes the primary]")
    base = baseline_pairs(gains=12, losses=1)
    rep_a = report_for(base, tmp, "sec_a")
    fast = baseline_pairs(gains=12, losses=1)
    for pid in range(R.N_PAIRS):
        # delayed escapes very early, control never escapes at all
        fast[pid]["delayed"] = arm_spec(counts=fast[pid]["delayed"]["counts"],
                                        curve=default_curve(0.25 * B))
        fast[pid]["control"] = arm_spec(counts=fast[pid]["control"]["counts"],
                                        curve=default_curve(None))
    rep_b = report_for(fast, tmp, "sec_b")
    check("the secondary summaries really did change",
          rep_a["secondary_escape_timing"]["control_events"] !=
          rep_b["secondary_escape_timing"]["control_events"])
    check("the primary 2x2 is unchanged",
          rep_a["primary"]["table"] == rep_b["primary"]["table"])
    check("the stage decision is unchanged",
          rep_a["statuses"]["stage_accepted"]["state"] ==
          rep_b["statuses"]["stage_accepted"]["state"])
    s = rep_b["secondary_escape_timing"]
    check("control runs are all censored", s["control_events"] == 0)
    check("delayed runs are all events", s["delayed_events"] == 48)
    check("joint censoring is counted", s["joint_censored_pairs"] == 0)
    check("paired restricted differences are reported",
          close(s["mean_restricted_difference"], (0.25 * B - 0.2 * B) - 0.8 * B, 1.0))
    check("the secondary note states it has no pass mark",
          "no pass mark" in s["note"])


def test_cli(tmp):
    print("[CLI: writes report.json/report.txt and refuses to overwrite]")
    root = Path(tmp) / "cli"
    plan, _jobs = write_fixture(root, baseline_pairs(gains=12, losses=1))
    out = root / "report"
    rc = R.main(["report", "--plan", str(plan), "--out", str(out),
                 "--resamples", str(FAST), "--quiet"])
    check("report exits 0", rc == 0)
    check("report.json written", (out / "report.json").is_file())
    check("report.txt written", (out / "report.txt").is_file())
    check("no .md file is written",
          not any(p.suffix == ".md" for p in out.iterdir()))
    data = json.loads((out / "report.json").read_text())
    check("report.json carries the frozen B", data["B"] == B)
    check("report.json carries the stage label",
          data["statuses"]["stage_accepted"]["label"] ==
          "accepted plateau-stage background: A3-teacher-delay-v2 at B=34062815112683.242")
    raised = False
    try:
        R.main(["report", "--plan", str(plan), "--out", str(out),
                "--resamples", str(FAST), "--quiet"])
    except SystemExit as exc:
        raised = "refusing to overwrite" in str(exc)
    check("a second run refuses to overwrite the output directory", raised)

    rc = R.main(["power", "--a", "0.26125", "--b", "0.03625", "--n", "48"])
    check("power sub-command exits 0", rc == 0)
    rc = R.main(["resources", "--jobs", "96", "--concurrency", "96", "--rate", "2.9e10",
                 "--eval-seconds", "200", "--setup-seconds", "100"])
    check("resources sub-command exits 0", rc == 0)


# ======================================================================================
# full-size bootstrap timing (opt-in)
# ======================================================================================
def timing_run():
    print("[full-size bootstrap timing: 48 pairs, real unit counts, 100,000 resamples, "
          "7 cells]")
    rng = random.Random(20260919)
    total = 0.0
    for cell in R.SAFEGUARD_CELLS:
        n = UNITS[cell]
        specs = []
        for _ in range(R.N_PAIRS):
            n_plus = rng.randint(0, int(0.04 * n))
            n_minus = rng.randint(0, int(0.04 * n))
            specs.append(spec_from(n, n_plus, n_minus))
        t0 = time.perf_counter()
        res = R.bootstrap_lower_bound(cell, specs, resamples=100_000)
        dt = time.perf_counter() - t0
        total += dt
        print(f"  {cell:>5}: n={n:>4}  LB={res['lower_bound']:+.6f}  {dt:8.2f}s")
    print(f"  TOTAL 7 cells x 100,000 resamples: {total:.2f}s")
    return total


# ======================================================================================
def main():
    tmp = tempfile.mkdtemp(prefix="a3-teacher-delay-report-")
    try:
        test_exact()
        test_power()
        test_resources()
        test_escape()
        test_bootstrap()
        test_bootstrap_equivalence()
        test_stage_acceptance(tmp)
        test_primary_below_floor(tmp)
        test_roster_missing_and_incomplete(tmp)
        test_recompute_disagreement(tmp)
        test_stuck_increase_blocks(tmp)
        test_harm_blocks(tmp)
        test_gpair_decrease_blocks(tmp)
        test_digest_mismatch_blocks(tmp)
        test_unit_and_policy_integrity(tmp)
        test_plan_integrity(tmp)
        test_secondary_cannot_move_primary(tmp)
        test_cli(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if "--timing" in sys.argv:
        timing_run()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} of {CHECKS} CHECKS FAILED:")
        for name in FAILURES:
            print(f"  - {name}")
        return 1
    print(f"ALL {CHECKS} CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
