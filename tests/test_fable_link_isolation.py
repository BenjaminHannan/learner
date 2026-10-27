"""Checks for scripts/fable_link_isolation.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_link_isolation.py
Run a group: python3.12 -B tests/test_fable_link_isolation.py --only loss
Groups: stagea, arms, loss, frozen, poison, probe, model, smoke.

``smoke`` runs every subcommand -- ``freeze``, ``wave`` (real subprocesses), ``worker`` and
``report`` -- for 10 updates per stage on non-registered dev seeds >= 995000, into a
temporary directory selected with ``FABLE_LINK_ISOLATION_OUT``. It never touches a
registered panel, never trains a registered seed, and never writes into the BASE checkout.
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
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts')):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_link_isolation as G                                      # noqa: E402
import fable_operator_startup as S                                    # noqa: E402
import fable_operator_variants as V                                   # noqa: E402

A, E, T, data, torch, P, C, R = G.A, G.E, G.T, G.data, G.torch, G.P, G.C, G.R
F = G.F
LINK, QUESTION, ANSWER, WORLD = G.LINK, G.QUESTION, G.ANSWER, G.WORLD
ENTITY_MIN, ENTITY_MAX, ENTITIES = G.ENTITY_MIN, G.ENTITY_MAX, G.ENTITIES
DEV_SEED = 995001                     # dev seeds are >= 995000; never 0-9
SHARED_KEY = 'fable-link-isolation-check:vrng'
CHECKS = 0


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def fresh_model(seed=DEV_SEED):
    return A.new_model(seed)


def frozen_copy(model):
    copied = copy.deepcopy(model)
    copied.eval()
    for parameter in copied.parameters():
        parameter.requires_grad_(False)
    return copied


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


# ------------------------------------------------------------------------------- builders

def stage_a(step=0, seed=DEV_SEED, rng=None, visits=4, **params):
    G.configure('a', seed=seed, **params)
    G.STATE['step'] = step
    return G.training_batch_stage_a(rng or random.Random(1101), visits, frozenset())


def stage_b(seed=DEV_SEED, rng=None, visits=4, arm=None, vrng_key=SHARED_KEY, **params):
    """One stage-B batch. ``arm`` is set in STATE on purpose: the batch must ignore it."""
    G.configure('b', seed=seed, arm=arm, **params)
    if vrng_key is not None:
        G.STATE['vrng'] = random.Random(vrng_key)
    return G.training_batch_stage_b(rng or random.Random(1101), visits, frozenset())


def margfull(rng=None, visits=4, vrng_key=SHARED_KEY, single_forward=True):
    """``marg-full --startup grow-blind`` past its growth window (curriculum fraction 1)."""
    S.configure_variant('marg-full', seed=DEV_SEED, startup='grow-blind', grow_g1=0,
                        grow_g2=0, blind_lines=16, single_forward=single_forward)
    S.STATE['vrng'] = random.Random(vrng_key)
    S.STATE['step'] = 0
    return S.training_batch_margfull(rng or random.Random(1101), visits, frozenset())


def batch_b_equal(a, b):
    """Every tensor a stage-B batch carries, including both packed forwards."""
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


def batch_a_equal(a, b):
    return (inputs_equal(a.one_hop, b.one_hop)
            and torch.equal(a.one_hop_targets.answer, b.one_hop_targets.answer)
            and torch.equal(a.one_hop_targets.lines, b.one_hop_targets.lines)
            and a.plan == b.plan and a.accounting == b.accounting)


# ------------------------------------------------------------------------- poisoned gold

class Poison:
    """Replace every annotation a label-free path must not read with nonsense."""

    def __enter__(self):
        data.bootstrap()
        import premonition.toy_ladder as L
        self.module, self.real = L, L.visit

        def poisoned(spec, rng, **kw):
            rows, world, record = self.real(spec, rng, **kw)
            for row in rows:
                if row.question:
                    row.gold = (10**6, 10**6 + 1)
                    row.supplied = (10**6,)*6
                    row.answer = [-7]
                    row.hops = -1
                    row.relation = -99
            return rows, world, record

        L.visit = poisoned
        return self

    def __exit__(self, *exc):
        self.module.visit = self.real
        return False


# ----------------------------------------------------------------------------- stage A

def test_stagea(visits=4, K=2):
    batch = stage_a(step=0, visits=visits, stage_a_extra=K)
    q = batch.one_hop.questions
    check('stage A builds 4 + K single-call records per visit',
          q.shape == ((4+K)*visits, 4) and batch.accounting['kinds']['one_hop'] == (4+K)*visits,
          f'{q.shape[0]} records, {visits} visits, K={K}')
    check('stage A reaches grow-blind\'s 6 records per visit at the default K',
          stage_a(step=0, visits=visits).one_hop.questions.shape[0]//visits == 6)
    check('stage A NEVER builds a LINK query',
          not bool((q[:, 2] == LINK).any()) and q.shape[1] == 4,
          f'relations {sorted(set(q[:, 2].tolist()))}')
    check('every stage-A relation is an attribute relation',
          set(q[:, 2].tolist()) <= set(G.ATTRIBUTE_RELATIONS))
    check('stage A builds no two-hop, monolithic, link or terminal record',
          batch.accounting['kinds']['marginalised_two_hop'] == 0
          and batch.accounting['kinds']['monolithic'] == 0
          and batch.accounting['kinds']['link'] == 0
          and batch.accounting['kinds']['terminal'] == 0)
    check('stage A uses no gold intermediate, no evidence line and no supplied card',
          batch.accounting['gold_entities_used'] == 0
          and batch.accounting['gold_fields_used'] == 0
          and batch.accounting['evidence_lines_used'] == 0)
    check('stage A places one record at each of the two two-hop question lines',
          batch.accounting['blind']['at_two_hop_line'] == 2*visits)

    paths = A.truth_paths(batch.one_hop)
    check('every stage-A record is answerable from its KEPT ELIGIBLE lines, in ONE call',
          [p[-1]['target'] for p in paths] == batch.one_hop_targets.answer.tolist()
          and all(len(p) == 1 for p in paths), f'{len(paths)} records')
    check('every stage-A answer is read off a kept visible fact row',
          all(batch.one_hop.memory[owner][line].tolist()[:4]
              == [WORLD, int(qq[1]), int(qq[2]), int(ans)]
              for owner, line, qq, ans in zip(batch.one_hop.owner.tolist(),
                                              batch.one_hop_targets.lines[:, 0].tolist(),
                                              q, batch.one_hop_targets.answer.tolist())))

    # The curriculum really reduces the story early and restores it by G2.
    early = stage_a(step=0, visits=visits, grow_g1=750, grow_g2=1500)
    late = stage_a(step=1500, visits=visits, grow_g1=750, grow_g2=1500)
    check('the grow-blind curriculum is on in stage A',
          early.plan['fraction'] == 0. and late.plan['fraction'] == 1.
          and early.one_hop.memory.shape[1] < late.one_hop.memory.shape[1],
          f'{early.one_hop.memory.shape[1]} lines at step 0, '
          f'{late.one_hop.memory.shape[1]} at G2')

    # The loss is a plain answer CE on the one record group; the step is a real update.
    model = fresh_model()
    loss = G.stage_a_loss(model, batch)
    check('stage A\'s loss is the mean answer CE over its records',
          float(loss) == float(F.cross_entropy(model(batch.one_hop),
                                               batch.one_hop_targets.answer)))
    before = params_of(model)
    G.configure('a', seed=DEV_SEED, stage_a_extra=K)
    G._step_stage_a(model, T.optimizer_for(model), batch, 0)
    check('stage A\'s step moves the model', not same_params(before, params_of(model), tol=0.))

    # The lr schedule is v3r's shape, rescaled to the stage length.
    check('lr_at_scaled(s, 6000) is v3r\'s schedule verbatim',
          all(G.lr_at_scaled(s, 6000) == V.lr_at(s) for s in range(0, 6000, 7)))
    check('lr_at_scaled hits the same lr at the same fraction of a 3,000-update stage',
          all(abs(G.lr_at_scaled(s, 3000) - V.lr_at(2*s)) < 1e-15 for s in range(0, 3000, 7))
          and abs(G.lr_at_scaled(2999, 3000) - 1.0009e-4) < 1e-6,
          f'lr(0)={G.lr_at_scaled(0, 3000):.2e}, lr(2999)={G.lr_at_scaled(2999, 3000):.2e}')


# -------------------------------------------------------- the three arms see one batch

def test_arms(visits=4, batches=8):
    per_arm = {}
    for arm in G.ARMS:
        G.configure('b', seed=DEV_SEED, arm=arm)
        G.STATE['vrng'] = random.Random(SHARED_KEY)
        rng = random.Random(1101)
        per_arm[arm] = ([G.training_batch_stage_b(rng, visits, frozenset())
                         for _ in range(batches)], rng.getstate(), G.STATE['vrng'].getstate())
    reference = per_arm['shared']
    for arm in G.ARMS[1:]:
        mine = per_arm[arm]
        check(f'{arm}: all {batches} batches are bit-identical to shared\'s',
              all(batch_b_equal(x, y) for x, y in zip(reference[0], mine[0])),
              f'{batches} batches x {visits} visits')
        check(f'{arm}: the world and curriculum RNG streams end in the same state',
              reference[1] == mine[1] and reference[2] == mine[2])
    check('the curriculum RNG namespace does not contain the arm',
          'arm' not in G.NAMESPACE_B and G.NAMESPACE_B == 'fable-link-isolation-b'
          and all(arm not in G.NAMESPACE_B for arm in G.ARMS))
    src = Path(G.__file__).read_text()
    body = src[src.index('def training_batch_stage_b'):src.index('def marginal_from')]
    code = body.split('"""')[2]                    # the docstring is allowed to say "arm"
    check('the stage-B batch builder never reads STATE["arm"]',
          'arm' not in code, 'checked by source inspection of the builder body')

    # ... and the same batches keep arriving once the models have diverged.
    streams = {}
    for arm in G.ARMS:
        model = fresh_model()
        frozen = frozen_copy(model)
        G.configure('b', seed=DEV_SEED, arm=arm, frozen=frozen)
        G.STATE['vrng'] = random.Random(SHARED_KEY)
        rng = random.Random(1101)
        optimizer = T.optimizer_for(model)
        seen = []
        for step in range(3):
            G.STATE['step'] = step
            batch = G.training_batch_stage_b(rng, visits, frozenset())
            seen.append(batch)
            G._step_stage_b(model, optimizer, batch, step)
        streams[arm] = (seen, params_of(model))
    check('after 3 real updates the arms have still seen identical batches',
          all(batch_b_equal(x, y) for arm in G.ARMS[1:]
              for x, y in zip(streams['shared'][0], streams[arm][0])))
    check('after 3 real updates the arms have moved to DIFFERENT weights',
          not same_params(streams['shared'][1], streams['frozen-terminal'][1], tol=1e-12)
          and not same_params(streams['frozen-terminal'][1],
                              streams['frozen-terminal-6'][1], tol=1e-12))


