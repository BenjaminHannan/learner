"""Checks for scripts/fable_operator_startup.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_operator_startup.py
Run a group: python3.12 -B tests/test_fable_operator_startup.py --only hintwarm
Groups: hintwarm, grow, blind, margfull, model, smoke (smoke trains <= 30 updates on
non-registered seeds >= 993400 and scores a freshly generated throwaway panel; it never
touches the registered panels and never trains a registered seed).
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

import fable_operator_startup as S                                    # noqa: E402
import fable_operator_variants as V                                   # noqa: E402

A, E, T, data, torch, P, C, R = S.A, S.E, S.T, S.data, S.torch, S.P, S.C, S.R
F = S.F
LINK, QUESTION, ANSWER, WORLD = S.LINK, S.QUESTION, S.ANSWER, S.WORLD
ENTITY_MIN, ENTITY_MAX, ENTITIES = S.ENTITY_MIN, S.ENTITY_MAX, S.ENTITIES
SMOKE_SEED = 993401
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


def build(variant, step=0, seed=SMOKE_SEED, rng=None, visits=16, **params):
    S.configure_variant(variant, seed=seed, **params)
    S.STATE['step'] = step
    return S.A.training_batch(rng or random.Random(1101), visits, frozenset())


# --------------------------------------------------------------------------- poisoned gold

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


def inputs_equal(x, y):
    return (torch.equal(x.memory, y.memory) and torch.equal(x.questions, y.questions)
            and torch.equal(x.owner, y.owner) and torch.equal(x.eligible, y.eligible))


def batch_equal(a, b):
    if isinstance(a, S.StartupMargBatch):
        return (inputs_equal(a.one_hop, b.one_hop) and inputs_equal(a.link, b.link)
                and inputs_equal(a.terminal, b.terminal) and inputs_equal(a.monolithic, b.monolithic)
                and torch.equal(a.terminal_index, b.terminal_index)
                and torch.equal(a.two_hop_answers, b.two_hop_answers)
                and torch.equal(a.monolithic_answers, b.monolithic_answers)
                and torch.equal(a.one_hop_targets.answer, b.one_hop_targets.answer))
    return (inputs_equal(a.canonical, b.canonical) and inputs_equal(a.monolithic, b.monolithic)
            and torch.equal(a.canonical_targets.answer, b.canonical_targets.answer)
            and torch.equal(a.monolithic_targets.answer, b.monolithic_targets.answer))


# ------------------------------------------------------------------------------- hintwarm

def test_hintwarm():
    batch = build('hintwarm', step=0)
    # Before H the loss must be v3r's; V._step_balance is v3r's step verbatim.
    a, b = fresh_model(), fresh_model()
    V._step_balance(a, T.optimizer_for(a), batch, 0)
    S.configure_variant('hintwarm', seed=SMOKE_SEED, hint_updates=1000)
    S.STATE['step'] = 0
    S._step_hintwarm(b, T.optimizer_for(b), batch, 0)
    check('hintwarm before H == v3r loss', same_params(params_of(a), params_of(b)),
          'identical parameters after one update')

    c, d = fresh_model(), fresh_model()
    V._step_e0(c, T.optimizer_for(c), batch, 0)
    S.configure_variant('hintwarm', seed=SMOKE_SEED, hint_updates=0)
    S.STATE['step'] = 0
    S._step_hintwarm(d, T.optimizer_for(d), batch, 0)
    check('hintwarm from H == pure answer CE', same_params(params_of(c), params_of(d)),
          'identical parameters after one update')
    check('hintwarm switch is hard', not same_params(params_of(a), params_of(c)),
          'the two regimes really differ')

    # The base recipe is v3r's (generator one-hop) unless --balance is set.
    plain = build('hintwarm', step=0)
    balanced = build('hintwarm', step=0, balance=True)
    base = V.training_batch_e0(random.Random(1101), 16, frozenset())
    check('default base is v3r, not balance',
          batch_equal(plain, base) and not batch_equal(balanced, base),
          'balance is opt-in')


# ----------------------------------------------------------------------------------- grow

def test_grow():
    p = dict(grow_g1=1500, grow_g2=3000, distractors=2)

    # (1) world RNG stream untouched.
    rng_base = random.Random(1101)
    for _ in range(3):
        V.training_batch_e0(rng_base, 16, frozenset())
    S.configure_variant('grow', seed=SMOKE_SEED, **p)
    rng_grow = random.Random(1101)
    for step in range(3):
        S.STATE['step'] = step
        S.A.training_batch(rng_grow, 16, frozenset())
    check('grow leaves the world stream unchanged', rng_base.getstate() == rng_grow.getstate())

    # (2) at step < G1 only truth-chain and distractor FACT lines survive.
    batch = build('grow', step=0, **p)
    full = V.training_batch_e0(random.Random(1101), 16, frozenset())
    chains = {}
    for x, y in ((full.canonical, full.canonical_targets), (full.monolithic, full.monolithic_targets)):
        for owner, lines in zip(x.owner.tolist(), y.lines.tolist()):
            chains.setdefault(owner, set()).update(lines)
    kept_rows = [[r for r in rows if any(r)] for rows in batch.canonical.memory.tolist()]
    check('grow keeps only fact lines at fraction 0',
          all(S._is_fact(r) for rows in kept_rows for r in rows),
          f'{sum(len(r) for r in kept_rows)} kept rows, all facts')
    chain_rows = {owner: sorted(tuple(full.canonical.memory[owner][line].tolist())
                                for line in lines) for owner, lines in chains.items()}
    present = all(row in [tuple(r) + (0,)*(full.canonical.memory.shape[2]-len(r))
                          for r in kept_rows[owner]]
                  for owner, rows in chain_rows.items() for row in rows)
    check('grow keeps every truth-chain line', present)
    check('grow really shrinks the story',
          max(len(r) for r in kept_rows) < full.canonical.memory.shape[1],
          f'{[len(r) for r in kept_rows][:4]} kept vs {full.canonical.memory.shape[1]} lines')

    # (3) every record stays answerable from its reduced eligible memory.
    paths = A.truth_paths(batch.canonical)
    check('grow records answerable from kept eligible lines',
          [q[-1]['target'] for q in paths] == batch.canonical_targets.answer.tolist())
    mono_paths = A.truth_paths(batch.monolithic)
    check('grow monolithic records answerable',
          [q[-1]['target'] for q in mono_paths] == batch.monolithic_targets.answer.tolist())

    # (4) size schedule.
    sizes = []
    for step in (0, 1500, 2250, 2999, 3000):
        b = build('grow', step=step, **p)
        rows = [sum(1 for r in m if any(r)) for m in b.canonical.memory.tolist()]
        sizes.append(sum(rows)/len(rows))
    check('grow fraction schedule', S.grow_fraction(1499, 1500, 3000) == 0.
          and S.grow_fraction(2250, 1500, 3000) == .5 and S.grow_fraction(3000, 1500, 3000) == 1.)
    check('grow story size increases with the schedule',
          sizes[0] == sizes[1] < sizes[2] < sizes[3] <= sizes[4], str([round(s, 2) for s in sizes]))

    # (5) after G2 the batch is the un-reduced base batch, tensor for tensor.
    after = build('grow', step=3000, **p)
    base = V.training_batch_e0(random.Random(1101), 16, frozenset())
    check('grow equals the full story after G2', batch_equal(after, base))
    check('grow after G2 reports no reduction', after.accounting['curriculum']['reduced'] is False)

    # (6) eligibility is gathered, never recomputed.
    x = data.pack([[[3, 52, 8, 60], [3, 53, 8, 61], [], [3, 54, 8, 62]]],
                  [[4, 52, 8, 5], [4, 54, 8, 5]], [0, 0], [2, 4])
    reduced = S._reduce_inputs(x, [[0, 3]])
    expect = torch.tensor([[bool(x.eligible[0][0]), bool(x.eligible[0][3])],
                           [bool(x.eligible[1][0]), bool(x.eligible[1][3])]])
    check('reduced eligibility equals the original per kept line',
          torch.equal(reduced.eligible, expect), str(reduced.eligible.tolist()))
    check('reduced memory keeps exactly the kept rows',
          reduced.memory[0].tolist() == [[3, 52, 8, 60], [3, 54, 8, 62]])

    # (7) the honest part: grow DOES read gold for its curriculum.
    with Poison():
        try:
            poisoned = build('grow', step=0, **p)
            differs = not batch_equal(poisoned, batch)
        except Exception:
            differs = True
    check('grow is documented as label-informed (poisoned gold changes it)', differs,
          'grow uses row.gold for line selection; only grow-blind does not')


# ----------------------------------------------------------------------------- grow-blind

def test_blind():
    p = dict(grow_g1=1500, grow_g2=3000, blind_lines=16)
    clean = build('grow-blind', step=0, **p)
    with Poison():
        poisoned = build('grow-blind', step=0, **p)
    check('grow-blind never consults row.gold/supplied/answer/hops/relation',
          batch_equal(poisoned, clean) and
          poisoned.accounting['blind'] == clean.accounting['blind'],
          'poisoned-gold batch is identical')

    paths = A.truth_paths(clean.canonical)
    check('grow-blind canonical questions answerable from kept eligible lines',
          [q[-1]['target'] for q in paths] == clean.canonical_targets.answer.tolist(),
          f'{len(paths)} records')
    mono = A.truth_paths(clean.monolithic)
    check('grow-blind monolithic questions answerable from kept eligible lines',
          [q[-1]['target'] for q in mono] == clean.monolithic_targets.answer.tolist())

    rows = [[r for r in m if any(r)] for m in clean.canonical.memory.tolist()]
    check('grow-blind keeps only fact lines at fraction 0',
          all(S._is_fact(r) for m in rows for r in m))
    check('grow-blind kept-fact counts follow --blind-lines',
          all(len(m) == 16 for m in rows), str(sorted({len(m) for m in rows})))

    two_hop = clean.monolithic.questions
    check('grow-blind two-hop relations stay in {8, 9}',
          set(two_hop[two_hop[:, 2] == LINK][:, 3].tolist()) <= {8, 9})

    rng_base = random.Random(1101)
    for _ in range(3):
        V.training_batch_e0(rng_base, 16, frozenset())
    S.configure_variant('grow-blind', seed=SMOKE_SEED, **p)
    rng_blind = random.Random(1101)
    for step in range(3):
        S.STATE['step'] = step
        S.A.training_batch(rng_blind, 16, frozenset())
    check('grow-blind leaves the world stream unchanged',
          rng_base.getstate() == rng_blind.getstate())

    grown = build('grow-blind', step=3000, **p)
    grown_rows = [sum(1 for r in m if any(r)) for m in grown.canonical.memory.tolist()]
    full = V.training_batch_e0(random.Random(1101), 16, frozenset())
    check('grow-blind reaches the full story after G2',
          grown_rows == [sum(1 for r in m if any(r)) for m in full.canonical.memory.tolist()],
          f'{grown_rows[:4]} lines per visit')

    relations = clean.accounting['relations']
    check('grow-blind relation census is recorded', set(relations) == {'8', '9', '10', '11'},
          json.dumps(relations))

    # The safety valve: at a kept-fact count too small for two-hop, one-hop records take
    # its place, are counted, and are still answerable from the kept eligible lines.
    tiny = dict(blind_lines=6, grow_g1=10**6, grow_g2=10**6)
    valve = build('grow-blind', step=0, **tiny)
    check('grow-blind degraded-two-hop valve fires and stays answerable',
          valve.accounting['blind']['degraded_two_hop'] > 0
          and [q[-1]['target'] for q in A.truth_paths(valve.canonical)]
          == valve.canonical_targets.answer.tolist()
          and [q[-1]['target'] for q in A.truth_paths(valve.monolithic)]
          == valve.monolithic_targets.answer.tolist(),
          f"{valve.accounting['blind']['degraded_two_hop']} degraded at --blind-lines 6")
    raised = False
    try:
        build('grow-blind', step=0, blind_lines=2, grow_g1=10**6, grow_g2=10**6)
    except RuntimeError:
        raised = True
    check('grow-blind fails loudly when no attribute fact survives', raised,
          'never emits a record it cannot answer')


# ------------------------------------------------------------------------------- marg-full

def single(x, i):
    return A.select(x, [i])


def test_margfull():
    p = dict(startup='hintwarm-onehop', hint_updates=0)
    clean = build('marg-full', step=0, visits=2, **p)
    with Poison():
        poisoned = build('marg-full', step=0, visits=2, **p)
    check('marg-full never touches gold intermediates or supporting lines',
          batch_equal(poisoned, clean), 'poisoned-gold batch is identical')
    for startup in ('grow', 'grow-blind'):
        q = dict(startup=startup, grow_g1=1500, grow_g2=3000)
        a = build('marg-full', step=0, visits=2, **q)
        with Poison():
            b = build('marg-full', step=0, visits=2, **q)
        check(f'marg-full --startup {startup} never touches gold', batch_equal(a, b))

    model = fresh_model()
    model.eval()

    # (1) brute force: independent per-entity forwards must reproduce the marginal.
    with torch.no_grad():
        got = S.marginal_probability(model, clean)
        link_logits = model(clean.link)
        want = []
        for i in range(clean.terminal_index.shape[0]):
            p1 = link_logits[i].softmax(-1)[ENTITY_MIN:ENTITY_MAX]
            total = 0.
            for e in range(ENTITIES):
                row = int(clean.terminal_index[i, e])
                logits = model(single(clean.terminal, row))[0]
                total += float(p1[e]) * float(logits.softmax(-1)[int(clean.two_hop_answers[i])])
            want.append(total)
    err = max(abs(float(a) - b) for a, b in zip(got, want))
    check('marginal equals a brute-force sum over the 16 entities', err < 1e-6, f'max |diff| {err:.3e}')

    # (2) the marginal is the same whether or not terminal calls are deduped.
    a = build('marg-full', step=0, visits=2, terminal_dedupe=True, **p)
    b = build('marg-full', step=0, visits=2, terminal_dedupe=False, **p)
    with torch.no_grad():
        pa, pb = S.marginal_probability(model, a), S.marginal_probability(model, b)
    check('terminal dedupe is exact', float((pa - pb).abs().max()) < 1e-6,
          f'{a.accounting["terminal_calls"]} vs {b.accounting["terminal_calls"]} terminal calls, '
          f'max |diff| {float((pa-pb).abs().max()):.3e}')
    check('dedupe only ever merges identical-eligibility calls',
          a.accounting['terminal_calls'] + a.accounting['blind']['deduped_terminal_calls']
          == a.accounting['terminal_calls_undeduped'])

    # (3) batching the 17 queries of a record into ONE forward == 17 separate forwards.
    record = 0
    parts = [('link', single(clean.link, record))]
    parts += [('t%d' % e, single(clean.terminal, int(clean.terminal_index[record, e])))
              for e in range(ENTITIES)]
    combined, slices = S._concat_inputs(parts)
    with torch.no_grad():
        batched = model(combined)
        separate = torch.cat([model(x) for _, x in parts], 0)
    err = float((batched - separate).abs().max())
    check('batched 17-query forward == 17 separate forwards', err < 1e-6, f'max |diff| {err:.3e}')
    check('the 17 queries share one memory encoding',
          combined.memory.shape[0] == clean.link.memory.shape[0] and combined.questions.shape[0] == 17)

    # (4) the whole-batch single forward agrees with four separate forwards.
    one = build('marg-full', step=0, visits=2, single_forward=True, **p)
    four = build('marg-full', step=0, visits=2, single_forward=False, **p)
    with torch.no_grad():
        a_pieces = S.margfull_logits(model, one)
        b_pieces = S.margfull_logits(model, four)
    worst = max(float((a_pieces[k] - b_pieces[k]).abs().max()) for k in a_pieces)
    check('single-forward plan == four-forward plan', worst < 1e-6, f'max |diff| {worst:.3e}')
    with torch.no_grad():
        la = S.margfull_losses(model, one)
        lb = S.margfull_losses(model, four)
    check('single-forward losses match', max(abs(float(x) - float(y)) for x, y in zip(la, lb)) < 1e-6)

    # (5) gradients reach BOTH the LINK call and the terminal calls.
    grad_model = fresh_model()
    link_logits = grad_model(clean.link)
    terminal_logits = grad_model(clean.terminal)
    link_logits.retain_grad(); terminal_logits.retain_grad()
    loss = -S.marginal_probability(grad_model, clean, link_logits,
                                   terminal_logits).clamp_min(1e-12).log().mean()
    loss.backward()
    check('gradient reaches the LINK call', float(link_logits.grad.abs().max()) > 0)
    check('gradient reaches the terminal calls', float(terminal_logits.grad.abs().max()) > 0)
    check('gradient reaches the embedding',
          float(grad_model.embedding.weight.grad.abs().max()) > 0)

    # (6) no evidence loss and no gold intermediate on the two-hop path.
    check('marg-full two-hop uses no supporting line',
          clean.accounting['evidence_lines_used'] == 0 and clean.accounting['gold_entities_used'] == 0)
    hinted = build('marg-full', step=0, visits=2, startup='hintwarm-onehop', hint_updates=1000)
    check('hintwarm-onehop hint touches only one-hop records',
          hinted.plan['hint'] and hinted.accounting['evidence_lines_used'] == hinted.accounting['kinds']['one_hop'],
          f'{hinted.accounting["evidence_lines_used"]} one-hop evidence lines, none elsewhere')
    late = build('marg-full', step=1000, visits=2, startup='hintwarm-onehop', hint_updates=1000)
    check('hintwarm-onehop hint switches off at H',
          not late.plan['hint'] and late.accounting['evidence_lines_used'] == 0)

    # (7) p1 is not renormalised: the sixteen entity probabilities may sum to < 1.
    with torch.no_grad():
        mass = model(clean.link).softmax(-1)[:, ENTITY_MIN:ENTITY_MAX].sum(-1)
    check('p1 is left un-renormalised', float(mass.max()) < 1. - 1e-9,
          f'entity mass max {float(mass.max()):.4f}')

    rng_base = random.Random(1101)
    for _ in range(3):
        V.training_batch_e0(rng_base, 16, frozenset())
    S.configure_variant('marg-full', seed=SMOKE_SEED, **p)
    rng_marg = random.Random(1101)
    for step in range(3):
        S.STATE['step'] = step
        S.A.training_batch(rng_marg, 16, frozenset())
    check('marg-full leaves the world stream unchanged',
          rng_base.getstate() == rng_marg.getstate())


# ---------------------------------------------------------------------------------- model

REFERENCE_KEYS = None


def test_model():
    global REFERENCE_KEYS
    model = A.new_model(SMOKE_SEED)
    check('parameter count is 79,316', model.parameters_count() == 79316,
          str(model.parameters_count()))
    reference = T.TokenMemoryReasoner()
    REFERENCE_KEYS = sorted(reference.state_dict())
    check('state-dict schema unchanged', sorted(model.state_dict()) == REFERENCE_KEYS,
          f'{len(REFERENCE_KEYS)} tensors')
    check('state-dict shapes unchanged',
          all(model.state_dict()[k].shape == reference.state_dict()[k].shape for k in REFERENCE_KEYS))
    for variant in S.VARIANTS:
        S.configure_variant(variant, seed=SMOKE_SEED)
        check(f'{variant} leaves the model untouched',
              A.new_model(SMOKE_SEED).parameters_count() == 79316
              and sorted(A.new_model(SMOKE_SEED).state_dict()) == REFERENCE_KEYS)


# ---------------------------------------------------------------------------------- smoke

def smoke_worker(variant, updates, n, root, seed, **params):
    """<= 30-update worker run against a throwaway manifest and a freshly made tiny panel."""
    out = root/f'fable-operator-{variant}-20260920'
    out.mkdir(parents=True, exist_ok=False)
    panel = P.generate('c1_own_one_hop', n=n, namespace=f'fable-startup-smoke:{variant}')
    panel_path = out/'smoke-panel.pt'
    torch.save(panel, panel_path)
    forbidden = out/'smoke-forbidden.json'
    forbidden.write_text('[]')
    here = Path(S.__file__).resolve()
    manifest = dict(variant=variant, startup=dict(params), smoke=True,
                    schedule=dict(updates=updates, training_seconds=900, work_seconds=1200,
                                  terminate_seconds=1230, visits_per_update=16),
                    exclusion_path=str(forbidden),
                    panels={'smoke': dict(path=str(panel_path), sha256=C.sha(panel_path),
                                          cutoff=0, n=n)},
                    files={str(here): C.sha(here)})
    (out/'astra_canonical_operator_launch.json').write_text(json.dumps(manifest))
    S.configure_variant(variant, seed=seed, **params)
    R.OUT = out
    started = time.monotonic()
    R.worker(seed, time.monotonic())
    completion = json.loads((out/f'astra_canonical_operator_seed-{seed}/completion.json').read_text())
    return completion, time.monotonic()-started


def test_smoke(updates, n):
    root = Path(tempfile.mkdtemp(prefix='fable-startup-smoke-'))
    try:
        assert updates <= 30, 'the smoke must never train more than 30 updates'
        for i, (variant, params) in enumerate((
                ('hintwarm', dict(hint_updates=max(1, updates//2))),
                ('grow', dict(grow_g1=max(1, updates//3), grow_g2=max(2, 2*updates//3))),
                ('grow-blind', dict(grow_g1=max(1, updates//3), grow_g2=max(2, 2*updates//3))),
                ('marg-full', dict(startup='hintwarm-onehop', hint_updates=max(1, updates//2))))):
            seed = 993400 + 10 + i
            assert seed >= 993400, seed
            completion, seconds = smoke_worker(variant, updates, n, root, seed, **params)
            check(f'{variant} worker smoke completes',
                  completion['complete'] and completion['updates'] == updates,
                  f'{updates} updates, R={completion["results"]["smoke"]["R"]}/{n}, '
                  f'{seconds:.1f}s, seed {seed}')
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ----------------------------------------------------------------------------------- main

GROUPS = dict(hintwarm=test_hintwarm, grow=test_grow, blind=test_blind,
              margfull=test_margfull, model=test_model)

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
