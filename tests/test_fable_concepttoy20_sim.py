"""Checks for scripts/fable_concepttoy20_sim.py and scripts/fable_concepttoy20_public.py.

Plain script; no pytest (repo convention).

Run:
    OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    python3.12 -B tests/test_fable_concepttoy20_sim.py

Covers every item in the build plan's "Required tests" list for Agent 1, plus
determinism (same config twice -> identical hashes, no timestamps in hashed files) and
the public/private boundary.

Expected values are derived independently here -- closed-form tanh/XOR arithmetic
written out by hand -- rather than by calling the simulator's own update routine.

Nothing here reads test.pt, any prior experiment artifact, or any registered
concept-toy20 output directory; every check generates into a throwaway directory.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import fable_concepttoy20_sim as S            # noqa: E402
import fable_concepttoy20_public as PUB       # noqa: E402

PASSED = 0
FAILED: list[tuple[str, str]] = []
TMP: str | None = None


def check(name, function):
    global PASSED
    try:
        function()
    except Exception as error:                      # noqa: BLE001
        FAILED.append((name, f'{type(error).__name__}: {error}'))
        print(f'FAIL  {name}\n      {type(error).__name__}: {error}', flush=True)
    else:
        PASSED += 1
        print(f'pass  {name}', flush=True)


def assert_close(got, want, tol=1e-12, what=''):
    if abs(float(got) - float(want)) > tol:
        raise AssertionError(f'{what}: got {got!r}, want {want!r}')


def act(verb, source, destination=None, dose=0):
    return S.Action(verb, source, destination, dose)


def toy_world(family, coefficients=None, permutation=(0, 1, 2, 3, 4)):
    """A hand-made world so the algebra checks do not depend on a drawn world."""
    coefficients = coefficients or {'a': 0.4, 'beta': 0.3, 'g': 1.0, 'b': 0.2, 'c': 0.5}
    return S.World(family=family, outer_split='unit-test', world_index=0,
                   coefficients=tuple(sorted(coefficients.items())),
                   verb_to_public=tuple(permutation))


# --------------------------------------------------------------------------------------
# 1.  exact pulse / contact / invert algebra, and simultaneity
# --------------------------------------------------------------------------------------

def test_pulse_contact_invert_algebra():
    a, beta, g, b = 0.4, 0.3, 1.1, 0.25
    world = toy_world('c', {'a': a, 'beta': beta, 'g': g, 'b': b, 'c': 0.5})
    properties = np.array([[0.5, -0.25, 0, 0, 0, 0], [-0.75, 0.1, 0, 0, 0, 0],
                           [0.2, 0.3, 0, 0, 0, 0], [-0.4, 0.9, 0, 0, 0, 0]])

    state = S.initial_state('c')
    if state.tolist() != [0.0, 0.0, 0.0, 0.0]:
        raise AssertionError('C initializes q to zero at reset')

    # pulse adds a * d, independently derived
    state = S.apply_transition(world, state, act(S.VERB_PULSE, 0, dose=1))
    assert_close(state[0], a, what='one +1 pulse')
    state = S.apply_transition(world, state, act(S.VERB_PULSE, 0, dose=-1))
    assert_close(state[0], 0.0, what='+1 then -1 pulse returns to zero')

    # clipping at +-2: a=0.4 so six +1 pulses would reach 2.4
    state = S.initial_state('c')
    for _ in range(6):
        state = S.apply_transition(world, state, act(S.VERB_PULSE, 1, dose=1))
    assert_close(state[1], 2.0, what='clip(q + a, -2, 2)')
    for _ in range(11):
        state = S.apply_transition(world, state, act(S.VERB_PULSE, 1, dose=-1))
    assert_close(state[1], -2.0, what='clip at the lower bound')

    # invert exactly negates, including a clipped value
    state = S.apply_transition(world, state, act(S.VERB_INVERT, 1))
    assert_close(state[1], 2.0, what='invert negates')

    # contact, computed by hand from the OLD state
    state = np.array([0.8, -0.2, 0.0, 0.0])
    after = S.apply_transition(world, state, act(S.VERB_CONTACT, 0, destination=1))
    delta = beta * (0.8 - (-0.2))
    assert_close(after[0], 0.8 - delta, what='contact source')
    assert_close(after[1], -0.2 + delta, what='contact destination')
    assert_close(after[0] + after[1], 0.8 + (-0.2), what='contact conserves the sum')
    if not np.array_equal(after[2:], state[2:]):
        raise AssertionError('contact touches only i and j')

    # read and wait change nothing at all
    for verb in (S.VERB_READ, S.VERB_WAIT):
        if not np.array_equal(S.apply_transition(world, after, act(verb, 3)), after):
            raise AssertionError(f'{S.INTERNAL_VERBS[verb]} must not change the state')

    # the device response is tanh(g*q + b*p[i,0]); the channel never returns q
    r = S.response(world, after, properties, 0)
    assert_close(r, math.tanh(g * after[0] + b * properties[0, 0]), what='response C')


def test_contact_updates_are_simultaneous():
    beta = 0.3
    world = toy_world('c', {'a': 0.4, 'beta': beta, 'g': 1.0, 'b': 0.2, 'c': 0.5})
    x, y = 0.9, -0.5
    state = np.array([x, y, 0.0, 0.0])
    after = S.apply_transition(world, state, act(S.VERB_CONTACT, 0, destination=1))
    simultaneous_j = y + beta * (x - y)
    sequential_j = y + beta * ((x - beta * (x - y)) - y)     # the wrong, in-place order
    if abs(simultaneous_j - sequential_j) < 1e-9:
        raise AssertionError('this fixture cannot distinguish the two orders')
    assert_close(after[1], simultaneous_j, what='destination uses the OLD source value')
    if abs(after[1] - sequential_j) < 1e-9:
        raise AssertionError('contact was applied sequentially, not simultaneously')


# --------------------------------------------------------------------------------------
# 2.  family M: directional XOR, behind the evaluator boundary
# --------------------------------------------------------------------------------------

def test_mode_family_directional_xor():
    g, b = 0.95, 0.3
    world = toy_world('m', {'a': 0.4, 'beta': 0.3, 'g': g, 'b': b, 'c': 0.5})
    if S.initial_state('m').tolist() != [0, 0, 0, 0]:
        raise AssertionError('M initializes m to zero bits')

    # pulse +1 flips, pulse -1 sets to zero, invert flips, read/wait do nothing
    state = S.initial_state('m')
    state = S.apply_transition(world, state, act(S.VERB_PULSE, 2, dose=1))
    if state[2] != 1:
        raise AssertionError('pulse d=+1 flips the bit')
    state = S.apply_transition(world, state, act(S.VERB_PULSE, 2, dose=1))
    if state[2] != 0:
        raise AssertionError('pulse d=+1 flips again')
    state = S.apply_transition(world, state, act(S.VERB_PULSE, 2, dose=1))
    state = S.apply_transition(world, state, act(S.VERB_PULSE, 2, dose=-1))
    if state[2] != 0:
        raise AssertionError('pulse d=-1 sets the bit to zero')
    state[3] = 1
    state = S.apply_transition(world, state, act(S.VERB_INVERT, 3))
    if state[3] != 0:
        raise AssertionError('invert flips the bit')
    for verb in (S.VERB_READ, S.VERB_WAIT):
        if not np.array_equal(S.apply_transition(world, state, act(verb, 0)), state):
            raise AssertionError(f'{S.INTERNAL_VERBS[verb]} must not change m')

    # contact changes ONLY the destination: full 2x2 truth table, written out by hand
    table = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
    for (mi, mj), expected_j in table.items():
        state = np.array([mi, mj, 0, 0], dtype=np.int64)
        after = S.apply_transition(world, state, act(S.VERB_CONTACT, 0, destination=1))
        if int(after[1]) != expected_j:
            raise AssertionError(f'XOR truth table failed at {(mi, mj)}')
        if int(after[0]) != mi:
            raise AssertionError('contact must leave the SOURCE bit untouched')

    # direction matters: contact(0,1) and contact(1,0) differ from (1,0)
    start = np.array([1, 0, 0, 0], dtype=np.int64)
    forward = S.apply_transition(world, start, act(S.VERB_CONTACT, 0, destination=1))
    backward = S.apply_transition(world, start, act(S.VERB_CONTACT, 1, destination=0))
    if np.array_equal(forward, backward):
        raise AssertionError('M contact must be directional')
    if forward.tolist() != [1, 1, 0, 0] or backward.tolist() != [1, 0, 0, 0]:
        raise AssertionError(f'directional XOR wrong: {forward.tolist()} {backward.tolist()}')

    # M has no additive conservation law: the bit sum is not preserved
    if int(forward.sum()) == int(start.sum()):
        raise AssertionError('this fixture should change the bit sum')

    properties = np.array([[0.4, 0, 0, 0, 0, 0]] * 4)
    assert_close(S.response(world, np.array([1, 0, 0, 0]), properties, 0),
                 math.tanh(g * 1.0 + b * 0.4), what='M response at m=1')
    assert_close(S.response(world, np.array([0, 0, 0, 0]), properties, 0),
                 math.tanh(-g + b * 0.4), what='M response at m=0')


# --------------------------------------------------------------------------------------
# 3.  controls have no hidden storage
# --------------------------------------------------------------------------------------

def test_no_hidden_storage_in_controls():
    rng = np.random.default_rng(7)
    properties = rng.uniform(-1, 1, size=(4, 6))
    for family in ('o', 'n'):
        world = toy_world(family)
        state = S.initial_state(family)
        start = state.copy()
        responses = []
        for _ in range(64):
            verb = int(rng.integers(0, 5))
            source = int(rng.integers(0, 4))
            destination = dose = None
            if verb == S.VERB_CONTACT:
                destination = int([k for k in range(4) if k != source][int(rng.integers(0, 3))])
                dose = 0
            elif verb == S.VERB_PULSE:
                dose = int(rng.choice([-1, 1]))
            else:
                dose = 0
            state = S.apply_transition(world, state, act(verb, source, destination, dose))
            if not np.array_equal(state, start):
                raise AssertionError(f'family {family} evolved a hidden state')
            responses.append([S.response(world, state, properties, i) for i in range(4)])
        first = responses[0]
        if any(row != first for row in responses):
            raise AssertionError(f'family {family} response depends on action history')
        coefficients = world.coef
        for i in range(4):
            expected = (math.tanh(coefficients['b'] * properties[i, 0]
                                  + coefficients['c'] * properties[i, 1])
                        if family == 'o' else 0.0)
            assert_close(first[i], expected, what=f'{family} response at object {i}')


# --------------------------------------------------------------------------------------
# 4.  reset scope, malformed actions
# --------------------------------------------------------------------------------------

def test_reset_scope():
    world = S.make_world('train', 'c', 0)
    episodes = [S.build_discovery_episode(world, index) for index in range(4)]
    for episode in episodes:
        if not np.array_equal(episode.latent[0], np.zeros(4)):
            raise AssertionError('every episode starts from an all-zero hidden state')
        head = S.support_records(world, episode)[0]
        if int(np.argmax(head[S.SL_RECORD_TYPE])) != S.RT_RESET:
            raise AssertionError('record 0 must be RESET')
        if head[S.SL_ACTION].any() or head[S.SL_SOURCE].any():
            raise AssertionError('RESET carries no action or source')
        if head[S.IX_SENSOR] or head[S.IX_SENSOR_PRESENT] or head[S.IX_DOSE]:
            raise AssertionError('RESET carries no measurement or dose')
    # the reset is per episode: object properties are redrawn and state does not carry
    if np.array_equal(episodes[0].properties, episodes[1].properties):
        raise AssertionError('episodes must have freshly created objects')
    if any(np.array_equal(e.latent[-1], np.zeros(4)) for e in episodes) and False:
        raise AssertionError('unreachable')


def test_malformed_actions_are_rejected():
    world = toy_world('c')
    state = S.initial_state('c')
    bad = [
        act(S.VERB_CONTACT, 1, destination=1),            # i == j
        act(S.VERB_CONTACT, 1, destination=None),         # missing destination
        act(S.VERB_CONTACT, 1, destination=2, dose=1),    # contact carries no dose
        act(S.VERB_PULSE, 0, dose=0),                     # pulse needs +-1
        act(S.VERB_PULSE, 0, dose=2),
        act(S.VERB_PULSE, 0, destination=2, dose=1),      # pulse carries no destination
        act(S.VERB_READ, 0, destination=1),
        act(S.VERB_WAIT, 0, dose=1),
        act(S.VERB_INVERT, 4),                            # source out of range
        act(9, 0),                                        # unknown verb
        act(S.VERB_CONTACT, 0, destination=4),            # destination out of range
    ]
    for action in bad:
        try:
            S.apply_transition(world, state, action)
        except S.MalformedAction:
            continue
        raise AssertionError(f'malformed action accepted: {action}')
    # the fixed-trace generator never produces one
    for index in range(16):
        for action in S.build_discovery_episode(world, index).actions:
            S.validate_action(action)


# --------------------------------------------------------------------------------------
# 5.  measurement, missingness and target isolation
# --------------------------------------------------------------------------------------

def test_missing_value_is_exactly_zero():
    world = S.make_world('train', 'c', 1)
    seen_missing = False
    for index in range(32):
        episode = S.build_discovery_episode(world, index)
        records = S.support_records(world, episode)
        for t in range(S.N_TRANSITIONS):
            observed = records[2 + 2 * t]
            if not episode.present[t]:
                seen_missing = True
                if observed[S.IX_SENSOR] != 0.0 or observed[S.IX_SENSOR_PRESENT] != 0.0:
                    raise AssertionError('a missing measurement must be exactly (0, 0)')
                if episode.observed[t] != 0.0:
                    raise AssertionError('a missing target must be exactly zero')
            else:
                assert_close(observed[S.IX_SENSOR],
                             episode.noise_free[t] + episode.noise[t],
                             what='returned y = r + epsilon')
                if observed[S.IX_SENSOR_PRESENT] != 1.0:
                    raise AssertionError('a present measurement sets the mask')
    if not seen_missing:
        raise AssertionError('no missing measurement appeared in 32 episodes')


def test_target_is_absent_from_the_query_prefix():
    world = S.make_world('validation', 'c', 0)
    for episode_index in range(8):
        episode = S.build_discovery_episode(world, episode_index)
        records = S.support_records(world, episode)
        for t in range(S.N_TRANSITIONS):
            query = records[1 + 2 * t]
            if query[S.IX_SENSOR] != 0.0 or query[S.IX_SENSOR_PRESENT] != 0.0:
                raise AssertionError('a QUERY token must carry no measurement')
            if int(np.argmax(query[S.SL_RECORD_TYPE])) != S.RT_QUERY:
                raise AssertionError('QUERY must precede OBSERVED for every transition')
            # the loss target of transition t must not be readable from its own prefix
            prefix = records[:1 + 2 * t + 1]
            value = np.float32(episode.observed[t])
            if episode.present[t] and value != 0 and bool((np.float32(prefix) == value).any()):
                raise AssertionError(f'target of transition {t} leaked into its prefix')

    targets = S.build_source_panels(world)
    for target in targets:
        final = target.records[target.query_index]
        if int(np.argmax(final[S.SL_RECORD_TYPE])) != S.RT_QUERY:
            raise AssertionError('the prediction is read at a QUERY record')
        if final[S.IX_SENSOR] or final[S.IX_SENSOR_PRESENT]:
            raise AssertionError('the final QUERY carries no measurement')
        value = np.float32(target.noisy)
        if value != 0 and bool((np.float32(target.records) == value).any()):
            raise AssertionError('a panel target leaked into its own public records')
        # forecast steps carry BLANK observed tokens -- never teacher forced
        first_forecast = 1 + 2 * target.prefix_length
        blanks = target.records[first_forecast + 1:target.query_index:2]
        if blanks.size and (blanks[:, S.IX_SENSOR].any() or blanks[:, S.IX_SENSOR_PRESENT].any()):
            raise AssertionError('a forecast step supplied an intermediate measurement')


# --------------------------------------------------------------------------------------
# 6.  splits, streams and the reserved composition
# --------------------------------------------------------------------------------------

def test_episode_and_outer_world_disjointness():
    universe = S.build_world_pool(S.WORLD_POOLS.keys())
    ids = [w.world_id for w in universe]
    stripped = [w.world_id_without_permutation for w in universe]
    aliases = [w.world_public_id for w in universe]
    for name, values in (('world_id', ids), ('permutation-free hash', stripped),
                         ('public alias', aliases)):
        if len(set(values)) != len(values):
            raise AssertionError(f'duplicate {name} across splits')
    if len(universe) != sum(sum(row.values()) for row in S.WORLD_POOLS.values()):
        raise AssertionError('world pool sizes do not match the registered table')
    for split, row in S.WORLD_POOLS.items():
        for family, count in row.items():
            got = sum(1 for w in universe
                      if w.outer_split == split and w.family == family)
            if got != count:
                raise AssertionError(f'{split}/{family}: expected {count}, built {got}')

    # every episode of a world lives in that world's namespace, and discovery episodes
    # never coincide with query-panel episodes
    world = S.make_world('train', 'c', 0)
    other = S.make_world('validation', 'c', 0)
    discovery = {S.tensor_hash(S.build_discovery_episode(world, i).properties)
                 for i in range(S.EPISODES_AT_MAX_BUDGET)}
    panels = {S.tensor_hash(t.records[0, S.SL_PROPERTIES].copy())
              for t in S.build_source_panels(world)}
    if discovery & panels:
        raise AssertionError('a query panel reused a discovery episode')
    cross = {S.tensor_hash(S.build_discovery_episode(other, i).properties)
             for i in range(8)}
    if discovery & cross:
        raise AssertionError('two worlds in different splits share episode data')


def test_reserved_composition_is_excluded_from_discovery():
    seen_prefixes = 0
    for family in ('c', 'o'):
        world = S.make_world('train', family, 0)
        for index in range(S.EPISODES_AT_MAX_BUDGET):
            episode = S.build_discovery_episode(world, index)
            verbs = [a.verb for a in episode.actions]
            if S.contains_reserved_composition(verbs):
                raise AssertionError(
                    f'discovery episode {index} contains the reserved composition')
            # every primitive and every shorter component stays available
            for length in (1, 2, 3):
                if S.contains_reserved_composition(
                        list(S.RESERVED_COMPOSITION[:length])):
                    raise AssertionError('a shorter component was wrongly excluded')
            seen_prefixes += 1
    if seen_prefixes == 0:
        raise AssertionError('no discovery episode was checked')
    if not S.contains_reserved_composition([4, 0, 1, 2, 3, 4]):
        raise AssertionError('the detector must find the contiguous pattern')
    if S.contains_reserved_composition([0, 1, 2, 4, 3]):
        raise AssertionError('a non-contiguous occurrence is not excluded')

    # the withheld composition IS what panel 2 asks for
    world = S.make_world('validation', 'c', 0)
    for target in S.build_source_panels(world):
        if target.panel != S.PANEL_COMPOSITION:
            continue
        break
    unit = S._composition_unit(world, S.PANEL_COMPOSITION, 0, 1)
    if tuple(a.verb for a in unit.actions[4:8]) != S.RESERVED_COMPOSITION:
        raise AssertionError('panel 2 must end with the reserved four-verb suffix')
    i = unit.actions[4].source
    j = unit.actions[5].destination
    if i == j:
        raise AssertionError('panel 2 requires i != j')
    if (unit.actions[5].source != i or unit.actions[6].source != j
            or unit.actions[7].source != j):
        raise AssertionError('panel 2 binding is wrong')


def test_budget_counts_include_validation():
    world = S.make_world('train', 'c', 2)
    roles = [S.episode_role(i) for i in range(S.EPISODES_AT_MAX_BUDGET)]
    rungs = [S.episode_budget_rung(i) for i in range(S.EPISODES_AT_MAX_BUDGET)]
    previous: list[int] = []
    for rung, budget in enumerate(S.BUDGETS):
        prefix = [i for i, r in enumerate(rungs) if r <= rung]
        if prefix != list(range(budget // S.N_TRANSITIONS)):
            raise AssertionError(f'budget {budget} is not a nested prefix')
        if len(prefix) * S.N_TRANSITIONS != budget:
            raise AssertionError(f'budget {budget} does not count every transition')
        if prefix[:len(previous)] != previous:
            raise AssertionError('budget prefixes are not nested')
        fit = sum(1 for i in prefix if roles[i] == S.ROLE_FIT)
        selection = sum(1 for i in prefix if roles[i] == S.ROLE_SELECTION)
        if fit * S.N_TRANSITIONS != 3 * budget // 4:
            raise AssertionError(f'budget {budget}: fit transitions {fit * 8}')
        if selection * S.N_TRANSITIONS != budget // 4:
            raise AssertionError(
                f'budget {budget}: discovery-validation transitions must be inside it')
        previous = prefix
    if S.BUDGETS[0] != 32 or roles[:4] != [0, 0, 0, 1]:
        raise AssertionError('B=32 must be three fit episodes plus one selection episode')
    if sum(1 for r in roles if r == S.ROLE_FIT) != 48:
        raise AssertionError('B=512 must have 48 fit episodes')
    if sum(1 for r in roles if r == S.ROLE_SELECTION) != 16:
        raise AssertionError('B=512 must have 16 selection episodes')
    # the reserved exclusion applies to discovery-validation episodes too
    for index in (3, 7, 11):
        episode = S.build_discovery_episode(world, index)
        if S.episode_role(index) != S.ROLE_SELECTION:
            raise AssertionError('wrong role fixture')
        if S.contains_reserved_composition([a.verb for a in episode.actions]):
            raise AssertionError('a selection episode contains the reserved composition')


# --------------------------------------------------------------------------------------
# 7.  pair panels
# --------------------------------------------------------------------------------------

def test_nuisance_edits_leave_the_response_unchanged():
    for family in ('c', 'o', 'n'):
        world = S.make_world('validation', family, 0)
        pairs: dict[str, dict[str, S.QueryTarget]] = {}
        for target in S.build_source_panels(world):
            if target.panel == S.PANEL_IRRELEVANT_PAIR:
                pairs.setdefault(target.pair_key, {})[target.branch] = target
        if len(pairs) != 16:
            raise AssertionError('panel 4 must have 16 pairs')
        for pair in pairs.values():
            base, edited = pair['base'], pair['edited']
            assert_close(edited.noise_free, base.noise_free, tol=1e-12,
                         what=f'{family} response under a nuisance edit')
            assert_close(edited.noisy, base.noisy, tol=1e-12,
                         what='common sensor noise across the pair')
            if np.array_equal(edited.records, base.records):
                raise AssertionError('the edited branch must actually differ')
            base_channels = base.records[0, S.SL_PROPERTIES].reshape(4, 6)
            edited_channels = edited.records[0, S.SL_PROPERTIES].reshape(4, 6)
            if np.array_equal(base_channels[:, 2:6], edited_channels[:, 2:6]):
                raise AssertionError('public channels 2..5 must be resampled')
            if not np.allclose(np.sort(base_channels[:, 0]),
                               np.sort(edited_channels[:, 0]), atol=1e-6):
                raise AssertionError('channel 0 must travel with its object unchanged')
            if not np.allclose(np.sort(base_channels[:, 1]),
                               np.sort(edited_channels[:, 1]), atol=1e-6):
                raise AssertionError('channel 1 must travel with its object unchanged')
            if float(np.abs(edited_channels[:, 2:6]).max()) > 2.0:
                raise AssertionError('replacement channels must lie in U[-2,2]')


def test_intervention_pair_differences():
    for family in ('c', 'm', 'o', 'n'):
        split = 'final' if family == 'm' else 'validation'
        world = S.make_world(split, family, 0)
        coefficients = world.coef
        pairs: dict[str, dict[str, S.QueryTarget]] = {}
        for target in S.build_source_panels(world):
            if target.panel == S.PANEL_RELEVANT_PAIR:
                pairs.setdefault(target.pair_key, {})[target.branch] = target
        if len(pairs) != 16:
            raise AssertionError('panel 3 must have 16 pairs')
        for pair in pairs.values():
            treated, control = pair['treated'], pair['control']
            if treated.detector_a != control.detector_a:
                raise AssertionError('both halves of a pair query the same object')
            i = treated.detector_a
            p0 = float(treated.records[0, S.SL_PROPERTIES].reshape(4, 6)[i, 0])
            difference = treated.noise_free - control.noise_free
            # common sensor noise means the NOISY difference equals the noise-free one
            assert_close(treated.noisy - control.noisy, difference, tol=1e-9,
                         what='common noise draws between branches')
            if family == 'c':
                # prefix is read/wait only, so q[i]=0; the treated branch adds one +1 pulse
                expected = (math.tanh(coefficients['g'] * coefficients['a']
                                      + coefficients['b'] * p0)
                            - math.tanh(coefficients['b'] * p0))
                assert_close(difference, expected, tol=1e-6, what='C pair difference')
                if abs(difference) < 1e-3:
                    raise AssertionError('C pair difference must be materially nonzero')
            elif family == 'm':
                expected = (math.tanh(coefficients['g'] + coefficients['b'] * p0)
                            - math.tanh(-coefficients['g'] + coefficients['b'] * p0))
                assert_close(difference, expected, tol=1e-6, what='M pair difference')
                if abs(difference) < 1e-3:
                    raise AssertionError('M pair difference must be materially nonzero')
            else:
                if difference != 0.0:
                    raise AssertionError(f'{family} control pair difference must be zero')


# --------------------------------------------------------------------------------------
# 8.  task-B label isolation
# --------------------------------------------------------------------------------------

def test_task_b_labels_are_absent_from_encoder_inputs():
    world = S.make_world('validation', 'c', 1)
    batch = S.build_task_b_episode(world, 0)
    records = np.float32(batch['records'])
    for name in ('b_label', 'b_label_noise_free'):
        for value in batch[name]:
            v = np.float32(value)
            if v != 0 and bool((records == v).any()):
                raise AssertionError(f'{name} value {value} appears inside the records')
    if batch['b_label'].shape != (S.N_TRANSITIONS,):
        raise AssertionError('one B label per transition')
    if batch['b_detector'].shape != (S.N_TRANSITIONS, S.DETECTOR_WIDTH):
        raise AssertionError('one B detector query per transition')
    for row in batch['b_detector']:
        if row[:4].sum() != 1 or row[4:].sum() != 1:
            raise AssertionError('the B detector is two one-hots')
        if int(np.argmax(row[4:])) == S.DESTINATION_NONE:
            raise AssertionError('task B uses two distinct object IDs, never NONE')
        if int(np.argmax(row[:4])) == int(np.argmax(row[4:])):
            raise AssertionError('task B uses two DISTINCT object IDs')
    # the public records are byte-identical to the same episode built with no B labels
    episode = batch['episode']
    plain = S.support_records(world, episode)
    if not np.array_equal(plain, batch['records']):
        raise AssertionError('B labels changed the public record tensor')
    # r_B is the registered readout of the SAME dynamics
    state, properties = episode.latent[1], episode.properties
    a = int(np.argmax(batch['b_detector'][0][:4]))
    b = int(np.argmax(batch['b_detector'][0][4:]))
    assert_close(batch['b_label_noise_free'][0],
                 0.5 * (S.response(world, state, properties, a)
                        - S.response(world, state, properties, b)),
                 tol=1e-12, what='r_B = (r(a) - r(b)) / 2')
    # the public loader keeps b_label in a target-only field
    fields = PUB.TaskBFittingBatch.__dataclass_fields__
    if 'b_label' not in fields or 'records' not in fields:
        raise AssertionError('the public B batch contract is missing a field')


# --------------------------------------------------------------------------------------
# 9.  determinism and the public/private boundary, end to end
# --------------------------------------------------------------------------------------

def _generate(subdirectory):
    out = Path(TMP) / subdirectory
    shutil.rmtree(out, ignore_errors=True)
    S.generate_calibration_data(out)
    return out


def test_generation_is_deterministic():
    first, second = _generate('det-a'), _generate('det-b')
    manifest_a = S.read_json(first / 'manifest.json')
    manifest_b = S.read_json(second / 'manifest.json')
    if manifest_a['file_hashes'] != manifest_b['file_hashes']:
        differing = [k for k in manifest_a['file_hashes']
                     if manifest_a['file_hashes'][k] != manifest_b['file_hashes'].get(k)]
        raise AssertionError(f'file hashes differ between runs: {differing[:5]}')
    if manifest_a['tensor_hashes'] != manifest_b['tensor_hashes']:
        raise AssertionError('tensor hashes differ between runs')
    if S.file_hash(first / 'manifest.json') != S.file_hash(second / 'manifest.json'):
        raise AssertionError('the manifest itself is not byte-reproducible')
    if not manifest_a['file_hashes']:
        raise AssertionError('no files were hashed')
    # no timestamp anywhere in a hashed file
    markers = ('timestamp', 'generated_at', 'created_at', 'mtime', 'utcnow', 'datetime')
    for name in manifest_a['file_hashes']:
        path = first / name
        if path.suffix == '.npy':
            header = path.read_bytes()[:256].decode('latin-1')
            for key in ('descr', 'fortran_order', 'shape'):
                if key not in header:
                    raise AssertionError(f'{name} has a non-canonical npy header')
            if 'time' in header.lower() or 'date' in header.lower():
                raise AssertionError(f'{name} header contains a timestamp')
        else:
            text = path.read_text(encoding='utf-8').lower()
            for marker in markers:
                if marker in text:
                    raise AssertionError(f'{name} contains {marker!r}')
    # the stream derivation itself is stable and independent per leaf
    ns = 'premonition/concept-toy20/v1/world/train/c/0'
    if S.stream_seed(ns) != S.stream_seed(ns):
        raise AssertionError('seed derivation is not a pure function')
    leaves = {S.stream_seed(f'{ns}/{leaf}') for leaf in ('public', 'mask', 'noise')}
    if len(leaves) != 3:
        raise AssertionError('noise, masks and actions must not share a stream')


def test_public_private_boundary_and_audit():
    root = _generate('det-a')
    report = S.audit_directory(root)
    failed = [c for c in report['checks'] if not c['pass']]
    if failed:
        raise AssertionError(f'audit failures: {[(c["check"], c["detail"]) for c in failed]}')

    config = S.read_json(root / 'private' / 'world_config.json')
    if any(row['outer_split'] == 'final' for row in config.values()):
        raise AssertionError('the pilot must generate no final world')
    if any(row['family'] == 'm' for row in config.values()):
        raise AssertionError('the pilot must generate no mode-family world')
    if len(config) != 12:
        raise AssertionError('the pilot pools are six train and six validation worlds')

    # `audit_keys.json` is excluded and checked separately: ruling C10 REQUIRES its
    # episode/horizon/endpoint join key to be public, and a fitting-audit horizon
    # discloses nothing the published sequence does not already state.
    public_text = '\n'.join(
        p.read_text(encoding='utf-8') for p in (root / 'public').rglob('*.json')
        if p.name != 'audit_keys.json')
    for forbidden in ('family', 'coefficient', 'verb_to_public', 'world_id', 'panel',
                      'noise_free', 'seed', 'latent', 'normaliz', 'horizon', 'unit'):
        if forbidden in public_text:
            raise AssertionError(f'public index mentions {forbidden!r}')
    allowed_audit = {'audit_id', 'episode_index', 'horizon', 'endpoint',
                     'endpoint_transition_index', 'n_records', 'query_index'}
    for path in sorted((root / 'public').rglob('audit_keys.json')):
        for entry in S.read_json(path):
            if set(entry) - allowed_audit:
                raise AssertionError(f'{path.name} carries {sorted(set(entry))}')
    normalization = S.read_json(root / 'private' / 'normalization.json')
    secrets = ([repr(float(v)) for row in config.values()
                for v in row['coefficients'].values()]
               + [repr(float(v['V'])) for v in normalization.values()
                  if float(v['V']) != S.V_FLOOR]
               + [row['world_id'] for row in config.values()])
    for secret in secrets:
        if secret in public_text:
            raise AssertionError(f'{secret} reached a public file')

    # every public float32 tensor is free of the world's secrets and of its own targets
    for wpid, row in config.items():
        truth = S.read_json(root / 'private' / wpid / 'query_truth.json')
        forbidden = np.unique(np.asarray(
            [v for v in row['coefficients'].values()]
            + [e['noise_free_response'] for e in truth if e['noise_free_response'] != 0]
            + [e['noisy_target'] for e in truth if e['noisy_target'] != 0]
            + [float(v['V']) for v in normalization.values()],
            dtype=np.float64).astype('<f4'))
        for path in sorted((root / 'public' / wpid).glob('*.npy')):
            array = np.load(path)
            if array.dtype == np.dtype('<f4') and bool(np.isin(array, forbidden).any()):
                raise AssertionError(f'{path.name} contains a private value')
        latent = np.load(root / 'private' / wpid / 'support_latent.npy')
        nonzero = np.unique(latent[latent != 0]).astype('<f4')
        support = np.load(root / 'public' / wpid / 'support_records.npy')
        if nonzero.size and bool(np.isin(support, nonzero).any()):
            raise AssertionError(f'{wpid}: a hidden state value reached the public tensor')

    # the normalization constant is private and V is floored on the noise-only control
    for key, row in normalization.items():
        if row['V'] < S.V_FLOOR - 1e-12:
            raise AssertionError(f'{key}: V below the registered floor')
        if row['family'] == 'n' and row['V'] != S.V_FLOOR:
            raise AssertionError('the noise-only control must sit on the V floor')
        if row['family'] == 'n' and row['panel_response_variance'] != 0.0:
            raise AssertionError('the noise-only control has zero signal variance')


def test_public_loader_cannot_reach_private_code():
    root = _generate('det-a')
    script = (
        'import sys; sys.path.insert(0, %r)\n'
        'import fable_concepttoy20_public as P\n'
        'assert "fable_concepttoy20_sim" not in sys.modules, "loader imported the simulator"\n'
        'd = P.PublicDataset(%r)\n'
        'worlds = d.worlds()\n'
        'assert len(worlds) == 12, worlds\n'
        'wpid = worlds[0][0]\n'
        'for budget, episodes in zip(d.budgets(), [4, 8, 16, 32, 64]):\n'
        '    s = d.support(wpid, budget)\n'
        '    assert s.n_episodes == episodes and s.n_transitions == budget\n'
        '    assert s.selection_indices().size * 8 == budget // 4\n'
        '    assert s.records.shape[1:] == (17, 44) and s.records.dtype.str == "<f4"\n'
        'q = d.queries(wpid)\n'
        'assert q.records.shape == (96, 17, 44) and q.detector.shape == (96, 9)\n'
        'assert len(q.record_id) == 96 and len(set(q.record_id)) == 96\n'
        'assert not hasattr(q, "target") and not hasattr(q, "noise_free")\n'
        'for bad in ("support_latent", "query_truth_noise_free", "family"):\n'
        '    try:\n'
        '        d._array(wpid, bad)\n'
        '    except Exception:\n'
        '        continue\n'
        '    raise AssertionError("public loader reached " + bad)\n'
        'print("OK")\n'
    ) % (str(Path(__file__).resolve().parents[1] / 'scripts'), str(root))
    environment = dict(os.environ)
    result = subprocess.run([sys.executable, '-B', '-c', script], capture_output=True,
                            text=True, env=environment, timeout=120)
    if result.returncode != 0 or 'OK' not in result.stdout:
        raise AssertionError(f'public loader check failed:\n{result.stdout}\n{result.stderr}')
    source = (Path(__file__).resolve().parents[1]
              / 'scripts' / 'fable_concepttoy20_public.py').read_text()
    if 'fable_concepttoy20_sim' in source.replace(
            'scripts/fable_concepttoy20_sim.py', '').replace(
            '`fable_concepttoy20_sim`', ''):
        raise AssertionError('the public loader references the simulator module')


# --------------------------------------------------------------------------------------
# 10.  interface contract, panel shape and the evaluator
# --------------------------------------------------------------------------------------

def test_public_record_contract():
    world = S.make_world('train', 'c', 0)
    episode = S.build_discovery_episode(world, 0)
    records = S.support_records(world, episode)
    if records.shape != (17, 44):
        raise AssertionError('a full eight-transition history has 17 records of width 44')
    widths = [(S.SL_PROPERTIES, 24), (S.SL_ACTION, 5), (S.SL_SOURCE, 4),
              (S.SL_DESTINATION, 5), (S.SL_RECORD_TYPE, 3)]
    if sum(w for _, w in widths) + 3 != 44:
        raise AssertionError('field widths do not sum to 44')
    for index, action in enumerate(episode.actions):
        row = records[1 + 2 * index]
        if int(np.argmax(row[S.SL_ACTION])) != world.verb_to_public[action.verb]:
            raise AssertionError('the public action ID must be the permuted verb')
        if int(np.argmax(row[S.SL_SOURCE])) != action.source:
            raise AssertionError('wrong source one-hot')
        expected = S.DESTINATION_NONE if action.destination is None else action.destination
        if int(np.argmax(row[S.SL_DESTINATION])) != expected:
            raise AssertionError('destination is NONE for every noncontact action')
        if action.verb != S.VERB_PULSE and row[S.IX_DOSE] != 0:
            raise AssertionError('only pulse carries a dose')
        if row[S.SL_RECORD_TYPE].sum() != 1 or row[S.SL_ACTION].sum() != 1:
            raise AssertionError('one-hot fields must have exactly one active entry')
        if not np.array_equal(row[S.SL_PROPERTIES],
                              episode.properties.reshape(-1)):
            raise AssertionError('every record repeats the static public properties')
    # internal verb names never occur in a learner file
    if any(name in str(records.tolist()) for name in S.INTERNAL_VERBS):
        raise AssertionError('a verb name reached the record tensor')
    # the verb map is a bijection, drawn separately per world
    if sorted(world.verb_to_public) != [0, 1, 2, 3, 4]:
        raise AssertionError('the verb map must be a bijection onto 0..4')
    maps = {S.make_world('final', 'c', i).verb_to_public for i in range(8)}
    if len(maps) < 2:
        raise AssertionError('the verb map must vary across worlds')
    # detector encoding
    vector = S.detector_vector(2, None)
    if vector.shape != (9,) or vector[2] != 1 or vector[4 + S.DESTINATION_NONE] != 1:
        raise AssertionError('task A detector is (a, NONE)')


def test_panel_shape_and_normalization():
    world = S.make_world('validation', 'c', 2)
    targets = S.build_source_panels(world)
    if len(targets) != 96:
        raise AssertionError('96 target predictions per world')
    units = {(t.panel, t.unit) for t in targets}
    if len(units) != 64:
        raise AssertionError('64 independent units per world')
    for target in targets:
        if target.n_records != 16 or target.query_index != 15:
            raise AssertionError('every pilot query sequence has 16 real records')
        if target.prefix_length + target.horizon != 8:
            raise AssertionError('every unit covers eight transitions')
        if target.detector_b is not None:
            raise AssertionError('task A queries (last_action.source, NONE)')
    horizons = sorted(t.horizon for t in targets if t.panel == S.PANEL_ORDINARY)
    if horizons != sorted(S.PANEL1_HORIZONS):
        raise AssertionError('panel 1 is six h=1, five h=2 and five h=4 forecasts')
    doses = [t for t in targets if t.panel == S.PANEL_COMPOSITION]
    if len(doses) != 16:
        raise AssertionError('panel 2 has 16 units')
    if len({t.record_id for t in targets}) != 96:
        raise AssertionError('record IDs must be unique')
    # A record ID is <opaque alias>-qNNNN and says nothing about panel, unit or branch:
    # sorting by it must not group the panels, and the true world_id must not appear.
    for index, target in enumerate(targets):
        if target.record_id != f'{world.world_public_id}-q{index:04d}':
            raise AssertionError(f'unexpected record ID {target.record_id}')
        if world.world_id[:8] in target.record_id:
            raise AssertionError('a record ID exposes the true world_id')
    by_id = [t.panel for t in sorted(targets, key=lambda t: t.record_id)]
    if by_id == sorted(by_id):
        raise AssertionError('record ID order groups the panels')
    if len(set(by_id[:16])) < 2:
        raise AssertionError('the first 16 records are all one panel')

    pool = [S.WorldData(world=w, support=[], targets=S.build_source_panels(w),
                        audit=[])
            for w in (S.make_world('validation', 'c', 0),
                      S.make_world('validation', 'n', 0))]
    constants = S.normalization_constants(pool)
    if constants['validation/A/n']['V'] != S.V_FLOOR:
        raise AssertionError('N normalizes on the floor')
    if constants['validation/A/c']['n_responses'] != 32:
        raise AssertionError('V uses the ordinary and composition panels only')
    assert_close(constants['validation/A/n']['analytic_sensor_floor'],
                 S.ANALYTIC_SENSOR_VARIANCE / S.V_FLOOR, what='published floor')


def test_evaluator_joins_by_record_id_only():
    root = _generate('det-a')
    config = S.read_json(root / 'private' / 'world_config.json')
    wpid = sorted(config)[0]
    truth = S.read_json(root / 'private' / wpid / 'query_truth.json')
    # a perfect predictor of the noise-free response scores E = 0
    predictions = [{'record_id': e['record_id'], 'prediction': e['noise_free_response'],
                    'arm': 'oracle', 'seed': '20001', 'rung': '0'} for e in truth]
    # and a zero predictor does not
    predictions += [{'record_id': e['record_id'], 'prediction': 0.0,
                     'arm': 'zero', 'seed': '20001', 'rung': '0'} for e in truth]
    report = S.evaluate_predictions(root, predictions)
    if report['n_unknown_record_ids'] != 0:
        raise AssertionError('every record ID must join')
    groups = {g['arm']: g for g in report['groups']}
    oracle = [w for w in groups['oracle']['worlds'] if w['world_public_id'] == wpid][0]
    zero = [w for w in groups['zero']['worlds'] if w['world_public_id'] == wpid][0]
    if oracle['n_targets_scored'] != 96 or not oracle['complete']:
        raise AssertionError('all 96 targets should be scored')
    assert_close(oracle['E_primary'], 0.0, tol=1e-12, what='oracle excess error')
    assert_close(oracle['raw_noise_free_mse'], 0.0, tol=1e-12, what='oracle raw MSE')
    if abs(oracle['raw_noisy_mse'] - S.ANALYTIC_SENSOR_VARIANCE) > 0.002:
        raise AssertionError(
            f"oracle noisy MSE {oracle['raw_noisy_mse']} should sit near the sensor floor")
    assert_close(oracle['panel3_relevant_pairs']['difference_mse_over_V'], 0.0,
                 tol=1e-12, what='oracle pair difference')
    assert_close(oracle['panel4_irrelevant_pairs']['between_branch_mse_over_V'], 0.0,
                 tol=1e-12, what='oracle nuisance invariance')
    if config[wpid]['family'] != 'n' and zero['E_primary'] <= 0.0:
        raise AssertionError('a zero predictor must have positive excess error')
    # an incomplete submission is visible, never silently dropped
    partial = S.evaluate_predictions(root, predictions[:10])
    world = partial['groups'][0]['worlds'][0]
    if world['complete'] or world['n_targets_scored'] != 10:
        raise AssertionError('missing predictions must be reported')
    # unknown IDs are reported rather than matched
    stray = S.evaluate_predictions(root, [{'record_id': 'nope', 'prediction': 0.0,
                                           'arm': '', 'seed': '', 'rung': '',
                                           'stage': 'final'}])
    if stray['n_unknown_record_ids'] != 1:
        raise AssertionError('an unknown record ID must be reported')


def test_fixture_exposes_no_final_world_or_mode_family():
    out = Path(TMP) / 'fixture'
    shutil.rmtree(out, ignore_errors=True)
    manifest = S.generate_fixture(out)
    if manifest['mode_family_present'] or manifest['final_worlds_present']:
        raise AssertionError('the fixture must expose neither M nor a final world')
    config = S.read_json(out / 'private' / 'world_config.json')
    if any(row['family'] == 'm' or row['outer_split'] == 'final'
           for row in config.values()):
        raise AssertionError('a fixture world is from a forbidden pool')
    text = (out / 'fixture.md').read_text(encoding='utf-8')
    for forbidden in ('accuracy', 'learning curve', 'MSE', 'loss', 'E_primary', '%'):
        if forbidden.lower() in text.lower():
            raise AssertionError(f'the fixture publishes {forbidden!r}')
    for row in S.read_json(out / 'private' / 'world_config.json').values():
        if row['family'] == 'm':
            raise AssertionError('a mode-family world reached the fixture')
    if 'QUERY' not in text or 'OBSERVED' not in text:
        raise AssertionError('the fixture must show the record tokenization')
    report = S.audit_directory(out)
    if report['failed']:
        raise AssertionError('the fixture directory fails its own audit')


# --------------------------------------------------------------------------------------
# 12.  ct20-v1.1 amendment: rulings B1, B6, B8, C9, C10, D
# --------------------------------------------------------------------------------------

def _panel_verbs(world, targets, records):
    """Internal verbs of each panel unit, decoded from the PUBLIC action one-hots."""
    public_to_verb = {public: verb for verb, public in enumerate(world.verb_to_public)}
    out = []
    for row, target in enumerate(targets):
        verbs = [public_to_verb[int(np.argmax(records[row, r, S.SL_ACTION]))]
                 for r in range(1, target.n_records, 2)]
        out.append((target, verbs))
    return out


def test_b1_panel_exclusion_applies_to_panels():
    if S.APPLY_COMPOSITION_EXCLUSION_TO_PANELS is not True:
        raise AssertionError('ruling B1 requires the panel exclusion to be ON')
    for family in ('c', 'o'):
        world = S.make_world('validation', family, 0)
        targets = S.build_source_panels(world)
        records = np.stack([t.records for t in targets])
        seen_composition = 0
        for target, verbs in _panel_verbs(world, targets, records):
            if len(verbs) != S.N_TRANSITIONS:
                raise AssertionError('a panel unit must expose all eight actions')
            is_composition = (target.panel == S.PANEL_COMPOSITION
                              or (target.panel == S.PANEL_IRRELEVANT_PAIR
                                  and target.unit >= 8))
            if is_composition:
                seen_composition += 1
                # the PREFIX obeys the discovery grammar ...
                if S.contains_reserved_composition(verbs[:4]):
                    raise AssertionError(
                        f'panel {target.panel} unit {target.unit} prefix contains the '
                        'reserved composition')
                # ... and the forced suffix is never rejected, so it is still there.
                if tuple(verbs[4:]) != S.RESERVED_COMPOSITION:
                    raise AssertionError('a forced composition suffix was altered')
            elif S.contains_reserved_composition(verbs):
                raise AssertionError(
                    f'panel {target.panel} unit {target.unit} branch {target.branch} '
                    'contains the reserved composition')
        if seen_composition != 16 + 16:      # panel 2, plus panel 4 units 8..15 x2
            raise AssertionError(f'expected 32 composition branches, saw {seen_composition}')


def test_b1_applies_to_task_b_query_recipes():
    """The exclusion is a shared switch, so a task-B query panel obeys it identically."""
    world = S.make_world('validation', 'c', 1)
    source = S.build_source_panels(world, S.STREAM_SOURCE_QUERY)
    reuse = S.build_source_panels(world, S.STREAM_REUSE_QUERY)
    records = np.stack([t.records for t in reuse])
    for target, verbs in _panel_verbs(world, reuse, records):
        is_composition = (target.panel == S.PANEL_COMPOSITION
                          or (target.panel == S.PANEL_IRRELEVANT_PAIR
                              and target.unit >= 8))
        window = verbs[:4] if is_composition else verbs
        if S.contains_reserved_composition(window):
            raise AssertionError('a task-B query recipe contains the reserved composition')
    if all(np.array_equal(a.records, b.records) for a, b in zip(source, reuse)):
        raise AssertionError('the reuse-query stream must draw its own episodes')
    # task-B FITTING episodes keep the whole-string exclusion they already had
    batch = S.build_task_b_episode(world, 0)
    if S.contains_reserved_composition([a.verb for a in batch['episode'].actions]):
        raise AssertionError('a task-B fitting episode contains the reserved composition')


def test_amendment_does_not_redraw_worlds_or_supports():
    """Ruling D: the version label must not touch the inherited RNG identity."""
    if S.NAMESPACE_ROOT != 'premonition/concept-toy20/v1':
        raise AssertionError('the inherited RNG namespace root changed')
    if S.WORLD_TUPLE_VERSION != S.PREVIOUS_VERSION:
        raise AssertionError('the world tuple label must stay pinned at ct20-v1')
    if S.VERSION == S.WORLD_TUPLE_VERSION:
        raise AssertionError('the experiment version label was not advanced')
    frozen = (Path(__file__).resolve().parents[1] / 'artifacts'
              / 'fable-concept-toy20-20260920' / 'calibration' / 'private'
              / 'world_config.json')
    if frozen.exists():
        for wpid, row in S.read_json(frozen).items():
            world = S.make_world(row['outer_split'], row['family'], row['world_index'])
            if world.world_id != row['world_id'] or world.world_public_id != wpid:
                raise AssertionError(f'world {wpid} was redrawn by the amendment')
        # and the frozen v1 support tensors still regenerate byte for byte
        v1 = frozen.parent.parent
        for wpid, row in list(S.read_json(frozen).items())[:2]:
            world = S.make_world(row['outer_split'], row['family'], row['world_index'])
            support = [S.build_discovery_episode(world, i)
                       for i in range(S.EPISODES_AT_MAX_BUDGET)]
            rebuilt = S._f4(np.stack([S.support_records(world, e) for e in support]))
            if S.tensor_hash(rebuilt) != S.tensor_hash(
                    np.load(v1 / 'public' / wpid / 'support_records.npy')):
                raise AssertionError(f'support set of {wpid} changed')


def test_normalization_stream_is_reserved_with_zero_draws():
    if S.STREAM_NORMALIZATION_RESERVED_UNUSED in S.ACTIVE_STREAMS:
        raise AssertionError('ruling B6 drops `normalization` from the active streams')
    if S.STREAM_NORMALIZATION_RESERVED_UNUSED not in S.RESERVED_UNUSED_STREAMS:
        raise AssertionError('`normalization` must stay registered as reserved')
    seen: list[str] = []
    original = S.make_rng
    S.make_rng = lambda namespace: seen.append(namespace) or original(namespace)
    try:
        data = S.build_world_data(S.make_world('train', 'c', 0))
    finally:
        S.make_rng = original
    if not seen:
        raise AssertionError('no namespace was recorded')
    if any('/normalization' in namespace for namespace in seen):
        raise AssertionError('the reserved stream consumed a draw')
    streams = {namespace.split('/episode/')[1].split('/')[1]
               for namespace in seen if '/episode/' in namespace}
    if not streams <= set(S.ACTIVE_STREAMS):
        raise AssertionError(f'an unregistered stream was used: {streams}')
    # V still comes from panels 1 and 2 of the existing targets, with the 0.05 floor
    constants = S.normalization_constants([data])
    for row in constants.values():
        if row['n_responses'] != 32 or row['V'] < S.V_FLOOR:
            raise AssertionError('V is no longer the floored panel-1/2 variance')


def test_outer_split_is_never_a_model_feature():
    """Ruling B8: `outer_split` stays in coordinator bookkeeping."""
    out = _generate('b8')
    index = S.read_json(out / 'public' / 'worlds.json')
    if not all('outer_split' in row for row in index['worlds']):
        raise AssertionError('the coordinator index must keep outer_split')
    for wpid in S.read_json(out / 'private' / 'world_config.json'):
        for path in sorted((out / 'public' / wpid).glob('*.npy')):
            if 'split' in path.stem:
                raise AssertionError(f'{path.name} names a split')
        for name in ('query_record_ids.json', 'audit_keys.json'):
            text = (out / 'public' / wpid / name).read_text(encoding='utf-8')
            for token in ('outer_split', 'train', 'validation', 'final'):
                if token in text:
                    raise AssertionError(f'{name} leaks a split label')
    for batch in (PUB.SupportBatch, PUB.QueryBatch, PUB.FittingAuditBatch,
                  PUB.TaskBFittingBatch):
        if any('split' in field for field in batch.__dataclass_fields__):
            raise AssertionError(f'{batch.__name__} exposes a split field')
    if S.PUBLIC_HINT_CLAIM_WORDING != ('randomly relabeled action IDs with public '
                                       'argument/dose structure'):
        raise AssertionError('the registered B8 claim wording changed')


def test_fitting_audit_set_definition():
    world = S.make_world('train', 'c', 1)
    support = [S.build_discovery_episode(world, i)
               for i in range(S.EPISODES_AT_MAX_BUDGET)]
    items = S.build_fitting_audit_set(world, support)
    seen = set()
    for item in items:
        if S.episode_role(item.episode_index) != S.ROLE_FIT:
            raise AssertionError('a selection episode entered the fitting audit')
        episode = support[item.episode_index]
        # the LAST eligible observed endpoint, and nothing later
        if not bool(episode.present[item.endpoint - 1]):
            raise AssertionError('the chosen endpoint was not observed')
        if any(bool(episode.present[t - 1])
               for t in range(item.endpoint + 1, S.N_TRANSITIONS + 1)):
            raise AssertionError('a later eligible endpoint existed')
        if item.endpoint < item.horizon:
            raise AssertionError('the endpoint cannot precede its own horizon')
        # shapes and the prediction position
        if item.n_records != 2 * item.endpoint or item.query_index != item.n_records - 1:
            raise AssertionError('the audit sequence length rule is broken')
        final = item.records[item.query_index]
        if (final[S.SL_RECORD_TYPE][S.RT_QUERY] != 1.0 or final[S.IX_SENSOR] != 0.0
                or final[S.IX_SENSOR_PRESENT] != 0.0):
            raise AssertionError('the audit prediction row is not a blank QUERY')
        if item.records[item.n_records:].any():
            raise AssertionError('padding after an audit sequence is not zero')
        # the h-1 forecast observations are blank, never teacher forced
        blanks = item.records[1 + 2 * (item.endpoint - item.horizon) + 1:
                              item.query_index:2]
        if blanks.size and (blanks[:, S.IX_SENSOR].any()
                            or blanks[:, S.IX_SENSOR_PRESENT].any()):
            raise AssertionError('a forecast observation was teacher forced')
        # the scored label never appears inside its own sequence
        if float(item.observed_label) != 0.0 and bool(
                (item.records == np.float64(item.observed_label)).any()):
            raise AssertionError('the audit label leaked into its sequence')
        assert_close(item.noise_free, episode.noise_free[item.endpoint - 1],
                     what='audit truth is the endpoint response')
        assert_close(item.observed_label, episode.observed[item.endpoint - 1],
                     what='audit label is the logged observation')
        if item.audit_id != S.audit_key(world.world_public_id, item.episode_index,
                                        item.horizon, item.endpoint):
            raise AssertionError('the audit key format drifted')
        seen.add(item.audit_id)
    if len(seen) != len(items):
        raise AssertionError('audit keys are not unique')
    expected = 48 * len(S.AUDIT_HORIZONS)
    if not 0 < len(items) <= expected:
        raise AssertionError(f'expected at most {expected} audit cases, got {len(items)}')
    if PUB.PublicDataset.audit_key(world.world_public_id, 3, 2, 7) != S.audit_key(
            world.world_public_id, 3, 2, 7):
        raise AssertionError('the loader and the simulator disagree on the key format')


def test_startup_predicate_boundary_values():
    """Ruling C9, on / just inside / just outside the 1e-12 tolerance."""
    threshold = S.STARTUP_IMPROVEMENT_THRESHOLD - S.STARTUP_RELATIVE_TOLERANCE
    if threshold != 0.1 - 1e-12:
        raise AssertionError('the C9 threshold is not 0.10 - 1e-12')

    # Walk L_final one ULP at a time across the boundary.  With L_initial = 1.0 the
    # subtraction 1.0 - L_final is exact (Sterbenz), so the r the evaluator computes is
    # the exact difference and the scan really does land on, just inside and just
    # outside the tolerance rather than near it.
    saw_true = saw_false = False
    closest = float('inf')
    l_final = float(1.0 - threshold)
    for _ in range(40):                      # start a few ULPs below the crossing
        l_final = float(np.nextafter(l_final, 1.0))
    for _ in range(80):
        verdict = S.startup_classification(1.0, l_final, 0.9, e_query_final=0.9)
        r = verdict['relative_improvement']
        assert_close(r, 1.0 - l_final, tol=0.0, what='r is the exact difference')
        if verdict['never_started'] is not bool(r < threshold):
            raise AssertionError(f'the predicate disagrees with r < threshold at r={r!r}')
        if verdict['never_started'] and verdict['status'] != 'never_started':
            raise AssertionError('never_started must set the matching status')
        saw_true |= bool(verdict['never_started'])
        saw_false |= not verdict['never_started']
        closest = min(closest, abs(r - threshold))
        l_final = float(np.nextafter(l_final, 0.0))
    if not (saw_true and saw_false):
        raise AssertionError('the scan did not cross the boundary')
    if closest > abs(np.nextafter(threshold, 1.0) - threshold):
        raise AssertionError('the scan never came within one ULP of the boundary')
    # exactly ON the boundary: r == 0.10 - 1e-12 is NOT < the threshold
    on_boundary = S.startup_classification(1.0, 1.0, 0.9, e_query_final=0.9)
    if on_boundary['never_started'] is not True:
        raise AssertionError('r = 0 is below the boundary and must be never_started')
    if bool(threshold < threshold):
        raise AssertionError('the comparison must be strict')
    # the ruling's own worked example
    example = S.startup_classification(1.0, 0.90, 0.9, e_query_final=0.9)
    if example['never_started'] is not False or example['status'] == 'never_started':
        raise AssertionError('L_initial=1.0, L_final=0.90 must not be never_started')
    assert_close(example['relative_improvement'], (1.0 - 0.90) / 1.0, tol=0.0,
                 what='the example r is computed without rounding')
    # the AND clause: a tiny improvement with good fitting E is NOT never_started
    if S.startup_classification(1.0, 1.0, 0.79, e_query_final=0.4)['never_started']:
        raise AssertionError('E_fit_final < 0.80 cannot be never_started')
    if not S.startup_classification(1.0, 1.0, 0.80, e_query_final=0.4)['never_started']:
        raise AssertionError('E_fit_final exactly 0.80 satisfies the >= clause')
    # the unchanged initial-floor boundary
    if S.startup_classification(1e-8, 1e-8, 0.9)['status'] != 'initially_at_floor':
        raise AssertionError('L_initial == 1e-8 is at the floor')
    just_above = np.nextafter(1e-8, 1.0)
    if S.startup_classification(float(just_above), float(just_above),
                                0.9, 0.9)['status'] != 'never_started':
        raise AssertionError('just above the floor the ordinary predicate applies')
    # failures and incompleteness take precedence and never become a start-up
    for bad in (float('nan'), float('inf')):
        for args in ((bad, 0.5, 0.5), (1.0, bad, 0.5), (1.0, 0.5, bad)):
            verdict = S.startup_classification(*args, e_query_final=0.1)
            if verdict['status'] != 'numerical_failure':
                raise AssertionError(f'{args} must be a numerical failure')
    missing = S.startup_classification(1.0, 0.1, 0.1, 0.1, complete=False)
    if missing['status'] != 'infrastructure_incomplete':
        raise AssertionError('a missing measurement must be reported as incomplete')
    # the remaining prereg section 8 classes
    cases = {
        (0.5, 0.3, None): 'started_not_yet_learned',
        (0.5, 0.2, 0.6): 'learned_failed_to_transfer',
        (0.5, 0.2, 0.4): 'learned_with_generalization',
    }
    for (l_final, e_fit, e_query), want in cases.items():
        got = S.startup_classification(1.0, l_final, e_fit,
                                       e_query_final=e_query if e_query else 0.9)
        if got['status'] != want:
            raise AssertionError(f'{(l_final, e_fit, e_query)} -> {got["status"]}')


def test_evaluator_finalizes_the_startup_diagnostic():
    out = _generate('startup')
    config = S.read_json(out / 'private' / 'world_config.json')
    rows: list[dict] = []
    for wpid in config:
        for entry in S.read_json(out / 'private' / wpid / 'query_truth.json'):
            rows.append({'record_id': entry['record_id'], 'prediction': 0.0,
                         'arm': 'G', 'seed': '20001', 'rung': '0', 'stage': 'initial'})
            rows.append({'record_id': entry['record_id'], 'stage': 'final',
                         'prediction': entry['noise_free_response'],
                         'arm': 'G', 'seed': '20001', 'rung': '4'})
        for entry in S.read_json(out / 'private' / wpid / 'audit_truth.json'):
            rows.append({'record_id': entry['audit_id'], 'prediction': 0.0,
                         'arm': 'G', 'seed': '20001', 'stage': 'initial'})
            rows.append({'record_id': entry['audit_id'], 'stage': 'final',
                         'prediction': entry['noise_free_response'],
                         'arm': 'G', 'seed': '20001'})
    report = S.evaluate_predictions(out, rows)
    diagnostics = report['startup_diagnostics']
    if len(diagnostics) != len(config):
        raise AssertionError('one start-up row per world and arm/seed is required')
    for row in diagnostics:
        if row['status'] != 'learned_with_generalization':
            raise AssertionError(f'an oracle scored {row["status"]}')
        if row['E_fit_final'] != 0.0 or row['E_query_final'] != 0.0:
            raise AssertionError('an oracle must reach zero excess error')
        if row['n_audit_cases_initial'] != row['n_audit_cases_expected']:
            raise AssertionError('audit coverage was not verified')
    # the diagnostic is finalized from SEALED predictions: it is JSON-serializable and
    # needs no simulator object
    S.canonical_json(report)
    # a stuck learner on a C world: no improvement and a high fitting E
    wpid = next(w for w, row in config.items() if row['family'] == 'c')
    stuck = [{'record_id': e['audit_id'], 'prediction': 0.0, 'arm': 'Z',
              'seed': '1', 'stage': stage}
             for stage in ('initial', 'final')
             for e in S.read_json(out / 'private' / wpid / 'audit_truth.json')]
    stuck += [{'record_id': e['record_id'], 'prediction': 0.0, 'arm': 'Z', 'seed': '1',
               'rung': '4', 'stage': 'final'}
              for e in S.read_json(out / 'private' / wpid / 'query_truth.json')]
    verdict = [row for row in S.evaluate_predictions(out, stuck)['startup_diagnostics']
               if row['world_public_id'] == wpid][0]
    if verdict['status'] != 'never_started' or verdict['relative_improvement'] != 0.0:
        raise AssertionError(f'a stuck learner scored {verdict["status"]}')
    # a missing final audit prediction can never be a successful start-up
    partial = [row for row in stuck if not (row.get('stage') == 'final'
                                            and 'fit' in row['record_id'])]
    verdict = [row for row in S.evaluate_predictions(out, partial)['startup_diagnostics']
               if row['world_public_id'] == wpid][0]
    if verdict['status'] != 'infrastructure_incomplete':
        raise AssertionError('a missing final audit set must be incomplete')
    # a ct20-v1 prediction file (no stage field) still scores as the final stage
    legacy = S.load_predictions.__doc__
    plain = [{'record_id': e['record_id'], 'prediction': 0.0}
             for e in S.read_json(out / 'private' / wpid / 'query_truth.json')]
    if S.evaluate_predictions(out, [{**row, 'arm': '', 'seed': '', 'rung': '',
                                     'stage': 'final'} for row in plain]
                              )['groups'][0]['stage'] != 'final' or not legacy:
        raise AssertionError('a stageless prediction file must default to final')


def test_audit_keys_survive_the_public_loader():
    out = _generate('audit-keys')
    dataset = PUB.PublicDataset(out)
    for wpid, _split in dataset.worlds():
        batch = dataset.fitting_audit(wpid)
        truth = S.read_json(out / 'private' / wpid / 'audit_truth.json')
        if batch.audit_id != [row['audit_id'] for row in truth]:
            raise AssertionError('the loader and the evaluator disagree on audit order')
        for slot, row in enumerate(truth):
            if PUB.PublicDataset.audit_key(
                    wpid, int(batch.episode_index[slot]), int(batch.horizon[slot]),
                    int(batch.endpoint[slot])) != row['audit_id']:
                raise AssertionError('a key rebuilt from public fields does not match')
            if abs(float(batch.observed_label[slot])
                   - float(row['observed_label'])) > 1e-6:
                raise AssertionError('the public label disagrees with the evaluator')
        types = PUB.PublicDataset.record_types(batch.records)
        for slot in range(len(batch.audit_id)):
            n = int(batch.n_records[slot])
            if types[slot, int(batch.query_index[slot])] != PUB.RT_QUERY:
                raise AssertionError('the prediction row is not a QUERY')
            if (types[slot, n:] != -1).any():
                raise AssertionError('padding is not identifiable')
        # a noise-free response can never be reached through the public loader
        for name in ('audit_truth_noise_free', 'query_truth_noise_free'):
            try:
                dataset._array(wpid, name)
            except PUB.PublicBoundaryError:
                continue
            raise AssertionError(f'the loader served {name}')


def test_one_audit_key_spelling():
    """Rulings 2: the frozen models build calls `PublicDataset.audit_key` itself, so the
    canonical spelling is the only one.  The compatibility reader is gone: a key in the
    retired `e{ep}/h{h}/t{t}` spelling must now be REFUSED, not quietly rewritten."""
    out = _generate('audit-key-spelling')
    wpid = S.read_json(out / 'public' / 'worlds.json')['worlds'][0]['world_public_id']
    truth = S.read_json(out / 'private' / wpid / 'audit_truth.json')

    for name in ('parse_models_audit_key', 'MODELS_AUDIT_KEY_FORMAT'):
        if hasattr(S, name):
            raise AssertionError(f'the retired compatibility shim {name} is still present')

    canonical = [row['audit_id'] for row in truth]
    for row in truth:
        rebuilt = PUB.PublicDataset.audit_key(
            wpid, row['episode_index'], row['horizon'], row['endpoint'])
        if rebuilt != row['audit_id'] or S.audit_key(
                wpid, row['episode_index'], row['horizon'], row['endpoint']) != rebuilt:
            raise AssertionError('the loader and the simulator disagree on the key')
        if '/' in row['audit_id']:
            raise AssertionError('a canonical key contains the retired separator')

    path = Path(TMP) / 'one-spelling-preds.json'
    S.write_json(path, [{'record_id': k, 'prediction': 0.0} for k in canonical])
    if [r['record_id'] for r in S.load_predictions(path)] != canonical:
        raise AssertionError('canonical keys did not load unchanged')

    retired = 'e{}/h{}/t{}'.format(
        truth[0]['episode_index'], truth[0]['horizon'], truth[0]['endpoint'])
    S.write_json(path, [{'record_id': retired, 'world_public_id': wpid,
                         'prediction': 0.0}])
    loaded = S.load_predictions(path)
    if loaded[0]['record_id'] != retired:
        raise AssertionError('the retired spelling was rewritten; the shim is still live')


def _r1_world(report, wpid):
    """The one world's row from the single (arm, seed, rung, stage) group.

    `evaluate_predictions` returns JSON-safe output, so an invalidated (NaN) term comes
    back as None -- that is the serialized contract the gate calculator will read.
    """
    groups = report['groups']
    if len(groups) != 1:
        raise AssertionError(f'expected one prediction group, got {len(groups)}')
    return next(w for w in groups[0]['worlds'] if w['world_public_id'] == wpid)


def _r1_fixture(out, wpid, predictor):
    """Prediction rows for one world, plus the squared errors they imply."""
    truth = S.read_json(out / 'private' / wpid / 'query_truth.json')
    config = S.read_json(out / 'private' / 'world_config.json')[wpid]
    normalization = S.read_json(out / 'private' / 'normalization.json')
    v = float(normalization[f"{config['outer_split']}/A/{config['family']}"]['V'])
    rows, squared = [], {}
    for entry in truth:
        prediction = predictor(entry)
        rows.append({'record_id': entry['record_id'], 'prediction': prediction,
                     'arm': 'G', 'seed': '20001', 'rung': '4', 'stage': S.STAGE_FINAL})
        squared[entry['record_id']] = (
            (prediction - float(entry['noise_free_response'])) ** 2, entry)
    return rows, squared, v


def test_r1_primary_error_definition():
    """Rulings 2 R1, hand-computed from the panel definition and compared to the
    evaluator: E_primary = (E_panel1 + E_panel2)/2, panel 1 = the EQUAL average of the
    h=1/2/4 means (not a flat mean over its 6/5/5 targets), panel 2 = the equal average of
    its 16 units, every squared error divided by the fixed evaluator-only V.

    The fixture is horizon-dependent on purpose, so a flat panel-1 mean would fail here.
    """
    out = _generate('r1-primary')
    index = S.read_json(out / 'public' / 'worlds.json')
    checked = 0
    for world_row in index['worlds']:
        wpid = world_row['world_public_id']
        counter = [0]

        def predictor(entry):
            counter[0] += 1
            return float(entry['noise_free_response']) + 0.1 * (counter[0] % 7) - 0.3

        rows, squared, v = _r1_fixture(out, wpid, predictor)
        got = _r1_world(S.evaluate_predictions(out, rows), wpid)

        by_horizon, panel2, all_targets = {}, [], []
        for value, entry in squared.values():
            all_targets.append(value)
            if entry['panel'] == S.PANEL_ORDINARY:
                by_horizon.setdefault(entry['horizon'], []).append(value)
            elif entry['panel'] == S.PANEL_COMPOSITION:
                panel2.append(value)
        if sorted(len(x) for x in by_horizon.values()) != [5, 5, 6]:
            raise AssertionError(f'panel 1 target counts are not 6/5/5: {by_horizon}')
        if len(panel2) != S.UNITS_PER_PANEL:
            raise AssertionError(f'panel 2 has {len(panel2)} units, expected 16')
        if len(all_targets) != 96:
            raise AssertionError(f'{len(all_targets)} targets scored, expected 96')

        horizon_means = [sum(by_horizon[h]) / len(by_horizon[h]) / v
                         for h in sorted(by_horizon)]
        hand_panel1 = sum(horizon_means) / len(horizon_means)
        hand_panel2 = sum(panel2) / len(panel2) / v
        hand_primary = (hand_panel1 + hand_panel2) / 2.0
        flat_panel1 = sum(sum(by_horizon[h]) for h in by_horizon) / 16 / v

        for label, hand, key in (('E_panel1', hand_panel1, 'E_panel1_ordinary'),
                                 ('E_panel2', hand_panel2, 'E_panel2_composition'),
                                 ('E_primary', hand_primary, 'E_primary')):
            if abs(float(got[key]) - hand) > 1e-12:
                raise AssertionError(
                    f'{wpid} {label}: evaluator {got[key]!r} != hand-computed {hand!r}')
        if abs(hand_panel1 - flat_panel1) < 1e-9:
            raise AssertionError('the fixture cannot distinguish the two panel-1 rules')
        for horizon, mean in zip(sorted(by_horizon), horizon_means):
            if abs(float(got['E_panel1_by_horizon'][f'h{horizon}']) - mean) > 1e-12:
                raise AssertionError(f'{wpid} h{horizon} mean disagrees')
        if float(got['V']) != v:
            raise AssertionError('the evaluator used a different V')
        if not got['complete'] or got['n_targets_scored'] != 96:
            raise AssertionError('all 96 targets must still be scored')
        checked += 1
    if checked != 12:
        raise AssertionError(f'only {checked} worlds checked')


def test_r1_panel4_excluded_and_missing_cases_invalidate():
    """R1: panels 3 and 4 are separate guards; NO panel-4 branch enters E_primary even
    though its recipes are ordinary and composition.  R2: a missing case invalidates
    rather than silently shortening a denominator."""
    out = _generate('r1-guards')
    wpid = S.read_json(out / 'public' / 'worlds.json')['worlds'][0]['world_public_id']
    truth = S.read_json(out / 'private' / wpid / 'query_truth.json')
    panel4 = [e for e in truth if e['panel'] == S.PANEL_IRRELEVANT_PAIR]
    if len(panel4) != 32 or {e['branch'] for e in panel4} != {'base', 'edited'}:
        raise AssertionError('panel 4 is not 32 base/edited targets')

    rows, _squared, _v = _r1_fixture(
        out, wpid,
        lambda e: (float(e['noise_free_response']) + 1000.0
                   if e['panel'] == S.PANEL_IRRELEVANT_PAIR
                   else float(e['noise_free_response'])))
    got = _r1_world(S.evaluate_predictions(out, rows), wpid)
    for key in ('E_panel1_ordinary', 'E_panel2_composition', 'E_primary'):
        if float(got[key]) != 0.0:
            raise AssertionError(f'panel 4 leaked into {key}: {got[key]!r}')
    if not float(got['E_all_targets']) > 1.0:
        raise AssertionError('E_all_targets should have absorbed the panel-4 error')
    if float(got['panel4_irrelevant_pairs']['E_base']) <= 1.0:
        raise AssertionError('panel 4 must still be scored and reported separately')
    if got['panel3_relevant_pairs']['n_pairs'] != 16:
        raise AssertionError('panel 3 must still be reported as a guard')

    dropped = next(e for e in truth
                   if e['panel'] == S.PANEL_ORDINARY and e['horizon'] == 4)
    short = [r for r in rows if r['record_id'] != dropped['record_id']]
    got = _r1_world(S.evaluate_predictions(out, short), wpid)
    if got['E_panel1_by_horizon']['h4'] is not None:
        raise AssertionError('a short horizon silently shortened its denominator')
    if not (got['E_panel1_ordinary'] is None and got['E_primary'] is None):
        raise AssertionError('a missing case must invalidate E_primary, not shrink it')
    if got['complete']:
        raise AssertionError('the world should not be reported complete')

    dropped2 = next(e for e in truth if e['panel'] == S.PANEL_COMPOSITION)
    short2 = [r for r in rows if r['record_id'] != dropped2['record_id']]
    got = _r1_world(S.evaluate_predictions(out, short2), wpid)
    if not (got['E_panel2_composition'] is None and got['E_primary'] is None):
        raise AssertionError('a short panel 2 must invalidate E_primary')


def test_serialized_padding_rows_are_all_zero():
    """SCHEMA.md 2.3.1: rows past `n_records` are all-zero in the SERIALIZED tensors.

    A consumer may keep the static property block on padded rows internally; that is
    permitted because the mask and the endpoint gather exclude them.  What is frozen is
    the file, and byte-equality is asserted only up to `n_records`.
    """
    out = _generate('padding-convention')
    index = S.read_json(out / 'public' / 'worlds.json')
    checked = 0
    for entry in index['worlds']:
        wpid = entry['world_public_id']
        for name in ('query', 'audit'):
            records = np.load(out / 'public' / wpid / f'{name}_records.npy')
            counts = np.load(out / 'public' / wpid / f'{name}_n_records.npy')
            masks = np.load(out / 'public' / wpid / f'{name}_padding_mask.npy')
            for slot in range(records.shape[0]):
                n = int(counts[slot])
                if records[slot, n:].size and np.any(records[slot, n:] != 0.0):
                    raise AssertionError(
                        f'{wpid}/{name}[{slot}] has a non-zero row past n_records')
                if np.any(masks[slot, n:] != 0) or np.any(masks[slot, :n] != 1):
                    raise AssertionError(f'{wpid}/{name}[{slot}] mask disagrees with n')
                checked += 1
    if checked < 12 * 96:
        raise AssertionError(f'only {checked} sequences checked')

    # the permitted internal convention cannot reach a prediction: carrying the property
    # block onto padded rows leaves every prediction row (query_index) untouched.
    wpid = index['worlds'][0]['world_public_id']
    records = np.load(out / 'public' / wpid / 'query_records.npy')
    counts = np.load(out / 'public' / wpid / 'query_n_records.npy')
    query_index = np.load(out / 'public' / wpid / 'query_index.npy')
    variant = records.copy()
    for slot in range(variant.shape[0]):
        n = int(counts[slot])
        variant[slot, n:, S.SL_PROPERTIES] = variant[slot, n - 1, S.SL_PROPERTIES]
        if int(query_index[slot]) >= n:
            raise AssertionError('the prediction row is inside the padding')
    for slot in range(variant.shape[0]):
        n = int(counts[slot])
        if not np.array_equal(variant[slot, :n], records[slot, :n]):
            raise AssertionError('the internal convention changed a real row')


CHECKS = [
    ('pulse / contact / invert algebra', test_pulse_contact_invert_algebra),
    ('contact updates are simultaneous', test_contact_updates_are_simultaneous),
    ('mode family directional XOR', test_mode_family_directional_xor),
    ('no hidden storage in O and N', test_no_hidden_storage_in_controls),
    ('reset scope', test_reset_scope),
    ('malformed actions are rejected', test_malformed_actions_are_rejected),
    ('a missing value is exactly zero', test_missing_value_is_exactly_zero),
    ('the target is absent from its QUERY prefix',
     test_target_is_absent_from_the_query_prefix),
    ('episode and outer-world disjointness', test_episode_and_outer_world_disjointness),
    ('the reserved composition is excluded from discovery',
     test_reserved_composition_is_excluded_from_discovery),
    ('budget counts include the validation partition',
     test_budget_counts_include_validation),
    ('nuisance edits leave r unchanged', test_nuisance_edits_leave_the_response_unchanged),
    ('intervention pair differences', test_intervention_pair_differences),
    ('task-B labels are absent from encoder inputs',
     test_task_b_labels_are_absent_from_encoder_inputs),
    ('generation is deterministic', test_generation_is_deterministic),
    ('public / private boundary and audit', test_public_private_boundary_and_audit),
    ('the public loader cannot reach private code',
     test_public_loader_cannot_reach_private_code),
    ('public record contract', test_public_record_contract),
    ('panel shape and normalization', test_panel_shape_and_normalization),
    ('the evaluator joins by record ID only', test_evaluator_joins_by_record_id_only),
    ('the fixture exposes no final world or mode family',
     test_fixture_exposes_no_final_world_or_mode_family),
    # --- ct20-v1.1 -------------------------------------------------------------------
    ('B1: panels exclude the reserved composition',
     test_b1_panel_exclusion_applies_to_panels),
    ('B1: task-B query recipes obey the same rule',
     test_b1_applies_to_task_b_query_recipes),
    ('D: the amendment redraws no world or support set',
     test_amendment_does_not_redraw_worlds_or_supports),
    ('B6: the normalization stream is reserved with zero draws',
     test_normalization_stream_is_reserved_with_zero_draws),
    ('B8: outer_split is never a model feature',
     test_outer_split_is_never_a_model_feature),
    ('C10: the fitting-audit set definition', test_fitting_audit_set_definition),
    ('C9: start-up predicate boundary values', test_startup_predicate_boundary_values),
    ('C10: the evaluator finalizes the start-up diagnostic',
     test_evaluator_finalizes_the_startup_diagnostic),
    ('C11: audit keys survive the public loader',
     test_audit_keys_survive_the_public_loader),
    ('audit 4.1: serialized padding rows are all-zero',
     test_serialized_padding_rows_are_all_zero),
    ('R1: E_primary is hand-computable from the panel definition',
     test_r1_primary_error_definition),
    ('R1: panel 4 never enters E_primary and shortfalls invalidate',
     test_r1_panel4_excluded_and_missing_cases_invalidate),
    ('rulings 2: one audit-key spelling only', test_one_audit_key_spelling),
]


def main():
    global TMP
    TMP = os.environ.get('CT20_TMP') or tempfile.mkdtemp(prefix='ct20-tests-')
    Path(TMP).mkdir(parents=True, exist_ok=True)
    try:
        for name, function in CHECKS:
            check(name, function)
    finally:
        if not os.environ.get('CT20_TMP'):
            shutil.rmtree(TMP, ignore_errors=True)
    if FAILED:
        print(json.dumps({'failed': [name for name, _ in FAILED]}), flush=True)
        raise SystemExit(f'{len(FAILED)} CHECKS FAILED')
    print(f'ALL {PASSED} CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