# ------------------------------------------------------------------------------ the loss

def test_loss(visits=4):
    mine = stage_b(visits=visits, single_forward=False)
    theirs = margfull(visits=visits, single_forward=False)
    check('the stage-B batch is marg-full\'s batch at fraction 1, minus the monolithic group',
          inputs_equal(mine.one_hop, theirs.one_hop) and inputs_equal(mine.link, theirs.link)
          and inputs_equal(mine.terminal, theirs.terminal)
          and torch.equal(mine.terminal_index, theirs.terminal_index)
          and torch.equal(mine.two_hop_answers, theirs.two_hop_answers)
          and torch.equal(mine.one_hop_answers, theirs.one_hop_targets.answer),
          f'{mine.terminal.questions.shape[0]} distinct terminal calls')
    check('the stage-B batch carries no monolithic record',
          mine.accounting['kinds']['monolithic'] == 0
          and theirs.accounting['kinds']['monolithic'] == 2*visits)

    model = fresh_model()
    with torch.no_grad():
        one_s, marg_s = G.stage_b_losses(model, mine, 'shared')
        one_m, marg_m, mono_m = S.margfull_losses(model, theirs)
    check('shared: the one-hop term equals marg-full\'s one-hop term at tolerance 0',
          float(one_s) == float(one_m), f'{float(one_s):.10f}')
    check('shared: the marginal term equals marg-full\'s marginal term at tolerance 0',
          float(marg_s) == float(marg_m), f'{float(marg_s):.10f}')
    w1, w2 = G.link_weights(mine)
    m1, m2, m3 = S.marg_weights(theirs)
    check('the weights are marg-full\'s, with the monolithic third REMOVED not renormalised',
          (w1, w2) == (m1, m2) == (1/3, 1/3), f'({w1:.6f}, {w2:.6f}) vs marg-full ({m1:.6f}, {m2:.6f}, {m3:.6f})')
    got, want = float(w1*one_s + w2*marg_s), float(m1*one_m + m2*marg_m)
    check('shared\'s total loss is marg-full\'s loss with the monolithic term dropped',
          abs(got - want) < 1e-12, f'{got:.10f} vs {want:.10f}')

    # ---- the frozen arms.
    frozen = frozen_copy(model)
    with torch.no_grad():
        one_f, marg_f = G.stage_b_losses(model, mine, 'frozen-terminal', frozen)
        one_6, marg_6 = G.stage_b_losses(model, mine, 'frozen-terminal-6', frozen)
    check('with an unchanged frozen copy, frozen-terminal reproduces shared exactly',
          float(one_f) == float(one_s) and float(marg_f) == float(marg_s),
          'the arms differ only in WHERE p_term comes from')
    check('frozen-terminal-6 differs from frozen-terminal (10 identities are dropped)',
          float(marg_6) != float(marg_f), f'{float(marg_6):.6f} vs {float(marg_f):.6f}')

    # frozen-terminal-6, computed by hand from the same tensors.
    with torch.no_grad():
        link_logits = model(mine.link)
        pt = model(mine.terminal).softmax(-1)[mine.terminal_index]
        n = link_logits.shape[0]
        conditional = pt.gather(2, mine.two_hop_answers[:, None, None].expand(n, ENTITIES, 1)).squeeze(2)
        p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX]
        mask = mine.present.double()
        restricted = (p1.double()*mask)/(p1.double()*mask).sum(1, keepdim=True)
        hand = -(restricted*conditional.double()*mask).sum(1).log().mean()
    check('frozen-terminal-6 sums only over the present people and renormalises p_link',
          abs(float(marg_6) - float(hand)) < 1e-5,
          f'{float(marg_6):.6f} vs hand-computed {float(hand):.6f}')
    check('exactly six identities are present in a six-person world',
          bool(mine.present.sum(1).eq(6).all()) and mine.present.shape[1] == ENTITIES)
    check('the present mask is derived from the visible story rows',
          all(sorted(set(row[1] for row in mine.link.memory[owner].tolist()
                         if S._is_fact(row))
                     | set(row[3] for row in mine.link.memory[owner].tolist()
                           if S._is_fact(row) and row[2] == LINK))
              == [ENTITY_MIN+i for i, on in enumerate(mask.tolist()) if on]
              for owner, mask in zip(mine.link.owner.tolist(), mine.present)))

    # ---- where the gradient goes.
    h = fresh_model()
    one_logits, link_logits, terminal = G.stage_b_pieces(h, mine, 'shared', None)
    link_logits.retain_grad()
    terminal.retain_grad()
    (-G.marginal_from(mine, link_logits, terminal).clamp_min(1e-12).log().mean()).backward()
    check('shared: the marginal reaches BOTH the LINK call and the terminal call',
          float(link_logits.grad.abs().max()) > 0 and float(terminal.grad.abs().max()) > 0)

    k = fresh_model()
    k_frozen = frozen_copy(fresh_model(DEV_SEED+1))          # a DIFFERENT frozen terminal
    one_logits, link_logits, terminal = G.stage_b_pieces(k, mine, 'frozen-terminal', k_frozen)
    check('frozen-terminal: p_term carries no gradient at all',
          terminal.requires_grad is False and terminal.grad_fn is None)
    link_logits.retain_grad()
    (-G.marginal_from(mine, link_logits, terminal).clamp_min(1e-12).log().mean()).backward()
    check('frozen-terminal: the marginal still reaches the LINK call',
          float(link_logits.grad.abs().max()) > 0)
    check('frozen-terminal: not one gradient reaches the frozen copy',
          all(q.grad is None for q in k_frozen.parameters()))

    # ---- single_forward is exact.
    packed = stage_b(visits=visits, single_forward=True)
    separate = stage_b(visits=visits, single_forward=False)
    ref = fresh_model()
    with torch.no_grad():
        a1, a2 = G.stage_b_losses(ref, packed, 'shared')
        b1, b2 = G.stage_b_losses(ref, separate, 'shared')
    check('--single-forward agrees with separate forwards to 1e-6',
          abs(float(a1)-float(b1)) < 1e-6 and abs(float(a2)-float(b2)) < 1e-6,
          f'one {abs(float(a1)-float(b1)):.2e}, marg {abs(float(a2)-float(b2)):.2e}')

    # ---- honest FLOPs.
    model = fresh_model()
    shared_flops = G.training_flops_stage_b(packed, model, 'shared')
    frozen_flops = G.training_flops_stage_b(packed, model, 'frozen-terminal', frozen)
    check('the frozen arms are charged less than shared (no terminal backward)',
          frozen_flops < shared_flops,
          f'{frozen_flops/1e9:.3f} vs {shared_flops/1e9:.3f} GFLOP/update '
          f'({frozen_flops/shared_flops:.3f}x)')
    check('terminal dedupe accounting closes',
          packed.accounting['terminal_calls']
          + packed.accounting['blind']['deduped_terminal_calls']
          == packed.accounting['terminal_calls_undeduped']
          == ENTITIES*packed.accounting['kinds']['marginalised_two_hop'])


