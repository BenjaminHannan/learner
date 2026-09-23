"""Agent 3 INDEPENDENT numerical gate calculator for concept-toy20 `ct20-v1.1`.

Written BEFORE any accuracy result exists, from
  * design/v3/20-concept-toy-preregistration-draft.md  (sections 4, 5, 8, 9)
  * design/v3/20-concept-toy-rulings-1.md              (ct20-v1.1, rulings A2/A3/C9/C10)
  * design/v3/20-concept-toy-rulings-2.md              (R1-R5, ratification)
and from nothing else.  It imports no builder module, reads no file, opens no
network, touches no global state and holds no random seed: every function here is
a pure function of its arguments.  It is the *referee*, so it must not share code
with the thing it referees.

RULINGS-2 STAMP.  `RULINGS_2_SHA256` below is the hash of the rulings-2 file this
code was written against, computed by me from the bytes on disk.  The coordinator
announced a DIFFERENT value (`8a62ef05...`); that discrepancy is reported in
PILOT-AUDIT.md and is unresolved.  This calculator is pinned to the bytes it read.

--------------------------------------------------------------------------------
RESULT-TABLE SCHEMA  (the only input this calculator accepts)
--------------------------------------------------------------------------------
A "result table" is a plain dict:

    {
      "version": "ct20-v1.1",         # str, must equal VERSION
      "tier":    "L" | "H",           # which registered source tier produced it
      "integrity": {                  # coordinator-supplied, evaluator-independent
          "accounting_valid": bool,   # per-rung 5% cross-arm rule + never over allowance
          "audit_passed":     bool,   # freeze / causal-interface / leak audit
          "timing_ok":        bool,   # wave finished inside the registered schedule
          "complete_wave_valid": bool,   # ruling R3: BOTH train and validation jobs
                                         # ran without numerical failure or missing
                                         # fit.  Absent is NOT true: see
                                         # `complete_wave_check`.  Train-world
                                         # ACCURACY is never read.
      },
      "cases": [ CASE, ... ]          # one entry per world x seed x arm
    }

    CASE = {
      "world_public_id": str,
      "outer_split": "train" | "validation",   # only `validation` decides the gate
      "family":      "c" | "m" | "o" | "n",
      "seed":        int,                      # 20001 | 20002 | 20003
      "arm":         "G" | "T",
      "status":      "complete" | "numerical_failure" | "infrastructure_incomplete",

      # evaluator-only query error E per source budget rung, keyed by int budget.
      # `None` (or an absent key) means the cell was not produced.
      "E": {32: float|None, 64: ..., 128: ..., 256: ..., 512: float|None},

      # untrained initial-checkpoint query E on the SAME panels (prereg s5 item 3)
      "E_initial": float|None,

      # observed *training-label* fitting losses on the same initial/final audit
      # set (prereg s8).  These are trainer-side; they carry no noise-free truth.
      "L_initial": float|None,
      "L_final":   float|None,

      # evaluator-only final fitting E on that audit set.  `None` => still pending.
      "E_fit_final": float|None,
    }

Every threshold below is applied with EXACT binary64 comparison.  Ruling C9 adds
one tolerance and one only: `1e-12` on the relative fitting-loss improvement.
No other E threshold gets a tolerance, no rounding is applied anywhere, and no
library-default `isclose` is used.

--------------------------------------------------------------------------------
OUTPUT SCHEMA
--------------------------------------------------------------------------------
`evaluate_tier(table)` returns

    { "tier": str,
      "verdict": one of VERDICTS,
      "escalates_to_H": bool,          # meaningful only for tier L
      "reasons": [str, ...],           # ordered, human-readable, exact numbers
      "prerequisite": {...},           # per-arm control competence detail
      "too_easy": {...}, "learned": {...}, "advance": {...},
      "startup_labels": {case_key: label},
      "integrity": {...} }

`evaluate_two_tier(table_L, table_H=None)` returns the whole registered procedure
including whether tier H was required, forbidden, or is still missing.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

VERSION = "ct20-v1.1"

# sha256 of design/v3/20-concept-toy-rulings-1.md and -2.md, as read from disk.
RULINGS_1_SHA256 = "40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de"
RULINGS_2_SHA256 = "1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2"

# PROVENANCE (resolved 20 September 2026; supersedes this module's earlier
# RULINGS_2_SHA_MISMATCH flag).  Two separate Astra chats each wrote
# design/v3/20-concept-toy-rulings-2.md two minutes apart.  The second
# overwrote the first, so the announced hash 8a62ef05... belongs to bytes that
# no longer exist on disk and can never be reproduced.  RULINGS_2_SHA256 above
# is the governing on-disk file.  The overwritten first version survives as
# relayed text, with its own provenance header and its own (necessarily
# different) hash, at the path below; Agent 3 read both in full and found no
# conflict on any operative point.  The freeze binds both documents: where one
# is silent the other governs.
RULINGS_2_SHA256_ANNOUNCED_UNREPRODUCIBLE = (
    "8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d"
)
RULINGS_2_FIRST_VERSION_RELAYED_PATH = (
    "artifacts/fable-concept-toy20-20260920/RULINGS-2-first-version-as-relayed.md"
)
RULINGS_2_FIRST_VERSION_RELAYED_SHA256 = (
    "fac03f785ca6b0e0a0fb3954ac2308b783629b75afda23863633e1ff3bca1269"
)
RULINGS_2_SHA_PROVENANCE_RESOLVED = True

# ---------------------------------------------------------------------------
# Registered constants.  Each line carries the clause it comes from.
# ---------------------------------------------------------------------------
SEEDS = (20001, 20002, 20003)                  # prereg s2
ARMS = ("G", "T")                              # prereg s5 (wave 1 is baseline-only)
BUDGETS = (32, 64, 128, 256, 512)              # prereg s3
GATE_SPLIT = "validation"                      # prereg s5: only validation decides
CONTROL_FAMILIES = ("o", "n")
HIDDEN_FAMILIES = ("c", "m")

N_C_CASES = 12                                 # 4 validation C worlds x 3 seeds
N_CONTROL_CASES = 6                            # 2 validation control worlds x 3 seeds

CONTROL_E512_MAX = 0.10                        # s5 item 1
CONTROL_MIN_PASSING = 5                        # s5 item 1: "at least 5 of its 6"

EASY_MEDIAN_E32_MAX = 0.05                     # s5 item 2
EASY_CASE_E32_MAX = 0.10                       # s5 item 2
EASY_MIN_CASES = 10                            # s5 item 2: "at least 10/12"
EASY_MEDIAN_E512_MAX = 0.05                    # s5 item 2

LEARNED_E512_MAX = 0.50                        # s5 item 3
LEARNED_MIN_RELATIVE_DROP = 0.25               # s5 item 3: ">= 25% lower than initial"

HARD_MIN_LEARNED_CASES = 9                     # s5 item 4: "at least 9/12"

ADVANCE_MIN_MEDIAN_E32 = 0.15                  # s5 item 5
ADVANCE_MEDIAN_E512_MAX = 0.50                 # s5 item 5

# prereg s8 / ruling C9
STARTUP_INITIAL_FLOOR_LOSS = 1e-8
STARTUP_MIN_RELATIVE_IMPROVEMENT = 0.10
STARTUP_IMPROVEMENT_TOLERANCE = 1e-12          # ruling C9, the ONLY tolerance
STARTUP_NEVER_STARTED_FITTING_E = 0.80
STARTUP_LEARNED_FITTING_E = 0.25
STARTUP_TRANSFER_QUERY_E = 0.50

TIERS = ("L", "H")
TIER_ALLOWANCE_PER_RUNG = {"L": 2.0e8, "H": 1.0e9}      # ruling A2
TIER_ALLOWANCE_PER_FIT = {"L": 1.0e9, "H": 5.0e9}       # ruling A2
CROSS_ARM_MAX_RELATIVE_GAP = 0.05                       # prereg s3, per rung (A1)

STARTUP_LABELS = (
    "numerical_failure",
    "infrastructure_incomplete",
    "initially_at_floor",
    "never_started",
    "started_not_yet_learned",
    "learned_and_failed_to_transfer",
    "learned_with_generalization",
    "pending_evaluator_E",
    "invalid_measurement",
)

VERDICTS = (
    "advance",                                    # s5 item 5
    "too-easy",                                   # s5 item 2
    "too-hard",                                   # s5 item 4
    "calibration-inconclusive",                   # s5 catch-all
    "calibration-invalid/startup-or-implementation",   # s5 item 1 (control competence)
    "calibration-invalid/numerical-failure",
    "calibration-invalid/missing-required-result",
    "calibration-invalid/accounting",
    "calibration-invalid/integrity-audit",
)

# Verdicts that, per ruling A3 step 2, trigger the single tier-H escalation.
ESCALATING_VERDICTS = (
    "too-hard",
    "calibration-inconclusive",
    "calibration-invalid/startup-or-implementation",
)


class GateError(ValueError):
    """Raised only for a malformed result table, never for a bad experiment."""


# ---------------------------------------------------------------------------
# Small numeric helpers.  Deliberately explicit: no statistics.median, because
# the even-count convention has to be visible and auditable.
# ---------------------------------------------------------------------------

def median(values: Sequence[float]) -> float:
    """Median, RATIFIED by ruling R2 (was an Agent 3 ambiguity, now registered).

    R2: "Sort the exact binary64 values.  For an even number of cases, the median
    is the arithmetic mean of the two central order statistics; for an odd
    number, the central value.  Use the complete registered case set, no rounding
    or outcome-dependent case exclusion."

    R2 also forbids shortening the denominator: a missing or non-finite case
    invalidates the required result instead.  So a non-finite input returns nan -
    which every caller treats as "not usable" - and is never dropped.  An empty
    sequence raises rather than inventing a value.
    """
    if not values:
        raise GateError("median of an empty sequence")
    ordered = sorted(float(v) for v in values)
    if any(not math.isfinite(v) for v in ordered):
        return float("nan")
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def cross_arm_gap(counted_ops_by_arm: Mapping[str, float]) -> float:
    """Relative spread of counted operations across arms at ONE rung.

    RATIFIED by ruling R4: "(maximum actual counted use - minimum actual counted
    use) / maximum actual counted use <= 0.05, including all required arms under
    the same frozen engineering cost convention.  A nonpositive denominator,
    absent/non-finite entry or exceeded allowance is invalid.  Apply the rule per
    rung as registered, not only to cumulative totals."

    The bound is INCLUSIVE: exactly 0.05 passes.  A non-finite or non-positive
    entry returns nan rather than silently passing, which R4 requires.  R4 also
    states these are "matched counted operations under the registered estimate",
    NOT equal hardware work, elapsed time or energy.
    """
    values = [float(v) for v in counted_ops_by_arm.values()]
    if len(values) < 2:
        raise GateError("cross-arm gap needs at least two arms")
    if any(not math.isfinite(v) for v in values):
        return float("nan")
    hi = max(values)
    if hi <= 0.0:
        return float("nan")
    return (hi - min(values)) / hi


def cross_arm_rule_per_rung(
    counted_by_arm_by_rung: Mapping[str, Mapping[int, float]],
    tier: str,
    budgets: Sequence[int] = BUDGETS,
) -> dict[str, Any]:
    """Ruling A1: check the 5% rule at EVERY rung and never over the allowance."""
    if tier not in TIER_ALLOWANCE_PER_RUNG:
        raise GateError(f"unknown tier {tier!r}")
    allowance = TIER_ALLOWANCE_PER_RUNG[tier]
    rows, ok = [], True
    for budget in budgets:
        by_arm = {}
        for arm, per_rung in counted_by_arm_by_rung.items():
            if budget not in per_rung:
                rows.append({"budget": budget, "error": f"missing arm {arm}"})
                ok = False
                by_arm = None
                break
            by_arm[arm] = float(per_rung[budget])
        if by_arm is None:
            continue
        gap = cross_arm_gap(by_arm)
        over = {a: v for a, v in by_arm.items() if v > allowance}
        within = math.isfinite(gap) and gap <= CROSS_ARM_MAX_RELATIVE_GAP
        ok &= bool(within) and not over
        rows.append({
            "budget": budget, "counted_total_ops_by_arm": by_arm,
            "relative_gap": gap, "within_5_percent": bool(within),
            "over_allowance": over, "allowance": allowance,
        })
    total_by_arm = {
        arm: sum(float(v) for v in per_rung.values())
        for arm, per_rung in counted_by_arm_by_rung.items()
    }
    over_fit = {a: v for a, v in total_by_arm.items() if v > TIER_ALLOWANCE_PER_FIT[tier]}
    ok &= not over_fit
    return {"tier": tier, "rungs": rows, "per_fit_total_by_arm": total_by_arm,
            "per_fit_allowance": TIER_ALLOWANCE_PER_FIT[tier],
            "over_per_fit_allowance": over_fit, "accounting_valid": bool(ok)}


# ---------------------------------------------------------------------------
# Ruling C9: startup classification, evaluated in binary64.
# ---------------------------------------------------------------------------

def classify_startup(
    L_initial: float | None,
    L_final: float | None,
    E_fit_final: float | None = None,
    E_query_final: float | None = None,
    status: str = "complete",
) -> str:
    """Return one of STARTUP_LABELS.

    Order (ruling C9): failure/incomplete statuses take precedence; then
    non-finite/absent required losses are invalid, never a successful startup;
    then `L_initial <= 1e-8` is `initially_at_floor`; then a missing evaluator
    quantity is `pending_evaluator_E`; then the exact predicate

        never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)

    with `r = (L_initial - L_final) / L_initial`.
    """
    if status == "numerical_failure":
        return "numerical_failure"
    if status == "infrastructure_incomplete":
        return "infrastructure_incomplete"
    if status != "complete":
        raise GateError(f"unknown case status {status!r}")
    if L_initial is None or L_final is None:
        return "invalid_measurement"
    if not _finite(L_initial) or not _finite(L_final):
        return "invalid_measurement"
    L_initial = float(L_initial)
    L_final = float(L_final)
    if L_initial <= STARTUP_INITIAL_FLOOR_LOSS:
        # Includes L_initial == 0.0, so the ratio below never divides by zero.
        return "initially_at_floor"
    if E_fit_final is None or E_query_final is None:
        return "pending_evaluator_E"
    if not _finite(E_fit_final) or not _finite(E_query_final):
        return "invalid_measurement"
    E_fit_final = float(E_fit_final)
    E_query_final = float(E_query_final)
    r = (L_initial - L_final) / L_initial
    if (r < STARTUP_MIN_RELATIVE_IMPROVEMENT - STARTUP_IMPROVEMENT_TOLERANCE
            and E_fit_final >= STARTUP_NEVER_STARTED_FITTING_E):
        return "never_started"
    if E_fit_final > STARTUP_LEARNED_FITTING_E:
        return "started_not_yet_learned"
    if E_query_final > STARTUP_TRANSFER_QUERY_E:
        return "learned_and_failed_to_transfer"
    return "learned_with_generalization"


# ---------------------------------------------------------------------------
# Case-level helpers
# ---------------------------------------------------------------------------

def case_key(case: Mapping[str, Any]) -> str:
    return f"{case['world_public_id']}/{case['seed']}/{case['arm']}"


def _E(case: Mapping[str, Any], budget: int) -> float | None:
    table = case.get("E") or {}
    value = table.get(budget, table.get(str(budget)))
    return None if value is None else float(value)


def is_learned_case(case: Mapping[str, Any]) -> tuple[bool, str]:
    """prereg s5 item 3, RATIFIED by ruling R1 (resolves audit A8 and A9).

    R1: "The learned-case comparison is final B=512 query E_primary against that
    same arm/world/seed's untrained initial query E_primary on identical panels:
    `E_512 <= 0.50` and `E_512 <= 0.75 * E_initial`.  Initial predictions are
    measured once before fitting and shared as the initial reference across the
    five rungs.  They are not fitting-audit loss and are not a checkpoint
    selected at a small budget.  Use the unchanged nonnegative-error definitions
    and exact comparisons; add no denominator floor to this inequality."

    Both clauses are required, both are exact binary64 comparisons, there is no
    tolerance and no floor.  R1 also confines this relative rule to the C cases:
    "O/N control competence uses its absolute E marks, not a newly imposed
    relative improvement requirement", which is why `control_prerequisite` never
    calls this function.
    """
    if case.get("status") != "complete":
        return False, f"status={case.get('status')}"
    e512 = _E(case, 512)
    e0 = case.get("E_initial")
    if e512 is None or e0 is None:
        return False, "missing E_512 or E_initial"
    if not _finite(e512) or not _finite(e0):
        return False, "non-finite E_512 or E_initial"
    e512, e0 = float(e512), float(e0)
    if e512 > LEARNED_E512_MAX:
        return False, f"E_512={e512!r} > {LEARNED_E512_MAX}"
    threshold = e0 * (1.0 - LEARNED_MIN_RELATIVE_DROP)
    if not (e512 <= threshold):
        return False, f"E_512={e512!r} > 0.75*E_initial={threshold!r}"
    return True, "learned"


# ---------------------------------------------------------------------------
# Table validation: missing cells are a verdict, not an exception.
# ---------------------------------------------------------------------------

def _gate_cases(table: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [c for c in table["cases"] if c.get("outer_split") == GATE_SPLIT]


def check_completeness(table: Mapping[str, Any]) -> dict[str, Any]:
    """Every required validation world x seed x arm cell present and finite."""
    cases = _gate_cases(table)
    seen: dict[tuple[str, int, str], Mapping[str, Any]] = {}
    duplicates = []
    for c in cases:
        key = (c["world_public_id"], int(c["seed"]), c["arm"])
        if key in seen:
            duplicates.append("/".join(map(str, key)))
        seen[key] = c
    worlds = sorted({c["world_public_id"] for c in cases})
    families = {c["world_public_id"]: c["family"] for c in cases}
    n_c = sum(1 for w in worlds if families[w] in HIDDEN_FAMILIES)
    n_ctl = sum(1 for w in worlds if families[w] in CONTROL_FAMILIES)

    missing_cells, nonfinite, numerical, incomplete = [], [], [], []
    for w in worlds:
        for seed in SEEDS:
            for arm in ARMS:
                c = seen.get((w, seed, arm))
                if c is None:
                    missing_cells.append(f"{w}/{seed}/{arm}")
                    continue
                st = c.get("status")
                if st == "numerical_failure":
                    numerical.append(case_key(c))
                    continue
                if st == "infrastructure_incomplete":
                    incomplete.append(case_key(c))
                    continue
                for b in BUDGETS:
                    v = _E(c, b)
                    if v is None:
                        missing_cells.append(f"{case_key(c)}/E_{b}")
                    elif not _finite(v):
                        nonfinite.append(f"{case_key(c)}/E_{b}")
                if c.get("E_initial") is None:
                    missing_cells.append(f"{case_key(c)}/E_initial")

    missing_arms = sorted({a for a in ARMS
                           if not any(c["arm"] == a for c in cases)})
    return {
        "n_gate_worlds": len(worlds),
        "n_hidden_worlds": n_c, "n_control_worlds": n_ctl,
        "expected_hidden_cases": N_C_CASES, "expected_control_cases": N_CONTROL_CASES,
        "missing_arms": missing_arms,
        "duplicate_cells": duplicates,
        "missing_cells": missing_cells,
        "non_finite_cells": nonfinite,
        "numerical_failures": numerical,
        "infrastructure_incomplete": incomplete,
        "complete": not (missing_arms or duplicates or missing_cells
                         or nonfinite or numerical or incomplete),
    }


def complete_wave_check(table: Mapping[str, Any]) -> dict[str, Any]:
    """Ruling R3 / audit A7: the OUTER requirement, beyond the validation rows.

    R3: "A numerical failure, missing required fit/prediction, invalid accounting
    or failed integrity check anywhere in the REQUIRED COMPLETE WAVE prevents a
    pass and prevents H escalation as a scientific budget treatment.  The
    coordinator must check both train and validation jobs before submitting the
    validation-only scientific gate table.  Train-world accuracy still never
    determines the difficulty window."

    R3 then permits this calculator to validate only its validation rows, on one
    condition: "the coordinator's complete-wave checks must enforce the outer
    requirement explicitly and be included in the frozen audit."

    So this function does both halves, and refuses to assume either one.

      * It scans EVERY case in the table, including `outer_split == "train"`,
        for a numerical failure or an incomplete fit.  Train-world *accuracy* is
        never read - only whether the job ran - so the difficulty window stays
        untouched, exactly as R3 requires.
      * It requires an explicit coordinator attestation
        `integrity["complete_wave_valid"]`.  Absent is NOT treated as true: an
        unsupplied attestation leaves the outer requirement unverified, and an
        unverified outer requirement cannot buy a tier-H escalation.

    Returns `blocks_escalation=True` whenever the outer requirement is failed or
    unverified.  A validation-only table with no train rows and no attestation is
    therefore reported honestly as unverified rather than silently passed.
    """
    attested = (table.get("integrity") or {}).get("complete_wave_valid")
    train_failures, train_incomplete = [], []
    for c in table["cases"]:
        if c.get("outer_split") == GATE_SPLIT:
            continue  # the validation rows are covered by check_completeness
        st = c.get("status")
        if st == "numerical_failure":
            train_failures.append(case_key(c))
        elif st == "infrastructure_incomplete":
            train_incomplete.append(case_key(c))
    n_non_gate = sum(1 for c in table["cases"] if c.get("outer_split") != GATE_SPLIT)
    failed = bool(train_failures or train_incomplete) or attested is False
    unverified = attested is None
    notes = []
    if train_failures:
        notes.append(f"non-validation numerical failures: {train_failures[:6]}")
    if train_incomplete:
        notes.append(f"non-validation incomplete fits: {train_incomplete[:6]}")
    if attested is False:
        notes.append("coordinator attested the complete wave is NOT valid")
    if unverified:
        notes.append(
            "integrity.complete_wave_valid was not supplied: the R3 outer "
            "requirement over train and validation jobs is UNVERIFIED by this "
            "calculator, so it cannot certify a tier-H escalation")
    return {
        "attestation": attested,
        "n_non_validation_cases_seen": n_non_gate,
        "non_validation_numerical_failures": train_failures,
        "non_validation_incomplete": train_incomplete,
        "failed": bool(failed),
        "unverified": bool(unverified),
        "blocks_escalation": bool(failed or unverified),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# The five registered calibration rules (prereg s5), each pure and separate.
# ---------------------------------------------------------------------------

def control_prerequisite(table: Mapping[str, Any]) -> dict[str, Any]:
    """s5 item 1: each arm needs E_512 <= 0.10 on at least 5 of its 6 control
    world x seed cases, and no numerical failures."""
    out: dict[str, Any] = {"by_arm": {}, "passes": True}
    for arm in ARMS:
        cases = [c for c in _gate_cases(table)
                 if c["arm"] == arm and c["family"] in CONTROL_FAMILIES]
        good, bad, by_type = 0, [], {}
        for c in cases:
            e = _E(c, 512)
            ok = (c.get("status") == "complete" and e is not None and _finite(e)
                  and float(e) <= CONTROL_E512_MAX)
            if ok:
                good += 1
            else:
                bad.append(f"{case_key(c)}[{c['family']}]={e!r}")
                by_type[c["family"]] = by_type.get(c["family"], 0) + 1
        passes = (len(cases) == N_CONTROL_CASES and good >= CONTROL_MIN_PASSING)
        out["by_arm"][arm] = {
            "n_control_cases": len(cases), "passing": good,
            "required": CONTROL_MIN_PASSING, "failing": bad,
            "failing_by_control_type": by_type, "passes": passes,
        }
        out["passes"] &= passes
    out["passes"] = bool(out["passes"])
    return out


def _hidden_cases(table: Mapping[str, Any], arm: str) -> list[Mapping[str, Any]]:
    return [c for c in _gate_cases(table)
            if c["arm"] == arm and c["family"] in HIDDEN_FAMILIES]


def too_easy(table: Mapping[str, Any]) -> dict[str, Any]:
    """s5 item 2: EITHER arm satisfies all three sub-conditions."""
    out: dict[str, Any] = {"by_arm": {}, "triggers": False}
    for arm in ARMS:
        cases = _hidden_cases(table, arm)
        e32 = [_E(c, 32) for c in cases]
        e512 = [_E(c, 512) for c in cases]
        usable = all(v is not None and _finite(v) for v in e32 + e512) and bool(cases)
        detail: dict[str, Any] = {"n_cases": len(cases), "usable": usable}
        if usable:
            m32 = median([float(v) for v in e32])
            m512 = median([float(v) for v in e512])
            n_low = sum(1 for v in e32 if float(v) <= EASY_CASE_E32_MAX)
            trig = (m32 <= EASY_MEDIAN_E32_MAX
                    and n_low >= EASY_MIN_CASES
                    and m512 <= EASY_MEDIAN_E512_MAX)
            detail.update(median_E32=m32, median_E512=m512,
                          cases_E32_at_or_below_0_10=n_low, triggers=bool(trig))
        else:
            detail.update(triggers=False)
        out["by_arm"][arm] = detail
        out["triggers"] |= bool(detail["triggers"])
    out["triggers"] = bool(out["triggers"])
    return out


def learned_counts(table: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"by_arm": {}}
    for arm in ARMS:
        cases = _hidden_cases(table, arm)
        marks = {case_key(c): is_learned_case(c) for c in cases}
        n = sum(1 for ok, _ in marks.values() if ok)
        out["by_arm"][arm] = {
            "n_cases": len(cases), "learned": n,
            "required_for_not_too_hard": HARD_MIN_LEARNED_CASES,
            "detail": {k: v[1] for k, v in marks.items()},
        }
    return out


def too_hard(table: Mapping[str, Any]) -> dict[str, Any]:
    """s5 item 4: neither arm has at least 9/12 learned C cases."""
    counts = learned_counts(table)
    trig = all(counts["by_arm"][a]["learned"] < HARD_MIN_LEARNED_CASES for a in ARMS)
    counts["triggers"] = bool(trig)
    return counts


def advance_window(table: Mapping[str, Any]) -> dict[str, Any]:
    """s5 item 5, RATIFIED and made literal by ruling R5.

    R5 keeps "the preregistration's literal cross-arm window":

        min(median_G_E32, median_T_E32) >= 0.15
        at least one arm has median C E_512 <= 0.50   ==  min(...) <= 0.50

    The first clause is written by R5 as a `min`, and equals "the better arm's
    median", because R5 defines the better arm at B=32 as the one with the LOWER
    median C E_32.  The two clauses may be supplied by DIFFERENT arms: "the arm
    supplying the latter condition need not be the arm with the lower B=32
    median".  No per-case arm selection is permitted, and these two median
    clauses cannot override the registered learned-case requirement.

    R5 on ties: an exact tie at B=32 "is reported as a tie; if a single display
    ID is needed, choose G before T deterministically.  This cannot change the
    numerical gate."  Both facts are reported below, and the gate arithmetic
    reads the `min`, never the display ID.
    """
    med32, med512 = {}, {}
    for arm in ARMS:
        cases = _hidden_cases(table, arm)
        v32 = [_E(c, 32) for c in cases]
        v512 = [_E(c, 512) for c in cases]
        med32[arm] = (median([float(v) for v in v32])
                      if cases and all(v is not None and _finite(v) for v in v32)
                      else float("nan"))
        med512[arm] = (median([float(v) for v in v512])
                       if cases and all(v is not None and _finite(v) for v in v512)
                       else float("nan"))
    usable = all(math.isfinite(v) for v in list(med32.values()) + list(med512.values()))
    if not usable:
        return {"median_E32_by_arm": med32, "median_E512_by_arm": med512,
                "usable": False, "holds": False}
    # R5: the gate reads the min, never a display ID.  `min(ARMS, key=...)`
    # returns the FIRST minimum and ARMS == ("G", "T"), so an exact tie names G
    # deterministically -- but the tie is reported in its own right.
    min32 = min(med32[a] for a in ARMS)
    min512 = min(med512[a] for a in ARMS)
    tie32 = med32["G"] == med32["T"]
    better32 = min(ARMS, key=lambda a: med32[a])
    cond_a = min32 >= ADVANCE_MIN_MEDIAN_E32
    cond_b = min512 <= ADVANCE_MEDIAN_E512_MAX
    supplying = [a for a in ARMS if med512[a] <= ADVANCE_MEDIAN_E512_MAX]
    return {
        "median_E32_by_arm": med32, "median_E512_by_arm": med512,
        "min_median_E32": min32, "min_median_E512": min512,
        "better_arm_at_32": better32,
        "better_arm_median_E32": med32[better32],
        "exact_tie_at_32": bool(tie32),
        "tie_note": ("exact tie at B=32; G is named only as a deterministic "
                     "display ID and the gate arithmetic does not read it"
                     if tie32 else ""),
        "arms_supplying_E512_condition": supplying,
        "arms_differ_across_budgets": bool(supplying and better32 not in supplying),
        "condition_median_E32_at_least_0_15": bool(cond_a),
        "condition_some_arm_median_E512_at_most_0_50": bool(cond_b),
        "usable": True, "holds": bool(cond_a and cond_b),
    }


# ---------------------------------------------------------------------------
# One tier's verdict, in the registered order.
# ---------------------------------------------------------------------------

def evaluate_tier(table: Mapping[str, Any]) -> dict[str, Any]:
    if table.get("version") != VERSION:
        raise GateError(f"result table version {table.get('version')!r} != {VERSION!r}")
    tier = table.get("tier")
    if tier not in TIERS:
        raise GateError(f"unknown tier {tier!r}")

    integrity = dict(table.get("integrity") or {})
    completeness = check_completeness(table)
    wave = complete_wave_check(table)

    labels = {}
    for c in table["cases"]:
        labels[case_key(c)] = classify_startup(
            c.get("L_initial"), c.get("L_final"),
            c.get("E_fit_final"), _E(c, 512), c.get("status", "complete"))

    prereq = control_prerequisite(table)
    easy = too_easy(table)
    hard = too_hard(table)
    adv = advance_window(table)

    reasons: list[str] = []
    verdict: str | None = None

    # -- 0. integrity, in the order ruling A3 step 2 lists it -------------------
    if completeness["numerical_failures"] or wave["non_validation_numerical_failures"]:
        verdict = "calibration-invalid/numerical-failure"
        if completeness["numerical_failures"]:
            reasons.append("numerical failures: "
                           + ", ".join(completeness["numerical_failures"][:6]))
        if wave["non_validation_numerical_failures"]:
            reasons.append("ruling R3: numerical failures outside the validation "
                           "split also invalidate the complete wave: "
                           + ", ".join(wave["non_validation_numerical_failures"][:6]))
    elif wave["non_validation_incomplete"] or wave["attestation"] is False:
        verdict = "calibration-invalid/missing-required-result"
        reasons.extend(f"ruling R3 complete wave: {n}" for n in wave["notes"])
    elif (completeness["missing_arms"] or completeness["missing_cells"]
          or completeness["non_finite_cells"] or completeness["duplicate_cells"]
          or completeness["infrastructure_incomplete"]):
        verdict = "calibration-invalid/missing-required-result"
        for field in ("missing_arms", "duplicate_cells", "missing_cells",
                      "non_finite_cells", "infrastructure_incomplete"):
            if completeness[field]:
                reasons.append(f"{field}: {completeness[field][:6]}")
    elif integrity.get("accounting_valid") is False:
        verdict = "calibration-invalid/accounting"
        reasons.append("coordinator reported invalid compute accounting")
    elif (integrity.get("audit_passed") is False
          or integrity.get("timing_ok") is False):
        verdict = "calibration-invalid/integrity-audit"
        reasons.append("coordinator reported a failed integrity audit or schedule")

    # -- 1..5. the registered calibration rules --------------------------------
    if verdict is None:
        if not prereq["passes"]:
            verdict = "calibration-invalid/startup-or-implementation"
            for arm, d in prereq["by_arm"].items():
                if not d["passes"]:
                    reasons.append(
                        f"arm {arm}: {d['passing']}/{d['n_control_cases']} control cases "
                        f"with E_512<=0.10 (need {d['required']}); failing by control "
                        f"type {d['failing_by_control_type']}")
            # Ruling R3: "Print both predicates and identify which takes
            # precedence."  A descriptive too-easy or too-hard predicate may well
            # be true alongside a control failure; it does not get to win.
            reasons.append(
                f"ruling R3 precedence: control competence is evaluated BEFORE "
                f"too-easy and too-hard.  Descriptive predicates at this tier: "
                f"too_easy={easy['triggers']}, too_hard={hard['triggers']}.  "
                f"Control competence takes precedence and supplies the verdict."
                + ("  A too-easy result alongside a control failure does NOT stop "
                   "the procedure here." if easy["triggers"] else ""))
        elif easy["triggers"]:
            verdict = "too-easy"
            for arm, d in easy["by_arm"].items():
                if d.get("triggers"):
                    reasons.append(
                        f"arm {arm}: median C E_32={d['median_E32']!r}<=0.05, "
                        f"{d['cases_E32_at_or_below_0_10']}/12 cases E_32<=0.10, "
                        f"median C E_512={d['median_E512']!r}<=0.05")
        elif hard["triggers"]:
            verdict = "too-hard"
            reasons.append("learned C cases: "
                           + ", ".join(f"{a}={hard['by_arm'][a]['learned']}/12"
                                       for a in ARMS)
                           + " (need >=9 in at least one arm)")
        elif adv["holds"]:
            verdict = "advance"
            reasons.append(
                f"better arm at B=32 is {adv['better_arm_at_32']} with median C "
                f"E_32={adv['better_arm_median_E32']!r}>=0.15; median C E_512 by arm "
                f"{adv['median_E512_by_arm']} (some arm <=0.50)")
        else:
            verdict = "calibration-inconclusive"
            if adv["usable"]:
                if not adv["condition_median_E32_at_least_0_15"]:
                    reasons.append(
                        f"better arm {adv['better_arm_at_32']} median C E_32="
                        f"{adv['better_arm_median_E32']!r} < 0.15 but the too-easy rule "
                        "did not trigger: narrow middle region")
                if not adv["condition_some_arm_median_E512_at_most_0_50"]:
                    reasons.append(
                        f"no arm reaches median C E_512<=0.50: {adv['median_E512_by_arm']}")
            else:
                reasons.append("advance-window medians are not computable")

    # Ruling R3: an invalid or UNVERIFIED complete wave "prevents H escalation as
    # a scientific budget treatment", whatever the validation rows say.  Tier H
    # never escalates again: "At H, a remaining competence failure is
    # calibration-invalid and ends the version; there is no third tier."
    would_escalate = bool(tier == "L" and verdict in ESCALATING_VERDICTS)
    escalates = bool(would_escalate and not wave["blocks_escalation"])
    if would_escalate and not escalates:
        reasons.append(
            f"ruling R3: tier-L verdict {verdict!r} would normally trigger the "
            f"single tier-H budget check, but escalation is BLOCKED because the "
            f"complete-wave requirement is not satisfied ({'; '.join(wave['notes'])})")

    return {
        "version": VERSION, "tier": tier, "verdict": verdict,
        "escalates_to_H": escalates,
        "escalation_blocked_by_complete_wave": bool(would_escalate and not escalates),
        "reasons": reasons,
        "completeness": completeness, "complete_wave": wave, "integrity": integrity,
        "prerequisite": prereq, "too_easy": easy, "learned": hard,
        "advance": adv, "startup_labels": labels,
        "rulings_1_sha256": RULINGS_1_SHA256,
        "rulings_2_sha256": RULINGS_2_SHA256,
    }


# ---------------------------------------------------------------------------
# The registered two-tier procedure (ruling A3, steps 2-6).
# ---------------------------------------------------------------------------

def evaluate_two_tier(
    table_L: Mapping[str, Any],
    table_H: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """L is evaluated first; H runs at most once and only when L escalates."""
    if table_L.get("tier") != "L":
        raise GateError("the first table must be tier L")
    res_L = evaluate_tier(table_L)

    out: dict[str, Any] = {
        "version": VERSION, "tier_L": res_L, "tier_H": None,
        "H_required": res_L["escalates_to_H"],
        "H_permitted": res_L["escalates_to_H"],
    }

    if not res_L["escalates_to_H"]:
        if table_H is not None:
            out["status"] = "protocol-violation"
            out["adopted_tier"] = None
            out["final_verdict"] = "calibration-invalid/integrity-audit"
            out["explanation"] = (
                f"tier L returned {res_L['verdict']!r}, which stops without "
                "escalation; a tier-H table must not exist")
            return out
        if res_L.get("escalation_blocked_by_complete_wave"):
            # Ruling R3: the verdict is NOT a scientific result here.  The wave
            # did not complete, so neither a pass nor a difficulty statement is
            # available, and the budget treatment cannot be bought.
            out["status"] = "blocked-incomplete-wave"
            out["final_verdict"] = None
            out["adopted_tier"] = None
            out["explanation"] = (
                f"Tier L's descriptive verdict is {res_L['verdict']!r}, but ruling "
                "R3's complete-wave requirement over BOTH train and validation "
                "jobs is failed or unverified, so tier H cannot be entered as a "
                "budget treatment and no scientific verdict is available. This is "
                "not a difficulty statement and not a pass. Resolve the complete "
                "wave, then re-evaluate. "
                + "; ".join(res_L["complete_wave"]["notes"]))
            return out
        out["status"] = "complete"
        out["final_verdict"] = res_L["verdict"]
        out["adopted_tier"] = "L" if res_L["verdict"] == "advance" else None
        out["explanation"] = _explain(res_L["verdict"], "L", res_L)
        return out

    if table_H is None:
        out["status"] = "awaiting-tier-H"
        out["final_verdict"] = None
        out["adopted_tier"] = None
        out["explanation"] = (
            f"tier L returned {res_L['verdict']!r}; the registered procedure "
            "requires exactly one tier-H trajectory before any verdict is final. "
            "A tier-L failure is never evidence of intrinsic task difficulty.")
        return out

    if table_H.get("tier") != "H":
        raise GateError("the second table must be tier H")
    res_H = evaluate_tier(table_H)
    out["tier_H"] = res_H
    out["status"] = "complete"
    out["final_verdict"] = res_H["verdict"]
    out["adopted_tier"] = "H" if res_H["verdict"] == "advance" else None
    out["explanation"] = _explain(res_H["verdict"], "H", res_H, after_L=res_L["verdict"])
    if res_H["escalates_to_H"]:
        # defensive: evaluate_tier already forces False for tier H
        out["explanation"] += "  There is no third tier."
    return out


def _explain(verdict: str, tier: str, res: Mapping[str, Any],
             after_L: str | None = None) -> str:
    """Ruling A3 step 5: the wording each outcome permits, and nothing stronger."""
    if verdict == "advance":
        if tier == "H":
            return ("Tier H is in the advance window; adopt H's per-rung source "
                    f"allowance for every later source arm. Tier L returned "
                    f"{after_L!r}, so report budget-limited learning at L.")
        return ("Tier L is in the advance window; adopt L's per-rung source "
                "allowance for every later source arm.")
    if verdict == "too-easy":
        return ("Too easy: stop before building the mechanism. A too-easy result "
                "stops at either tier and never escalates.")
    if verdict == "too-hard":
        if tier == "H":
            return ("Not learned by these baselines under EITHER registered budget. "
                    "This is not proof that the toy is intrinsically too hard and not "
                    "a convergence certificate; falling loss alone supplies none.")
        return ("Tier L is too hard under the small budget. This is NOT evidence of "
                "intrinsic task difficulty; tier H must run before any difficulty "
                "statement is made.")
    if verdict == "calibration-inconclusive":
        return ("Inconclusive. A narrow middle region does not justify adjusting the "
                "pass marks; no within-v1 retuning is permitted.")
    if verdict == "calibration-invalid/startup-or-implementation":
        if tier == "H":
            return ("A control-competence failure remains at tier H: calibration-invalid, "
                    "and under ruling R3 this ENDS THE VERSION -- there is no third tier "
                    "and no further budget treatment, whatever the descriptive C "
                    "predicates say. Report which control type failed. This is not "
                    "evidence that hidden concepts are hard.")
        return ("Control competence failed at tier L. Under ruling A3 this is permitted "
                "to trigger the single budget check, because the controls may simply be "
                "under-trained; it does not excuse an implementation failure.")
    return ("Stopped without escalation: a numerical failure, missing required result, "
            "invalid accounting or failed integrity audit is never a budget question.")
