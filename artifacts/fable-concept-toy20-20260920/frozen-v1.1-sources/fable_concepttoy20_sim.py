"""concept-toy20 (ct20-v1.1) simulator, traces, panels and private evaluator.

Agent 1 deliverable, PILOT stage.  Authoritative contracts:
    design/v3/20-concept-toy-simulator-spec.md
    design/v3/20-concept-toy-preregistration-draft.md
    design/v3/20-concept-toy-build-plan.md   (section "Agent 1 -- Simulator and panels")

SCOPE OF THIS FILE
------------------
  * v1 C / O / N simulator, anonymous public interface, nested 32..512 support sets,
    the four calibration query panels, deterministic generators and hashes.
  * Family M's equations live here too, BEHIND the evaluator boundary, so their
    algebraic identities can be unit-checked.  `calibration-data` refuses to emit an
    M world (the pilot pools contain none) and this file produces no mode-family
    example trace, calibration score or learning curve.
  * No learner, no optimizer, no difficulty tuning, no final-world data generation.
    Final-split world TUPLES are derived for the cross-split collision audit only;
    no final episode, panel or target is generated.

The public loader lives in a separate module, `fable_concepttoy20_public.py`, which
imports nothing from here, so a model dataset can never reach the world object.

Internal arithmetic is float64.  Public records are serialized as little-endian
float32 ('<f4').  No timestamps are written into any hashed file.

Run:
    python3.12 -B scripts/fable_concepttoy20_sim.py calibration-data --out DIR
    python3.12 -B scripts/fable_concepttoy20_sim.py fixture --out DIR
    python3.12 -B scripts/fable_concepttoy20_sim.py audit --data DIR
    python3.12 -B scripts/fable_concepttoy20_sim.py evaluate \
        --predictions FILE --private DIR --out FILE
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

# --------------------------------------------------------------------------------------
# 0.  Version, namespace and registered constants (spec sections 2-5)
# --------------------------------------------------------------------------------------

VERSION = 'ct20-v1.1'
# Astra ruling D: the experiment version label is SEPARATE from the RNG namespace root.
# The root below is inherited unchanged from ct20-v1 so that no world, support episode or
# initialization is redrawn by the amendment.
NAMESPACE_ROOT = 'premonition/concept-toy20/v1'
INHERITED_RNG_NAMESPACE_ROOT = 'premonition/concept-toy20/v1'
PREVIOUS_VERSION = 'ct20-v1'
# The world tuple hash is part of the inherited RNG identity: every episode namespace is
# keyed by world_id, so letting the experiment-version label into the tuple would redraw
# every world, support episode and alias.  Ruling D forbids exactly that, so this label
# is PINNED at the inherited value and must never track VERSION.
WORLD_TUPLE_VERSION = 'ct20-v1'
RULINGS_FILE = 'design/v3/20-concept-toy-rulings-1.md'
RULINGS_SHA256 = '40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de'
# Rulings 2 is additive: it resolves the remaining pilot numerics and ratifies the public
# interface.  Rulings 1 is NOT superseded, so both are stamped wherever either is.
# NOTE: the coordinator quoted sha 8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d
# for this file.  The copy in this worktree hashes to the value below, measured twice.  The
# discrepancy is unresolved and is reported, not silently reconciled: this constant records
# what was ACTUALLY read and applied.
RULINGS2_FILE = 'design/v3/20-concept-toy-rulings-2.md'
RULINGS2_SHA256 = '1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2'
RULINGS2_SHA256_AS_QUOTED_BY_COORDINATOR = (
    '8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d')

INTERNAL_VERBS = ('pulse', 'contact', 'invert', 'read', 'wait')
VERB_PULSE, VERB_CONTACT, VERB_INVERT, VERB_READ, VERB_WAIT = range(5)
RESERVED_COMPOSITION = (VERB_PULSE, VERB_CONTACT, VERB_INVERT, VERB_READ)

N_OBJECTS = 4
N_PROPERTIES = 6
N_TRANSITIONS = 8
N_RECORDS_FULL = 17          # 1 RESET + 8 * (QUERY, OBSERVED)
RECORD_WIDTH = 44
DETECTOR_WIDTH = 9           # one-hot a (4) + one-hot b incl. NONE (5)

SENSOR_SIGMA = 0.03
ANALYTIC_SENSOR_VARIANCE = 0.0009
PRESENT_PROBABILITY = 0.75
Q_CLIP = 2.0
MAX_ACTION_ATTEMPTS = 10000

BUDGETS = (32, 64, 128, 256, 512)
GROUP_SIZE = 4               # 3 fitting episodes : 1 discovery-validation episode
SELECTION_INDEX_IN_GROUP = 3
EPISODES_AT_MAX_BUDGET = BUDGETS[-1] // N_TRANSITIONS      # 64
ROLE_FIT, ROLE_SELECTION = 0, 1

LOSS_NORMALIZATION_CONSTANT = 0.25     # public, family independent (spec section 6)
V_FLOOR = 0.05                         # prereg section 4

# Coefficient draw order is part of the frozen generator.
COEFFICIENT_RANGES = (
    ('a', 0.25, 0.60),
    ('beta', 0.20, 0.45),
    ('g', 0.80, 1.20),
    ('b', 0.10, 0.40),
    ('c', 0.20, 0.60),
)

FAMILIES = ('c', 'm', 'o', 'n')
CONTROL_FAMILIES = ('o', 'n')

WORLD_POOLS = {
    'train':      {'c': 4, 'm': 0, 'o': 1, 'n': 1},
    'validation': {'c': 4, 'm': 0, 'o': 1, 'n': 1},
    'final':      {'c': 8, 'm': 8, 'o': 4, 'n': 4},
}
PILOT_SPLITS = ('train', 'validation')

# The readable interface fixture uses its own outer-split name so that no fixture world
# can ever collide with a registered pool world.  See AMBIGUITY_RULINGS.
FIXTURE_SPLIT = 'fixture'

STREAM_DISCOVERY = 'discovery'
STREAM_SOURCE_QUERY = 'source-query'
STREAM_REUSE_FIT = 'reuse-fit'
STREAM_REUSE_QUERY = 'reuse-query'
# Ruling B6: `normalization` is dropped from the ACTIVE stream list and kept only as a
# reserved name with zero draws.  V is computed by the evaluator from the panel-1/panel-2
# noise-free responses that already exist; no separate normalization sample is drawn.
# Removing it perturbs no other stream because every stream is an independent SHA-256
# namespace, not a position in a shared sequence.
STREAM_NORMALIZATION_RESERVED_UNUSED = 'normalization'
ACTIVE_STREAMS = (STREAM_DISCOVERY, STREAM_SOURCE_QUERY, STREAM_REUSE_FIT,
                  STREAM_REUSE_QUERY)
RESERVED_UNUSED_STREAMS = (STREAM_NORMALIZATION_RESERVED_UNUSED,)

# --- public record layout (spec section 3), field order exactly as tabulated ----------
SL_PROPERTIES = slice(0, 24)
SL_ACTION = slice(24, 29)
SL_SOURCE = slice(29, 33)
SL_DESTINATION = slice(33, 38)
IX_DOSE = 38
IX_SENSOR = 39
IX_SENSOR_PRESENT = 40
SL_RECORD_TYPE = slice(41, 44)
DESTINATION_NONE = 4
RT_RESET, RT_QUERY, RT_OBSERVED = 0, 1, 2
RECORD_TYPE_NAMES = ('RESET', 'QUERY', 'OBSERVED')

PANEL_ORDINARY = 1
PANEL_COMPOSITION = 2
PANEL_RELEVANT_PAIR = 3
PANEL_IRRELEVANT_PAIR = 4
PANEL_NAMES = {
    PANEL_ORDINARY: 'ordinary',
    PANEL_COMPOSITION: 'new-composition',
    PANEL_RELEVANT_PAIR: 'relevant-intervention-pair',
    PANEL_IRRELEVANT_PAIR: 'irrelevant-change-pair',
}
UNITS_PER_PANEL = 16
# Spec section 4: "six forecasts of horizon 1, five of horizon 2, five of horizon 4".
PANEL1_HORIZONS = (1,) * 6 + (2,) * 5 + (4,) * 5
# The three horizon LEVELS panel 1 averages over with equal weight (rulings 2 R1).
# Derived, so it can never drift from the 6/5/5 target counts above.
PANEL1_HORIZON_LEVELS = tuple(sorted(set(PANEL1_HORIZONS)))

# --------------------------------------------------------------------------------------
# 0b.  Every place the spec is silent or self-contradictory.
#      Named constants, listed verbatim in the manifest and in the final report.
# --------------------------------------------------------------------------------------

# The spec never fixes the internal verb ORDER used to index the verb permutation.
# Taken literally from the order of the transition table in spec section 2.
VERB_ORDER_CONVENTION = 'table order in spec section 2: pulse, contact, invert, read, wait'

# "Randomly permute the four local object IDs."  Direction is unobservable because the
# six properties are i.i.d. per object and every family's initial state is all zeros;
# the draw is still consumed so the stream matches the registration.
OBJECT_PERMUTATION_DIRECTION = 'internal_of_public'      # p_public = p_internal[perm]

# Spec section 3 says action_id and source_id are "all zero at RESET" but describes
# destination as "NONE for noncontact actions and RESET".  Literal reading: the
# destination one-hot IS set to NONE at RESET.
# RULING B4 (confirmed): destination = NONE, action/source blocks zero, dose/sensor/
# present zero, properties populated, RESET record type set.
RESET_DESTINATION_IS_NONE = True

# RULING B1 (versioned amendment, ct20-v1.1).  Previously False on the literal reading
# that panels are not "discovery episodes".  Astra ruled YES:
#   * exclude the reserved composition from every COMPLETE ordinary action string in
#     panel 1 and panel-4-ordinary;
#   * apply the same discovery-grammar exclusion to the four-action PREFIX of a
#     composition unit, and NEVER reject its forced [pulse, contact, invert, read]
#     suffix;
#   * rejection is action-only (verbs only), whole-string redraw, 10,000-attempt limit;
#   * applies to source AND task-B query recipes.
APPLY_COMPOSITION_EXCLUSION_TO_PANELS = True

# Query-panel targets are evaluator-held labels, not returned measurements, so the
# Bernoulli(0.75) presence mask is not applied to them.  Sensor noise still is, so a
# raw noisy-target MSE exists for every target.
# RULING B2 (confirmed): all 96 targets are always present to the evaluator; prefix A
# observations keep their Bernoulli(0.75) missingness and forecast observations stay
# blank.  B2 is an evaluator-availability rule, never an unmasked sensor in a rollout.
PANEL_TARGET_ALWAYS_PRESENT = True

# Panel 4 reuses "eight ordinary and eight new-composition recipes".  The spec does not
# say which horizons the eight ordinary ones use; panel 1's 6/5/5 split does not divide
# by two.  Most balanced literal scaling:
# RULING B3 (confirmed): keep (1,1,1,2,2,2,4,4) on ordinary units 0..7, equal pair-unit
# weighting for panel 4.
PANEL4_ORDINARY_HORIZONS = (1, 1, 1, 2, 2, 2, 4, 4)

# "use pulse dose +-1 equally" -- deterministic first-half / second-half assignment.
PANEL2_DOSE_SPLIT = 'units 0-7 use dose +1, units 8-15 use dose -1'

# Panel 4's recipes are drawn fresh (not copied from panels 1 and 2) so that the spec's
# "64 independent units" holds.
# RULING B7 (confirmed): eight fresh ordinary and eight fresh composition recipes,
# independently keyed from panels 1/2.  Branches inside a pair still count as one unit.
PANEL4_RECIPES_ARE_FRESH = True

# RULING B5 (confirmed): exactly one scored prediction per branch, read at the final
# QUERY after rolling forward h actions.  Intermediate QUERY records are processed but
# are not additional scored targets.  16 + 16 + 2*16 + 2*16 = 96.
ONE_SCORED_PREDICTION_AT_FINAL_QUERY = True

# RULING B8 (accepted as intended): arity/dose structure and action IDs stay public;
# `outer_split` stays in coordinator bookkeeping and never enters a tensor or a
# split-conditioned fitting choice.  Required claim wording, verbatim:
PUBLIC_HINT_CLAIM_WORDING = ('randomly relabeled action IDs with public argument/dose '
                             'structure')
OUTER_SPLIT_IS_BOOKKEEPING_ONLY = True

# Public query files must not carry panel identity (the build plan lists panel identity
# as a PRIVATE evaluator field).  Records are therefore emitted in a deterministic
# hash order rather than panel order.  No new RNG stream is introduced.
QUERY_ORDER_BY_HASH = True

# mask ~ Bernoulli(0.75) is realised as rng.random() < 0.75.
MASK_DRAW_CONVENTION = 'rng.random() < 0.75'

# V uses the population variance (ddof=0) of the pool's noise-free ordinary and
# composition panel responses.
V_VARIANCE_DDOF = 0

# Task-B streams are not in the registered namespace table; these suffixes are added
# for the B-label-isolation fixture/test only.  No pilot data uses them.
TASK_B_DETECTOR_STREAM_SUFFIX = 'detector-b'
TASK_B_NOISE_STREAM_SUFFIX = 'noise-b'

# --- ruling C9: start-up boundary, evaluated in binary64 -------------------------------
# never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80),  r = (L_i - L_f) / L_i
# No rounding, no library isclose, and no new tolerance on any other E threshold.
STARTUP_IMPROVEMENT_THRESHOLD = 0.10
STARTUP_RELATIVE_TOLERANCE = 1e-12
STARTUP_NEVER_STARTED_FITTING_E = 0.80
STARTUP_INITIAL_FLOOR = 1e-8
LEARNED_FITTING_E = 0.25          # prereg section 8
TRANSFER_QUERY_E = 0.50           # prereg section 8
QUERY_E_TARGET = 0.25             # prereg section 8 "required 0.25 mark"

AMBIGUITY_RULINGS = {
    'VERB_ORDER_CONVENTION': VERB_ORDER_CONVENTION,
    'OBJECT_PERMUTATION_DIRECTION': OBJECT_PERMUTATION_DIRECTION,
    'RESET_DESTINATION_IS_NONE': RESET_DESTINATION_IS_NONE,
    'APPLY_COMPOSITION_EXCLUSION_TO_PANELS': APPLY_COMPOSITION_EXCLUSION_TO_PANELS,
    'PANEL_TARGET_ALWAYS_PRESENT': PANEL_TARGET_ALWAYS_PRESENT,
    'PANEL4_ORDINARY_HORIZONS': list(PANEL4_ORDINARY_HORIZONS),
    'PANEL2_DOSE_SPLIT': PANEL2_DOSE_SPLIT,
    'PANEL4_RECIPES_ARE_FRESH': PANEL4_RECIPES_ARE_FRESH,
    'ONE_SCORED_PREDICTION_AT_FINAL_QUERY': ONE_SCORED_PREDICTION_AT_FINAL_QUERY,
    'QUERY_ORDER_BY_HASH': QUERY_ORDER_BY_HASH,
    'MASK_DRAW_CONVENTION': MASK_DRAW_CONVENTION,
    'V_VARIANCE_DDOF': V_VARIANCE_DDOF,
    'FIXTURE_SPLIT': FIXTURE_SPLIT,
    'QUERY_EPISODE_INDEX_SERIALIZATION': '"{panel}/{unit}" inside the episode namespace',
    'ACTION_DRAW_ORDER': 'verb, then source, then (contact destination | pulse dose)',
    'TASK_B_STREAM_SUFFIXES': [TASK_B_DETECTOR_STREAM_SUFFIX, TASK_B_NOISE_STREAM_SUFFIX],
    'OUTER_SPLIT_IS_BOOKKEEPING_ONLY': OUTER_SPLIT_IS_BOOKKEEPING_ONLY,
    'PUBLIC_HINT_CLAIM_WORDING': PUBLIC_HINT_CLAIM_WORDING,
}

# Every accepted stream constant, with its exact value and draw order, as ruling
# "Other stream choices: accept as implemented" requires them to be recorded.
ACCEPTED_STREAM_CONSTANTS = {
    'rng_namespace_root': INHERITED_RNG_NAMESPACE_ROOT,
    'stream_seed': "int.from_bytes(sha256(namespace)[:8], 'little', signed=False)",
    'bit_generator': 'numpy PCG64 seeded by that integer',
    'active_streams': list(ACTIVE_STREAMS),
    'reserved_unused_streams_zero_draws': list(RESERVED_UNUSED_STREAMS),
    'episode_namespace': '{root}/episode/{world_id}/{stream}/{episode_key}/{leaf}',
    'panel_edit_namespace': '{root}/panel/{world_id}/{panel}/{unit}/edit',
    'world_namespace': '{root}/world/{outer_split}/{family}/{world_index}',
    'episode_leaf_draw_order': [
        "'public': uniform(-1,1,(4,6)) properties, THEN permutation(4); panel extras "
        'continue on this same generator',
        "'actions/{attempt}': per transition verb~U{0..4}, source~U{0..3}, then contact "
        'destination ~ U over the other three, or pulse dose = +1 if U{0,1}==1 else -1',
        "'mask': rng.random(8) < 0.75",
        "'noise': rng.normal(0.0, 0.03, size=8)",
        "'detector-b' / 'noise-b': task-B only, per transition a~U{0..3} then b~U over "
        'the other three; label noise ~ Normal(0,0.03) of size 8',
    ],
    'panel_edit_draw_order': 'permutation(4), then uniform(-2,2,(4,4))',
    'world_draw_order': ('coefficients a,beta,g,b,c in that order, then '
                         'permutation(5) for the public verb map'),
    'object_permutation_direction': OBJECT_PERMUTATION_DIRECTION,
    'query_episode_keys': '"{panel}/{unit}"',
    'fixture_split': FIXTURE_SPLIT,
    'task_b_stream_suffixes': [TASK_B_DETECTOR_STREAM_SUFFIX, TASK_B_NOISE_STREAM_SUFFIX],
    'query_order_by_hash': QUERY_ORDER_BY_HASH,
    'v_variance_ddof': V_VARIANCE_DDOF,
    'panel2_dose_split': PANEL2_DOSE_SPLIT,
    'panel4_composition_dose_split': 'units 8-11 use dose +1, units 12-15 use dose -1',
    'reset_destination_is_none': RESET_DESTINATION_IS_NONE,
    'note': ('Frozen at ct20-v1.1.  Distributionally equivalent substitutes are not '
             'permitted after this freeze.'),
}


class IntegrityError(RuntimeError):
    """A generator invariant that must never fail in a valid run."""


class MalformedAction(ValueError):
    """An action that the fixed-trace generator must never produce."""


# --------------------------------------------------------------------------------------
# 1.  streams -- SHA-256 -> PCG64 derivation, canonical serialization, hashing
# --------------------------------------------------------------------------------------

def stream_seed(namespace: str) -> int:
    """Unsigned little-endian integer from the first eight bytes of SHA256(namespace)."""
    digest = hashlib.sha256(namespace.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'little', signed=False)


def make_rng(namespace: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(stream_seed(namespace)))


def canonical_json(obj: Any) -> str:
    """Sorted keys, compact separators, round-trip floats, no NaN/Inf, ASCII."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      allow_nan=False, ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def tensor_hash(array: np.ndarray) -> str:
    """Hash covers dtype, shape and raw contiguous little-endian bytes."""
    array = np.ascontiguousarray(array)
    header = canonical_json({'dtype': array.dtype.str, 'shape': list(array.shape)})
    return hashlib.sha256(header.encode('utf-8') + b'|' + array.tobytes()).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_npy(path: Path, array: np.ndarray) -> None:
    """np.save writes only a dtype/shape/order header -- deterministic, no timestamp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as handle:
        np.save(handle, np.ascontiguousarray(array), allow_pickle=False)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(obj), encoding='utf-8')


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _json_safe(obj: Any) -> Any:
    """canonical_json forbids NaN/Inf.  A diagnostic that could not be computed is
    written as null; its STATUS field, not a rounded number, carries the meaning."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def episode_namespace(world_id: str, stream: str, episode_key: str, leaf: str,
                      attempt: int | None = None) -> str:
    base = f'{NAMESPACE_ROOT}/episode/{world_id}/{stream}/{episode_key}/{leaf}'
    return base if attempt is None else f'{base}/{attempt}'