# ------------------------------------------------------------------- the frozen terminal

def test_frozen(visits=4, updates=5):
    for arm in ('frozen-terminal', 'frozen-terminal-6'):
        model = fresh_model()
        frozen = frozen_copy(model)
        before = params_of(frozen)
        fingerprint = C.fingerprint(frozen)
        optimizer = T.optimizer_for(model)
        optimized = {id(p) for group in optimizer.param_groups for p in group['params']}
        check(f'{arm}: the optimizer never receives a frozen parameter',
              not any(id(p) in optimized for p in frozen.parameters()))
        G.configure('b', seed=DEV_SEED, arm=arm, frozen=frozen)
        G.STATE['vrng'] = random.Random(SHARED_KEY)
        rng = random.Random(1101)
        for step in range(updates):
            G.STATE['step'] = step
            G._step_stage_b(model, optimizer, G.training_batch_stage_b(rng, visits, frozenset()),
                            step)
        check(f'{arm}: the frozen copy is bit-identical after {updates} updates',
              same_params(before, params_of(frozen), tol=0.)
              and C.fingerprint(frozen) == fingerprint)
        check(f'{arm}: the frozen copy received no gradient and stayed in eval mode',
              all(q.grad is None and not q.requires_grad for q in frozen.parameters())
              and not frozen.training)
        check(f'{arm}: the trainable model DID move',
              C.fingerprint(model) != fingerprint)


