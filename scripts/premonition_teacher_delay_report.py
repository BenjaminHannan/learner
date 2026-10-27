"""A3-teacher-delay-v2 reporting adapter (Claude/Opus, 2026-09-19).

Implements the reporting responsibility of `design/v3/12-teacher-delay-contract.md`:
full 48-pair roster accounting, the exact paired primary on L_train, the descriptive
G_pair and not-stuck tables, the seven continuous no-harm safeguards (paired
hierarchical bootstrap), censor-aware secondary escape timing, the exact planning
power sum and the full-wave resource formula -- with *distinct* stage statuses.

Pure Python standard library.  It reads only JSON produced by the planner/launcher
(`scripts/premonition_teacher_delay.py`) and the evaluator
(`scripts/premonition_teacher_delay_eval.py`).  It imports no project code, loads no
checkpoints and no tensors, touches no GPU, network, SSH or credentials, and it
launches nothing.

    PY = /Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12

    PY -B scripts/premonition_teacher_delay_report.py report \
        --plan DIR/plan.json --out DIR/report
    PY -B scripts/premonition_teacher_delay_report.py power --a .26125 --b .03625 --n 48
    PY -B scripts/premonition_teacher_delay_report.py resources \
        --jobs 96 --concurrency 96 --rate 2.9e10 --eval-seconds 200 --setup-seconds 100

`report` refuses to overwrite an existing --out directory and writes report.json and
report.txt (never a .md file).

Contract points this file is the sole owner of
-------------------------------------------------------------------------------
* Missing / invalid / incomplete / failed jobs stay in the roster of 48 pairs and
  score as FAILED outcomes for their arm; any such job also *blocks* stage
  acceptance, so a missing control can never manufacture an accepted treatment gain.
* The primary is L_train only.  It is computed before any secondary statistic and no
  secondary statistic is an input to it.  The denominator is always the registered 48.
* `specified`, `admitted`, `complete`, `stage-accepted` and `G_pair outcomes` are five
  separate fields and are never conflated.  A stage acceptance is not a G_pair
  advancement and is not G_cert.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

# --------------------------------------------------------------------------------------
# Frozen contract literals (design/v3/12-teacher-delay-contract.md).  Do not recompute.
# --------------------------------------------------------------------------------------
EXPERIMENT_ID = "A3-teacher-delay-v2"
B = 34062815112683.242                     # = B_ref / 2, B_ref = 68125630225366.484
N_PAIRS = 48
N_JOBS = 2 * N_PAIRS
ARMS = ("control", "delayed")

G_PAIR_CELLS = ("c1", "c2", "c3", "c4", "c5", "c6")
SAFEGUARD_CELLS = ("c1", "reads", "c2", "c3", "c4", "c5", "c6")   # order from the contract
L_TRAIN_CELLS = ("c1", "c2")

CUTOFF = {"c1": 1969, "c2": 1969, "c3": 1876, "c4": 945, "c5": 945, "c6": 945}
UNITS = {"c1": 2048, "c2": 2048, "c3": 2048, "c4": 1024, "c5": 1024, "c6": 1024, "reads": 512}
STUCK_BELOW = 1536                         # c1_correct < 1536/2048 is "stuck"

ALPHA = 0.05                               # exact one-sided primary size
NET_GAIN_FLOOR_NUM, NET_GAIN_FLOOR_DEN = 1, 10     # (g-l)/n >= .10, compared exactly
NO_HARM_MARGIN = -0.02                     # every lower bound must be > this
DEFAULT_RESAMPLES = 100_000
LOWER_BOUND_FRACTION = 0.05                # sorted floor(.05*R)-th, 1-indexed

TRAIN_SECONDS_CAP = 1200.0
UPDATE_CEILING = 20000
FLOP_RATE_FLOOR = B / TRAIN_SECONDS_CAP    # 2.838567926e10 counted FLOP/s
TARGET_T_SECONDS = 1500.0                  # margin target
CEILING_T_SECONDS = 1800.0                 # Ben's 30-minute wall-clock ceiling

ESCAPE_THRESHOLD = 0.3                     # strictly greater than
GOLD_SHARE = 0.2                           # gold ends at .2B for both arms
HORIZON_SHARE = 0.8                        # right-censor at .8B of post-gold compute

SCHEDULE = {"control": {"teacher_until": 0.3666, "ramp_until": 0.5334},
            "delayed": {"teacher_until": 0.6, "ramp_until": 0.7668}}
SCHEDULE_TOL = 1e-9

SELECTOR_POLICY = "not_applicable"
# The frozen trainer records `stop` as free text: "flop budget", "flop budget (the next batch
# would pass the tolerance)", "max_seconds", "max_steps", "stream ended".  The launcher's own
# completion predicate is stop.startswith("flop budget") AND budget_ok; mirror it exactly.
BUDGET_STOP_PREFIXES = ("flop budget", "flop_budget", "flop-budget")
NON_BUDGET_STOP_PREFIXES = ("max_seconds", "max_steps", "max seconds", "max steps",
                            "stream ended", "steps", "time", "update", "error", "failed")


def is_budget_stop(stop) -> bool:
    """True only for a FLOP-budget stop.  An update/time stop or a saved checkpoint is not
    training completion (contract: completion and Ben's time/cost rule)."""
    s = str(stop or "").strip().lower()
    return s.startswith(BUDGET_STOP_PREFIXES)

STAGE_LABEL = f"accepted plateau-stage background: {EXPERIMENT_ID} at B={B!r}"
NOT_ADVANCEMENT = ("This stage status is NOT a G_pair advancement and NOT G_cert. It means "
                   "improved native learned-gate attainment (L_train) with the declared "
                   "safeguards; it does not certify held-out relation transfer, does not mean "
                   "every seed escaped, and does not prove the plateau's cause.")

JOB_STATUSES = ("missing", "invalid", "failed", "incomplete", "complete-train", "complete-eval")


# ======================================================================================
# 2.  Exact paired primary test and its planning power
# ======================================================================================
def exact_p(g: int, l: int) -> float:
    """One-sided exact paired (sign) test.  p = sum_{k=g..d} C(d,k) / 2**d, 1 when d == 0."""
    if g < 0 or l < 0:
        raise ValueError("g and l must be non-negative")
    d = g + l
    if d == 0:
        return 1.0
    return sum(math.comb(d, k) for k in range(g, d + 1)) / float(2 ** d)


def net_gain_ok(g: int, l: int, n: int = N_PAIRS) -> bool:
    """(g - l) / n >= .10, compared in exact integer arithmetic."""
    return (g - l) * NET_GAIN_FLOOR_DEN >= n * NET_GAIN_FLOOR_NUM


def primary_pass(g: int, l: int, n: int = N_PAIRS) -> bool:
    """The registered primary rule: p_exact <= .05 AND (g-l)/n >= .10.  Losses enter both."""
    return exact_p(g, l) <= ALPHA and net_gain_ok(g, l, n)


def exact_power(a: float, b: float, n: int = N_PAIRS) -> float:
    """Exact primary power: sum over (g,l) passing BOTH inequalities of the multinomial

        n! / (g! l! (n-g-l)!) * a^g * b^l * (1-a-b)^(n-g-l).
    """
    if a < 0 or b < 0 or a + b > 1.0:
        raise ValueError("need a >= 0, b >= 0, a + b <= 1")
    c = 1.0 - a - b
    total = 0.0
    for g in range(n + 1):
        for l in range(n - g + 1):
            if not primary_pass(g, l, n):
                continue
            coef = math.comb(n, g) * math.comb(n - g, l)
            total += coef * (a ** g) * (b ** l) * (c ** (n - g - l))
    return total


def two_by_two(pairs_outcomes) -> dict:
    """pairs_outcomes: iterable of (control_bool, delayed_bool), one entry per registered pair.

    Returns the complete 2x2 table plus g / l / d / p_exact and the primary verdict.  The
    denominator used for the net-gain floor is always the registered 48."""
    both = ctrl_only = del_only = neither = 0
    for c, d in pairs_outcomes:
        if c and d:
            both += 1
        elif c and not d:
            ctrl_only += 1
        elif d and not c:
            del_only += 1
        else:
            neither += 1
    g, l = del_only, ctrl_only
    n = both + ctrl_only + del_only + neither
    return {"n": n,
            "control_pass_delayed_pass": both,
            "control_pass_delayed_fail": ctrl_only,
            "control_fail_delayed_pass": del_only,
            "control_fail_delayed_fail": neither,
            "control_pass_total": both + ctrl_only,
            "delayed_pass_total": both + del_only,
            "g": g, "l": l, "d": g + l,
            "p_exact": exact_p(g, l),
            "net_gain": (g - l) / float(N_PAIRS),
            "net_gain_ok": net_gain_ok(g, l, N_PAIRS),
            "primary_pass": primary_pass(g, l, N_PAIRS)}


def table_lines(title: str, t: dict) -> list:
    return [f"{title}  (denominator is always the registered {N_PAIRS})",
            "                        delayed PASS   delayed FAIL         total",
            "  control PASS   {:14d} {:14d} {:13d}".format(
                t["control_pass_delayed_pass"], t["control_pass_delayed_fail"],
                t["control_pass_total"]),
            "  control FAIL   {:14d} {:14d} {:13d}".format(
                t["control_fail_delayed_pass"], t["control_fail_delayed_fail"],
                t["control_fail_delayed_pass"] + t["control_fail_delayed_fail"]),
            "  total          {:14d} {:14d} {:13d}".format(
                t["delayed_pass_total"], t["n"] - t["delayed_pass_total"], t["n"]),
            "  g (control-fail & delayed-pass) = {g}   l (control-pass & delayed-fail) = {l}"
            "   d = {d}".format(**t),
            "  p_exact = {:.10g}   (g-l)/48 = {:.6f}".format(t["p_exact"], t["net_gain"])]


# ======================================================================================
# 4.  Paired hierarchical bootstrap for the seven continuous no-harm safeguards
# ======================================================================================
def bootstrap_seed(cell: str) -> int:
    """Manifest-derived diagnostic RNG seed: SHA-256 of 'EXPID|bootstrap|<cell>'."""
    digest = hashlib.sha256(f"{EXPERIMENT_ID}|bootstrap|{cell}".encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def diff_spec(control_units, delayed_units) -> tuple:
    """Per-pair difference summary.

    The shared-index hierarchical resample of a pair's two arms is *exactly* a resample of
    the per-unit difference array d[i] = delayed[i] - control[i], whose values lie in
    {-1, 0, +1}; so only (n, n_plus, n_minus) and the raw difference tuple are needed."""
    if len(control_units) != len(delayed_units):
        raise ValueError("arms disagree on the number of world units")
    n = len(control_units)
    diffs = tuple(int(delayed_units[i]) - int(control_units[i]) for i in range(n))
    n_plus = sum(1 for v in diffs if v > 0)
    n_minus = sum(1 for v in diffs if v < 0)
    return (n, n_plus, n_minus, diffs)


def _resample_multinomial(rnd, specs, n_pairs, resamples):
    """Multinomial shortcut (the documented method).

    Within a drawn pair, resampling n world units with replacement -- the SAME sampled
    indices for both arms -- and averaging is the mean of n iid draws from
    {-1 w.p. n_minus/n, 0 w.p. n_zero/n, +1 w.p. n_plus/n}, i.e. a multinomial over the
    three difference values.  Draw k_nz ~ Binomial(n, (n_plus+n_minus)/n) non-zero units,
    then k_plus ~ Binomial(k_nz, n_plus/(n_plus+n_minus)); the resampled mean is
    (2*k_plus - k_nz)/n.  This is statistically identical to unit resampling with shared
    indices -- an exact reparameterisation, not an approximation."""
    prepared = []
    for (n, n_plus, n_minus, _diffs) in specs:
        if n == 0:
            prepared.append((1, 0.0, 0.0, True))
            continue
        q = (n_plus + n_minus) / n
        p_plus = 0.0 if (n_plus + n_minus) == 0 else n_plus / (n_plus + n_minus)
        prepared.append((n, q, p_plus, (n_plus + n_minus) == 0))
    binom = rnd.binomialvariate
    below = rnd._randbelow
    inv = 1.0 / n_pairs
    out = []
    append = out.append
    for _ in range(resamples):
        total = 0.0
        for _ in range(n_pairs):
            n, q, p_plus, trivial = prepared[below(n_pairs)]
            if trivial:
                continue
            k_nz = binom(n, q)
            if k_nz == 0:
                continue
            if p_plus >= 1.0:
                k_plus = k_nz
            elif p_plus <= 0.0:
                k_plus = 0
            else:
                k_plus = binom(k_nz, p_plus)
            total += (2 * k_plus - k_nz) / n
        append(total * inv)
    return out


def _resample_units(rnd, specs, n_pairs, resamples):
    """Brute-force reference: literally resample world units with replacement inside each
    drawn pair, using the same sampled indices for both arms.  Only for small fixtures and
    for the equivalence test -- far slower than the multinomial shortcut."""
    below = rnd._randbelow
    inv = 1.0 / n_pairs
    out = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(n_pairs):
            n, _np_, _nm_, diffs = specs[below(n_pairs)]
            if n == 0:
                continue
            s = 0
            for _ in range(n):
                s += diffs[below(n)]
            total += s / n
        out.append(total * inv)
    return out


def bootstrap_lower_bound(cell: str, specs, resamples: int = DEFAULT_RESAMPLES,
                          method: str = "multinomial") -> dict:
    """Paired hierarchical bootstrap one-sided 95% lower bound on the treatment-minus-control
    mean accuracy for one cell.  Seed pairs are resampled with replacement and weighted
    equally (the statistic is the mean over pairs of the per-pair accuracy difference).  The
    bound is the sorted floor(.05*R)-th value, 1-indexed (the 5,000th of 100,000)."""
    n_pairs = len(specs)
    if n_pairs == 0:
        return {"cell": cell, "pairs_used": 0, "point_estimate": None, "lower_bound": None,
                "resamples": resamples, "method": method, "passes": False,
                "margin": NO_HARM_MARGIN, "note": "no usable pairs"}
    point = statistics.fmean([(s[1] - s[2]) / s[0] for s in specs if s[0] > 0])
    rnd = random.Random(bootstrap_seed(cell))
    if method == "multinomial":
        draws = _resample_multinomial(rnd, specs, n_pairs, resamples)
    elif method == "units":
        draws = _resample_units(rnd, specs, n_pairs, resamples)
    else:
        raise ValueError(f"unknown bootstrap method {method!r}")
    draws.sort()
    idx = max(1, math.floor(LOWER_BOUND_FRACTION * resamples)) - 1
    lb = draws[idx]
    return {"cell": cell, "pairs_used": n_pairs, "point_estimate": point,
            "lower_bound": lb, "resamples": resamples, "method": method,
            "order_statistic": idx + 1, "margin": NO_HARM_MARGIN,
            "passes": lb > NO_HARM_MARGIN}


# ======================================================================================
# 5.  Secondary escape timing (no pass mark, cannot touch the primary)
# ======================================================================================
def escape_timing(curve, budget: float = B, threshold: float = ESCAPE_THRESHOLD) -> dict:
    """First NON-gold saved log whose passive gold_recall_at_4 is strictly greater than .3.

    Common-horizon statistic: event time = flops - .2B, right-censored at .8B.  Logs beyond
    the nominal budget are ignored for that statistic but retained in the raw record.
    Gold-phase observations involve preloaded cards and never count as escapes.
    """
    horizon_hit = None
    raw_hit = None
    beyond_budget_logs = 0
    for e in curve or ():
        flops = float(e.get("flops", 0.0))
        if flops > budget:
            beyond_budget_logs += 1
        phase = str(e.get("phase", "")).lower()
        if phase == "gold":
            continue
        value = e.get("gold_recall_at_4")
        if value is None:
            continue
        if not (float(value) > threshold):       # strictly greater than .3
            continue
        step = float(e.get("step") or 0)
        key = (flops, step)
        rec = {"step": e.get("step"), "flops": flops, "phase": e.get("phase"),
               "gold_recall_at_4": float(value)}
        if raw_hit is None or key < (raw_hit["flops"], float(raw_hit["step"] or 0)):
            raw_hit = rec
        if flops <= budget and (horizon_hit is None
                                or key < (horizon_hit["flops"],
                                          float(horizon_hit["step"] or 0))):
            horizon_hit = rec
    horizon = budget * HORIZON_SHARE
    if horizon_hit is not None:
        restricted = min(horizon_hit["flops"] - GOLD_SHARE * budget, horizon)
        restricted = max(restricted, 0.0)
        out = {"event": True, "censored": False, "restricted_time": restricted,
               "event_step": horizon_hit["step"], "event_flops": horizon_hit["flops"],
               "event_phase": horizon_hit["phase"],
               "event_recall": horizon_hit["gold_recall_at_4"]}
    else:
        out = {"event": False, "censored": True, "restricted_time": horizon,
               "event_step": None, "event_flops": None, "event_phase": None,
               "event_recall": None}
    out["horizon"] = horizon
    out["raw_first_crossing_step"] = raw_hit["step"] if raw_hit else None
    out["raw_first_crossing_flops"] = raw_hit["flops"] if raw_hit else None
    out["raw_censored_at_run_end"] = raw_hit is None
    out["logs_beyond_nominal_budget"] = beyond_budget_logs
    out["threshold"] = threshold
    return out


# ======================================================================================
# 8.  Resource worksheet
# ======================================================================================
def resource_worksheet(jobs: int, concurrency: int, rate: float, eval_seconds: float,
                       setup_seconds: float, price_per_hour=None, machines=None) -> dict:
    if concurrency <= 0:
        raise ValueError("--concurrency must be positive")
    if rate <= 0:
        raise ValueError("--rate must be positive")
    waves = math.ceil(jobs / concurrency)
    per_job_train = B / rate
    T = setup_seconds + waves * (per_job_train + eval_seconds)
    out = {"jobs": jobs, "concurrency": concurrency, "waves": waves,
           "rate_flops_per_second": rate, "eval_seconds": eval_seconds,
           "setup_seconds": setup_seconds, "B": B,
           "per_job_training_seconds": per_job_train,
           "per_job_training_within_1200s_cap": per_job_train <= TRAIN_SECONDS_CAP,
           "required_rate_floor_flops_per_second": FLOP_RATE_FLOOR,
           "rate_meets_floor": rate >= FLOP_RATE_FLOOR,
           "T_seconds": T,
           "T_within_1500s_target": T <= TARGET_T_SECONDS,
           "T_within_1800s_ceiling": T <= CEILING_T_SECONDS,
           "nominal_training_flops_total": B * jobs,
           "formula": "T = s + ceil(jobs/C) * (B/f_rate + e)",
           "cost_usd": None, "price_per_hour": price_per_hour, "machines": machines,
           "cost_note": ("Billing minimums, billing increments, rehearsal, setup, fees, "
                         "retries and discarded work are NOT included unless the caller "
                         "folded them into --setup-seconds / --price-per-hour."),
           "admission_note": ("The per-job training floor does not by itself admit a wave. "
                              "Throughput, memory, e, s and prices require a disjoint "
                              "resource rehearsal/quote under later execution authority.")}
    if price_per_hour is not None:
        h = 1 if machines is None else machines
        out["machines"] = h
        out["cost_usd"] = h * price_per_hour * T / 3600.0
    return out


# ======================================================================================
# 1.  Roster accounting
# ======================================================================================
def _read_json(path: Path):
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, "missing"
    except Exception as exc:                        # malformed JSON, permission, ...
        return None, f"unreadable: {exc.__class__.__name__}"


def _classify(job_id: str, pair_id, arm: str, job_dir: Path) -> dict:
    """Six-way job status plus every recomputed quantity and integrity flag."""
    rec = {"job_id": job_id, "pair_id": pair_id, "arm": arm, "specified": True,
           "directory": str(job_dir), "status": "missing", "train_status": "missing",
           "eval_status": "missing", "flags": [], "integrity_failures": [],
           "counts": None, "recomputed": None, "declared": None,
           "init_state_sha256": None, "first_batches_sha256": None,
           "seconds_train": None, "parameters": None, "report": {},
           "curve_points": 0, "per_unit": None}
    result, err = _read_json(job_dir / "result.json")
    if result is None:
        rec["train_status"] = "missing" if err == "missing" else "invalid"
        rec["status"] = rec["train_status"]
        rec["eval_status"] = "not-attempted"
        rec["flags"].append(f"result.json {err}")
        rec["integrity_failures"].append(f"result.json {err}")
        return rec
    rec["init_state_sha256"] = result.get("init_state_sha256")
    rec["first_batches_sha256"] = result.get("first_batches_sha256")
    rec["seconds_train"] = result.get("seconds_train")
    rec["parameters"] = result.get("parameters")
    rec["report"] = result.get("report") or {}
    rec["curve_points"] = len(result.get("curve") or ())
    if result.get("job_id") != job_id:
        rec["integrity_failures"].append("result.json job_id does not match the plan")
    if result.get("pair_id") != pair_id:
        rec["integrity_failures"].append("result.json pair_id does not match the plan")
    if result.get("arm") != arm:
        rec["integrity_failures"].append("result.json arm does not match the plan")
    status = str(result.get("status", "")).lower()
    rep = rec["report"]
    budget_ok = rep.get("budget_ok")
    stop = str(rep.get("stop", "") or "").strip().lower()
    budget_stop = is_budget_stop(stop)
    if stop and not budget_stop and not stop.startswith(NON_BUDGET_STOP_PREFIXES):
        rec["flags"].append(f"unrecognised training stop reason {stop!r}; treated as non-budget")
    if status == "failed":
        rec["train_status"] = "failed"
    elif status == "incomplete":
        rec["train_status"] = "incomplete"
    elif status == "complete":
        if budget_ok is True and budget_stop:
            rec["train_status"] = "complete"
        else:
            rec["train_status"] = "incomplete"
            rec["flags"].append("status=complete but the FLOP-budget completion predicate "
                                f"failed (stop={rep.get('stop')!r}, budget_ok={budget_ok!r}); "
                                "an update/time stop or a saved checkpoint is insufficient")
    else:
        rec["train_status"] = "invalid"
        rec["flags"].append(f"unrecognised result.json status {result.get('status')!r}")
    steps = rep.get("steps")
    if isinstance(steps, (int, float)) and steps > UPDATE_CEILING:
        rec["flags"].append(f"steps {steps} exceed the {UPDATE_CEILING}-update safety ceiling")
    if isinstance(rec["seconds_train"], (int, float)) and rec["seconds_train"] > TRAIN_SECONDS_CAP:
        rec["flags"].append(f"seconds_train {rec['seconds_train']} exceeds the "
                            f"{TRAIN_SECONDS_CAP:.0f}s per-job training cap")
    if rec["train_status"] != "complete":
        rec["status"] = rec["train_status"]
        rec["eval_status"] = "not-attempted"
        return rec

    ev, err = _read_json(job_dir / "eval.json")
    if ev is None:
        rec["eval_status"] = "missing" if err == "missing" else "invalid"
        rec["status"] = "complete-train"
        rec["flags"].append(f"eval.json {err}")
        rec["integrity_failures"].append(f"eval.json {err}")
        return rec
    estatus = str(ev.get("status", "")).lower()
    if estatus != "complete":
        rec["eval_status"] = "failed" if estatus == "failed" else "invalid"
        rec["status"] = "complete-train"
        rec["flags"].append(f"eval.json status {ev.get('status')!r}")
        rec["integrity_failures"].append(f"eval.json status {ev.get('status')!r}")
        return rec
    rec["eval_status"] = "complete"
    if ev.get("job_id") != job_id:
        rec["integrity_failures"].append("eval.json job_id does not match the plan")
    if ev.get("pair_id") != pair_id:
        rec["integrity_failures"].append("eval.json pair_id does not match the plan")
    if ev.get("arm") != arm:
        rec["integrity_failures"].append("eval.json arm does not match the plan")
    if ev.get("selector_policy") != SELECTOR_POLICY:
        rec["integrity_failures"].append(
            f"selector_policy {ev.get('selector_policy')!r} is not {SELECTOR_POLICY!r}")

    counts = ev.get("counts") or {}
    sizes = ev.get("n") or {}
    per_unit = ev.get("per_unit") or {}
    ok_units = True
    for cell in SAFEGUARD_CELLS:
        if cell not in counts:
            rec["integrity_failures"].append(f"eval.json counts is missing {cell}")
            ok_units = False
            continue
        want = UNITS[cell]
        got = sizes.get(cell)
        if got != want:
            rec["integrity_failures"].append(
                f"{cell}: n={got!r} but the registered panel has {want} scoring units")
            ok_units = False
        units = per_unit.get(cell)
        if units is None:
            rec["integrity_failures"].append(f"eval.json per_unit is missing {cell}")
            ok_units = False
            continue
        if len(units) != want:
            rec["integrity_failures"].append(
                f"{cell}: per_unit has {len(units)} entries, expected {want} "
                "(every twin pair is ONE scoring/resampling unit)")
            ok_units = False
            continue
        if any(v not in (0, 1, True, False) for v in units):
            rec["integrity_failures"].append(f"{cell}: per_unit holds non-binary entries")
            ok_units = False
            continue
        if sum(int(v) for v in units) != counts.get(cell):
            rec["integrity_failures"].append(
                f"{cell}: per_unit sums to {sum(int(v) for v in units)} but counts says "
                f"{counts.get(cell)!r}")
            ok_units = False
    rec["counts"] = {c: counts.get(c) for c in SAFEGUARD_CELLS}
    if ok_units:
        rec["per_unit"] = {c: [int(v) for v in per_unit[c]] for c in SAFEGUARD_CELLS}

    # ---- recompute the three binary endpoints from the counts; never trust the booleans
    def _ge(cell):
        v = counts.get(cell)
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= CUTOFF[cell]

    c1 = counts.get("c1")
    recomputed = {"L_train": all(_ge(c) for c in L_TRAIN_CELLS),
                  "G_pair": all(_ge(c) for c in G_PAIR_CELLS),
                  "c1_stuck": (isinstance(c1, (int, float)) and not isinstance(c1, bool)
                               and c1 < STUCK_BELOW)}
    declared = {"L_train": ev.get("L_train"), "G_pair": ev.get("G_pair"),
                "c1_stuck": ev.get("c1_stuck")}
    rec["recomputed"], rec["declared"] = recomputed, declared
    for key, value in declared.items():
        if value is None:
            continue
        if bool(value) != recomputed[key]:
            rec["integrity_failures"].append(
                f"{key}: eval.json says {bool(value)} but the counts give {recomputed[key]}")
    rec["status"] = "complete-eval"
    return rec


def _empty_job(pair_id, arm, why):
    return {"job_id": None, "pair_id": pair_id, "arm": arm, "specified": True,
            "status": "missing", "train_status": "missing", "eval_status": "missing",
            "flags": [why], "integrity_failures": [why], "counts": None,
            "recomputed": None, "declared": None, "init_state_sha256": None,
            "first_batches_sha256": None, "seconds_train": None, "parameters": None,
            "report": {}, "curve_points": 0, "per_unit": None, "directory": None}


def build_roster(plan: dict, jobs_dir: Path) -> dict:
    pairs = plan.get("pairs") or []
    roster, problems, seen_ids = {}, [], {}
    for spec in pairs:
        pid = spec.get("pair_id")
        entry = {"pair_id": pid,
                 "seeds": {k: spec.get(k) for k in ("init_seed", "data_seed", "eval_seed")},
                 "jobs": {}, "integrity_failures": []}
        for arm in ARMS:
            jspec = (spec.get("jobs") or {}).get(arm) or {}
            job_id = jspec.get("job_id")
            if not job_id:
                why = f"plan.json pair {pid} registers no {arm} job_id"
                entry["integrity_failures"].append(why)
                entry["jobs"][arm] = _empty_job(pid, arm, why)
                continue
            seen_ids.setdefault(job_id, []).append((pid, arm))
            rec = _classify(job_id, pid, arm, jobs_dir / job_id)
            # frozen schedule fields: the ONLY independent arm difference is t
            want = SCHEDULE[arm]
            for field in ("teacher_until", "ramp_until"):
                got = jspec.get(field)
                if got is None or abs(float(got) - want[field]) > SCHEDULE_TOL:
                    rec["integrity_failures"].append(
                        f"plan {arm}.{field}={got!r}, contract requires {want[field]}")
            entry["jobs"][arm] = rec
        roster[pid] = entry
    for job_id, uses in seen_ids.items():
        if len(uses) > 1:
            problems.append(f"job_id {job_id!r} is registered more than once: {uses}")
    return {"roster": roster, "problems": problems}


def pair_digest_check(entry: dict) -> list:
    """Parity requirement 3: both arms share the initial tensors and the generated batches."""
    out = []
    c = entry["jobs"].get("control") or {}
    d = entry["jobs"].get("delayed") or {}
    trained = ("complete-train", "complete-eval")
    for field in ("init_state_sha256", "first_batches_sha256"):
        cv, dv = c.get(field), d.get(field)
        if cv is None or dv is None:
            if c.get("status") in trained and d.get("status") in trained:
                out.append(f"pair {entry['pair_id']}: {field} absent from one or both arms")
            continue
        if cv != dv:
            out.append(f"pair {entry['pair_id']}: {field} differs between arms "
                       f"({cv} vs {dv}) -- the shared prefix was not common")
    return out


# ======================================================================================
# 6.  The report
# ======================================================================================
def build_report(plan_path: Path, jobs_dir: Path, resamples: int = DEFAULT_RESAMPLES,
                 method: str = "multinomial") -> dict:
    plan = json.loads(Path(plan_path).read_text())
    spec_failures = []
    if plan.get("experiment_id") != EXPERIMENT_ID:
        spec_failures.append(f"plan experiment_id {plan.get('experiment_id')!r} is not "
                             f"{EXPERIMENT_ID!r}")
    if plan.get("B") is None or float(plan["B"]) != B:
        spec_failures.append(f"plan B {plan.get('B')!r} is not the frozen {B!r}")
    pairs = plan.get("pairs") or []
    if len(pairs) != N_PAIRS:
        spec_failures.append(f"plan registers {len(pairs)} pairs, contract requires {N_PAIRS}")

    built = build_roster(plan, jobs_dir)
    roster = built["roster"]
    spec_failures.extend(built["problems"])

    pair_ids = sorted(roster, key=lambda x: (x is None, x))
    jobs_flat = [roster[p]["jobs"][a] for p in pair_ids for a in ARMS]
    status_counts = {s: 0 for s in JOB_STATUSES}
    for j in jobs_flat:
        status_counts[j["status"]] = status_counts.get(j["status"], 0) + 1
    n_complete = sum(1 for j in jobs_flat if j["status"] == "complete-eval")
    all_complete = (len(jobs_flat) == N_JOBS and n_complete == N_JOBS)

    integrity_failures = list(spec_failures)
    for pid in pair_ids:
        entry = roster[pid]
        entry["integrity_failures"].extend(pair_digest_check(entry))
        integrity_failures.extend(entry["integrity_failures"])
        for arm in ARMS:
            job = entry["jobs"][arm]
            for msg in job["integrity_failures"]:
                integrity_failures.append(f"{job['job_id']}: {msg}")

    # ---- binary outcomes: a non-complete job is a FAILED outcome for its arm, never dropped
    def outcome(job, key, default_when_not_complete):
        if job["status"] != "complete-eval" or not job.get("recomputed"):
            return default_when_not_complete
        return bool(job["recomputed"][key])

    l_rows, g_rows, notstuck_rows, per_pair = [], [], [], []
    for pid in pair_ids:
        jc, jd = roster[pid]["jobs"]["control"], roster[pid]["jobs"]["delayed"]
        lc, ld = outcome(jc, "L_train", False), outcome(jd, "L_train", False)
        gc, gd = outcome(jc, "G_pair", False), outcome(jd, "G_pair", False)
        # a job with no valid complete evaluation has not demonstrated an escape: it is stuck
        sc, sd = outcome(jc, "c1_stuck", True), outcome(jd, "c1_stuck", True)
        l_rows.append((lc, ld))
        g_rows.append((gc, gd))
        notstuck_rows.append((not sc, not sd))
        per_pair.append({"pair_id": pid,
                         "control_status": jc["status"], "delayed_status": jd["status"],
                         "L_train": {"control": lc, "delayed": ld},
                         "G_pair": {"control": gc, "delayed": gd},
                         "c1_stuck": {"control": sc, "delayed": sd},
                         "counts": {"control": jc.get("counts"), "delayed": jd.get("counts")}})

    primary = two_by_two(l_rows)
    g_table = two_by_two(g_rows)
    notstuck = two_by_two(notstuck_rows)

    # gains whose control arm is not a valid complete record -- reported, never usable
    spurious_gains = [pid for i, pid in enumerate(pair_ids)
                      if (not l_rows[i][0] and l_rows[i][1])
                      and roster[pid]["jobs"]["control"]["status"] != "complete-eval"]

    stuck_control = sum(1 for r in notstuck_rows if not r[0])
    stuck_delayed = sum(1 for r in notstuck_rows if not r[1])
    stuck_ok = stuck_delayed <= stuck_control
    g_control = g_table["control_pass_total"]
    g_delayed = g_table["delayed_pass_total"]
    g_no_decrease = g_delayed >= g_control

    # ---- seven continuous safeguards
    safeguards, pairs_per_cell = {}, {}
    for cell in SAFEGUARD_CELLS:
        specs, skipped, c_acc, d_acc = [], [], [], []
        for pid in pair_ids:
            jc, jd = roster[pid]["jobs"]["control"], roster[pid]["jobs"]["delayed"]
            cu = (jc.get("per_unit") or {}).get(cell)
            du = (jd.get("per_unit") or {}).get(cell)
            if cu is None or du is None or len(cu) != len(du) or not cu:
                skipped.append(pid)
                continue
            specs.append(diff_spec(cu, du))
            c_acc.append(sum(cu) / len(cu))
            d_acc.append(sum(du) / len(du))
        res = bootstrap_lower_bound(cell, specs, resamples=resamples, method=method)
        res["pairs_skipped"] = skipped
        res["complete_roster"] = (len(specs) == N_PAIRS)
        res["control_mean_accuracy"] = statistics.fmean(c_acc) if c_acc else None
        res["delayed_mean_accuracy"] = statistics.fmean(d_acc) if d_acc else None
        safeguards[cell] = res
        pairs_per_cell[cell] = len(specs)
    safeguards_ok = all(safeguards[c]["passes"] for c in SAFEGUARD_CELLS)
    safeguards_complete = all(safeguards[c]["complete_roster"] for c in SAFEGUARD_CELLS)

    # ---- secondary escape timing.  Computed AFTER the primary; never an input to it.
    escape_pairs, ev_c, ev_d, joint_cens, diffs = [], 0, 0, 0, []
    for pid in pair_ids:
        row = {"pair_id": pid}
        for arm in ARMS:
            job = roster[pid]["jobs"][arm]
            curve = None
            if job["status"] in ("complete-train", "complete-eval") and job["job_id"]:
                data, _err = _read_json(jobs_dir / job["job_id"] / "result.json")
                curve = (data or {}).get("curve")
            row[arm] = escape_timing(curve, B) if curve is not None else None
        if row["control"] and row["delayed"]:
            ev_c += int(row["control"]["event"])
            ev_d += int(row["delayed"]["event"])
            if row["control"]["censored"] and row["delayed"]["censored"]:
                joint_cens += 1
            diff = row["delayed"]["restricted_time"] - row["control"]["restricted_time"]
            row["restricted_difference"] = diff
            diffs.append(diff)
        else:
            row["restricted_difference"] = None
        escape_pairs.append(row)
    secondary = {"pairs": escape_pairs,
                 "pairs_with_both_curves": len(diffs),
                 "control_events": ev_c, "delayed_events": ev_d,
                 "joint_censored_pairs": joint_cens,
                 "mean_restricted_difference": statistics.fmean(diffs) if diffs else None,
                 "median_restricted_difference": statistics.median(diffs) if diffs else None,
                 "horizon_flops": HORIZON_SHARE * B,
                 "threshold": ESCAPE_THRESHOLD,
                 "has_pass_mark": False,
                 "note": ("Secondary, descriptive only: there is no pass mark and no secondary "
                          "statistic enters the primary decision or stage acceptance. Faster "
                          "escape alone cannot rescue a failed stage acceptance. Logs beyond "
                          "the nominal budget are ignored here but retained in the raw record. "
                          "Logs average observations and may straddle a phase boundary, so "
                          "neither timestamp is an exact onset or a measured escape hazard.")}

    # ---- resource admission (only when a worksheet was frozen into the plan)
    worksheet = plan.get("resource_worksheet")
    if isinstance(worksheet, dict) and worksheet.get("T_seconds") is not None:
        T = float(worksheet["T_seconds"])
        admitted = {"state": "admitted" if T <= TARGET_T_SECONDS else "not-admitted",
                    "T_seconds": T, "within_1500s_target": T <= TARGET_T_SECONDS,
                    "within_1800s_ceiling": T <= CEILING_T_SECONDS,
                    "source": "plan.resource_worksheet",
                    "cost_exception_documented": worksheet.get("cost_exception") is not None}
    else:
        admitted = {"state": "pending",
                    "note": ("no frozen resource worksheet in plan.json; run the `resources` "
                             "sub-command and register its result. Resource admission is a "
                             "separate status and is NOT implied by completion.")}

    # ---- stage decision: five distinct statuses, never conflated
    conditions = {
        "1_primary_L_train_passes": primary["primary_pass"],
        "1b_all_96_records_valid_and_complete": all_complete,
        "2_no_increase_in_fresh_c1_stuck_count": stuck_ok,
        "3_all_seven_lower_bounds_above_margin": bool(safeguards_ok and safeguards_complete),
        "4_G_pair_pass_count_does_not_decrease": g_no_decrease,
        "5_integrity_records_clean": not integrity_failures,
    }
    blocking = [k for k, v in conditions.items() if not v]
    stage_accepted = not blocking
    statuses = {
        "specified": {"state": "specified" if not spec_failures else "specification-invalid",
                      "pairs_registered": len(pairs), "jobs_registered": len(jobs_flat),
                      "failures": spec_failures},
        "admitted": admitted,
        "complete": {"state": "complete" if all_complete else "incomplete",
                     "jobs_complete_eval": n_complete, "jobs_required": N_JOBS,
                     "job_status_counts": status_counts,
                     "note": ("Incomplete training or evaluation prevents advancement; the "
                              "affected jobs stay in the roster as FAILED outcomes rather "
                              "than manufacturing treatment gains from missing controls.")},
        "stage_accepted": {"state": "stage-accepted" if stage_accepted else "not-stage-accepted",
                           "label": STAGE_LABEL if stage_accepted else None,
                           "conditions": conditions, "blocking_reasons": blocking,
                           "is_g_pair_advancement": False, "is_g_cert": False,
                           "unlocks": ("eligibility for a separately registered relation-fix "
                                       "comparison trained afresh on a complete new roster"),
                           "statement": NOT_ADVANCEMENT},
        "g_pair_outcomes": {"state": "descriptive-only",
                            "control_pass_count": g_control,
                            "delayed_pass_count": g_delayed,
                            "does_not_decrease": g_no_decrease,
                            "table": g_table,
                            "both_rosters_all_zero": (g_control == 0 and g_delayed == 0),
                            "blocks_stage_acceptance_by_being_zero": False,
                            "note": ("Descriptive. Both G_pair rosters being all-zero does NOT "
                                     "by itself block stage acceptance: absence of a positive "
                                     "held-out score is different from a detected relative "
                                     "degradation. This count check is not a confidence-"
                                     "certified G_pair non-inferiority margin and not an "
                                     "advancement.")},
    }

    return {
        "experiment_id": EXPERIMENT_ID,
        "B": B,
        "plan_path": str(plan_path),
        "jobs_dir": str(jobs_dir),
        "n_pairs_registered": N_PAIRS,
        "primary": {"endpoint": "L_train",
                    "definition": "c1_correct >= 1969/2048 AND c2_correct >= 1969/2048",
                    "table": primary,
                    "alpha": ALPHA, "net_gain_floor": 0.10, "denominator": N_PAIRS,
                    "gains_with_non_complete_control_pairs": spurious_gains,
                    "endpoint_switching": False,
                    "sample_enlargement": False,
                    "outcome_based_replacement": False,
                    "early_efficacy_stopping": False,
                    "selective_omission": False,
                    "secondary_used_in_primary": False},
        "g_pair_table": g_table,
        "not_stuck_table": notstuck,
        "stuck": {"control_count": stuck_control, "delayed_count": stuck_delayed,
                  "no_increase": stuck_ok, "rule": f"c1_correct < {STUCK_BELOW}/2048",
                  "note": ("A job without a valid complete evaluation has not demonstrated an "
                           "escape and is scored as stuck in its own arm.")},
        "safeguards": safeguards,
        "safeguards_all_pass": bool(safeguards_ok and safeguards_complete),
        "secondary_escape_timing": secondary,
        "roster": {"pairs": per_pair,
                   "jobs": [{k: v for k, v in j.items() if k != "per_unit"}
                            for j in jobs_flat],
                   "job_status_counts": status_counts},
        "integrity_failures": integrity_failures,
        "statuses": statuses,
        "bootstrap": {"resamples": resamples, "method": method,
                      "seed_rule": f"SHA-256 of '{EXPERIMENT_ID}|bootstrap|<cell>'",
                      "lower_bound_rule": "sorted floor(0.05*R)-th difference, 1-indexed",
                      "units_per_cell": UNITS,
                      "pairs_used_per_cell": pairs_per_cell},
    }


def render_text(rep: dict) -> str:
    L = []
    add = L.append
    add(f"{EXPERIMENT_ID} stage report")
    add(f"B = {B!r} counted model FLOPs per job (frozen literal; never recomputed)")
    add(f"plan: {rep['plan_path']}")
    add(f"jobs: {rep['jobs_dir']}")
    add("")
    add("=" * 88)
    add("1. ROSTER -- all 48 registered pairs / 96 registered jobs")
    add("=" * 88)
    sc = rep["roster"]["job_status_counts"]
    add("  job status counts: " + ", ".join(f"{k}={sc.get(k, 0)}" for k in JOB_STATUSES))
    add("  No pair is ever dropped. A missing / invalid / incomplete / failed job stays in the")
    add("  roster and scores as a FAILED outcome for its arm; it also blocks advancement.")
    add("")
    add("  pair | control          | delayed          | L_train c/d | G_pair c/d | stuck c/d")
    for row in rep["roster"]["pairs"]:
        add("  {:>4} | {:<16} | {:<16} | {:^11} | {:^10} | {:^9}".format(
            str(row["pair_id"]), row["control_status"], row["delayed_status"],
            "{}/{}".format("P" if row["L_train"]["control"] else "F",
                           "P" if row["L_train"]["delayed"] else "F"),
            "{}/{}".format("P" if row["G_pair"]["control"] else "F",
                           "P" if row["G_pair"]["delayed"] else "F"),
            "{}/{}".format("Y" if row["c1_stuck"]["control"] else "n",
                           "Y" if row["c1_stuck"]["delayed"] else "n")))
    add("")
    if rep["integrity_failures"]:
        add(f"  INTEGRITY FAILURES ({len(rep['integrity_failures'])}):")
        for msg in rep["integrity_failures"]:
            add(f"    - {msg}")
    else:
        add("  integrity: no failures (plan fields, job/pair/arm identity, selector policy,")
        add("             recomputed-vs-declared booleans, unit counts, and within-pair")
        add("             init_state_sha256 / first_batches_sha256 all agree)")
    add("")
    add("=" * 88)
    add("2. PRIMARY -- L_train (c1 >= 1969/2048 AND c2 >= 1969/2048).  Sole primary endpoint.")
    add("=" * 88)
    t = rep["primary"]["table"]
    L.extend("  " + s for s in table_lines("L_train 2x2", t))
    add("  rule: p_exact <= 0.05 AND (g-l)/48 >= 0.10   ->   "
        + ("PASS" if t["primary_pass"] else "FAIL"))
    if rep["primary"]["gains_with_non_complete_control_pairs"]:
        add("  NOTE: these apparent gains have a control arm that is not a valid complete")
        add("        record: pairs " + ", ".join(
            str(p) for p in rep["primary"]["gains_with_non_complete_control_pairs"]))
        add("        They stay in the table, but the incomplete record blocks stage acceptance,")
        add("        so a missing control cannot manufacture an accepted treatment gain.")
    add("  No sample enlargement, outcome-based replacement, early efficacy stopping, endpoint")
    add("  switching or selective omission. No secondary statistic entered this decision.")
    add("")
    add("=" * 88)
    add("3. DESCRIPTIVE BINARY TABLES")
    add("=" * 88)
    L.extend("  " + s for s in table_lines("G_pair 2x2 (descriptive)", rep["g_pair_table"]))
    gp = rep["statuses"]["g_pair_outcomes"]
    add("  safeguard: observed G_pair pass count does not decrease -> control={} delayed={} {}"
        .format(gp["control_pass_count"], gp["delayed_pass_count"],
                "OK" if gp["does_not_decrease"] else "BLOCKED"))
    add("")
    L.extend("  " + s for s in table_lines("not-stuck 2x2 (descriptive)", rep["not_stuck_table"]))
    add("  safeguard: fresh c1-stuck count does not increase -> control={} delayed={} {}".format(
        rep["stuck"]["control_count"], rep["stuck"]["delayed_count"],
        "OK" if rep["stuck"]["no_increase"] else "BLOCKED"))
    add("")
    add("=" * 88)
    add("4. SEVEN CONTINUOUS NO-HARM SAFEGUARDS (treatment minus control mean accuracy)")
    add("=" * 88)
    bs = rep["bootstrap"]
    add(f"  paired hierarchical bootstrap, R = {bs['resamples']}, method = {bs['method']}")
    add(f"  seeds: {bs['seed_rule']};  bound: {bs['lower_bound_rule']}")
    add("  seed pairs resampled with replacement, then world units within each drawn pair and")
    add("  cell with replacement using the SAME sampled unit indices for both arms; every twin")
    add("  pair is one unit; seeds weighted equally.  Required: lower bound > -0.02.")
    add("")
    add("   cell |  pairs |  control mean |  delayed mean |   difference |    95% LB | verdict")
    for cell in SAFEGUARD_CELLS:
        s = rep["safeguards"][cell]
        add("  {:>5} | {:>6} | {:>13} | {:>13} | {:>12} | {:>9} | {}".format(
            cell, s["pairs_used"],
            "n/a" if s.get("control_mean_accuracy") is None
            else f"{s['control_mean_accuracy']:.6f}",
            "n/a" if s.get("delayed_mean_accuracy") is None
            else f"{s['delayed_mean_accuracy']:.6f}",
            "n/a" if s["point_estimate"] is None else f"{s['point_estimate']:+.6f}",
            "n/a" if s["lower_bound"] is None else f"{s['lower_bound']:+.6f}",
            "PASS" if s["passes"] else "BLOCKED"))
        if not s.get("complete_roster", False):
            add("        incomplete roster for this cell: pairs without a usable pair of "
                f"per-unit vectors = {s.get('pairs_skipped')}")
    add("  These are the inherited approximate intervals, not exact small-sample guarantees;")
    add("  inconclusive does not establish no harm.")
    add("")
    add("=" * 88)
    add("5. SECONDARY -- escape timing (descriptive, NO pass mark)")
    add("=" * 88)
    s = rep["secondary_escape_timing"]
    add(f"  first NON-gold saved log with gold_recall_at_4 strictly > {s['threshold']}")
    add(f"  event time = flops - 0.2B; right-censored at 0.8B = {s['horizon_flops']!r}")
    add(f"  pairs with both curves: {s['pairs_with_both_curves']}   "
        f"events control={s['control_events']} delayed={s['delayed_events']}   "
        f"jointly censored pairs={s['joint_censored_pairs']}")
    if s["mean_restricted_difference"] is not None:
        add("  paired restricted-time difference (delayed - control): "
            f"mean {s['mean_restricted_difference']:.6g}, "
            f"median {s['median_restricted_difference']:.6g} counted FLOPs")
    add("  raw first-crossing update counts per pair (control, delayed):")
    for row in s["pairs"]:
        c, d = row.get("control"), row.get("delayed")
        add("    pair {:>3}: control raw step {} (event={}), delayed raw step {} (event={})"
            .format(str(row["pair_id"]),
                    None if not c else c["raw_first_crossing_step"],
                    None if not c else c["event"],
                    None if not d else d["raw_first_crossing_step"],
                    None if not d else d["event"]))
    add("  " + s["note"])
    add("")
    add("=" * 88)
    add("6. STAGE STATUS -- five distinct statuses, never conflated")
    add("=" * 88)
    st = rep["statuses"]
    add(f"  specified        : {st['specified']['state']} "
        f"({st['specified']['pairs_registered']} pairs / "
        f"{st['specified']['jobs_registered']} jobs registered)")
    for msg in st["specified"]["failures"]:
        add(f"                     - {msg}")
    add(f"  admitted         : {st['admitted']['state']}"
        + (f"  (T = {st['admitted']['T_seconds']:.1f}s)"
           if "T_seconds" in st["admitted"] else ""))
    if "note" in st["admitted"]:
        add(f"                     {st['admitted']['note']}")
    add(f"  complete         : {st['complete']['state']} "
        f"({st['complete']['jobs_complete_eval']}/{st['complete']['jobs_required']} "
        "jobs valid and complete)")
    add(f"  G_pair outcomes  : {st['g_pair_outcomes']['state']} "
        f"(control {st['g_pair_outcomes']['control_pass_count']}, "
        f"delayed {st['g_pair_outcomes']['delayed_pass_count']})")
    add(f"  stage acceptance : {st['stage_accepted']['state']}")
    for key, value in st["stage_accepted"]["conditions"].items():
        add(f"                     [{'x' if value else ' '}] {key}")
    if st["stage_accepted"]["blocking_reasons"]:
        add("  blocking reasons: " + ", ".join(st["stage_accepted"]["blocking_reasons"]))
    add("")
    if st["stage_accepted"]["state"] == "stage-accepted":
        add("  " + STAGE_LABEL)
    else:
        add("  NOT stage-accepted. Secondary escape timing cannot override this result.")
    add("  " + NOT_ADVANCEMENT)
    add("  " + st["g_pair_outcomes"]["note"])
    add("")
    add("=" * 88)
    add("7. RESOURCE LEDGER")
    add("=" * 88)
    add("  T = s + ceil(96/C) * (B/f_rate + e);  per-job training floor B/1200 = "
        f"{FLOP_RATE_FLOOR!r} counted FLOP/s")
    add(f"  nominal training total across the roster = {B * N_JOBS!r} counted FLOPs")
    add("  Resource admission is a separate status and is not implied by completion.")
    add("")
    return "\n".join(L) + "\n"


# ======================================================================================
# CLI
# ======================================================================================
def cmd_report(a) -> int:
    plan_path = Path(a.plan).resolve()
    if not plan_path.is_file():
        raise SystemExit(f"plan not found: {plan_path}")
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {out}")
    jobs_dir = Path(a.jobs_dir).resolve() if a.jobs_dir else plan_path.parent / "jobs"
    rep = build_report(plan_path, jobs_dir, resamples=a.resamples, method=a.bootstrap_method)
    out.mkdir(parents=True, exist_ok=False)
    (out / "report.json").write_text(json.dumps(rep, indent=1, sort_keys=False))
    text = render_text(rep)
    (out / "report.txt").write_text(text)
    if not a.quiet:
        print(text)
    print(f"wrote {out / 'report.json'}")
    print(f"wrote {out / 'report.txt'}")
    return 0


def cmd_power(a) -> int:
    p = exact_power(a.a, a.b, a.n)
    print(f"exact primary power  n={a.n}  a(gain)={a.a!r}  b(loss)={a.b!r}  ->  {p:.6f}")
    print("  rule: p_exact <= 0.05 AND (g-l)/n >= 0.10, summed over every passing (g,l)")
    print("  Planning arithmetic under iid pairs. Not a model result; the safeguards lower the")
    print("  total advancement probability below this number.")
    if a.json:
        Path(a.json).write_text(json.dumps({"n": a.n, "a": a.a, "b": a.b, "power": p}, indent=1))
    return 0


def cmd_resources(a) -> int:
    w = resource_worksheet(a.jobs, a.concurrency, a.rate, a.eval_seconds, a.setup_seconds,
                           a.price_per_hour, a.machines)
    print(f"T = s + ceil({a.jobs}/{a.concurrency}) * (B/f_rate + e)")
    print(f"  waves                          {w['waves']}")
    print(f"  per-job training seconds B/f   {w['per_job_training_seconds']:.4f}"
          f"   (<= 1200s cap: {w['per_job_training_within_1200s_cap']})")
    print(f"  required rate floor B/1200     {w['required_rate_floor_flops_per_second']!r}"
          f"   (rate meets floor: {w['rate_meets_floor']})")
    print(f"  T seconds                      {w['T_seconds']:.4f}")
    print(f"  T <= 1500s target              {w['T_within_1500s_target']}")
    print(f"  T <= 1800s ceiling             {w['T_within_1800s_ceiling']}")
    print(f"  nominal training FLOPs total   {w['nominal_training_flops_total']!r}")
    if w["cost_usd"] is not None:
        print(f"  cost = machines * price/h * T/3600 = {w['cost_usd']:.4f} USD "
              f"({w['machines']} machine(s) at {w['price_per_hour']} USD/h)")
    else:
        print("  cost                           not computed (no --price-per-hour given)")
    print("  " + w["cost_note"])
    print("  " + w["admission_note"])
    if a.json:
        Path(a.json).write_text(json.dumps(w, indent=1))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=f"{EXPERIMENT_ID} stage reporting adapter")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="full roster/primary/safeguard/secondary report")
    r.add_argument("--plan", required=True)
    r.add_argument("--out", required=True, help="output directory; refuses to overwrite")
    r.add_argument("--jobs-dir", default=None, help="default: <plan dir>/jobs")
    r.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    r.add_argument("--bootstrap-method", choices=("multinomial", "units"), default="multinomial")
    r.add_argument("--quiet", action="store_true", help="write the files without echoing them")
    r.set_defaults(func=cmd_report)

    w = sub.add_parser("power", help="exact primary power for planning rates a (gain), b (loss)")
    w.add_argument("--a", type=float, required=True)
    w.add_argument("--b", type=float, required=True)
    w.add_argument("--n", type=int, default=N_PAIRS)
    w.add_argument("--json", default=None)
    w.set_defaults(func=cmd_power)

    s = sub.add_parser("resources", help="full-wave resource worksheet")
    s.add_argument("--jobs", type=int, default=N_JOBS)
    s.add_argument("--concurrency", type=int, required=True)
    s.add_argument("--rate", type=float, required=True, help="counted FLOP/s per job at load")
    s.add_argument("--eval-seconds", type=float, required=True)
    s.add_argument("--setup-seconds", type=float, required=True)
    s.add_argument("--price-per-hour", type=float, default=None)
    s.add_argument("--machines", type=int, default=None)
    s.add_argument("--json", default=None)
    s.set_defaults(func=cmd_resources)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
