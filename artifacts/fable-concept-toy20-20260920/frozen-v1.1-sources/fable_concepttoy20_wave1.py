#!/usr/bin/env python3
"""Registered WAVE-1 driver for concept-toy20 `ct20-v1.1`  (baseline arms G and T).

This is the coordinator-side program that turns the frozen pieces into one
registered wave.  It owns no model mathematics and no scoring mathematics: the
models live in `fable_concepttoy20_models.py`, the private truth lives behind
`fable_concepttoy20_sim.py evaluate`, and the gate arithmetic lives in Agent 3's
independent `audit/gate_calculator.py`, which is IMPORTED here and never
re-implemented.  What this file contributes is the order of operations, the
resource discipline and the refusals.

Order of operations (preregistration sections 5, 8, 9 and rulings 1 + 2):

  0. stamp every input hash, and refuse to overwrite an existing wave;
  1. prove per-sequence isolation (rulings 2, public-interface ratification:
     "Each query branch must be predicted independently") and refuse to launch
     if the proof fails;
  2. run the bounded synthetic launch preflight AT THE CONCURRENCY THE WAVE WILL
     ACTUALLY USE, charge its elapsed seconds to the wave, and stop with
     `resource-infeasible` if the REMAINING complete schedule no longer fits
     inside the registered limits;
  3. fit tier L for every registered world x seed x arm through the
     boundary-checked SCHEMA.md public path, saving the initial checkpoint, every
     rung checkpoint and the executed cost ledger;
  4. seal the predictions (initial checkpoint and every rung, all 96 query
     targets per world by opaque record ID, plus the canonical audit keys) and
     hand them to the evaluator AS A SEPARATE PROCESS;
  5. finalise the `pending_evaluator_E` startup labels from the evaluator's
     answer (ruling C10), build the gate calculator's input table with a TOTAL
     adapter and call `evaluate_two_tier`;
  6. run tier H once, as a fresh complete trajectory from the same initialization
     bytes, IF AND ONLY IF the two-tier result is `awaiting-tier-H` -- re-running
     the preflight first;
  7. write a verdict JSON and a short text report.

What this file will not do: shrink the world/seed/arm counts, re-run a failed
seed, spend an unused reservation on extra fitting, let a train world touch the
gate table, or call tier H when tier L did not escalate.

Nothing here has been run on `calibration-v1.1`: `--fixture` exercises the whole
path on the two-world interface fixture, which is what the tests use.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

import torch

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
ARTIFACTS = REPO / "artifacts" / "fable-concept-toy20-20260920"
AUDIT_DIR = ARTIFACTS / "audit"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(AUDIT_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_DIR))

import fable_concepttoy20_models as M  # noqa: E402
import gate_calculator as GATE  # noqa: E402

# =============================================================================
# REGISTERED CONSTANTS
# =============================================================================

EXPERIMENT_VERSION = M.EXPERIMENT_VERSION            # "ct20-v1.1"
RULINGS_1_DOC = "design/v3/20-concept-toy-rulings-1.md"
# Two Astra chats wrote rulings 2; the second overwrote the first.  The ON-DISK
# file governs, and the overwritten first version -- the one that explicitly
# ratifies the three cost constants, per-rung query scoring and the per-rung step
# table -- is preserved as a relayed copy.  Both are stamped, because a later
# reader has to be able to see exactly which two texts this wave was run under.
RULINGS_2_DOC = "design/v3/20-concept-toy-rulings-2.md"
RULINGS_2_FIRST_VERSION_DOC = (
    "artifacts/fable-concept-toy20-20260920/RULINGS-2-first-version-as-relayed.md"
)
PREREG_DOC = "design/v3/20-concept-toy-preregistration-draft.md"
SCHEMA_DOC = "artifacts/fable-concept-toy20-20260920/SCHEMA.md"

# Ruling R1: the evaluator's primary error is (E_panel1 + E_panel2)/2, which it
# publishes under ONE key.  Kept as a single constant so a rename in the
# simulator is a one-line reconciliation here, not a hunt.
EVALUATOR_E_KEY = "E_primary"

# Preregistration section 9: "On Mac, maximum six simultaneous jobs with
# OMP/MKL/OpenBLAS/PyTorch intra-op and inter-op thread counts each set to 1."
CONCURRENCY_LIMIT = 6
THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}

# Prereg section 2: "exactly three training seeds: 20001, 20002, 20003, for every
# required world and arm", and rulings 2: "All seeds 20001/20002/20003 remain; no
# replacements or selective restarts."  These are also the gate calculator's.
SEEDS = GATE.SEEDS                                    # (20001, 20002, 20003)
ARMS = M.WAVE1_ARMS                                   # ("G", "T")
BUDGETS = M.BUDGETS                                   # (32, 64, 128, 256, 512)
TIERS = M.TIERS                                       # ("L", "H")

STAGE_INITIAL = "initial"
STAGE_FINAL = "final"
# The evaluator picks the highest-labelled rung per stage.  The initial
# checkpoint is scored once (ruling R1: "measured once before fitting and shared
# as the initial reference across the five rungs"), so it is labelled with the
# FIRST rung and never competes with a final-stage label.
INITIAL_STAGE_RUNG = BUDGETS[0]

# The frozen numerical convention for the ruling R4 / rulings-2 isolation proof.
# Measured, not assumed; see `sequence_isolation_report`.
ISOLATION_EXACT = 0.0
BATCH_SHAPE_TOLERANCE = 1e-6

WAVE_DIR_NAME = "wave1"

# The simulator and the independent calculator spell ONE ruling-C9 label
# differently.  Preregistration section 8 writes "Learned and failed to
# transfer", which is the calculator's (and the models module's)
# `learned_and_failed_to_transfer`; the simulator and SCHEMA section 8 drop the
# "and".  The two definitions are word for word identical -- fitting E <= 0.25
# with final query E > 0.50 -- so this is a spelling reconciliation, and it is
# recorded as one.  It is NOT a licence to equate two labels in general: any
# other difference between the two implementations stays a fatal disagreement.
STARTUP_LABEL_ALIASES = {"learned_failed_to_transfer": "learned_and_failed_to_transfer"}

# The phrase rulings 2 (R4) requires, and the phrase it forbids.
COST_PHRASE = "equal counted operations under the registered estimate"
FORBIDDEN_COST_PHRASE = "equal compute"


# =============================================================================
# SMALL HELPERS
# =============================================================================


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def python_executable() -> str:
    return sys.executable


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(THREAD_ENV)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def stamped_hashes(data_root: pathlib.Path) -> dict[str, str]:
    """Every input this wave depends on, by content hash.

    A wave that cannot name the exact bytes it ran on cannot be audited later,
    so this is computed before anything is fitted and written into the verdict.
    """
    data_root = pathlib.Path(data_root)
    out: dict[str, str] = {
        "models_source_sha256": M.source_hash(),
        "wave1_source_sha256": sha256_file(pathlib.Path(__file__)),
        "gate_calculator_sha256": sha256_file(AUDIT_DIR / "gate_calculator.py"),
        "simulator_source_sha256": sha256_file(HERE / "fable_concepttoy20_sim.py"),
        "public_loader_sha256": sha256_file(HERE / "fable_concepttoy20_public.py"),
        "rulings_1_sha256": sha256_file(REPO / RULINGS_1_DOC),
        "rulings_2_sha256": sha256_file(REPO / RULINGS_2_DOC),
        "rulings_2_first_version_relayed_sha256": sha256_file(REPO / RULINGS_2_FIRST_VERSION_DOC),
        "preregistration_sha256": sha256_file(REPO / PREREG_DOC),
        "schema_sha256": sha256_file(REPO / SCHEMA_DOC),
    }
    manifest = data_root / "manifest.json"
    out["data_manifest_sha256"] = sha256_file(manifest) if manifest.exists() else ""
    return out


def load_public_worlds(public_dir: pathlib.Path) -> list[dict[str, Any]]:
    """The public world list.  `outer_split` is public; `family` is NOT.

    The gate's family labels arrive later, from the evaluator, which is the only
    place they legitimately exist.
    """
    payload = json.loads((pathlib.Path(public_dir) / "worlds.json").read_text(encoding="utf-8"))
    return list(payload["worlds"])


def shard_plan(
    world_ids: list[str], seeds: tuple[int, ...] | list[int], arms: tuple[str, ...], concurrency: int
) -> list[dict[str, Any]]:
    """Split the wave into at most `concurrency` single-thread processes.

    A shard is (arm, a slice of worlds, ALL seeds).  Lanes inside one process are
    vectorised but stay mathematically independent (proved by the isolation
    guard), so this split changes the schedule's wall clock and nothing else.
    """
    per_arm = max(1, concurrency // len(arms))
    chunk = math.ceil(len(world_ids) / per_arm)
    shards: list[dict[str, Any]] = []
    for arm in arms:
        for start in range(0, len(world_ids), chunk):
            block = world_ids[start : start + chunk]
            if not block:
                continue
            shards.append(
                {
                    "shard_id": f"{arm}-{start // chunk}",
                    "arm": arm,
                    "world_ids": block,
                    "seeds": [int(s) for s in seeds],
                    "lanes": len(block) * len(seeds),
                }
            )
    return shards


# =============================================================================
# 1.  RULINGS-2 ISOLATION PROOF  (R4 / public-interface ratification)
#
# "Each query branch must be predicted independently.  No prediction may inspect
#  another query branch, including its paired counterpart; no cross-query state,
#  batch statistics, pair detection, joint fitting or prediction copying is
#  allowed. ... Vectorized inference is allowed only with independent lanes and
#  the same results as separate inference."
#
# The proof is empirical and runs on the real published panels, because that is
# the only thing that can refute a harness bug.  Two different properties are
# measured, and they are NOT the same property:
#
#   CONTENT invariance -- with the batch SHAPE held fixed, replacing every other
#   sequence in the batch (including the paired counterpart of a panel-3/panel-4
#   unit) must change no prediction AT ALL.  This is the leakage property, and it
#   is required to be EXACT (bit-identical).  A single changed bit here would mean
#   one query's answer depended on another query's content.
#
#   SHAPE invariance -- splitting the same rows across different batch sizes or
#   lane counts.  Measured bit-identical for every partition whose per-call batch
#   size is large enough for the same float32 BLAS blocking, and agreeing to
#   <= 1e-6 absolute otherwise, because float32 matrix multiply selects a
#   different kernel for a very small batch.  That is arithmetic re-association
#   inside ONE sequence's own algebra, not information crossing between
#   sequences -- which is exactly what the exact content result above proves.
#   The registered path scores each 96-row panel in a single call, so registered
#   numbers are on the exact side of this distinction.
# =============================================================================


def _predict(arm: str, parameters: dict[str, torch.Tensor], records, endpoint, features):
    with torch.no_grad():
        return M.forward(arm, parameters, records, endpoint, features)


def _lane_parameters(arm: str, world_id: str, seed: int, lanes: int = 1) -> dict[str, torch.Tensor]:
    base = M.initial_parameters(arm, world_id, seed)
    return {
        name: torch.tensor(value, dtype=torch.float32)[None, ...].repeat(
            lanes, *([1] * value.ndim)
        )
        for name, value in base.items()
    }


def sequence_isolation_report(
    arm: str,
    world_dir: pathlib.Path,
    world_id: str,
    seed: int,
    pair_index: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Measure the four registered perturbations for one arm on one real panel.

    (i)   change the companion sequences in the batch
    (ii)  reorder the batch
    (iii) change the batch partition / lane count
    (iv)  replace the other branch of a panel-3/panel-4 pair

    `pair_index` is (row, its paired counterpart row).  Pair membership is
    evaluator-side knowledge used only to CONSTRUCT the test; no prediction in
    this function is given anything but public records.
    """
    _record_ids, records, endpoint, features = M.load_queries_agent1(world_dir)
    count = int(records.shape[0])
    parameters = _lane_parameters(arm, world_id, seed)
    reference = _predict(arm, parameters, records[None, ...], endpoint, features)[0]

    # (i) companion content: keep row 0, replace every other row's sequence.
    rolled = torch.arange(count).roll(1)
    r2, e2, f2 = records.clone(), endpoint.clone(), features.clone()
    r2[1:] = records[rolled][1:]
    e2[1:] = endpoint[rolled][1:]
    f2[1:] = features[rolled][1:]
    companions = _predict(arm, parameters, r2[None, ...], e2, f2)[0]
    companion_delta = float((reference[0] - companions[0]).abs().max())

    # (ii) reorder: a fixed deterministic permutation, not a random one.
    order = torch.tensor(sorted(range(count), key=lambda i: (i * 37 + 11) % count))
    shuffled = _predict(arm, parameters, records[order][None, ...], endpoint[order], features[order])[0]
    reorder_delta = float((reference[order] - shuffled).abs().max())

    # (iii) partition / lane count.
    partition_deltas: dict[str, float] = {}
    for size in (1, 2, 3, 6, 32, 48):
        pieces = [
            _predict(
                arm, parameters, records[i : i + size][None, ...], endpoint[i : i + size], features[i : i + size]
            )[0]
            for i in range(0, count, size)
        ]
        partition_deltas[f"batch_{size}"] = float((reference - torch.cat(pieces)).abs().max())
    # Same rows, two lanes, second lane carrying a different world's ordering.
    two_lane_parameters = _lane_parameters(arm, world_id, seed, lanes=2)
    stacked = torch.cat([records[None, ...], records.flip(0)[None, ...]], dim=0)
    two_lane = _predict(arm, two_lane_parameters, stacked, endpoint, features)
    partition_deltas["two_lanes"] = float((reference - two_lane[0]).abs().max())

    # (iv) paired counterpart: replace ONLY the other branch of this row's pair.
    pair_delta: float | None = None
    if pair_index is not None:
        row, mate = pair_index
        donor = (mate + 1) % count
        while donor in (row, mate):
            donor = (donor + 1) % count
        r3, e3, f3 = records.clone(), endpoint.clone(), features.clone()
        r3[mate] = records[donor]
        e3[mate] = endpoint[donor]
        f3[mate] = features[donor]
        replaced = _predict(arm, parameters, r3[None, ...], e3, f3)[0]
        pair_delta = float((reference[row] - replaced[row]).abs().max())

    exact_content = companion_delta == ISOLATION_EXACT and (
        pair_delta is None or pair_delta == ISOLATION_EXACT
    )
    within_shape = reorder_delta == ISOLATION_EXACT and all(
        value <= BATCH_SHAPE_TOLERANCE for value in partition_deltas.values()
    )
    return {
        "arm": arm,
        "world_public_id": world_id,
        "seed": seed,
        "n_sequences": count,
        "companion_content_delta": companion_delta,
        "pair_branch_delta": pair_delta,
        "reorder_delta": reorder_delta,
        "partition_deltas": partition_deltas,
        "content_invariance_is_exact": bool(exact_content),
        "shape_invariance_within_tolerance": bool(within_shape),
        "batch_shape_tolerance": BATCH_SHAPE_TOLERANCE,
        "passes": bool(exact_content and within_shape),
    }