def panel_edit_namespace(world_id: str, panel: int, unit: int) -> str:
    return f'{NAMESPACE_ROOT}/panel/{world_id}/{panel}/{unit}/edit'


# --------------------------------------------------------------------------------------
# 2.  world -- immutable world record and the C / M / O / N update laws
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class World:
    """(family, action-permutation, coefficients).  Split and index are bookkeeping."""
    family: str
    outer_split: str
    world_index: int
    coefficients: tuple[tuple[str, float], ...]
    verb_to_public: tuple[int, ...]

    @property
    def coef(self) -> dict[str, float]:
        return dict(self.coefficients)

    @property
    def public_to_verb(self) -> tuple[int, ...]:
        inverse = [0] * 5
        for verb, public in enumerate(self.verb_to_public):
            inverse[public] = verb
        return tuple(inverse)

    def tuple_metadata(self, include_permutation: bool = True) -> dict[str, Any]:
        meta: dict[str, Any] = {
            'version': WORLD_TUPLE_VERSION,      # pinned; see the constant's comment
            'family': self.family,
            'coefficients': {name: float(value) for name, value in self.coefficients},
        }
        if include_permutation:
            meta['verb_to_public'] = [int(x) for x in self.verb_to_public]
        return meta

    @property
    def world_id(self) -> str:
        return sha256_text(canonical_json(self.tuple_metadata(True)))

    @property
    def world_id_without_permutation(self) -> str:
        return sha256_text(canonical_json(self.tuple_metadata(False)))

    @property
    def world_public_id(self) -> str:
        """Opaque public alias.  The true world_id never enters a public file."""
        return sha256_text(self.world_id + '/public-alias')[:16]

    @property
    def has_hidden_state(self) -> bool:
        return self.family in ('c', 'm')


def make_world(outer_split: str, family: str, world_index: int) -> World:
    if family not in FAMILIES:
        raise ValueError(f'unknown family {family!r}')
    namespace = f'{NAMESPACE_ROOT}/world/{outer_split}/{family}/{world_index}'
    rng = make_rng(namespace)
    # All five coefficients are drawn in EVERY family so record sizes and the coefficient
    # stream cannot identify a family (spec section 2).
    coefficients = tuple(
        (name, float(rng.uniform(low, high))) for name, low, high in COEFFICIENT_RANGES
    )
    permutation = tuple(int(x) for x in rng.permutation(5))
    return World(family=family, outer_split=outer_split, world_index=world_index,
                 coefficients=coefficients, verb_to_public=permutation)


@dataclass(frozen=True)
class Action:
    verb: int
    source: int
    destination: int | None
    dose: int


def validate_action(action: Action) -> None:
    if action.verb not in range(5):
        raise MalformedAction(f'verb {action.verb}')
    if action.source not in range(N_OBJECTS):
        raise MalformedAction(f'source {action.source}')
    if action.verb == VERB_CONTACT:
        if action.destination is None or action.destination not in range(N_OBJECTS):
            raise MalformedAction('contact needs a destination object')
        if action.destination == action.source:
            raise MalformedAction('contact requires i != j')
        if action.dose != 0:
            raise MalformedAction('contact carries no dose')
    else:
        if action.destination is not None:
            raise MalformedAction(f'{INTERNAL_VERBS[action.verb]} carries no destination')
        if action.verb == VERB_PULSE:
            if action.dose not in (-1, 1):
                raise MalformedAction('pulse dose must be -1 or +1')
        elif action.dose != 0:
            raise MalformedAction(f'{INTERNAL_VERBS[action.verb]} carries no dose')


def initial_state(family: str) -> np.ndarray:
    """q[4] float64 for C; m[4] int64 for M; an inert all-zero vector for O and N."""
    if family == 'm':
        return np.zeros(N_OBJECTS, dtype=np.int64)
    return np.zeros(N_OBJECTS, dtype=np.float64)


def apply_transition(world: World, state: np.ndarray, action: Action) -> np.ndarray:
    """Return the post-action state.  Never mutates `state`."""
    validate_action(action)
    coef = world.coef
    nxt = state.copy()
    if world.family == 'c':
        i = action.source
        if action.verb == VERB_PULSE:
            nxt[i] = float(np.clip(state[i] + coef['a'] * action.dose, -Q_CLIP, Q_CLIP))
        elif action.verb == VERB_CONTACT:
            j = action.destination
            delta = coef['beta'] * (state[i] - state[j])     # from the OLD state
            nxt[i] = state[i] - delta
            nxt[j] = state[j] + delta
        elif action.verb == VERB_INVERT:
            nxt[i] = -state[i]
        # read / wait: no state change
        return nxt
    if world.family == 'm':
        i = action.source
        if action.verb == VERB_PULSE:
            nxt[i] = (state[i] ^ 1) if action.dose > 0 else 0
        elif action.verb == VERB_CONTACT:
            j = action.destination
            nxt[j] = state[j] ^ state[i]                     # destination only
        elif action.verb == VERB_INVERT:
            nxt[i] = state[i] ^ 1
        return nxt
    # O and N have no hidden evolving state at all.
    return nxt


def response(world: World, state: np.ndarray, properties: np.ndarray, i: int) -> float:
    """Noise-free device response at object i.  Evaluator-only quantity."""
    coef = world.coef
    if world.family == 'c':
        return float(np.tanh(coef['g'] * state[i] + coef['b'] * properties[i, 0]))
    if world.family == 'm':
        return float(np.tanh(coef['g'] * (2.0 * state[i] - 1.0)
                             + coef['b'] * properties[i, 0]))
    if world.family == 'o':
        return float(np.tanh(coef['b'] * properties[i, 0] + coef['c'] * properties[i, 1]))
    return 0.0


def response_task_b(world: World, state: np.ndarray, properties: np.ndarray,
                    a: int, b: int) -> float:
    """r_B(a,b) = (r(a) - r(b)) / 2.  Task B readout; unused by pilot data."""
    if a == b:
        raise ValueError('task B detector needs distinct a, b')
    return 0.5 * (response(world, state, properties, a)
                  - response(world, state, properties, b))


# --------------------------------------------------------------------------------------
# 3.  traces -- fixed action scheduler, episode simulation, QUERY-before-OBSERVED tokens
# --------------------------------------------------------------------------------------

def sample_action(rng: np.random.Generator) -> Action:
    """Verb uniform over 5, source uniform over 4, contact destination uniform over the
    other 3, pulse dose uniform over {-1,+1}.  Draw order is frozen."""
    verb = int(rng.integers(0, 5))
    source = int(rng.integers(0, N_OBJECTS))
    destination: int | None = None
    dose = 0
    if verb == VERB_CONTACT:
        others = [k for k in range(N_OBJECTS) if k != source]
        destination = int(others[int(rng.integers(0, N_OBJECTS - 1))])
    elif verb == VERB_PULSE:
        dose = 1 if int(rng.integers(0, 2)) == 1 else -1
    action = Action(verb, source, destination, dose)
    validate_action(action)
    return action


def contains_reserved_composition(verbs: Sequence[int]) -> bool:
    window = len(RESERVED_COMPOSITION)
    return any(tuple(verbs[t:t + window]) == RESERVED_COMPOSITION
               for t in range(len(verbs) - window + 1))


def sample_action_string(world_id: str, stream: str, episode_key: str,
                         length: int = N_TRANSITIONS,
                         exclude_reserved: bool = True) -> tuple[list[Action], int]:
    """Redraw the WHOLE string on rejection.  Rejection examines verbs only."""
    for attempt in range(MAX_ACTION_ATTEMPTS):
        rng = make_rng(episode_namespace(world_id, stream, episode_key, 'actions', attempt))
        actions = [sample_action(rng) for _ in range(length)]
        if not exclude_reserved:
            return actions, attempt
        if not contains_reserved_composition([a.verb for a in actions]):
            return actions, attempt
    raise IntegrityError(
        f'action rejection exhausted {MAX_ACTION_ATTEMPTS} attempts for {episode_key}')


def draw_episode_properties(world_id: str, stream: str,
                            episode_key: str) -> tuple[np.ndarray, np.ndarray,
                                                       np.random.Generator]:
    """Six public properties per object, then the local-ID permutation.  The generator is
    returned so panel-specific extras continue on the same registered `public` stream."""
    rng = make_rng(episode_namespace(world_id, stream, episode_key, 'public'))
    internal = rng.uniform(-1.0, 1.0, size=(N_OBJECTS, N_PROPERTIES))
    permutation = rng.permutation(N_OBJECTS)
    public = internal[permutation]          # OBJECT_PERMUTATION_DIRECTION
    return public, permutation, rng


def draw_masks(world_id: str, stream: str, episode_key: str) -> np.ndarray:
    rng = make_rng(episode_namespace(world_id, stream, episode_key, 'mask'))
    return rng.random(N_TRANSITIONS) < PRESENT_PROBABILITY


def draw_noise(world_id: str, stream: str, episode_key: str) -> np.ndarray:
    rng = make_rng(episode_namespace(world_id, stream, episode_key, 'noise'))
    return rng.normal(0.0, SENSOR_SIGMA, size=N_TRANSITIONS)


@dataclass
class Episode:
    world_public_id: str
    stream: str
    episode_key: str
    properties: np.ndarray        # (4, 6) float64, public order
    object_permutation: np.ndarray
    actions: list[Action]
    latent: np.ndarray            # (9, 4) state after RESET and after each transition
    noise_free: np.ndarray        # (8,) r at the source object, post-action
    noise: np.ndarray             # (8,)
    present: np.ndarray           # (8,) bool
    observed: np.ndarray          # (8,) y returned to the learner, exactly 0 if absent
    action_attempts: int


