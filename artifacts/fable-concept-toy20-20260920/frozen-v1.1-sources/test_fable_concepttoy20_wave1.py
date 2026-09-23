#!/usr/bin/env python3
"""Checks for the registered wave-1 driver, `scripts/fable_concepttoy20_wave1.py`.

Two jobs.

  A. The rulings-2 ISOLATION PROOF (public-interface ratification, "Each query
     branch must be predicted independently").  For BOTH arms, on the real
     published panels, the four registered perturbations: change the companion
     sequences, reorder the batch, change the batch partition / lane count, and
     replace the other branch of a panel-3/panel-4 pair.  The tests also check
     that the harness REFUSES to launch when the proof fails.

  B. The driver itself, end to end on `fixture-v1.1` in a scratch directory --
     the identical code path the registered wave uses, with the same preflight,
     the same fitting subprocesses, the same separate evaluator process, the same
     total adapter and the same imported gate calculator.

Nothing here reads, fits or scores `calibration-v1.1`; the registered wave is
launched by the coordinator after the auditor closes the freeze.

Run:  python3 tests/test_fable_concepttoy20_wave1.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

import torch

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "fable-concept-toy20-20260920"
FIXTURE = ARTIFACTS / "fixture-v1.1"
CALIBRATION = ARTIFACTS / "calibration-v1.1"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ARTIFACTS / "audit"))
W = _load("fable_concepttoy20_wave1", ROOT / "scripts" / "fable_concepttoy20_wave1.py")
M = W.M
GATE = W.GATE

PASSED = 0
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSED
    if ok:
        PASSED += 1
        print(f"ok  {name}" + (f" -- {detail}" if detail else ""))
    else:
        FAILED.append(name)
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))


# =============================================================================
# GROUP: rulings-2 isolation proof (item A).
# =============================================================================


def group_isolation() -> None:
    public = FIXTURE / "public"
    world_id = sorted(entry.name for entry in public.iterdir() if entry.is_dir())[0]
    world_dir = public / world_id
    record_ids, _records, _endpoint, _features = M.load_queries_agent1(world_dir)
    pair = W.find_pair_rows(FIXTURE / "private", world_id, record_ids)
    check(
        "isolation: a real panel-3/panel-4 PAIR was located, so perturbation (iv) "
        "perturbs an actual paired counterpart rather than an arbitrary neighbour",
        pair is not None and len(pair) == 2 and pair[0] != pair[1],
        str(pair),
    )

    for arm in M.WAVE1_ARMS:
        report = W.sequence_isolation_report(arm, world_dir, world_id, 20001, pair)

        check(
            f"isolation[{arm}] (i): replacing EVERY companion sequence in the batch, at a "
            "fixed batch shape, changes the target prediction by exactly zero -- no query "
            "can read another query's content",
            report["companion_content_delta"] == 0.0,
            f"delta {report['companion_content_delta']}",
        )
        check(
            f"isolation[{arm}] (ii): reordering the batch reproduces every prediction bit "
            "for bit, so position in the batch carries no information",
            report["reorder_delta"] == 0.0,
            f"delta {report['reorder_delta']}",
        )
        check(
            f"isolation[{arm}] (iii): every batch partition and lane count reproduces the "
            "single-call panel to within the frozen convention, and EXACTLY when the "
            "per-call batch size is preserved",
            report["partition_deltas"]["batch_32"] == 0.0
            and report["partition_deltas"]["batch_48"] == 0.0
            and report["partition_deltas"]["two_lanes"] == 0.0
            and all(v <= W.BATCH_SHAPE_TOLERANCE for v in report["partition_deltas"].values()),
            "max "
            f"{max(report['partition_deltas'].values()):.3g} <= {W.BATCH_SHAPE_TOLERANCE}",
        )
        check(
            f"isolation[{arm}] (iv): replacing the OTHER BRANCH of this row's own "
            "panel-3/panel-4 pair with a different sequence changes this row's prediction "
            "by exactly zero -- the paired counterpart is not inspected",
            report["pair_branch_delta"] == 0.0,
            f"delta {report['pair_branch_delta']}",
        )
        check(
            f"isolation[{arm}]: the report separates EXACT content invariance from "
            "tolerance-bounded shape invariance, and both hold",
            report["content_invariance_is_exact"]
            and report["shape_invariance_within_tolerance"]
            and report["passes"],
        )

    # The distinction the frozen convention rests on: the only deviations are
    # caused by batch SIZE, never by batch CONTENT.  If content mattered even at
    # the last bit, the two numbers below could not be exactly zero while the
    # small-batch numbers are not.
    reference = W.sequence_isolation_report("T", world_dir, world_id, 20001, pair)
    check(
        "isolation: the measured deviations are a property of batch SIZE alone -- the "
        "content and ordering perturbations are exactly zero while a 1-row batch is not, "
        "which is float32 matrix-multiply blocking, not information flow",
        reference["companion_content_delta"] == 0.0
        and reference["reorder_delta"] == 0.0
        and reference["partition_deltas"]["batch_1"] > 0.0,
        f"batch_1 {reference['partition_deltas']['batch_1']:.3g}",
    )

    # And the harness must REFUSE, not warn, when the proof fails.
    original = W.sequence_isolation_report
    try:
        W.sequence_isolation_report = lambda *a, **k: {"arm": "G", "passes": False}
        refused = ""
        try:
            W.isolation_guard(public, FIXTURE / "private", [world_id])
        except RuntimeError as error:
            refused = str(error)
    finally:
        W.sequence_isolation_report = original
    check(
        "isolation: a failed proof REFUSES to launch the wave rather than recording a "
        "warning and fitting anyway",
        "refusing to launch" in refused,
        refused[:80],
    )

    passing = W.isolation_guard(public, FIXTURE / "private", [world_id])
    check(
        "isolation: the guard runs both registered arms and states its frozen numerical "
        "convention in words",
        passing["passes"]
        and len(passing["reports"]) == len(M.WAVE1_ARMS)
        and "no prediction bit" in passing["statement"],
    )


# =============================================================================
# GROUP: the registered plan, its limits and its stamps.
# =============================================================================


def group_plan() -> None:
    world_ids = [f"w{i:02d}" for i in range(12)]
    shards = W.shard_plan(world_ids, W.SEEDS, M.WAVE1_ARMS, W.CONCURRENCY_LIMIT)
    check(
        "plan: the wave is split into at most six single-thread processes, as the "
        "preregistration's Mac limit requires",
        len(shards) <= W.CONCURRENCY_LIMIT,
        f"{len(shards)} shards",
    )
    covered = sorted(
        (world_id, seed, shard["arm"])
        for shard in shards
        for world_id in shard["world_ids"]
        for seed in shard["seeds"]
    )
    expected = sorted(
        (world_id, seed, arm)
        for world_id in world_ids
        for seed in W.SEEDS
        for arm in M.WAVE1_ARMS
    )
    check(
        "plan: the shards cover every world x seed x arm EXACTLY once -- 72 fits, no "
        "duplicate and no dropped cell",
        covered == expected and len(covered) == 72,
        f"{len(covered)} cells",
    )
    check(
        "plan: the registered seeds are the calculator's own 20001/20002/20003, taken "
        "from one place so they cannot drift",
        tuple(W.SEEDS) == (20001, 20002, 20003) and W.SEEDS == GATE.SEEDS,
    )
    check(
        "plan: every child process is forced to one thread per library",
        all(value == "1" for value in W.THREAD_ENV.values())
        and {"OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"} <= set(W.THREAD_ENV),
    )
    code = W.main(["--concurrency", "7", "--fixture", "--isolation-only"]) if False else None
    check(
        "plan: a concurrency above six is refused by the CLI rather than silently clamped",
        _cli_rejects_concurrency(),
        str(code),
    )

    hashes = W.stamped_hashes(FIXTURE)
    required = {
        "models_source_sha256",
        "wave1_source_sha256",
        "gate_calculator_sha256",
        "simulator_source_sha256",
        "public_loader_sha256",
        "rulings_1_sha256",
        "rulings_2_sha256",
        "rulings_2_first_version_relayed_sha256",
        "preregistration_sha256",
        "schema_sha256",
        "data_manifest_sha256",
    }
    check(
        "stamps: the wave records the content hash of every input it depends on -- both "
        "rulings documents including the overwritten first version, the schema, the "
        "calculator, the simulator, the loader and the data manifest",
        required <= set(hashes) and all(len(hashes[key]) == 64 for key in required),
        f"{len(hashes)} stamps",
    )
    check(
        "stamps: the governing rulings-2 hash is the ON-DISK file, and the relayed first "
        "version is stamped separately rather than conflated with it",
        hashes["rulings_2_sha256"]
        == W.sha256_file(ROOT / "design" / "v3" / "20-concept-toy-rulings-2.md")
        and hashes["rulings_2_first_version_relayed_sha256"]
        != hashes["rulings_2_sha256"],
        hashes["rulings_2_sha256"][:12],
    )
    check(
        "stamps: the evaluator's gate key is read from ONE constant, so a rename on the "
        "simulator side is a one-line reconciliation",
        W.EVALUATOR_E_KEY == "E_primary",
        W.EVALUATOR_E_KEY,
    )


def _cli_rejects_concurrency() -> bool:
    try:
        W.main(["--fixture", "--isolation-only", "--concurrency", "7"])
    except SystemExit as error:
        return error.code != 0
    return False


# =============================================================================
# GROUP: the total adapter, null E_primary, and the R3 attestation.
# =============================================================================


def _synthetic_evaluation(e_value: float | None = 0.4) -> dict:
    worlds = [("w0", "validation", "c"), ("w1", "train", "o")]
    groups = []
    for arm in M.WAVE1_ARMS:
        for seed in W.SEEDS:
            for stage, rungs in ((W.STAGE_INITIAL, [32]), (W.STAGE_FINAL, list(M.BUDGETS))):
                for rung in rungs:
                    groups.append(
                        {
                            "arm": arm,
                            "seed": str(seed),
                            "rung": str(rung),
                            "stage": stage,
                            "worlds": [
                                {"world_public_id": world, W.EVALUATOR_E_KEY: e_value}
                                for world, _split, _family in worlds
                            ],
                        }
                    )
    diagnostics = [
        {
            "arm": arm,
            "seed": str(seed),
            "world_public_id": world,
            "outer_split": split,
            "family": family,
            "status": "learned_with_generalization",
            "L_initial": 1.0,
            "L_final": 0.2,
            "E_fit_final": 0.1,
            "E_query_final": 0.3,
        }
        for arm in M.WAVE1_ARMS
        for seed in W.SEEDS
        for world, split, family in worlds
    ]
    return {"version": "test", "groups": groups, "startup_diagnostics": diagnostics,
            "n_unknown_record_ids": 0}


def group_adapter() -> None:
    integrity = {"accounting_valid": True, "audit_passed": True, "timing_ok": True}
    table, gaps = W.build_gate_table(_synthetic_evaluation(), "L", integrity)
    check(
        "adapter: with a complete evaluator report the adapter reports NO gaps and one "
        "case per world x seed x arm",
        not gaps and len(table["cases"]) == 2 * len(W.SEEDS) * len(M.WAVE1_ARMS),
        f"{len(table['cases'])} cases, {len(gaps)} gaps",
    )
    check(
        "adapter: every case carries all five registered rungs plus the initial reference, "
        "each read from a NAMED evaluator field",
        all(
            sorted(case["E"]) == sorted(M.BUDGETS) and case["E_initial"] is not None
            for case in table["cases"]
        ),
    )
    check(
        "adapter: the split and family come from the evaluator, never from the trainer -- "
        "a train world stays labelled train",
        {case["outer_split"] for case in table["cases"]} == {"train", "validation"},
    )

    # A null E_primary is a MISSING REQUIRED RESULT, not a number.
    table_null, gaps_null = W.build_gate_table(_synthetic_evaluation(None), "L", integrity)
    check(
        "adapter: a null E_primary (short horizon or short panel 2) becomes a missing "
        "required result -- recorded as a gap, never coerced to a number and never "
        "quietly dropped from a median's denominator",
        gaps_null
        and any("is null" in gap for gap in gaps_null)
        and all(
            ("is null" in gap or "no final-stage query E" in gap or "no initial-stage query E" in gap
             or "no query E at rungs" in gap)
            for gap in gaps_null
        )
        and all(case["E"] == {} and case["E_initial"] is None for case in table_null["cases"]),
        f"{len(gaps_null)} gaps",
    )
    verdict_null = GATE.evaluate_tier(
        {**table_null, "integrity": {**table_null["integrity"], "complete_wave_valid": True}}
    )
    check(
        "adapter: the calculator turns those null cells into "
        "`calibration-invalid/missing-required-result`, which cannot escalate to tier H",
        verdict_null["verdict"] == "calibration-invalid/missing-required-result",
        verdict_null["verdict"],
    )

    # Missing evaluator fields must surface, not be defaulted.
    broken = copy.deepcopy(_synthetic_evaluation())
    del broken["startup_diagnostics"][0]["L_final"]
    broken["groups"][0]["worlds"][0].pop(W.EVALUATOR_E_KEY)
    try:
        _table, gaps_broken = W.build_gate_table(broken, "L", integrity)
        raised = ""
    except KeyError as error:
        gaps_broken = []
        raised = str(error)
    check(
        "adapter: a field the evaluator did not emit is a recorded gap or a hard error -- "
        "never a default, a guess or a back-filled value",
        bool(gaps_broken) or bool(raised),
        (gaps_broken[:2] if gaps_broken else raised)[:90].__str__(),
    )

    # Ruling R3 attestation.
    world_ids = ["w0", "w1"]
    complete = W.complete_wave_check(table, world_ids, list(W.SEEDS))
    check(
        "R3: the driver attests the COMPLETE wave over train AND validation jobs, and "
        "counts every required cell",
        complete["complete"]
        and complete["required_cells"] == 2 * len(W.SEEDS) * len(M.WAVE1_ARMS)
        and complete["present_cells"] == complete["required_cells"],
        f"{complete['present_cells']}/{complete['required_cells']}",
    )
    missing_one = copy.deepcopy(table)
    missing_one["cases"] = missing_one["cases"][1:]
    check(
        "R3: one missing required job makes the attestation false",
        not W.complete_wave_check(missing_one, world_ids, list(W.SEEDS))["complete"],
    )
    check(
        "R3: the calculator REFUSES to certify an escalation when the attestation is "
        "absent, so the field is required and an absent one is not treated as true",
        GATE.complete_wave_check({**table, "integrity": {}})["blocks_escalation"] is True
        and GATE.complete_wave_check(
            {**table, "integrity": {**table["integrity"], "complete_wave_valid": True}}
        )["blocks_escalation"]
        is False,
    )


# =============================================================================
# GROUP: the whole driver, end to end on the fixture.
# =============================================================================


def group_end_to_end() -> None:
    temporary = Path(tempfile.mkdtemp(prefix="ct20-wave1-"))
    try:
        out = temporary / "run"
        verdict = W.run_wave(
            data_root=FIXTURE,
            out_root=out,
            mode="fixture",
            concurrency=W.CONCURRENCY_LIMIT,
            preflight_seconds=0.6,
            resume=False,
        )
        block = verdict["tiers"]["L"]

        check(
            "driver: the launch preflight ran on the real machine, charged its own elapsed "
            "seconds to the wave and projected only the REMAINING schedule",
            block["preflight"]["fixture_seconds_charged"] > 0.0
            and verdict["preflight_seconds_charged"] >= block["preflight"]["fixture_seconds_charged"]
            and block["preflight"]["remaining_tiers"] == ["L", "H"]
            and block["preflight"]["timing_margin"] == 1.5
            and block["preflight"]["scoring_reserve_seconds"] == 300.0
            and block["preflight"]["soft_compute_stop_seconds"] == 1200.0
            and block["preflight"]["hard_deadline_seconds"] == 1500.0,
            f"charged {verdict['preflight_seconds_charged']:.1f}s",
        )
        check(
            "driver: every fitting shard completed through the models CLI, at most six at "
            "a time",
            block["all_shards_ok"] and block["n_shards"] <= W.CONCURRENCY_LIMIT,
            f"{block['n_shards']} shards",
        )
        check(
            "driver: the fits went through the boundary-checked SCHEMA.md public path -- "
            "the rung checkpoints and prediction files exist for every cell",
            all(
                M.predictions_path(out / "fits", arm, world_id, seed, "L").exists()
                and all(
                    M.checkpoint_path(out / "fits", arm, world_id, seed, budget, "L").exists()
                    for budget in M.BUDGETS
                )
                for arm in M.WAVE1_ARMS
                for world_id in verdict["world_public_ids"]
                for seed in verdict["seeds"]
            ),
        )
        # The audit-set size is a property of the world as PUBLISHED, not a constant:
        # each world ships its own audit_keys.json, and the fixture worlds are small.
        # Derive it per world so the check cannot drift from the data.
        expected_rows = 0
        for world_id in verdict["world_public_ids"]:
            n_audit = len(
                json.loads(
                    (FIXTURE / "public" / world_id / "audit_keys.json").read_text(
                        encoding="utf-8"
                    )
                )
            )
            expected_rows += (
                len(M.WAVE1_ARMS)
                * len(verdict["seeds"])
                * (96 * (1 + len(M.BUDGETS)) + 2 * n_audit)
            )
        check(
            "driver: it sealed the initial checkpoint's panel, every rung's panel (96 "
            "targets each, opaque record IDs) and both audit sets, with no gaps",
            not block["prediction_gaps"]
            and abs(block["n_prediction_rows"] - expected_rows) <= 2 * 6 * 2,
            f"{block['n_prediction_rows']} rows vs about {expected_rows}",
        )
        check(
            "driver: the evaluator recognised EVERY record ID, so the canonical audit keys "
            "and the opaque query IDs both join (the retired spelling would not)",
            block["n_unknown_record_ids"] == 0,
            str(block["n_unknown_record_ids"]),
        )
        check(
            "driver: the evaluator ran as a SEPARATE PROCESS -- the driver never imported "
            "the simulator into the trainer's own interpreter",
            "fable_concepttoy20_sim" not in sys.modules,
        )
        check(
            "driver: the executed per-rung cross-arm rule was checked for every world x "
            "seed and passed, with the gap reported",
            block["cross_arm"]["accounting_valid"]
            and block["cross_arm"]["worst_relative_gap"] <= GATE.CROSS_ARM_MAX_RELATIVE_GAP,
            f"worst gap {block['cross_arm']['worst_relative_gap']:.6f}",
        )
        check(
            "driver: unused reservations are reported SEPARATELY from executed operations, "
            "with the words that say they are not consumed work",
            "not consumed work" in block["unused_reservations"]["note"]
            and block["unused_reservations"]["unused_ops_by_arm_by_rung"],
        )
        check(
            "driver: the R3 complete-wave attestation was computed and handed to the "
            "calculator, which then does not block on an unverified outer requirement",
            block["complete_wave"]["complete"]
            and block["complete_wave_calculator_view"]["attestation"] is True
            and block["complete_wave_calculator_view"]["blocks_escalation"] is False,
        )
        check(
            "driver: the trainer's `pending_evaluator_E` labels were finalised by the "
            "evaluator, and the independent implementation agrees on every case",
            block["startup"]["n_labels"] == 12
            and not block["startup"]["still_pending"]
            and block["startup"]["agree"],
            f"{len(block['startup']['spelling_reconciliations'])} spelling reconciliations",
        )
        check(
            "driver: the one label difference between simulator and calculator is a named "
            "SPELLING reconciliation against the preregistration's own wording, not a "
            "silent equality -- and it is reported",
            set(block["startup"]["label_aliases_applied"]) == {"learned_failed_to_transfer"},
            str(block["startup"]["label_aliases_applied"]),
        )
        check(
            "driver: on the fixture the verdict is "
            "`calibration-invalid/missing-required-result`, exactly as the auditor found, "
            "because a fixture carries no validation rows",
            block["gate"]["verdict"] == "calibration-invalid/missing-required-result"
            and verdict["two_tier"]["final_verdict"]
            == "calibration-invalid/missing-required-result",
            block["gate"]["verdict"],
        )
        check(
            "driver: tier H was NOT run -- that verdict does not escalate, and H is "
            "permitted only on `awaiting-tier-H`",
            "H" not in verdict["tiers"] and verdict["two_tier"].get("tier_H") is None,
        )
        report = (out / "report.txt").read_text(encoding="utf-8")
        check(
            "driver: the written report says " + W.COST_PHRASE + " and never says "
            + W.FORBIDDEN_COST_PHRASE,
            W.COST_PHRASE in report and W.FORBIDDEN_COST_PHRASE not in report,
        )
        saved = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
        check(
            "driver: the verdict JSON stamps the source, both rulings, the schema and the "
            "data manifest, and records the isolation proof",
            saved["hashes"]["models_source_sha256"] == M.source_hash()
            and saved["hashes"]["rulings_2_sha256"]
            and saved["hashes"]["data_manifest_sha256"]
            and saved["isolation"]["passes"],
        )
        table = json.loads((out / "tierL" / "gate_table.json").read_text(encoding="utf-8"))
        check(
            "driver: the submitted table carries all four integrity attestations, "
            "`complete_wave_valid` among them",
            {"accounting_valid", "audit_passed", "timing_ok", "complete_wave_valid"}
            == set(table["integrity"]),
            str(sorted(table["integrity"])),
        )
        check(
            "driver: the table carries no truth, no noise-free response and no V -- only "
            "evaluator-reported error summaries the gate is entitled to see",
            not any(
                key in case
                for case in table["cases"]
                for key in ("noise_free_response", "truth", "V", "prediction")
            ),
        )

        # Refusing to overwrite, and resuming instead.
        refused = ""
        try:
            W.run_wave(FIXTURE, out, "fixture", W.CONCURRENCY_LIMIT, 0.6, resume=False)
        except FileExistsError as error:
            refused = str(error)
        check(
            "driver: a completed wave is never overwritten; continuing it needs --resume",
            "never overwritten" in refused,
            refused[:70],
        )
        again = W.run_wave(FIXTURE, out, "fixture", W.CONCURRENCY_LIMIT, 0.6, resume=True)
        check(
            "driver: resuming re-uses the sha-verified checkpoints already on disk and "
            "reaches the same verdict",
            again["two_tier"]["final_verdict"] == verdict["two_tier"]["final_verdict"]
            and again["tiers"]["L"]["complete_wave"]["complete"],
            again["two_tier"]["final_verdict"],
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


# =============================================================================
# GROUP: the registered data is prepared but untouched.
# =============================================================================


def group_registered_untouched() -> None:
    check(
        "registered: calibration-v1.1 is present with its twelve worlds, six train and "
        "six validation, so the wave has somewhere to run (no array is opened here)",
        CALIBRATION.is_dir()
        and len([e for e in (CALIBRATION / "public").iterdir() if e.is_dir()]) == 12,
    )
    worlds = W.load_public_worlds(CALIBRATION / "public")
    splits = sorted(str(row["outer_split"]) for row in worlds)
    check(
        "registered: the public world list gives the split (public) and NOT the family "
        "(evaluator-only), and the split is six/six",
        splits.count("train") == 6
        and splits.count("validation") == 6
        and not any("family" in row for row in worlds),
    )
    check(
        "registered: this test suite has produced no wave-1 output for the registered "
        "data -- the coordinator launches that run",
        not (ARTIFACTS / W.WAVE_DIR_NAME / "registered" / "verdict.json").exists(),
    )


def main() -> int:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    group_isolation()
    group_plan()
    group_adapter()
    group_end_to_end()
    group_registered_untouched()
    total = PASSED + len(FAILED)
    if FAILED:
        print(f"\n{len(FAILED)} of {total} CHECKS FAILED")
        for name in FAILED:
            print(f"  - {name}")
        return 1
    print(f"\nALL {total} CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