def find_pair_rows(private_dir: pathlib.Path, world_id: str, record_ids: list[str]) -> tuple[int, int] | None:
    """Locate one panel-3/panel-4 pair by its evaluator-side `pair_key`.

    Only used to CHOOSE which two rows to perturb.  Returns None when the private
    side is not available, in which case perturbation (iv) is skipped rather
    than faked.
    """
    path = pathlib.Path(private_dir) / world_id / "query_truth.json"
    if not path.exists():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    position = {str(record_id): index for index, record_id in enumerate(record_ids)}
    by_pair: dict[str, list[int]] = {}
    for row in rows:
        key = row.get("pair_key")
        if not key:
            continue
        index = position.get(str(row["record_id"]))
        if index is not None:
            by_pair.setdefault(str(key), []).append(index)
    for members in by_pair.values():
        if len(members) == 2:
            return (members[0], members[1])
    return None


def isolation_guard(public_dir: pathlib.Path, private_dir: pathlib.Path, world_ids: list[str]) -> dict[str, Any]:
    """Run the proof for BOTH arms and refuse to launch if it fails."""
    world_id = world_ids[0]
    world_dir = pathlib.Path(public_dir) / world_id
    record_ids, _records, _endpoint, _features = M.load_queries_agent1(world_dir)
    pair = find_pair_rows(private_dir, world_id, record_ids)
    reports = [
        sequence_isolation_report(arm, world_dir, world_id, SEEDS[0], pair) for arm in ARMS
    ]
    failures = [report for report in reports if not report["passes"]]
    out = {
        "checked_world": world_id,
        "pair_rows": list(pair) if pair else None,
        "pair_perturbation_ran": pair is not None,
        "reports": reports,
        "passes": not failures,
        "statement": (
            "with the batch shape held fixed, replacing every other sequence in the "
            "batch -- including the paired counterpart -- changes no prediction bit; "
            "reordering changes no prediction bit; repartitioning agrees bit for bit "
            f"wherever the batch size is preserved and within {BATCH_SHAPE_TOLERANCE} "
            "absolute otherwise, from float32 matrix-multiply blocking inside one "
            "sequence's own algebra"
        ),
    }
    if failures:
        raise RuntimeError(
            "rulings 2 isolation proof FAILED for "
            + ", ".join(f"{report['arm']}" for report in failures)
            + "; refusing to launch a registered wave whose predictions are not "
            "independent per query branch"
        )
    return out


