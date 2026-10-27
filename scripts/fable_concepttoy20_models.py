#!/usr/bin/env python3
"""concept-toy20 PHASE A -- baseline learners G (GRU) and T (transformer).

Registered by design/v3/20-concept-toy-simulator-spec.md (the executable contract),
design/v3/20-concept-toy-preregistration-draft.md (optimizer, budgets, startup
classification, compute accounting) and design/v3/20-concept-toy-build-plan.md
(Agent 2, Phase A).

PHASE A SCOPE.  Only arms G and T exist here, plus the shared decoder, loss,
initialization, runner, forecast API, checkpointing and compute-cost hooks needed
for the wave-1 baseline calibration pilot.  The state pool and the arms P, T-pool,
T-fit, R, Q and P-fixed are DELIBERATELY ABSENT: the build plan forbids building
them until the calibration gate passes.

NOTHING IN THIS FILE HAS BEEN FIT ON SIMULATOR DATA.  Every number printed by
`count-params`, `cost` and `timing-fixture` is an architecture or an engineering
timing fact.  No learning claim is made or implied.

ADDITIVE ONLY.  This module imports no earlier experiment code and loads no
earlier checkpoint.

CLI
---
    fit             independent per-world/per-seed fitting (optional vectorised
                    lanes with separate parameters/moments/gradients/draws),
                    resumable with exact-state resumption, `--budget-seconds`
                    wave deadline handling.
    predict         forecasts for public query records, keyed by opaque record ID.
    count-params    instantiated parameter counts vs the spec's contract numbers.
    cost            operator-level cost ledger and the frozen per-rung step table.
    timing-fixture  bounded synthetic dry-run timing + wave-1 projection.

Run with the project's registered interpreter and one thread, e.g.

    OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    PYTHONPATH="$(python3 -c 'import json;print(":".join(json.load(open("runtime.local.json"))["import_roots"]))')" \
    python3.12 -B scripts/fable_concepttoy20_models.py count-params
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import pathlib
import resource
import sys
import time
from typing import Any

import numpy as np
import torch

# =============================================================================
# ADAPTER SECTION -- ALL CONTRACT ASSUMPTIONS LIVE HERE AND NOWHERE ELSE.
#
# Diff this block against Agent 1's
#   artifacts/fable-concept-toy20-20260920/SCHEMA.md
# and change it in ONE place if the simulator's serialization differs.
#
# Sources: simulator spec section 3 ("Exact public interface"), section 2
# ("Measurement and missingness"), section 4 ("Fixed traces and budgets"),
# section 6 (widths), build plan section 1 ("Public batch contract").
# =============================================================================

CONTRACT_VERSION = "ct20-v1"
# design/v3/20-concept-toy-rulings-1.md takes precedence over the three contracts.
# Ruling D: the prospective freeze is ct20-v1.1; A2/A3 and B1 are substantive
# amendments and must never be presented as unchanged ct20-v1.
#
# Three version layers, per rulings 3 (ct20-v1.2) section 1.3:
#   - RNG / contract root:        ct20-v1   (CONTRACT_VERSION, inherited, unchanged)
#   - data and gate contract:     ct20-v1.1 (simulator, loader, calculator, both data
#                                            manifests -- bytes and hashes UNCHANGED)
#   - registration of this run:   ct20-v1.2 (EXPERIMENT_VERSION, below)
# ct20-v1.1 ran wave 1 once and ended `calibration-invalid/accounting`: the fit executed
# a seventh query panel (`final_query_panel`) that the registered schedule never reserved,
# carrying rung 512 over its allowance.  ct20-v1.2 removes that redundant pass and adds
# accounting guards.  It changes no step table, allowance, cost constant, seed, data byte,
# initialization byte or RNG namespace, so it is an implementation-conformance repair under
# rulings 1 D, not a substantive amendment.  See wave1/ACCOUNTING-DIAGNOSIS.md
# (sha256 1de7eb489ea0b2e8cde7d1f59798a9352dbd7678821cfd4d6ff527facc225ea7) and
# design/v3/20-concept-toy-rulings-3-fable-review.md.
EXPERIMENT_VERSION = "ct20-v1.2"
RULINGS_DOC = "design/v3/20-concept-toy-rulings-1.md"
RULINGS_SHA256 = "40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de"
# Ruling D: the RNG root is INHERITED unchanged; the experiment version is
# separate, and no world or initialization is redrawn to change a version label.
ROOT_NAMESPACE = "premonition/concept-toy20/v1"

# --- the float32 record vector of length 44, in the spec's field order ---------
RECORD_WIDTH = 44
SLICE_PROPERTIES = slice(0, 24)      # four rows of six, sorted by local public ID
SLICE_ACTION = slice(24, 29)         # one-hot public action ID, all zero at RESET
SLICE_SOURCE = slice(29, 33)         # one-hot i, all zero at RESET
SLICE_DESTINATION = slice(33, 38)    # one-hot j=0..3 or NONE=4
SLICE_DOSE = slice(38, 39)           # -1/+1 on pulse, zero otherwise
SLICE_SENSOR = slice(39, 40)         # returned y; zero if missing or a query token
SLICE_PRESENT = slice(40, 41)        # observation mask; zero on QUERY and RESET
SLICE_RECORD_TYPE = slice(41, 44)    # one-hot RESET / QUERY / OBSERVED

RECORD_TYPE_RESET = 0
RECORD_TYPE_QUERY = 1
RECORD_TYPE_OBSERVED = 2

N_OBJECTS = 4
N_PROPERTIES = 6
N_ACTIONS = 5
DESTINATION_NONE = 4                 # index 4 of the width-5 destination one-hot
N_TRANSITIONS = 8                    # transitions per episode
MAX_RECORDS = 17                     # RESET + 8 * (QUERY, OBSERVED)

# --- the public detector query (a, b) -----------------------------------------
QUERY_A_WIDTH = 4                    # one-hot a over objects
QUERY_B_WIDTH = 5                    # one-hot b over objects, including NONE
QUERY_B_NONE = 4

# --- decoder input layout (spec section 6) ------------------------------------
CONTEXT_WIDTH = 24
POOL_COORDINATES_MAX = 4             # Phase A always writes zeros into these slices
DECODER_INPUT_WIDTH = (
    CONTEXT_WIDTH                    # 24 context
    + POOL_COORDINATES_MAX           # z[a, 4]  -- zero for ordinary baselines
    + POOL_COORDINATES_MAX           # z[b, 4]  -- zero for ordinary baselines
    + N_PROPERTIES                   # p[a, 6]
    + N_PROPERTIES                   # p[b, 6]  -- zero when b is NONE
    + QUERY_A_WIDTH                  # onehot(a, 4)
    + QUERY_B_WIDTH                  # onehot(b, 5)
)                                    # == 53
DECODER_HIDDEN = 16

# --- simulator constants the learner is allowed to know (public, family-free) --
LOSS_NORMALIZER = 0.25               # prereg section 3: squared error / 0.25
BUDGETS = (32, 64, 128, 256, 512)    # environment transitions, nested prefixes
EPISODE_GROUP = 4                    # in each group of four episodes ...
SELECTION_INDEX_IN_GROUP = 3         # ... index 3 is the selection episode
HORIZONS = (1, 2, 4)

# --- public batch key names (Agent 1's arrays).  GUESSED; diff vs SCHEMA.md ----
# The semantic fields below are sufficient to rebuild the 44-wide record vector
# exactly as the spec defines it, so this module never depends on Agent 1's
# tokenization, only on these per-transition semantic arrays.
PUBLIC_KEYS = {
    "properties": "public_properties",       # (E, 4, 6) float32
    "action_id": "action_id",                # (E, 8) int
    "source_id": "source_id",                # (E, 8) int
    "destination_id": "destination_id",      # (E, 8) int, 4 == NONE
    "dose": "dose",                          # (E, 8) float32
    "sensor": "sensor",                      # (E, 8) float32, zero where absent
    "sensor_present": "sensor_present",      # (E, 8) {0, 1}
    "episode_role": "episode_role",          # (E,) 0 == fitting, 1 == selection
    "episode_index": "episode_index",        # (E,) nested-prefix order
    "record_id": "record_id",                # (Q,) opaque string IDs
    "prefix_len": "prefix_len",              # (Q,) observed transitions in a query
    "horizon": "horizon",                    # (Q,) forecast steps
    "query_a": "query_a",                    # (Q,) detector a
    "query_b": "query_b",                    # (Q,) detector b, 4 == NONE
}
EPISODE_ROLE_FIT = 0
EPISODE_ROLE_SELECTION = 1

# Ruling C10 + C11: saved audit predictions need STABLE episode/horizon/endpoint
# keys, and the amended SCHEMA.md (section 3) is the single contract that fixes
# their spelling.  This is THAT canonical spelling, and `audit_key` below builds
# it by calling the public loader's own `PublicDataset.audit_key` so the string
# can only ever be produced in one place.  `endpoint` is 1-based and equals
# prefix_length + horizon; `episode_index` is the registered nested-prefix index,
# so a key means the same case at every rung, in both tiers, for both arms.
#
# The earlier models-side spelling "e{episode}/h{horizon}/t{endpoint}" is GONE:
# it omitted the world and was therefore ambiguous across the twelve worlds.  The
# simulator keeps a read-side shim for it, but this frozen build emits only the
# canonical form.
AUDIT_KEY_FORMAT = "{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}"
PUBLIC_LOADER_MODULE = "fable_concepttoy20_public.py"
_public_loader: Any = None


def public_loader() -> Any:
    """Import Agent 1's public loader from beside this file, once.

    This is the ONLY module a learner is allowed to import (its own docstring),
    it reads no `private/` path and it imports nothing from the simulator, so no
    coefficient, family, latent state, noise-free response or normalization
    constant can reach a model through it.  Returns None if it is absent, which
    keeps this module runnable on its own for `count-params` and `cost`.
    """
    global _public_loader
    if _public_loader is None:
        path = pathlib.Path(__file__).with_name(PUBLIC_LOADER_MODULE)
        if not path.exists():  # pragma: no cover - only when run outside the repo
            _public_loader = False
        else:
            import importlib.util

            spec = importlib.util.spec_from_file_location("fable_concepttoy20_public", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["fable_concepttoy20_public"] = module
            spec.loader.exec_module(module)
            _public_loader = module
    return _public_loader or None


def audit_key(world_public_id: str, episode_index: int, horizon: int, endpoint: int) -> str:
    """The one supported join key (amended SCHEMA.md section 3).

    Delegates to `PublicDataset.audit_key` whenever the public loader is present,
    so the models side cannot drift from the data side by re-spelling the format.
    """
    loader = public_loader()
    if loader is not None:
        return loader.PublicDataset.audit_key(world_public_id, episode_index, horizon, endpoint)
    return AUDIT_KEY_FORMAT.format(
        world_public_id=world_public_id,
        episode_index=int(episode_index),
        horizon=int(horizon),
        endpoint=int(endpoint),
    )

# Anything outside this allowlist in a query file is refused: the trainer must
# never receive hidden responses, noise, family tags, coefficients or world
# identity (spec section 3; build plan "Private evaluator contract").
QUERY_FILE_ALLOWED_KEYS = frozenset(
    [
        PUBLIC_KEYS["record_id"],
        PUBLIC_KEYS["properties"],
        PUBLIC_KEYS["prefix_len"],
        PUBLIC_KEYS["horizon"],
        PUBLIC_KEYS["action_id"],
        PUBLIC_KEYS["source_id"],
        PUBLIC_KEYS["destination_id"],
        PUBLIC_KEYS["dose"],
        PUBLIC_KEYS["sensor"],
        PUBLIC_KEYS["sensor_present"],
        PUBLIC_KEYS["query_a"],
        PUBLIC_KEYS["query_b"],
    ]
)
SUPPORT_FILE_ALLOWED_KEYS = frozenset(
    [
        PUBLIC_KEYS["properties"],
        PUBLIC_KEYS["action_id"],
        PUBLIC_KEYS["source_id"],
        PUBLIC_KEYS["destination_id"],
        PUBLIC_KEYS["dose"],
        PUBLIC_KEYS["sensor"],
        PUBLIC_KEYS["sensor_present"],
        PUBLIC_KEYS["episode_role"],
        PUBLIC_KEYS["episode_index"],
        PUBLIC_KEYS["record_id"],
    ]
)

# =============================================================================
# NAMED CONSTANTS FOR EVERY PLACE THE CONTRACTS WERE SILENT OR AMBIGUOUS.
#
# ALL NINE ARE NOW RULED by design/v3/20-concept-toy-rulings-1.md section C
# (the rulings' C1..C9 correspond to the items labelled A1..A9 below, in order).
# Every ruling CONFIRMED the literal value already implemented here, so no
# behaviour changes; the constants stay because the ruling names the reading and
# forbids the alternative, and a named constant is where an auditor looks.
# =============================================================================

# A1 == ruling C1.  RULED: keep properties, action, source, destination, dose and
#     the OBSERVED type; zero only sensor and present.  "The forecast removes
#     future measurements, not the known action history."
#     "append its QUERY and then a blank OBSERVED token (sensor=0, present=0)".
#     Literal: only the measurement is blanked; the action fields stay, exactly as
#     a real OBSERVED record repeats "the same action".
#     Alternative: an all-zero token except record_type.
BLANK_OBSERVED_KEEPS_ACTION_FIELDS = True

# A2 == ruling C2.  RULED: include self (j<=i).  "QUERY may see its own action,
#     never its later OBSERVED result or padding."
#     Attention: "No attention mask may include the current result" and "prefix
#     attention includes only preceding RESET/QUERY/OBSERVED records".  A QUERY
#     token carries no result, so literal causal self-inclusion is safe and is
#     required for record 0 to have anything to attend to.
#     Alternative: strictly-preceding attention (diagonal excluded).
CAUSAL_ATTENTION_INCLUDES_SELF = True

# A3 == ruling C3.  RULED: freeze THREE separate projections, each initialized by
#     its own named 24x24 Xavier draw.  A fused 24x72 draw has a different fan-out
#     and therefore a different distribution.  A later fused implementation is
#     permitted only if it preserves these split tensors, names and behaviour.
#     "QKV 1,800" parameters is consistent with either one fused Linear(24,72) or
#     three Linear(24,24).  The counts match; the Xavier bound does NOT
#     (sqrt(6/96) fused vs sqrt(6/48) split).  Literal reading of "Ordinary Linear
#     matrices: Xavier uniform" plus a standard block: three separate projections.
QKV_SPLIT_PROJECTIONS = True

# A4 == ruling C4.  RULED: eight updates; zero-based update u uses
#     lr = 0.001 * min((u + 1) / 8, 1).  Continue across rungs; reset at the start
#     of each independent tier fit and of task B.  (u = 0 -> 0.001/8, u = 7 ->
#     0.001, which is exactly what `LanedAdamW.learning_rate` already computed.)
#     "First eight optimizer updates linearly warm up from 0.001/8 to 0.001".
#     Literal: update u in 1..8 uses lr = BASE_LR * u / 8, so update 1 is
#     BASE_LR/8 and update 8 is BASE_LR.
#     Alternative: update 1 already at BASE_LR/8 rising to BASE_LR at update 9.
WARMUP_UPDATES = 8

# A5 == ruling C5.  RULED: zero-based, h = (1, 2, 4)[u % 3]; update 0 gets h = 1;
#     the global counter continues across rungs.
#     "Horizon cycles 1,2,4 by global optimizer update index".  Literal: a
#     zero-based count of completed updates, so the first update uses h=1.
#     Alternative: one-based, first update h=2.
HORIZON_CYCLE_IS_ZERO_BASED = True

# A6 == ruling C6.  RULED: draw four fitting episode indices WITH REPLACEMENT
#     first, then four endpoints uniformly in h..8 INCLUSIVE, in this stream
#     order.  Keep absent endpoints and zero-loss batches; never select examples
#     by observation availability.
#     Minibatch draw order inside one `fit/{world}/{seed}/{rung}/{update}` stream.
#     Literal reading of the sentence order in prereg section 3: episodes first
#     ("samples four fitting episodes"), then endpoints ("within each sampled
#     episode choose endpoint t").
MINIBATCH_DRAW_ORDER = ("episodes", "endpoints")
MINIBATCH_EPISODES = 4

# A7 == ruling C7.  RULED: keep fixed 17-record execution for all arms, with the
#     prediction gathered at the correct final QUERY and future/padding excluded
#     causally -- PROVIDED the cost ledger charges their actual work, which is
#     why `operator_cost_table` is evaluated at FIXED_SEQUENCE_LENGTH.
#     Sequence length actually executed.  Forecast sequences are never longer than
#     16 records, but padding every batch to the full 17 makes the counted
#     operation ledger exact rather than data dependent, and makes a vectorised
#     lane structurally identical to an unbatched run.  Causal masking guarantees
#     the endpoint prediction cannot see padded positions.
FIXED_SEQUENCE_LENGTH = MAX_RECORDS

# A8 == ruling C8.  RULED: matrix weights only; no bias or LayerNorm scale/offset
#     decay; determined from each UNBATCHED parameter, EXCLUDING the vectorized
#     lane axis, so batching cannot turn a bias vector into a decayed matrix.
#     Weight decay "on matrix weights only": applied to every 2-D parameter
#     (including GRU weight_ih / weight_hh), never to biases or LayerNorm
#     scale/offset, which are 1-D.
WEIGHT_DECAY_ON_NDIM = 2

# A9 == ruling A1/C7.  RULED: the cost conventions are accepted as a frozen
#     ENGINEERING COST ESTIMATE -- not equal hardware FLOPs, elapsed time or
#     energy -- and dense 17x17 attention is charged when that is what executes.
#     Attention operation counting.  The ledger counts the DENSE T x T attention
#     matmuls, not the causal-triangle half, because the executed kernel is dense.
COST_COUNTS_DENSE_ATTENTION = True

# --- registered optimizer (prereg section 2) ---------------------------------
BASE_LR = 0.001
ADAM_BETA1 = 0.9
ADAM_BETA2 = 0.99
ADAM_EPS = 1e-8
WEIGHT_DECAY = 0.0001
GRAD_CLIP_NORM = 1.0

# --- registered compute allowances -------------------------------------------
# Ruling A2: TWO tiers are registered and both are frozen BEFORE the first fit.
# Ruling A3: tier H runs at most once, only after a complete, finite, valid tier-L
# run returns a too-hard / failed-control-competence / inconclusive verdict.  A
# tier-L failure is NEVER evidence of intrinsic task difficulty.
TIERS = ("L", "H")
TIER_ALLOWANCE_PER_RUNG = {"L": 2.0e8, "H": 1.0e9}
TIER_ALLOWANCE_PER_FIT = {"L": 1.0e9, "H": 5.0e9}
DEFAULT_TIER = "L"
SOURCE_ALLOWANCE_PER_RUNG = TIER_ALLOWANCE_PER_RUNG[DEFAULT_TIER]   # legacy alias
SOURCE_ALLOWANCE_CUMULATIVE = (2e8, 4e8, 6e8, 8e8, 1e9)
# Ruling A3 step 6: task B's allowance is unchanged.  Task B is not Phase A and
# is not implemented here; the constant exists so the number is recorded once.
TASK_B_ALLOWANCE_PER_RUNG = 1.0e8
# Ruling A1: the 5% cross-arm actual-use requirement is checked at EVERY rung,
# not only on the final total.
CROSS_ARM_MAX_RELATIVE_GAP = 0.05

# Ruling A3 step 3: H is a FRESH complete five-rung trajectory from the SAME saved
# initialization bytes, the same worlds/seeds/support/query tensors and the same
# registered RNG mappings, with Adam and the global update counter reset at the
# start of the tier.  It is never an extension of L's B=512 checkpoint, never a
# rerun of only the failed cases, and it carries separate output IDs and ledgers.
# Ruling D: NO TIER SALT enters the shared initialization or data streams, so
# neither `init_namespace` nor `fit_namespace` mentions the tier -- the tiers are
# distinguished by output path and ledger field only.
TIER_IS_A_FRESH_TRAJECTORY = True

# --- registered wave limits (prereg section 9) -------------------------------
WAVE_SOFT_COMPUTE_STOP_SECONDS = 1200.0
WAVE_HARD_DEADLINE_SECONDS = 1500.0
WAVE_SCORING_RESERVE_SECONDS = 300.0
WAVE_TIMING_MARGIN = 1.5

# --- startup classification thresholds (prereg section 8) --------------------
STARTUP_MIN_RELATIVE_IMPROVEMENT = 0.10
# Ruling C9: evaluate in binary64 with this tolerance on the RELATIVE IMPROVEMENT
# only, so an algebraic 10% improvement cannot become a failed startup through
# subtraction roundoff.  No rounding, no library-default isclose, and NO new
# tolerance on any other E threshold.
STARTUP_IMPROVEMENT_TOLERANCE = 1e-12
STARTUP_NEVER_STARTED_FITTING_E = 0.80
STARTUP_LEARNED_FITTING_E = 0.25
STARTUP_TRANSFER_QUERY_E = 0.50
STARTUP_INITIAL_FLOOR_LOSS = 1e-8

# --- registered contract parameter counts (spec sections 6 and 7) ------------
SPEC_PARAMETER_COUNTS = {
    "gru_backbone": 5040,
    "decoder": 881,
    "G": 5921,
    "T": 6881,
    "T_input_projection": 1080,
    "T_qkv": 1800,
    "T_attention_output": 600,
    "T_feedforward": 2376,
    "T_block_norms": 96,
    "T_final_norm": 48,
}

ARMS = ("G", "T")


# =============================================================================
# DETERMINISTIC SEED DERIVATION (spec section 5)
# =============================================================================


def namespace_seed(namespace: str) -> int:
    """Unsigned little-endian integer from the first eight bytes of SHA256(ns)."""
    digest = hashlib.sha256(namespace.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


def namespace_generator(namespace: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(namespace_seed(namespace)))


def init_namespace(world_id: str, seed: int, component: str, parameter: str) -> str:
    return f"{ROOT_NAMESPACE}/model/{world_id}/{seed}/{component}/{parameter}"


def fit_namespace(world_id: str, seed: int, rung: int, update: int) -> str:
    return f"{ROOT_NAMESPACE}/fit/{world_id}/{seed}/{rung}/{update}"


def tensor_hash(tensor: torch.Tensor) -> str:
    """SHA-256 over dtype, shape and raw contiguous little-endian bytes."""
    array = tensor.detach().to(torch.float32).cpu().numpy()
    array = np.ascontiguousarray(array, dtype="<f4")
    hasher = hashlib.sha256()
    hasher.update(str(array.dtype.str).encode("utf-8"))
    hasher.update(str(array.shape).encode("utf-8"))
    hasher.update(array.tobytes())
    return hasher.hexdigest()


# =============================================================================
# INITIALIZATION (prereg section 2).  Generated on CPU in float32 from the
# per-parameter namespaces, never from a framework global RNG.
# =============================================================================


def xavier_uniform(shape: tuple[int, int], rng: np.random.Generator, gain: float = 1.0) -> np.ndarray:
    """Xavier uniform for a PyTorch-style (out, in) matrix, gain 1."""
    fan_out, fan_in = shape
    bound = gain * math.sqrt(6.0 / (fan_in + fan_out))
    return rng.uniform(-bound, bound, size=shape).astype(np.float32)


def orthogonal(shape: tuple[int, int], rng: np.random.Generator, gain: float = 1.0) -> np.ndarray:
    """Orthogonal init, gain 1, with the standard diag(R) sign correction."""
    rows, cols = shape
    flat = rng.standard_normal(size=(max(rows, cols), min(rows, cols)))
    q, r = np.linalg.qr(flat)
    q = q * np.sign(np.diag(r))
    if rows < cols:
        q = q.T
    return (gain * q[:rows, :cols]).astype(np.float32)


def sinusoidal_positions(length: int, width: int) -> torch.Tensor:
    """Fixed sinusoidal encoding with frequencies 10000^(-2j/width)."""
    position = np.arange(length, dtype=np.float64)[:, None]
    pair = np.arange(width // 2, dtype=np.float64)[None, :]
    frequency = np.power(10000.0, -2.0 * pair / width)
    table = np.zeros((length, width), dtype=np.float64)
    table[:, 0::2] = np.sin(position * frequency)
    table[:, 1::2] = np.cos(position * frequency)
    return torch.tensor(table, dtype=torch.float32)


def init_decoder(world_id: str, seed: int) -> dict[str, np.ndarray]:
    """Shared 53 -> 16 -> 1 decoder.  Identical starting bytes across all arms."""
    component = "decoder"
    out: dict[str, np.ndarray] = {}
    out["hidden_weight"] = xavier_uniform(
        (DECODER_HIDDEN, DECODER_INPUT_WIDTH),
        namespace_generator(init_namespace(world_id, seed, component, "hidden_weight")),
    )
    out["hidden_bias"] = np.zeros((DECODER_HIDDEN,), dtype=np.float32)
    out["out_weight"] = xavier_uniform(
        (1, DECODER_HIDDEN),
        namespace_generator(init_namespace(world_id, seed, component, "out_weight")),
    )
    out["out_bias"] = np.zeros((1,), dtype=np.float32)
    return out


def init_gru(world_id: str, seed: int) -> dict[str, np.ndarray]:
    """GRU24 backbone.  PyTorch gate order r / z / n, two bias vectors.

    Input matrices: Xavier uniform separately per gate.
    Recurrent matrices: orthogonal separately per gate, gain 1.
    Input-side update-gate bias is +1; every other bias entry is zero.
    """
    component = "backbone_gru24"
    hidden = CONTEXT_WIDTH
    weight_ih = np.zeros((3 * hidden, RECORD_WIDTH), dtype=np.float32)
    weight_hh = np.zeros((3 * hidden, hidden), dtype=np.float32)
    for index, gate in enumerate(("reset", "update", "new")):
        weight_ih[index * hidden : (index + 1) * hidden] = xavier_uniform(
            (hidden, RECORD_WIDTH),
            namespace_generator(init_namespace(world_id, seed, component, f"weight_ih_{gate}")),
        )
        weight_hh[index * hidden : (index + 1) * hidden] = orthogonal(
            (hidden, hidden),
            namespace_generator(init_namespace(world_id, seed, component, f"weight_hh_{gate}")),
        )
    bias_ih = np.zeros((3 * hidden,), dtype=np.float32)
    bias_hh = np.zeros((3 * hidden,), dtype=np.float32)
    bias_ih[hidden : 2 * hidden] = 1.0  # input-side UPDATE gate bias only
    return {
        "weight_ih": weight_ih,
        "weight_hh": weight_hh,
        "bias_ih": bias_ih,
        "bias_hh": bias_hh,
    }


def init_transformer(world_id: str, seed: int) -> dict[str, np.ndarray]:
    """One causal pre-LN block, 2 heads, FF width 48, tanh FF.

    Attention-output and FF-output matrices are divided by sqrt(2): the
    registered residual scale, applied after the ordinary Xavier draw.
    """
    component = "backbone_transformer"
    width = CONTEXT_WIDTH
    residual_scale = 1.0 / math.sqrt(2.0)

    def draw(name: str, shape: tuple[int, int]) -> np.ndarray:
        return xavier_uniform(shape, namespace_generator(init_namespace(world_id, seed, component, name)))

    out: dict[str, np.ndarray] = {}
    out["input_weight"] = draw("input_weight", (width, RECORD_WIDTH))
    out["input_bias"] = np.zeros((width,), dtype=np.float32)
    for name in ("q", "k", "v"):
        out[f"{name}_weight"] = draw(f"{name}_weight", (width, width))
        out[f"{name}_bias"] = np.zeros((width,), dtype=np.float32)
    out["attn_out_weight"] = (draw("attn_out_weight", (width, width)) * residual_scale).astype(np.float32)
    out["attn_out_bias"] = np.zeros((width,), dtype=np.float32)
    out["ff_in_weight"] = draw("ff_in_weight", (48, width))
    out["ff_in_bias"] = np.zeros((48,), dtype=np.float32)
    out["ff_out_weight"] = (draw("ff_out_weight", (width, 48)) * residual_scale).astype(np.float32)
    out["ff_out_bias"] = np.zeros((width,), dtype=np.float32)
    for name in ("ln1", "ln2", "ln_final"):
        out[f"{name}_weight"] = np.ones((width,), dtype=np.float32)
        out[f"{name}_bias"] = np.zeros((width,), dtype=np.float32)
    return out


def initial_parameters(arm: str, world_id: str, seed: int) -> dict[str, np.ndarray]:
    if arm == "G":
        backbone = init_gru(world_id, seed)
    elif arm == "T":
        backbone = init_transformer(world_id, seed)
    else:
        raise ValueError(f"Phase A implements only G and T, not {arm!r}")
    parameters = {f"backbone.{key}": value for key, value in backbone.items()}
    parameters.update({f"decoder.{key}": value for key, value in init_decoder(world_id, seed).items()})
    return parameters


# =============================================================================
# PUBLIC RECORD / SEQUENCE CONSTRUCTION (spec section 3 "Causal ordering").
#
# Every sequence is RESET, then (QUERY, OBSERVED) per observed transition, then
# the forecast: QUERY, blank OBSERVED, ..., final QUERY.  The prediction is read
# at that final QUERY, strictly before its blank OBSERVED.  The current target
# OBSERVED record is therefore never constructed at all.
# =============================================================================


@dataclasses.dataclass
class Episodes:
    """Semantic public support data for one world.  No hidden fields exist here."""

    properties: torch.Tensor        # (E, 4, 6) float32
    action_id: torch.Tensor         # (E, 8) int64
    source_id: torch.Tensor         # (E, 8) int64
    destination_id: torch.Tensor    # (E, 8) int64, 4 == NONE
    dose: torch.Tensor              # (E, 8) float32
    sensor: torch.Tensor            # (E, 8) float32
    sensor_present: torch.Tensor    # (E, 8) float32 in {0, 1}
    role: torch.Tensor              # (E,) int64
    episode_index: torch.Tensor     # (E,) int64

    def __len__(self) -> int:
        return int(self.properties.shape[0])

    def select(self, index: torch.Tensor) -> "Episodes":
        return Episodes(
            properties=self.properties[index],
            action_id=self.action_id[index],
            source_id=self.source_id[index],
            destination_id=self.destination_id[index],
            dose=self.dose[index],
            sensor=self.sensor[index],
            sensor_present=self.sensor_present[index],
            role=self.role[index],
            episode_index=self.episode_index[index],
        )

    def data_hash(self) -> str:
        hasher = hashlib.sha256()
        for name in (
            "properties",
            "action_id",
            "source_id",
            "destination_id",
            "dose",
            "sensor",
            "sensor_present",
            "role",
            "episode_index",
        ):
            array = getattr(self, name).cpu().numpy()
            hasher.update(name.encode("utf-8"))
            hasher.update(str(array.dtype.str).encode("utf-8"))
            hasher.update(str(array.shape).encode("utf-8"))
            hasher.update(np.ascontiguousarray(array).tobytes())
        return hasher.hexdigest()


def build_sequences(
    episodes: Episodes,
    prefix_len: torch.Tensor,
    horizon: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return (records, endpoint_index).

    `records` is (N, FIXED_SEQUENCE_LENGTH, 44) float32.  `prefix_len[n]` observed
    transitions carry their real masked measurement; the following `horizon[n]`
    transitions are forecast, so their OBSERVED tokens are blank.  The final QUERY
    of the forecast is at `endpoint_index[n]` and has no OBSERVED token at all.
    """
    count = len(episodes)
    length = FIXED_SEQUENCE_LENGTH
    records = torch.zeros((count, length, RECORD_WIDTH), dtype=torch.float32)

    flat_properties = episodes.properties.reshape(count, N_OBJECTS * N_PROPERTIES)
    # Properties are static and public: present on every record, including RESET.
    records[:, :, SLICE_PROPERTIES] = flat_properties[:, None, :]

    # RESET at index 0: the action and source one-hots stay all zero,
    # but the destination one-hot IS set, to NONE: the spec says "All zero at
    # RESET" for action and source only, and "NONE for noncontact actions and
    # RESET" for destination.  Ruling B4 confirms this encoding.
    records[:, 0, SLICE_DESTINATION.start + DESTINATION_NONE] = 1.0
    records[:, 0, SLICE_RECORD_TYPE.start + RECORD_TYPE_RESET] = 1.0

    endpoint = torch.zeros((count,), dtype=torch.int64)
    for n in range(count):
        observed = int(prefix_len[n])
        steps = int(horizon[n])
        total = observed + steps
        if total > N_TRANSITIONS:
            raise ValueError(f"prefix {observed} + horizon {steps} exceeds {N_TRANSITIONS}")
        for t in range(total):
            query_at = 1 + 2 * t
            observed_at = query_at + 1
            is_forecast = t >= observed
            action = int(episodes.action_id[n, t])
            source = int(episodes.source_id[n, t])
            destination = int(episodes.destination_id[n, t])
            dose = float(episodes.dose[n, t])

            def write_action(row: int) -> None:
                records[n, row, SLICE_ACTION.start + action] = 1.0
                records[n, row, SLICE_SOURCE.start + source] = 1.0
                records[n, row, SLICE_DESTINATION.start + destination] = 1.0
                records[n, row, SLICE_DOSE.start] = dose

            write_action(query_at)
            records[n, query_at, SLICE_RECORD_TYPE.start + RECORD_TYPE_QUERY] = 1.0
            # sensor and sensor_present stay zero on a QUERY token.

            if t == total - 1:
                endpoint[n] = query_at
                break  # the target OBSERVED record is never built.

            records[n, observed_at, SLICE_RECORD_TYPE.start + RECORD_TYPE_OBSERVED] = 1.0
            if BLANK_OBSERVED_KEEPS_ACTION_FIELDS:
                write_action(observed_at)
            else:  # pragma: no cover - alternative reading, not the registered one
                if not is_forecast:
                    write_action(observed_at)
            if not is_forecast:
                present = float(episodes.sensor_present[n, t])
                records[n, observed_at, SLICE_SENSOR.start] = float(episodes.sensor[n, t]) * present
                records[n, observed_at, SLICE_PRESENT.start] = present
            # A forecast OBSERVED token keeps sensor = 0 and present = 0: no
            # teacher forcing, no predicted sensor value, no future mask.
    return records, endpoint