def simulate_episode(world: World, properties: np.ndarray,
                     object_permutation: np.ndarray, actions: Sequence[Action],
                     present: np.ndarray, noise: np.ndarray,
                     stream: str, episode_key: str) -> Episode:
    if len(actions) != N_TRANSITIONS:
        raise IntegrityError('an episode has exactly eight transitions')
    state = initial_state(world.family)
    latent = [np.asarray(state, dtype=np.float64).copy()]
    noise_free = np.zeros(N_TRANSITIONS, dtype=np.float64)
    for t, action in enumerate(actions):
        state = apply_transition(world, state, action)
        latent.append(np.asarray(state, dtype=np.float64).copy())
        noise_free[t] = response(world, state, properties, action.source)
    observed = np.where(present, noise_free + noise, 0.0)
    return Episode(world_public_id=world.world_public_id, stream=stream,
                   episode_key=episode_key, properties=properties,
                   object_permutation=object_permutation, actions=list(actions),
                   latent=np.stack(latent), noise_free=noise_free, noise=noise,
                   present=np.asarray(present, dtype=bool), observed=observed,
                   action_attempts=0)


def build_discovery_episode(world: World, episode_index: int) -> Episode:
    key = str(episode_index)
    properties, permutation, _ = draw_episode_properties(
        world.world_id, STREAM_DISCOVERY, key)
    actions, attempts = sample_action_string(
        world.world_id, STREAM_DISCOVERY, key, exclude_reserved=True)
    present = draw_masks(world.world_id, STREAM_DISCOVERY, key)
    noise = draw_noise(world.world_id, STREAM_DISCOVERY, key)
    episode = simulate_episode(world, properties, permutation, actions, present, noise,
                               STREAM_DISCOVERY, key)
    episode.action_attempts = attempts
    return episode


# --- tokenization ---------------------------------------------------------------------

def _base_record(properties: np.ndarray) -> np.ndarray:
    record = np.zeros(RECORD_WIDTH, dtype=np.float64)
    record[SL_PROPERTIES] = properties.reshape(-1)
    return record


def make_reset_record(properties: np.ndarray) -> np.ndarray:
    record = _base_record(properties)
    if RESET_DESTINATION_IS_NONE:
        record[SL_DESTINATION.start + DESTINATION_NONE] = 1.0
    record[SL_RECORD_TYPE.start + RT_RESET] = 1.0
    return record


def make_action_record(world: World, properties: np.ndarray, action: Action,
                       record_type: int, sensor: float, sensor_present: float
                       ) -> np.ndarray:
    validate_action(action)
    record = _base_record(properties)
    record[SL_ACTION.start + world.verb_to_public[action.verb]] = 1.0
    record[SL_SOURCE.start + action.source] = 1.0
    destination = DESTINATION_NONE if action.destination is None else action.destination
    record[SL_DESTINATION.start + destination] = 1.0
    record[IX_DOSE] = float(action.dose)
    record[IX_SENSOR] = float(sensor)
    record[IX_SENSOR_PRESENT] = float(sensor_present)
    record[SL_RECORD_TYPE.start + record_type] = 1.0
    return record


def support_records(world: World, episode: Episode) -> np.ndarray:
    """Seventeen records: RESET then QUERY/OBSERVED per transition."""
    records = np.zeros((N_RECORDS_FULL, RECORD_WIDTH), dtype=np.float64)
    records[0] = make_reset_record(episode.properties)
    for t, action in enumerate(episode.actions):
        records[1 + 2 * t] = make_action_record(
            world, episode.properties, action, RT_QUERY, 0.0, 0.0)
        records[2 + 2 * t] = make_action_record(
            world, episode.properties, action, RT_OBSERVED,
            float(episode.observed[t]), 1.0 if episode.present[t] else 0.0)
    return records


def query_records(world: World, episode: Episode, prefix_length: int, horizon: int,
                  allow_partial_span: bool = False) -> tuple[np.ndarray, int, int]:
    """Prefix of real QUERY/OBSERVED pairs, then h-1 QUERY + blank OBSERVED pairs, then
    the final QUERY at which the prediction is read.  Returns (records, n, query_index).

    Every query PANEL unit spans all eight transitions.  The fitting-audit set may stop
    at an earlier endpoint, so it passes allow_partial_span=True; the remaining records
    are then zero padding covered by the padding mask.
    """
    if prefix_length + horizon > N_TRANSITIONS or (
            not allow_partial_span and prefix_length + horizon != N_TRANSITIONS):
        raise IntegrityError('every panel unit covers exactly eight transitions')
    rows: list[np.ndarray] = [make_reset_record(episode.properties)]
    for t in range(prefix_length):
        action = episode.actions[t]
        rows.append(make_action_record(world, episode.properties, action, RT_QUERY, 0.0, 0.0))
        rows.append(make_action_record(world, episode.properties, action, RT_OBSERVED,
                                       float(episode.observed[t]),
                                       1.0 if episode.present[t] else 0.0))
    for t in range(prefix_length, prefix_length + horizon - 1):
        action = episode.actions[t]
        rows.append(make_action_record(world, episode.properties, action, RT_QUERY, 0.0, 0.0))
        rows.append(make_action_record(world, episode.properties, action, RT_OBSERVED,
                                       0.0, 0.0))          # blank -- never teacher forced
    final_t = prefix_length + horizon - 1
    rows.append(make_action_record(world, episode.properties, episode.actions[final_t],
                                   RT_QUERY, 0.0, 0.0))
    n_records = len(rows)
    query_index = n_records - 1
    padded = np.zeros((N_RECORDS_FULL, RECORD_WIDTH), dtype=np.float64)
    padded[:n_records] = np.stack(rows)
    return padded, n_records, query_index


def detector_vector(a: int, b: int | None) -> np.ndarray:
    vector = np.zeros(DETECTOR_WIDTH, dtype=np.float64)
    vector[a] = 1.0
    vector[N_OBJECTS + (DESTINATION_NONE if b is None else b)] = 1.0
    return vector


# --------------------------------------------------------------------------------------
# 4.  panels -- ordinary, new composition, relevant pairs, irrelevant-change pairs
# --------------------------------------------------------------------------------------

@dataclass
class QueryTarget:
    """One scored prediction point.  Public half + evaluator-only half."""
    # public
    records: np.ndarray          # (17, 44) float64, cast to <f4 at serialization
    n_records: int
    query_index: int
    detector: np.ndarray         # (9,) float64
    # private
    panel: int
    unit: int
    branch: str
    pair_key: str | None
    horizon: int
    prefix_length: int
    detector_a: int
    detector_b: int | None
    noise_free: float
    noisy: float
    record_id: str = ''


def _panel_key(panel: int, unit: int) -> str:
    return f'{panel}/{unit}'          # QUERY_EPISODE_INDEX_SERIALIZATION


def _target_from_episode(world: World, episode: Episode, panel: int, unit: int,
                         branch: str, prefix_length: int, horizon: int,
                         detector_a: int, detector_b: int | None,
                         pair_key: str | None,
                         override_noise: np.ndarray | None = None) -> QueryTarget:
    records, n_records, query_index = query_records(world, episode, prefix_length, horizon)
    final_t = prefix_length + horizon - 1
    noise = episode.noise if override_noise is None else override_noise
    noise_free = float(episode.noise_free[final_t])
    noisy = noise_free + float(noise[final_t])       # PANEL_TARGET_ALWAYS_PRESENT
    return QueryTarget(records=records, n_records=n_records, query_index=query_index,
                       detector=detector_vector(detector_a, detector_b),
                       panel=panel, unit=unit, branch=branch, pair_key=pair_key,
                       horizon=horizon, prefix_length=prefix_length,
                       detector_a=detector_a, detector_b=detector_b,
                       noise_free=noise_free, noisy=noisy)


def _ordinary_unit(world: World, panel: int, unit: int, horizon: int,
                   stream: str = STREAM_SOURCE_QUERY) -> tuple[Episode, int]:
    """Eight actions from the discovery grammar; prefix length 8-h.

    Ruling B1: the exclusion is applied to the COMPLETE eight-action string.  `stream`
    exists so a later task-B query panel on `reuse-query` obeys the identical rule; the
    source panels always pass the default and therefore draw exactly as registered.
    """
    key = _panel_key(panel, unit)
    properties, permutation, _ = draw_episode_properties(world.world_id, stream, key)
    actions, _ = sample_action_string(
        world.world_id, stream, key,
        exclude_reserved=APPLY_COMPOSITION_EXCLUSION_TO_PANELS)
    present = draw_masks(world.world_id, stream, key)
    noise = draw_noise(world.world_id, stream, key)
    episode = simulate_episode(world, properties, permutation, actions, present, noise,
                               stream, key)
    return episode, N_TRANSITIONS - horizon


def _composition_unit(world: World, panel: int, unit: int, dose: int,
                      stream: str = STREAM_SOURCE_QUERY) -> Episode:
    """Four grammar prefix transitions, then the withheld [pulse, contact, invert, read]
    suffix bound to i (pulse/contact source) and j (contact destination, invert, read).

    Ruling B1: the exclusion applies to the four-action PREFIX only.  The forced suffix
    is never inspected and never rejected, so the complete string deliberately contains
    the reserved composition exactly once, at positions 4..7.
    """
    key = _panel_key(panel, unit)
    properties, permutation, rng = draw_episode_properties(world.world_id, stream, key)
    i = int(rng.integers(0, N_OBJECTS))
    others = [k for k in range(N_OBJECTS) if k != i]
    j = int(others[int(rng.integers(0, N_OBJECTS - 1))])
    prefix, _ = sample_action_string(
        world.world_id, stream, key, length=4,
        exclude_reserved=APPLY_COMPOSITION_EXCLUSION_TO_PANELS)
    suffix = [Action(VERB_PULSE, i, None, dose),
              Action(VERB_CONTACT, i, j, 0),
              Action(VERB_INVERT, j, None, 0),
              Action(VERB_READ, j, None, 0)]
    present = draw_masks(world.world_id, stream, key)
    noise = draw_noise(world.world_id, stream, key)
    return simulate_episode(world, properties, permutation, prefix + suffix, present,
                            noise, stream, key)


def build_panel_ordinary(world: World,
                         stream: str = STREAM_SOURCE_QUERY) -> list[QueryTarget]:
    targets: list[QueryTarget] = []
    for unit, horizon in enumerate(PANEL1_HORIZONS):
        episode, prefix_length = _ordinary_unit(world, PANEL_ORDINARY, unit, horizon,
                                                stream)
        a = episode.actions[N_TRANSITIONS - 1].source          # last_action.source
        targets.append(_target_from_episode(
            world, episode, PANEL_ORDINARY, unit, 'single', prefix_length, horizon,
            a, None, None))
    return targets


def build_panel_composition(world: World,
                            stream: str = STREAM_SOURCE_QUERY) -> list[QueryTarget]:
    targets: list[QueryTarget] = []
    for unit in range(UNITS_PER_PANEL):
        dose = 1 if unit < UNITS_PER_PANEL // 2 else -1        # PANEL2_DOSE_SPLIT
        episode = _composition_unit(world, PANEL_COMPOSITION, unit, dose, stream)
        a = episode.actions[N_TRANSITIONS - 1].source          # the read(j)
        targets.append(_target_from_episode(
            world, episode, PANEL_COMPOSITION, unit, 'single', 4, 4, a, None, None))
    return targets


def build_panel_relevant_pairs(world: World,
                               stream: str = STREAM_SOURCE_QUERY) -> list[QueryTarget]:
    """Prefix [read(i),wait(i),read(i),wait(i)]; treated suffix injects pulse(i,+1).
    Both branches share properties, masks and sensor-noise draws.

    Every action here is fully forced, so ruling B1's exclusion has nothing to reject:
    neither branch's eight verbs can form [pulse, contact, invert, read] (no contact).
    """
    targets: list[QueryTarget] = []
    for unit in range(UNITS_PER_PANEL):
        key = _panel_key(PANEL_RELEVANT_PAIR, unit)
        properties, permutation, rng = draw_episode_properties(
            world.world_id, stream, key)
        i = int(rng.integers(0, N_OBJECTS))
        present = draw_masks(world.world_id, stream, key)
        noise = draw_noise(world.world_id, stream, key)
        prefix = [Action(VERB_READ, i, None, 0), Action(VERB_WAIT, i, None, 0),
                  Action(VERB_READ, i, None, 0), Action(VERB_WAIT, i, None, 0)]
        branches = {
            'treated': [Action(VERB_PULSE, i, None, 1), Action(VERB_READ, i, None, 0),
                        Action(VERB_WAIT, i, None, 0), Action(VERB_READ, i, None, 0)],
            'control': [Action(VERB_WAIT, i, None, 0), Action(VERB_READ, i, None, 0),
                        Action(VERB_WAIT, i, None, 0), Action(VERB_READ, i, None, 0)],
        }
        pair_key = f'p{PANEL_RELEVANT_PAIR}u{unit}'
        for branch, suffix in branches.items():
            episode = simulate_episode(world, properties, permutation, prefix + suffix,
                                       present, noise, stream, key)
            targets.append(_target_from_episode(
                world, episode, PANEL_RELEVANT_PAIR, unit, branch, 4, 4, i, None, pair_key))
    return targets


def apply_nuisance_edit(world: World, episode: Episode, sigma: np.ndarray,
                        fresh_channels: np.ndarray) -> Episode:
    """Permute local IDs and replace public channels 2..5 with independent U[-2,2].
    Channels 0 and 1 travel with their object, so every noise-free response is preserved
    under the relabeling.  The edited branch is RE-SIMULATED, never copied."""
    edited_properties = np.zeros_like(episode.properties)
    for i in range(N_OBJECTS):
        edited_properties[sigma[i], 0:2] = episode.properties[i, 0:2]
    edited_properties[:, 2:6] = fresh_channels
    edited_actions = [
        Action(a.verb, int(sigma[a.source]),
               None if a.destination is None else int(sigma[a.destination]), a.dose)
        for a in episode.actions
    ]
    return simulate_episode(world, edited_properties, episode.object_permutation,
                            edited_actions, episode.present, episode.noise,
                            episode.stream, episode.episode_key)


def build_panel_irrelevant_pairs(world: World,
                                 stream: str = STREAM_SOURCE_QUERY) -> list[QueryTarget]:
    targets: list[QueryTarget] = []
    for unit in range(UNITS_PER_PANEL):
        if unit < 8:
            horizon = PANEL4_ORDINARY_HORIZONS[unit]
            episode, prefix_length = _ordinary_unit(
                world, PANEL_IRRELEVANT_PAIR, unit, horizon, stream)
        else:
            horizon, prefix_length = 4, 4
            dose = 1 if unit < 12 else -1
            episode = _composition_unit(world, PANEL_IRRELEVANT_PAIR, unit, dose, stream)
        rng = make_rng(panel_edit_namespace(world.world_id, PANEL_IRRELEVANT_PAIR, unit))
        sigma = rng.permutation(N_OBJECTS)
        fresh_channels = rng.uniform(-2.0, 2.0, size=(N_OBJECTS, 4))
        edited = apply_nuisance_edit(world, episode, sigma, fresh_channels)
        a = episode.actions[N_TRANSITIONS - 1].source
        pair_key = f'p{PANEL_IRRELEVANT_PAIR}u{unit}'
        targets.append(_target_from_episode(
            world, episode, PANEL_IRRELEVANT_PAIR, unit, 'base', prefix_length, horizon,
            a, None, pair_key))
        targets.append(_target_from_episode(
            world, edited, PANEL_IRRELEVANT_PAIR, unit, 'edited', prefix_length, horizon,
            int(sigma[a]), None, pair_key))
    return targets