# ----------------------------------------------------------------- label-free invariance

def test_poison(visits=4, K=2):
    clean_a = stage_a(step=0, visits=visits, stage_a_extra=K)
    with Poison():
        dirty_a = stage_a(step=0, visits=visits, stage_a_extra=K)
    check('stage A: poisoned gold/supplied/answer/hops/relation leaves the batch identical',
          batch_a_equal(clean_a, dirty_a))
    a, b = fresh_model(), fresh_model()
    G.configure('a', seed=DEV_SEED, stage_a_extra=K)
    G._step_stage_a(a, T.optimizer_for(a), clean_a, 0)
    G._step_stage_a(b, T.optimizer_for(b), dirty_a, 0)
    check('stage A: poisoned annotations leave the loss and the update identical',
          same_params(params_of(a), params_of(b), tol=0.))

    clean_b = stage_b(visits=visits)
    with Poison():
        dirty_b = stage_b(visits=visits)
    check('stage B: poisoned gold leaves the batch identical, diagnostics included',
          batch_b_equal(clean_b, dirty_b))
    for arm in G.ARMS:
        c, d = fresh_model(), fresh_model()
        fc, fd = frozen_copy(c), frozen_copy(d)
        G.configure('b', seed=DEV_SEED, arm=arm, frozen=fc)
        G._step_stage_b(c, T.optimizer_for(c), clean_b, 0)
        G.STATE['frozen'] = fd
        G._step_stage_b(d, T.optimizer_for(d), dirty_b, 0)
        check(f'{arm}: poisoned annotations leave the loss and the update identical',
              same_params(params_of(c), params_of(d), tol=0.))

    # The diagnostics are evaluator-only: scrambling them must not move a single gradient.
    for arm in G.ARMS:
        batch = stage_b(visits=visits)
        model, frozen = fresh_model(), frozen_copy(fresh_model(DEV_SEED+1))
        w1, w2 = G.link_weights(batch)
        one, marg = G.stage_b_losses(model, batch, arm, frozen)
        (w1*one + w2*marg).backward()
        clean_grads, clean_loss = grads_of(model), (float(one), float(marg))
        truth = {k: v.clone() for k, v in batch.diagnostics.items()}
        batch.diagnostics['intermediate'] = torch.full_like(truth['intermediate'], ENTITY_MIN)
        batch.diagnostics['shares_answer'] = torch.zeros_like(truth['shares_answer'])
        other = fresh_model()
        one2, marg2 = G.stage_b_losses(other, batch, arm, frozen)
        (w1*one2 + w2*marg2).backward()
        check(f'{arm}: scrambled diagnostics change no loss and no gradient',
              same_grads(clean_grads, grads_of(other), tol=0.)
              and (float(one2), float(marg2)) == clean_loss,
              f'{int(truth["intermediate"].shape[0])} two-hop records')
        batch.diagnostics.update(truth)

    # ``present`` is NOT a diagnostic: frozen-terminal-6 reads it, and only that arm.
    batch = stage_b(visits=visits)
    model, frozen = fresh_model(), frozen_copy(fresh_model(DEV_SEED+1))
    scrambled = copy.deepcopy(batch)
    scrambled.present = torch.ones_like(batch.present)
    losses = {}
    for arm in G.ARMS:
        with torch.no_grad():
            losses[arm] = (float(G.stage_b_losses(model, batch, arm, frozen)[1]),
                           float(G.stage_b_losses(model, scrambled, arm, frozen)[1]))
    check('only frozen-terminal-6 reads the present mask in its loss',
          losses['shared'][0] == losses['shared'][1]
          and losses['frozen-terminal'][0] == losses['frozen-terminal'][1]
          and losses['frozen-terminal-6'][0] != losses['frozen-terminal-6'][1])

    # And the diagnostic intermediate really is the visit's visible LINK target.
    memory = batch.link.memory.tolist()
    wanted = []
    for owner, q in zip(batch.link.owner.tolist(), batch.link.questions.tolist()):
        wanted += [row[3] for row in memory[owner]
                   if len(row) >= 4 and row[0] == WORLD and row[1] == q[1] and row[2] == LINK]
    check('the logged intermediate is the visit\'s visible LINK target',
          wanted == batch.diagnostics['intermediate'].tolist(), f'{len(wanted)} records')