def build_query_features(properties: torch.Tensor, query_a: torch.Tensor, query_b: torch.Tensor) -> torch.Tensor:
    """The non-context part of the decoder input: p[a], p[b], onehot(a), onehot(b).

    Width 4 + 4 + 6 + 6 + 4 + 5 = 29; the pool coordinate slices z[a], z[b] are
    exactly zero for the ordinary baselines (spec section 6).
    """
    count = properties.shape[0]
    z_a = torch.zeros((count, POOL_COORDINATES_MAX), dtype=torch.float32)
    z_b = torch.zeros((count, POOL_COORDINATES_MAX), dtype=torch.float32)
    p_a = properties[torch.arange(count), query_a]
    is_none = query_b == QUERY_B_NONE
    safe_b = torch.where(is_none, torch.zeros_like(query_b), query_b)
    p_b = properties[torch.arange(count), safe_b]
    p_b = torch.where(is_none[:, None], torch.zeros_like(p_b), p_b)
    onehot_a = torch.zeros((count, QUERY_A_WIDTH), dtype=torch.float32)
    onehot_a[torch.arange(count), query_a] = 1.0
    onehot_b = torch.zeros((count, QUERY_B_WIDTH), dtype=torch.float32)
    onehot_b[torch.arange(count), query_b] = 1.0
    return torch.cat([z_a, z_b, p_a, p_b, onehot_a, onehot_b], dim=-1)