# =============================================================================
# 2.  LAUNCH PREFLIGHT
# =============================================================================


def _timing_fixture_child(arm: str, lanes: int, seconds: float) -> dict[str, Any]:
    result = subprocess.run(
        [
            python_executable(),
            "-B",
            str(HERE / "fable_concepttoy20_models.py"),
            "timing-fixture",
            "--model",
            arm,
            "--lanes",
            str(lanes),
            "--seconds",
            str(seconds),
        ],
        capture_output=True,
        text=True,
        env=child_env(),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"timing fixture for arm {arm} failed: {result.stderr[-400:]}")
    return json.loads(result.stdout)["measurements"][arm]


def preflight(
    remaining_tiers: list[str],
    lanes_per_shard: int,
    concurrency: int,
    seconds: float,
    elapsed_charged: float,
) -> dict[str, Any]:
    """Prereg section 9: time a bounded synthetic fixture, then decide.

    The fixture runs at the lane count and the process concurrency the wave will
    actually use, so contention between the six single-thread jobs is inside the
    measurement rather than assumed away.  Its own elapsed time is charged to the
    wave, as section 4 requires.  The projection covers only the REMAINING tiers,
    so the tier-H preflight does not re-charge tier L's completed work.
    """
    started = time.time()
    jobs = [(arm, index) for arm in ARMS for index in range(max(1, concurrency // len(ARMS)))]
    measurements: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {
            pool.submit(_timing_fixture_child, arm, lanes_per_shard, seconds): arm for arm, _ in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            arm = futures[future]
            measured = future.result()
            # The SLOWEST concurrent observation is the one the schedule must
            # survive, so a contended machine cannot be projected away.
            previous = measurements.get(arm)
            if previous is None or float(measured["updates_per_second_all_lanes"]) < float(
                previous["updates_per_second_all_lanes"]
            ):
                measurements[arm] = measured
    fixture_seconds = time.time() - started

    # M.wave1_projection owns the schedule arithmetic; this only selects which of
    # its tiers are still ahead of us.
    full = M.wave1_projection(measurements)
    remaining_raw = sum(
        float(full["per_tier"][tier]["projected_tier_seconds"]) for tier in remaining_tiers
    )
    charged = elapsed_charged + fixture_seconds
    projected = remaining_raw * M.WAVE_TIMING_MARGIN
    usable = M.WAVE_SOFT_COMPUTE_STOP_SECONDS - M.WAVE_SCORING_RESERVE_SECONDS - charged
    fits = projected <= usable and (projected + charged) <= M.WAVE_HARD_DEADLINE_SECONDS
    return {
        "remaining_tiers": list(remaining_tiers),
        "lanes_per_shard": lanes_per_shard,
        "concurrency": concurrency,
        "fixture_seconds_charged": fixture_seconds,
        "elapsed_charged_before": elapsed_charged,
        "elapsed_charged_total": charged,
        "projected_remaining_seconds_raw": remaining_raw,
        "projected_remaining_seconds_with_margin": projected,
        "timing_margin": M.WAVE_TIMING_MARGIN,
        "scoring_reserve_seconds": M.WAVE_SCORING_RESERVE_SECONDS,
        "soft_compute_stop_seconds": M.WAVE_SOFT_COMPUTE_STOP_SECONDS,
        "hard_deadline_seconds": M.WAVE_HARD_DEADLINE_SECONDS,
        "usable_seconds_remaining": usable,
        "full_schedule_projection": full,
        "fits": bool(fits),
        "verdict": "fits" if fits else "resource-infeasible",
    }


# =============================================================================
# 3.  FITTING
# =============================================================================


def lane_is_complete(fits_dir: pathlib.Path, tier: str, arm: str, world_id: str, seed: int,
                     recorded: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Is this one fit finished, and are its bytes still the bytes we recorded?

    A fit counts as complete only with all five rung checkpoints present AND a
    predictions file that carries the INITIAL query panel, every rung's panel and
    both audit sets.  The initial panel matters: ruling R1 makes the untrained
    initial checkpoint the reference for the learned-case comparison, it is
    measured once before fitting, and a fit that resumed past it cannot produce
    it afterwards.  `recorded` is this wave's own sha record; when present, every
    hash must still match, so a file edited between sessions is refitted rather
    than trusted.
    """
    for budget in BUDGETS:
        path = M.checkpoint_path(fits_dir, arm, world_id, seed, budget, tier)
        if not path.exists():
            return False, f"missing checkpoint at rung {budget}"
        if recorded and recorded.get(f"rung{budget}") not in (None, sha256_file(path)):
            return False, f"checkpoint at rung {budget} no longer matches its recorded sha"
    predictions = M.predictions_path(fits_dir, arm, world_id, seed, tier)
    if not predictions.exists():
        return False, "no predictions file"
    if recorded and recorded.get("predictions") not in (None, sha256_file(predictions)):
        return False, "predictions file no longer matches its recorded sha"
    payload = json.loads(predictions.read_text(encoding="utf-8"))
    if not payload.get("query_predictions_initial"):
        return False, "no initial query panel (ruling R1's reference)"
    if not payload.get("audit_predictions_initial") or not payload.get("audit_predictions_final"):
        return False, "an audit set is missing"
    by_rung = payload.get("query_predictions_by_rung") or {}
    missing = [budget for budget in BUDGETS if not by_rung.get(str(budget))]
    if missing:
        return False, f"no query panel at rungs {missing}"
    return True, ""


def lane_record(fits_dir: pathlib.Path, tier: str, arm: str, world_id: str, seed: int) -> dict[str, str]:
    record = {
        f"rung{budget}": sha256_file(M.checkpoint_path(fits_dir, arm, world_id, seed, budget, tier))
        for budget in BUDGETS
        if M.checkpoint_path(fits_dir, arm, world_id, seed, budget, tier).exists()
    }
    predictions = M.predictions_path(fits_dir, arm, world_id, seed, tier)
    if predictions.exists():
        record["predictions"] = sha256_file(predictions)
    return record


def resume_shards(
    shards: list[dict[str, Any]], fits_dir: pathlib.Path, tier: str, state: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Drop the fits that are already finished; regroup what is left.

    The unit of resumption is ONE FIT, not one rung.  An unfinished fit is run
    again from its own saved initialization bytes rather than continued from a
    mid-trajectory checkpoint: the trajectory is deterministic, so this
    reproduces the registered work exactly, and unlike a mid-flight resume it
    still measures the initial reference R1 requires.  Rulings 2 R3 calls exact
    continuation after an interruption "resumption of the registered work, not a
    new seed", which is what this is.
    """
    done: list[str] = []
    todo: list[tuple[str, str, int]] = []
    for shard in shards:
        for world_id in shard["world_ids"]:
            for seed in shard["seeds"]:
                key = f"{tier}/{shard['arm']}/{world_id}/{seed}"
                complete, why = lane_is_complete(
                    fits_dir, tier, shard["arm"], world_id, int(seed), (state.get(key) or {})
                )
                if complete:
                    done.append(key)
                else:
                    todo.append((shard["arm"], world_id, int(seed)))
                    if why:
                        state.setdefault("_reasons", {})[key] = why
    grouped: dict[tuple[str, int], list[str]] = {}
    for arm, world_id, seed in todo:
        grouped.setdefault((arm, seed), []).append(world_id)
    rebuilt = [
        {
            "shard_id": f"{arm}-s{seed}",
            "arm": arm,
            "world_ids": sorted(world_ids),
            "seeds": [seed],
            "lanes": len(world_ids),
        }
        for (arm, seed), world_ids in sorted(grouped.items())
    ]
    return rebuilt, done, [f"{arm}/{world}/{seed}" for arm, world, seed in todo]


def _fit_child(shard: dict[str, Any], data_dir: pathlib.Path, out_dir: pathlib.Path, tier: str,
               ledger_dir: pathlib.Path) -> dict[str, Any]:
    ledger = ledger_dir / f"ledger-{tier}-{shard['shard_id']}.jsonl"
    command = [
        python_executable(),
        "-B",
        str(HERE / "fable_concepttoy20_models.py"),
        "fit",
        "--model",
        shard["arm"],
        "--data",
        str(data_dir),
        "--world-ids",
        *shard["world_ids"],
        "--seed",
        *[str(seed) for seed in shard["seeds"]],
        "--budget",
        str(BUDGETS[-1]),
        "--out",
        str(out_dir),
        "--tier",
        tier,
        # Deliberately NOT --resume: see `resume_shards`.  A mid-trajectory
        # resume skips the initial audit and the initial query panel, and ruling
        # R1 needs that untrained reference.  Resumption happens one whole fit at
        # a time, in the driver.
        "--ledger",
        str(ledger),
    ]
    started = time.time()
    result = subprocess.run(command, capture_output=True, text=True, env=child_env(), check=False)
    if result.returncode != 0:
        return {
            "shard_id": shard["shard_id"],
            "arm": shard["arm"],
            "tier": tier,
            "ok": False,
            "wall_seconds": time.time() - started,
            "error": result.stderr[-1000:],
            "command": command,
        }
    report = json.loads(result.stdout)
    return {
        "shard_id": shard["shard_id"],
        "arm": shard["arm"],
        "tier": tier,
        "ok": True,
        "wall_seconds": time.time() - started,
        "ledger_file": str(ledger),
        "report": report,
        "command": command,
    }


def run_tier_fits(
    shards: list[dict[str, Any]],
    data_dir: pathlib.Path,
    out_dir: pathlib.Path,
    tier: str,
    ledger_dir: pathlib.Path,
    concurrency: int,
) -> list[dict[str, Any]]:
    """At most `concurrency` single-thread fitting processes, never more."""
    ledger_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(concurrency, len(shards))) as pool:
        futures = [pool.submit(_fit_child, shard, data_dir, out_dir, tier, ledger_dir) for shard in shards]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda row: row["shard_id"])


# =============================================================================
# 4.  SEALING PREDICTIONS AND CALLING THE EVALUATOR
# =============================================================================


def collect_prediction_rows(
    out_dir: pathlib.Path, tier: str, world_ids: list[str], seeds: list[int]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Every sealed prediction this wave produced, in the evaluator's row format.

    Emitted per world x seed x arm:
      * the INITIAL checkpoint's 96 query targets  (stage=initial)
      * each rung's 96 query targets               (stage=final, rung=budget)
      * the initial and final audit predictions    (canonical audit keys)

    `gaps` records anything the fit did not produce.  Nothing is defaulted.
    """
    rows: list[dict[str, Any]] = []
    gaps: list[str] = []
    for arm in ARMS:
        for world_id in world_ids:
            for seed in seeds:
                path = M.predictions_path(out_dir, arm, world_id, seed, tier)
                if not path.exists():
                    gaps.append(f"{tier}/{arm}/{world_id}/{seed}: no predictions file")
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                common = {"arm": arm, "seed": str(seed), "world_public_id": world_id}

                initial = payload.get("query_predictions_initial")
                if not initial:
                    gaps.append(f"{tier}/{arm}/{world_id}/{seed}: no initial query predictions")
                else:
                    for record_id, value in initial.items():
                        rows.append({**common, "record_id": record_id, "prediction": float(value),
                                     "rung": str(INITIAL_STAGE_RUNG), "stage": STAGE_INITIAL})

                by_rung = payload.get("query_predictions_by_rung") or {}
                for budget in BUDGETS:
                    values = by_rung.get(str(budget))
                    if not values:
                        gaps.append(f"{tier}/{arm}/{world_id}/{seed}: no query predictions at rung {budget}")
                        continue
                    for record_id, value in values.items():
                        rows.append({**common, "record_id": record_id, "prediction": float(value),
                                     "rung": str(budget), "stage": STAGE_FINAL})

                for field, stage in (("audit_predictions_initial", STAGE_INITIAL),
                                     ("audit_predictions_final", STAGE_FINAL)):
                    audit = payload.get(field)
                    if not audit:
                        gaps.append(f"{tier}/{arm}/{world_id}/{seed}: no {field}")
                        continue
                    for key, entry in audit.items():
                        rows.append({**common, "record_id": key,
                                     "prediction": float(entry["prediction"]),
                                     "rung": "", "stage": stage})
    return rows, gaps


def run_evaluator(rows: list[dict[str, Any]], data_root: pathlib.Path, work_dir: pathlib.Path,
                  tier: str) -> dict[str, Any]:
    """Call the private scorer AS A SEPARATE PROCESS.

    Ruling C10 keeps the trainer and the evaluator apart: this process never
    imports the simulator, never opens a `private/` path, and receives back only
    the evaluator's own report.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    predictions_file = work_dir / f"predictions-{tier}.json"
    report_file = work_dir / f"evaluation-{tier}.json"
    predictions_file.write_text(
        json.dumps({"version": EXPERIMENT_VERSION, "tier": tier, "predictions": rows}, indent=1),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            python_executable(),
            "-B",
            str(HERE / "fable_concepttoy20_sim.py"),
            "evaluate",
            "--predictions",
            str(predictions_file),
            "--private",
            str(data_root),
            "--out",
            str(report_file),
        ],
        capture_output=True,
        text=True,
        env=child_env(),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"the evaluator refused the predictions: {result.stderr[-1500:]}")
    return json.loads(report_file.read_text(encoding="utf-8"))


# =============================================================================
# 5.  ACCOUNTING, THE TOTAL ADAPTER AND THE GATE
# =============================================================================


def read_ledgers(ledger_dir: pathlib.Path, tier: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(ledger_dir.glob(f"ledger-{tier}-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def executed_cross_arm_check(ledger_rows: list[dict[str, Any]], tier: str) -> dict[str, Any]:
    """Ruling R4, on EXECUTED counted operations, at EVERY rung, per fit.

    The comparison is made separately for each world x seed, because that is the
    unit the arms are matched on; the wave passes only if every one of them
    passes.  The rule and its arithmetic come from the independent calculator.
    """
    per_case: dict[tuple[str, int], dict[str, dict[int, float]]] = {}
    for row in ledger_rows:
        if str(row.get("tier")) != tier:
            continue
        key = (str(row["world_id"]), int(row["seed"]))
        per_case.setdefault(key, {}).setdefault(str(row["arm"]), {})[int(row["rung_budget"])] = float(
            row["rung_counted_total_ops"]
        )
    cases: list[dict[str, Any]] = []
    worst = 0.0
    valid = bool(per_case)
    for (world_id, seed), by_arm in sorted(per_case.items()):
        if sorted(by_arm) != sorted(ARMS):
            cases.append({"world_public_id": world_id, "seed": seed,
                          "error": f"arms present: {sorted(by_arm)}", "accounting_valid": False})
            valid = False
            continue
        result = GATE.cross_arm_rule_per_rung(by_arm, tier)
        gaps = [row["relative_gap"] for row in result["rungs"] if "relative_gap" in row]
        finite = [g for g in gaps if math.isfinite(g)]
        worst = max([worst] + finite)
        valid = valid and bool(result["accounting_valid"])
        cases.append({"world_public_id": world_id, "seed": seed, **result})
    return {
        "tier": tier,
        "rule": "(max actual counted use - min actual counted use) / max <= 0.05, inclusive, per rung",
        "phrase": COST_PHRASE,
        "n_cases": len(cases),
        "worst_relative_gap": worst,
        "accounting_valid": bool(valid),
        "cases": cases,
    }


def unused_reservations(ledger_rows: list[dict[str, Any]], tier: str) -> dict[str, Any]:
    """Ruling A1 / R4: reported separately, never spent on extra fitting."""
    by_arm_rung: dict[str, dict[int, list[float]]] = {}
    for row in ledger_rows:
        if str(row.get("tier")) != tier:
            continue
        by_arm_rung.setdefault(str(row["arm"]), {}).setdefault(int(row["rung_budget"]), []).append(
            float(row["rung_unused_reservation_ops"])
        )
    return {
        "tier": tier,
        "note": "a reservation is an upper bound, not consumed work; savings cannot buy fitting",
        "unused_ops_by_arm_by_rung": {
            arm: {str(rung): sum(values) / len(values) for rung, values in sorted(rungs.items())}
            for arm, rungs in sorted(by_arm_rung.items())
        },
    }


def build_gate_table(
    evaluation: dict[str, Any], tier: str, integrity: dict[str, bool]
) -> tuple[dict[str, Any], list[str]]:
    """TOTAL adapter: evaluator report -> the calculator's CASE schema.

    Every value is read from a NAMED evaluator field.  Nothing is defaulted,
    inferred, back-filled or guessed: a field the evaluator did not emit becomes
    an entry in `gaps`, which invalidates the wave rather than quietly shrinking
    a median's denominator (ruling R2).
    """
    gaps: list[str] = []
    e_final: dict[tuple[str, str, str], dict[int, float]] = {}
    e_initial: dict[tuple[str, str, str], float] = {}
    for group in evaluation["groups"]:
        label = str(group.get("rung", ""))
        if not label:
            continue
        try:
            budget = int(label)
        except ValueError:
            gaps.append(f"unmapped rung label {label!r}")
            continue
        if budget not in BUDGETS:
            gaps.append(f"rung label {label!r} is not a registered budget")
            continue
        for world in group["worlds"]:
            key = (str(group["arm"]), str(group["seed"]), str(world["world_public_id"]))
            if EVALUATOR_E_KEY not in world:
                gaps.append(f"{key}: evaluator did not emit {EVALUATOR_E_KEY}")
                continue
            value = world[EVALUATOR_E_KEY]
            if value is None:
                # SCHEMA section 3.2: the evaluator nulls E_primary when a horizon
                # is short of its registered count or panel 2 is short of 16.  A
                # null is a MISSING REQUIRED RESULT, never a number: the cell is
                # left absent so the calculator's completeness check fails, and
                # ruling R2 forbids shortening a median's denominator instead.
                gaps.append(
                    f"{key}/{group['stage']}/rung {budget}: {EVALUATOR_E_KEY} is null "
                    "(short panel or horizon) -- missing required result"
                )
                continue
            if not math.isfinite(float(value)):
                gaps.append(f"{key}/{group['stage']}/rung {budget}: {EVALUATOR_E_KEY} is not finite")
                continue
            if group["stage"] == STAGE_FINAL:
                e_final.setdefault(key, {})[budget] = float(value)
            elif group["stage"] == STAGE_INITIAL:
                e_initial[key] = float(value)

    cases: list[dict[str, Any]] = []
    diagnostics = evaluation.get("startup_diagnostics") or []
    if not diagnostics:
        gaps.append("evaluator emitted no startup diagnostics")
    for row in diagnostics:
        key = (str(row["arm"]), str(row["seed"]), str(row["world_public_id"]))
        for field in ("L_initial", "L_final", "E_fit_final", "status", "outer_split", "family"):
            if field not in row:
                gaps.append(f"{key}: evaluator did not emit {field}")
        if key not in e_final:
            gaps.append(f"{key}: no final-stage query E")
        if key not in e_initial:
            gaps.append(f"{key}: no initial-stage query E")
        missing_rungs = [b for b in BUDGETS if b not in e_final.get(key, {})]
        if missing_rungs:
            gaps.append(f"{key}: no query E at rungs {missing_rungs}")
        cases.append(
            {
                "world_public_id": row["world_public_id"],
                "outer_split": row["outer_split"],
                "family": row["family"],
                "seed": int(row["seed"]),
                "arm": row["arm"],
                "status": (
                    row["status"]
                    if row["status"] in ("numerical_failure", "infrastructure_incomplete")
                    else "complete"
                ),
                "E": e_final.get(key, {}),
                "E_initial": e_initial.get(key),
                "L_initial": row["L_initial"],
                "L_final": row["L_final"],
                "E_fit_final": row["E_fit_final"],
                "startup_label": row["status"],
            }
        )
    table = {
        "version": GATE.VERSION,
        "tier": tier,
        "integrity": {
            "accounting_valid": bool(integrity["accounting_valid"]),
            "audit_passed": bool(integrity["audit_passed"]),
            "timing_ok": bool(integrity["timing_ok"]),
            # Ruling R3, attested by THIS driver and required by the calculator's
            # `complete_wave_check`: absent is not true.  It is filled in by
            # `complete_wave_check` below, from all required train AND validation
            # jobs being present, finite and numerically valid -- never from any
            # train-world accuracy value.
            "complete_wave_valid": False,
        },
        "cases": cases,
    }
    return table, gaps


def complete_wave_check(table: dict[str, Any], world_ids: list[str], seeds: list[int]) -> dict[str, Any]:
    """Ruling R3: the COMPLETE wave, train worlds included, before the gate.

    The calculator validates only its validation rows by design, so R3 makes this
    outer requirement the coordinator's job, and its `complete_wave_check` now
    REQUIRES the resulting attestation in `integrity.complete_wave_valid` (an
    absent attestation is not true and cannot buy a tier-H escalation).

    Only PRESENCE, FINITENESS and the job's own status are read here.  No E value
    is compared against any threshold, so no train-world accuracy can reach the
    difficulty window, which R3 forbids.
    """
    seen = {
        (str(case["world_public_id"]), int(case["seed"]), str(case["arm"])): case
        for case in table["cases"]
    }
    missing = [
        f"{world_id}/{seed}/{arm}"
        for world_id in world_ids
        for seed in seeds
        for arm in ARMS
        if (world_id, int(seed), arm) not in seen
    ]
    failed = sorted(
        key_to_string(key)
        for key, case in seen.items()
        if case["status"] != "complete"
    )
    nonfinite = sorted(
        key_to_string(key)
        for key, case in seen.items()
        if case["E_initial"] is None
        or not math.isfinite(float(case["E_initial"]))
        or any(
            case["E"].get(budget) is None or not math.isfinite(float(case["E"][budget]))
            for budget in BUDGETS
        )
    )
    return {
        "required_cells": len(world_ids) * len(seeds) * len(ARMS),
        "present_cells": len(seen),
        "missing_cells": missing,
        "failed_cells": failed,
        "non_finite_cells": nonfinite,
        "train_and_validation_both_checked": True,
        "complete": not (missing or failed or nonfinite),
    }


def key_to_string(key: tuple[str, int, str]) -> str:
    return f"{key[0]}/{key[1]}/{key[2]}"


def finalise_startup_labels(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Ruling C10: the trainer wrote `pending_evaluator_E`; the evaluator decides.

    The two implementations of the C9 predicate -- the simulator's and the
    independent calculator's -- are compared here on the same numbers, and a
    disagreement invalidates the labels rather than picking a winner.
    """
    labels: dict[str, str] = {}
    disagreements: list[str] = []
    spelling: list[str] = []
    for row in evaluation.get("startup_diagnostics") or []:
        key = f"{row['world_public_id']}/{row['seed']}/{row['arm']}"
        emitted = str(row["status"])
        labels[key] = emitted
        independent = GATE.classify_startup(
            row.get("L_initial"),
            row.get("L_final"),
            row.get("E_fit_final"),
            row.get("E_query_final"),
            "complete" if emitted not in ("numerical_failure", "infrastructure_incomplete")
            else emitted,
        )
        if independent == emitted:
            continue
        if STARTUP_LABEL_ALIASES.get(emitted, emitted) == independent:
            spelling.append(f"{key}: evaluator={emitted} calculator={independent}")
            continue
        disagreements.append(f"{key}: evaluator={emitted} calculator={independent}")
    return {
        "labels": labels,
        "n_labels": len(labels),
        "still_pending": sorted(k for k, v in labels.items() if v == "pending_evaluator_E"),
        "independent_disagreements": disagreements,
        "spelling_reconciliations": spelling,
        "label_aliases_applied": STARTUP_LABEL_ALIASES,
        "agree": not disagreements,
    }


# =============================================================================
# 6.  THE WAVE
# =============================================================================


def text_report(verdict: dict[str, Any]) -> str:
    lines = [
        f"concept-toy20 wave 1 -- {verdict['experiment_version']}  ({verdict['mode']})",
        "",
        f"data            : {verdict['data_root']}",
        f"worlds x seeds  : {verdict['n_worlds']} x {len(verdict['seeds'])}, arms {', '.join(ARMS)}"
        f"  -> {verdict['n_fits_per_tier']} fits per tier",
        f"concurrency     : {verdict['concurrency']} single-thread processes",
        f"wall clock      : {verdict['wall_seconds']:.1f} s"
        f" (preflight charged {verdict['preflight_seconds_charged']:.1f} s)",
        "",
        "isolation (rulings 2): "
        + ("PASS" if verdict["isolation"]["passes"] else "FAIL")
        + " -- " + verdict["isolation"]["statement"],
        "",
    ]
    for tier, block in verdict["tiers"].items():
        lines += [
            f"tier {tier}:",
            f"  preflight            : {block['preflight']['verdict']}"
            f" (remaining {block['preflight']['projected_remaining_seconds_with_margin']:.1f} s"
            f" with the {block['preflight']['timing_margin']}x margin"
            f" against {block['preflight']['usable_seconds_remaining']:.1f} s usable)",
            f"  fits                 : {block['n_shards']} shards,"
            f" {block['n_fits']} fits ({block['n_fits_run_now']} run now,"
            f" {block['n_fits_reused_from_disk']} reused sha-verified from disk),"
            f" all ok = {block['all_shards_ok']}",
            f"  accounting           : valid = {block['cross_arm']['accounting_valid']},"
            f" worst per-rung gap = {block['cross_arm']['worst_relative_gap']:.6f}"
            f"  [{COST_PHRASE}]",
            f"  complete wave        : {block['complete_wave']['complete']}"
            f" ({block['complete_wave']['present_cells']}/{block['complete_wave']['required_cells']} cells)",
            f"  startup labels       : {block['startup']['n_labels']},"
            f" pending = {len(block['startup']['still_pending'])},"
            f" independent agreement = {block['startup']['agree']}"
            f" ({len(block['startup']['spelling_reconciliations'])} spelling reconciliations)",
            f"  gate verdict         : {block['gate']['verdict']}",
            "",
        ]
    lines += [
        f"two-tier status : {verdict['two_tier']['status']}",
        f"final verdict   : {verdict['two_tier'].get('final_verdict')}",
        f"explanation     : {verdict['two_tier'].get('explanation')}",
        "",
        "Cost language: the arms are matched on " + COST_PHRASE + ".  This is not "
        "equal hardware work, elapsed time or energy.",
    ]
    return "\n".join(lines)


def run_wave(
    data_root: pathlib.Path,
    out_root: pathlib.Path,
    mode: str,
    concurrency: int,
    preflight_seconds: float,
    resume: bool,
) -> dict[str, Any]:
    started = time.time()
    data_root = pathlib.Path(data_root).resolve()
    out_root = pathlib.Path(out_root).resolve()
    public_dir = data_root / "public"
    private_dir = data_root / "private"

    verdict_file = out_root / "verdict.json"
    if verdict_file.exists() and not resume:
        raise FileExistsError(
            f"{verdict_file} already exists; a registered wave is never overwritten. "
            "Pass --resume to continue the same wave, or choose another --out."
        )
    out_root.mkdir(parents=True, exist_ok=True)

    worlds = load_public_worlds(public_dir)
    world_ids = [str(row["world_public_id"]) for row in worlds]
    seeds = [int(seed) for seed in SEEDS]
    shards = shard_plan(world_ids, seeds, ARMS, concurrency)

    hashes = stamped_hashes(data_root)
    isolation = isolation_guard(public_dir, private_dir, world_ids)

    verdict: dict[str, Any] = {
        "experiment_version": EXPERIMENT_VERSION,
        "mode": mode,
        "data_root": str(data_root),
        "out_root": str(out_root),
        "n_worlds": len(world_ids),
        "world_public_ids": world_ids,
        "splits": {str(row["world_public_id"]): str(row["outer_split"]) for row in worlds},
        "seeds": seeds,
        "arms": list(ARMS),
        "n_fits_per_tier": len(world_ids) * len(seeds) * len(ARMS),
        "concurrency": concurrency,
        "evaluator_E_key": EVALUATOR_E_KEY,
        "hashes": hashes,
        "isolation": isolation,
        "tiers": {},
        "shards": shards,
    }

    charged = 0.0
    remaining = ["L", "H"]
    table_L: dict[str, Any] | None = None
    table_H: dict[str, Any] | None = None
    two_tier: dict[str, Any] = {}

    for tier in TIERS:
        if tier == "H" and two_tier.get("status") != "awaiting-tier-H":
            break
        check = preflight(
            remaining_tiers=remaining,
            lanes_per_shard=max(shard["lanes"] for shard in shards),
            concurrency=concurrency,
            seconds=preflight_seconds,
            elapsed_charged=charged,
        )
        charged = check["elapsed_charged_total"]
        if not check["fits"]:
            verdict["tiers"][tier] = {"preflight": check}
            verdict["two_tier"] = {
                "status": "resource-infeasible",
                "final_verdict": "resource-infeasible",
                "explanation": (
                    "the remaining complete schedule no longer fits inside the registered "
                    "limits; the wave stops before fitting rather than launching an "
                    "inevitably partial experiment"
                ),
            }
            verdict["wall_seconds"] = time.time() - started
            verdict["preflight_seconds_charged"] = charged
            verdict["cost_language"] = COST_PHRASE
            verdict_file.write_text(
                json.dumps(verdict, indent=1, sort_keys=True, default=str), encoding="utf-8"
            )
            (out_root / "report.txt").write_text(text_report(verdict), encoding="utf-8")
            return verdict

        ledger_dir = out_root / f"tier{tier}" / "ledgers"
        fits_dir = out_root / "fits"
        state_file = out_root / "state.json"
        state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
        pending, already_done, refitting = resume_shards(shards, fits_dir, tier, state)
        shard_results = (
            run_tier_fits(pending, public_dir, fits_dir, tier, ledger_dir, concurrency)
            if pending
            else []
        )
        failures = [row for row in shard_results if not row["ok"]]
        for arm in ARMS:
            for world_id in world_ids:
                for seed in seeds:
                    state[f"{tier}/{arm}/{world_id}/{seed}"] = lane_record(
                        fits_dir, tier, arm, world_id, seed
                    )
        state.pop("_reasons", None)
        state_file.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")

        ledger_rows = read_ledgers(ledger_dir, tier)
        cross_arm = executed_cross_arm_check(ledger_rows, tier)
        reservations = unused_reservations(ledger_rows, tier)

        rows, gaps = collect_prediction_rows(fits_dir, tier, world_ids, seeds)
        evaluation = run_evaluator(rows, data_root, out_root / f"tier{tier}", tier)
        startup = finalise_startup_labels(evaluation)

        timing_ok = (time.time() - started + charged) <= M.WAVE_SOFT_COMPUTE_STOP_SECONDS
        audit_passed = bool(
            isolation["passes"]
            and not failures
            and not gaps
            and startup["agree"]
            and int(evaluation.get("n_unknown_record_ids", 0)) == 0
        )
        table, adapter_gaps = build_gate_table(
            evaluation,
            tier,
            {
                "accounting_valid": cross_arm["accounting_valid"],
                "audit_passed": audit_passed,
                "timing_ok": timing_ok,
            },
        )
        # The adapter's own gaps are integrity failures too, and they exist only
        # after it has run, so the flag is tightened here rather than guessed
        # before.  It is only ever tightened, never relaxed.
        table["integrity"]["audit_passed"] = bool(
            table["integrity"]["audit_passed"] and not adapter_gaps
        )
        complete = complete_wave_check(table, world_ids, seeds)
        table["integrity"]["complete_wave_valid"] = bool(complete["complete"])
        if not complete["complete"]:
            table["integrity"]["audit_passed"] = False

        gate = GATE.evaluate_tier(table)
        calculator_outer = GATE.complete_wave_check(table)
        verdict["tiers"][tier] = {
            "preflight": check,
            "n_shards": len(shard_results),
            "n_fits": len(world_ids) * len(seeds) * len(ARMS),
            "n_fits_reused_from_disk": len(already_done),
            "n_fits_run_now": len(refitting),
            "all_shards_ok": not failures,
            "shard_failures": failures,
            "prediction_gaps": gaps,
            "adapter_gaps": adapter_gaps,
            "n_prediction_rows": len(rows),
            "evaluator_version": evaluation.get("version"),
            "n_unknown_record_ids": evaluation.get("n_unknown_record_ids"),
            "cross_arm": cross_arm,
            "unused_reservations": reservations,
            "complete_wave": complete,
            "complete_wave_calculator_view": calculator_outer,
            "startup": startup,
            "gate": gate,
            "table_file": str(out_root / f"tier{tier}" / "gate_table.json"),
        }
        (out_root / f"tier{tier}").mkdir(parents=True, exist_ok=True)
        (out_root / f"tier{tier}" / "gate_table.json").write_text(
            json.dumps(table, indent=1, sort_keys=True), encoding="utf-8"
        )

        if tier == "L":
            table_L = table
            two_tier = GATE.evaluate_two_tier(table_L)
            remaining = ["H"]
            # Rulings 2 R3: a numerical failure, missing required result, invalid
            # accounting or failed integrity check anywhere in the required
            # complete wave prevents H escalation as a budget treatment.
            if not (cross_arm["accounting_valid"] and complete["complete"] and not failures):
                two_tier = dict(two_tier)
                two_tier["status"] = "complete"
                two_tier["H_permitted"] = False
                two_tier["explanation"] = (
                    "tier H is not run: the required complete wave did not pass its "
                    "integrity/completeness/accounting checks, and ruling R3 puts those "
                    "ahead of every scientific predicate. " + str(two_tier.get("explanation", ""))
                )
                break
        else:
            table_H = table
            two_tier = GATE.evaluate_two_tier(table_L, table_H)

    verdict["two_tier"] = two_tier
    verdict["wall_seconds"] = time.time() - started
    verdict["preflight_seconds_charged"] = charged
    verdict["cost_language"] = COST_PHRASE
    verdict_file.write_text(json.dumps(verdict, indent=1, sort_keys=True, default=str), encoding="utf-8")
    (out_root / "report.txt").write_text(text_report(verdict), encoding="utf-8")
    return verdict


# =============================================================================
# CLI
# =============================================================================


def main(argv: list[str] | None = None) -> int:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="run the identical path end to end on fixture-v1.1 (not a registered wave)",
    )
    parser.add_argument("--data", default=None, help="data root holding public/ and private/")
    parser.add_argument("--out", default=None, help="output root (refuses to overwrite)")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY_LIMIT)
    parser.add_argument("--preflight-seconds", type=float, default=6.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--isolation-only",
        action="store_true",
        help="run the rulings-2 isolation proof and exit",
    )
    options = parser.parse_args(argv)

    if options.concurrency > CONCURRENCY_LIMIT:
        parser.error(
            f"the preregistration caps this machine at {CONCURRENCY_LIMIT} simultaneous jobs"
        )

    data_root = pathlib.Path(
        options.data or (ARTIFACTS / ("fixture-v1.1" if options.fixture else "calibration-v1.1"))
    )
    out_root = pathlib.Path(
        options.out
        or (ARTIFACTS / WAVE_DIR_NAME / ("fixture" if options.fixture else "registered"))
    )

    if options.isolation_only:
        worlds = load_public_worlds(data_root / "public")
        report = isolation_guard(
            data_root / "public", data_root / "private", [str(w["world_public_id"]) for w in worlds]
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    try:
        verdict = run_wave(
            data_root=data_root,
            out_root=out_root,
            mode="fixture" if options.fixture else "registered",
            concurrency=options.concurrency,
            preflight_seconds=options.preflight_seconds,
            resume=options.resume,
        )
    except FileExistsError as error:
        print(str(error), file=sys.stderr)
        return 4

    print(text_report(verdict))
    if verdict["two_tier"].get("final_verdict") == "resource-infeasible":
        print("resource-infeasible", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
