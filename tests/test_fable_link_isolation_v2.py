"""Checks for scripts/fable_link_isolation_v2.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_link_isolation_v2.py
Run a group: python3.12 -B tests/test_fable_link_isolation_v2.py --only loss
Groups: schedule, streams, validation, arms, loss, frozen, poison, measure, score, gate,
        preflight, smoke.

``smoke`` runs every subcommand -- ``build-validation``, ``freeze``, ``wave`` (real
subprocesses), ``worker``, ``qualify`` and ``report`` -- for 10 updates per stage on
non-registered dev seeds >= 995100, into a temporary directory selected with
``FABLE_LINK_ISOLATION_V2_OUT``. It never touches a registered panel, never trains a
registered seed (1400/1401/1402) and never writes into the BASE checkout.

The ten PREFLIGHT items the spec lists are the ``preflight`` group plus the dedicated
``poison``, ``frozen``, ``gate`` and ``schedule`` groups; each item names itself in its
check text.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts'), str(HERE)):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_link_isolation_v2 as G                                   # noqa: E402
import fable_link_isolation as G1                                     # noqa: E402
import fable_operator_startup as S                                    # noqa: E402
import fable_operator_variants as V                                   # noqa: E402
from test_fable_link_isolation import Poison                          # noqa: E402

A, E, T, data, torch, P, C, R = G.A, G.E, G.T, G.data, G.torch, G.P, G.C, G.R
F = G.F
LINK, QUESTION, ANSWER, WORLD = G.LINK, G.QUESTION, G.ANSWER, G.WORLD
ENTITY_MIN, ENTITY_MAX, ENTITIES = G.ENTITY_MIN, G.ENTITY_MAX, G.ENTITIES
DEV_SEED = 995101                     # dev seeds are >= 995100; never 1400/1401/1402
SHARED_KEY = 'fable-link-isolation-v2-check:vrng'
CHECKS = 0


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def fresh_model(seed=DEV_SEED):
    return G.new_model(seed)


def params_of(model):
    return [p.detach().clone() for p in model.parameters()]


def same_params(a, b, tol=0.):
    return all(bool((x - y).abs().max() <= tol) for x, y in zip(a, b))


def grads_of(model):
    return [None if p.grad is None else p.grad.detach().clone() for p in model.parameters()]


def same_grads(a, b, tol=0.):
    return all((x is None and y is None) or bool((x - y).abs().max() <= tol)
               for x, y in zip(a, b))


def inputs_equal(x, y):
    return (torch.equal(x.memory, y.memory) and torch.equal(x.questions, y.questions)
            and torch.equal(x.owner, y.owner) and torch.equal(x.eligible, y.eligible))


def stage_a(step=0, seed=DEV_SEED, rng=None, visits=4, forbidden=frozenset(), **params):
    G.configure('a', seed=seed, **params)
    G.set_step(step)
    return G.training_batch_stage_a(rng or random.Random(1101), visits, forbidden)


def stage_b(seed=DEV_SEED, rng=None, visits=4, arm=None, vrng_key=SHARED_KEY,
            forbidden=frozenset(), **params):
    """One stage-B batch. ``arm`` is set in STATE on purpose: the batch must ignore it."""
    G.configure('b', seed=seed, arm=arm, **params)
    if vrng_key is not None:
        G1.STATE['vrng'] = random.Random(vrng_key)
    return G.training_batch_stage_b(rng or random.Random(1101), visits, forbidden)


def batch_b_equal(a, b):
    return (inputs_equal(a.one_hop, b.one_hop) and inputs_equal(a.link, b.link)
            and inputs_equal(a.terminal, b.terminal)
            and inputs_equal(a.combined_all, b.combined_all)
            and inputs_equal(a.combined_head, b.combined_head)
            and torch.equal(a.one_hop_answers, b.one_hop_answers)
            and torch.equal(a.terminal_index, b.terminal_index)
            and torch.equal(a.two_hop_answers, b.two_hop_answers)
            and torch.equal(a.present, b.present)
            and a.plan == b.plan and a.accounting == b.accounting
            and torch.equal(a.diagnostics['intermediate'], b.diagnostics['intermediate'])
            and torch.equal(a.diagnostics['shares_answer'], b.diagnostics['shares_answer']))


def small_sets():
    return dict(qualification=G.build_validation('qualification', 6, 16, 4, 16),
                six=G.build_validation('probe-six', 6, 16, 4, 16),
                sixteen=G.build_validation('probe-sixteen', ENTITIES, 16, 4, 16))


# ------------------------------------------------------------------- PREFLIGHT 10: schedule

def test_schedule():
    anchors = G.stage_b_schedule_anchors(3000)
    check('PREFLIGHT 10: the stage-B budget is 3,000 updates',
          G.STAGE_B_UPDATES == 3000 and anchors['updates'] == 3000)
    check('PREFLIGHT 10: warm-up is 100 updates to 1e-3',
          anchors['warmup'] == 100 and G.lr_stage_b(0, 3000) == 1e-5
          and G.lr_stage_b(99, 3000) == 1e-3,
          f"lr(0)={G.lr_stage_b(0, 3000):.2e}, lr(99)={G.lr_stage_b(99, 3000):.2e}")
    check('PREFLIGHT 10: the rate is flat at 1e-3 through update 2,000',
          anchors['flat_through'] == 2000
          and all(G.lr_stage_b(s, 3000) == 1e-3 for s in range(99, 2001, 7)))
    check('PREFLIGHT 10: the rate decays linearly to 1e-4 at 3,000',
          abs(G.lr_stage_b(2500, 3000) - 5.5e-4) < 1e-15
          and abs(G.lr_stage_b(3000, 3000) - 1e-4) < 1e-15
          and abs(G.lr_stage_b(2999, 3000) - 1.009e-4) < 1e-9,
          f'lr(2500)={G.lr_stage_b(2500, 3000):.3e}, lr(2999)={G.lr_stage_b(2999, 3000):.3e}')
    check('v2 stage B does NOT reuse v1\'s 50-update warm-up',
          G.lr_stage_b(50, 3000) != G1.lr_at_scaled(50, 3000)
          and G1.lr_at_scaled(50, 3000) == 1e-3,
          f'v2 {G.lr_stage_b(50, 3000):.2e} vs v1 {G1.lr_at_scaled(50, 3000):.2e}')
    check('stage A retains the proposal\'s schedule verbatim',
          all(G.lr_stage_a(s, 3000) == G1.lr_at_scaled(s, 3000) for s in range(0, 3000, 11))
          and all(G.lr_stage_a(s, 6000) == V.lr_at(s) for s in range(0, 6000, 17)))
    check('the registered seeds are 1400/1401/1402 and are never replaced',
          G.SEEDS == (1400, 1401, 1402))
    check('the arms are shared / frozen / frozen-present-mask, with detached as a flagged '
          'diagnostic, and v1\'s renormalised frozen-terminal-6 is gone',
          G.PRIMARY_ARMS == ('shared', 'frozen', 'frozen-present-mask')
          and G.DIAGNOSTIC_ARMS == ('detached',)
          and 'frozen-terminal-6' not in G.ALL_ARMS)


# ------------------------------------------------------------------- independent RNG streams

def test_streams():
    names = (G.NAMESPACE_MODEL, G.NAMESPACE_TORCH, G.NAMESPACE_WORLD, G.NAMESPACE_A,
             G.NAMESPACE_A_EXTRA, G.NAMESPACE_B, G.NAMESPACE_VALIDATION)
    check('model, torch, world, curriculum, extra, stage-B and validation streams are all '
          'independently NAMED', len(set(names)) == len(names), ', '.join(names))
    check('the stage-B curriculum namespace does not contain the arm',
          all(arm not in G.NAMESPACE_B for arm in G.ALL_ARMS))
    seeds = (1400, 1401, 1402)
    model_seeds = [G.named_seed(G.NAMESPACE_MODEL, s) for s in seeds]
    check('each registered seed gets a different model init draw',
          len(set(model_seeds)) == 3, str(model_seeds))
    check('the model stream is independent of the data streams',
          all(G.named_seed(G.NAMESPACE_MODEL, s) != G.named_seed(G.NAMESPACE_WORLD, s)
              for s in seeds))
    worlds = []
    for seed in seeds:
        rng = G.world_rng(seed)
        worlds.append([rng.random() for _ in range(8)])
    check('each seed draws a DIFFERENT world stream (v1 used random.Random(1101) for all)',
          len({tuple(w) for w in worlds}) == 3
          and worlds[0] != [random.Random(1101).random() for _ in range(8)])
    prints = [C.fingerprint(G.new_model(s)) for s in seeds]
    check('the three registered seeds really produce different initial weights',
          len(set(prints)) == 3, ', '.join(f[:10] for f in prints))


# -------------------------------------------------------------------------- validation sets

def test_validation():
    sets = small_sets()
    six = sets['six']
    check('a validation set has exactly the requested two-hop and per-relation counts',
          six['n'] == 16 and six['attribute_per_relation'] == 16)
    counts = {r: 0 for r in G.ATTRIBUTE_RELATIONS}
    for chunk in six['chunks']:
        for relation in chunk.one_hop.questions[:, 2].tolist():
            counts[relation] += 1
    check('every attribute relation reaches its own denominator',
          counts == {8: 16, 9: 16, 10: 16}, str(counts))
    check('the six-person set has six present people, the sixteen-person set sixteen',
          bool(six['chunks'][0].present.sum(1).eq(6).all())
          and bool(sets['sixteen']['chunks'][0].present.sum(1).eq(ENTITIES).all()))
    again = G.build_validation('probe-six', 6, 16, 4, 16)
    check('a validation set is deterministic and fingerprintable',
          G.set_fingerprint(again) == G.set_fingerprint(six))
    check('a different label draws different worlds',
          G.set_fingerprint(sets['qualification']) != G.set_fingerprint(six))
    chunk = six['chunks'][0]
    paths = A.truth_paths(chunk.monolithic)
    check('PREFLIGHT 5: the set\'s answers and middle people agree with the visible-fact '
          'interpreter',
          [p[-1]['target'] for p in paths] == chunk.answers.tolist()
          and [p[0]['target'] for p in paths] == chunk.intermediate.tolist(),
          f'{len(paths)} two-hop questions')
    check('PREFLIGHT 5: relation 10 is never a two-hop terminal',
          not bool((chunk.terminal.questions[:, 2] == 10).any())
          and set(chunk.monolithic.questions[:, 3].tolist()) <= set(G.TWO_HOP_RELATIONS))
    check('every two-hop question is a real LINK question over visible facts',
          bool((chunk.link.questions[:, 2] == LINK).all())
          and chunk.monolithic.questions.shape[1] == 5)
    signatures = G.set_signatures(six)
    check('the set\'s ACTUAL semantic signatures are recoverable from the packed inputs',
          len(signatures) > six['n'], f'{len(signatures)} signatures')
    families = {}
    for label, vset in sets.items():
        families[label] = G.set_signatures(vset)
    check('PREFLIGHT 6: the qualification family is disjoint from the probe family',
          not (families['qualification'] & families['six']))
    registered = G.registered_exclusion()
    check('PREFLIGHT 6: no validation question collides with the registered exclusion set',
          not (signatures & registered), f'{len(registered)} registered entries')

    # build-validation writes the union, and the union really contains the signatures.
    root = Path(tempfile.mkdtemp(prefix='fable-link-v2-validation-'))
    was = G.OUT
    try:
        G.OUT = root
        G.build_validation_command(G.normalize_params(dict(
            probe_six=16, probe_sixteen=16, probe_attribute=16, qualification_two_hop=16,
            qualification_attribute=16, confirm_six=16, confirm_sixteen=16,
            confirm_attribute=16, probe_per_visit=4)))
        union = set(json.loads((root/'validation'/'exclusion_union.json').read_text()))
        blob = json.loads((root/'validation'/'validation.json').read_text())
        check('PREFLIGHT 6: build-validation writes an exclusion UNION containing every '
              'validation signature',
              signatures <= union and registered <= union
              and blob['families_pairwise_disjoint'] is True,
              f'{len(union)} entries, {len(registered)} registered')
        check('the five registered sets are all described in validation.json',
              set(blob['sets']) == set(G.VALIDATION_SETS)
              and blob['selected_on_model_outcomes'] is False)
        check('the confirmation family is reserved: disjoint from probe and qualification',
              blob['families_pairwise_disjoint'] and set(blob['families']) ==
              {'qualification', 'probe', 'confirmation'})
    finally:
        G.OUT = was
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------- PREFLIGHT 3: paired batches per arm

def test_arms(visits=4, batches=8):
    per_arm = {}
    for arm in G.ALL_ARMS:
        G.configure('b', seed=DEV_SEED, arm=arm)
        G1.STATE['vrng'] = random.Random(SHARED_KEY)
        rng = random.Random(1101)
        per_arm[arm] = ([G.training_batch_stage_b(rng, visits, frozenset())
                         for _ in range(batches)], rng.getstate(),
                        G1.STATE['vrng'].getstate())
    reference = per_arm['shared']
    for arm in G.ALL_ARMS[1:]:
        mine = per_arm[arm]
        check(f'PREFLIGHT 3: {arm}: all {batches} batches are bit-identical to shared\'s',
              all(batch_b_equal(x, y) for x, y in zip(reference[0], mine[0])))
        check(f'PREFLIGHT 3: {arm}: the world and curriculum streams end in the same state',
              reference[1] == mine[1] and reference[2] == mine[2])
    check('v2 never writes the arm into the batch builder\'s state',
          G1.STATE['arm'] is None and G.STATE['arm'] == G.ALL_ARMS[-1])

    streams, optimizer_states = {}, {}
    for arm in G.ALL_ARMS:
        model = fresh_model()
        frozen = G.make_frozen(model)
        G.configure('b', seed=DEV_SEED, arm=arm, frozen=frozen)
        G1.STATE['vrng'] = random.Random(SHARED_KEY)
        rng = random.Random(1101)
        optimizer = T.optimizer_for(model)
        seen = []
        for step in range(3):
            G.set_step(step)
            batch = G.training_batch_stage_b(rng, visits, frozenset())
            seen.append(batch)
            G._step_stage_b(model, optimizer, batch, step, 3000)
        streams[arm] = (seen, params_of(model))
        optimizer_states[arm] = sorted(optimizer.state_dict()['param_groups'][0])
    check('after 3 real updates the arms have still seen identical batches',
          all(batch_b_equal(x, y) for arm in G.ALL_ARMS[1:]
              for x, y in zip(streams['shared'][0], streams[arm][0])))
    check('PREFLIGHT 3: every arm uses the same optimizer configuration',
          len({tuple(v) for v in optimizer_states.values()}) == 1)
    check('after 3 real updates the primary arms have moved to DIFFERENT weights',
          not same_params(streams['shared'][1], streams['frozen'][1], tol=1e-12)
          and not same_params(streams['frozen'][1],
                              streams['frozen-present-mask'][1], tol=1e-12))


# ------------------------------------------------------------------------------- the losses

def test_loss(visits=4):
    batch = stage_b(visits=visits, single_forward=False)
    model = fresh_model()
    frozen = G.make_frozen(model)
    with torch.no_grad():
        v1_shared = G1.stage_b_losses(model, batch, 'shared')
        v1_frozen = G1.stage_b_losses(model, batch, 'frozen-terminal', frozen)
        arms = {arm: G.stage_b_losses(model, batch, arm, frozen) for arm in G.ALL_ARMS}
    check('shared reproduces v1\'s shared loss at tolerance 0',
          tuple(map(float, arms['shared'])) == tuple(map(float, v1_shared)))
    check('frozen reproduces v1\'s frozen-terminal loss at tolerance 0',
          tuple(map(float, arms['frozen'])) == tuple(map(float, v1_frozen)))
    check('with an unchanged frozen copy, frozen equals shared (the arms differ only in '
          'WHERE p_term comes from)',
          float(arms['frozen'][1]) == float(arms['shared'][1]))
    check('detached with an unmoved model also equals shared, and is NOT the frozen arm',
          float(arms['detached'][1]) == float(arms['shared'][1])
          and 'detached' in G.DIAGNOSTIC_ARMS)
    check('frozen-present-mask differs from frozen (10 absent identities are dropped)',
          float(arms['frozen-present-mask'][1]) != float(arms['frozen'][1]),
          f"{float(arms['frozen-present-mask'][1]):.6f} vs {float(arms['frozen'][1]):.6f}")
    check('the attribute CE term is identical in every arm',
          len({float(v[0]) for v in arms.values()}) == 1)

    # The clean absent-candidate arm, computed by hand: mask, NO renormalisation.
    with torch.no_grad():
        link_logits = model(batch.link)
        pt = model(batch.terminal).softmax(-1)[batch.terminal_index]
        n = link_logits.shape[0]
        conditional = pt.gather(
            2, batch.two_hop_answers[:, None, None].expand(n, ENTITIES, 1)).squeeze(2)
        p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX].double()
        mask = batch.present.double()
        hand = -((p1*mask*conditional.double()).sum(1)).log().mean()
        renormalised = -(((p1*mask)/(p1*mask).sum(1, keepdim=True)
                          * conditional.double()*mask).sum(1)).log().mean()
    check('frozen-present-mask sums only over present people and does NOT renormalise',
          abs(float(arms['frozen-present-mask'][1]) - float(hand)) < 1e-5
          and abs(float(arms['frozen-present-mask'][1]) - float(renormalised)) > 1e-3,
          f"arm {float(arms['frozen-present-mask'][1]):.6f}, hand {float(hand):.6f}, "
          f'v1-style renormalised {float(renormalised):.6f}')
    with torch.no_grad():
        terminal_probabilities = model(batch.terminal).softmax(-1)
        masked_marginal = G.marginal_from(batch, link_logits, terminal_probabilities,
                                          present_mask=True)
        plain_marginal = G.marginal_from(batch, link_logits, terminal_probabilities)
    check('the absent/non-entity penalty survives the mask (the masked marginal is SMALLER '
          'than the unrestricted one, never renormalised back up)',
          bool((masked_marginal <= plain_marginal).all())
          and bool((masked_marginal < plain_marginal).any()))
    with torch.no_grad():
        sixteen_mask = copy.deepcopy(batch)
        sixteen_mask.present = torch.ones_like(batch.present)
        masked = G.marginal_from(sixteen_mask, link_logits,
                                 model(batch.terminal).softmax(-1), present_mask=True)
        plain = G.marginal_from(sixteen_mask, link_logits,
                                model(batch.terminal).softmax(-1))
    check('with every identity present the masked marginal IS the unrestricted marginal',
          bool(torch.equal(masked, plain)))

    w1, w2 = G.link_weights(batch)
    check('the coefficients are 1/3 attribute CE + 1/3 marginal, monolithic REMOVED not '
          'renormalised', (w1, w2) == (1/3, 1/3), f'({w1:.6f}, {w2:.6f})')
    check('PREFLIGHT 5: the stage-B batch carries no monolithic record and 2+2 per visit',
          batch.accounting['kinds']['monolithic'] == 0
          and batch.accounting['kinds']['one_hop'] == 2*visits
          and batch.accounting['kinds']['marginalised_two_hop'] <= 2*visits)

    # where the gradient goes
    h = fresh_model()
    one_logits, link_logits, terminal = G.stage_b_pieces(h, batch, 'shared', None)
    link_logits.retain_grad(); terminal.retain_grad()
    (-G.marginal_from(batch, link_logits, terminal).clamp_min(1e-12).log().mean()).backward()
    check('shared: the marginal reaches BOTH the LINK call and the terminal call',
          float(link_logits.grad.abs().max()) > 0 and float(terminal.grad.abs().max()) > 0)
    for arm in ('frozen', 'frozen-present-mask', 'detached'):
        k = fresh_model()
        k_frozen = G.make_frozen(fresh_model(DEV_SEED+1))
        _one, link_logits, terminal = G.stage_b_pieces(k, batch, arm, k_frozen)
        check(f'{arm}: p_term carries no gradient at all',
              terminal.requires_grad is False and terminal.grad_fn is None)
        link_logits.retain_grad()
        (-G.marginal_from(batch, link_logits, terminal,
                          present_mask=(arm == 'frozen-present-mask')
                          ).clamp_min(1e-12).log().mean()).backward()
        check(f'{arm}: the marginal still reaches the LINK call',
              float(link_logits.grad.abs().max()) > 0)
        check(f'{arm}: not one gradient reaches the frozen copy',
              all(q.grad is None for q in k_frozen.parameters()))

    packed = stage_b(visits=visits, single_forward=True)
    separate = stage_b(visits=visits, single_forward=False)
    ref = fresh_model()
    for arm in G.ALL_ARMS:
        with torch.no_grad():
            a1, a2 = G.stage_b_losses(ref, packed, arm, G.make_frozen(ref))
            b1, b2 = G.stage_b_losses(ref, separate, arm, G.make_frozen(ref))
        check(f'{arm}: --single-forward agrees with separate forwards to 1e-6',
              abs(float(a1)-float(b1)) < 1e-6 and abs(float(a2)-float(b2)) < 1e-6)
    flops = {arm: G.training_flops_stage_b(packed, ref, arm, G.make_frozen(ref))
             for arm in G.ALL_ARMS}
    check('the non-shared arms are charged less than shared (no terminal backward)',
          all(flops[arm] < flops['shared'] for arm in G.ALL_ARMS[1:]),
          ', '.join(f'{k} {v/1e9:.3f}' for k, v in flops.items()) + ' GFLOP/update')


# -------------------------------------------------------- PREFLIGHT 2: the immutable copy

def test_frozen(visits=4, updates=5):
    for arm in G.FROZEN_ARMS:
        model = fresh_model()
        frozen = G.make_frozen(model)
        before = params_of(frozen)
        fingerprint = C.fingerprint(frozen)
        optimizer = T.optimizer_for(model)
        check(f'PREFLIGHT 2: {arm}: the frozen copy passes every check at initialisation',
              G.assert_frozen_intact(frozen, fingerprint, optimizer, 'initialisation'))
        G.configure('b', seed=DEV_SEED, arm=arm, frozen=frozen)
        G1.STATE['vrng'] = random.Random(SHARED_KEY)
        rng = random.Random(1101)
        for step in range(updates):
            G.set_step(step)
            G._step_stage_b(model, optimizer,
                            G.training_batch_stage_b(rng, visits, frozenset()), step, 3000)
            G.assert_frozen_intact(frozen, fingerprint, optimizer, f'checkpoint {step}')
        check(f'PREFLIGHT 2: {arm}: the frozen copy is bit-identical after {updates} updates',
              same_params(before, params_of(frozen), tol=0.)
              and C.fingerprint(frozen) == fingerprint)
        check(f'PREFLIGHT 2: {arm}: eval mode, no grads, not in the optimizer',
              G.assert_frozen_intact(frozen, fingerprint, optimizer, 'final scoring'))
        check(f'{arm}: the trainable model DID move', C.fingerprint(model) != fingerprint)

    model = fresh_model()
    frozen = G.make_frozen(model)
    fingerprint = C.fingerprint(frozen)
    optimizer = T.optimizer_for(model)
    failures = 0
    for label, mutate in (
            ('a moved weight', lambda: next(frozen.parameters()).data.add_(1e-6)),
            ('train mode', lambda: frozen.train()),
            ('requires_grad', lambda: next(frozen.parameters()).requires_grad_(True))):
        undo = copy.deepcopy(frozen.state_dict())
        mutate()
        try:
            G.assert_frozen_intact(frozen, fingerprint, optimizer, 'tamper')
        except AssertionError:
            failures += 1
        frozen.load_state_dict(undo)
        frozen.eval()
        for q in frozen.parameters():
            q.requires_grad_(False)
    check('PREFLIGHT 2: the immutability check CATCHES a moved weight, train mode and '
          'requires_grad', failures == 3, f'{failures}/3 tampering attempts rejected')
    shared_optimizer = T.optimizer_for(frozen)
    rejected = False
    try:
        G.assert_frozen_intact(frozen, fingerprint, shared_optimizer, 'tamper')
    except AssertionError:
        rejected = True
    check('PREFLIGHT 2: the check CATCHES a frozen parameter inside the optimizer', rejected)


# --------------------------------------------- PREFLIGHT 1: label-free / poison invariance

def test_poison(visits=4, K=2):
    clean_a = stage_a(step=0, visits=visits, stage_a_extra=K)
    with Poison():
        dirty_a = stage_a(step=0, visits=visits, stage_a_extra=K)
    check('PREFLIGHT 1: stage A: poisoned gold/supplied/answer/hops/relation leaves the '
          'batch identical',
          inputs_equal(clean_a.one_hop, dirty_a.one_hop)
          and torch.equal(clean_a.one_hop_targets.answer, dirty_a.one_hop_targets.answer)
          and clean_a.accounting == dirty_a.accounting)
    a, b = fresh_model(), fresh_model()
    G.configure('a', seed=DEV_SEED, stage_a_extra=K)
    G._step_stage_a(a, T.optimizer_for(a), clean_a, 0)
    G._step_stage_a(b, T.optimizer_for(b), dirty_a, 0)
    check('PREFLIGHT 1: stage A: poisoned annotations leave the loss and the update identical',
          same_params(params_of(a), params_of(b), tol=0.))

    clean_b = stage_b(visits=visits)
    with Poison():
        dirty_b = stage_b(visits=visits)
    check('PREFLIGHT 1: stage B: poisoned gold leaves the batch identical, diagnostics '
          'included', batch_b_equal(clean_b, dirty_b))
    for arm in G.ALL_ARMS:
        c, d = fresh_model(), fresh_model()
        G.configure('b', seed=DEV_SEED, arm=arm, frozen=G.make_frozen(c))
        G._step_stage_b(c, T.optimizer_for(c), clean_b, 0, 3000)
        G.STATE['frozen'] = G.make_frozen(d)
        G._step_stage_b(d, T.optimizer_for(d), dirty_b, 0, 3000)
        check(f'PREFLIGHT 1: {arm}: poisoned annotations leave the update identical',
              same_params(params_of(c), params_of(d), tol=0.))

    for arm in G.ALL_ARMS:
        batch = stage_b(visits=visits)
        model, frozen = fresh_model(), G.make_frozen(fresh_model(DEV_SEED+1))
        w1, w2 = G.link_weights(batch)
        one, marg = G.stage_b_losses(model, batch, arm, frozen)
        (w1*one + w2*marg).backward()
        clean_grads = grads_of(model)
        clean_loss = (float(one.detach()), float(marg.detach()))
        truth = {k: v.clone() for k, v in batch.diagnostics.items()}
        batch.diagnostics['intermediate'] = torch.full_like(truth['intermediate'], ENTITY_MIN)
        batch.diagnostics['shares_answer'] = torch.zeros_like(truth['shares_answer'])
        other = fresh_model()
        one2, marg2 = G.stage_b_losses(other, batch, arm, frozen)
        (w1*one2 + w2*marg2).backward()
        check(f'PREFLIGHT 1: {arm}: scrambled evaluator-only diagnostics change no loss and '
              'no gradient',
              same_grads(clean_grads, grads_of(other), tol=0.)
              and (float(one2.detach()), float(marg2.detach())) == clean_loss)
        batch.diagnostics.update(truth)

    batch = stage_b(visits=visits)
    model, frozen = fresh_model(), G.make_frozen(fresh_model(DEV_SEED+1))
    scrambled = copy.deepcopy(batch)
    scrambled.present = torch.ones_like(batch.present)
    losses = {}
    for arm in G.ALL_ARMS:
        with torch.no_grad():
            losses[arm] = (float(G.stage_b_losses(model, batch, arm, frozen)[1]),
                           float(G.stage_b_losses(model, scrambled, arm, frozen)[1]))
    check('only frozen-present-mask reads the present mask in its loss',
          all(losses[arm][0] == losses[arm][1]
              for arm in ('shared', 'frozen', 'detached'))
          and losses['frozen-present-mask'][0] != losses['frozen-present-mask'][1])

    memory = batch.link.memory.tolist()
    wanted = []
    for owner, q in zip(batch.link.owner.tolist(), batch.link.questions.tolist()):
        wanted += [row[3] for row in memory[owner]
                   if len(row) >= 4 and row[0] == WORLD and row[1] == q[1] and row[2] == LINK]
    check('the logged intermediate is the visit\'s visible LINK target',
          wanted == batch.diagnostics['intermediate'].tolist(), f'{len(wanted)} records')


# ------------------------------------------------------------------------- the measurements

def test_measure():
    six = G.build_validation('probe-six', 6, 32, 4, 32)
    sixteen = G.build_validation('probe-sixteen', ENTITIES, 32, 4, 32)
    model = fresh_model()
    frozen = G.make_frozen(fresh_model(DEV_SEED+1))
    row = G.measure_set(model, six, frozen, execution=True)
    for key in G.MEASURED_KEYS:
        check(f'the every-100 line reports {key}', key in row)
    check('the two-call rollout and the frozen margin are reported too',
          'execution' in row and 'frozen_terminal_margin' in row)
    reference = G1.probe_diagnostics(model, six, frozen)
    differ = {k for k in reference if k != 'execution' and row.get(k) != reference.get(k)}
    check('measure_set(execution=True) reproduces v1\'s probe_diagnostics exactly',
          not differ, f'{len(reference)} keys compared')
    mass = sum(row[k] for k in ('p_link_true', 'p_link_wrong_present', 'p_link_absent',
                                'p_link_non_entity'))
    check('the four p_link masses partition the FULL LINK softmax',
          abs(mass - 1.) < 2e-3, f'sum {mass:.6f}')
    check('PREFLIGHT 4: full-vocabulary and entity-only argmax are reported SEPARATELY and '
          'are not the same statistic',
          row['link_accuracy'] != row['link_accuracy_entity_argmax']
          or row['link_accuracy'] == 0.,
          f"full {row['link_accuracy']}, entity-only {row['link_accuracy_entity_argmax']}")
    check('the sixteen-person set has no absent identity to put mass on',
          G.measure_set(model, sixteen, frozen)['p_link_absent'] == 0.)
    cheap = G.measure_set(model, six, frozen, execution=False)
    check('the every-100 measurement skips only the rollout',
          'execution' not in cheap
          and all(cheap[k] == row[k] for k in G.MEASURED_KEYS))
    before = params_of(model)
    G.measure_set(model, six, frozen, execution=True)
    check('a measurement pass changes no parameter and leaves no gradient',
          same_params(before, params_of(model), tol=0.)
          and all(q.grad is None for q in model.parameters()))


# ----------------------------------------------------------- the two inference systems

def test_score():
    six = G.build_validation('confirm-six', 6, 32, 4, 32)
    model = fresh_model()
    frozen = G.make_frozen(fresh_model(DEV_SEED+1))
    score = G.score_systems(model, six, frozen)
    check('both inference systems are scored separately for a frozen arm',
          set(score['systems']) == {'trainable_two_call', 'link_plus_frozen'})
    check('the two-copy system is labelled as one, with its extra parameter cost',
          score['systems']['link_plus_frozen']['extra_frozen_parameters'] == 79316
          and 'not a parameter-matched' in score['systems']['link_plus_frozen']['note'])
    check('a single-model arm is scored on the deployment system only',
          set(G.score_systems(model, six, None)['systems']) == {'trainable_two_call'})
    for system, blob in score['systems'].items():
        check(f'{system}: the split accounts for every question',
              blob['answer_correct'] + blob['wrong_answer'] + blob['aborted'] == blob['n'] == 32
              and blob['via_right_person'] + blob['via_wrong_person'] == blob['answer_correct']
              and blob['path_and_answer_correct'] == blob['via_right_person'])
    check('PREFLIGHT 4: LINK is scored on the UNRESTRICTED full-vocabulary argmax',
          score['link_correct'] == sum(
              int((model(c.link).argmax(-1) == c.intermediate).sum()) for c in six['chunks']))
    check('the deployment system\'s LINK call is the registered executor\'s first call',
          all(A.execute(model, c.monolithic)['emitted'][i][0]
              == int(model(c.link).argmax(-1)[i])
              for c in six['chunks'] for i in range(int(c.answers.shape[0]))))
    check('attribute accuracy is scored per relation on integer counts',
          set(score['attribute_total'].values()) == {32}
          and set(score['attribute_correct']) == {'8', '9', '10'})

    perfect = dict(label='confirm-six', entities=6, link_correct=487, link_total=512,
                   attribute_correct={'8': 487, '9': 500, '10': 512},
                   attribute_total={'8': 512, '9': 512, '10': 512},
                   systems=dict(trainable_two_call=dict(n=512, path_and_answer_correct=461),
                                link_plus_frozen=dict(n=512, path_and_answer_correct=460)))
    verdict = G.acceptance_verdict(perfect)
    check('acceptance is >=487/512 LINK, >=487/512 attribute per relation and '
          '>=461/512 complete paths+answers, per system',
          verdict['trainable_two_call']['accepted']
          and not verdict['link_plus_frozen']['accepted']
          and '460/512' in verdict['link_plus_frozen']['reasons'][0],
          json.dumps(verdict['link_plus_frozen']['reasons']))
    weak = copy.deepcopy(perfect)
    weak['attribute_correct']['8'] = 486
    check('a lost relation fails BOTH systems (retained attribute accuracy)',
          not any(v['accepted'] for v in G.acceptance_verdict(weak).values()))
    weak = copy.deepcopy(perfect)
    weak['link_correct'] = 486
    check('486/512 LINK fails', not any(v['accepted'] for v in
                                        G.acceptance_verdict(weak).values()))


# ------------------------------------------------------------- PREFLIGHT 9: the stage-A gate

def test_gate():
    six = G.build_validation('qualification', 6, 32, 4, 32)
    model = fresh_model()
    counts = G.qualification_counts(model, six)
    check('the gate counts attribute answers per relation and terminal answers given the '
          'TRUE endpoint',
          set(counts['attribute_total'].values()) == {32}
          and counts['terminal_true_endpoint_total'] == 32)
    check('the gate reports terminal discriminability stratified by answer-value collisions',
          set(counts['terminal_discriminability']) == {'collision', 'no_collision'}
          and all('margin' in v for v in counts['terminal_discriminability'].values())
          and counts['terminal_discriminability']['collision']['n']
          + counts['terminal_discriminability']['no_collision']['n'] == 32,
          json.dumps(counts['terminal_discriminability']))
    ok, reasons = G.qualification_verdict(counts)
    check('an untrained model does not qualify', not ok and reasons)

    good = dict(attribute_correct={'8': 487, '9': 512, '10': 500},
                attribute_total={'8': 512, '9': 512, '10': 512},
                terminal_true_endpoint_correct=487, terminal_true_endpoint_total=512)
    check('487/512 on every relation AND on the terminal criterion qualifies',
          G.qualification_verdict(good)[0])
    for label, spoil in (('relation 8 at 486', dict(attribute_correct={'8': 486, '9': 512,
                                                                      '10': 500})),
                         ('terminal at 486', dict(terminal_true_endpoint_correct=486))):
        blob = dict(good, **spoil)
        check(f'{label} does NOT qualify', not G.qualification_verdict(blob)[0])

    # the refusal paths, against a synthetic output root
    root = Path(tempfile.mkdtemp(prefix='fable-link-v2-gate-'))
    was = G.OUT
    try:
        G.OUT = root
        (root/'astra_canonical_operator_launch.json').write_text(json.dumps(dict(a=1)))
        folder = G.stage_folder('a', seed=DEV_SEED)
        folder.mkdir(parents=True)
        checkpoint = folder/'stage_a.pt'
        checkpoint.write_bytes(b'not a real checkpoint')
        launch = C.sha(root/'astra_canonical_operator_launch.json')

        def refusal():
            try:
                G.require_qualified(DEV_SEED)
            except RuntimeError as exc:
                return str(exc)
            return ''

        check('PREFLIGHT 9: stage B refuses a seed with no qualification file',
              'has not been evaluated' in refusal(), refusal())
        C.write_new(folder/'qualification.json',
                    dict(qualified=False, checkpoint_sha256=C.sha(checkpoint),
                         launch_sha256=launch))
        check('PREFLIGHT 9: a failed seed is refused with the registered wording',
              refusal().endswith(G.FAILED_MESSAGE)
              and G.FAILED_MESSAGE ==
              'stage A failed; stage-B hypothesis untested for this seed', refusal())
        (folder/'qualification.json').unlink()
        C.write_new(folder/'qualification.json',
                    dict(qualified=True, checkpoint_sha256='0'*64, launch_sha256=launch))
        check('PREFLIGHT 9: a qualification evaluated on a DIFFERENT checkpoint is refused',
              'DIFFERENT' in refusal(), refusal())
        (folder/'qualification.json').unlink()
        C.write_new(folder/'qualification.json',
                    dict(qualified=True, checkpoint_sha256=C.sha(checkpoint),
                         launch_sha256='0'*64))
        check('PREFLIGHT 9: a qualification from a different manifest is refused',
              'different registered manifest' in refusal(), refusal())
        (folder/'qualification.json').unlink()
        C.write_new(folder/'qualification.json',
                    dict(qualified=True, checkpoint_sha256=C.sha(checkpoint),
                         launch_sha256=launch))
        check('PREFLIGHT 9: a qualified seed with matching hashes is admitted',
              refusal() == '')
    finally:
        G.OUT = was
        shutil.rmtree(root, ignore_errors=True)


# ------------------------------------------------------------------- remaining preflights

def test_preflight(visits=4):
    batch = stage_a(step=0, visits=visits)
    q = batch.one_hop.questions
    check('PREFLIGHT 5: stage A NEVER builds a LINK query (that would BE the intermediate '
          'label)',
          not bool((q[:, 2] == LINK).any())
          and set(q[:, 2].tolist()) <= set(G.ATTRIBUTE_RELATIONS)
          and batch.accounting['kinds']['link'] == 0)
    check('PREFLIGHT 5: stage A uses no gold intermediate, evidence line or supplied card',
          batch.accounting['gold_entities_used'] == 0
          and batch.accounting['gold_fields_used'] == 0
          and batch.accounting['evidence_lines_used'] == 0)
    check('PREFLIGHT 5: stage A builds six attribute records per visit and nothing else',
          q.shape[0] == 6*visits
          and batch.accounting['kinds']['one_hop'] == 6*visits
          and batch.accounting['kinds']['monolithic'] == 0)
    b = stage_b(visits=visits)
    check('PREFLIGHT 5: no stage-B record carries a LINK target',
          b.accounting['gold_entities_used'] == 0
          and b.accounting['evidence_lines_used'] == 0
          and not hasattr(b, 'link_targets'))

    # train/probe exclusion, enforced on the PRESENTED story.
    presented = G.presented_signatures(b.one_hop, b.link)
    raised = ''
    try:
        G.assert_no_validation_overlap(presented, b.one_hop)
    except RuntimeError as exc:
        raised = str(exc)
    check('PREFLIGHT 6: a planted validation signature stops a training batch (PRESENTED '
          'story)', 'PRESENTED' in raised, raised)
    check('PREFLIGHT 6: a disjoint union leaves the batch alone',
          G.assert_no_validation_overlap({'0'*64}, b.one_hop, b.link, b.terminal))
    raised = ''
    try:
        stage_b(visits=visits, forbidden=frozenset(presented))
    except RuntimeError as exc:
        raised = str(exc)
    check('PREFLIGHT 6: the batch BUILDER also refuses on a constructed-question overlap',
          'overlap' in raised, raised)

    text = G.prereg_path().read_text()
    for phrase in ('decomposition', 'token grammar', 'visible fact parsing'):
        check(f'PREFLIGHT 8: the report states that the {phrase} remains supplied',
              phrase in text)
    check('PREFLIGHT 8: the preregistration ends with an EMPTY predictions section',
          text.rstrip().endswith("## Fable's predictions"))
    check('the preregistration names the withdrawn v1 and its void predictions',
          'WITHDRAWN-BEFORE-ANY-RUN' in text and 'P21' in text)
    check('the preregistration states the acceptance numbers and the three-seed denominator',
          '487/512' in text and '461/512' in text and 'ORIGINAL three-seed denominator' in text)

    model = A.new_model(G.named_seed(G.NAMESPACE_MODEL, DEV_SEED))
    check('parameter count is 79,316', model.parameters_count() == G.PARAMETERS == 79316)
    reference = T.TokenMemoryReasoner()
    check('state-dict schema and shapes unchanged',
          sorted(model.state_dict()) == sorted(reference.state_dict())
          and all(model.state_dict()[k].shape == reference.state_dict()[k].shape
                  for k in reference.state_dict()))
    hooks = (A.training_batch, A.training_step, A.training_flops)
    for stage in G.STAGES:
        G.configure(stage, seed=DEV_SEED)
    check('this module does NOT monkeypatch the registered runner',
          (A.training_batch, A.training_step, A.training_flops) == hooks)
    check('v1 is imported READ-ONLY: its own module constants are untouched',
          G1.NAME == 'fable-link-isolation-20260920'
          and G1.ARMS == ('shared', 'frozen-terminal', 'frozen-terminal-6')
          and G1.STATE['arm'] is None)
    check('the output root follows the registered naming',
          G.NAME == 'fable-link-isolation-v2-20260920'
          and G.stage_folder('b', 'frozen', 1400).name == 'seed-1400')


# ---------------------------------------------------------------------------------- smoke

SIZES = ('--probe-six', '8', '--probe-sixteen', '8', '--probe-attribute', '8',
         '--qualification-two-hop', '8', '--qualification-attribute', '8',
         '--confirm-six', '8', '--confirm-sixteen', '8', '--confirm-attribute', '8',
         '--probe-per-visit', '4')


def run(root, *args):
    env = dict(os.environ, FABLE_LINK_ISOLATION_V2_OUT=str(root), OMP_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([R.PYTHON, '-B', str(Path(G.__file__).resolve()), *args],
                          env=env, capture_output=True, text=True, timeout=1800)


def test_smoke(updates, seed):
    assert seed >= 995100, seed
    assert seed not in G.SEEDS
    root = Path(tempfile.mkdtemp(prefix='fable-link-isolation-v2-smoke-'))
    try:
        started = time.monotonic()
        out = run(root, 'build-validation', *SIZES)
        check('build-validation writes the union and the set descriptions',
              out.returncode == 0
              and (root/'validation'/'exclusion_union.json').exists()
              and (root/'validation'/'validation.json').exists(),
              (out.stdout or out.stderr).strip().splitlines()[-1][:160])
        out = run(root, 'freeze', *SIZES, '--stage-a-updates', str(updates),
                  '--stage-b-updates', str(updates), '--stage-a-seconds', '600',
                  '--stage-b-seconds', '600', '--grow-g1', str(max(1, updates//3)),
                  '--grow-g2', str(max(2, 2*updates//3)), '--include-detached',
                  '--measure-every', '5')
        check('freeze writes a manifest', out.returncode == 0
              and (root/'astra_canonical_operator_launch.json').exists(),
              (out.stdout or out.stderr).strip().splitlines()[-1][:120])
        manifest = json.loads((root/'astra_canonical_operator_launch.json').read_text())
        check('PREFLIGHT 7: freeze hashes v1, both wrappers, this module, the '
              'preregistration and BOTH validation files',
              all(any(k.endswith(name) for k in manifest['files']) for name in
                  ('fable_link_isolation.py', 'fable_link_isolation_v2.py',
                   'fable_operator_startup.py', 'fable_operator_variants.py',
                   'PREREGISTRATION.md', 'exclusion_union.json', 'validation.json')),
              f'{len(manifest["files"])} files frozen')
        check('the manifest records the seeds, the arms and the exclusion union as the '
              'training exclusion path',
              manifest['seeds'] == [1400, 1401, 1402]
              and manifest['arms'] == list(G.ALL_ARMS)
              and manifest['exclusion_path'].endswith('exclusion_union.json')
              and manifest['schedule']['stage_b']['warmup'] == max(1, min(100,
                                                                          (2*updates)//3)))

        out = run(root, 'wave', '--stage', 'b', '--arm', 'frozen', '--seeds', str(seed),
                  '--name', 'gate-refusal')
        check('PREFLIGHT 9: a stage-B wave refuses every seed before stage A has run',
              out.returncode == 0
              and json.loads(out.stdout.strip().splitlines()[-1])['refused'],
              out.stdout.strip().splitlines()[-1][:160])

        out = run(root, 'wave', '--stage', 'a', '--seeds', str(seed), '--name', 'smoke')
        check('wave (stage a) completes', out.returncode == 0
              and json.loads(out.stdout.strip().splitlines()[-1])['complete'],
              (out.stdout.strip().splitlines() or [out.stderr[-200:]])[-1][:160])
        saved = P.load(root/f'stage-a/seed-{seed}/stage_a.pt')
        check('stage_a.pt carries the model, the optimizer, every RNG state and both '
              'named seeds',
              set(saved) >= {'state_dict', 'optimizer', 'torch_rng', 'world_rng', 'vrng',
                             'xrng', 'model_seed', 'torch_seed'}
              and saved['updates'] == updates)

        out = run(root, 'wave', '--stage', 'b', '--arm', 'frozen', '--seeds', str(seed),
                  '--name', 'ungated')
        check('PREFLIGHT 9: stage B still refuses before the gate has been evaluated',
              json.loads(out.stdout.strip().splitlines()[-1])['refused'],
              out.stdout.strip().splitlines()[-1][:160])

        out = run(root, 'qualify', '--seeds', str(seed))
        summary = json.loads(out.stdout.strip().splitlines()[-1])
        check('qualify writes a verdict and reports the ORIGINAL three-seed denominator',
              out.returncode == 0 and summary['registered_seeds'] == [1400, 1401, 1402]
              and summary['qualified_of_registered'].endswith('/3')
              and (root/f'stage-a/seed-{seed}/qualification.json').exists(),
              json.dumps(summary)[:200])

        for arm in G.ALL_ARMS:
            out = run(root, 'wave', '--stage', 'b', '--arm', arm, '--seeds', str(seed),
                      '--name', 'smoke')
            check(f'wave (stage b, {arm}) completes', out.returncode == 0
                  and json.loads(out.stdout.strip().splitlines()[-1])['complete'],
                  (out.stdout.strip().splitlines() or [out.stderr[-200:]])[-1][:160])
            blob = json.loads((root/f'stage-b/{arm}/seed-{seed}/final_score.json').read_text())
            check(f'{arm}: the frozen copy is unchanged and was checked three times',
                  blob['frozen_unchanged']
                  and blob['frozen_fingerprint'] == blob['stage_a_fingerprint']
                  and blob['frozen_checked_at'] == ['initialisation',
                                                    'every logged checkpoint',
                                                    'final scoring'])
            check(f'{arm}: final scoring names the right inference systems',
                  set(blob['confirmation']['confirm-six']['systems'])
                  == ({'trainable_two_call', 'link_plus_frozen'} if arm in G.FROZEN_ARMS
                      else {'trainable_two_call'}))
            check(f'{arm}: the arm kind is stated',
                  ('NOT frozen' in blob['arm_kind']) == (arm in G.DIAGNOSTIC_ARMS))
            lines = [json.loads(line) for line in
                     (root/f'stage-b/{arm}/seed-{seed}/diagnostics.jsonl')
                     .read_text().splitlines()]
            kinds = [line['kind'] for line in lines]
            check(f'{arm}: a full measurement is written BEFORE the first update and after '
                  'the last',
                  lines[0]['kind'] == 'probe-full' and lines[0]['update'] == 0
                  and lines[-1]['kind'] == 'probe-full' and lines[-1]['update'] == updates
                  and 'probe-sixteen' in lines[0]['probes']
                  and 'probe-six' in lines[0]['probes'],
                  f'{len(lines)} lines')
            check(f'{arm}: the periodic measurement writes a train line AND a six-person '
                  'probe line at every interval',
                  kinds.count('train') == kinds.count('probe-probe') == updates//5
                  and all(set(line['probes']) == {'probe-six'} for line in lines
                          if line['kind'] == 'probe-probe')
                  and all(key in line for line in lines if line['kind'] == 'probe-probe'
                          for key in ('update',)),
                  f"{kinds.count('train')} train lines, {kinds.count('probe-probe')} probes")
            measured = [line['probes']['probe-six'] for line in lines
                        if line['kind'] == 'probe-probe']
            check(f'{arm}: every periodic measurement carries the full spec list',
                  all(all(key in row for key in G.MEASURED_KEYS) for row in measured)
                  and all('execution' not in row for row in measured))
            check(f'{arm}: the supplied list names decomposition, grammar and fact parsing',
                  len(blob['supplied']) == 3
                  and any('decomposition' in s for s in blob['supplied']))

        blobs = {arm: json.loads(
            (root/f'stage-b/{arm}/seed-{seed}/final_score.json').read_text())
            for arm in G.ALL_ARMS}
        check('every arm started from the same stage-A checkpoint',
              len({b['stage_a_fingerprint'] for b in blobs.values()}) == 1)
        check('the primary arms ended at different weights',
              len({blobs[a]['final_fingerprint'] for a in G.PRIMARY_ARMS})
              == len(G.PRIMARY_ARMS))

        out = run(root, 'report', '--seeds', str(seed))
        check('report prints the gate, the trajectories and BOTH inference systems',
              out.returncode == 0 and 'qualification gate' in out.stdout
              and 'FINAL CONFIRMATION' in out.stdout
              and 'link_plus_frozen' in out.stdout
              and 'trainable_two_call' in out.stdout
              and 'ORIGINAL three registered seeds' in out.stdout,
              f'{len(out.stdout.splitlines())} lines, {time.monotonic()-started:.0f}s total')

        (root/'astra_canonical_operator_launch.json').write_text(
            json.dumps(dict(manifest, files=dict(manifest['files'], **{'run.py': '0'*64}))))
        out = run(root, 'wave', '--stage', 'a', '--seeds', str(seed), '--name', 'smoke-2')
        check('PREFLIGHT 7: a changed registered file stops the wave',
              out.returncode != 0 and 'registered file changed' in (out.stdout + out.stderr))
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ----------------------------------------------------------------------------------- main

GROUPS = dict(schedule=test_schedule, streams=test_streams, validation=test_validation,
              arms=test_arms, loss=test_loss, frozen=test_frozen, poison=test_poison,
              measure=test_measure, score=test_score, gate=test_gate,
              preflight=test_preflight)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', default=None, choices=list(GROUPS) + ['smoke'])
    ap.add_argument('--smoke-updates', type=int, default=10)
    ap.add_argument('--smoke-seed', type=int, default=995111)
    args = ap.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    data.bootstrap()
    if args.only == 'smoke':
        test_smoke(args.smoke_updates, args.smoke_seed)
    elif args.only:
        GROUPS[args.only]()
    else:
        for fn in GROUPS.values():
            fn()
        test_smoke(args.smoke_updates, args.smoke_seed)
    print(f'ALL {CHECKS} CHECKS PASSED')
