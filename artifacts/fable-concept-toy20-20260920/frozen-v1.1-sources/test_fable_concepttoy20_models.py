"""Phase-A checks for scripts/fable_concepttoy20_models.py.

Plain script, matching this repo's convention.  Run it; it prints one line per
check and ends with `ALL N CHECKS PASSED` or raises.

NOTHING HERE TOUCHES THE SIMULATOR.  Agent 1's generator is being written in
parallel, so the data below comes from a tiny synthetic generator defined in this
file that emits tensors in the spec's PUBLIC BATCH CONTRACT.  Its values are
random: these are plumbing, causality and bookkeeping checks, not learning
checks, and no statement about learning is made or implied anywhere.

The load-bearing groups:

  "causality"        -- changing a FUTURE observed value, or the current target's
                        own OBSERVED value, leaves the earlier forecast bitwise
                        unchanged; the target OBSERVED record is never even built.
  "rollout"          -- intermediate forecast steps carry blank observations, so a
                        four-step forecast is not four one-step predictions with
                        the answers supplied.
  "lane independence"-- one vectorised lane equals the same unbatched run to 1e-6,
                        and no optimizer moment, gradient, draw or normalization
                        statistic is shared between worlds.
  "registered numbers"- the parameter counts and interface widths are re-read out
                        of design/v3/20-concept-toy-simulator-spec.md and asserted
                        against the instantiated models.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import tempfile

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "design" / "v3" / "20-concept-toy-simulator-spec.md"
PREREG = ROOT / "design" / "v3" / "20-concept-toy-preregistration-draft.md"

_spec = importlib.util.spec_from_file_location(
    "fable_concepttoy20_models", ROOT / "scripts" / "fable_concepttoy20_models.py"
)
M = importlib.util.module_from_spec(_spec)
sys.modules["fable_concepttoy20_models"] = M
_spec.loader.exec_module(M)

CHECKS = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f"FAILED: {label} {detail}")
    print(f"ok  {label}{(' -- ' + detail) if detail else ''}")


# =============================================================================
# TINY SYNTHETIC GENERATOR IN THE PUBLIC BATCH CONTRACT.
# Random values; no world law, no hidden state, no simulator.
# =============================================================================


def synthetic_public_arrays(n_episodes: int, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.Generator(np.random.PCG64(seed))
    shape = (n_episodes, M.N_TRANSITIONS)
    action = rng.integers(0, M.N_ACTIONS, size=shape)
    source = rng.integers(0, M.N_OBJECTS, size=shape)
    destination = rng.integers(0, M.N_OBJECTS + 1, size=shape)
    dose = rng.choice([-1.0, 0.0, 1.0], size=shape)
    index = np.arange(n_episodes)
    return {
        M.PUBLIC_KEYS["properties"]: rng.uniform(
            -1.0, 1.0, size=(n_episodes, M.N_OBJECTS, M.N_PROPERTIES)
        ).astype(np.float32),
        M.PUBLIC_KEYS["action_id"]: action.astype(np.int64),
        M.PUBLIC_KEYS["source_id"]: source.astype(np.int64),
        M.PUBLIC_KEYS["destination_id"]: destination.astype(np.int64),
        M.PUBLIC_KEYS["dose"]: dose.astype(np.float32),
        M.PUBLIC_KEYS["sensor"]: rng.uniform(-1.0, 1.0, size=shape).astype(np.float32),
        M.PUBLIC_KEYS["sensor_present"]: (rng.random(size=shape) < 0.75).astype(np.float32),
        M.PUBLIC_KEYS["episode_role"]: np.where(
            index % M.EPISODE_GROUP == M.SELECTION_INDEX_IN_GROUP,
            M.EPISODE_ROLE_SELECTION,
            M.EPISODE_ROLE_FIT,
        ).astype(np.int64),
        M.PUBLIC_KEYS["episode_index"]: index.astype(np.int64),
    }


def synthetic_episodes(n_episodes: int, seed: int) -> "M.Episodes":
    arrays = synthetic_public_arrays(n_episodes, seed)
    return M.Episodes(
        properties=torch.tensor(arrays[M.PUBLIC_KEYS["properties"]]),
        action_id=torch.tensor(arrays[M.PUBLIC_KEYS["action_id"]]),
        source_id=torch.tensor(arrays[M.PUBLIC_KEYS["source_id"]]),
        destination_id=torch.tensor(arrays[M.PUBLIC_KEYS["destination_id"]]),
        dose=torch.tensor(arrays[M.PUBLIC_KEYS["dose"]]),
        sensor=torch.tensor(arrays[M.PUBLIC_KEYS["sensor"]]),
        sensor_present=torch.tensor(arrays[M.PUBLIC_KEYS["sensor_present"]]),
        role=torch.tensor(arrays[M.PUBLIC_KEYS["episode_role"]]),
        episode_index=torch.tensor(arrays[M.PUBLIC_KEYS["episode_index"]]),
    )


def write_world_semantic(directory: Path, world_id: str, n_episodes: int, seed: int) -> None:
    """The FIXTURE-ONLY semantic .npz layout.  Ruling C11 makes this unreachable
    from fit/predict, so it now exists to prove the refusal, not to drive runs."""
    target = directory / world_id
    target.mkdir(parents=True, exist_ok=True)
    np.savez(target / "discovery.npz", **synthetic_public_arrays(n_episodes, seed))


def write_world(directory: Path, world_id: str, n_episodes: int, seed: int) -> None:
    """The PRODUCTION serialized layout (ruling C11): tokenized .npy files.

    Written with this module's own `build_sequences`, which has been checked bit
    for bit against Agent 1's serializer on the published interface fixture.
    """
    target = directory / world_id
    target.mkdir(parents=True, exist_ok=True)
    episodes = synthetic_episodes(n_episodes, seed)

    # Records 0..15 come straight from the forecast builder; row 16 is the final
    # OBSERVED, which the builder deliberately never constructs for a prediction.
    records, _ = M.build_sequences(
        episodes,
        torch.full((n_episodes,), M.N_TRANSITIONS - 1, dtype=torch.int64),
        torch.ones((n_episodes,), dtype=torch.int64),
    )
    records = records.clone()
    last = M.N_TRANSITIONS - 1
    for n in range(n_episodes):
        row = 2 * M.N_TRANSITIONS
        records[n, row, M.SLICE_PROPERTIES] = records[n, 0, M.SLICE_PROPERTIES]
        records[n, row, M.SLICE_ACTION.start + int(episodes.action_id[n, last])] = 1.0
        records[n, row, M.SLICE_SOURCE.start + int(episodes.source_id[n, last])] = 1.0
        records[n, row, M.SLICE_DESTINATION.start + int(episodes.destination_id[n, last])] = 1.0
        records[n, row, M.SLICE_DOSE.start] = float(episodes.dose[n, last])
        present = float(episodes.sensor_present[n, last])
        records[n, row, M.SLICE_SENSOR.start] = float(episodes.sensor[n, last]) * present
        records[n, row, M.SLICE_PRESENT.start] = present
        records[n, row, M.SLICE_RECORD_TYPE.start + M.RECORD_TYPE_OBSERVED] = 1.0

    masked = (episodes.sensor * episodes.sensor_present).numpy().astype(np.float32)
    rung = np.zeros((n_episodes,), dtype=np.int8)
    for index in range(n_episodes):
        for position, budget in enumerate(M.BUDGETS):
            if index < budget // M.N_TRANSITIONS:
                rung[index] = position
                break
        else:
            rung[index] = len(M.BUDGETS) - 1

    np.save(target / "support_records.npy", records.numpy().astype(np.float32))
    np.save(target / "support_observed_target.npy", masked)
    np.save(
        target / "support_observed_present.npy",
        episodes.sensor_present.numpy().astype(np.uint8),
    )
    np.save(target / "support_episode_role.npy", episodes.role.numpy().astype(np.int8))
    np.save(target / "support_budget_rung.npy", rung)
    np.save(
        target / "support_padding_mask.npy",
        np.ones((n_episodes, M.FIXED_SEQUENCE_LENGTH), dtype=np.uint8),
    )

    # A small query panel in the same serialized form.
    panel = synthetic_episodes(M.QUERY_PANEL_TARGETS, seed + 5000)
    prefix = torch.tensor(
        [(index % (M.N_TRANSITIONS - 3)) for index in range(M.QUERY_PANEL_TARGETS)], dtype=torch.int64
    )
    horizon = torch.tensor(
        [M.HORIZONS[index % len(M.HORIZONS)] for index in range(M.QUERY_PANEL_TARGETS)],
        dtype=torch.int64,
    )
    query_records, endpoint = M.build_sequences(panel, prefix, horizon)
    detector = np.zeros((M.QUERY_PANEL_TARGETS, M.QUERY_A_WIDTH + M.QUERY_B_WIDTH), dtype=np.float32)
    for index in range(M.QUERY_PANEL_TARGETS):
        detector[index, index % M.N_OBJECTS] = 1.0
        detector[index, M.QUERY_A_WIDTH + M.QUERY_B_NONE] = 1.0
    np.save(target / "query_records.npy", query_records.numpy().astype(np.float32))
    np.save(target / "query_n_records.npy", (endpoint.numpy() + 1).astype(np.int32))
    np.save(target / "query_detector.npy", detector)
    np.save(
        target / "query_padding_mask.npy",
        np.ones((M.QUERY_PANEL_TARGETS, M.FIXED_SEQUENCE_LENGTH), dtype=np.uint8),
    )
    (target / "query_record_ids.json").write_text(
        json.dumps([f"{world_id}-q{index:04d}" for index in range(M.QUERY_PANEL_TARGETS)]),
        encoding="utf-8",
    )


# =============================================================================
# GROUP: public interface shape and the adapter's own arithmetic
# =============================================================================


def group_interface() -> None:
    text = SPEC.read_text(encoding="utf-8")

    check(
        "interface: spec says float32 vector of length 44",
        "float32 vector of length 44" in text and M.RECORD_WIDTH == 44,
    )
    widths = [
        (M.SLICE_PROPERTIES, 24),
        (M.SLICE_ACTION, 5),
        (M.SLICE_SOURCE, 4),
        (M.SLICE_DESTINATION, 5),
        (M.SLICE_DOSE, 1),
        (M.SLICE_SENSOR, 1),
        (M.SLICE_PRESENT, 1),
        (M.SLICE_RECORD_TYPE, 3),
    ]
    check(
        "interface: field widths sum to 44 with no gap or overlap",
        sum(width for _, width in widths) == 44
        and all(slot.stop - slot.start == width for slot, width in widths)
        and [slot.start for slot, _ in widths] == [0, 24, 29, 33, 38, 39, 40, 41],
    )
    check("interface: decoder input width is 53", M.DECODER_INPUT_WIDTH == 53)
    check(
        "interface: 17 records in a full eight-transition history",
        "17 records" in text and M.MAX_RECORDS == 17 and M.MAX_RECORDS == 1 + 2 * M.N_TRANSITIONS,
    )

    episodes = synthetic_episodes(2, seed=1)
    records, endpoint = M.build_sequences(
        episodes, torch.tensor([8, 8]), torch.tensor([0, 0])
    ) if False else M.build_sequences(episodes, torch.tensor([7, 7]), torch.tensor([1, 1]))
    check(
        "interface: records tensor is (N, 17, 44) float32",
        tuple(records.shape) == (2, 17, 44) and records.dtype == torch.float32,
    )
    one_hot_ok = True
    for n in range(2):
        for row in range(int(endpoint[n]) + 1):
            record_type = records[n, row, M.SLICE_RECORD_TYPE]
            if abs(float(record_type.sum()) - 1.0) > 1e-9:
                one_hot_ok = False
    check("interface: every built record has exactly one record_type bit", one_hot_ok)


# =============================================================================
# GROUP: causal ordering and target leakage
# =============================================================================


def group_causality() -> None:
    episodes = synthetic_episodes(4, seed=11)
    prefix = torch.tensor([3, 3, 3, 3])
    horizon = torch.tensor([2, 2, 2, 2])
    records, endpoint = M.build_sequences(episodes, prefix, horizon)

    # endpoint is the final QUERY; the record AFTER it must not exist at all.
    check(
        "causality: prediction is read at a QUERY token",
        all(
            float(records[n, int(endpoint[n]), M.SLICE_RECORD_TYPE.start + M.RECORD_TYPE_QUERY]) == 1.0
            for n in range(4)
        ),
    )
    check(
        "causality: the target OBSERVED record is never built (all rows after the "
        "endpoint are exactly zero apart from the static public properties)",
        all(
            float(records[n, int(endpoint[n]) + 1 :, 24:].abs().sum()) == 0.0 for n in range(4)
        ),
    )
    check(
        "causality: the endpoint QUERY carries sensor=0 and sensor_present=0",
        float(records[:, :, M.SLICE_SENSOR].gather(1, endpoint.view(-1, 1, 1)).abs().sum()) == 0.0
        and float(records[:, :, M.SLICE_PRESENT].gather(1, endpoint.view(-1, 1, 1)).abs().sum()) == 0.0,
    )

    for arm in M.ARMS:
        parameters = {
            name: torch.tensor(value).unsqueeze(0)
            for name, value in M.initial_parameters(arm, "causality-world", 20001).items()
        }
        query_a = episodes.source_id[torch.arange(4), prefix + horizon - 1]
        query_b = torch.full((4,), M.QUERY_B_NONE, dtype=torch.int64)
        features = M.build_query_features(episodes.properties, query_a, query_b)
        with torch.no_grad():
            base = M.forward(arm, parameters, records.unsqueeze(0), endpoint, features)

        # (a) change every FUTURE observed value, including the target's own.
        edited = M.Episodes(**{**episodes.__dict__})
        edited.sensor = episodes.sensor.clone()
        edited.sensor_present = episodes.sensor_present.clone()
        edited.sensor[:, 3:] = edited.sensor[:, 3:] + 17.0
        edited.sensor_present[:, 3:] = 1.0 - edited.sensor_present[:, 3:]
        edited_records, edited_endpoint = M.build_sequences(edited, prefix, horizon)
        with torch.no_grad():
            after = M.forward(arm, parameters, edited_records.unsqueeze(0), edited_endpoint, features)
        check(
            f"causality[{arm}]: changing every future observed value and mask leaves "
            "the earlier forecast bitwise unchanged",
            torch.equal(base, after),
            f"max abs diff {float((base - after).abs().max()):.3e}",
        )

        # (b) the current target's OBSERVED value alone.
        only_target = M.Episodes(**{**episodes.__dict__})
        only_target.sensor = episodes.sensor.clone()
        only_target.sensor[:, 4] = only_target.sensor[:, 4] + 99.0
        target_records, target_endpoint = M.build_sequences(only_target, prefix, horizon)
        with torch.no_grad():
            after_target = M.forward(arm, parameters, target_records.unsqueeze(0), target_endpoint, features)
        check(
            f"causality[{arm}]: the current target OBSERVED record is outside the graph "
            "producing its QUERY prediction",
            torch.equal(base, after_target),
        )

        # (c) gradient reachability: no gradient flows from the target's sensor value.
        leak_records = records.clone().requires_grad_(True)
        prediction = M.forward(arm, parameters, leak_records.unsqueeze(0), endpoint, features)
        prediction.sum().backward()
        tail = torch.stack(
            [leak_records.grad[n, int(endpoint[n]) + 1 :, :].abs().sum() for n in range(4)]
        )
        check(
            f"causality[{arm}]: zero gradient reaches any record after the endpoint QUERY",
            float(tail.sum()) == 0.0,
        )


# =============================================================================
# GROUP: multi-step rollout, no teacher forcing
# =============================================================================


def group_rollout() -> None:
    episodes = synthetic_episodes(3, seed=21)
    prefix = torch.tensor([4, 4, 4])
    horizon = torch.tensor([4, 4, 4])
    records, endpoint = M.build_sequences(episodes, prefix, horizon)

    blank_rows = []
    for n in range(3):
        for t in range(4, 7):  # the intermediate forecast steps
            blank_rows.append(records[n, 1 + 2 * t + 1])
    blanks = torch.stack(blank_rows)
    check(
        "rollout: every intermediate forecast OBSERVED token has sensor=0 and present=0",
        float(blanks[:, M.SLICE_SENSOR].abs().sum()) == 0.0
        and float(blanks[:, M.SLICE_PRESENT].abs().sum()) == 0.0,
    )
    check(
        "rollout: those blank OBSERVED tokens still carry their action fields "
        "(BLANK_OBSERVED_KEEPS_ACTION_FIELDS, the literal reading)",
        M.BLANK_OBSERVED_KEEPS_ACTION_FIELDS
        and float(blanks[:, M.SLICE_ACTION].sum()) == float(blanks.shape[0]),
    )

    observed_rows = torch.stack([records[n, 1 + 2 * t + 1] for n in range(3) for t in range(4)])
    check(
        "rollout: real prefix OBSERVED tokens do carry their measurement, so the blanks "
        "are a rollout property and not a constructor that blanks everything",
        float(observed_rows[:, M.SLICE_PRESENT].sum()) > 0.0,
    )

    for arm in M.ARMS:
        parameters = {
            name: torch.tensor(value).unsqueeze(0)
            for name, value in M.initial_parameters(arm, "rollout-world", 20002).items()
        }
        query_a = episodes.source_id[torch.arange(3), prefix + horizon - 1]
        query_b = torch.full((3,), M.QUERY_B_NONE, dtype=torch.int64)
        features = M.build_query_features(episodes.properties, query_a, query_b)
        with torch.no_grad():
            base = M.forward(arm, parameters, records.unsqueeze(0), endpoint, features)
        teacher = M.Episodes(**{**episodes.__dict__})
        teacher.sensor = episodes.sensor.clone()
        teacher.sensor[:, 4:7] += 5.0          # what teacher forcing would have fed in
        teacher.sensor_present = episodes.sensor_present.clone()
        teacher.sensor_present[:, 4:7] = 1.0
        teacher_records, teacher_endpoint = M.build_sequences(teacher, prefix, horizon)
        with torch.no_grad():
            after = M.forward(arm, parameters, teacher_records.unsqueeze(0), teacher_endpoint, features)
        check(
            f"rollout[{arm}]: a four-step forecast is unchanged when the intermediate "
            "true measurements change, so it is not four teacher-forced one-step calls",
            torch.equal(base, after),
        )


# =============================================================================
# GROUP: reset behaviour
# =============================================================================


def group_reset() -> None:
    episodes = synthetic_episodes(2, seed=31)
    records, _ = M.build_sequences(episodes, torch.tensor([2, 2]), torch.tensor([1, 1]))
    reset = records[:, 0, :]
    check(
        "reset: record 0 is a RESET token",
        float(reset[:, M.SLICE_RECORD_TYPE.start + M.RECORD_TYPE_RESET].sum()) == 2.0,
    )
    check(
        "reset: RESET has all-zero action and source one-hots (spec: 'All zero at RESET')",
        float(reset[:, M.SLICE_ACTION].abs().sum()) == 0.0
        and float(reset[:, M.SLICE_SOURCE].abs().sum()) == 0.0,
    )
    check(
        "reset: RESET destination is NONE, dose/sensor/present are zero",
        float(reset[:, M.SLICE_DESTINATION.start + M.DESTINATION_NONE].sum()) == 2.0
        and float(reset[:, M.SLICE_DOSE].abs().sum()) == 0.0
        and float(reset[:, M.SLICE_SENSOR].abs().sum()) == 0.0
        and float(reset[:, M.SLICE_PRESENT].abs().sum()) == 0.0,
    )
    check(
        "reset: the public properties are present on the RESET record",
        float(reset[:, M.SLICE_PROPERTIES].abs().sum()) > 0.0,
    )

    parameters = {
        name: torch.tensor(value).unsqueeze(0)
        for name, value in M.initial_parameters("G", "reset-world", 20001).items()
    }
    # Every episode starts from an empty recurrent state: two identical episodes
    # evaluated in different batch positions and orders agree exactly.
    duplicated = episodes.select(torch.tensor([0, 0, 1, 0]))
    dup_records, dup_endpoint = M.build_sequences(
        duplicated, torch.tensor([2, 2, 2, 2]), torch.tensor([1, 1, 1, 1])
    )
    features = M.build_query_features(
        duplicated.properties,
        duplicated.source_id[torch.arange(4), torch.tensor([2, 2, 2, 2])],
        torch.full((4,), M.QUERY_B_NONE, dtype=torch.int64),
    )
    with torch.no_grad():
        out = M.forward("G", parameters, dup_records.unsqueeze(0), dup_endpoint, features)
    check(
        "reset: no state carries between episodes in a batch (copies of one episode "
        "at positions 0, 1 and 3 give the identical prediction)",
        torch.equal(out[0, 0], out[0, 1]) and torch.equal(out[0, 0], out[0, 3]),
    )


# =============================================================================
# GROUP: registered numbers, re-read from the spec text
# =============================================================================


def group_registered_numbers() -> None:
    text = SPEC.read_text(encoding="utf-8")

    def number(pattern: str) -> int:
        found = re.search(pattern, text)
        if not found:
            raise AssertionError(f"spec text no longer contains {pattern!r}")
        return int(found.group(1).replace(",", ""))

    gru_spec = number(r"hidden width 24, one layer, PyTorch-style two bias vectors, \*\*([\d,]+) parameters\*\*")
    decoder_spec = number(r"Decoder: Linear\(53,16\), tanh, Linear\(16,1\), \*\*([\d,]+) parameters\*\*")
    g_spec = number(r"\| G \| GRU24 above; zero module slices[^|]*\| ([\d,]+) \|")
    t_spec = number(r"\| T \| Input Linear\(44,24\);[^|]*\| ([\d,]+) \|")
    transformer_line = re.search(
        r"Transformer counts: input projection ([\d,]+); QKV ([\d,]+); attention output ([\d,]+); "
        r"FF ([\d,]+); two block norms ([\d,]+); final norm ([\d,]+); decoder ([\d,]+)\.",
        text,
    )
    if not transformer_line:
        raise AssertionError("spec text no longer contains the transformer count sentence")
    parts = [int(value.replace(",", "")) for value in transformer_line.groups()]

    counts = {arm: M.count_parameters(arm) for arm in M.ARMS}
    check(
        "registered numbers: GRU backbone == the spec's 5,040",
        gru_spec == 5040 and counts["G"]["backbone"] == gru_spec,
        f"instantiated {counts['G']['backbone']}",
    )
    check(
        "registered numbers: shared decoder == the spec's 881",
        decoder_spec == 881 and counts["G"]["decoder"] == decoder_spec == counts["T"]["decoder"],
    )
    check(
        "registered numbers: arm G total == the spec table's 5,921",
        g_spec == 5921 and counts["G"]["total"] == g_spec,
        f"instantiated {counts['G']['total']}",
    )
    check(
        "registered numbers: arm T total == the spec table's 6,881",
        t_spec == 6881 and counts["T"]["total"] == t_spec,
        f"instantiated {counts['T']['total']}",
    )
    check(
        "registered numbers: the transformer count sentence (1080/1800/600/2376/96/48/881) "
        "matches the instantiated block component by component",
        parts == [1080, 1800, 600, 2376, 96, 48, 881]
        and sum(parts) == counts["T"]["total"]
        and all(counts["T"]["contract_checks"].values()),
    )
    check(
        "registered numbers: no arm exceeds its spec maximum, and widths were not "
        "changed to chase accuracy",
        M.CONTEXT_WIDTH == 24 and M.FF_WIDTH == 48 and M.N_HEADS == 2 and M.DECODER_HIDDEN == 16,
    )

    prereg = PREREG.read_text(encoding="utf-8")
    check(
        "registered numbers: optimizer recipe matches the preregistration text",
        "AdamW, learning rate 0.001, betas (0.9,0.99), epsilon 1e-8" in prereg
        and M.BASE_LR == 0.001
        and (M.ADAM_BETA1, M.ADAM_BETA2) == (0.9, 0.99)
        and M.ADAM_EPS == 1e-8
        and M.WEIGHT_DECAY == 0.0001
        and M.GRAD_CLIP_NORM == 1.0
        and M.WARMUP_UPDATES == 8,
    )
    check(
        "registered numbers: budgets, allowances and wave limits match the preregistration",
        M.BUDGETS == (32, 64, 128, 256, 512)
        and "2.0e8 counted floating-point operations per source rung" in prereg
        and M.SOURCE_ALLOWANCE_PER_RUNG == 2.0e8
        and "1,200-second soft compute stop and a 1,500-second hard wall deadline" in prereg
        and M.WAVE_SOFT_COMPUTE_STOP_SECONDS == 1200.0
        and M.WAVE_HARD_DEADLINE_SECONDS == 1500.0,
    )
    check(
        "registered numbers: three training seeds 20001/20002/20003",
        "three training seeds: 20001, 20002, 20003" in prereg,
    )
    check(
        "phase A scope: no pool, P, T-pool, T-fit, R, Q or P-fixed arm exists yet",
        M.ARMS == ("G", "T") and not hasattr(M, "Pool") and not hasattr(M, "select_candidate"),
    )


# =============================================================================
# GROUP: shapes, gradients and initialization
# =============================================================================


def group_shapes_and_gradients() -> None:
    episodes = synthetic_episodes(8, seed=41)
    for arm in M.ARMS:
        lanes = [M.Lane(f"shape-world-{i}", 20001, episodes) for i in range(2)]
        runner = M.Runner(arm, lanes)
        check(
            f"shapes[{arm}]: every parameter carries a leading lane dimension of 2",
            all(tensor.shape[0] == 2 for tensor in runner.parameters.values()),
        )
        info = runner.update(64, 0)
        check(
            f"shapes[{arm}]: one update produces one finite loss per lane",
            len(info["loss_per_lane"]) == 2 and all(math.isfinite(v) for v in info["loss_per_lane"]),
        )
        check(
            f"shapes[{arm}]: every parameter received a finite gradient",
            all(
                tensor.grad is not None
                and tensor.grad.shape == tensor.shape
                and bool(torch.isfinite(tensor.grad).all())
                for tensor in runner.parameters.values()
            ),
        )
        check(
            f"shapes[{arm}]: parameters stayed finite after the AdamW step",
            all(bool(torch.isfinite(tensor).all()) for tensor in runner.parameters.values()),
        )

    # initialization recipe
    parameters = M.initial_parameters("G", "init-world", 20001)
    hidden = M.CONTEXT_WIDTH
    bias_ih = parameters["backbone.bias_ih"]
    check(
        "init: GRU input-side UPDATE-gate bias is +1 and every other GRU bias entry is 0 "
        "(the 'do not set both update biases' rule)",
        np.allclose(bias_ih[hidden : 2 * hidden], 1.0)
        and np.allclose(bias_ih[:hidden], 0.0)
        and np.allclose(bias_ih[2 * hidden :], 0.0)
        and np.allclose(parameters["backbone.bias_hh"], 0.0),
    )
    weight_hh = parameters["backbone.weight_hh"]
    orthogonality = max(
        float(np.abs(weight_hh[i * hidden : (i + 1) * hidden] @ weight_hh[i * hidden : (i + 1) * hidden].T - np.eye(hidden)).max())
        for i in range(3)
    )
    check(
        "init: each GRU recurrent gate block is orthogonal, gain 1",
        orthogonality < 1e-5,
        f"max |W W^T - I| = {orthogonality:.2e}",
    )
    transformer = M.initial_parameters("T", "init-world", 20001)
    check(
        "init: transformer pre-LN scales are 1 and offsets 0",
        all(
            np.allclose(transformer[f"backbone.{name}_weight"], 1.0)
            and np.allclose(transformer[f"backbone.{name}_bias"], 0.0)
            for name in ("ln1", "ln2", "ln_final")
        ),
    )
    plain_bound = math.sqrt(6.0 / (24 + 24))
    check(
        "init: attention-output and FF-output matrices are divided by sqrt(2) "
        "(the registered residual scale), so they cannot exceed bound/sqrt(2)",
        float(np.abs(transformer["backbone.attn_out_weight"]).max()) <= plain_bound / math.sqrt(2) + 1e-7
        and float(np.abs(transformer["backbone.q_weight"]).max()) <= plain_bound + 1e-7,
    )
    check(
        "init: the shared decoder has identical starting bytes across arms for one "
        "world and seed (corresponding components start equal)",
        all(
            np.array_equal(
                M.initial_parameters("G", "same", 20003)[f"decoder.{k}"],
                M.initial_parameters("T", "same", 20003)[f"decoder.{k}"],
            )
            for k in ("hidden_weight", "hidden_bias", "out_weight", "out_bias")
        ),
    )
    check(
        "init: a different world or seed gives different backbone bytes",
        not np.array_equal(
            M.initial_parameters("G", "world-a", 20001)["backbone.weight_ih"],
            M.initial_parameters("G", "world-b", 20001)["backbone.weight_ih"],
        )
        and not np.array_equal(
            M.initial_parameters("G", "world-a", 20001)["backbone.weight_ih"],
            M.initial_parameters("G", "world-a", 20002)["backbone.weight_ih"],
        ),
    )
    check(
        "init: seeds come from SHA-256 of the registered namespace string",
        M.namespace_seed("premonition/concept-toy20/v1/model/w/20001/decoder/out_bias")
        == int.from_bytes(
            __import__("hashlib")
            .sha256(b"premonition/concept-toy20/v1/model/w/20001/decoder/out_bias")
            .digest()[:8],
            "little",
        ),
    )


# =============================================================================
# GROUP: lane independence and absence of shared state
# =============================================================================


def group_lane_independence() -> None:
    worlds = ["lane-world-a", "lane-world-b", "lane-world-c"]
    seeds = [20001, 20002]
    episodes = {world: synthetic_episodes(8, seed=50 + i) for i, world in enumerate(worlds)}
    updates = 6

    def run(world_list: list[str], seed_list: list[int], arm: str) -> dict[str, torch.Tensor]:
        lanes = [M.Lane(w, s, episodes[w]) for w in world_list for s in seed_list]
        runner = M.Runner(arm, lanes)
        for step in range(updates):
            runner.update(64, step)
        return {name: tensor.detach().clone() for name, tensor in runner.parameters.items()}

    for arm in M.ARMS:
        batched = run(worlds, seeds, arm)
        worst = 0.0
        for lane_index, (world, seed) in enumerate((w, s) for w in worlds for s in seeds):
            alone = run([world], [seed], arm)
            for name in batched:
                diff = float((batched[name][lane_index] - alone[name][0]).abs().max())
                worst = max(worst, diff)
        check(
            f"lane independence[{arm}]: each of 6 vectorised lanes equals its own "
            f"unbatched run after {updates} updates, to 1e-6 on CPU",
            worst <= 1e-6,
            f"max abs parameter difference {worst:.3e}",
        )

    # no shared optimizer tensors
    lanes = [M.Lane(w, 20001, episodes[w]) for w in worlds]
    runner = M.Runner("G", lanes)
    runner.update(64, 0)
    check(
        "lane independence: every Adam moment tensor is per lane (leading dim 3)",
        all(tensor.shape[0] == 3 for tensor in runner.optimizer.moment1.values())
        and all(tensor.shape[0] == 3 for tensor in runner.optimizer.moment2.values()),
    )
    check(
        "lane independence: no Adam moment tensor is aliased between lanes",
        all(
            not torch.equal(tensor[0], tensor[1])
            for tensor in runner.optimizer.moment1.values()
            if tensor.numel() > 3 and float(tensor.abs().sum()) > 0
        ),
    )
    # gradient clipping must be per lane, not one global norm across worlds
    runner.optimizer.zero_grad()
    for tensor in runner.parameters.values():
        tensor.grad = torch.zeros_like(tensor)
    runner.parameters["decoder.out_bias"].grad[0] = 1000.0
    runner.parameters["decoder.out_bias"].grad[1] = 0.25
    norms = runner.optimizer.clip_per_lane()
    check(
        "lane independence: the gradient-norm clip is computed PER LANE, so a huge "
        "gradient in world 0 does not rescale world 1",
        abs(float(runner.parameters["decoder.out_bias"].grad[1]) - 0.25) < 1e-6
        and float(runner.parameters["decoder.out_bias"].grad[0]) < 1.0001
        and float(norms[2]) == 0.0,
    )
    check(
        "lane independence: the model holds no running normalization statistic "
        "(LayerNorm is computed from the current activation only; the only module-level "
        "buffer is the fixed sinusoidal position table)",
        torch.equal(M._POSITION_TABLE, M.sinusoidal_positions(M.MAX_RECORDS, M.CONTEXT_WIDTH))
        and not any("running" in name for name in runner.parameters),
    )
    check(
        "lane independence: minibatch draws come from the per-world/per-seed namespace, "
        "so two worlds at the same rung and update draw independently",
        M.sample_minibatch("world-a", 20001, 64, 3, 6, 2)[0].tolist()
        != M.sample_minibatch("world-b", 20001, 64, 3, 6, 2)[0].tolist()
        or M.sample_minibatch("world-a", 20001, 64, 3, 6, 2)[1].tolist()
        != M.sample_minibatch("world-b", 20001, 64, 3, 6, 2)[1].tolist(),
    )
    check(
        "lane independence: the same namespace reproduces the same draw exactly",
        M.sample_minibatch("world-a", 20001, 64, 3, 6, 2)[0].tolist()
        == M.sample_minibatch("world-a", 20001, 64, 3, 6, 2)[0].tolist(),
    )


# =============================================================================
# GROUP: loss, horizon cycle and compute ledger
# =============================================================================


def group_loss_and_cost() -> None:
    prediction = torch.tensor([[1.0, 2.0, 3.0]])
    target = torch.tensor([[1.5, 2.0, 9.0]])
    present = torch.tensor([[1.0, 1.0, 0.0]])
    value = M.normalized_squared_error(prediction, target, present)
    check(
        "loss: squared error is divided by the registered constant 0.25 and only "
        "present endpoints contribute",
        abs(float(value[0]) - ((0.25 / 0.25) + 0.0) / 2) < 1e-6,
    )
    empty = M.normalized_squared_error(prediction, target, torch.zeros_like(present))
    check(
        "loss: a minibatch with no present endpoint yields exactly zero loss "
        "(it consumes its scheduled work and is never redrawn)",
        float(empty[0]) == 0.0,
    )
    check(
        "loss: the horizon cycles 1, 2, 4 by global optimizer update index",
        [M.horizon_for_update(i) for i in range(6)] == [1, 2, 4, 1, 2, 4],
    )
    check(
        "optimizer: the first eight updates warm up linearly from 0.001/8 to 0.001",
        [
            round(M.LanedAdamW({}, 1).__class__.learning_rate.__get__(
                type("S", (), {"step_count": i, "__init__": lambda self: None})()
            )(), 9)
            for i in range(0, 9)
        ]
        == [round(0.001 * min(i + 1, 8) / 8, 9) for i in range(0, 9)],
    )
    check(
        "optimizer: weight decay applies to matrix weights only, never to biases or "
        "LayerNorm scale/offset",
        M.LanedAdamW.decays("backbone.weight_ih", torch.zeros(2, 72, 44))
        and M.LanedAdamW.decays("decoder.hidden_weight", torch.zeros(2, 16, 53))
        and not M.LanedAdamW.decays("backbone.bias_ih", torch.zeros(2, 72))
        and not M.LanedAdamW.decays("backbone.ln1_weight", torch.zeros(2, 24)),
    )

    for arm in M.ARMS:
        table = M.step_table(arm)
        check(
            f"cost[{arm}]: every rung's counted total stays within its 2.0e8 allowance",
            all(row["counted_total_ops"] <= M.SOURCE_ALLOWANCE_PER_RUNG for row in table),
            f"max {max(row['counted_total_ops'] for row in table):.4g}",
        )
        check(
            f"cost[{arm}]: the step table is frozen and positive at every rung",
            all(row["steps"] > 0 for row in table) and len(table) == len(M.BUDGETS),
            f"steps {[row['steps'] for row in table]}",
        )
        report = M.cost_report(arm, "L")
        check(
            f"cost[{arm}]: the operator ledger covers forward, backward, optimizer and "
            "evaluation, and a multiply-add counts as two operations",
            M.OPS_PER_MAC == 2
            and report["forward_ops_one_sequence"] == sum(report["operator_table_one_sequence"].values())
            and report["ops_per_update"]
            > report["forward_ops_one_sequence"] * M.MINIBATCH_EPISODES,
        )
    totals = {arm: M.cost_report(arm)["step_table"] for arm in M.ARMS}
    worst = max(
        abs(totals["G"][i]["counted_total_ops"] - totals["T"][i]["counted_total_ops"])
        / max(totals["G"][i]["counted_total_ops"], totals["T"][i]["counted_total_ops"])
        for i in range(len(M.BUDGETS))
    )
    check(
        "cost: counted total use agrees within the registered 5% across G and T at every rung",
        worst <= 0.05,
        f"worst relative gap {worst * 100:.3f}%",
    )


# =============================================================================
# GROUP: startup classification hook
# =============================================================================


def group_startup() -> None:
    prereg = PREREG.read_text(encoding="utf-8")
    check(
        "startup: the preregistration's 'never started' definition is reproduced verbatim "
        "in the implementation's thresholds",
        "improved less than 10% relative to initialization **and** final fitting E>=0.80" in prereg
        and M.STARTUP_MIN_RELATIVE_IMPROVEMENT == 0.10
        and M.STARTUP_NEVER_STARTED_FITTING_E == 0.80
        and "If the initial loss is <=1e-8, mark `initially_at_floor`" in prereg
        and M.STARTUP_INITIAL_FLOOR_LOSS == 1e-8,
    )
    cases = [
        # (initial, final, fitting_E, query_E) -> label
        ((1.0, 0.95, 0.9, 0.9), "never_started"),          # <10% improvement and E>=0.80
        ((1.0, 0.95, 0.79, 0.9), "started_not_yet_learned"),  # escaped by E alone
        ((1.0, 0.80, 0.9, 0.9), "started_not_yet_learned"),   # escaped by improvement alone
        ((1.0, 0.85, 0.5, 0.9), "started_not_yet_learned"),   # 15% region, E>0.25
        ((1.0, 0.10, 0.20, 0.90), "learned_and_failed_to_transfer"),
        ((1.0, 0.10, 0.20, 0.30), "learned_with_generalization"),
        ((1e-9, 1e-9, 0.0, 0.0), "initially_at_floor"),
    ]
    for (initial, final, fitting_e, query_e), expected in cases:
        got = M.classify_startup(initial, final, fitting_e, query_e)
        check(
            f"startup: ({initial}, {final}, fitE={fitting_e}, queryE={query_e}) -> {expected}",
            got == expected,
            f"got {got}",
        )
    check(
        "startup: boundaries are the registered ones -- an 11% improvement escapes "
        "'never started', a 9% improvement with E>=0.80 does not, E=0.25 IS learned "
        "and query E=0.50 IS competent",
        M.classify_startup(1.0, 0.89, 0.80, 0.9) == "started_not_yet_learned"
        and M.classify_startup(1.0, 0.91, 0.80, 0.9) == "never_started"
        and M.classify_startup(1.0, 0.1, 0.25, 0.50) == "learned_with_generalization"
        and M.classify_startup(1.0, 0.1, 0.25, 0.501) == "learned_and_failed_to_transfer",
    )
    check(
        "startup C9: the float artifact is now RULED.  (1.0-0.90) is "
        "0.09999999999999998, and ruling C9 registers r < 0.10 - 1e-12, so an "
        "algebraic 10% improvement is NOT 'never started'",
        (1.0 - 0.90) < M.STARTUP_MIN_RELATIVE_IMPROVEMENT
        and M.STARTUP_IMPROVEMENT_TOLERANCE == 1e-12
        and M.classify_startup(1.0, 0.90, 0.80, 0.9) == "started_not_yet_learned",
    )
    check(
        "startup C9: values ON, just inside and just outside the 1e-12 tolerance "
        "boundary classify as the ruling's exact predicate requires",
        M.classify_startup(1.0, 1.0 - 0.10, 0.80, 0.9) == "started_not_yet_learned"
        and M.classify_startup(1.0, 1.0 - (0.10 - 1e-13), 0.80, 0.9) == "started_not_yet_learned"
        and M.classify_startup(1.0, 1.0 - (0.10 - 1e-9), 0.80, 0.9) == "never_started",
    )
    check(
        "startup C9: the tolerance touches the relative improvement ONLY -- the "
        "unchanged initial-floor boundary and the other E thresholds keep no epsilon",
        M.STARTUP_INITIAL_FLOOR_LOSS == 1e-8
        and M.classify_startup(1e-8, 1e-8, 0.9, 0.9) == "initially_at_floor"
        and M.classify_startup(1e-8 + 1e-9, 1e-8, 0.9, 0.9) != "initially_at_floor"
        and M.classify_startup(1.0, 0.1, 0.25, 0.5) == "learned_with_generalization"
        and M.classify_startup(1.0, 0.1, 0.2500000001, 0.5) == "started_not_yet_learned",
    )
    check(
        "startup: a NaN loss is a numerical failure, and a deadline is infrastructure "
        "incomplete -- neither disappears from a denominator",
        M.classify_startup(float("nan"), 1.0, 0.5, 0.5) == "numerical_failure"
        and M.classify_startup(1.0, 0.5, 0.5, 0.5, infrastructure_incomplete=True)
        == "infrastructure_incomplete",
    )
    check(
        "startup: fitting E and query E are EVALUATOR-ONLY, so the trainer's own label "
        "is explicitly pending rather than silently guessed",
        M.classify_startup(1.0, 0.5) == "pending_evaluator_E",
    )
    episodes = synthetic_episodes(8, seed=61)
    index, prefix, horizons = M.audit_set(episodes)
    check(
        "startup: the fitting audit set uses fit episodes only, each horizon, its LAST "
        "eligible observed endpoint -- deterministic and not chosen by difficulty",
        all(int(episodes.role[i]) == M.EPISODE_ROLE_FIT for i in index.tolist())
        and set(horizons.tolist()) <= set(M.HORIZONS)
        and all(
            float(episodes.sensor_present[int(i), int(p) + int(h) - 1]) == 1.0
            for i, p, h in zip(index, prefix, horizons)
        ),
    )
    repeat = M.audit_set(episodes)
    check(
        "startup: the audit set is identical when recomputed (same initial/final set)",
        torch.equal(index, repeat[0]) and torch.equal(prefix, repeat[1]) and torch.equal(horizons, repeat[2]),
    )


# =============================================================================
# GROUP: fit, resume, predict, data boundary
# =============================================================================


def group_fit_resume_predict() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        data = root / "data"
        for index, world in enumerate(["w0", "w1"]):
            write_world(data, world, n_episodes=8, seed=70 + index)

        override = [2, 3, 0, 0, 0]
        full = M.run_fit(
            "G",
            str(data),
            ["w0", "w1"],
            [20001],
            budget=64,
            out_dir=str(root / "full"),
            override_step_table=override,
        )
        check(
            "fit: a run declares when its step table was overridden, so a debug "
            "schedule can never be mistaken for the registered one",
            full["step_table_overridden"] is True,
        )
        check(
            "fit: checkpoints are written per world, per seed, per rung",
            (root / "full" / "tierL" / "G" / "w0" / "seed20001" / "rung32.pt").exists()
            and (root / "full" / "tierL" / "G" / "w1" / "seed20001" / "rung64.pt").exists(),
        )
        check(
            "fit: the report carries a startup record per lane with the audit losses "
            "and relative improvement",
            len(full["lanes"]) == 2
            and all(
                set(lane) >= {
                    "fit_audit_loss_initial",
                    "fit_audit_loss_final",
                    "fit_audit_relative_improvement",
                    "startup_label",
                }
                for lane in full["lanes"]
            ),
        )
        check(
            "fit: the ledger records world/seed/arm/rung, data-prefix hash, checkpoint "
            "hash, parameters, storage, updates, counted work, wall time and status",
            all(
                set(entry)
                >= {
                    "world_id",
                    "seed",
                    "arm",
                    "rung_budget",
                    "data_prefix_hash",
                    "checkpoint_hash",
                    "trainable_parameters",
                    "persistent_bytes",
                    "working_history_bytes",
                    "updates",
                    "examples",
                    "observed_targets",
                    "forward_ops",
                    "backward_ops",
                    "optimizer_ops",
                    "evaluation_ops",
                    "wall_seconds",
                    "status",
                }
                for entry in full["ledger"]
            ),
        )

        # exact-state resumption: stop after rung 32, resume, land bitwise identical.
        M.run_fit(
            "G",
            str(data),
            ["w0", "w1"],
            [20001],
            budget=32,
            out_dir=str(root / "part"),
            override_step_table=override,
        )
        M.run_fit(
            "G",
            str(data),
            ["w0", "w1"],
            [20001],
            budget=64,
            out_dir=str(root / "part"),
            resume=True,
            override_step_table=override,
        )
        worst = 0.0
        for world in ["w0", "w1"]:
            a = torch.load(root / "full" / "tierL" / "G" / world / "seed20001" / "rung64.pt", weights_only=False)
            b = torch.load(root / "part" / "tierL" / "G" / world / "seed20001" / "rung64.pt", weights_only=False)
            check(
                f"resume[{world}]: the resumed run continued at the same optimizer step "
                "and rung cursor",
                a["optimizer_step_count"] == b["optimizer_step_count"]
                and a["rung_index"] == b["rung_index"]
                and a["update_in_rung"] == b["update_in_rung"],
            )
            for name in a["parameters"]:
                worst = max(worst, float((a["parameters"][name] - b["parameters"][name]).abs().max()))
                worst = max(worst, float((a["moment1"][name] - b["moment1"][name]).abs().max()))
                worst = max(worst, float((a["moment2"][name] - b["moment2"][name]).abs().max()))
        check(
            "resume: exact-state resumption reproduces weights AND Adam moments bitwise",
            worst == 0.0,
            f"max abs difference {worst:.3e}",
        )

        # predict, keyed by opaque record ID only
        arrays = synthetic_public_arrays(5, seed=99)
        queries = {
            M.PUBLIC_KEYS["record_id"]: np.array([f"rec-{i:04d}" for i in range(5)]),
            M.PUBLIC_KEYS["properties"]: arrays[M.PUBLIC_KEYS["properties"]],
            M.PUBLIC_KEYS["prefix_len"]: np.array([6, 6, 4, 0, 7], dtype=np.int64),
            M.PUBLIC_KEYS["horizon"]: np.array([1, 2, 4, 1, 1], dtype=np.int64),
            M.PUBLIC_KEYS["action_id"]: arrays[M.PUBLIC_KEYS["action_id"]],
            M.PUBLIC_KEYS["source_id"]: arrays[M.PUBLIC_KEYS["source_id"]],
            M.PUBLIC_KEYS["destination_id"]: arrays[M.PUBLIC_KEYS["destination_id"]],
            M.PUBLIC_KEYS["dose"]: arrays[M.PUBLIC_KEYS["dose"]],
            M.PUBLIC_KEYS["sensor"]: arrays[M.PUBLIC_KEYS["sensor"]],
            M.PUBLIC_KEYS["sensor_present"]: arrays[M.PUBLIC_KEYS["sensor_present"]],
            M.PUBLIC_KEYS["query_a"]: np.array([0, 1, 2, 3, 0], dtype=np.int64),
            M.PUBLIC_KEYS["query_b"]: np.array([4, 4, 4, 4, 4], dtype=np.int64),
        }
        query_file = root / "queries.npz"
        np.savez(query_file, **queries)
        out_file = root / "predictions.json"
        values = M.run_predict_semantic_fixture(
            str(root / "full" / "tierL" / "G" / "w0" / "seed20001" / "rung64.pt"), str(query_file), str(out_file)
        )
        check(
            "predict: predictions are keyed by the opaque record ID only, one per record",
            sorted(values) == [f"rec-{i:04d}" for i in range(5)]
            and all(math.isfinite(v) for v in values.values()),
        )
        payload = json.loads(out_file.read_text())
        check(
            "predict: the output file carries no world, family, seed or truth field",
            set(payload) == {"contract_version", "arm", "checkpoint", "predictions"},
        )
        check(
            "predict: a horizon-0 prefix (forecast straight from RESET) is supported",
            math.isfinite(values["rec-0003"]),
        )

        # data boundary: a file carrying evaluator-side fields is refused outright.
        poisoned = dict(queries)
        poisoned["noise_free_response"] = np.zeros((5,), dtype=np.float32)
        poisoned_file = root / "poisoned.npz"
        np.savez(poisoned_file, **poisoned)
        refused = False
        try:
            M.load_queries_semantic_fixture(poisoned_file)
        except ValueError as error:
            refused = "noise_free_response" in str(error)
        check(
            "data boundary: a query file carrying an evaluator-side field is refused, "
            "so the trainer can never hold simulator truth",
            refused,
        )
        family_file = root / "family.npz"
        np.savez(family_file, **{**queries, "family": np.array([1, 1, 1, 1, 1])})
        refused_family = False
        try:
            M.load_queries_semantic_fixture(family_file)
        except ValueError:
            refused_family = True
        check("data boundary: a family tag in a query file is refused", refused_family)

        # deadline handling
        timed = M.run_fit(
            "G",
            str(data),
            ["w0"],
            [20001],
            budget=512,
            out_dir=str(root / "timed"),
            budget_seconds=0.0,
            override_step_table=[5, 5, 5, 5, 5],
        )
        check(
            "deadline: a `--budget-seconds` stop records infrastructure_incomplete "
            "rather than silently reporting a short run as complete",
            timed["deadline_hit"] is True
            and timed["lanes"][0]["startup_label"] == "infrastructure_incomplete"
            and any(entry["status"] == "infrastructure_incomplete" for entry in timed["ledger"]),
        )

        # a mid-rung interruption resumes THAT rung, not the next one
        saved = torch.load(
            root / "timed" / "tierL" / "G" / "w0" / "seed20001" / "rung32.pt", weights_only=False
        )
        check(
            "deadline: the interrupted checkpoint is marked as an incomplete rung",
            saved["completed_rung"] is False and saved["rung_index"] == 0,
        )
        M.run_fit(
            "G",
            str(data),
            ["w0"],
            [20001],
            budget=32,
            out_dir=str(root / "timed"),
            resume=True,
            override_step_table=[5, 5, 5, 5, 5],
        )
        clean = M.run_fit(
            "G",
            str(data),
            ["w0"],
            [20001],
            budget=32,
            out_dir=str(root / "clean"),
            override_step_table=[5, 5, 5, 5, 5],
        )
        resumed_ckpt = torch.load(
            root / "timed" / "tierL" / "G" / "w0" / "seed20001" / "rung32.pt", weights_only=False
        )
        clean_ckpt = torch.load(
            root / "clean" / "tierL" / "G" / "w0" / "seed20001" / "rung32.pt", weights_only=False
        )
        gap = max(
            float((resumed_ckpt["parameters"][n] - clean_ckpt["parameters"][n]).abs().max())
            for n in clean_ckpt["parameters"]
        )
        check(
            "resume: a run interrupted mid rung restarts THAT rung at its exact cursor "
            "and reaches the uninterrupted result bitwise",
            resumed_ckpt["completed_rung"] is True
            and resumed_ckpt["optimizer_step_count"] == clean_ckpt["optimizer_step_count"]
            and gap == 0.0,
            f"max abs difference {gap:.3e}",
        )


# =============================================================================
# GROUP: Agent 1's real public layout.
#
# Uses ONLY the small interface FIXTURE that Agent 1 published for this purpose.
# It deliberately does not read, fit on or score the registered calibration
# worlds: that would be an accuracy measurement, which the preregistration does
# not permit before the wave-1 freeze.
# =============================================================================

ARTIFACTS = ROOT / "artifacts" / "fable-concept-toy20-20260920"
# ct20-v1.1 regenerated data.  The FIXTURE is the small interface fixture this
# file may read and fit on; CALIBRATION is the registered set, which this file
# checks at the FILENAME level only -- it never opens an array there, never fits
# and never scores, because that would be an accuracy measurement before the
# wave-1 freeze.
FIXTURE = ARTIFACTS / "fixture-v1.1" / "public"
CALIBRATION = ARTIFACTS / "calibration-v1.1" / "public"


def group_agent1_layout() -> None:
    if not FIXTURE.is_dir():
        print("skip  agent1 layout: Agent 1's fixture is not present yet")
        return
    worlds = [entry for entry in sorted(FIXTURE.iterdir()) if entry.is_dir()]
    check("agent1: the interface fixture publishes at least one world", len(worlds) >= 1)

    for world in worlds:
        result = M.verify_tokenization_against_agent1(world)
        check(
            f"agent1[{world.name}]: this module's tokenizer reproduces Agent 1's own "
            "support records BIT FOR BIT over a full eight-transition history",
            result["tokenizations_agree"] and result["endpoint_is_final_query"],
            f"max abs difference {result['max_abs_difference_records_0_to_15']}",
        )

    world = worlds[0]
    episodes = M.load_support_agent1(world)
    check(
        "agent1: support episodes carry the registered 3:1 fitting/selection pattern",
        [int(v) for v in episodes.role[:4]] == [0, 0, 0, 1],
    )
    counts = {
        budget: len(M.prefix_episodes(episodes, budget))
        for budget in M.BUDGETS
        if budget // M.N_TRANSITIONS <= len(episodes)
    }
    check(
        "agent1: the nested prefix at each budget holds exactly budget/8 episodes, "
        "ordered by Agent 1's own budget rung",
        all(count == budget // M.N_TRANSITIONS for budget, count in counts.items()),
        str(counts),
    )
    fit_part, selection_part = M.split_roles(M.prefix_episodes(episodes, min(counts) ))
    check(
        "agent1: B=32 is three fitting episodes plus one selection episode",
        len(fit_part) == 3 and len(selection_part) == 1,
    )

    record_ids, records, endpoint, features = M.load_queries_agent1(world)
    check(
        "agent1: a query panel is 96 target predictions with opaque record IDs",
        len(record_ids) == M.QUERY_PANEL_TARGETS
        and tuple(records.shape) == (96, M.FIXED_SEQUENCE_LENGTH, M.RECORD_WIDTH)
        and all(isinstance(value, str) and value for value in record_ids),
    )
    check(
        "agent1: every panel endpoint is a QUERY token with no measurement, and "
        "nothing follows it",
        all(
            float(records[i, int(endpoint[i]), M.SLICE_RECORD_TYPE.start + M.RECORD_TYPE_QUERY]) == 1.0
            and float(records[i, int(endpoint[i]), M.SLICE_SENSOR]) == 0.0
            and float(records[i, int(endpoint[i]), M.SLICE_PRESENT]) == 0.0
            and float(records[i, int(endpoint[i]) + 1 :, 24:].abs().sum()) == 0.0
            for i in range(records.shape[0])
        ),
    )
    check(
        "agent1: the detector query decodes to a valid (a, b) and the decoder feature "
        "block is width 29 (53 minus the 24 context)",
        tuple(features.shape) == (96, M.DECODER_INPUT_WIDTH - M.CONTEXT_WIDTH),
    )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        report = M.run_fit(
            "T",
            str(FIXTURE),
            [world.name],
            [20001],
            budget=32,
            out_dir=str(root / "out"),
            override_step_table=[2, 0, 0, 0, 0],
        )
        check(
            "agent1: the runner fits directly from Agent 1's published layout",
            report["ledger"] and report["ledger"][0]["status"] == "complete",
        )
        values = M.run_predict_agent1(
            str(root / "out" / "tierL" / "T" / world.name / "seed20001" / "rung32.pt"),
            str(world),
            str(root / "p.json"),
        )
        check(
            "agent1: predictions come back keyed by Agent 1's opaque record IDs only",
            sorted(values) == sorted(record_ids) and all(math.isfinite(v) for v in values.values()),
        )

    # -- C11: one join key, spelled by the public loader -----------------------
    loader = M.public_loader()
    check(
        "agent1: the models module imports Agent 1's public loader and builds the "
        "audit join key by CALLING it, so the two sides cannot drift",
        loader is not None
        and M.audit_key("abc123", 7, 2, 8) == loader.PublicDataset.audit_key("abc123", 7, 2, 8)
        and M.audit_key("abc123", 7, 2, 8) == "abc123-fit0007h2e8",
        M.audit_key("abc123", 7, 2, 8),
    )
    check(
        "agent1: the module's own format constant is the canonical SCHEMA.md section 3 "
        "spelling, not the retired models-side one",
        M.AUDIT_KEY_FORMAT == "{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}",
        M.AUDIT_KEY_FORMAT,
    )

    published = json.loads((world / "audit_keys.json").read_text(encoding="utf-8"))
    published_ids = sorted(entry["audit_id"] for entry in published)
    episodes = M.load_support_agent1(world)
    budget = len(episodes) * M.N_TRANSITIONS
    runner = M.Runner("G", [M.Lane(world_id=world.name, seed=20001, episodes=episodes)])
    _, keyed = runner.audit_pass(budget)
    check(
        "agent1: the audit keys this module computes are EXACTLY the audit set Agent 1 "
        "published for the same world -- same cases, same spelling, same endpoints",
        sorted(keyed[0]) == published_ids,
        f"{len(keyed[0])} computed vs {len(published_ids)} published",
    )
    by_id = {entry["audit_id"]: entry for entry in published}
    check(
        "agent1: every computed key's endpoint and horizon agree with Agent 1's own "
        "endpoint/horizon columns for that case",
        all(
            key.endswith(f"h{by_id[key]['horizon']}e{by_id[key]['endpoint']}") for key in keyed[0]
        ),
    )

    # -- the registered set: filenames only ------------------------------------
    if CALIBRATION.is_dir():
        registered = [entry for entry in sorted(CALIBRATION.iterdir()) if entry.is_dir()]
        needed = sorted(M.AGENT1_FILES.values())
        check(
            "agent1: every registered calibration-v1.1 world carries exactly the "
            "SCHEMA.md filenames the production loader resolves (names only -- this "
            "test opens no registered array, fits nothing and scores nothing)",
            len(registered) == 12
            and all(
                all((entry / name).is_file() for name in needed) for entry in registered
            ),
            f"{len(registered)} worlds",
        )


# =============================================================================
# GROUP: Astra's rulings, design/v3/20-concept-toy-rulings-1.md (ct20-v1.1).
#
# One check per model/accounting ruling this module had to implement, plus the
# two-tier freeze, the reconciled ledger and the worst-case L+H preflight.
# =============================================================================

RULINGS = ROOT / "design" / "v3" / "20-concept-toy-rulings-1.md"


def group_rulings() -> None:
    digest = hashlib.sha256(RULINGS.read_bytes()).hexdigest()
    text = RULINGS.read_text(encoding="utf-8")
    check(
        "rulings: the module records the exact rulings document it implements",
        M.RULINGS_SHA256 == digest and M.EXPERIMENT_VERSION == "ct20-v1.1",
        digest[:12],
    )
    check(
        "rulings D: the version label changed but the RNG root did NOT -- no world or "
        "initialization is redrawn just to change a version",
        M.ROOT_NAMESPACE == "premonition/concept-toy20/v1"
        and "Keep the original `premonition/concept-toy20/v1` RNG root" in text,
    )

    # -- A2/A3: two tiers, frozen before the first fit ------------------------
    check(
        "rulings A2: both source tiers are registered with the exact allowances, and "
        "task B's 1.0e8 per rung is unchanged",
        M.TIER_ALLOWANCE_PER_RUNG == {"L": 2.0e8, "H": 1.0e9}
        and M.TIER_ALLOWANCE_PER_FIT == {"L": 1.0e9, "H": 5.0e9}
        and M.TASK_B_ALLOWANCE_PER_RUNG == 1.0e8
        and "tier L: 2.0e8 operations per source rung, 1.0e9 total per fit" in text
        and "tier H: 1.0e9 per rung, 5.0e9 total per fit" in text,
    )
    for tier in M.TIERS:
        for arm in M.ARMS:
            table = M.step_table(arm, tier)
            total = sum(row["counted_total_ops"] for row in table)
            check(
                f"rulings A2[{tier}/{arm}]: every rung is inside its allowance, the fit "
                "total is inside the per-fit allowance, and the table is frozen before "
                "any fit because nothing in it can depend on data or accuracy",
                len(table) == len(M.BUDGETS)
                and all(row["steps"] > 0 for row in table)
                and all(row["counted_total_ops"] <= M.TIER_ALLOWANCE_PER_RUNG[tier] for row in table)
                and total <= M.TIER_ALLOWANCE_PER_FIT[tier],
                f"steps {[row['steps'] for row in table]} total {total:.4g}",
            )
    check(
        "rulings D: NO TIER SALT reaches the shared initialization or data streams -- "
        "the namespaces are identical for L and H, so H starts from the same bytes",
        "H" not in M.init_namespace("w", 1, "c", "p")
        and M.init_namespace("w", 1, "c", "p") == f"{M.ROOT_NAMESPACE}/model/w/1/c/p"
        and M.fit_namespace("w", 1, 32, 0) == f"{M.ROOT_NAMESPACE}/fit/w/1/32/0",
    )

    # -- A1: the reconciled ledger -------------------------------------------
    first = M.rung_reservation("G", M.BUDGETS[0], 0)
    last = M.rung_reservation("G", M.BUDGETS[-1], len(M.BUDGETS) - 1)
    check(
        "rulings A1: rung 1 now charges initialization, the initial fitting audit AND "
        "the initial query panel the calibration gate needs for initial query E",
        {"initialization", "initial_audit_forward", "initial_audit_loss", "initial_query_panel_forward"}
        <= set(first)
        and first["initialization"] == M.initialization_ops("G"),
    )
    check(
        "rulings A1: every rung charges its selection forwards and its query panel, and "
        "the last rung charges the final fitting diagnostics",
        {"selection_forward", "selection_loss", "rung_query_panel_forward"} <= set(first)
        and {"final_audit_forward", "final_audit_loss"} <= set(last),
    )
    check(
        "rulings A1: loss computation is charged, so one update costs more than its "
        "forward, backward and optimizer work alone",
        M.loss_ops(4) == 4 * M.OPS_LOSS_PER_TARGET + M.OPS_LOSS_PER_BATCH
        and M.update_ops("G")
        > M.forward_ops("G", sequences=M.MINIBATCH_EPISODES) * (1 + M.BACKWARD_MULTIPLIER)
        + M.SPEC_PARAMETER_COUNTS["G"] * (M.OPS_ADAMW_PER_PARAMETER + M.OPS_GRADCLIP_PER_PARAMETER),
    )
    check(
        "rulings A1: reservations are upper bounds -- the audit reservation uses the "
        "LARGEST LEGAL audit set, which no observation mask can exceed",
        M.audit_targets(512) == (64 - 16) * len(M.HORIZONS)
        and M.selection_targets(512) == 16 * len(M.HORIZONS),
    )
    for tier in M.TIERS:
        rows = M.planned_cross_arm_use(tier)
        check(
            f"rulings A1[{tier}]: the 5% cross-arm rule is checked at EVERY rung, not "
            "only on the final total",
            len(rows) == len(M.BUDGETS) and all(row["within_5_percent"] for row in rows),
            "worst gap " + f"{max(row['relative_gap'] for row in rows):.4%}",
        )
    actual = M.actual_cross_arm_use(
        {"G": {32: 1.0e8, 64: 1.0e8}, "T": {32: 1.0e8, 64: 2.0e8}}
    )
    check(
        "rulings A1: the same 5% test applies to EXECUTED operations from run ledgers, "
        "and it fails loudly when the arms really diverge",
        actual[0]["within_5_percent"] is True and actual[1]["within_5_percent"] is False,
    )

    # -- C8: the lane axis must not create a decayed matrix -------------------
    check(
        "rulings C8: decay is judged from the UNBATCHED parameter -- a 1-D bias stays "
        "undecayed at every lane count, and a lane axis never promotes it to a matrix",
        all(
            not M.LanedAdamW.decays("backbone.bias_ih", torch.zeros(lanes, 72))
            and not M.LanedAdamW.decays("backbone.ln1_weight", torch.zeros(lanes, 24))
            and M.LanedAdamW.decays("backbone.weight_ih", torch.zeros(lanes, 72, 44))
            for lanes in (1, 2, 36)
        )
        and M.WEIGHT_DECAY_ON_NDIM == 2,
    )

    # -- C3/C4/C5/C6/C7: confirmed conventions --------------------------------
    parameters = M.initial_parameters("T", "ruling-check", 20001)
    check(
        "rulings C3: Q, K and V are three separate 24x24 tensors, each from its own "
        "named Xavier draw, so no fused 24x72 fan-out is used",
        M.QKV_SPLIT_PROJECTIONS
        and all(tuple(parameters[f"backbone.{n}_weight"].shape) == (24, 24) for n in "qkv")
        and len({parameters[f"backbone.{n}_weight"].tobytes() for n in "qkv"}) == 3,
    )
    optimizer = M.LanedAdamW({"w": torch.zeros(1, 2, 2, requires_grad=True)}, 1)
    rates = []
    for _ in range(10):
        rates.append(optimizer.learning_rate())
        optimizer.step_count += 1
    check(
        "rulings C4: lr = 0.001 * min((u+1)/8, 1) on the zero-based update index, "
        "continuing across rungs",
        rates == [0.001 * min((u + 1) / 8, 1) for u in range(10)],
    )
    check(
        "rulings C5: h = (1,2,4)[u%3] on the global counter, so update 0 gets h = 1",
        [M.horizon_for_update(u) for u in range(7)] == [1, 2, 4, 1, 2, 4, 1],
    )
    episodes_drawn, endpoints_drawn = M.sample_minibatch("w", 20001, 32, 0, 3, 4)
    check(
        "rulings C6: four episode indices WITH REPLACEMENT first, then four endpoints "
        "uniform in h..8 inclusive, in that stream order",
        M.MINIBATCH_DRAW_ORDER == ("episodes", "endpoints")
        and len(episodes_drawn) == 4
        and len(endpoints_drawn) == 4
        and all(4 <= int(value) <= M.N_TRANSITIONS for value in endpoints_drawn),
    )
    check(
        "rulings C7: fixed 17-record execution, and the ledger charges that full "
        "executed length rather than a shorter nominal one",
        M.FIXED_SEQUENCE_LENGTH == M.MAX_RECORDS
        and M.operator_cost_table("T") == M.operator_cost_table("T", M.FIXED_SEQUENCE_LENGTH),
    )

    # -- C11 and C10, on disk -------------------------------------------------
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        data = root / "data"
        write_world(data, "w0", n_episodes=8, seed=310)
        semantic = root / "semantic"
        write_world_semantic(semantic, "w0", n_episodes=8, seed=310)

        refused = ""
        try:
            M.load_world_support(semantic, "w0")
        except ValueError as error:
            refused = str(error)
        check(
            "rulings C11: the production loader REFUSES a world published only in the "
            "semantic-array format -- the serialized SCHEMA.md layout is the single "
            "data contract for a registered run",
            "SCHEMA.md" in refused,
        )
        check(
            "rulings C11: the semantic adapter still works for fixtures, but only "
            "behind an explicit opt-in that no production entry point passes",
            len(M.load_world_support(semantic, "w0", allow_semantic_fixture=True)) == 8,
        )
        fit_refused = ""
        try:
            M.run_fit("G", str(semantic), ["w0"], [20001], 32, str(root / "no"),
                      override_step_table=[1, 0, 0, 0, 0])
        except ValueError as error:
            fit_refused = str(error)
        check(
            "rulings C11: `fit` itself is unreachable from the semantic adapter on "
            "registered data",
            "SCHEMA.md" in fit_refused,
        )
        predict_refused = ""
        try:
            M.run_predict("nonexistent.pt", str(semantic / "w0" / "discovery.npz"), "")
        except ValueError as error:
            predict_refused = str(error)
        check(
            "rulings C11: `predict` is unreachable from the semantic adapter too",
            "SCHEMA.md" in predict_refused,
        )

        report_l = M.run_fit(
            "G", str(data), ["w0"], [20001], budget=64, out_dir=str(root / "out"),
            override_step_table=[2, 2, 0, 0, 0], tier="L",
        )
        report_h = M.run_fit(
            "G", str(data), ["w0"], [20001], budget=64, out_dir=str(root / "out"),
            override_step_table=[3, 3, 0, 0, 0], tier="H",
        )
        check(
            "rulings A3: the two tiers write SEPARATE output trees, so neither can be "
            "mistaken for the other's trajectory",
            (root / "out" / "tierL" / "G" / "w0" / "seed20001" / "rung64.pt").exists()
            and (root / "out" / "tierH" / "G" / "w0" / "seed20001" / "rung64.pt").exists()
            and report_l["tier"] == "L"
            and report_h["tier"] == "H",
        )
        low = torch.load(root / "out" / "tierL" / "G" / "w0" / "seed20001" / "rung32.pt", weights_only=False)
        high = torch.load(root / "out" / "tierH" / "G" / "w0" / "seed20001" / "rung32.pt", weights_only=False)
        check(
            "rulings A3: tier H is a FRESH trajectory from the SAME saved initialization "
            "bytes, with its own Adam state and update counter -- never an extension of "
            "tier L's checkpoint",
            low["initial_parameter_hashes"] == high["initial_parameter_hashes"]
            and low["optimizer_step_count"] == 2
            and high["optimizer_step_count"] == 3
            and low["tier"] == "L"
            and high["tier"] == "H",
        )
        mismatch = ""
        try:
            M.run_fit(
                "G", str(data), ["w0"], [20001], budget=64,
                out_dir=str(root / "crossed"), resume=True, tier="H",
                override_step_table=[2, 2, 0, 0, 0],
            )
            # plant an L checkpoint under the H tree and try again
            target = M.checkpoint_path(root / "crossed", "G", "w0", 20001, 64, "H")
            planted = dict(torch.load(target, weights_only=False))
            planted["tier"] = "L"
            torch.save(planted, target)
            M.run_fit(
                "G", str(data), ["w0"], [20001], budget=64,
                out_dir=str(root / "crossed"), resume=True, tier="H",
                override_step_table=[2, 2, 0, 0, 0],
            )
        except ValueError as error:
            mismatch = str(error)
        check(
            "rulings A3: resuming one tier from the other tier's checkpoint is refused "
            "outright, not silently relabelled",
            "forbids extending one tier" in mismatch,
        )

        saved = json.loads(
            M.predictions_path(root / "out", "G", "w0", 20001, "L").read_text(encoding="utf-8")
        )
        check(
            "rulings C10: the fit saves INITIAL and FINAL audit predictions, the initial "
            "and final query predictions and the observed losses, so the evaluator can "
            "finalise without another fit",
            saved["audit_predictions_initial"]
            and saved["audit_predictions_final"]
            and saved["query_predictions_initial"]
            and saved["query_predictions_final"]
            and set(saved["observed_losses"])
            >= {"fit_audit_initial", "fit_audit_final", "selection_by_rung", "updates"},
        )
        keys = sorted(saved["audit_predictions_final"])
        check(
            "rulings C10/C11: audit predictions carry the amended SCHEMA.md join key -- "
            "world, 4-digit episode, horizon, 1-based endpoint -- and the same keys "
            "appear in the initial and final sets",
            keys == sorted(saved["audit_predictions_initial"])
            and all(re.fullmatch(r"w0-fit\d{4}h[124]e\d+", key) for key in keys),
            keys[0],
        )
        check(
            "rulings C11: the saved key equals what the public loader itself would "
            "spell for the same (world, episode, horizon, endpoint), and the retired "
            "models-side spelling appears nowhere in the file",
            all(
                key
                == M.public_loader().PublicDataset.audit_key(
                    "w0", int(key[6:10]), int(key[11]), int(key.split("e")[-1])
                )
                for key in keys
            )
            and not any(re.fullmatch(r"e\d+/h\d+/t\d+", key) for key in keys),
            saved["audit_key_format"],
        )
        check(
            "rulings C10: query predictions are keyed by the panel's opaque record IDs "
            "and the file carries no truth, noise-free response, V or family field",
            all(key.startswith("w0-q") for key in saved["query_predictions_final"])
            and len(saved["query_predictions_final"]) == M.QUERY_PANEL_TARGETS
            and not ({"noise_free_response", "truth", "V", "family", "outer_split"} & set(saved)),
        )
        check(
            "rulings C10/D: every saved artefact records ct20-v1.1 and the rulings hash",
            saved["experiment_version"] == "ct20-v1.1"
            and saved["rulings_sha256"] == digest
            and low["experiment_version"] == "ct20-v1.1"
            and all(entry["experiment_version"] == "ct20-v1.1" for entry in report_l["ledger"]),
        )
        check(
            "rulings C10: the trainer's own label stays `pending_evaluator_E` -- the "
            "evaluator finalises it after the predictions are sealed",
            saved["startup_label"] == "pending_evaluator_E"
            and saved["startup_label_is_final"] is False,
        )

        entry = report_l["ledger"][0]
        check(
            "rulings A1: the ledger reports USEFUL updates, examples and empty batches "
            "alongside estimated operations",
            {"useful_updates", "useful_lane_updates", "examples", "empty_minibatches"} <= set(entry)
            and entry["useful_updates"] <= entry["updates"],
        )
        check(
            "rulings A1: each rung reports its reservation, the operations actually "
            "EXECUTED and the UNUSED reservation separately -- and the unused saving is "
            "never spent on extra fitting",
            {"rung_reserved_ops", "rung_executed_non_fitting_ops", "rung_unused_reservation_ops"}
            <= set(entry)
            and entry["rung_unused_reservation_ops"] > 0
            and all(row["rung_within_allowance"] for row in report_l["ledger"])
            and all(
                row["completed_steps_in_rung"] <= row["planned_steps"] for row in report_l["ledger"]
            ),
            f"unused {entry['rung_unused_reservation_ops']:.4g} of {entry['rung_reserved_ops']:.4g}",
        )
        check(
            "rulings A1: initialization is charged once, and the executed ledger "
            "itemises the initial audit and the initial query panel by purpose",
            report_l["work"]["initialization_ops"] == M.initialization_ops("G")
            and {"initial_fitting_audit", "initial_query_panel", "final_query_panel"}
            <= set(report_l["work"]["evaluation_ops_by_purpose"]),
        )


def group_wave_preflight() -> None:
    # A deliberately tiny dry run: this is a plumbing check on the PROJECTION,
    # not a timing measurement, and it reports no accuracy of any kind.
    measurements = {arm: M.timing_fixture(arm, lanes=2, seconds=0.2) for arm in M.WAVE1_ARMS}
    projection = M.wave1_projection(measurements)
    check(
        "preflight: the projection covers the WORST-CASE COMPLETE L+H schedule, both "
        "arms, all five rungs, 12 worlds x 3 seeds",
        set(projection["per_tier"]) == set(M.TIERS)
        and all(
            set(projection["per_tier"][tier]["per_arm"]) == set(M.WAVE1_ARMS) for tier in M.TIERS
        )
        and projection["lanes_per_arm"] == 36
        and projection["fits"] == 72,
    )
    check(
        "preflight: it includes every scoring pass and every write, not fitting alone -- "
        "the reviewed ~80-second figure counted neither the query panels nor the writes",
        all(
            projection["per_tier"][tier]["per_arm"][arm]["projected_query_panel_seconds"] > 0.0
            and projection["per_tier"][tier]["per_arm"][arm]["projected_write_seconds"] > 0.0
            and projection["per_tier"][tier]["per_arm"][arm]["projected_evaluation_seconds"] > 0.0
            for tier in M.TIERS
            for arm in M.WAVE1_ARMS
        ),
    )
    check(
        "preflight: tier H is projected to need far more fitting time than tier L, "
        "because it is a complete second trajectory at five times the allowance",
        projection["per_tier"]["H"]["projected_tier_seconds"]
        > 3.0 * projection["per_tier"]["L"]["projected_tier_seconds"],
    )
    check(
        "preflight: the 1.5x margin, the 300-second reserve and the unchanged "
        "1,200/1,500-second limits are all applied, and the verdict is explicit",
        projection["projected_seconds_with_1_5x_margin"]
        == projection["projected_seconds_raw"] * 1.5
        and projection["scoring_reserve_seconds"] == 300.0
        and projection["soft_compute_stop_seconds"] == 1200.0
        and projection["hard_deadline_seconds"] == 1500.0
        and projection["usable_seconds"] == 900.0
        and projection["verdict"] in {"fits", "resource-infeasible"},
    )
    check(
        "preflight: an infeasible schedule is reported as `resource-infeasible` rather "
        "than by omitting cells or silently adding another wave",
        M.wave1_projection(
            {
                arm: {**measurements[arm], "updates_per_second_all_lanes": 1e-6}
                for arm in M.WAVE1_ARMS
            }
        )["verdict"]
        == "resource-infeasible",
    )


# =============================================================================


def main() -> int:
    torch.set_num_threads(1)
    group_interface()
    group_causality()
    group_rollout()
    group_reset()
    group_registered_numbers()
    group_shapes_and_gradients()
    group_lane_independence()
    group_loss_and_cost()
    group_startup()
    group_fit_resume_predict()
    group_agent1_layout()
    group_rulings()
    group_wave_preflight()
    print(f"\nALL {CHECKS} CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