# ------------------------------------------------------------------------------- probes

def test_probe(n=32):
    six = G.build_probe('six', n, 6, 4, chunk_visits=4)
    sixteen = G.build_probe('sixteen', n, ENTITIES, 4, chunk_visits=4)
    check('the probe sets have exactly the requested size',
          six['n'] == n and sixteen['n'] == n and six['overlap_with_exclusion_set'] == 0)
    check('the probe is deterministic for a given label/size',
          torch.equal(G.build_probe('six', n, 6, 4, chunk_visits=4)['chunks'][0].intermediate,
                      six['chunks'][0].intermediate))
    check('the six-person probe has six present people, the sixteen-person probe sixteen',
          bool(six['chunks'][0].present.sum(1).eq(6).all())
          and bool(sixteen['chunks'][0].present.sum(1).eq(ENTITIES).all()))
    chunk = six['chunks'][0]
    check('every probe question is a fresh two-hop question over visible facts',
          chunk.monolithic.questions.shape[1] == 5
          and bool((chunk.monolithic.questions[:, 2] == LINK).all())
          and set(chunk.monolithic.questions[:, 3].tolist()) <= set(G.TWO_HOP_RELATIONS)
          and chunk.link.questions.shape[1] == 4
          and bool((chunk.link.questions[:, 2] == LINK).all()))
    paths = A.truth_paths(chunk.monolithic)
    check('the probe answers agree with the visible-fact interpreter',
          [p[-1]['target'] for p in paths] == chunk.answers.tolist()
          and [p[0]['target'] for p in paths] == chunk.intermediate.tolist(),
          f'{len(paths)} probe questions')
    check('relation 10 is never a probe terminal',
          not bool((chunk.terminal.questions[:, 2] == 10).any()))
    check('the probe one-hop questions cover all three attribute relations',
          set(chunk.one_hop.questions[:, 2].tolist()) == set(G.ATTRIBUTE_RELATIONS))

    model = fresh_model()
    frozen = frozen_copy(fresh_model(DEV_SEED+1))
    row = G.probe_diagnostics(model, six, frozen)
    for key in ('link_accuracy', 'p_link_true', 'p_link_wrong_present', 'p_link_absent',
                'p_link_non_entity', 'terminal_p_true_person', 'terminal_p_wrong_present',
                'terminal_margin', 'shared_answer_rate', 'one_hop_accuracy_r8',
                'one_hop_accuracy_r9', 'one_hop_accuracy_r10', 'execution'):
        check(f'the probe reports {key}', key in row)
    mass = sum(row[k] for k in ('p_link_true', 'p_link_wrong_present', 'p_link_absent',
                                'p_link_non_entity'))
    check('the four p_link masses partition the LINK softmax',
          abs(mass - 1.) < 2e-3, f'sum {mass:.6f}')
    ex = row['execution']
    check('the execution split accounts for every probe question',
          ex['via_right_person'] + ex['via_wrong_person'] == ex['answer_correct']
          and ex['answer_correct'] + ex['wrong_answer'] + ex['aborted'] == ex['n'] == n,
          json.dumps(ex))
    check('the sixteen-person probe has no absent identity to put mass on',
          G.probe_diagnostics(model, sixteen, frozen)['p_link_absent'] == 0.)

    # The probe never touches a loss: every model parameter is untouched by a probe pass.
    before = params_of(model)
    G.probe_diagnostics(model, six, frozen)
    check('a probe pass changes no parameter and leaves no gradient',
          same_params(before, params_of(model), tol=0.)
          and all(q.grad is None for q in model.parameters()))