def build_source_panels(world: World,
                        stream: str = STREAM_SOURCE_QUERY) -> list[QueryTarget]:
    """64 units, 96 target predictions: 16 + 16 + 2*16 + 2*16 (ruling B5).

    `stream` defaults to the registered source-query stream.  Passing
    STREAM_REUSE_QUERY builds the task-B query panels under exactly the same B1 rules;
    no task-B panel is generated in this pilot.
    """
    targets = (build_panel_ordinary(world, stream)
               + build_panel_composition(world, stream)
               + build_panel_relevant_pairs(world, stream)
               + build_panel_irrelevant_pairs(world, stream))
    if len(targets) != 96:
        raise IntegrityError(f'expected 96 targets, built {len(targets)}')
    order = sorted(
        range(len(targets)),
        key=lambda ix: sha256_text(
            f'{world.world_public_id}/order/{targets[ix].panel}/{targets[ix].unit}/'
            f'{targets[ix].branch}')
    ) if QUERY_ORDER_BY_HASH else list(range(len(targets)))
    ordered = [targets[ix] for ix in order]
    for index, target in enumerate(ordered):
        target.record_id = f'{world.world_public_id}-q{index:04d}'
    return ordered


# --------------------------------------------------------------------------------------
# 5.  task B batch shape -- used only by the fixture and the B-label-isolation test
# --------------------------------------------------------------------------------------

def build_task_b_episode(world: World, episode_index: int) -> dict[str, Any]:
    """One task-B fitting episode: the SAME public records as task A, plus B detector
    queries and B labels carried in target-only fields that never touch the records."""
    key = str(episode_index)
    properties, permutation, _ = draw_episode_properties(
        world.world_id, STREAM_REUSE_FIT, key)
    actions, _ = sample_action_string(world.world_id, STREAM_REUSE_FIT, key,
                                      exclude_reserved=True)
    present = draw_masks(world.world_id, STREAM_REUSE_FIT, key)
    noise = draw_noise(world.world_id, STREAM_REUSE_FIT, key)
    episode = simulate_episode(world, properties, permutation, actions, present, noise,
                               STREAM_REUSE_FIT, key)
    detector_rng = make_rng(episode_namespace(world.world_id, STREAM_REUSE_FIT, key,
                                              TASK_B_DETECTOR_STREAM_SUFFIX))
    label_noise = make_rng(episode_namespace(world.world_id, STREAM_REUSE_FIT, key,
                                             TASK_B_NOISE_STREAM_SUFFIX)
                           ).normal(0.0, SENSOR_SIGMA, size=N_TRANSITIONS)
    detectors = np.zeros((N_TRANSITIONS, DETECTOR_WIDTH), dtype=np.float64)
    labels = np.zeros(N_TRANSITIONS, dtype=np.float64)
    labels_noise_free = np.zeros(N_TRANSITIONS, dtype=np.float64)
    for t in range(N_TRANSITIONS):
        a = int(detector_rng.integers(0, N_OBJECTS))
        others = [k for k in range(N_OBJECTS) if k != a]
        b = int(others[int(detector_rng.integers(0, N_OBJECTS - 1))])
        detectors[t] = detector_vector(a, b)
        state = episode.latent[t + 1]
        if world.family == 'm':
            state = state.astype(np.int64)
        labels_noise_free[t] = response_task_b(world, state, properties, a, b)
        labels[t] = labels_noise_free[t] + label_noise[t]
    return {
        'records': support_records(world, episode),
        'b_detector': detectors,
        'b_label': labels,                    # target-only field
        'b_label_noise_free': labels_noise_free,
        'episode': episode,
    }


# --------------------------------------------------------------------------------------
# 5b.  fitting-audit set (prereg section 8, rulings C9/C10)
#
# "At initialization and at the fixed B=512 endpoint, score a deterministic fitting audit
#  set: for each fit episode and each h, its last eligible observed endpoint."
#
# Nothing here is sampled.  The set is a pure function of the already-public support
# episodes and their already-public presence masks, so it adds no RNG stream and reveals
# no hidden state.  The learner predicts on these sequences; the evaluator alone joins
# them to noise-free truth.
# --------------------------------------------------------------------------------------

AUDIT_HORIZONS = (1, 2, 4)
# The spec does not fix an index convention for "endpoint".  Literal, named choice:
AUDIT_ENDPOINT_INDEXING = ('1-based: endpoint t in h..8 names the t-th action of the '
                           'episode; its response is episode.noise_free[t-1]')
# "Eligible" = the endpoint admits a horizon-h forecast (t >= h) AND its own observation
# was returned to the learner (present[t-1]), because the fitting loss uses observed y.
AUDIT_ELIGIBILITY = 'present[t-1] is True and t >= h; the LAST such t is used'
# Fit episodes only, over the full B=512 prefix; roles come from episode_role().
AUDIT_EPISODE_ROLE = 'ROLE_FIT episodes of the 512-transition prefix (48 of 64)'


@dataclass
class FittingAuditItem:
    """One deterministic fitting-audit case.  Public half + evaluator-only half."""
    # public
    audit_id: str
    episode_index: int
    horizon: int
    endpoint: int                # 1-based, see AUDIT_ENDPOINT_INDEXING
    records: np.ndarray          # (17, 44)
    n_records: int
    query_index: int
    detector: np.ndarray         # (9,)
    observed_label: float        # the training label; already public in the support set
    # private
    noise_free: float
    detector_a: int


def last_eligible_observed_endpoint(present: np.ndarray, horizon: int) -> int | None:
    for endpoint in range(N_TRANSITIONS, horizon - 1, -1):
        if bool(present[endpoint - 1]):
            return endpoint
    return None


def build_fitting_audit_set(world: World,
                            support: Sequence[Episode]) -> list[FittingAuditItem]:
    items: list[FittingAuditItem] = []
    for episode_index, episode in enumerate(support):
        if episode_role(episode_index) != ROLE_FIT:
            continue
        for horizon in AUDIT_HORIZONS:
            endpoint = last_eligible_observed_endpoint(episode.present, horizon)
            if endpoint is None:
                continue                      # no eligible case; never chosen by loss
            prefix_length = endpoint - horizon
            records, n_records, query_index = query_records(
                world, episode, prefix_length, horizon, allow_partial_span=True)
            detector_a = episode.actions[endpoint - 1].source
            items.append(FittingAuditItem(
                audit_id=(f'{world.world_public_id}-fit{episode_index:04d}'
                          f'h{horizon}e{endpoint}'),
                episode_index=episode_index, horizon=horizon, endpoint=endpoint,
                records=records, n_records=n_records, query_index=query_index,
                detector=detector_vector(detector_a, None),
                observed_label=float(episode.observed[endpoint - 1]),
                noise_free=float(episode.noise_free[endpoint - 1]),
                detector_a=detector_a))
    return items


def audit_key(world_public_id: str, episode_index: int, horizon: int,
              endpoint: int) -> str:
    """The one supported join key format.  Agent 2 may send this string, or the
    (world_public_id, episode_index, horizon, endpoint) fields, which map to it here."""
    return f'{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}'


# There is exactly ONE audit-key spelling (rulings 2, public-interface ratification).
# An earlier draft of the models builder used "e{ep}/h{h}/t{t}"; the frozen build now
# calls `PublicDataset.audit_key` itself, so the compatibility reader that briefly lived
# here has been removed rather than left as a second legal spelling in a frozen contract.

# --------------------------------------------------------------------------------------
# 6.  generation -- nested 32..512 support sets, world pools, collision audit, V
# --------------------------------------------------------------------------------------

def episode_role(episode_index: int) -> int:
    """In every group of four, indices 0,1,2 fit and index 3 selects."""
    return (ROLE_SELECTION if episode_index % GROUP_SIZE == SELECTION_INDEX_IN_GROUP
            else ROLE_FIT)


def episode_budget_rung(episode_index: int) -> int:
    """Smallest rung whose nested prefix already contains this episode."""
    for rung, budget in enumerate(BUDGETS):
        if episode_index < budget // N_TRANSITIONS:
            return rung
    raise IntegrityError(f'episode {episode_index} is outside the 512 prefix')


def build_world_pool(splits: Iterable[str]) -> list[World]:
    worlds: list[World] = []
    for split in splits:
        for family in FAMILIES:
            for index in range(WORLD_POOLS[split][family]):
                worlds.append(make_world(split, family, index))
    return worlds


def collision_audit(worlds: Sequence[World]) -> dict[str, Any]:
    """Any duplicate full tuple hash, permutation-free tuple hash or public alias across
    the whole registered universe (train, validation AND final) aborts generation."""
    full: dict[str, list[str]] = {}
    stripped: dict[str, list[str]] = {}
    alias: dict[str, list[str]] = {}
    for world in worlds:
        tag = f'{world.outer_split}/{world.family}/{world.world_index}'
        full.setdefault(world.world_id, []).append(tag)
        stripped.setdefault(world.world_id_without_permutation, []).append(tag)
        alias.setdefault(world.world_public_id, []).append(tag)
    duplicates = {
        'full_tuple': {k: v for k, v in full.items() if len(v) > 1},
        'permutation_removed': {k: v for k, v in stripped.items() if len(v) > 1},
        'public_alias': {k: v for k, v in alias.items() if len(v) > 1},
    }
    report = {
        'version': VERSION,
        'worlds_checked': len(worlds),
        'splits_checked': sorted({w.outer_split for w in worlds}),
        'counts_by_split_and_family': {
            split: {family: sum(1 for w in worlds
                                if w.outer_split == split and w.family == family)
                    for family in FAMILIES}
            for split in sorted({w.outer_split for w in worlds})
        },
        'distinct_full_tuple_hashes': len(full),
        'distinct_permutation_removed_hashes': len(stripped),
        'distinct_public_aliases': len(alias),
        'duplicate_full_tuple_hashes': len(duplicates['full_tuple']),
        'duplicate_permutation_removed_hashes': len(duplicates['permutation_removed']),
        'duplicate_public_aliases': len(duplicates['public_alias']),
        'note': ('World identities are checked across every registered split, including '
                 'final.  No final episode, panel or target was generated.  This report '
                 'never maps a public alias to a family.'),
    }
    if any(duplicates.values()):
        raise IntegrityError(f'world tuple collision: {canonical_json(duplicates)}')
    return report


@dataclass
class WorldData:
    world: World
    support: list[Episode]
    targets: list[QueryTarget]
    audit: list[FittingAuditItem]


def build_world_data(world: World) -> WorldData:
    support = [build_discovery_episode(world, index)
               for index in range(EPISODES_AT_MAX_BUDGET)]
    targets = build_source_panels(world)
    audit = build_fitting_audit_set(world, support)
    return WorldData(world=world, support=support, targets=targets, audit=audit)


def normalization_constants(pool: Sequence[WorldData], task: str = 'A'
                            ) -> dict[str, dict[str, float]]:
    """V = max(variance of noise-free responses in that pool's ordinary and composition
    query panels, 0.05), per outer pool / task / family."""
    grouped: dict[tuple[str, str], list[float]] = {}
    for data in pool:
        key = (data.world.outer_split, data.world.family)
        for target in data.targets:
            if target.panel in (PANEL_ORDINARY, PANEL_COMPOSITION):
                grouped.setdefault(key, []).append(target.noise_free)
    out: dict[str, dict[str, float]] = {}
    for (split, family), values in sorted(grouped.items()):
        variance = float(np.var(np.asarray(values, dtype=np.float64),
                                ddof=V_VARIANCE_DDOF))
        v = max(variance, V_FLOOR)
        out[f'{split}/{task}/{family}'] = {
            'outer_split': split, 'task': task, 'family': family,
            'panel_response_variance': variance, 'V': v,
            'analytic_sensor_floor': ANALYTIC_SENSOR_VARIANCE / v,
            'n_responses': len(values),
        }
    return out


def generator_config() -> dict[str, Any]:
    return {
        'version': VERSION,
        'experiment_version': VERSION,
        'previous_version': PREVIOUS_VERSION,
        'rulings_file': RULINGS_FILE,
        'rulings_sha256': RULINGS_SHA256,
        'rulings2_file': RULINGS2_FILE,
        'rulings2_sha256': RULINGS2_SHA256,
        'namespace_root': NAMESPACE_ROOT,
        'inherited_rng_namespace_root': INHERITED_RNG_NAMESPACE_ROOT,
        'active_streams': list(ACTIVE_STREAMS),
        'reserved_unused_streams': list(RESERVED_UNUSED_STREAMS),
        'accepted_stream_constants': ACCEPTED_STREAM_CONSTANTS,
        'fitting_audit_set': {
            'horizons': list(AUDIT_HORIZONS),
            'episode_role': AUDIT_EPISODE_ROLE,
            'endpoint_indexing': AUDIT_ENDPOINT_INDEXING,
            'eligibility': AUDIT_ELIGIBILITY,
            'key_format': '{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}',
        },
        'startup_predicate': {
            'expression': 'never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)',
            'r': '(L_initial - L_final) / L_initial, binary64, no rounding',
            'improvement_threshold': STARTUP_IMPROVEMENT_THRESHOLD,
            'relative_tolerance': STARTUP_RELATIVE_TOLERANCE,
            'never_started_fitting_E': STARTUP_NEVER_STARTED_FITTING_E,
            'initial_floor': STARTUP_INITIAL_FLOOR,
            'learned_fitting_E': LEARNED_FITTING_E,
            'transfer_query_E': TRANSFER_QUERY_E,
        },
        'internal_verbs': list(INTERNAL_VERBS),
        'reserved_composition': [INTERNAL_VERBS[v] for v in RESERVED_COMPOSITION],
        'n_objects': N_OBJECTS,
        'n_properties': N_PROPERTIES,
        'n_transitions': N_TRANSITIONS,
        'n_records_full': N_RECORDS_FULL,
        'record_width': RECORD_WIDTH,
        'detector_width': DETECTOR_WIDTH,
        'sensor_sigma': SENSOR_SIGMA,
        'analytic_sensor_variance': ANALYTIC_SENSOR_VARIANCE,
        'present_probability': PRESENT_PROBABILITY,
        'q_clip': Q_CLIP,
        'max_action_attempts': MAX_ACTION_ATTEMPTS,
        'budgets': list(BUDGETS),
        'group_size': GROUP_SIZE,
        'selection_index_in_group': SELECTION_INDEX_IN_GROUP,
        'loss_normalization_constant': LOSS_NORMALIZATION_CONSTANT,
        'v_floor': V_FLOOR,
        'coefficient_ranges': [[n, lo, hi] for n, lo, hi in COEFFICIENT_RANGES],
        'world_pools': WORLD_POOLS,
        'panel_units': UNITS_PER_PANEL,
        'panel1_horizons': list(PANEL1_HORIZONS),
        'panel_names': {str(k): v for k, v in PANEL_NAMES.items()},
        'record_layout': {
            'public_properties': [0, 24], 'action_id': [24, 29], 'source_id': [29, 33],
            'destination_id': [33, 38], 'dose': [38, 39], 'sensor': [39, 40],
            'sensor_present': [40, 41], 'record_type': [41, 44],
            'destination_none_index': DESTINATION_NONE,
            'record_type_order': list(RECORD_TYPE_NAMES),
        },
        'ambiguity_rulings': AMBIGUITY_RULINGS,
        'python_version': '.'.join(str(x) for x in sys.version_info[:3]),
        'numpy_version': np.__version__,
        'public_dtype': '<f4',
        'simulator_dtype': 'float64',
    }