# =============================================================================
# LANE-BATCHED MODELS.
#
# Every parameter carries a LEADING LANE DIMENSION L.  One lane == one
# (world, seed) fit.  Lanes share no parameter, no Adam moment, no gradient, no
# normalization statistic and no random draw; batching is purely an execution
# optimization, exactly as the build plan requires.
# =============================================================================

LAYERNORM_EPS = 1e-5
N_HEADS = 2
HEAD_DIM = CONTEXT_WIDTH // N_HEADS
FF_WIDTH = 48


def laned_linear(x: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor) -> torch.Tensor:
    """x (L, ..., in) @ weight (L, out, in)^T + bias (L, out)."""
    if x.dim() == 3:
        out = torch.einsum("lni,loi->lno", x, weight)
        return out + bias[:, None, :]
    if x.dim() == 4:
        out = torch.einsum("lnti,loi->lnto", x, weight)
        return out + bias[:, None, None, :]
    raise ValueError(f"unsupported rank {x.dim()}")


def laned_layer_norm(x: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor) -> torch.Tensor:
    mean = x.mean(dim=-1, keepdim=True)
    variance = x.var(dim=-1, unbiased=False, keepdim=True)
    normed = (x - mean) * torch.rsqrt(variance + LAYERNORM_EPS)
    return normed * weight[:, None, None, :] + bias[:, None, None, :]


def causal_mask(length: int) -> torch.Tensor:
    """Lower-triangular attention mask.

    CAUSAL_ATTENTION_INCLUDES_SELF keeps the diagonal: a QUERY token carries its
    action but never a result, so attending to itself cannot leak the target.
    """
    mask = torch.ones((length, length), dtype=torch.bool).tril(
        diagonal=0 if CAUSAL_ATTENTION_INCLUDES_SELF else -1
    )
    return mask


def _gather_endpoint(stacked: torch.Tensor, endpoint: torch.Tensor, width: int) -> torch.Tensor:
    """Read the context at each sequence's final QUERY.

    `endpoint` may be (N,) when every lane shares an endpoint, or (L, N) when each
    lane drew its own endpoint.  The gather is lane-aware either way, so a lane
    never reads another lane's position.
    """
    lanes, count = stacked.shape[0], stacked.shape[1]
    if endpoint.dim() == 1:
        endpoint = endpoint.unsqueeze(0).expand(lanes, count)
    index = endpoint.reshape(lanes, count, 1, 1).expand(lanes, count, 1, width)
    return stacked.gather(2, index).squeeze(2)


def gru_context(parameters: dict[str, torch.Tensor], records: torch.Tensor, endpoint: torch.Tensor) -> torch.Tensor:
    """PyTorch-equivalent GRU cell, gate order r / z / n, two bias vectors."""
    lanes, count, length, _ = records.shape
    hidden = CONTEXT_WIDTH
    weight_ih = parameters["backbone.weight_ih"]
    weight_hh = parameters["backbone.weight_hh"]
    bias_ih = parameters["backbone.bias_ih"]
    bias_hh = parameters["backbone.bias_hh"]
    state = torch.zeros((lanes, count, hidden), dtype=records.dtype)
    outputs = []
    gates_input_all = torch.einsum("lnti,loi->lnto", records, weight_ih) + bias_ih[:, None, None, :]
    for step in range(length):
        gates_input = gates_input_all[:, :, step, :]
        gates_hidden = torch.einsum("lni,loi->lno", state, weight_hh) + bias_hh[:, None, :]
        i_r, i_z, i_n = gates_input.split(hidden, dim=-1)
        h_r, h_z, h_n = gates_hidden.split(hidden, dim=-1)
        reset = torch.sigmoid(i_r + h_r)
        update = torch.sigmoid(i_z + h_z)
        candidate = torch.tanh(i_n + reset * h_n)
        state = (1.0 - update) * candidate + update * state
        outputs.append(state)
    stacked = torch.stack(outputs, dim=2)  # (L, N, T, hidden)
    return _gather_endpoint(stacked, endpoint, hidden)


_POSITION_TABLE = sinusoidal_positions(MAX_RECORDS, CONTEXT_WIDTH)


def transformer_context(
    parameters: dict[str, torch.Tensor], records: torch.Tensor, endpoint: torch.Tensor
) -> torch.Tensor:
    """One causal pre-LN block, 2 heads, FF width 48 with tanh, final LayerNorm."""
    lanes, count, length, _ = records.shape
    x = laned_linear(records, parameters["backbone.input_weight"], parameters["backbone.input_bias"])
    x = x + _POSITION_TABLE[:length].to(x.dtype)[None, None, :, :]

    normed = laned_layer_norm(x, parameters["backbone.ln1_weight"], parameters["backbone.ln1_bias"])
    query = laned_linear(normed, parameters["backbone.q_weight"], parameters["backbone.q_bias"])
    key = laned_linear(normed, parameters["backbone.k_weight"], parameters["backbone.k_bias"])
    value = laned_linear(normed, parameters["backbone.v_weight"], parameters["backbone.v_bias"])

    def heads(tensor: torch.Tensor) -> torch.Tensor:
        return tensor.view(lanes, count, length, N_HEADS, HEAD_DIM).permute(0, 1, 3, 2, 4)

    query, key, value = heads(query), heads(key), heads(value)
    scores = torch.einsum("lnhtd,lnhsd->lnhts", query, key) / math.sqrt(HEAD_DIM)
    mask = causal_mask(length).to(scores.device)
    scores = scores.masked_fill(~mask[None, None, None, :, :], float("-inf"))
    weights = torch.softmax(scores, dim=-1)
    attended = torch.einsum("lnhts,lnhsd->lnhtd", weights, value)
    attended = attended.permute(0, 1, 3, 2, 4).reshape(lanes, count, length, CONTEXT_WIDTH)
    x = x + laned_linear(
        attended, parameters["backbone.attn_out_weight"], parameters["backbone.attn_out_bias"]
    )

    normed = laned_layer_norm(x, parameters["backbone.ln2_weight"], parameters["backbone.ln2_bias"])
    hidden = torch.tanh(
        laned_linear(normed, parameters["backbone.ff_in_weight"], parameters["backbone.ff_in_bias"])
    )
    x = x + laned_linear(hidden, parameters["backbone.ff_out_weight"], parameters["backbone.ff_out_bias"])
    x = laned_layer_norm(x, parameters["backbone.ln_final_weight"], parameters["backbone.ln_final_bias"])

    return _gather_endpoint(x, endpoint, CONTEXT_WIDTH)


def decode(parameters: dict[str, torch.Tensor], context: torch.Tensor, query_features: torch.Tensor) -> torch.Tensor:
    """Shared decoder: Linear(53, 16), tanh, Linear(16, 1).  Unbounded scalar."""
    lanes = context.shape[0]
    if query_features.dim() == 2:
        query_features = query_features.unsqueeze(0).expand(lanes, -1, -1)
    features = torch.cat([context, query_features], dim=-1)
    hidden = torch.tanh(
        laned_linear(features, parameters["decoder.hidden_weight"], parameters["decoder.hidden_bias"])
    )
    return laned_linear(hidden, parameters["decoder.out_weight"], parameters["decoder.out_bias"]).squeeze(-1)


def forward(
    arm: str,
    parameters: dict[str, torch.Tensor],
    records: torch.Tensor,
    endpoint: torch.Tensor,
    query_features: torch.Tensor,
) -> torch.Tensor:
    """Prediction at the final QUERY of each sequence.  Shape (L, N)."""
    if arm == "G":
        context = gru_context(parameters, records, endpoint)
    elif arm == "T":
        context = transformer_context(parameters, records, endpoint)
    else:
        raise ValueError(f"Phase A implements only G and T, not {arm!r}")
    return decode(parameters, context, query_features)


# =============================================================================
# PER-LANE ADAMW.
#
# torch.optim.AdamW plus torch.nn.utils.clip_grad_norm_ would compute ONE global
# gradient norm across every lane, silently coupling independent worlds.  This
# implementation keeps the norm, the moments and the step scaling strictly
# per lane, and holds no state that a lane could read from another lane.
# =============================================================================


class LanedAdamW:
    """AdamW matching torch's decoupled-decay formulation, one lane at a time."""

    def __init__(self, parameters: dict[str, torch.Tensor], lanes: int):
        self.parameters = parameters
        self.lanes = lanes
        self.step_count = 0
        self.moment1 = {name: torch.zeros_like(tensor) for name, tensor in parameters.items()}
        self.moment2 = {name: torch.zeros_like(tensor) for name, tensor in parameters.items()}

    @staticmethod
    def decays(name: str, tensor: torch.Tensor) -> bool:
        """Weight decay on matrix weights only (2-D once the lane dim is removed)."""
        return (tensor.dim() - 1) >= WEIGHT_DECAY_ON_NDIM

    def learning_rate(self) -> float:
        update = self.step_count + 1  # one-based index of the update about to run
        if update <= WARMUP_UPDATES:
            return BASE_LR * update / WARMUP_UPDATES
        return BASE_LR

    def clip_per_lane(self) -> torch.Tensor:
        squared = torch.zeros((self.lanes,), dtype=torch.float32)
        for tensor in self.parameters.values():
            if tensor.grad is None:
                continue
            squared = squared + tensor.grad.detach().pow(2).reshape(self.lanes, -1).sum(dim=1)
        norm = squared.sqrt()
        coefficient = (GRAD_CLIP_NORM / (norm + 1e-6)).clamp(max=1.0)
        for tensor in self.parameters.values():
            if tensor.grad is None:
                continue
            shape = [self.lanes] + [1] * (tensor.dim() - 1)
            tensor.grad.mul_(coefficient.view(shape))
        return norm

    @torch.no_grad()
    def step(self) -> dict[str, float]:
        norm = self.clip_per_lane()
        lr = self.learning_rate()
        self.step_count += 1
        bias1 = 1.0 - ADAM_BETA1**self.step_count
        bias2 = 1.0 - ADAM_BETA2**self.step_count
        for name, tensor in self.parameters.items():
            grad = tensor.grad
            if grad is None:
                continue
            if self.decays(name, tensor):
                tensor.mul_(1.0 - lr * WEIGHT_DECAY)
            self.moment1[name].mul_(ADAM_BETA1).add_(grad, alpha=1.0 - ADAM_BETA1)
            self.moment2[name].mul_(ADAM_BETA2).addcmul_(grad, grad, value=1.0 - ADAM_BETA2)
            denominator = (self.moment2[name].sqrt() / math.sqrt(bias2)).add_(ADAM_EPS)
            tensor.addcdiv_(self.moment1[name], denominator, value=-lr / bias1)
        return {"learning_rate": lr, "grad_norm_mean": float(norm.mean())}

    def zero_grad(self) -> None:
        for tensor in self.parameters.values():
            tensor.grad = None

    def state(self) -> dict[str, Any]:
        return {
            "step_count": self.step_count,
            "moment1": {name: tensor.clone() for name, tensor in self.moment1.items()},
            "moment2": {name: tensor.clone() for name, tensor in self.moment2.items()},
        }

    def load_state(self, state: dict[str, Any]) -> None:
        self.step_count = int(state["step_count"])
        for name in self.moment1:
            self.moment1[name].copy_(state["moment1"][name])
            self.moment2[name].copy_(state["moment2"][name])


# =============================================================================
# LOSS AND MINIBATCH SAMPLING (prereg section 3).
# =============================================================================


def normalized_squared_error(prediction: torch.Tensor, target: torch.Tensor, present: torch.Tensor) -> torch.Tensor:
    """(prediction - observed_sensor)^2 / 0.25 on present endpoints only.

    A minibatch with no present endpoint yields exactly zero loss; it consumes its
    scheduled work and is logged, and is never redrawn.
    """
    squared = (prediction - target).pow(2) / LOSS_NORMALIZER
    masked = squared * present
    count = present.sum(dim=-1)
    total = masked.sum(dim=-1)
    return torch.where(count > 0, total / count.clamp(min=1.0), torch.zeros_like(total))


def horizon_for_update(global_update_index: int) -> int:
    index = global_update_index if HORIZON_CYCLE_IS_ZERO_BASED else global_update_index + 1
    return HORIZONS[index % len(HORIZONS)]


def sample_minibatch(
    world_id: str, seed: int, rung_budget: int, update_index: int, n_fit_episodes: int, horizon: int
) -> tuple[np.ndarray, np.ndarray]:
    """Draw MINIBATCH_EPISODES episodes with replacement, then an endpoint each.

    The stream is the registered `fit/{world}/{seed}/{rung}/{update}` namespace, so
    a lane's draws depend on nothing but its own identity: resumption is exact and
    lanes cannot influence each other.
    """
    generator = namespace_generator(fit_namespace(world_id, seed, rung_budget, update_index))
    assert MINIBATCH_DRAW_ORDER == ("episodes", "endpoints")
    episodes = generator.integers(0, n_fit_episodes, size=MINIBATCH_EPISODES)
    endpoints = generator.integers(horizon, N_TRANSITIONS + 1, size=MINIBATCH_EPISODES)
    return episodes, endpoints


# =============================================================================
# OPERATION-COST LEDGER (prereg section 3, build plan section 3).
#
# DECLARED ENGINEERING CONVENTIONS, not a measurement of elapsed time or energy.
# A multiply and an add count as two operations, as registered.  Every non-MAC
# operator cost below is declared here and applied identically to both arms.
# =============================================================================

OPS_PER_MAC = 2
OPS_BIAS_ADD = 1
OPS_TANH = 4
OPS_SIGMOID = 4
OPS_LAYERNORM_PER_ELEMENT = 7      # mean, centred square, sum, rsqrt, scale, shift
OPS_SOFTMAX_PER_ELEMENT = 5        # max, subtract, exp, sum, divide
OPS_ELEMENTWISE = 1
BACKWARD_MULTIPLIER = 2.0          # declared: backward is twice the forward cost
OPS_ADAMW_PER_PARAMETER = 11       # decay, two moment updates, bias corrections, step
OPS_GRADCLIP_PER_PARAMETER = 3     # square, accumulate, rescale
# Ruling A1 reconciliation: the reviewed table charged neither initialization nor
# loss computation nor the INITIAL query panel.  All three are declared here and
# charged both in the frozen reservation and in the executed ledger.
OPS_INIT_PER_PARAMETER = 2         # draw one value and write it
OPS_LOSS_PER_TARGET = 4            # subtract, square, divide by 0.25, accumulate
OPS_LOSS_PER_BATCH = 2             # count the present targets and divide by it


def linear_ops(tokens: int, fan_in: int, fan_out: int) -> int:
    return tokens * (fan_in * fan_out * OPS_PER_MAC + fan_out * OPS_BIAS_ADD)