# ---------------------------------------------------------------------------------- model

def test_model():
    model = A.new_model(DEV_SEED)
    check('parameter count is 79,316', model.parameters_count() == G.PARAMETERS == 79316,
          str(model.parameters_count()))
    reference = T.TokenMemoryReasoner()
    keys = sorted(reference.state_dict())
    check('state-dict schema unchanged', sorted(model.state_dict()) == keys, f'{len(keys)} tensors')
    check('state-dict shapes unchanged',
          all(model.state_dict()[k].shape == reference.state_dict()[k].shape for k in keys))
    hooks = (A.training_batch, A.training_step, A.training_flops)
    for stage in G.STAGES:
        G.configure(stage, seed=DEV_SEED)
        fresh = A.new_model(DEV_SEED)
        check(f'stage {stage} leaves the model untouched',
              fresh.parameters_count() == 79316 and sorted(fresh.state_dict()) == keys)
    check('this module does NOT monkeypatch the registered runner',
          (A.training_batch, A.training_step, A.training_flops) == hooks
          and A.training_batch is not G.training_batch_stage_a
          and A.training_batch is not G.training_batch_stage_b,
          'configure() touches only R.OUT and this module\'s own STATE')
    check('the output root follows the registered naming',
          G.NAME == 'fable-link-isolation-20260920'
          and G.stage_folder('b', 'shared', 3).name == 'seed-3')