# --- serialization --------------------------------------------------------------------

def _f4(array: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(array, dtype=np.float64).astype('<f4')


def write_world_public(root: Path, data: WorldData) -> dict[str, str]:
    world, wpid = data.world, data.world.world_public_id
    directory = root / 'public' / wpid
    arrays: dict[str, np.ndarray] = {}
    arrays['support_records'] = _f4(np.stack(
        [support_records(world, ep) for ep in data.support]))
    arrays['support_observed_target'] = _f4(np.stack([ep.observed for ep in data.support]))
    arrays['support_observed_present'] = np.stack(
        [ep.present for ep in data.support]).astype(np.uint8)
    arrays['support_episode_role'] = np.asarray(
        [episode_role(i) for i in range(len(data.support))], dtype=np.int8)
    arrays['support_budget_rung'] = np.asarray(
        [episode_budget_rung(i) for i in range(len(data.support))], dtype=np.int8)
    arrays['support_padding_mask'] = np.ones(
        (len(data.support), N_RECORDS_FULL), dtype=np.uint8)
    arrays['query_records'] = _f4(np.stack([t.records for t in data.targets]))
    arrays['query_detector'] = _f4(np.stack([t.detector for t in data.targets]))
    arrays['query_n_records'] = np.asarray([t.n_records for t in data.targets],
                                           dtype=np.int32)
    arrays['query_index'] = np.asarray([t.query_index for t in data.targets],
                                       dtype=np.int32)
    mask = np.zeros((len(data.targets), N_RECORDS_FULL), dtype=np.uint8)
    for row, target in enumerate(data.targets):
        mask[row, :target.n_records] = 1
    arrays['query_padding_mask'] = mask
    # --- fitting-audit set (prereg section 8 / ruling C10) -----------------------------
    audit = data.audit
    arrays['audit_records'] = _f4(np.stack([a.records for a in audit]))
    arrays['audit_detector'] = _f4(np.stack([a.detector for a in audit]))
    arrays['audit_n_records'] = np.asarray([a.n_records for a in audit], dtype=np.int32)
    arrays['audit_index'] = np.asarray([a.query_index for a in audit], dtype=np.int32)
    audit_mask = np.zeros((len(audit), N_RECORDS_FULL), dtype=np.uint8)
    for row, item in enumerate(audit):
        audit_mask[row, :item.n_records] = 1
    arrays['audit_padding_mask'] = audit_mask
    arrays['audit_episode_index'] = np.asarray([a.episode_index for a in audit],
                                               dtype=np.int32)
    arrays['audit_horizon'] = np.asarray([a.horizon for a in audit], dtype=np.int32)
    arrays['audit_endpoint'] = np.asarray([a.endpoint for a in audit], dtype=np.int32)
    # The training label is already public: it is the masked observation the learner
    # received in support_observed_target for that episode and endpoint.
    arrays['audit_observed_label'] = _f4(
        np.asarray([a.observed_label for a in audit], dtype=np.float64))
    hashes: dict[str, str] = {}
    for name, array in arrays.items():
        write_npy(directory / f'{name}.npy', array)
        hashes[f'public/{wpid}/{name}.npy'] = tensor_hash(array)
    write_json(directory / 'query_record_ids.json',
               [t.record_id for t in data.targets])
    write_json(directory / 'audit_keys.json',
               [{'audit_id': a.audit_id, 'episode_index': a.episode_index,
                 'horizon': a.horizon, 'endpoint': a.endpoint,
                 'endpoint_transition_index': a.endpoint - 1,
                 'n_records': a.n_records, 'query_index': a.query_index}
                for a in audit])
    return hashes


def write_world_private(root: Path, data: WorldData) -> dict[str, str]:
    world, wpid = data.world, data.world.world_public_id
    directory = root / 'private' / wpid
    hashes: dict[str, str] = {}
    arrays = {
        'support_truth_noise_free': np.stack([ep.noise_free for ep in data.support]),
        'support_truth_noise': np.stack([ep.noise for ep in data.support]),
        'support_latent': np.stack([ep.latent for ep in data.support]),
        'support_action_attempts': np.asarray(
            [ep.action_attempts for ep in data.support], dtype=np.int32),
        'query_truth_noise_free': np.asarray(
            [t.noise_free for t in data.targets], dtype=np.float64),
        'query_truth_noisy': np.asarray([t.noisy for t in data.targets],
                                        dtype=np.float64),
        'audit_truth_noise_free': np.asarray([a.noise_free for a in data.audit],
                                             dtype=np.float64),
        'audit_truth_observed': np.asarray([a.observed_label for a in data.audit],
                                           dtype=np.float64),
    }
    for name, array in arrays.items():
        write_npy(directory / f'{name}.npy', array)
        hashes[f'private/{wpid}/{name}.npy'] = tensor_hash(array)
    truth = [{
        'record_id': t.record_id, 'world_public_id': wpid, 'world_id': world.world_id,
        'family': world.family, 'outer_split': world.outer_split, 'task': 'A',
        'panel': t.panel, 'panel_name': PANEL_NAMES[t.panel], 'unit': t.unit,
        'branch': t.branch, 'pair_key': t.pair_key, 'horizon': t.horizon,
        'prefix_length': t.prefix_length, 'detector_a': t.detector_a,
        'detector_b': t.detector_b, 'noise_free_response': t.noise_free,
        'noisy_target': t.noisy,
    } for t in data.targets]
    write_json(directory / 'query_truth.json', truth)
    write_json(directory / 'audit_truth.json', [{
        'audit_id': a.audit_id, 'world_public_id': wpid, 'world_id': world.world_id,
        'family': world.family, 'outer_split': world.outer_split, 'task': 'A',
        'episode_index': a.episode_index, 'horizon': a.horizon, 'endpoint': a.endpoint,
        'prefix_length': a.endpoint - a.horizon, 'detector_a': a.detector_a,
        'detector_b': None, 'noise_free_response': a.noise_free,
        'observed_label': a.observed_label,
    } for a in data.audit])
    return hashes


def tree_file_hashes(root: Path) -> dict[str, str]:
    """SHA-256 of raw bytes for every generated file except the manifest and reports."""
    skip = {'manifest.json', 'audit_report.json'}
    return {
        str(path.relative_to(root)): file_hash(path)
        for path in sorted(Path(root).rglob('*'))
        if path.is_file() and path.name not in skip
    }


def generate_calibration_data(out: Path) -> dict[str, Any]:
    """Frozen pilot calibration files for the train and validation pools."""
    out = Path(out)
    universe = build_world_pool(WORLD_POOLS.keys())      # includes final TUPLES only
    collisions = collision_audit(universe)
    pool_worlds = [w for w in universe if w.outer_split in PILOT_SPLITS]
    if any(w.family == 'm' for w in pool_worlds):
        raise IntegrityError('the pilot pools must contain no mode-family world')
    pool = [build_world_data(world) for world in pool_worlds]

    tensor_hashes: dict[str, str] = {}
    for data in pool:
        tensor_hashes.update(write_world_public(out, data))
        tensor_hashes.update(write_world_private(out, data))

    public_index = {
        'version': VERSION,
        'budgets': list(BUDGETS),
        'episodes_per_budget': [b // N_TRANSITIONS for b in BUDGETS],
        'n_support_episodes': EPISODES_AT_MAX_BUDGET,
        'n_query_records': 96,
        'record_width': RECORD_WIDTH,
        'n_records_full': N_RECORDS_FULL,
        'detector_width': DETECTOR_WIDTH,
        'worlds': sorted(
            [{'world_public_id': d.world.world_public_id,
              'outer_split': d.world.outer_split,
              'n_audit_records': len(d.audit)} for d in pool],
            key=lambda row: (row['outer_split'], row['world_public_id'])),
    }
    write_json(out / 'public' / 'worlds.json', public_index)

    world_config = {
        d.world.world_public_id: {
            'world_id': d.world.world_id,
            'world_id_without_permutation': d.world.world_id_without_permutation,
            'family': d.world.family, 'outer_split': d.world.outer_split,
            'world_index': d.world.world_index,
            'coefficients': {k: v for k, v in d.world.coefficients},
            'verb_to_public': {INTERNAL_VERBS[i]: p
                               for i, p in enumerate(d.world.verb_to_public)},
        } for d in pool
    }
    write_json(out / 'private' / 'world_config.json', world_config)
    write_json(out / 'private' / 'normalization.json', normalization_constants(pool))
    write_json(out / 'collision_report.json', collisions)

    file_hashes = tree_file_hashes(out)
    manifest = {
        'version': VERSION,
        'experiment_version': VERSION,
        'previous_version': PREVIOUS_VERSION,
        'rulings_file': RULINGS_FILE,
        'rulings_sha256': RULINGS_SHA256,
        'rulings2_file': RULINGS2_FILE,
        'rulings2_sha256': RULINGS2_SHA256,
        'amendment': {
            'versioned_changes': [
                'B1: the reserved composition is excluded from every complete ordinary '
                'panel action string and from every composition-unit prefix, which '
                'changes the ordinary/composition query distributions.',
            ],
            'confirmations_without_behaviour_change': [
                'B2 all 96 targets always present to the evaluator',
                'B3 panel-4 ordinary horizons (1,1,1,2,2,2,4,4)',
                'B4 RESET destination = NONE',
                'B5 one scored prediction at the final QUERY',
                'B7 fresh panel-4 recipes',
                'B8 public hints accepted as intended',
            ],
            'bookkeeping_changes': [
                'B6: the `normalization` stream is reserved/unused with zero draws and '
                'no longer appears in the active stream list.',
                'C9/C10: a deterministic fitting-audit set and the start-up predicate '
                'are added for the evaluator.',
            ],
            'unchanged': ['RNG namespace root', 'world tuples', 'discovery supports',
                          'panel-3 recipes', 'masks', 'sensor noise'],
        },
        'stage': 'pilot-calibration',
        'generator_config': generator_config(),
        'public_files': sorted(k for k in file_hashes if k.startswith('public/')),
        'private_files': sorted(k for k in file_hashes if k.startswith('private/')),
        'file_hashes': dict(sorted(file_hashes.items())),
        'tensor_hashes': dict(sorted(tensor_hashes.items())),
        'collision_report_sha256': file_hash(out / 'collision_report.json'),
        'boundary': {
            'public_contains': ['public tensors', 'observed masked A targets',
                                'episode roles', 'budget rungs', 'detector queries',
                                'padding masks', 'opaque record IDs',
                                'opaque world aliases', 'outer split labels',
                                'fitting-audit sequences with episode/horizon/endpoint '
                                'keys and their already-public observed labels'],
            'public_excludes': ['hidden state', 'coefficients', 'family', 'verb map',
                                'simulator seeds', 'world_id', 'noise-free responses',
                                'query targets', 'normalization constant V',
                                'panel identity',
                                'noise-free fitting-audit responses'],
        },
        'note': ('No timestamp is written into any file listed here.  Regenerating with '
                 'the same configuration reproduces every hash byte for byte.'),
    }
    write_json(out / 'manifest.json', manifest)
    return manifest


# --------------------------------------------------------------------------------------
# 7.  fixture -- small readable synthetic interface example
# --------------------------------------------------------------------------------------

FIXTURE_FAMILIES = ('c', 'o')
FIXTURE_SUPPORT_EPISODES = 8


def _decode_record(row: np.ndarray) -> dict[str, Any]:
    record_type = int(np.argmax(row[SL_RECORD_TYPE])) if row[SL_RECORD_TYPE].any() else -1
    action = row[SL_ACTION]
    source = row[SL_SOURCE]
    destination = row[SL_DESTINATION]
    return {
        'record_type': RECORD_TYPE_NAMES[record_type] if record_type >= 0 else 'PAD',
        'action_id': int(np.argmax(action)) if action.any() else None,
        'source_id': int(np.argmax(source)) if source.any() else None,
        'destination_id': ('NONE' if destination.any()
                           and int(np.argmax(destination)) == DESTINATION_NONE
                           else (int(np.argmax(destination)) if destination.any()
                                 else None)),
        'dose': float(row[IX_DOSE]),
        'sensor': round(float(row[IX_SENSOR]), 6),
        'sensor_present': float(row[IX_SENSOR_PRESENT]),
    }


def _record_table(records: np.ndarray, n_records: int) -> list[str]:
    lines = ['| # | record_type | action_id | source_id | destination_id | dose | sensor '
             '| sensor_present |',
             '| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |']
    for index in range(n_records):
        d = _decode_record(np.asarray(records[index], dtype=np.float64))
        lines.append(
            f"| {index} | {d['record_type']} | {'' if d['action_id'] is None else d['action_id']} "
            f"| {'' if d['source_id'] is None else d['source_id']} | {d['destination_id']} "
            f"| {d['dose']:+.0f} | {d['sensor']:+.6f} | {d['sensor_present']:.0f} |")
    return lines


def generate_fixture(out: Path) -> dict[str, Any]:
    out = Path(out)
    worlds = [make_world(FIXTURE_SPLIT, family, 0) for family in FIXTURE_FAMILIES]
    if any(w.family == 'm' for w in worlds):
        raise IntegrityError('the interface fixture must not use the mode family')
    if any(w.outer_split == 'final' for w in worlds):
        raise IntegrityError('the interface fixture must not use a final world')
    # A fixture world must not coincide with any registered pool world.
    registered = {w.world_id for w in build_world_pool(WORLD_POOLS.keys())}
    for world in worlds:
        if world.world_id in registered:
            raise IntegrityError('fixture world collides with a registered pool world')

    tensor_hashes: dict[str, str] = {}
    pool: list[WorldData] = []
    for world in worlds:
        support = [build_discovery_episode(world, i)
                   for i in range(FIXTURE_SUPPORT_EPISODES)]
        data = WorldData(
            world=world,
            support=support,
            targets=build_source_panels(world),
            audit=build_fitting_audit_set(world, support))
        pool.append(data)
        tensor_hashes.update(write_world_public(out, data))
        tensor_hashes.update(write_world_private(out, data))

    demo = pool[0]
    b_batch = build_task_b_episode(demo.world, 0)
    write_npy(out / 'private' / demo.world.world_public_id / 'task_b_demo_records.npy',
              _f4(b_batch['records']))
    write_npy(out / 'private' / demo.world.world_public_id / 'task_b_demo_detector.npy',
              _f4(b_batch['b_detector']))
    write_npy(out / 'private' / demo.world.world_public_id / 'task_b_demo_label.npy',
              np.asarray(b_batch['b_label'], dtype=np.float64))

    support_public = np.load(
        out / 'public' / demo.world.world_public_id / 'support_records.npy')
    query_public = np.load(
        out / 'public' / demo.world.world_public_id / 'query_records.npy')
    query_n = np.load(out / 'public' / demo.world.world_public_id / 'query_n_records.npy')
    record_ids = read_json(
        out / 'public' / demo.world.world_public_id / 'query_record_ids.json')

    lines: list[str] = []
    lines.append(f'# concept-toy20 interface fixture ({VERSION})')
    lines.append('')
    lines.append('Synthetic format fixture produced by '
                 '`scripts/fable_concepttoy20_sim.py fixture`.')
    lines.append('')
    lines.append(f'* Outer split `{FIXTURE_SPLIT}` -- **not** a registered pool world, '
                 'and never a `final` world.')
    lines.append('* Families present: ' + ', '.join(FIXTURE_FAMILIES.__iter__()) +
                 ' -- the mode family M is absent, so this file contains no mode-family '
                 'example.')
    lines.append('* This file carries no learner output, no score and no curve.')
    lines.append('')
    lines.append('## Public record layout, float32 `<f4`, width 44')
    lines.append('')
    lines.append('| offsets | field | width | encoding |')
    lines.append('| --- | --- | ---: | --- |')
    lines.append('| 0:24 | `public_properties` | 24 | four rows of six, by local public ID |')
    lines.append('| 24:29 | `action_id` | 5 | one-hot public ID, all zero at RESET |')
    lines.append('| 29:33 | `source_id` | 4 | one-hot i, all zero at RESET |')
    lines.append('| 33:38 | `destination_id` | 5 | one-hot j=0..3 or NONE=4 |')
    lines.append('| 38:39 | `dose` | 1 | -1/+1 on pulse, zero otherwise |')
    lines.append('| 39:40 | `sensor` | 1 | returned y, zero if missing or a QUERY token |')
    lines.append('| 40:41 | `sensor_present` | 1 | observation mask, zero on QUERY/RESET |')
    lines.append('| 41:44 | `record_type` | 3 | one-hot RESET, QUERY, OBSERVED |')
    lines.append('')
    lines.append('## One support episode -- 17 records, QUERY always before OBSERVED')
    lines.append('')
    lines.append('Properties (four objects x six channels), rounded for reading:')
    lines.append('')
    lines.append('```')
    for i in range(N_OBJECTS):
        values = ' '.join(f'{v:+.4f}'
                          for v in np.asarray(support_public[0, 0, SL_PROPERTIES]
                                              ).reshape(N_OBJECTS, N_PROPERTIES)[i])
        lines.append(f'object {i}: {values}')
    lines.append('```')
    lines.append('')
    lines.extend(_record_table(support_public[0], N_RECORDS_FULL))
    lines.append('')
    lines.append('Every OBSERVED record with `sensor_present = 0` carries `sensor = 0` '
                 'exactly.  Every QUERY record carries `sensor = 0` and '
                 '`sensor_present = 0`, so the target of transition t is absent from the '
                 'prefix that predicts it.')
    lines.append('')
    lines.append(f'## One query unit -- record ID `{record_ids[0]}`')
    lines.append('')
    lines.append(f'`n_records = {int(query_n[0])}`; the prediction is read at the final '
                 f'QUERY, index {int(query_n[0]) - 1}.  Forecast steps append a QUERY and '
                 'then a BLANK OBSERVED token, so no intermediate measurement is ever '
                 'teacher forced.')
    lines.append('')
    lines.extend(_record_table(query_public[0], int(query_n[0])))
    lines.append('')
    lines.append('Panel identity, horizon and the target itself are evaluator-only fields; '
                 'the public file carries an opaque record ID and nothing else.')
    lines.append('')
    lines.append('## Task-B batch shape (label isolation)')
    lines.append('')
    lines.append('A task-B fitting batch carries the SAME 44-wide records as task A, plus '
                 'two extra arrays:')
    lines.append('')
    lines.append('```')
    lines.append(f"records      float32 {tuple(b_batch['records'].shape)}   "
                 '# identical to the task-A tokenization')
    lines.append(f"b_detector   float32 {tuple(b_batch['b_detector'].shape)}       "
                 '# public (a,b) query, one row per transition')
    lines.append(f"b_label      float64 {tuple(b_batch['b_label'].shape)}          "
                 '# TARGET-ONLY field, never concatenated into records')
    lines.append('```')
    lines.append('')
    lines.append('`b_label` values never appear anywhere inside `records`; the B readout '
                 'is a label, never an encoder input.')
    lines.append('')
    lines.append('## Public tensor hashes (dtype, shape, raw little-endian bytes)')
    lines.append('')
    lines.append('| array | sha256 |')
    lines.append('| --- | --- |')
    for name, digest in sorted(tensor_hashes.items()):
        if name.startswith('public/'):
            lines.append(f'| `{name}` | `{digest}` |')
    (out / 'fixture.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    write_json(out / 'public' / 'worlds.json', {
        'version': VERSION, 'stage': 'interface-fixture',
        'budgets': list(BUDGETS),
        'n_support_episodes': FIXTURE_SUPPORT_EPISODES,
        'n_query_records': 96,
        'record_width': RECORD_WIDTH, 'n_records_full': N_RECORDS_FULL,
        'detector_width': DETECTOR_WIDTH,
        'worlds': sorted([{'world_public_id': d.world.world_public_id,
                           'outer_split': d.world.outer_split,
                           'n_audit_records': len(d.audit)} for d in pool],
                         key=lambda r: r['world_public_id']),
    })
    write_json(out / 'private' / 'world_config.json', {
        d.world.world_public_id: {
            'world_id': d.world.world_id,
            'world_id_without_permutation': d.world.world_id_without_permutation,
            'family': d.world.family, 'outer_split': d.world.outer_split,
            'world_index': d.world.world_index,
            'coefficients': {k: v for k, v in d.world.coefficients},
            'verb_to_public': {INTERNAL_VERBS[i]: p
                               for i, p in enumerate(d.world.verb_to_public)},
        } for d in pool})
    write_json(out / 'private' / 'normalization.json', normalization_constants(pool))
    file_hashes = tree_file_hashes(out)
    manifest = {
        'version': VERSION, 'experiment_version': VERSION,
        'previous_version': PREVIOUS_VERSION,
        'rulings_file': RULINGS_FILE, 'rulings_sha256': RULINGS_SHA256,
        'rulings2_file': RULINGS2_FILE, 'rulings2_sha256': RULINGS2_SHA256,
        'stage': 'interface-fixture',
        'generator_config': generator_config(),
        'families_present': list(FIXTURE_FAMILIES),
        'mode_family_present': False, 'final_worlds_present': False,
        'public_files': sorted(k for k in file_hashes if k.startswith('public/')),
        'private_files': sorted(k for k in file_hashes if k.startswith('private/')),
        'file_hashes': dict(sorted(file_hashes.items())),
        'tensor_hashes': dict(sorted(tensor_hashes.items())),
        'readable': 'fixture.md',
    }
    write_json(out / 'manifest.json', manifest)
    return manifest


# --------------------------------------------------------------------------------------
# 8.  audit -- re-verify a generated directory without trusting the generator
# --------------------------------------------------------------------------------------

_TIMESTAMP_MARKERS = ('timestamp', 'generated_at', 'created_at', 'mtime', 'ctime',
                      'datetime', 'utcnow')
_FORBIDDEN_PUBLIC_KEYS = ('family', 'coefficient', 'verb_to_public', 'world_id',
                          'noise_free', 'noisy_target', 'normaliz', 'panel', 'seed',
                          'latent', 'hidden', 'V', 'response', 'unit', 'branch',
                          'horizon', 'pair')


def _load_world_public(root: Path, wpid: str) -> dict[str, np.ndarray]:
    directory = root / 'public' / wpid
    return {path.stem: np.load(path) for path in sorted(directory.glob('*.npy'))}


def _load_world_private(root: Path, wpid: str) -> dict[str, Any]:
    directory = root / 'private' / wpid
    out: dict[str, Any] = {path.stem: np.load(path)
                           for path in sorted(directory.glob('*.npy'))}
    out['query_truth'] = read_json(directory / 'query_truth.json')
    out['audit_truth'] = read_json(directory / 'audit_truth.json')
    return out


def audit_directory(root: Path) -> dict[str, Any]:
    root = Path(root)
    manifest = read_json(root / 'manifest.json')
    config = read_json(root / 'private' / 'world_config.json')
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str = '') -> None:
        checks.append({'check': name, 'pass': bool(ok), 'detail': detail})

    # 1 -- every manifest hash reproduces.
    bad = [name for name, digest in manifest['file_hashes'].items()
           if not (root / name).exists() or file_hash(root / name) != digest]
    on_disk = set(tree_file_hashes(root))
    extra = sorted(on_disk - set(manifest['file_hashes']))
    record('manifest_file_hashes', not bad and not extra,
           f'{len(bad)} mismatched: {bad[:5]}; unlisted files: {extra[:5]}')

    bad_tensors = [name for name, digest in manifest['tensor_hashes'].items()
                   if tensor_hash(np.load(root / name)) != digest]
    record('manifest_tensor_hashes', not bad_tensors,
           f'{len(bad_tensors)} mismatched: {bad_tensors[:5]}')

    # 2 -- worlds regenerate from their registered namespace.
    mismatch = []
    for wpid, row in config.items():
        world = make_world(row['outer_split'], row['family'], row['world_index'])
        if (world.world_id != row['world_id'] or world.world_public_id != wpid
                or world.coef != row['coefficients']):
            mismatch.append(wpid)
    record('world_regeneration', not mismatch, f'mismatched: {mismatch}')

    # 3 -- no tuple collision anywhere in the registered universe.
    try:
        collision_audit(build_world_pool(WORLD_POOLS.keys()))
        record('cross_split_tuple_disjointness', True,
               'train/validation/final tuple and alias hashes all distinct')
    except IntegrityError as error:
        record('cross_split_tuple_disjointness', False, str(error))

    # 4 -- no timestamp in any hashed file.
    stamped = []
    for name in manifest['file_hashes']:
        path = root / name
        if path.suffix == '.npy':
            header = path.read_bytes()[:256].decode('latin-1')
            if not set(header.split("'")) >= {'descr', 'fortran_order', 'shape'}:
                stamped.append(name)
        else:
            text = path.read_text(encoding='utf-8').lower()
            if any(marker in text for marker in _TIMESTAMP_MARKERS):
                stamped.append(name)
    record('no_timestamps_in_hashed_files', not stamped, f'{stamped[:5]}')

    # 5 -- public/private boundary.  Scans every file under public/ plus manifest.json,
    # which the coordinator may read; forbidden KEYS are checked in the public tree only,
    # while per-world secrets must be absent from the manifest as well.
    #
    # `audit_keys.json` is excluded from the forbidden-KEY scan and checked against an
    # exact allowed key set instead.  Ruling C10 requires the fitting-audit join key to
    # carry episode/horizon/endpoint, and `horizon` is on the forbidden list because a
    # PANEL horizon would disclose panel identity.  An audit-case horizon discloses
    # nothing further: the number of blanked OBSERVED records in the published sequence
    # already states it.  No other public file may name a horizon.
    public_json = [name for name in manifest['file_hashes']
                   if name.startswith('public/') and (root / name).suffix == '.json']
    public_text = '\n'.join((root / name).read_text(encoding='utf-8')
                            for name in public_json
                            if Path(name).name != 'audit_keys.json')
    manifest_text = (root / 'manifest.json').read_text(encoding='utf-8')
    leaked_keys = [key for key in _FORBIDDEN_PUBLIC_KEYS
                   if f'"{key}' in public_text or f'{key}":' in public_text]
    allowed_audit_keys = {'audit_id', 'episode_index', 'horizon', 'endpoint',
                          'endpoint_transition_index', 'n_records', 'query_index'}
    for name in public_json:
        if Path(name).name != 'audit_keys.json':
            continue
        for entry in read_json(root / name):
            extra = set(entry) - allowed_audit_keys
            if extra:
                leaked_keys.append(f'{name}:{sorted(extra)}')
    normalization = read_json(root / 'private' / 'normalization.json')
    secret_text = ([row['world_id'] for row in config.values()]
                   + [row['world_id_without_permutation'] for row in config.values()]
                   + [repr(float(v)) for row in config.values()
                      for v in row['coefficients'].values()]
                   + [repr(float(v['V'])) for v in normalization.values()
                      if float(v['V']) != V_FLOOR])
    # A V that sits exactly on the registered public floor carries no world-specific
    # information beyond "variance <= 0.05", and 0.05 is itself a published constant,
    # so it is excluded from the numeric scan.  The public TREE is still required to
    # contain no normalization field at all (checked via _FORBIDDEN_PUBLIC_KEYS).
    leaked_ids = sorted({token for token in secret_text
                         if token in public_text or token in manifest_text})
    leaked_numbers: list[str] = []
    for wpid, row in config.items():
        arrays = _load_world_public(root, wpid)
        secrets = [float(v) for v in row['coefficients'].values()]
        secrets += [float(v['V']) for v in normalization.values()]
        private = _load_world_private(root, wpid)
        secrets += [float(v) for v in private['query_truth_noise_free'] if v != 0.0]
        secrets += [float(v) for v in private['query_truth_noisy'] if v != 0.0]
        secret32 = np.unique(np.asarray(secrets, dtype=np.float64).astype('<f4'))
        for name, array in arrays.items():
            if array.dtype != np.dtype('<f4'):
                continue
            if np.isin(array, secret32).any():
                leaked_numbers.append(f'{wpid}/{name}')
    record('public_private_boundary',
           not leaked_keys and not leaked_ids and not leaked_numbers,
           f'keys={leaked_keys} secret_strings={leaked_ids[:5]} '
           f'secret_floats_in_tensors={leaked_numbers[:5]}')

    # 6..n -- per-world structural and semantic invariants.
    failures: dict[str, list[str]] = {
        'support_shapes': [], 'budget_counts': [], 'reset_scope': [],
        'missing_is_zero': [], 'observed_target_consistency': [],
        'query_no_target': [], 'blank_forecast_observations': [],
        'panel_composition': [], 'query_order_not_grouped': [],
        'nuisance_edit_invariance': [], 'intervention_differences': [],
        'episode_disjointness': [],
        'audit_set_definition': [], 'audit_no_target': [],
        'audit_label_matches_public_support': [],
        'panel_action_strings_exclude_reserved': [],
    }
    for wpid, row in config.items():
        arrays = _load_world_public(root, wpid)
        private = _load_world_private(root, wpid)
        family = row['family']
        support = arrays['support_records']
        n_episodes = support.shape[0]
        if (support.dtype != np.dtype('<f4')
                or support.shape[1:] != (N_RECORDS_FULL, RECORD_WIDTH)
                or arrays['query_records'].shape != (96, N_RECORDS_FULL, RECORD_WIDTH)
                or arrays['query_detector'].shape != (96, DETECTOR_WIDTH)):
            failures['support_shapes'].append(wpid)

        roles = arrays['support_episode_role']
        rungs = arrays['support_budget_rung']
        expected_roles = np.asarray([episode_role(i) for i in range(n_episodes)],
                                    dtype=np.int8)
        ok_budgets = bool((roles == expected_roles).all())
        for rung, budget in enumerate(BUDGETS):
            if budget // N_TRANSITIONS > n_episodes:
                continue
            prefix = np.flatnonzero(rungs <= rung)
            if (prefix.size * N_TRANSITIONS != budget
                    or not np.array_equal(prefix, np.arange(budget // N_TRANSITIONS))
                    or int((roles[prefix] == ROLE_SELECTION).sum()) * N_TRANSITIONS
                    != budget // GROUP_SIZE
                    or int((roles[prefix] == ROLE_FIT).sum()) * N_TRANSITIONS
                    != 3 * budget // GROUP_SIZE):
                ok_budgets = False
        if not ok_budgets:
            failures['budget_counts'].append(wpid)

        reset_ok = True
        for episode in range(n_episodes):
            head = support[episode, 0]
            reset_ok &= (int(np.argmax(head[SL_RECORD_TYPE])) == RT_RESET
                         and not head[SL_ACTION].any() and not head[SL_SOURCE].any()
                         and head[IX_DOSE] == 0 and head[IX_SENSOR] == 0
                         and head[IX_SENSOR_PRESENT] == 0
                         and bool(head[SL_DESTINATION.start + DESTINATION_NONE]
                                  == (1.0 if RESET_DESTINATION_IS_NONE else 0.0)))
        latent0 = private['support_latent'][:, 0, :]
        reset_ok &= bool((latent0 == 0).all())
        if not reset_ok:
            failures['reset_scope'].append(wpid)

        present = arrays['support_observed_present'].astype(bool)
        targets = arrays['support_observed_target']
        observed_rows = support[:, 2::2, :]
        if not ((targets[~present] == 0.0).all()
                and (observed_rows[..., IX_SENSOR][~present] == 0.0).all()
                and (observed_rows[..., IX_SENSOR_PRESENT] == present).all()):
            failures['missing_is_zero'].append(wpid)
        if not np.array_equal(observed_rows[..., IX_SENSOR], targets):
            failures['observed_target_consistency'].append(wpid)
        query_rows = support[:, 1::2, :]
        if not ((query_rows[..., IX_SENSOR] == 0).all()
                and (query_rows[..., IX_SENSOR_PRESENT] == 0).all()):
            failures['query_no_target'].append(wpid)

        qrecords = arrays['query_records']
        qn = arrays['query_n_records']
        qindex = arrays['query_index']
        truth = {row2['record_id']: row2 for row2 in private['query_truth']}
        ids = read_json(root / 'public' / wpid / 'query_record_ids.json')
        for slot, record_id in enumerate(ids):
            entry = truth[record_id]
            n = int(qn[slot])
            final = int(qindex[slot])
            sequence = qrecords[slot]
            if (sequence[final, SL_RECORD_TYPE][RT_QUERY] != 1.0
                    or sequence[final, IX_SENSOR] != 0.0
                    or sequence[final, IX_SENSOR_PRESENT] != 0.0
                    or bool(sequence[n:].any())):
                failures['query_no_target'].append(f'{wpid}/{record_id}')
            noisy32 = np.float32(entry['noisy_target'])
            if noisy32 != 0 and bool((sequence == noisy32).any()):
                failures['query_no_target'].append(f'{wpid}/{record_id}/target-in-prefix')
            prefix_records = 1 + 2 * int(entry['prefix_length'])
            blanks = sequence[prefix_records + 1:final:2]
            if blanks.size and not ((blanks[:, IX_SENSOR] == 0).all()
                                    and (blanks[:, IX_SENSOR_PRESENT] == 0).all()):
                failures['blank_forecast_observations'].append(f'{wpid}/{record_id}')

        by_panel: dict[int, list[dict[str, Any]]] = {}
        for entry in private['query_truth']:
            by_panel.setdefault(entry['panel'], []).append(entry)
        if (len(private['query_truth']) != 96
                or sorted(by_panel) != [1, 2, 3, 4]
                or len(by_panel[1]) != 16 or len(by_panel[2]) != 16
                or len(by_panel[3]) != 32 or len(by_panel[4]) != 32
                or sorted(e['horizon'] for e in by_panel[1]) != sorted(PANEL1_HORIZONS)):
            failures['panel_composition'].append(wpid)
        panel_sequence = [truth[record_id]['panel'] for record_id in ids]
        if panel_sequence == sorted(panel_sequence):
            failures['query_order_not_grouped'].append(wpid)

        pairs4 = {}
        for entry in by_panel[4]:
            pairs4.setdefault(entry['pair_key'], {})[entry['branch']] = entry
        if not all(abs(p['base']['noise_free_response']
                       - p['edited']['noise_free_response']) <= 1e-12
                   for p in pairs4.values()):
            failures['nuisance_edit_invariance'].append(wpid)

        pairs3 = {}
        for entry in by_panel[3]:
            pairs3.setdefault(entry['pair_key'], {})[entry['branch']] = entry
        differences = [abs(p['treated']['noise_free_response']
                           - p['control']['noise_free_response'])
                       for p in pairs3.values()]
        if family in ('c', 'm'):
            if min(differences) <= 1e-9:
                failures['intervention_differences'].append(wpid)
        elif max(differences) != 0.0:
            failures['intervention_differences'].append(wpid)

        # --- ruling B1, verified from the serialized bytes alone ----------------------
        public_to_verb = {int(public): INTERNAL_VERBS.index(name)
                          for name, public in row['verb_to_public'].items()}
        for slot, record_id in enumerate(ids):
            entry = truth[record_id]
            n = int(qn[slot])
            verbs = [public_to_verb[int(np.argmax(qrecords[slot, r, SL_ACTION]))]
                     for r in range(1, n, 2)]
            if len(verbs) != N_TRANSITIONS:
                failures['panel_action_strings_exclude_reserved'].append(
                    f'{wpid}/{record_id}/length')
                continue
            is_composition = (entry['panel'] == PANEL_COMPOSITION
                              or (entry['panel'] == PANEL_IRRELEVANT_PAIR
                                  and entry['unit'] >= 8))
            if is_composition:
                ok = (not contains_reserved_composition(verbs[:4])
                      and tuple(verbs[4:]) == RESERVED_COMPOSITION)
            else:
                ok = not contains_reserved_composition(verbs)
            if not ok:
                failures['panel_action_strings_exclude_reserved'].append(
                    f'{wpid}/{record_id}')

        # --- fitting-audit set --------------------------------------------------------
        audit_rows = private['audit_truth']
        audit_records = arrays['audit_records']
        audit_n = arrays['audit_n_records']
        audit_ix = arrays['audit_index']
        expected_audit: list[tuple[int, int, int]] = []
        for episode in range(n_episodes):
            if episode_role(episode) != ROLE_FIT:
                continue
            for horizon in AUDIT_HORIZONS:
                endpoint = last_eligible_observed_endpoint(present[episode], horizon)
                if endpoint is not None:
                    expected_audit.append((episode, horizon, endpoint))
        got_audit = [(int(a), int(b), int(c)) for a, b, c in
                     zip(arrays['audit_episode_index'], arrays['audit_horizon'],
                         arrays['audit_endpoint'])]
        keys = read_json(root / 'public' / wpid / 'audit_keys.json')
        if (got_audit != expected_audit
                or len(audit_rows) != len(expected_audit)
                or [k['audit_id'] for k in keys] != [a['audit_id'] for a in audit_rows]
                or [a['audit_id'] for a in audit_rows]
                != [audit_key(wpid, e, h, t) for e, h, t in expected_audit]
                or audit_records.shape[1:] != (N_RECORDS_FULL, RECORD_WIDTH)):
            failures['audit_set_definition'].append(wpid)
        for slot, entry in enumerate(audit_rows):
            n = int(audit_n[slot])
            final = int(audit_ix[slot])
            sequence = audit_records[slot]
            if (n != 2 * entry['endpoint'] or final != n - 1
                    or sequence[final, SL_RECORD_TYPE][RT_QUERY] != 1.0
                    or sequence[final, IX_SENSOR] != 0.0
                    or sequence[final, IX_SENSOR_PRESENT] != 0.0
                    or bool(sequence[n:].any())):
                failures['audit_no_target'].append(f'{wpid}/{entry["audit_id"]}')
            label32 = np.float32(entry['observed_label'])
            if label32 != 0 and bool((sequence == label32).any()):
                failures['audit_no_target'].append(
                    f'{wpid}/{entry["audit_id"]}/label-in-prefix')
            if (float(targets[entry['episode_index'], entry['endpoint'] - 1])
                    != np.float32(entry['observed_label'])
                    or not bool(present[entry['episode_index'], entry['endpoint'] - 1])
                    or float(arrays['audit_observed_label'][slot])
                    != np.float32(entry['observed_label'])):
                failures['audit_label_matches_public_support'].append(
                    f'{wpid}/{entry["audit_id"]}')

        support_signatures = {tensor_hash(support[e, 0, SL_PROPERTIES])
                              for e in range(n_episodes)}
        query_signatures = {tensor_hash(qrecords[s, 0, SL_PROPERTIES])
                            for s in range(96)}
        if support_signatures & query_signatures:
            failures['episode_disjointness'].append(wpid)

    aliases = list(config)
    if len(set(aliases)) != len(aliases):
        failures['episode_disjointness'].append('duplicate alias')
    for name, bad_worlds in failures.items():
        record(name, not bad_worlds, f'{bad_worlds[:5]}')

    passed = sum(1 for c in checks if c['pass'])
    return {'version': VERSION, 'root': str(root), 'checks': checks,
            'passed': passed, 'failed': len(checks) - passed}


# --------------------------------------------------------------------------------------
# 9.  evaluate -- private scorer, joined to predictions by opaque record ID only
# --------------------------------------------------------------------------------------

STAGE_INITIAL, STAGE_FINAL = 'initial', 'final'
STAGES = (STAGE_INITIAL, STAGE_FINAL)


def load_predictions(path: Path) -> list[dict[str, Any]]:
    """Accepts JSON or CSV rows.

    Required: `prediction`, plus either `record_id` (a query record ID or a fitting-audit
    ID) or the four audit fields `world_public_id`, `episode_index`, `horizon`,
    `endpoint`, which are folded into the one registered audit key.

    Optional: `arm`, `seed`, `rung`, and `stage` in {'initial','final'}.  A missing
    stage means 'final', so a ct20-v1 prediction file still scores unchanged.

    There is one audit-key spelling and one only (rulings 2): the canonical key in
    SCHEMA.md section 3, which the models builder now produces by calling
    `PublicDataset.audit_key` itself.
    """
    path = Path(path)
    if path.suffix.lower() == '.csv':
        with open(path, newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
    else:
        payload = read_json(path)
        rows = payload['predictions'] if isinstance(payload, dict) else payload
    out = []
    for row in rows:
        record_id = row.get('record_id')
        if not record_id and all(row.get(field) not in (None, '') for field in
                                 ('world_public_id', 'episode_index', 'horizon',
                                  'endpoint')):
            record_id = audit_key(str(row['world_public_id']), int(row['episode_index']),
                                  int(row['horizon']), int(row['endpoint']))
        if not record_id or 'prediction' not in row:
            raise ValueError('every prediction row needs a prediction and either a '
                             'record_id or world_public_id/episode_index/horizon/'
                             'endpoint')
        stage = str(row.get('stage', STAGE_FINAL) or STAGE_FINAL).lower()
        if stage not in STAGES:
            raise ValueError(f'stage must be one of {STAGES}, got {stage!r}')
        out.append({'record_id': str(record_id),
                    'prediction': float(row['prediction']),
                    'arm': str(row.get('arm', '')), 'seed': str(row.get('seed', '')),
                    'rung': str(row.get('rung', '')), 'stage': stage})
    return out


def _mse(pred: np.ndarray, truth: np.ndarray) -> float:
    return float(np.mean((pred - truth) ** 2)) if pred.size else float('nan')


def startup_classification(l_initial: float, l_final: float, e_fit_final: float,
                           e_query_final: float | None = None,
                           complete: bool = True,
                           incomplete_detail: str = '') -> dict[str, Any]:
    """Ruling C9, evaluated in binary64 exactly as written.

        never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)

    No rounding, no library `isclose`, and no tolerance is applied to any other
    threshold.  Failure and incomplete statuses take precedence over every label, so a
    missing or non-finite required measurement can never become a successful start-up.
    """
    l_initial = float(l_initial) if l_initial is not None else float('nan')
    l_final = float(l_final) if l_final is not None else float('nan')
    e_fit_final = float(e_fit_final) if e_fit_final is not None else float('nan')
    out: dict[str, Any] = {
        'L_initial': l_initial, 'L_final': l_final, 'E_fit_final': e_fit_final,
        'E_query_final': (None if e_query_final is None else float(e_query_final)),
        'relative_improvement': None, 'never_started': None,
        'threshold': STARTUP_IMPROVEMENT_THRESHOLD - STARTUP_RELATIVE_TOLERANCE,
    }
    if not complete:
        out['status'] = 'infrastructure_incomplete'
        out['detail'] = incomplete_detail or 'a required audit or query result is missing'
        return out
    if not (math.isfinite(l_initial) and math.isfinite(l_final)
            and math.isfinite(e_fit_final)):
        out['status'] = 'numerical_failure'
        out['detail'] = 'a required measurement is NaN or Inf'
        return out
    if l_initial <= STARTUP_INITIAL_FLOOR:
        out['status'] = 'initially_at_floor'
        out['detail'] = f'L_initial <= {STARTUP_INITIAL_FLOOR}'
        return out
    r = (l_initial - l_final) / l_initial          # binary64, exactly as ruled
    out['relative_improvement'] = r
    if not math.isfinite(r):
        out['status'] = 'numerical_failure'
        out['detail'] = 'relative improvement is not finite'
        return out
    never_started = bool(
        (r < STARTUP_IMPROVEMENT_THRESHOLD - STARTUP_RELATIVE_TOLERANCE)
        and (e_fit_final >= STARTUP_NEVER_STARTED_FITTING_E))
    out['never_started'] = never_started
    if never_started:
        out['status'] = 'never_started'
        out['detail'] = ''
        return out
    if e_fit_final > LEARNED_FITTING_E:
        out['status'] = 'started_not_yet_learned'
        out['detail'] = ('escaped the never-started criterion but did not reach '
                         f'fitting E <= {LEARNED_FITTING_E}')
        return out
    if e_query_final is None or not math.isfinite(float(e_query_final)):
        out['status'] = 'infrastructure_incomplete'
        out['detail'] = 'fitting E is at the learned mark but final query E is missing'
        return out
    if float(e_query_final) > TRANSFER_QUERY_E:
        out['status'] = 'learned_failed_to_transfer'
    else:
        out['status'] = 'learned_with_generalization'
        out['reached_query_0_25'] = bool(float(e_query_final) <= QUERY_E_TARGET)
    out['detail'] = ''
    return out


def evaluate_predictions(private_root: Path, predictions: Sequence[dict[str, Any]]
                         ) -> dict[str, Any]:
    private_root = Path(private_root)
    if (private_root / 'private').is_dir():
        private_root = private_root / 'private'
    config = read_json(private_root / 'world_config.json')
    normalization = read_json(private_root / 'normalization.json')
    truth: dict[str, dict[str, Any]] = {}
    audit_truth: dict[str, dict[str, Any]] = {}
    for wpid in config:
        for entry in read_json(private_root / wpid / 'query_truth.json'):
            truth[entry['record_id']] = entry
        audit_path = private_root / wpid / 'audit_truth.json'
        if audit_path.exists():
            for entry in read_json(audit_path):
                audit_truth[entry['audit_id']] = entry

    groups: dict[tuple[str, str, str, str], dict[str, float]] = {}
    audit_groups: dict[tuple[str, str, str], dict[str, float]] = {}
    unknown = []
    for row in predictions:
        # `.get` so a dict built in-process, not through load_predictions, still scores;
        # an absent stage means the final stage, exactly as the file contract says.
        arm, seed = str(row.get('arm', '')), str(row.get('seed', ''))
        rung, stage = str(row.get('rung', '')), str(row.get('stage', STAGE_FINAL))
        if row['record_id'] in truth:
            groups.setdefault((arm, seed, rung, stage), {})[
                row['record_id']] = row['prediction']
        elif row['record_id'] in audit_truth:
            audit_groups.setdefault((arm, seed, stage), {})[
                row['record_id']] = row['prediction']
        else:
            unknown.append(row['record_id'])

    query_e: dict[tuple[str, str, str, str, str], float] = {}
    results = []
    for (arm, seed, rung, stage), lookup in sorted(groups.items()):
        per_world = []
        for wpid, row in sorted(config.items()):
            entries = [truth[rid] for rid in truth
                       if truth[rid]['world_public_id'] == wpid]
            have = [e for e in entries if e['record_id'] in lookup]
            if not have:
                continue
            key = f"{row['outer_split']}/A/{row['family']}"
            v = float(normalization[key]['V'])
            pred = np.asarray([lookup[e['record_id']] for e in have], dtype=np.float64)
            nf = np.asarray([e['noise_free_response'] for e in have], dtype=np.float64)
            noisy = np.asarray([e['noisy_target'] for e in have], dtype=np.float64)

            def panel_error(panel: int, branch: str | None = None) -> float:
                rows = [(lookup[e['record_id']], e['noise_free_response'])
                        for e in have if e['panel'] == panel
                        and (branch is None or e['branch'] == branch)]
                if not rows:
                    return float('nan')
                p = np.asarray([r[0] for r in rows]); t = np.asarray([r[1] for r in rows])
                return _mse(p, t) / v

            # Ruling R1 (rulings 2): E_primary = (E_panel1 + E_panel2)/2, where E_panel1 is
            # the EQUAL average of the three horizon-specific means -- NOT a flat mean over
            # panel 1's 6/5/5 targets -- and E_panel2 is the equal average of panel 2's 16
            # units (one target each, so a flat mean over them is that same average).
            # Panel-4 branches never reach either term even when their recipe is ordinary
            # or composition, because a target carries the panel that OWNS it (panel 4),
            # not the panel its recipe imitates.
            #
            # A missing case invalidates rather than silently shortening a denominator
            # (rulings 2 R2): a horizon short of its registered count, or a panel 2 short
            # of 16, yields NaN instead of an average over whatever happened to arrive.
            horizon_means = []
            for horizon in PANEL1_HORIZON_LEVELS:
                rows = [(lookup[e['record_id']], e['noise_free_response'])
                        for e in have if e['panel'] == PANEL_ORDINARY
                        and e['horizon'] == horizon]
                expected = sum(1 for h in PANEL1_HORIZONS if h == horizon)
                horizon_means.append(
                    _mse(np.asarray([r[0] for r in rows]),
                         np.asarray([r[1] for r in rows])) / v
                    if len(rows) == expected else float('nan'))
            e_panel1 = float(np.mean(horizon_means))
            n_panel2 = sum(1 for e in have if e['panel'] == PANEL_COMPOSITION)
            e_panel2 = (panel_error(PANEL_COMPOSITION) if n_panel2 == UNITS_PER_PANEL
                        else float('nan'))
            e_primary = float(np.mean([e_panel1, e_panel2]))

            def pair_metrics(panel: int, first: str, second: str) -> dict[str, float]:
                pairs: dict[str, dict[str, Any]] = {}
                for e in have:
                    if e['panel'] == panel:
                        pairs.setdefault(e['pair_key'], {})[e['branch']] = e
                complete = [p for p in pairs.values() if first in p and second in p]
                if not complete:
                    return {'n_pairs': 0}
                dp = np.asarray([lookup[p[first]['record_id']]
                                 - lookup[p[second]['record_id']] for p in complete])
                dt = np.asarray([p[first]['noise_free_response']
                                 - p[second]['noise_free_response'] for p in complete])
                return {'n_pairs': len(complete),
                        'difference_mse_over_V': _mse(dp, dt) / v,
                        'between_branch_mse_over_V': float(np.mean(dp ** 2)) / v,
                        f'E_{first}': panel_error(panel, first),
                        f'E_{second}': panel_error(panel, second)}

            query_e[(arm, seed, stage, rung, wpid)] = e_primary
            per_world.append({
                'world_public_id': wpid, 'outer_split': row['outer_split'],
                'family': row['family'], 'V': v,
                'analytic_sensor_floor': ANALYTIC_SENSOR_VARIANCE / v,
                'n_targets_expected': len(entries), 'n_targets_scored': len(have),
                'complete': len(have) == len(entries),
                'raw_noisy_mse': _mse(pred, noisy),
                'raw_noise_free_mse': _mse(pred, nf),
                'E_all_targets': _mse(pred, nf) / v,
                'E_panel1_ordinary': e_panel1,
                'E_panel1_by_horizon': dict(zip(('h1', 'h2', 'h4'), horizon_means)),
                'E_panel2_composition': e_panel2,
                'E_primary': e_primary,
                'panel3_relevant_pairs': pair_metrics(
                    PANEL_RELEVANT_PAIR, 'treated', 'control'),
                'panel4_irrelevant_pairs': pair_metrics(
                    PANEL_IRRELEVANT_PAIR, 'base', 'edited'),
            })
        families: dict[str, Any] = {}
        for world in per_world:
            key = f"{world['outer_split']}/{world['family']}"
            families.setdefault(key, []).append(world['E_primary'])
        results.append({
            'arm': arm, 'seed': seed, 'rung': rung, 'stage': stage,
            'worlds': per_world,
            'mean_E_primary_by_split_family': {
                k: float(np.mean(v)) for k, v in sorted(families.items())},
            'complete': all(w['complete'] for w in per_world),
        })

    startup = _startup_diagnostics(config, normalization, audit_truth, audit_groups,
                                   query_e)
    return _json_safe({'version': VERSION, 'n_predictions': len(predictions),
            'unknown_record_ids': unknown[:20],
            'n_unknown_record_ids': len(unknown), 'groups': results,
            'startup_diagnostics': startup,
            'note': ('Scored from frozen private files only; no simulator object is '
                     'required.  Predictions join to truth by opaque record ID, and '
                     'fitting-audit predictions by the registered '
                     'episode/horizon/endpoint key.  A non-finite or absent measurement '
                     'serializes as null; its meaning is carried by the accompanying '
                     'status field, never by a rounded number.')})


def _pick_final_query_e(query_e: dict[tuple[str, str, str, str, str], float],
                        arm: str, seed: str, stage: str,
                        wpid: str) -> tuple[float | None, str, str]:
    """The query E for this stage.  One rung -> that rung.  Several numeric rungs ->
    the largest, which is the registered B=512 endpoint.  Otherwise ambiguous."""
    candidates = {rung: value for (a, s, st, rung, w), value in query_e.items()
                  if (a, s, st, w) == (arm, seed, stage, wpid)}
    if not candidates:
        return None, '', 'no query predictions at this stage'
    if len(candidates) == 1:
        rung, value = next(iter(candidates.items()))
        return value, rung, ''
    try:
        rung = max(candidates, key=lambda r: float(r))
    except ValueError:
        return None, '', f'ambiguous rung labels {sorted(candidates)}'
    return candidates[rung], rung, ''


def _startup_diagnostics(config: dict[str, Any], normalization: dict[str, Any],
                         audit_truth: dict[str, dict[str, Any]],
                         audit_groups: dict[tuple[str, str, str], dict[str, float]],
                         query_e: dict[tuple[str, str, str, str, str], float]
                         ) -> list[dict[str, Any]]:
    """Ruling C10: the evaluator finalises the start-up diagnostic from sealed
    predictions alone.  Nothing here can reach a trainer or change an update schedule."""
    if not audit_truth:
        return []
    by_world: dict[str, list[dict[str, Any]]] = {}
    for entry in audit_truth.values():
        by_world.setdefault(entry['world_public_id'], []).append(entry)
    for rows in by_world.values():
        rows.sort(key=lambda e: (e['episode_index'], e['horizon'], e['endpoint']))

    cases = sorted({(arm, seed) for arm, seed, _stage in audit_groups})
    out: list[dict[str, Any]] = []
    for arm, seed in cases:
        for wpid, rows in sorted(by_world.items()):
            world_row = config[wpid]
            v = float(normalization[f"{world_row['outer_split']}/A/"
                                    f"{world_row['family']}"]['V'])
            expected = [e['audit_id'] for e in rows]
            stage_stats: dict[str, dict[str, Any]] = {}
            missing: list[str] = []
            for stage in STAGES:
                lookup = audit_groups.get((arm, seed, stage), {})
                have = [e for e in rows if e['audit_id'] in lookup]
                if len(have) != len(expected):
                    missing.append(f'{stage}:{len(have)}/{len(expected)}')
                if not have:
                    stage_stats[stage] = {'L': float('nan'), 'E_fit': float('nan'),
                                          'n_cases': 0}
                    continue
                pred = np.asarray([lookup[e['audit_id']] for e in have],
                                  dtype=np.float64)
                observed = np.asarray([e['observed_label'] for e in have],
                                      dtype=np.float64)
                nf = np.asarray([e['noise_free_response'] for e in have],
                                dtype=np.float64)
                stage_stats[stage] = {
                    'L': _mse(pred, observed) / LOSS_NORMALIZATION_CONSTANT,
                    'raw_observed_mse': _mse(pred, observed),
                    'E_fit': _mse(pred, nf) / v,
                    'n_cases': len(have),
                }
            e_query_final, final_rung, query_detail = _pick_final_query_e(
                query_e, arm, seed, STAGE_FINAL, wpid)
            e_query_initial, initial_rung, _ = _pick_final_query_e(
                query_e, arm, seed, STAGE_INITIAL, wpid)
            detail = '; '.join(x for x in
                               [f'incomplete audit coverage {missing}' if missing else '',
                                query_detail] if x)
            verdict = startup_classification(
                stage_stats[STAGE_INITIAL]['L'], stage_stats[STAGE_FINAL]['L'],
                stage_stats[STAGE_FINAL]['E_fit'], e_query_final,
                complete=not missing and e_query_final is not None,
                incomplete_detail=detail)
            verdict.update({
                'arm': arm, 'seed': seed, 'world_public_id': wpid,
                'outer_split': world_row['outer_split'], 'family': world_row['family'],
                'V': v,
                'n_audit_cases_expected': len(expected),
                'n_audit_cases_initial': stage_stats[STAGE_INITIAL]['n_cases'],
                'n_audit_cases_final': stage_stats[STAGE_FINAL]['n_cases'],
                'E_fit_initial': stage_stats[STAGE_INITIAL]['E_fit'],
                'E_query_initial': e_query_initial,
                'query_rung_used_initial': initial_rung,
                'query_rung_used_final': final_rung,
            })
            out.append(verdict)
    return out


# --------------------------------------------------------------------------------------
# 10.  CLI
# --------------------------------------------------------------------------------------

def _directory_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)

    calibration = sub.add_parser('calibration-data',
                                 help='generate the frozen pilot calibration files')
    calibration.add_argument('--out', required=True)

    fixture = sub.add_parser('fixture', help='write the readable interface fixture')
    fixture.add_argument('--out', required=True)

    audit = sub.add_parser('audit', help='re-verify a generated directory')
    audit.add_argument('--data', required=True)

    evaluate = sub.add_parser('evaluate', help='private scorer, joined by record ID')
    evaluate.add_argument('--predictions', required=True)
    evaluate.add_argument('--private', required=True)
    evaluate.add_argument('--out', required=True)

    args = parser.parse_args(argv)

    if args.command == 'calibration-data':
        manifest = generate_calibration_data(Path(args.out))
        print(canonical_json({
            'stage': manifest['stage'],
            'worlds': len(read_json(Path(args.out) / 'private' / 'world_config.json')),
            'files': len(manifest['file_hashes']),
            'bytes': _directory_bytes(Path(args.out)),
            'manifest_sha256': file_hash(Path(args.out) / 'manifest.json'),
        }))
        return 0

    if args.command == 'fixture':
        manifest = generate_fixture(Path(args.out))
        print(canonical_json({
            'stage': manifest['stage'], 'families': manifest['families_present'],
            'files': len(manifest['file_hashes']),
            'bytes': _directory_bytes(Path(args.out)),
            'manifest_sha256': file_hash(Path(args.out) / 'manifest.json'),
        }))
        return 0

    if args.command == 'audit':
        report = audit_directory(Path(args.data))
        write_json(Path(args.data) / 'audit_report.json', report)
        for check in report['checks']:
            status = 'PASS' if check['pass'] else 'FAIL'
            print(f"{status}  {check['check']}"
                  + ('' if check['pass'] else f"  -- {check['detail']}"))
        print(canonical_json({'passed': report['passed'], 'failed': report['failed']}))
        return 0 if report['failed'] == 0 else 1

    report = evaluate_predictions(Path(args.private), load_predictions(Path(args.predictions)))
    write_json(Path(args.out), report)
    print(canonical_json({'groups': len(report['groups']),
                          'n_predictions': report['n_predictions'],
                          'n_unknown_record_ids': report['n_unknown_record_ids']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