def decoder_ops() -> dict[str, int]:
    return {
        "decoder.hidden": linear_ops(1, DECODER_INPUT_WIDTH, DECODER_HIDDEN),
        "decoder.tanh": DECODER_HIDDEN * OPS_TANH,
        "decoder.out": linear_ops(1, DECODER_HIDDEN, 1),
    }


def gru_ops(tokens: int) -> dict[str, int]:
    hidden = CONTEXT_WIDTH
    return {
        "gru.input_gates": linear_ops(tokens, RECORD_WIDTH, 3 * hidden),
        "gru.hidden_gates": linear_ops(tokens, hidden, 3 * hidden),
        "gru.reset_gate": tokens * hidden * (OPS_ELEMENTWISE + OPS_SIGMOID),
        "gru.update_gate": tokens * hidden * (OPS_ELEMENTWISE + OPS_SIGMOID),
        "gru.candidate": tokens * hidden * (2 * OPS_ELEMENTWISE + OPS_TANH),
        "gru.state_blend": tokens * hidden * 4 * OPS_ELEMENTWISE,
    }


def transformer_ops(tokens: int) -> dict[str, int]:
    width = CONTEXT_WIDTH
    pairs = tokens * tokens if COST_COUNTS_DENSE_ATTENTION else tokens * (tokens + 1) // 2
    return {
        "transformer.input_projection": linear_ops(tokens, RECORD_WIDTH, width),
        "transformer.position_add": tokens * width * OPS_ELEMENTWISE,
        "transformer.layer_norm_1": tokens * width * OPS_LAYERNORM_PER_ELEMENT,
        "transformer.qkv": 3 * linear_ops(tokens, width, width),
        "transformer.scores": N_HEADS * pairs * HEAD_DIM * OPS_PER_MAC + N_HEADS * pairs * OPS_ELEMENTWISE,
        "transformer.softmax": N_HEADS * pairs * OPS_SOFTMAX_PER_ELEMENT,
        "transformer.attend": N_HEADS * pairs * HEAD_DIM * OPS_PER_MAC,
        "transformer.attention_output": linear_ops(tokens, width, width),
        "transformer.residual_1": tokens * width * OPS_ELEMENTWISE,
        "transformer.layer_norm_2": tokens * width * OPS_LAYERNORM_PER_ELEMENT,
        "transformer.feedforward_in": linear_ops(tokens, width, FF_WIDTH),
        "transformer.feedforward_tanh": tokens * FF_WIDTH * OPS_TANH,
        "transformer.feedforward_out": linear_ops(tokens, FF_WIDTH, width),
        "transformer.residual_2": tokens * width * OPS_ELEMENTWISE,
        "transformer.layer_norm_final": tokens * width * OPS_LAYERNORM_PER_ELEMENT,
    }


def operator_cost_table(arm: str, tokens: int = FIXED_SEQUENCE_LENGTH) -> dict[str, int]:
    """Operator-level forward cost for ONE sequence of `tokens` records."""
    table = gru_ops(tokens) if arm == "G" else transformer_ops(tokens)
    table.update(decoder_ops())
    return table


def forward_ops(arm: str, sequences: int = 1, tokens: int = FIXED_SEQUENCE_LENGTH) -> int:
    return sequences * sum(operator_cost_table(arm, tokens).values())


def parameter_total(arm: str) -> int:
    return SPEC_PARAMETER_COUNTS[arm]


def loss_ops(targets: int, batches: int = 1) -> int:
    """Normalized-squared-error computation for `targets` scored predictions."""
    return targets * OPS_LOSS_PER_TARGET + batches * OPS_LOSS_PER_BATCH


def initialization_ops(arm: str) -> int:
    """Drawing and writing one fit's initial parameter bytes."""
    return parameter_total(arm) * OPS_INIT_PER_PARAMETER


def update_ops(arm: str) -> int:
    """One complete optimizer update: forward, loss, backward, clip and AdamW."""
    forward = forward_ops(arm, sequences=MINIBATCH_EPISODES) + loss_ops(MINIBATCH_EPISODES)
    backward = int(round(forward * BACKWARD_MULTIPLIER))
    parameters = parameter_total(arm)
    optimizer = parameters * (OPS_ADAMW_PER_PARAMETER + OPS_GRADCLIP_PER_PARAMETER)
    return forward + backward + optimizer