# ---------------------------------------------------------------------------------- smoke

def run(root, *args):
    env = dict(os.environ, FABLE_LINK_ISOLATION_OUT=str(root), OMP_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([R.PYTHON, '-B', str(Path(G.__file__).resolve()), *args],
                          env=env, capture_output=True, text=True, timeout=1800)


def test_smoke(updates, seed):
    assert seed >= 995000, seed
    root = Path(tempfile.mkdtemp(prefix='fable-link-isolation-smoke-'))
    try:
        started = time.monotonic()
        out = run(root, 'freeze', '--stage-a-updates', str(updates),
                  '--stage-b-updates', str(updates), '--stage-a-seconds', '600',
                  '--stage-b-seconds', '600', '--grow-g1', str(max(1, updates//3)),
                  '--grow-g2', str(max(2, 2*updates//3)), '--probe-six', '8',
                  '--probe-sixteen', '8', '--probe-per-visit', '4')
        check('freeze writes a manifest', out.returncode == 0
              and (root/'astra_canonical_operator_launch.json').exists(),
              (out.stdout or out.stderr).strip().splitlines()[-1][:120])
        manifest = json.loads((root/'astra_canonical_operator_launch.json').read_text())
        check('freeze hashes this module, both wrappers and the preregistration',
              any(k.endswith('fable_link_isolation.py') for k in manifest['files'])
              and any(k.endswith('fable_operator_startup.py') for k in manifest['files'])
              and any(k.endswith('fable_operator_variants.py') for k in manifest['files'])
              and any(k.endswith('PREREGISTRATION.md') for k in manifest['files']),
              f'{len(manifest["files"])} files frozen')

        out = run(root, 'wave', '--stage', 'a', '--seeds', str(seed), '--name', 'smoke')
        check('wave (stage a) completes', out.returncode == 0
              and json.loads(out.stdout.strip().splitlines()[-1])['complete'],
              (out.stdout.strip().splitlines() or [out.stderr[-200:]])[-1][:160])
        saved = P.load(root/f'stage-a/seed-{seed}/stage_a.pt')
        check('stage_a.pt carries the model, the optimizer and every RNG state',
              set(saved) >= {'state_dict', 'optimizer', 'torch_rng', 'world_rng', 'vrng', 'xrng'}
              and saved['updates'] == updates)

        for arm in G.ARMS:
            out = run(root, 'wave', '--stage', 'b', '--arm', arm, '--seeds', str(seed),
                      '--name', 'smoke')
            check(f'wave (stage b, {arm}) completes', out.returncode == 0
                  and json.loads(out.stdout.strip().splitlines()[-1])['complete'],
                  (out.stdout.strip().splitlines() or [out.stderr[-200:]])[-1][:160])
            blob = json.loads((root/f'stage-b/{arm}/seed-{seed}/final_probe.json').read_text())
            check(f'{arm}: the frozen copy is unchanged at the end of the run',
                  blob['frozen_unchanged'] and blob['frozen_fingerprint'] == blob['stage_a_fingerprint'])
            lines = [json.loads(line) for line in
                     (root/f'stage-b/{arm}/seed-{seed}/diagnostics.jsonl').read_text().splitlines()]
            check(f'{arm}: diagnostics land in the jsonl, probe first and last',
                  lines[0]['kind'] == 'probe' and lines[-1]['kind'] == 'probe'
                  and sum(1 for line in lines if line['kind'] == 'train') == updates//G.LOG_EVERY_B
                  if updates >= G.LOG_EVERY_B else lines[0]['kind'] == 'probe',
                  f'{len(lines)} lines')

        # Both arms started from the same stage-A weights; only `shared` moves the terminal.
        blobs = {arm: json.loads((root/f'stage-b/{arm}/seed-{seed}/final_probe.json').read_text())
                 for arm in G.ARMS}
        check('every arm started from the same stage-A checkpoint',
              len({b['stage_a_fingerprint'] for b in blobs.values()}) == 1)
        check('the arms ended at different weights',
              len({b['final_fingerprint'] for b in blobs.values()}) == len(G.ARMS))

        out = run(root, 'report', '--seeds', str(seed))
        check('report prints a per-seed, per-arm table',
              out.returncode == 0 and 'LINK acc' in out.stdout
              and all(arm in out.stdout for arm in G.ARMS) and 'pass mark' in out.stdout,
              f'{len(out.stdout.splitlines())} lines, {time.monotonic()-started:.0f}s total')

        # The manifest really is enforced.
        (root/'astra_canonical_operator_launch.json').write_text(
            json.dumps(dict(manifest, files=dict(manifest['files'], **{'run.py': '0'*64}))))
        out = run(root, 'wave', '--stage', 'a', '--seeds', str(seed), '--name', 'smoke-2')
        check('a changed registered file stops the wave',
              out.returncode != 0 and 'registered file changed' in (out.stdout + out.stderr))
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ----------------------------------------------------------------------------------- main

GROUPS = dict(stagea=test_stagea, arms=test_arms, loss=test_loss, frozen=test_frozen,
              poison=test_poison, probe=test_probe, model=test_model)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', default=None, choices=list(GROUPS) + ['smoke'])
    ap.add_argument('--smoke-updates', type=int, default=10)
    ap.add_argument('--smoke-seed', type=int, default=995011)
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
