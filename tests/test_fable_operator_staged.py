"""Checks for scripts/fable_operator_staged.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_operator_staged.py
Run a group: python3.12 -B tests/test_fable_operator_staged.py --only loss
Groups: identity, loss, dense, poison, flops, model, smoke.

``smoke`` trains <= 30 updates on non-registered seeds >= 993500 against a freshly
generated throwaway panel; it never touches a registered panel and never trains a
registered seed. Nothing here writes into the BASE checkout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts')):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_operator_staged as G                                     # noqa: E402
import fable_operator_startup as S                                    # noqa: E402
import fable_operator_variants as V                                   # noqa: E402

A, E, T, data, torch, P, C, R = G.A, G.E, G.T, G.data, G.torch, G.P, G.C, G.R
F = G.F
LINK, QUESTION, ANSWER, WORLD = G.LINK, G.QUESTION, G.ANSWER, G.WORLD
ENTITY_MIN, ENTITY_MAX, ENTITIES = G.ENTITY_MIN, G.ENTITY_MAX, G.ENTITIES
SMOKE_SEED = 993501
M = 2500                       # the registered default --marg-start
CURRICULUM = dict(grow_g1=1500, grow_g2=3000, blind_lines=16)
CHECKS = 0


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def fresh_model(seed=SMOKE_SEED):
    return A.new_model(seed)


def params_of(model):
    return [p.detach().clone() for p in model.parameters()]


def same_params(a, b, tol=0.):
    return all(bool((x - y).abs().max() <= tol) for x, y in zip(a, b))


def grads_of(model):
    return [None if p.grad is None else p.grad.detach().clone() for p in model.parameters()]


def same_grads(a, b, tol=0.):
    return all((x is None and y is None) or bool((x - y).abs().max() <= tol)
               for x, y in zip(a, b))


# ------------------------------------------------------------------------------- builders

def staged(variant, step, seed=SMOKE_SEED, rng=None, visits=16, **params):
    """One staged batch at ``step``, from a freshly seeded variant."""
    G.configure_variant(variant, seed=seed, **dict(CURRICULUM, **params))
    G.STATE['step'] = step
    return G.training_batch_staged(rng or random.Random(1101), visits, frozenset())


def margfull(step, seed=SMOKE_SEED, rng=None, visits=16, **params):
    """One ``marg-full --startup grow-blind`` batch at ``step``, same seeding."""
    S.configure_variant('marg-full', seed=seed, startup='grow-blind',
                        **dict(CURRICULUM, **params))
    S.STATE['step'] = step
    return S.training_batch_margfull(rng or random.Random(1101), visits, frozenset())


def inputs_equal(x, y):
    return (torch.equal(x.memory, y.memory) and torch.equal(x.questions, y.questions)
            and torch.equal(x.owner, y.owner) and torch.equal(x.eligible, y.eligible))


def groups_equal(a, b, extra=0, per_visit=2):
    """Every group equal; for ``extra`` > 0 only the GENERATOR one-hop records are compared.

    The extra records of ``marg-staged-dense`` are appended after each visit's two generator
    one-hop records, so rows with ``i % (per_visit + extra) < per_visit`` are the generator's.
    """
    if not (inputs_equal(a.link, b.link) and inputs_equal(a.terminal, b.terminal)
            and inputs_equal(a.monolithic, b.monolithic)
            and torch.equal(a.terminal_index, b.terminal_index)
            and torch.equal(a.two_hop_answers, b.two_hop_answers)
            and torch.equal(a.monolithic_answers, b.monolithic_answers)):
        return False
    if not extra:
        return (inputs_equal(a.one_hop, b.one_hop)
                and torch.equal(a.one_hop_targets.answer, b.one_hop_targets.answer))
    rows = [i for i in range(a.one_hop.questions.shape[0]) if i % (per_visit+extra) < per_visit]
    return (torch.equal(a.one_hop.memory, b.one_hop.memory)
            and torch.equal(a.one_hop.questions[rows], b.one_hop.questions)
            and torch.equal(a.one_hop.owner[rows], b.one_hop.owner)
            and torch.equal(a.one_hop.eligible[rows], b.one_hop.eligible)
            and torch.equal(a.one_hop_targets.answer[rows], b.one_hop_targets.answer))


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


# -------------------------------------------------------------- identity with marg-full

def test_identity(batches=20, visits=16):
    """The curriculum, the world stream and every record must match marg-full batch for batch."""
    for variant, extra in (('marg-staged', 0), ('marg-staged-dense', 4)):
        G.configure_variant(variant, seed=SMOKE_SEED, extra_onehop=extra, **CURRICULUM)
        S.configure_variant('marg-full', seed=SMOKE_SEED, startup='grow-blind', **CURRICULUM)
        ours, theirs = random.Random(1101), random.Random(1101)
        agree = True
        for step in range(batches):
            G.STATE['step'] = step
            S.STATE['step'] = step
            a = G.training_batch_staged(ours, visits, frozenset())
            b = S.training_batch_margfull(theirs, visits, frozenset())
            if not groups_equal(a, b, extra=extra):
                agree = False
                break
        check(f'{variant}: first {batches} batches identical to marg-full --startup grow-blind',
              agree, f'{batches} batches x {visits} visits, extra_onehop={extra}')
        check(f'{variant}: world RNG stream identical to marg-full',
              ours.getstate() == theirs.getstate())

    # The curriculum RNG namespace is marg-full's on purpose.
    check('curriculum RNG namespace is marg-full\'s',
          G.CURRICULUM_NAMESPACE == 'fable-startup-marg-full'
          and G.EXTRA_NAMESPACE == 'fable-staged-extra')
    G.configure_variant('marg-staged-dense', seed=7, **CURRICULUM)
    S.configure_variant('marg-full', seed=7, startup='grow-blind', **CURRICULUM)
    check('curriculum RNG state matches marg-full at the same seed',
          G.STATE['vrng'].getstate() == S.STATE['vrng'].getstate())
    check('the extra records draw from a SEPARATE stream',
          G.STATE['xrng'].getstate() != G.STATE['vrng'].getstate())

    # marg-staged forces K = 0 whatever is passed, so the two arms differ by exactly one thing.
    check('marg-staged forces extra_onehop to 0',
          G.normalize_params('marg-staged', dict(extra_onehop=4))['extra_onehop'] == 0
          and G.normalize_params('marg-staged-dense', dict(extra_onehop=4))['extra_onehop'] == 4)
    check('both variants are pinned to the grow-blind curriculum',
          all(G.normalize_params(v, {})['startup'] == 'grow-blind' for v in G.VARIANTS))


# ------------------------------------------------------------------------------- the loss

def test_loss(visits=4):
    model_ref = fresh_model()

    # ---- before M: marg-full's loss with the marginal term removed (w1, w3 unchanged).
    pre = staged('marg-staged', step=M-1, visits=visits, marg_start=M)
    mf = margfull(step=M-1, visits=visits)
    check('pre-M staged batch equals the marg-full batch', groups_equal(pre, mf))
    check('pre-M plan says the marginal is off and only two groups are forwarded',
          pre.plan['marginal'] is False
          and pre.accounting['forwards']['groups'] == ['one_hop', 'monolithic'])

    with torch.no_grad():
        one_s, marg_s, mono_s = G.staged_losses(model_ref, pre)
        one_m, marg_m, mono_m = S.margfull_losses(model_ref, mf)
    check('pre-M never computes the marginal term', marg_s is None)
    w1, w2, w3 = S.marg_weights(mf)
    check('pre-M record weights are marg-full\'s, not renormalised',
          (w1, w2, w3) == S.marg_weights(pre) == (1/3, 1/3, 1/3),
          f'({w1:.4f}, {w2:.4f}, {w3:.4f})')
    got = float(w1*one_s + w3*mono_s)
    want = float(w1*one_m + w3*mono_m)
    check('pre-M loss == marg-full loss with the marginal term removed',
          abs(got - want) < 1e-6, f'{got:.8f} vs {want:.8f}, |diff| {abs(got-want):.3e}')
    check('the marginal term is what was dropped', abs(float(w2*marg_m)) > 1e-3,
          f'dropped term {float(w2*marg_m):.6f}')

    # ---- from M: byte-for-byte marg-full's loss and marg-full's update.
    post = staged('marg-staged', step=M, visits=visits, marg_start=M)
    mf_post = margfull(step=M, visits=visits)
    check('post-M staged batch equals the marg-full batch', groups_equal(post, mf_post))
    check('post-M plan forwards all four groups in marg-full\'s order',
          post.plan['marginal'] is True
          and post.accounting['forwards']['groups'] == ['one_hop', 'link', 'terminal', 'monolithic'])
    with torch.no_grad():
        ls = G.staged_losses(model_ref, post)
        lm = S.margfull_losses(model_ref, mf_post)
    check('post-M losses equal marg-full\'s exactly',
          all(float(x) == float(y) for x, y in zip(ls, lm)),
          ', '.join(f'{float(x):.8f}' for x in ls))

    a, b = fresh_model(), fresh_model()
    G.configure_variant('marg-staged', seed=SMOKE_SEED, marg_start=M, **CURRICULUM)
    G.STATE['step'] = M
    G._step_staged(a, T.optimizer_for(a), post, M)
    S._step_margfull(b, T.optimizer_for(b), mf_post, M)
    check('post-M update is marg-full\'s update, parameter for parameter',
          same_params(params_of(a), params_of(b), tol=0.))

    c, d = fresh_model(), fresh_model()
    G.configure_variant('marg-staged', seed=SMOKE_SEED, marg_start=M, **CURRICULUM)
    G.STATE['step'] = M-1
    G._step_staged(c, T.optimizer_for(c), pre, M-1)
    S._step_margfull(d, T.optimizer_for(d), mf, M-1)
    check('the switch is hard: the pre-M update really differs from marg-full\'s',
          not same_params(params_of(c), params_of(d), tol=1e-9))

    # ---- gradients before M reach the one-hop and monolithic paths only.
    g = fresh_model()
    one, marg, mono = G.staged_losses(g, pre)
    (w1*one + w3*mono).backward()
    check('pre-M gradient reaches the embedding', float(g.embedding.weight.grad.abs().max()) > 0)
    h = fresh_model()
    link_logits, terminal_logits = h(post.link), h(post.terminal)
    link_logits.retain_grad(); terminal_logits.retain_grad()
    (-S.marginal_probability(h, post, link_logits,
                             terminal_logits).clamp_min(1e-12).log().mean()).backward()
    check('post-M gradient reaches both the LINK and the terminal calls',
          float(link_logits.grad.abs().max()) > 0 and float(terminal_logits.grad.abs().max()) > 0)

    # ---- the exact switch point.
    check('marginal is off at M-1 and on at M',
          staged('marg-staged', step=M-1, visits=2, marg_start=M).plan['marginal'] is False
          and staged('marg-staged', step=M, visits=2, marg_start=M).plan['marginal'] is True)
    check('--marg-start 0 reproduces marg-full from update 0',
          staged('marg-staged', step=0, visits=2, marg_start=0).plan['marginal'] is True)


# -------------------------------------------------------------------- the extra records

def test_dense(visits=8, K=4):
    batch = staged('marg-staged-dense', step=0, visits=visits, extra_onehop=K, marg_start=M)

    check('dense adds exactly K extra one-hop records per visit',
          batch.accounting['blind']['extra_one_hop'] == K*visits
          and batch.accounting['kinds']['one_hop'] == (2+K)*visits,
          f'{batch.accounting["kinds"]["one_hop"]} one-hop records, {visits} visits, K={K}')
    check('dense reaches grow-blind\'s 6 single-call attribute records per visit',
          batch.accounting['kinds']['one_hop']//visits == 6)

    q = batch.one_hop.questions
    check('no constructed one-hop record is ever a LINK call',
          not bool((q[:, 2] == LINK).any()) and q.shape[1] == 4,
          f'relations {sorted(set(q[:, 2].tolist()))}')
    check('every one-hop relation is an attribute relation',
          set(q[:, 2].tolist()) <= set(G.ATTRIBUTE_RELATIONS))
    check('no LINK question appears anywhere outside the marginalised LINK group',
          not bool((batch.monolithic.questions[:, 3] == LINK).any()))

    paths = A.truth_paths(batch.one_hop)
    check('every one-hop record is answerable from its KEPT ELIGIBLE lines',
          [p[-1]['target'] for p in paths] == batch.one_hop_targets.answer.tolist()
          and all(len(p) == 1 for p in paths),
          f'{len(paths)} records, all single-call')
    check('the extra records\' supporting lines are kept visible fact rows',
          all(batch.one_hop.memory[owner][line].tolist()[:4]
              == [WORLD, int(qq[1]), int(qq[2]), int(ans)]
              for owner, line, qq, ans in zip(batch.one_hop.owner.tolist(),
                                              batch.one_hop_targets.lines[:, 0].tolist(),
                                              q, batch.one_hop_targets.answer.tolist())))

    # Relation uniform over (8, 9, 10) for the extras: all three must show up.
    rows = [i for i in range(q.shape[0]) if i % (2+K) >= 2]
    check('extra records draw all three attribute relations',
          set(q[rows][:, 2].tolist()) == {8, 9, 10},
          f'{len(rows)} extra records, relations {sorted(set(q[rows][:, 2].tolist()))}')

    # K = 0 on the dense arm reproduces marg-staged exactly.
    zero = staged('marg-staged-dense', step=0, visits=visits, extra_onehop=0, marg_start=M)
    plain = staged('marg-staged', step=0, visits=visits, marg_start=M)
    check('dense with K = 0 reproduces marg-staged exactly', groups_equal(zero, plain))

    w = S.marg_weights(batch)
    check('equal weight per record gives (2+K, 2, 2)/(6+K)',
          all(abs(a - b) < 1e-12 for a, b in zip(w, ((2+K)/(6+K), 2/(6+K), 2/(6+K)))),
          f'({w[0]:.4f}, {w[1]:.4f}, {w[2]:.4f})')

    # The extras exist before AND after M.
    late = staged('marg-staged-dense', step=M, visits=2, extra_onehop=K, marg_start=M)
    check('the extra records are present after M too',
          late.accounting['blind']['extra_one_hop'] == K*2 and late.plan['marginal'] is True)


# ----------------------------------------------------------------- label-free invariance

def test_poison(visits=4, K=4):
    for variant, extra, step in (('marg-staged', 0, M-1), ('marg-staged', 0, M),
                                 ('marg-staged-dense', K, M-1), ('marg-staged-dense', K, M)):
        clean = staged(variant, step=step, visits=visits, extra_onehop=extra, marg_start=M)
        with Poison():
            dirty = staged(variant, step=step, visits=visits, extra_onehop=extra, marg_start=M)
        check(f'{variant} @ step {step}: poisoned gold leaves the batch identical',
              groups_equal(clean, dirty)
              and clean.accounting['blind'] == dirty.accounting['blind']
              and torch.equal(clean.diagnostics['intermediate'], dirty.diagnostics['intermediate']))

        a, b = fresh_model(), fresh_model()
        G.configure_variant(variant, seed=SMOKE_SEED, extra_onehop=extra,
                            marg_start=M, **CURRICULUM)
        G.STATE['step'] = step
        G._step_staged(a, T.optimizer_for(a), clean, step)
        G.STATE['step'] = step
        G._step_staged(b, T.optimizer_for(b), dirty, step)
        check(f'{variant} @ step {step}: poisoned gold leaves losses and the update identical',
              same_params(params_of(a), params_of(b), tol=0.))

    # The diagnostics are evaluator-only: scrambling them must not move a single gradient.
    for step in (M-1, M):
        batch = staged('marg-staged-dense', step=step, visits=visits,
                       extra_onehop=K, marg_start=M)
        model = fresh_model()
        one, marg, mono = G.staged_losses(model, batch)
        w1, w2, w3 = S.marg_weights(batch)
        (w1*one + w3*mono if marg is None else w1*one + w2*marg + w3*mono).backward()
        clean_grads, clean_loss = grads_of(model), float(one.detach())
        truth = batch.diagnostics['intermediate'].clone()
        batch.diagnostics['intermediate'] = torch.full_like(truth, ENTITY_MIN)
        model2 = fresh_model()
        one2, marg2, mono2 = G.staged_losses(model2, batch)
        (w1*one2 + w3*mono2 if marg2 is None else w1*one2 + w2*marg2 + w3*mono2).backward()
        check(f'scrambled diagnostics change no loss and no gradient @ step {step}',
              same_grads(clean_grads, grads_of(model2), tol=0.)
              and float(one2.detach()) == clean_loss
              and (marg is None) == (marg2 is None), f'{int(truth.shape[0])} two-hop records')
        batch.diagnostics['intermediate'] = truth

    # And the diagnostic intermediate really is the true one, read off the visible LINK row.
    batch = staged('marg-staged', step=M, visits=visits, marg_start=M)
    memory = batch.link.memory.tolist()
    wanted = []
    for owner, q in zip(batch.link.owner.tolist(), batch.link.questions.tolist()):
        wanted += [row[3] for row in memory[owner]
                   if len(row) >= 4 and row[0] == WORLD and row[1] == q[1] and row[2] == LINK]
    check('the logged intermediate is the visit\'s visible LINK target',
          wanted == batch.diagnostics['intermediate'].tolist(), f'{len(wanted)} records')

    probe = G._probe(fresh_model(), batch)
    check('the probe reports one-hop, marginal, LINK and terminal-given-true',
          set(probe) == {'one_hop_acc', 'monolithic_acc', 'mean_marginal_probability',
                         'link_argmax_acc', 'terminal_given_true_acc'}, json.dumps(probe))


# ------------------------------------------------------------------------ honest FLOPs

def test_flops(visits=4):
    model = fresh_model()
    pre = staged('marg-staged', step=M-1, visits=visits, marg_start=M)
    post = staged('marg-staged', step=M, visits=visits, marg_start=M)
    mf_post = margfull(step=M, visits=visits)
    a, b = G.training_flops_staged(pre, model), G.training_flops_staged(post, model)
    check('post-M FLOPs equal marg-full\'s FLOPs on the same batch',
          b == S.training_flops_margfull(mf_post, model), f'{b:,} FLOPs')
    check('pre-M FLOPs are strictly smaller (the 16-way expansion is not forwarded)',
          a < b, f'{a:,} vs {b:,} FLOPs ({a/b:.3f}x)')

    sep_pre = staged('marg-staged', step=M-1, visits=visits, marg_start=M, single_forward=False)
    sep_post = staged('marg-staged', step=M, visits=visits, marg_start=M, single_forward=False)
    check('without --single-forward, pre-M charges exactly one_hop + monolithic',
          G.training_flops_staged(sep_pre, model)
          == T.training_flops(sep_pre.one_hop, model) + T.training_flops(sep_pre.monolithic, model))
    check('without --single-forward, post-M charges all four groups',
          G.training_flops_staged(sep_post, model)
          == sum(T.training_flops(x, model) for x in (sep_post.one_hop, sep_post.link,
                                                      sep_post.terminal, sep_post.monolithic)))
    check('the 16-way expansion is charged in full after M',
          post.accounting['terminal_calls'] > 0
          and post.accounting['terminal_calls_undeduped']
          == ENTITIES*post.accounting['kinds']['marginalised_two_hop'])
    check('terminal dedupe accounting closes',
          post.accounting['terminal_calls'] + post.accounting['blind']['deduped_terminal_calls']
          == post.accounting['terminal_calls_undeduped'])


# ---------------------------------------------------------------------------------- model

def test_model():
    model = A.new_model(SMOKE_SEED)
    check('parameter count is 79,316', model.parameters_count() == 79316,
          str(model.parameters_count()))
    reference = T.TokenMemoryReasoner()
    keys = sorted(reference.state_dict())
    check('state-dict schema unchanged', sorted(model.state_dict()) == keys, f'{len(keys)} tensors')
    check('state-dict shapes unchanged',
          all(model.state_dict()[k].shape == reference.state_dict()[k].shape for k in keys))
    for variant in G.VARIANTS:
        G.configure_variant(variant, seed=SMOKE_SEED, **CURRICULUM)
        fresh = A.new_model(SMOKE_SEED)
        check(f'{variant} leaves the model untouched',
              fresh.parameters_count() == 79316 and sorted(fresh.state_dict()) == keys)
    check('configure_variant wires the runner to this module',
          A.training_batch is G.training_batch_staged and A.training_flops is G.training_flops_staged)
    check('output roots follow the registered naming',
          [str(G.out_for(v).name) for v in G.VARIANTS]
          == ['fable-operator-marg-staged-20260920', 'fable-operator-marg-staged-dense-20260920'])


# ---------------------------------------------------------------------------------- smoke

def smoke_worker(variant, updates, n, root, seed, **params):
    """<= 30-update worker run against a throwaway manifest and a freshly made tiny panel."""
    out = root/f'fable-operator-{variant}-20260920'
    out.mkdir(parents=True, exist_ok=False)
    panel = P.generate('c1_own_one_hop', n=n, namespace=f'fable-staged-smoke:{variant}')
    panel_path = out/'smoke-panel.pt'
    torch.save(panel, panel_path)
    forbidden = out/'smoke-forbidden.json'
    forbidden.write_text('[]')
    here = Path(G.__file__).resolve()
    manifest = dict(variant=variant, startup=dict(params), smoke=True,
                    schedule=dict(updates=updates, training_seconds=900, work_seconds=1200,
                                  terminate_seconds=1230, visits_per_update=16),
                    exclusion_path=str(forbidden),
                    panels={'smoke': dict(path=str(panel_path), sha256=C.sha(panel_path),
                                          cutoff=0, n=n)},
                    files={str(here): C.sha(here)})
    (out/'astra_canonical_operator_launch.json').write_text(json.dumps(manifest))
    G.configure_variant(variant, seed=seed, **params)
    R.OUT = out
    started = time.monotonic()
    R.worker(seed, time.monotonic())
    completion = json.loads((out/f'astra_canonical_operator_seed-{seed}/completion.json').read_text())
    return completion, time.monotonic()-started


def test_smoke(updates, n):
    root = Path(tempfile.mkdtemp(prefix='fable-staged-smoke-'))
    try:
        assert updates <= 30, 'the smoke must never train more than 30 updates'
        # The switch must fire inside the smoke, so both loss regimes are exercised.
        base = dict(grow_g1=max(1, updates//3), grow_g2=max(2, 2*updates//3),
                    blind_lines=16, marg_start=max(1, updates//2))
        for i, (variant, params) in enumerate((('marg-staged', dict(base)),
                                               ('marg-staged-dense', dict(base, extra_onehop=4)))):
            seed = 993500 + 10 + i
            assert seed >= 993500, seed
            completion, seconds = smoke_worker(variant, updates, n, root, seed, **params)
            check(f'{variant} worker smoke completes',
                  completion['complete'] and completion['updates'] == updates,
                  f'{updates} updates (switch at {params["marg_start"]}), '
                  f'R={completion["results"]["smoke"]["R"]}/{n}, {seconds:.1f}s, seed {seed}')
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ----------------------------------------------------------------------------------- main

GROUPS = dict(identity=test_identity, loss=test_loss, dense=test_dense,
              poison=test_poison, flops=test_flops, model=test_model)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', default=None, choices=list(GROUPS) + ['smoke'])
    ap.add_argument('--smoke-updates', type=int, default=10)
    ap.add_argument('--smoke-panel', type=int, default=32)
    args = ap.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    data.bootstrap()
    if args.only == 'smoke':
        test_smoke(args.smoke_updates, args.smoke_panel)
    elif args.only:
        GROUPS[args.only]()
    else:
        for fn in GROUPS.values():
            fn()
        test_smoke(args.smoke_updates, args.smoke_panel)
    print(f'ALL {CHECKS} CHECKS PASSED')