def selection_targets(budget: int) -> int:
    """Upper bound: one forecast per eligible horizon per selection episode."""
    return ((budget // N_TRANSITIONS) // EPISODE_GROUP) * len(HORIZONS)


def audit_targets(budget: int) -> int:
    """Upper bound: the LARGEST LEGAL fitting audit set at this budget.

    Ruling A1: largest-legal-audit-set reservations are acceptable for
    data-independent step allocation, but they are UPPER BOUNDS, not consumed
    operations.  The executed ledger charges the shapes actually run.
    """
    episodes = budget // N_TRANSITIONS
    fit_episodes = episodes - episodes // EPISODE_GROUP
    return fit_episodes * len(HORIZONS)


def selection_ops(arm: str, budget: int) -> int:
    return forward_ops(arm, sequences=selection_targets(budget))


def audit_ops(arm: str, budget: int) -> int:
    return forward_ops(arm, sequences=audit_targets(budget))


QUERY_PANEL_TARGETS = 96  # spec section 4: 96 target predictions per world


def query_panel_ops(arm: str) -> int:
    return forward_ops(arm, sequences=QUERY_PANEL_TARGETS)


def rung_reservation(arm: str, budget: int, index: int) -> dict[str, int]:
    """Every non-fitting model operation charged to this rung, itemised.

    Ruling A1 reconciliation.  The reviewed table reserved the initial fitting
    audit at rung 1 but charged neither initialization, nor the INITIAL QUERY
    PANEL that the calibration gate needs for initial query E, nor loss
    computation.  All of them are itemised here, and `Runner` charges the same
    categories against the shapes it actually executes.
    """
    last = len(BUDGETS) - 1
    parts: dict[str, int] = {
        "selection_forward": selection_ops(arm, budget),
        "selection_loss": loss_ops(selection_targets(budget), len(HORIZONS)),
        "rung_query_panel_forward": query_panel_ops(arm),
    }
    if index == 0:
        parts["initialization"] = initialization_ops(arm)
        parts["initial_audit_forward"] = audit_ops(arm, BUDGETS[last])
        parts["initial_audit_loss"] = loss_ops(audit_targets(BUDGETS[last]), len(HORIZONS))
        parts["initial_query_panel_forward"] = query_panel_ops(arm)
    if index == last:
        parts["final_audit_forward"] = audit_ops(arm, BUDGETS[last])
        parts["final_audit_loss"] = loss_ops(audit_targets(BUDGETS[last]), len(HORIZONS))
    return parts


def step_table(arm: str, tier: str = DEFAULT_TIER) -> list[dict[str, Any]]:
    """Frozen per-rung step counts for one source tier.

    Ruling A2/A3: BOTH tiers' tables are frozen before the first fit.  Nothing
    here can depend on learning success or on the data, so the table is fixed
    before any accuracy run and is identical for L and H apart from the allowance.
    """
    if tier not in TIER_ALLOWANCE_PER_RUNG:
        raise ValueError(f"unknown source tier {tier!r}; registered tiers are {TIERS}")
    allowance = TIER_ALLOWANCE_PER_RUNG[tier]
    rows = []
    per_update = update_ops(arm)
    for index, budget in enumerate(BUDGETS):
        parts = rung_reservation(arm, budget, index)
        reserved = sum(parts.values())
        steps = int((allowance - reserved) // per_update)
        rows.append(
            {
                "tier": tier,
                "budget": budget,
                "allowance": allowance,
                "reserved_ops": reserved,
                "reserved_by_category": parts,
                "ops_per_update": per_update,
                "steps": max(steps, 0),
                "fitting_ops": max(steps, 0) * per_update,
                "counted_total_ops": max(steps, 0) * per_update + reserved,
            }
        )
    return rows


def cumulative_steps(arm: str, tier: str = DEFAULT_TIER) -> list[int]:
    total = 0
    out = []
    for row in step_table(arm, tier):
        total += int(row["steps"])
        out.append(total)
    return out


def cross_arm_gap(values: dict[str, float]) -> float:
    """Relative gap between arms, 0 when every arm counts the same work."""
    finite = [float(value) for value in values.values() if math.isfinite(float(value))]
    if not finite or max(finite) <= 0.0:
        return 0.0
    return (max(finite) - min(finite)) / max(finite)


def planned_cross_arm_use(tier: str = DEFAULT_TIER) -> list[dict[str, Any]]:
    """Ruling A1: the 5% cross-arm rule, checked at EVERY rung, not on the total.

    This is the PLANNED (reservation) view.  `actual_cross_arm_use` applies the
    identical test to the operations a completed run really executed.
    """
    tables = {arm: step_table(arm, tier) for arm in ARMS}
    rows = []
    for index, budget in enumerate(BUDGETS):
        by_arm = {arm: float(tables[arm][index]["counted_total_ops"]) for arm in ARMS}
        gap = cross_arm_gap(by_arm)
        rows.append(
            {
                "tier": tier,
                "budget": budget,
                "counted_total_ops_by_arm": by_arm,
                "relative_gap": gap,
                "within_5_percent": gap <= CROSS_ARM_MAX_RELATIVE_GAP,
            }
        )
    return rows


def actual_cross_arm_use(counted_by_arm_by_rung: dict[str, dict[int, float]]) -> list[dict[str, Any]]:
    """The same 5% test applied per rung to EXECUTED operations from run ledgers.

    `counted_by_arm_by_rung[arm][budget]` is that arm's counted operations for one
    fit at that rung, taken from `run_fit`'s ledger.
    """
    rows = []
    for budget in BUDGETS:
        by_arm = {
            arm: float(counted_by_arm_by_rung[arm][budget])
            for arm in counted_by_arm_by_rung
            if budget in counted_by_arm_by_rung[arm]
        }
        if len(by_arm) < 2:
            continue
        gap = cross_arm_gap(by_arm)
        rows.append(
            {
                "budget": budget,
                "counted_total_ops_by_arm": by_arm,
                "relative_gap": gap,
                "within_5_percent": gap <= CROSS_ARM_MAX_RELATIVE_GAP,
            }
        )
    return rows


# =============================================================================
# START-UP CLASSIFICATION HOOK (prereg section 8), implemented exactly as
# written.  Fitting E and query E are EVALUATOR-ONLY quantities computed from
# noise-free responses, which the trainer must never hold; the trainer therefore
# records the training-label loss reduction and the audit-set predictions, and
# this pure function resolves the label once the evaluator supplies E.
# =============================================================================

STARTUP_LABELS = (
    "numerical_failure",
    "infrastructure_incomplete",
    "initially_at_floor",
    "never_started",
    "started_not_yet_learned",
    "learned_and_failed_to_transfer",
    "learned_with_generalization",
    "pending_evaluator_E",
)


def classify_startup(
    initial_fitting_loss: float,
    final_fitting_loss: float,
    fitting_E: float | None = None,
    query_E: float | None = None,
    numerical_failure: bool = False,
    infrastructure_incomplete: bool = False,
) -> str:
    if numerical_failure:
        return "numerical_failure"
    if infrastructure_incomplete:
        return "infrastructure_incomplete"
    if not math.isfinite(initial_fitting_loss) or not math.isfinite(final_fitting_loss):
        return "numerical_failure"
    if initial_fitting_loss <= STARTUP_INITIAL_FLOOR_LOSS:
        return "initially_at_floor"
    if fitting_E is None or query_E is None:
        return "pending_evaluator_E"
    # Ruling C9, the exact registered predicate, evaluated in binary64:
    #     never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)
    # so L_initial = 1.0, L_final = 0.90 is NOT never_started even though
    # 1.0 - 0.90 evaluates to 0.09999999999999998.  The tolerance applies to the
    # relative improvement ONLY; no other E threshold gets one.
    improvement = (initial_fitting_loss - final_fitting_loss) / initial_fitting_loss
    if (
        improvement < STARTUP_MIN_RELATIVE_IMPROVEMENT - STARTUP_IMPROVEMENT_TOLERANCE
        and fitting_E >= STARTUP_NEVER_STARTED_FITTING_E
    ):
        return "never_started"
    if fitting_E > STARTUP_LEARNED_FITTING_E:
        return "started_not_yet_learned"
    if query_E > STARTUP_TRANSFER_QUERY_E:
        return "learned_and_failed_to_transfer"
    return "learned_with_generalization"


def relative_improvement(initial_fitting_loss: float, final_fitting_loss: float) -> float:
    if initial_fitting_loss <= 0.0 or not math.isfinite(initial_fitting_loss):
        return float("nan")
    return (initial_fitting_loss - final_fitting_loss) / initial_fitting_loss


def audit_set(
    episodes: Episodes, role: int = EPISODE_ROLE_FIT
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Deterministic audit endpoints: each fit episode, each horizon, its LAST
    eligible observed endpoint.  Returns (episode_index, prefix_len, horizon).

    The same set is used at initialization and at the B=512 endpoint; cases are
    never chosen by difficulty.
    """
    rows_episode: list[int] = []
    rows_prefix: list[int] = []
    rows_horizon: list[int] = []
    for n in range(len(episodes)):
        if int(episodes.role[n]) != role:
            continue
        for horizon in HORIZONS:
            chosen = None
            for t in range(N_TRANSITIONS, horizon - 1, -1):
                if float(episodes.sensor_present[n, t - 1]) > 0.0:
                    chosen = t
                    break
            if chosen is None:
                continue
            rows_episode.append(n)
            rows_prefix.append(chosen - horizon)
            rows_horizon.append(horizon)
    return (
        torch.tensor(rows_episode, dtype=torch.int64),
        torch.tensor(rows_prefix, dtype=torch.int64),
        torch.tensor(rows_horizon, dtype=torch.int64),
    )


# =============================================================================
# PUBLIC DATA LOADING.  Only public tensors and observed fitting targets cross
# this boundary; a file carrying anything else is refused, so the trainer can
# never be handed hidden responses, coefficients, families or world identity.
# =============================================================================


def _refuse_private_fields(present: set[str], allowed: frozenset[str], path: str) -> None:
    extra = sorted(present - set(allowed))
    if extra:
        raise ValueError(
            f"{path} carries fields outside the public contract: {extra}. "
            "The trainer must never receive evaluator-side data."
        )


def load_support_semantic_fixture(path: str | os.PathLike[str]) -> Episodes:
    """FIXTURE / TEST ONLY.  Per-transition semantic .npz support episodes.

    Ruling C11: the amended SCHEMA.md is the SINGLE serialized-data contract and
    the registered driver must use its boundary-checked public path.  This
    semantic-array reader may remain, but only for fixtures and tests: it is
    unreachable from `run_fit` / `run_predict`, because `load_world_support`
    refuses it unless a caller passes `allow_semantic_fixture=True`, which no
    production entry point does.  Two independently selected production formats
    can silently change interpretation even when one fixture agrees.
    """
    path = str(path)
    with np.load(path, allow_pickle=False) as handle:
        present = set(handle.files)
        _refuse_private_fields(present, SUPPORT_FILE_ALLOWED_KEYS, path)
        data = {key: handle[key] for key in handle.files}
    count = data[PUBLIC_KEYS["properties"]].shape[0]
    role = data.get(PUBLIC_KEYS["episode_role"])
    if role is None:
        index = np.arange(count)
        role = np.where(index % EPISODE_GROUP == SELECTION_INDEX_IN_GROUP, EPISODE_ROLE_SELECTION, EPISODE_ROLE_FIT)
    episode_index = data.get(PUBLIC_KEYS["episode_index"], np.arange(count))
    return Episodes(
        properties=torch.tensor(data[PUBLIC_KEYS["properties"]], dtype=torch.float32),
        action_id=torch.tensor(data[PUBLIC_KEYS["action_id"]], dtype=torch.int64),
        source_id=torch.tensor(data[PUBLIC_KEYS["source_id"]], dtype=torch.int64),
        destination_id=torch.tensor(data[PUBLIC_KEYS["destination_id"]], dtype=torch.int64),
        dose=torch.tensor(data[PUBLIC_KEYS["dose"]], dtype=torch.float32),
        sensor=torch.tensor(data[PUBLIC_KEYS["sensor"]], dtype=torch.float32),
        sensor_present=torch.tensor(data[PUBLIC_KEYS["sensor_present"]], dtype=torch.float32),
        role=torch.tensor(np.asarray(role), dtype=torch.int64),
        episode_index=torch.tensor(np.asarray(episode_index), dtype=torch.int64),
    )


def support_path(data_dir: str | os.PathLike[str], world_id: str) -> pathlib.Path:
    return pathlib.Path(data_dir) / world_id / "discovery.npz"


def load_world_support(
    data_dir: str | os.PathLike[str], world_id: str, allow_semantic_fixture: bool = False
) -> Episodes:
    """THE registered production loader (ruling C11).

    Reads ONLY the serialized SCHEMA.md layout.  The semantic-array adapter is
    reachable from here solely under an explicit `allow_semantic_fixture=True`,
    which `run_fit` and `run_predict` never pass, so a registered run cannot
    silently take the second format's interpretation.
    """
    world_dir = pathlib.Path(data_dir) / world_id
    if (world_dir / AGENT1_FILES["support_records"]).exists():
        return load_support_agent1(world_dir)
    if allow_semantic_fixture:
        return load_support_semantic_fixture(support_path(data_dir, world_id))
    raise ValueError(
        f"{world_dir} has no {AGENT1_FILES['support_records']}. Ruling C11: the "
        "registered driver reads only the serialized SCHEMA.md layout; the "
        "semantic-array adapter is fixture-only and is not reachable from fit or "
        "predict on registered data."
    )


def prefix_episodes(episodes: Episodes, budget: int) -> Episodes:
    """Nested prefix: the first budget/8 episodes, in their registered order."""
    wanted = budget // N_TRANSITIONS
    order = torch.argsort(episodes.episode_index)
    return episodes.select(order[:wanted])


def split_roles(episodes: Episodes) -> tuple[Episodes, Episodes]:
    fit = episodes.select(torch.nonzero(episodes.role == EPISODE_ROLE_FIT, as_tuple=True)[0])
    selection = episodes.select(torch.nonzero(episodes.role == EPISODE_ROLE_SELECTION, as_tuple=True)[0])
    return fit, selection


# =============================================================================
# RUNNER: independent per-world / per-seed fitting with optional vectorised lanes.
# =============================================================================


@dataclasses.dataclass
class Lane:
    world_id: str
    seed: int
    episodes: Episodes          # the full B=512 support for this world
    # The published query panel for this world, exactly as the SCHEMA path
    # returns it: (record_ids, records, endpoint, features).  Holding it here
    # lets the ledger charge the INITIAL and per-rung query panels as executed
    # work (ruling A1) and lets the fit save the predictions the evaluator needs
    # to finalise without another fit (ruling C10).  It contains no truth.
    query: tuple[list[str], torch.Tensor, torch.Tensor, torch.Tensor] | None = None

    @property
    def key(self) -> str:
        return f"{self.world_id}/seed{self.seed}"


def batch_from_requests(
    episodes: Episodes,
    episode_index: torch.Tensor,
    prefix_len: torch.Tensor,
    horizon: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Build (records, endpoint, query_features, target, present) for one lane.

    The detector query for task A is (a = last_action.source, b = NONE), so the
    target is the measurement produced by the very action whose QUERY we read.
    """
    chosen = episodes.select(episode_index)
    records, endpoint = build_sequences(chosen, prefix_len, horizon)
    count = len(chosen)
    rows = torch.arange(count)
    last_transition = prefix_len + horizon - 1
    query_a = chosen.source_id[rows, last_transition]
    query_b = torch.full((count,), QUERY_B_NONE, dtype=torch.int64)
    query_features = build_query_features(chosen.properties, query_a, query_b)
    target = chosen.sensor[rows, last_transition]
    present = chosen.sensor_present[rows, last_transition]
    return records, endpoint, query_features, target, present


class Runner:
    """Fits one arm across `lanes` independent (world, seed) lanes."""

    def __init__(self, arm: str, lanes: list[Lane]):
        if arm not in ARMS:
            raise ValueError(f"Phase A implements only {ARMS}, not {arm!r}")
        self.arm = arm
        self.lanes = lanes
        self.n_lanes = len(lanes)
        per_lane = [initial_parameters(arm, lane.world_id, lane.seed) for lane in lanes]
        names = list(per_lane[0])
        self.parameters = {}
        for name in names:
            stacked = np.stack([entry[name] for entry in per_lane], axis=0)
            tensor = torch.tensor(stacked, dtype=torch.float32, requires_grad=True)
            self.parameters[name] = tensor
        self.initial_hashes = {name: tensor_hash(tensor) for name, tensor in self.parameters.items()}
        self.optimizer = LanedAdamW(self.parameters, self.n_lanes)
        self.rung_index = 0
        self.update_in_rung = 0
        # Ruling A1: the ledger charges EXECUTED work, itemised, including
        # initialization, loss computation and every evaluation pass by purpose.
        self.work: dict[str, Any] = {
            "initialization_ops": float(initialization_ops(arm) * self.n_lanes),
            "forward_ops": 0.0,
            "backward_ops": 0.0,
            "loss_ops": 0.0,
            "optimizer_ops": 0.0,
            "evaluation_ops": 0.0,
            "evaluation_loss_ops": 0.0,
            "evaluation_ops_by_purpose": {},
            "updates": 0,
            "useful_updates": 0,
            "lane_updates": 0,
            "useful_lane_updates": 0,
            "examples": 0,
            "observed_targets": 0,
            "empty_minibatches": 0,
            "evaluation_forward_sequences": 0,
        }

    def _charge_evaluation(self, purpose: str, sequences: int, targets: int, batches: int) -> None:
        """Charge one evaluation pass at the shape it ACTUALLY executed.

        `sequences` counts real padding too, because padding is what the kernel
        runs (rulings A1 and C7).  Reservations are reconciled against these
        numbers in `run_fit`, and any unused reservation is reported separately
        rather than spent on extra fitting.
        """
        forward = float(forward_ops(self.arm, sequences=sequences))
        loss = float(loss_ops(targets, batches))
        self.work["evaluation_ops"] += forward
        self.work["evaluation_loss_ops"] += loss
        self.work["evaluation_forward_sequences"] += sequences
        bucket = self.work["evaluation_ops_by_purpose"]
        bucket[purpose] = bucket.get(purpose, 0.0) + forward + loss

    def counted_total_ops(self) -> float:
        """Every model operation this runner has executed, all lanes."""
        return float(
            self.work["initialization_ops"]
            + self.work["forward_ops"]
            + self.work["backward_ops"]
            + self.work["loss_ops"]
            + self.work["optimizer_ops"]
            + self.work["evaluation_ops"]
            + self.work["evaluation_loss_ops"]
        )

    # -- forward helpers -----------------------------------------------------

    def _stack_requests(
        self, requests: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        parts = [batch_from_requests(lane.episodes, *request) for lane, request in zip(self.lanes, requests)]
        records = torch.stack([part[0] for part in parts], dim=0)
        endpoint = torch.stack([part[1] for part in parts], dim=0)  # (L, N), lane-aware
        query_features = torch.stack([part[2] for part in parts], dim=0)
        target = torch.stack([part[3] for part in parts], dim=0)
        present = torch.stack([part[4] for part in parts], dim=0)
        return records, endpoint, query_features, target, present

    def predict_batch(
        self, records: torch.Tensor, endpoint: torch.Tensor, query_features: torch.Tensor
    ) -> torch.Tensor:
        return forward(self.arm, self.parameters, records, endpoint, query_features)

    # -- one optimizer update ------------------------------------------------

    def update(self, rung_budget: int, global_update_index: int) -> dict[str, Any]:
        horizon = horizon_for_update(global_update_index)
        requests = []
        for lane in self.lanes:
            prefix = prefix_episodes(lane.episodes, rung_budget)
            fit_episodes, _ = split_roles(prefix)
            episodes_drawn, endpoints_drawn = sample_minibatch(
                lane.world_id, lane.seed, rung_budget, global_update_index, len(fit_episodes), horizon
            )
            index_in_full = torch.nonzero(prefix.role == EPISODE_ROLE_FIT, as_tuple=True)[0][
                torch.tensor(episodes_drawn, dtype=torch.int64)
            ]
            order = torch.argsort(lane.episodes.episode_index)[: rung_budget // N_TRANSITIONS]
            requests.append(
                (
                    order[index_in_full],
                    torch.tensor(endpoints_drawn, dtype=torch.int64) - horizon,
                    torch.full((MINIBATCH_EPISODES,), horizon, dtype=torch.int64),
                )
            )
        records, endpoint, query_features, target, present = self._stack_requests(requests)
        prediction = self.predict_batch(records, endpoint, query_features)
        loss_per_lane = normalized_squared_error(prediction, target, present)
        self.optimizer.zero_grad()
        loss_per_lane.sum().backward()
        stats = self.optimizer.step()

        forward_cost = forward_ops(self.arm, sequences=MINIBATCH_EPISODES) * self.n_lanes
        loss_cost = float(loss_ops(MINIBATCH_EPISODES) * self.n_lanes)
        self.work["forward_ops"] += forward_cost
        self.work["loss_ops"] += loss_cost
        self.work["backward_ops"] += (forward_cost + loss_cost) * BACKWARD_MULTIPLIER
        self.work["optimizer_ops"] += (
            parameter_total(self.arm) * (OPS_ADAMW_PER_PARAMETER + OPS_GRADCLIP_PER_PARAMETER) * self.n_lanes
        )
        self.work["updates"] += 1
        self.work["lane_updates"] += self.n_lanes
        self.work["examples"] += MINIBATCH_EPISODES * self.n_lanes
        observed = int(present.sum())
        self.work["observed_targets"] += observed
        # Ruling C6: an all-absent minibatch is KEPT.  It consumes its scheduled
        # update and is logged as empty rather than redrawn, so "useful updates"
        # (at least one present target) is reported separately from "updates".
        empty = int((present.sum(dim=-1) == 0).sum())
        self.work["empty_minibatches"] += empty
        self.work["useful_lane_updates"] += self.n_lanes - empty
        self.work["useful_updates"] += 1 if empty < self.n_lanes else 0
        return {
            "horizon": horizon,
            "loss_per_lane": [float(value) for value in loss_per_lane.detach()],
            "empty_minibatches": empty,
            **stats,
        }

    # -- evaluation ----------------------------------------------------------

    @torch.no_grad()
    def audit_pass(
        self, budget: int, role: int = EPISODE_ROLE_FIT, purpose: str = "audit"
    ) -> tuple[list[float], list[dict[str, dict[str, float]]]]:
        """Training-label loss AND keyed predictions on the deterministic audit set.

        Lanes can have different numbers of eligible endpoints because their
        observation masks differ, so shorter lanes are padded with repeats whose
        present flag is forced to zero.  Padding changes no lane's value, and the
        padded shape is what the ledger charges (rulings A1 and C7).

        Rulings C10 and C11: the second return value is, per lane, a dictionary
        keyed by the amended SCHEMA.md join key (built by `audit_key`, which
        defers to the public loader) -- a stable world/episode/horizon/endpoint
        key -- holding the prediction, the observed training label and its
        present flag, so the evaluator can join its noise-free truth without
        another fit.
        """
        totals = [0.0] * self.n_lanes
        counts = [0] * self.n_lanes
        keyed: list[dict[str, dict[str, float]]] = [{} for _ in range(self.n_lanes)]
        for horizon in HORIZONS:
            per_lane: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = []
            for lane in self.lanes:
                prefix = prefix_episodes(lane.episodes, budget)
                episode_index, prefix_len, horizons = audit_set(prefix, role)
                keep = horizons == horizon
                order = torch.argsort(lane.episodes.episode_index)[: budget // N_TRANSITIONS]
                per_lane.append((order[episode_index[keep]], prefix_len[keep], horizons[keep]))
            widest = max(int(request[0].shape[0]) for request in per_lane)
            if widest == 0:
                continue
            valid = torch.zeros((self.n_lanes, widest), dtype=torch.float32)
            padded: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = []
            for lane_index, (episodes_i, prefix_i, horizon_i) in enumerate(per_lane):
                have = int(episodes_i.shape[0])
                valid[lane_index, :have] = 1.0
                if have == 0:
                    filler = torch.zeros((widest,), dtype=torch.int64)
                    padded.append(
                        (filler, filler.clone(), torch.full((widest,), horizon, dtype=torch.int64))
                    )
                    continue
                pad = widest - have
                padded.append(
                    (
                        torch.cat([episodes_i, episodes_i[:1].repeat(pad)]),
                        torch.cat([prefix_i, prefix_i[:1].repeat(pad)]),
                        torch.cat([horizon_i, horizon_i[:1].repeat(pad)]),
                    )
                )
            records, endpoint, query_features, target, present = self._stack_requests(padded)
            present = present * valid
            prediction = self.predict_batch(records, endpoint, query_features)
            squared = (prediction - target).pow(2) / LOSS_NORMALIZER * present
            self._charge_evaluation(
                purpose,
                sequences=widest * self.n_lanes,
                targets=widest * self.n_lanes,
                batches=self.n_lanes,
            )
            for lane_index in range(self.n_lanes):
                totals[lane_index] += float(squared[lane_index].sum())
                counts[lane_index] += int(present[lane_index].sum())
                episodes_i, prefix_i, _ = per_lane[lane_index]
                for position in range(int(episodes_i.shape[0])):
                    key = audit_key(
                        world_public_id=self.lanes[lane_index].world_id,
                        episode_index=int(
                            self.lanes[lane_index].episodes.episode_index[int(episodes_i[position])]
                        ),
                        horizon=horizon,
                        endpoint=int(prefix_i[position]) + horizon,
                    )
                    keyed[lane_index][key] = {
                        "prediction": float(prediction[lane_index, position]),
                        "observed_target": float(target[lane_index, position]),
                        "present": float(present[lane_index, position]),
                    }
        losses = [
            totals[index] / counts[index] if counts[index] > 0 else float("nan")
            for index in range(self.n_lanes)
        ]
        return losses, keyed

    def audit_loss(self, budget: int, role: int = EPISODE_ROLE_FIT, purpose: str = "audit") -> list[float]:
        return self.audit_pass(budget, role, purpose)[0]

    @torch.no_grad()
    def query_pass(self, purpose: str) -> list[dict[str, float]] | None:
        """Run each lane's published query panel through that lane's parameters.

        Ruling A1 required the INITIAL query panel to be charged as well as the
        per-rung panels; ruling C10 requires the initial and final predictions to
        be saved.  Returns one record-ID-keyed dictionary per lane, or None when
        the data directory published no panel (a fixture without queries).
        """
        if any(lane.query is None for lane in self.lanes):
            return None
        records = torch.stack([lane.query[1] for lane in self.lanes], dim=0)
        endpoint = torch.stack([lane.query[2] for lane in self.lanes], dim=0)
        features = torch.stack([lane.query[3] for lane in self.lanes], dim=0)
        prediction = self.predict_batch(records, endpoint, features)
        count = int(records.shape[1])
        # No loss: the trainer holds no query truth, so nothing is scored here.
        self._charge_evaluation(purpose, sequences=count * self.n_lanes, targets=0, batches=0)
        return [
            {
                record_id: float(value)
                for record_id, value in zip(lane.query[0], prediction[lane_index])
            }
            for lane_index, lane in enumerate(self.lanes)
        ]

    # -- checkpointing -------------------------------------------------------

    def lane_checkpoint(
        self, lane_index: int, rung_budget: int, completed_rung: bool, tier: str = DEFAULT_TIER
    ) -> dict[str, Any]:
        state = self.optimizer.state()
        return {
            "format": "ct20-phaseA-checkpoint-v1",
            "contract_version": CONTRACT_VERSION,
            "experiment_version": EXPERIMENT_VERSION,
            "rulings_sha256": RULINGS_SHA256,
            "tier": tier,
            "arm": self.arm,
            "world_id": self.lanes[lane_index].world_id,
            "seed": self.lanes[lane_index].seed,
            "rung_budget": rung_budget,
            "rung_index": self.rung_index,
            "update_in_rung": self.update_in_rung,
            "completed_rung": bool(completed_rung),
            "optimizer_step_count": state["step_count"],
            "parameters": {
                name: tensor.detach()[lane_index : lane_index + 1].clone()
                for name, tensor in self.parameters.items()
            },
            "moment1": {name: tensor[lane_index : lane_index + 1].clone() for name, tensor in state["moment1"].items()},
            "moment2": {name: tensor[lane_index : lane_index + 1].clone() for name, tensor in state["moment2"].items()},
            "initial_parameter_hashes": self.initial_hashes,
            "data_prefix_hash": prefix_episodes(self.lanes[lane_index].episodes, rung_budget).data_hash(),
            "work": dict(self.work),
        }

    def load_lane_checkpoints(self, checkpoints: list[dict[str, Any]]) -> None:
        if len(checkpoints) != self.n_lanes:
            raise ValueError("one checkpoint per lane is required for exact resumption")
        state = {"step_count": checkpoints[0]["optimizer_step_count"], "moment1": {}, "moment2": {}}
        for name in self.parameters:
            with torch.no_grad():
                self.parameters[name].copy_(
                    torch.cat([entry["parameters"][name] for entry in checkpoints], dim=0)
                )
            state["moment1"][name] = torch.cat([entry["moment1"][name] for entry in checkpoints], dim=0)
            state["moment2"][name] = torch.cat([entry["moment2"][name] for entry in checkpoints], dim=0)
        self.optimizer.load_state(state)
        if bool(checkpoints[0].get("completed_rung", True)):
            # The saved rung finished: restart the cursor at the NEXT rung.
            self.rung_index = int(checkpoints[0]["rung_index"]) + 1
            self.update_in_rung = 0
        else:
            # Interrupted mid rung: resume that same rung at its exact cursor.
            self.rung_index = int(checkpoints[0]["rung_index"])
            self.update_in_rung = int(checkpoints[0]["update_in_rung"])
        self.work = dict(checkpoints[0]["work"])


# =============================================================================
# FIT DRIVER.
# =============================================================================


def output_root(out_dir: str | os.PathLike[str], tier: str, arm: str, world_id: str, seed: int) -> pathlib.Path:
    """Ruling A3: the two tiers have SEPARATE output IDs and ledgers."""
    if tier not in TIER_ALLOWANCE_PER_RUNG:
        raise ValueError(f"unknown source tier {tier!r}; registered tiers are {TIERS}")
    return pathlib.Path(out_dir) / f"tier{tier}" / arm / world_id / f"seed{seed}"


def checkpoint_path(
    out_dir: str | os.PathLike[str],
    arm: str,
    world_id: str,
    seed: int,
    budget: int,
    tier: str = DEFAULT_TIER,
) -> pathlib.Path:
    return output_root(out_dir, tier, arm, world_id, seed) / f"rung{budget}.pt"


def predictions_path(
    out_dir: str | os.PathLike[str], arm: str, world_id: str, seed: int, tier: str = DEFAULT_TIER
) -> pathlib.Path:
    return output_root(out_dir, tier, arm, world_id, seed) / "predictions.json"


def _purpose_rung_index(purpose: str) -> int:
    """Attribute one executed evaluation pass to the rung that reserved it."""
    last = len(BUDGETS) - 1
    if purpose.startswith("initial_"):
        return 0
    if purpose.startswith("final_"):
        return last
    for marker in ("selection_rung", "query_panel_rung"):
        if purpose.startswith(marker):
            budget = int(purpose[len(marker) :])
            return BUDGETS.index(budget)
    return 0


def peak_memory_bytes() -> int:
    """Peak resident set size.  macOS reports ru_maxrss in BYTES, Linux in KiB;
    verified against `ps -o rss=` on this Mac before use."""
    usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return usage if sys.platform == "darwin" else usage * 1024


def run_fit(
    arm: str,
    data_dir: str,
    world_ids: list[str],
    seeds: list[int],
    budget: int,
    out_dir: str,
    budget_seconds: float | None = None,
    resume: bool = False,
    vectorise: bool = True,
    ledger_path: str | None = None,
    override_step_table: list[int] | None = None,
    tier: str = DEFAULT_TIER,
) -> dict[str, Any]:
    """`override_step_table` is a TEST/DEBUG hook only.  It is not reachable from
    the CLI, and any run that uses it records `step_table_overridden: true`, so a
    tampered schedule can never be mistaken for the registered one.

    `tier` selects a REGISTERED source tier (ruling A2).  Tier H is a fresh
    complete trajectory from the same saved initialization bytes with Adam and the
    global update counter reset, never a resume of tier L: `resume` only ever
    looks inside this tier's own output root.
    """
    started = time.time()
    if tier not in TIER_ALLOWANCE_PER_RUNG:
        raise ValueError(f"unknown source tier {tier!r}; registered tiers are {TIERS}")
    # Ruling C11: the production path, never the semantic fixture adapter.
    supports = {world_id: load_world_support(data_dir, world_id) for world_id in world_ids}
    panels = {}
    for world_id in world_ids:
        world_dir = pathlib.Path(data_dir) / world_id
        panels[world_id] = (
            load_queries_agent1(world_dir)
            if (world_dir / AGENT1_FILES["query_records"]).exists()
            else None
        )
    lanes = [
        Lane(world_id, seed, supports[world_id], panels[world_id])
        for world_id in world_ids
        for seed in seeds
    ]
    if not vectorise and len(lanes) > 1:
        reports = []
        for lane in lanes:
            reports.append(
                run_fit(
                    arm,
                    data_dir,
                    [lane.world_id],
                    [lane.seed],
                    budget,
                    out_dir,
                    budget_seconds,
                    resume,
                    True,
                    ledger_path,
                    override_step_table,
                    tier,
                )
            )
        return {"mode": "unvectorised", "tier": tier, "reports": reports}

    runner = Runner(arm, lanes)
    table = step_table(arm, tier)
    if override_step_table is not None:
        table = [dict(row, steps=int(count)) for row, count in zip(table, override_step_table)]
    last_budget = max(b for b in BUDGETS if b <= budget)
    audit_budget = min(BUDGETS[-1], last_budget)

    resumed_from = None
    if resume:
        for candidate in reversed([b for b in BUDGETS if b <= budget]):
            paths = [
                checkpoint_path(out_dir, arm, lane.world_id, lane.seed, candidate, tier) for lane in lanes
            ]
            if all(path.exists() for path in paths):
                checkpoints = [torch.load(path, weights_only=False) for path in paths]
                foreign = sorted({str(entry.get("tier", DEFAULT_TIER)) for entry in checkpoints} - {tier})
                if foreign:
                    raise ValueError(
                        f"refusing to resume tier {tier} from tier {foreign} checkpoints: ruling A3 "
                        "forbids extending one tier's trajectory and calling it the other's budget curve"
                    )
                runner.load_lane_checkpoints(checkpoints)
                resumed_from = candidate
                break

    # Ruling A1/C10: the INITIAL audit and the INITIAL query panel both run here,
    # before any update, and both are charged and saved.
    initial_audit = None
    initial_audit_keyed: list[dict[str, dict[str, float]]] | None = None
    initial_queries = None
    if resumed_from is None:
        initial_audit, initial_audit_keyed = runner.audit_pass(
            audit_budget, purpose="initial_fitting_audit"
        )
        initial_queries = runner.query_pass("initial_query_panel")

    ledger: list[dict[str, Any]] = []
    deadline_hit = False
    numerical_failure = False
    rung_queries: dict[int, list[dict[str, float]] | None] = {}
    selection_by_rung: dict[int, list[float]] = {}
    update_losses: list[dict[str, Any]] = []
    # ct20-v1.2: the largest rung budget this call actually ran, so the saved
    # `query_predictions_final` comes from the LAST EXECUTED rung rather than assuming 512.
    last_rung_budget: int | None = None

    for rung_index in range(runner.rung_index, len(BUDGETS)):
        rung_budget = BUDGETS[rung_index]
        if rung_budget > budget:
            break
        runner.rung_index = rung_index
        last_rung_budget = rung_budget
        planned = int(table[rung_index]["steps"])
        rung_started = time.time()
        while runner.update_in_rung < planned:
            if budget_seconds is not None and (time.time() - started) >= budget_seconds:
                deadline_hit = True
                break
            info = runner.update(rung_budget, runner.optimizer.step_count)
            update_losses.append(
                {
                    "rung_budget": rung_budget,
                    "global_update": runner.optimizer.step_count - 1,
                    "horizon": info["horizon"],
                    "learning_rate": info["learning_rate"],
                    "loss_per_lane": info["loss_per_lane"],
                    "empty_minibatches": info["empty_minibatches"],
                }
            )
            if any(not math.isfinite(value) for value in info["loss_per_lane"]):
                numerical_failure = True
                break
            runner.update_in_rung += 1
        selection = runner.audit_loss(
            rung_budget, role=EPISODE_ROLE_SELECTION, purpose=f"selection_rung{rung_budget}"
        )
        selection_by_rung[rung_budget] = selection
        rung_queries[rung_budget] = runner.query_pass(f"query_panel_rung{rung_budget}")
        # Ruling A1: this rung's frozen RESERVATION.  The executed counterpart is
        # filled in after the final audit, below, and the difference is reported
        # as an unused reservation -- never spent on extra fitting.
        reserved_parts = rung_reservation(arm, rung_budget, rung_index)
        reserved = float(sum(reserved_parts.values()))
        for lane_index, lane in enumerate(lanes):
            record = runner.lane_checkpoint(
                lane_index, rung_budget, completed_rung=runner.update_in_rung >= planned, tier=tier
            )
            path = checkpoint_path(out_dir, arm, lane.world_id, lane.seed, rung_budget, tier)
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(record, path)
            fitting_ops = (
                runner.work["forward_ops"]
                + runner.work["backward_ops"]
                + runner.work["loss_ops"]
                + runner.work["optimizer_ops"]
            ) / len(lanes)
            ledger.append(
                {
                    "experiment_version": EXPERIMENT_VERSION,
                    "rulings_sha256": RULINGS_SHA256,
                    "tier": tier,
                    "world_id": lane.world_id,
                    "seed": lane.seed,
                    "arm": arm,
                    "rung_budget": rung_budget,
                    "candidate_k": 0,
                    "data_prefix_hash": record["data_prefix_hash"],
                    "checkpoint_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "selection_loss": selection[lane_index],
                    "trainable_parameters": parameter_total(arm),
                    "persistent_bytes": parameter_total(arm) * 4,
                    "working_history_bytes": MAX_RECORDS * RECORD_WIDTH * 4,
                    "updates": runner.work["updates"],
                    "useful_updates": runner.work["useful_updates"],
                    "lane_updates": runner.work["lane_updates"] / len(lanes),
                    "useful_lane_updates": runner.work["useful_lane_updates"] / len(lanes),
                    "examples": runner.work["examples"] / len(lanes),
                    "observed_targets": runner.work["observed_targets"] / len(lanes),
                    "empty_minibatches": runner.work["empty_minibatches"] / len(lanes),
                    "initialization_ops": runner.work["initialization_ops"] / len(lanes),
                    "forward_ops": runner.work["forward_ops"] / len(lanes),
                    "backward_ops": runner.work["backward_ops"] / len(lanes),
                    "loss_ops": runner.work["loss_ops"] / len(lanes),
                    "optimizer_ops": runner.work["optimizer_ops"] / len(lanes),
                    "evaluation_ops": runner.work["evaluation_ops"] / len(lanes),
                    "evaluation_loss_ops": runner.work["evaluation_loss_ops"] / len(lanes),
                    "cumulative_counted_ops": runner.counted_total_ops() / len(lanes),
                    "cumulative_fitting_ops": fitting_ops,
                    "rung_allowance": TIER_ALLOWANCE_PER_RUNG[tier],
                    "rung_reserved_ops": reserved,
                    "rung_reserved_by_category": reserved_parts,
                    "rung_index": rung_index,
                    "planned_steps": planned,
                    "completed_steps_in_rung": runner.update_in_rung,
                    "wall_seconds": time.time() - rung_started,
                    "status": (
                        "numerical_failure"
                        if numerical_failure
                        else ("infrastructure_incomplete" if runner.update_in_rung < planned else "complete")
                    ),
                }
            )
        if deadline_hit or numerical_failure:
            break
        runner.update_in_rung = 0

    final_audit, final_audit_keyed = runner.audit_pass(audit_budget, purpose="final_fitting_audit")
    # ct20-v1.2 (rulings 3 section 1.1, condition 6).  ct20-v1.1 ran a SEVENTH query panel
    # here -- `runner.query_pass("final_query_panel")` -- on parameters unchanged since
    # `query_panel_rung{last}` and after that rung's checkpoint was already written.  The
    # registered schedule has SIX panels per fit (one initial + one per rung: rulings 1 A,
    # prereg section 3, rulings 2 R5), and no reservation line existed for a seventh, so the
    # executed charge carried the last rung over its allowance.  The pass produced no
    # information: its output was bit-identical to the last rung's panel in 12/12 fixture
    # fits.  The C10 artefact key is KEPT and filled from the last EXECUTED rung's panel --
    # `last_rung_budget`, not BUDGETS[-1], so a call with budget < 512 behaves as it did in
    # v1.1.  No `final_query_panel` purpose may ever appear in evaluation_ops_by_purpose.
    final_queries = rung_queries.get(last_rung_budget) if last_rung_budget is not None else None

    # Ruling A1 reconciliation, now that every evaluation pass has run: attribute
    # each executed non-fitting charge to its rung and report the unused
    # reservation separately from the consumed operations.
    executed_by_rung: dict[int, float] = {}
    for purpose, ops in runner.work["evaluation_ops_by_purpose"].items():
        index = _purpose_rung_index(purpose)
        executed_by_rung[index] = executed_by_rung.get(index, 0.0) + float(ops) / len(lanes)
    executed_by_rung[0] = executed_by_rung.get(0, 0.0) + float(initialization_ops(arm))
    for entry in ledger:
        index = int(entry["rung_index"])
        executed = executed_by_rung.get(index, 0.0)
        entry["rung_executed_non_fitting_ops"] = executed
        entry["rung_unused_reservation_ops"] = float(entry["rung_reserved_ops"]) - executed
        entry["rung_counted_total_ops"] = executed + float(entry["planned_steps"]) * update_ops(arm)
        entry["rung_within_allowance"] = (
            entry["rung_counted_total_ops"] <= TIER_ALLOWANCE_PER_RUNG[tier]
        )

    report = {
        "contract_version": CONTRACT_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "rulings_sha256": RULINGS_SHA256,
        "tier": tier,
        "tier_allowance_per_rung": TIER_ALLOWANCE_PER_RUNG[tier],
        "tier_allowance_per_fit": TIER_ALLOWANCE_PER_FIT[tier],
        "arm": arm,
        "budget": budget,
        "audit_budget": audit_budget,
        "resumed_from": resumed_from,
        "step_table_overridden": override_step_table is not None,
        "deadline_hit": deadline_hit,
        "numerical_failure": numerical_failure,
        "wall_seconds": time.time() - started,
        "peak_memory_bytes": peak_memory_bytes(),
        "work": {key: value for key, value in runner.work.items()},
        "counted_total_ops_per_fit": runner.counted_total_ops() / len(lanes),
        "query_panel_executed": final_queries is not None,
        "lanes": [],
        "ledger": ledger,
    }
    for lane_index, lane in enumerate(lanes):
        initial = initial_audit[lane_index] if initial_audit is not None else float("nan")
        final = final_audit[lane_index]
        label = classify_startup(
            initial,
            final,
            numerical_failure=numerical_failure,
            infrastructure_incomplete=deadline_hit,
        )
        # Ruling C10: everything the evaluator needs to finalise WITHOUT another
        # fit -- initial and final audit predictions under stable
        # episode/horizon/endpoint keys, the observed losses, and the initial and
        # final query predictions under the panel's opaque record IDs.  No truth,
        # no noise-free response and no V ever enters this file.
        payload = {
            "experiment_version": EXPERIMENT_VERSION,
            "contract_version": CONTRACT_VERSION,
            "rulings_sha256": RULINGS_SHA256,
            "audit_key_format": AUDIT_KEY_FORMAT,
            "tier": tier,
            "arm": arm,
            "world_id": lane.world_id,
            "seed": lane.seed,
            "audit_budget": audit_budget,
            "audit_predictions_initial": (
                initial_audit_keyed[lane_index] if initial_audit_keyed is not None else None
            ),
            "audit_predictions_final": final_audit_keyed[lane_index],
            "query_predictions_initial": (
                initial_queries[lane_index] if initial_queries is not None else None
            ),
            "query_predictions_final": (
                final_queries[lane_index] if final_queries is not None else None
            ),
            "query_predictions_by_rung": {
                str(rung): (values[lane_index] if values is not None else None)
                for rung, values in rung_queries.items()
            },
            "observed_losses": {
                "fit_audit_initial": initial,
                "fit_audit_final": final,
                "selection_by_rung": {
                    str(rung): values[lane_index] for rung, values in selection_by_rung.items()
                },
                "updates": [
                    {
                        "rung_budget": row["rung_budget"],
                        "global_update": row["global_update"],
                        "horizon": row["horizon"],
                        "learning_rate": row["learning_rate"],
                        "loss": row["loss_per_lane"][lane_index],
                    }
                    for row in update_losses
                ],
            },
            "startup_label": label,
            "startup_label_is_final": bool(numerical_failure or deadline_hit),
        }
        predictions_file = predictions_path(out_dir, arm, lane.world_id, lane.seed, tier)
        predictions_file.parent.mkdir(parents=True, exist_ok=True)
        with open(predictions_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        report["lanes"].append(
            {
                "world_id": lane.world_id,
                "seed": lane.seed,
                # Startup hook, prereg section 8, ruling C10.  Fitting E and query
                # E are evaluator-only; the label resolves once the evaluator joins
                # its noise-free responses to the saved predictions.  A pending
                # label is acceptable here but may NOT remain pending in a
                # completed report, and it never authorises extra updates or a
                # selective restart.
                "fit_audit_loss_initial": initial,
                "fit_audit_loss_final": final,
                "fit_audit_relative_improvement": relative_improvement(initial, final),
                "startup_label": label,
                "startup_label_is_final": numerical_failure or deadline_hit,
                "predictions_file": str(predictions_file),
                "predictions_sha256": hashlib.sha256(predictions_file.read_bytes()).hexdigest(),
            }
        )
    if ledger_path:
        with open(ledger_path, "a", encoding="utf-8") as handle:
            for entry in ledger:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return report


# =============================================================================
# PREDICT: public query records in, predictions keyed by opaque record ID out.
# The trainer holds no simulator and no evaluator object at any point.
# =============================================================================


def load_queries_semantic_fixture(path: str | os.PathLike[str]) -> tuple[list[str], Episodes, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """FIXTURE / TEST ONLY (ruling C11), like `load_support_semantic_fixture`."""
    path = str(path)
    with np.load(path, allow_pickle=False) as handle:
        _refuse_private_fields(set(handle.files), QUERY_FILE_ALLOWED_KEYS, path)
        data = {key: handle[key] for key in handle.files}
    count = data[PUBLIC_KEYS["properties"]].shape[0]
    record_ids = [str(value) for value in data[PUBLIC_KEYS["record_id"]]]
    episodes = Episodes(
        properties=torch.tensor(data[PUBLIC_KEYS["properties"]], dtype=torch.float32),
        action_id=torch.tensor(data[PUBLIC_KEYS["action_id"]], dtype=torch.int64),
        source_id=torch.tensor(data[PUBLIC_KEYS["source_id"]], dtype=torch.int64),
        destination_id=torch.tensor(data[PUBLIC_KEYS["destination_id"]], dtype=torch.int64),
        dose=torch.tensor(data[PUBLIC_KEYS["dose"]], dtype=torch.float32),
        sensor=torch.tensor(data[PUBLIC_KEYS["sensor"]], dtype=torch.float32),
        sensor_present=torch.tensor(data[PUBLIC_KEYS["sensor_present"]], dtype=torch.float32),
        role=torch.full((count,), EPISODE_ROLE_FIT, dtype=torch.int64),
        episode_index=torch.arange(count, dtype=torch.int64),
    )
    prefix_len = torch.tensor(data[PUBLIC_KEYS["prefix_len"]], dtype=torch.int64)
    horizon = torch.tensor(data[PUBLIC_KEYS["horizon"]], dtype=torch.int64)
    query_a = torch.tensor(data[PUBLIC_KEYS["query_a"]], dtype=torch.int64)
    query_b = torch.tensor(data[PUBLIC_KEYS["query_b"]], dtype=torch.int64)
    return record_ids, episodes, prefix_len, horizon, query_a, query_b


@torch.no_grad()
def run_predict(
    checkpoint_file: str, queries: str, out_file: str, allow_semantic_fixture: bool = False
) -> dict[str, float]:
    """THE registered prediction entry point (ruling C11).

    `queries` is a world directory in the serialized SCHEMA.md layout.  The
    semantic .npz reader is reachable only under an explicit
    `allow_semantic_fixture=True`, which the CLI never passes.
    """
    path = pathlib.Path(queries)
    if path.is_dir() and (path / AGENT1_FILES["query_records"]).exists():
        return run_predict_agent1(checkpoint_file, str(path), out_file)
    if not allow_semantic_fixture:
        raise ValueError(
            f"{queries} is not a world directory containing "
            f"{AGENT1_FILES['query_records']}. Ruling C11: predict reads only the "
            "serialized SCHEMA.md layout on registered data."
        )
    return run_predict_semantic_fixture(checkpoint_file, str(queries), out_file)


@torch.no_grad()
def run_predict_semantic_fixture(checkpoint_file: str, queries_file: str, out_file: str) -> dict[str, float]:
    """FIXTURE / TEST ONLY (ruling C11)."""
    checkpoint = torch.load(checkpoint_file, weights_only=False)
    arm = checkpoint["arm"]
    parameters = {name: tensor.clone() for name, tensor in checkpoint["parameters"].items()}
    record_ids, episodes, prefix_len, horizon, query_a, query_b = load_queries_semantic_fixture(queries_file)
    records, endpoint = build_sequences(episodes, prefix_len, horizon)
    query_features = build_query_features(episodes.properties, query_a, query_b)
    prediction = forward(arm, parameters, records.unsqueeze(0), endpoint, query_features)
    values = {record_id: float(value) for record_id, value in zip(record_ids, prediction[0])}
    if out_file:
        pathlib.Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "contract_version": CONTRACT_VERSION,
                    "arm": arm,
                    "checkpoint": os.path.basename(checkpoint_file),
                    "predictions": values,
                },
                handle,
                indent=2,
                sort_keys=True,
            )
    return values


@torch.no_grad()
def forecast(
    arm: str,
    parameters: dict[str, torch.Tensor],
    episodes: Episodes,
    prefix_len: torch.Tensor,
    horizon: torch.Tensor,
    query_a: torch.Tensor,
    query_b: torch.Tensor,
) -> torch.Tensor:
    """The spec's roll-forward contract, as a single public entry point.

    Forks after the last real OBSERVED (or RESET), appends each planned action's
    QUERY followed by a BLANK OBSERVED, and reads the prediction at the final
    QUERY before its blank OBSERVED.  No true measurement, predicted sensor
    value, future availability mask, label or hidden state is fed back.

    (The persistent initialize/advance/observe/features handle API of spec
    section 8 belongs to task B and is deliberately NOT built in Phase A.)
    """
    records, endpoint = build_sequences(episodes, prefix_len, horizon)
    features = build_query_features(episodes.properties, query_a, query_b)
    lanes = next(iter(parameters.values())).shape[0]
    return forward(arm, parameters, records.unsqueeze(0).expand(lanes, -1, -1, -1), endpoint, features)


# =============================================================================
# PARAMETER COUNTS, COST REPORT AND TIMING FIXTURE.
# =============================================================================


def count_parameters(arm: str) -> dict[str, Any]:
    parameters = initial_parameters(arm, "contract-check", 20001)
    per_tensor = {name: int(np.prod(value.shape)) for name, value in parameters.items()}
    backbone = sum(value for name, value in per_tensor.items() if name.startswith("backbone."))
    decoder = sum(value for name, value in per_tensor.items() if name.startswith("decoder."))
    total = backbone + decoder
    checks = {
        "decoder_matches_spec_881": decoder == SPEC_PARAMETER_COUNTS["decoder"],
        f"{arm}_total_matches_spec_{SPEC_PARAMETER_COUNTS[arm]}": total == SPEC_PARAMETER_COUNTS[arm],
    }
    if arm == "G":
        checks["gru_backbone_matches_spec_5040"] = backbone == SPEC_PARAMETER_COUNTS["gru_backbone"]
    if arm == "T":
        groups = {
            "T_input_projection": ("backbone.input_weight", "backbone.input_bias"),
            "T_qkv": tuple(f"backbone.{n}_{p}" for n in "qkv" for p in ("weight", "bias")),
            "T_attention_output": ("backbone.attn_out_weight", "backbone.attn_out_bias"),
            "T_feedforward": (
                "backbone.ff_in_weight",
                "backbone.ff_in_bias",
                "backbone.ff_out_weight",
                "backbone.ff_out_bias",
            ),
            "T_block_norms": tuple(
                f"backbone.{n}_{p}" for n in ("ln1", "ln2") for p in ("weight", "bias")
            ),
            "T_final_norm": ("backbone.ln_final_weight", "backbone.ln_final_bias"),
        }
        for label, names in groups.items():
            counted = sum(per_tensor[name] for name in names)
            checks[f"{label}_matches_spec_{SPEC_PARAMETER_COUNTS[label]}"] = (
                counted == SPEC_PARAMETER_COUNTS[label]
            )
    return {
        "arm": arm,
        "per_tensor": per_tensor,
        "backbone": backbone,
        "decoder": decoder,
        "total": total,
        "spec_total": SPEC_PARAMETER_COUNTS[arm],
        "contract_checks": checks,
        "all_contract_checks_pass": all(checks.values()),
    }


def cost_report(arm: str, tier: str = DEFAULT_TIER) -> dict[str, Any]:
    table = step_table(arm, tier)
    return {
        "arm": arm,
        "tier": tier,
        "experiment_version": EXPERIMENT_VERSION,
        "rulings_sha256": RULINGS_SHA256,
        "allowance_per_rung": TIER_ALLOWANCE_PER_RUNG[tier],
        "allowance_per_fit": TIER_ALLOWANCE_PER_FIT[tier],
        "conventions": {
            "ops_per_mac": OPS_PER_MAC,
            "ops_bias_add": OPS_BIAS_ADD,
            "ops_tanh": OPS_TANH,
            "ops_sigmoid": OPS_SIGMOID,
            "ops_layernorm_per_element": OPS_LAYERNORM_PER_ELEMENT,
            "ops_softmax_per_element": OPS_SOFTMAX_PER_ELEMENT,
            "backward_multiplier": BACKWARD_MULTIPLIER,
            "ops_adamw_per_parameter": OPS_ADAMW_PER_PARAMETER,
            "ops_gradclip_per_parameter": OPS_GRADCLIP_PER_PARAMETER,
            "counts_dense_attention": COST_COUNTS_DENSE_ATTENTION,
            "sequence_length": FIXED_SEQUENCE_LENGTH,
            "note": "declared engineering conventions, not elapsed time or energy",
        },
        "operator_table_one_sequence": operator_cost_table(arm),
        "forward_ops_one_sequence": forward_ops(arm),
        "initialization_ops": initialization_ops(arm),
        "ops_per_update": update_ops(arm),
        "selection_ops_by_budget": {budget: selection_ops(arm, budget) for budget in BUDGETS},
        "audit_ops_by_budget": {budget: audit_ops(arm, budget) for budget in BUDGETS},
        "query_panel_ops": query_panel_ops(arm),
        "step_table": table,
        "total_updates_per_fit": sum(int(row["steps"]) for row in table),
        "total_counted_ops_per_fit": sum(float(row["counted_total_ops"]) for row in table),
        "within_per_fit_allowance": sum(float(row["counted_total_ops"]) for row in table)
        <= TIER_ALLOWANCE_PER_FIT[tier],
    }


def synthetic_episodes(count: int, seed: int) -> Episodes:
    """Random plumbing data in the public contract's shapes.  Not learnable, and
    not produced by any simulator: this exists only to time and shape-check."""
    generator = np.random.Generator(np.random.PCG64(seed))
    destination = generator.integers(0, N_OBJECTS + 1, size=(count, N_TRANSITIONS))
    return Episodes(
        properties=torch.tensor(
            generator.uniform(-1.0, 1.0, size=(count, N_OBJECTS, N_PROPERTIES)), dtype=torch.float32
        ),
        action_id=torch.tensor(generator.integers(0, N_ACTIONS, size=(count, N_TRANSITIONS)), dtype=torch.int64),
        source_id=torch.tensor(generator.integers(0, N_OBJECTS, size=(count, N_TRANSITIONS)), dtype=torch.int64),
        destination_id=torch.tensor(destination, dtype=torch.int64),
        dose=torch.tensor(generator.choice([-1.0, 0.0, 1.0], size=(count, N_TRANSITIONS)), dtype=torch.float32),
        sensor=torch.tensor(generator.uniform(-1.0, 1.0, size=(count, N_TRANSITIONS)), dtype=torch.float32),
        sensor_present=torch.tensor(
            (generator.random(size=(count, N_TRANSITIONS)) < 0.75).astype(np.float32), dtype=torch.float32
        ),
        role=torch.tensor(
            np.where(np.arange(count) % EPISODE_GROUP == SELECTION_INDEX_IN_GROUP, EPISODE_ROLE_SELECTION, EPISODE_ROLE_FIT),
            dtype=torch.int64,
        ),
        episode_index=torch.arange(count, dtype=torch.int64),
    )


def timing_fixture(arm: str, lanes: int, seconds: float, budget: int = BUDGETS[-1]) -> dict[str, Any]:
    """Bounded synthetic dry run.  No registered world data, no accuracy choice."""
    episodes = synthetic_episodes(budget // N_TRANSITIONS, seed=7)
    lane_list = [Lane(f"timing-world-{index}", 20001 + index, episodes) for index in range(lanes)]
    runner = Runner(arm, lane_list)
    for warm in range(3):
        runner.update(budget, warm)
    started = time.time()
    updates = 0
    while time.time() - started < seconds:
        runner.update(budget, updates + 3)
        updates += 1
    elapsed = time.time() - started
    evaluation_started = time.time()
    runner.audit_loss(budget)
    evaluation_seconds = time.time() - evaluation_started

    # A full 96-target query panel forward, per lane: the cost the reviewed
    # projection omitted entirely (ruling A1 / the wave-1 preflight requirement).
    panel_episodes = synthetic_episodes(QUERY_PANEL_TARGETS, seed=11)
    panel_records, panel_endpoint = build_sequences(
        panel_episodes,
        torch.full((QUERY_PANEL_TARGETS,), N_TRANSITIONS - 1, dtype=torch.int64),
        torch.ones((QUERY_PANEL_TARGETS,), dtype=torch.int64),
    )
    panel_features = build_query_features(
        panel_episodes.properties,
        torch.zeros((QUERY_PANEL_TARGETS,), dtype=torch.int64),
        torch.full((QUERY_PANEL_TARGETS,), QUERY_B_NONE, dtype=torch.int64),
    )
    for lane_object in lane_list:
        lane_object.query = (
            [f"timing-{index}" for index in range(QUERY_PANEL_TARGETS)],
            panel_records,
            panel_endpoint,
            panel_features,
        )
    panel_started = time.time()
    runner.query_pass("timing_query_panel")
    panel_seconds = time.time() - panel_started

    # Checkpoint and prediction writes, which the wave must also fit.
    with open(os.devnull, "rb"):
        pass
    write_started = time.time()
    scratch = pathlib.Path(
        os.environ.get("TMPDIR", "/tmp")
    ) / f"ct20-timing-{os.getpid()}-{arm}.pt"
    torch.save(runner.lane_checkpoint(0, budget, completed_rung=True, tier=DEFAULT_TIER), scratch)
    write_seconds = time.time() - write_started
    try:
        scratch.unlink()
    except OSError:  # pragma: no cover - best effort cleanup only
        pass

    return {
        "arm": arm,
        "lanes": lanes,
        "measured_seconds": elapsed,
        "updates": updates,
        "updates_per_second_all_lanes": updates / elapsed if elapsed > 0 else float("nan"),
        "lane_updates_per_second": updates * lanes / elapsed if elapsed > 0 else float("nan"),
        "audit_pass_seconds": evaluation_seconds,
        "query_panel_seconds": panel_seconds,
        "checkpoint_write_seconds_per_lane": write_seconds,
        "peak_memory_bytes": peak_memory_bytes(),
    }


WAVE1_WORLDS = 12          # prereg section 5: six train + six validation worlds
WAVE1_SEEDS = 3            # 20001, 20002, 20003
WAVE1_ARMS = ("G", "T")
WAVE1_FITS = WAVE1_WORLDS * WAVE1_SEEDS * len(WAVE1_ARMS)   # 72 independent fits


def wave1_projection(measurements: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """WORST-CASE COMPLETE L+H SCHEDULE for wave 1, from synthetic timing.

    Required before launching tier L (rulings A3 and the fallback paragraph):
    12 worlds x 3 seeds x {G, T} x five nested rungs, BOTH tiers, every scoring
    pass and every write, the existing 1.5x margin and the 300-second reserve,
    against the unchanged 1,200 / 1,500-second limits.  If the worst case does
    not fit, the caller must report `resource-infeasible` BEFORE fitting, and may
    neither omit cells nor silently add another wave.

    `measurements[arm]` must come from timing_fixture at the lane count actually
    planned for the run, so the projection uses the real vectorised shapes.
    """
    lanes_needed = WAVE1_WORLDS * WAVE1_SEEDS
    per_tier: dict[str, Any] = {}
    total = 0.0
    for tier in TIERS:
        per_arm: dict[str, Any] = {}
        tier_total = 0.0
        for arm in WAVE1_ARMS:
            measured = measurements[arm]
            updates = sum(int(row["steps"]) for row in step_table(arm, tier))
            rate = float(measured["updates_per_second_all_lanes"])
            lanes = int(measured["lanes"])
            # scale linearly if the fixture ran fewer lanes than the wave needs
            scale = lanes_needed / lanes
            fit_seconds = updates / rate * scale
            # Evaluation passes actually scheduled per fit: the initial fitting
            # audit, one selection pass per rung, and the final fitting audit.
            # The selection set is smaller than the audit set, so charging it at
            # the audit rate is deliberately conservative.
            audit_passes = 2 + len(BUDGETS)
            evaluation_seconds = float(measured["audit_pass_seconds"]) * scale * audit_passes
            # Query panels: the INITIAL panel, one per rung, and the final panel.
            panel_passes = 2 + len(BUDGETS)
            panel_seconds = float(measured.get("query_panel_seconds", 0.0)) * scale * panel_passes
            # Writes: one checkpoint per rung per fit, plus one predictions file.
            write_seconds = (
                float(measured.get("checkpoint_write_seconds_per_lane", 0.0))
                * lanes_needed
                * (len(BUDGETS) + 1)
            )
            arm_total = fit_seconds + evaluation_seconds + panel_seconds + write_seconds
            per_arm[arm] = {
                "updates_per_fit": updates,
                "measured_lanes": lanes,
                "measured_updates_per_second": rate,
                "projected_fit_seconds": fit_seconds,
                "projected_evaluation_seconds": evaluation_seconds,
                "projected_query_panel_seconds": panel_seconds,
                "projected_write_seconds": write_seconds,
                "projected_arm_seconds": arm_total,
            }
            tier_total += arm_total
        per_tier[tier] = {
            "allowance_per_rung": TIER_ALLOWANCE_PER_RUNG[tier],
            "per_arm": per_arm,
            "projected_tier_seconds": tier_total,
        }
        total += tier_total
    projected = total * WAVE_TIMING_MARGIN
    usable = WAVE_SOFT_COMPUTE_STOP_SECONDS - WAVE_SCORING_RESERVE_SECONDS
    fits = projected <= usable and projected <= WAVE_HARD_DEADLINE_SECONDS
    return {
        "experiment_version": EXPERIMENT_VERSION,
        "rulings_sha256": RULINGS_SHA256,
        "schedule": "worst case: tier L complete, then tier H complete",
        "fits": WAVE1_FITS,
        "fits_per_tier": WAVE1_FITS,
        "lanes_per_arm": lanes_needed,
        "per_tier": per_tier,
        "projected_seconds_raw": total,
        "projected_seconds_with_1_5x_margin": projected,
        "soft_compute_stop_seconds": WAVE_SOFT_COMPUTE_STOP_SECONDS,
        "hard_deadline_seconds": WAVE_HARD_DEADLINE_SECONDS,
        "scoring_reserve_seconds": WAVE_SCORING_RESERVE_SECONDS,
        "usable_seconds": usable,
        "fits_within_wave": fits,
        "verdict": "fits" if fits else "resource-infeasible",
        "note": "projection from a synthetic fixture; no registered wave has been run",
    }


# =============================================================================
# CLI
# =============================================================================


def source_hash() -> str:
    return hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    fit = sub.add_parser("fit", help="independent per-world/per-seed fitting")
    fit.add_argument("--model", choices=ARMS, required=True)
    fit.add_argument("--data", required=True)
    fit.add_argument("--world-ids", nargs="+", required=True)
    fit.add_argument("--budget", type=int, default=BUDGETS[-1], choices=BUDGETS)
    fit.add_argument("--seed", type=int, nargs="+", default=[20001, 20002, 20003])
    fit.add_argument("--out", required=True)
    fit.add_argument("--budget-seconds", type=float, default=None)
    fit.add_argument("--resume", action="store_true")
    fit.add_argument("--no-vectorise", action="store_true")
    fit.add_argument("--ledger", default=None)
    fit.add_argument(
        "--tier",
        choices=TIERS,
        default=DEFAULT_TIER,
        help="registered source tier (ruling A2): L = 2.0e8 ops/rung, H = 1.0e9",
    )

    predict = sub.add_parser("predict", help="forecasts keyed by opaque record ID")
    predict.add_argument("--ckpt", required=True)
    predict.add_argument("--queries", required=True)
    predict.add_argument("--out", required=True)

    counts = sub.add_parser("count-params", help="instantiated counts vs the spec")
    counts.add_argument("--model", choices=ARMS, default=None)

    cost = sub.add_parser("cost", help="operation-cost ledger and frozen step tables")
    cost.add_argument("--model", choices=ARMS, default=None)
    cost.add_argument(
        "--tier",
        choices=TIERS,
        default=None,
        help="one registered tier; omitted, BOTH frozen tables are printed",
    )

    timing = sub.add_parser("timing-fixture", help="bounded synthetic dry-run timing")
    timing.add_argument("--model", choices=ARMS, default=None)
    timing.add_argument("--lanes", type=int, default=36)
    timing.add_argument("--seconds", type=float, default=5.0)
    timing.add_argument("--project-wave1", action="store_true")
    timing.add_argument(
        "--tier",
        choices=TIERS,
        default=None,
        help="ignored for the projection, which always covers the worst-case L+H schedule",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1) if torch.get_num_interop_threads() != 1 else None
    torch.use_deterministic_algorithms(True, warn_only=False)
    parser = build_parser()
    options = parser.parse_args(argv)
    header = {
        "contract_version": CONTRACT_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "rulings_sha256": RULINGS_SHA256,
        "source_sha256": source_hash(),
    }

    if options.command == "fit":
        report = run_fit(
            arm=options.model,
            data_dir=options.data,
            world_ids=options.world_ids,
            seeds=options.seed,
            budget=options.budget,
            out_dir=options.out,
            budget_seconds=options.budget_seconds,
            resume=options.resume,
            vectorise=not options.no_vectorise,
            ledger_path=options.ledger,
            tier=options.tier,
        )
        print(json.dumps({**header, **report}, indent=2, sort_keys=True, default=str))
        return 0

    if options.command == "predict":
        # Ruling C11: the CLI never enables the fixture-only semantic adapter.
        values = run_predict(options.ckpt, options.queries, options.out)
        print(json.dumps({**header, "n_predictions": len(values), "out": options.out}, indent=2))
        return 0

    if options.command == "count-params":
        arms = [options.model] if options.model else list(ARMS)
        payload = {**header, "arms": {arm: count_parameters(arm) for arm in arms}}
        payload["all_contract_checks_pass"] = all(
            entry["all_contract_checks_pass"] for entry in payload["arms"].values()
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["all_contract_checks_pass"] else 1

    if options.command == "cost":
        arms = [options.model] if options.model else list(ARMS)
        tiers = [options.tier] if options.tier else list(TIERS)
        payload = {
            **header,
            "tiers": {
                tier: {
                    "arms": {arm: cost_report(arm, tier) for arm in arms},
                    "cross_arm_use_by_rung": planned_cross_arm_use(tier),
                    "cross_arm_rule_holds_at_every_rung": all(
                        row["within_5_percent"] for row in planned_cross_arm_use(tier)
                    ),
                }
                for tier in tiers
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if options.command == "timing-fixture":
        arms = [options.model] if options.model else list(ARMS)
        measurements = {
            arm: timing_fixture(arm, lanes=options.lanes, seconds=options.seconds) for arm in arms
        }
        payload = {**header, "measurements": measurements}
        infeasible = False
        if options.project_wave1 and set(arms) == set(WAVE1_ARMS):
            projection = wave1_projection(measurements)
            payload["wave1_projection"] = projection
            infeasible = not projection["fits_within_wave"]
        print(json.dumps(payload, indent=2, sort_keys=True))
        if infeasible:
            # The fallback paragraph of the rulings: say so BEFORE fitting.
            print("resource-infeasible", file=sys.stderr)
            return 3
        return 0

    parser.error("unknown command")
    return 2


# The `__main__` guard is at the END of this file, after every definition.  It
# used to sit here, which made `python fable_concepttoy20_models.py fit` raise
# NameError on AGENT1_FILES -- that name is defined in the adapter section below,
# which had not executed yet when `main()` ran.  Importing the module always
# worked, so only the command-line `fit` and `predict` paths were affected.  This
# is a load-order correction; it changes no value this module computes.


# =============================================================================
# ADAPTER (2): AGENT 1'S ACTUAL ON-DISK LAYOUT.
#
# Verified on 2026-09-20 against
#   artifacts/fable-concept-toy20-20260920/fixture/public/<world>/
# Agent 1 ships PRE-TOKENIZED records, one directory of .npy files per world,
# rather than the per-transition semantic arrays the first adapter block assumes.
# Field offsets, record ordering, the RESET encoding, the detector width and the
# 3:1 role pattern all match this module's independent construction exactly, so
# only the FILE layout needed an adapter.  Both readers are kept: the semantic
# one drives the synthetic plumbing tests, this one drives the registered run.
#
# AGENT 1 FILES (per world directory):
#   support_records.npy          (E, 17, 44) float32   full tokenized episodes
#   support_padding_mask.npy     (E, 17)     uint8
#   support_observed_target.npy  (E, 8)      float32   masked measurement per transition
#   support_observed_present.npy (E, 8)      uint8
#   support_episode_role.npy     (E,)        int8      0 fitting, 1 selection
#   support_budget_rung.npy      (E,)        int8      nested-prefix rung index
#   query_records.npy            (Q, 17, 44) float32   panels, already rolled forward
#   query_padding_mask.npy       (Q, 17)     uint8
#   query_n_records.npy          (Q,)        int32     endpoint == n_records - 1
#   query_detector.npy           (Q, 9)      float32   onehot(a,4) ++ onehot(b,5)
#   query_record_ids.json                              opaque IDs, order-aligned
# =============================================================================

AGENT1_FILES = {
    "support_records": "support_records.npy",
    "support_padding_mask": "support_padding_mask.npy",
    "support_observed_target": "support_observed_target.npy",
    "support_observed_present": "support_observed_present.npy",
    "support_episode_role": "support_episode_role.npy",
    "support_budget_rung": "support_budget_rung.npy",
    "query_records": "query_records.npy",
    "query_n_records": "query_n_records.npy",
    "query_detector": "query_detector.npy",
    "query_record_ids": "query_record_ids.json",
}


def decode_semantic_fields(records: np.ndarray) -> dict[str, np.ndarray]:
    """Recover the per-transition semantic fields from tokenized records.

    Reads the QUERY row of each transition, which carries the action, source,
    destination and dose but never a measurement.  This is a pure re-reading of
    the public record; nothing hidden is reconstructed.
    """
    count = records.shape[0]
    action = np.zeros((count, N_TRANSITIONS), dtype=np.int64)
    source = np.zeros((count, N_TRANSITIONS), dtype=np.int64)
    destination = np.full((count, N_TRANSITIONS), DESTINATION_NONE, dtype=np.int64)
    dose = np.zeros((count, N_TRANSITIONS), dtype=np.float32)
    for t in range(N_TRANSITIONS):
        row = records[:, 1 + 2 * t, :]
        action[:, t] = np.argmax(row[:, SLICE_ACTION], axis=-1)
        source[:, t] = np.argmax(row[:, SLICE_SOURCE], axis=-1)
        destination[:, t] = np.argmax(row[:, SLICE_DESTINATION], axis=-1)
        dose[:, t] = row[:, SLICE_DOSE.start]
    return {
        "properties": records[:, 0, SLICE_PROPERTIES].reshape(count, N_OBJECTS, N_PROPERTIES),
        "action_id": action,
        "source_id": source,
        "destination_id": destination,
        "dose": dose,
    }


def load_support_agent1(world_dir: str | os.PathLike[str]) -> Episodes:
    """Read one world's support episodes from Agent 1's tokenized directory."""
    base = pathlib.Path(world_dir)
    records = np.load(base / AGENT1_FILES["support_records"], allow_pickle=False)
    target = np.load(base / AGENT1_FILES["support_observed_target"], allow_pickle=False)
    present = np.load(base / AGENT1_FILES["support_observed_present"], allow_pickle=False)
    role = np.load(base / AGENT1_FILES["support_episode_role"], allow_pickle=False)
    rung = np.load(base / AGENT1_FILES["support_budget_rung"], allow_pickle=False)
    fields = decode_semantic_fields(records)
    # Nested prefixes: ordering by (rung, position) makes the first B/8 episodes
    # exactly the registered prefix for budget B.
    order = np.lexsort((np.arange(len(rung)), rung))
    episode_index = np.empty(len(rung), dtype=np.int64)
    episode_index[order] = np.arange(len(rung), dtype=np.int64)
    return Episodes(
        properties=torch.tensor(fields["properties"], dtype=torch.float32),
        action_id=torch.tensor(fields["action_id"], dtype=torch.int64),
        source_id=torch.tensor(fields["source_id"], dtype=torch.int64),
        destination_id=torch.tensor(fields["destination_id"], dtype=torch.int64),
        dose=torch.tensor(fields["dose"], dtype=torch.float32),
        sensor=torch.tensor(np.asarray(target), dtype=torch.float32),
        sensor_present=torch.tensor(np.asarray(present), dtype=torch.float32),
        role=torch.tensor(np.asarray(role), dtype=torch.int64),
        episode_index=torch.tensor(episode_index, dtype=torch.int64),
    )


def verify_tokenization_against_agent1(world_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Rebuild Agent 1's own support records from the decoded fields and compare.

    This is the single check that this module's private tokenizer and Agent 1's
    serializer agree bit for bit on a full eight-transition history.  A mismatch
    here means the two agents disagree about the public interface, and must be
    resolved before any freeze.
    """
    base = pathlib.Path(world_dir)
    reference = np.load(base / AGENT1_FILES["support_records"], allow_pickle=False)
    episodes = load_support_agent1(base)
    count = len(episodes)
    rebuilt, endpoint = build_sequences(
        episodes,
        torch.full((count,), N_TRANSITIONS - 1, dtype=torch.int64),
        torch.ones((count,), dtype=torch.int64),
    )
    # A full history built as "7 observed transitions + a 1-step forecast" covers
    # records 0..15; Agent 1's row 16 is the final OBSERVED, which this module
    # deliberately never constructs for a prediction.
    covered = reference[:, :16, :]
    difference = float(np.abs(rebuilt.numpy()[:, :16, :] - covered).max())
    return {
        "world_dir": str(base),
        "episodes": count,
        "max_abs_difference_records_0_to_15": difference,
        "tokenizations_agree": difference == 0.0,
        "endpoint_is_final_query": bool(int(endpoint[0]) == 15),
    }


def load_queries_agent1(
    world_dir: str | os.PathLike[str],
) -> tuple[list[str], torch.Tensor, torch.Tensor, torch.Tensor]:
    """Read a pre-rolled query panel.  Returns (record_ids, records, endpoint, features).

    Agent 1's panels are already rolled forward under the spec's contract, so this
    path runs them as given rather than rebuilding them: there is no second
    tokenizer to diverge.  The detector one-hot is consumed directly.
    """
    base = pathlib.Path(world_dir)
    records = np.load(base / AGENT1_FILES["query_records"], allow_pickle=False)
    n_records = np.load(base / AGENT1_FILES["query_n_records"], allow_pickle=False)
    detector = np.load(base / AGENT1_FILES["query_detector"], allow_pickle=False)
    with open(base / AGENT1_FILES["query_record_ids"], encoding="utf-8") as handle:
        record_ids = json.load(handle)
    if isinstance(record_ids, dict):
        record_ids = record_ids.get("record_ids", record_ids.get("ids"))
    count = records.shape[0]
    query_a = torch.tensor(np.argmax(detector[:, :QUERY_A_WIDTH], axis=-1), dtype=torch.int64)
    query_b = torch.tensor(np.argmax(detector[:, QUERY_A_WIDTH:], axis=-1), dtype=torch.int64)
    properties = torch.tensor(
        records[:, 0, SLICE_PROPERTIES].reshape(count, N_OBJECTS, N_PROPERTIES), dtype=torch.float32
    )
    features = build_query_features(properties, query_a, query_b)
    endpoint = torch.tensor(np.asarray(n_records), dtype=torch.int64) - 1
    padded = np.zeros((count, FIXED_SEQUENCE_LENGTH, RECORD_WIDTH), dtype=np.float32)
    padded[:, : records.shape[1], :] = records
    return [str(value) for value in record_ids], torch.tensor(padded), endpoint, features


@torch.no_grad()
def run_predict_agent1(checkpoint_file: str, world_dir: str, out_file: str) -> dict[str, float]:
    checkpoint = torch.load(checkpoint_file, weights_only=False)
    arm = checkpoint["arm"]
    parameters = {name: tensor.clone() for name, tensor in checkpoint["parameters"].items()}
    record_ids, records, endpoint, features = load_queries_agent1(world_dir)
    prediction = forward(arm, parameters, records.unsqueeze(0), endpoint, features)
    values = {record_id: float(value) for record_id, value in zip(record_ids, prediction[0])}
    if out_file:
        pathlib.Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "contract_version": CONTRACT_VERSION,
                    "arm": arm,
                    "checkpoint": os.path.basename(checkpoint_file),
                    "predictions": values,
                },
                handle,
                indent=2,
                sort_keys=True,
            )
    return values


if __name__ == "__main__":
    raise SystemExit(main())
