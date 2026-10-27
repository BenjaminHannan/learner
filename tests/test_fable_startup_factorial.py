"""Checks for scripts/fable_startup_factorial.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_startup_factorial.py
Run a group: python3.12 -B tests/test_fable_startup_factorial.py --only arms
Groups:
  arms      the 2x2 shares its questions/answers and differs only in story rows
  blind     arm A reproduces grow-blind's early batch bit-for-bit, on both RNG streams
  step      the training step equals the registered ``_step_e0`` step
  diag      the diagnostics are read-only (poisoned .grad) and measure what they claim
  panels    fresh probe builders and the supporting-line locator
  resume    a split extend run equals an unsplit run bit-for-bit
All groups train at most a handful of updates on non-registered seeds >= 997000 and never
touch a registered folder, a registered seed, or the registered panels except read-only.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts')):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_startup_factorial as F                                   # noqa: E402
import fable_operator_startup as S                                    # noqa: E402
import fable_operator_variants as V                                   # noqa: E402

A, E, T, data, torch, P, C = F.A, F.E, F.T, F.data, F.torch, F.P, F.C
QUESTION, ANSWER, WORLD, LINK = F.QUESTION, F.ANSWER, F.WORLD, F.LINK
DEV_SEED = 997001
CHECKS = 0

torch.set_num_threads(1)


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def streams(seed=DEV_SEED):
    return random.Random(1101), random.Random(f'fable-startup-factorial:{seed}')


def plans_once(visits=4, seed=DEV_SEED):
    rng, vrng = streams(seed)
    return F.plan_batch(rng, vrng, visits)


def same(a, b):
    return bool(torch.equal(a, b))


# --------------------------------------------------------------------------------- arms

def group_arms():
    plans, info = plans_once(visits=6)
    batches = {arm: F.materialise(plans, arm, info['records'], info['census'])
               for arm in F.ARM_NAMES}

    ref = batches['A']
    for arm in ('B', 'C', 'D'):
        b = batches[arm]
        for part, x, y in (('canonical', b.canonical, b.canonical_targets),
                           ('monolithic', b.monolithic, b.monolithic_targets)):
            rx = getattr(ref, part)
            ry = ref.canonical_targets if part == 'canonical' else ref.monolithic_targets
            check(f'{arm}: {part} questions bit-identical to A', same(x.questions, rx.questions))
            check(f'{arm}: {part} owner bit-identical to A', same(x.owner, rx.owner))
            check(f'{arm}: {part} answers bit-identical to A', same(y.answer, ry.answer))
    for arm, b in batches.items():
        ok = True
        for x in (b.canonical, b.monolithic):
            ok &= bool((x.eligible == x.memory.ne(0).any(-1)[x.owner]).all())
        check(f'{arm}: eligible == exactly the real kept rows of the visit', ok)

    # The supporting lines are the SAME original rows in every arm, only renumbered.
    for arm in ('B', 'C', 'D'):
        for part in ('canonical', 'monolithic'):
            ok = True
            for a_arm, b_arm in ((('A', arm),)):
                ka = {v: F.arm_keep(p, a_arm) for v, p in enumerate(plans)}
                kb = {v: F.arm_keep(p, b_arm) for v, p in enumerate(plans)}
                xa = getattr(batches[a_arm], part)
                ya = batches[a_arm].canonical_targets if part == 'canonical' \
                    else batches[a_arm].monolithic_targets
                yb = batches[b_arm].canonical_targets if part == 'canonical' \
                    else batches[b_arm].monolithic_targets
                for owner, la, lb in zip(xa.owner.tolist(), ya.lines.tolist(), yb.lines.tolist()):
                    ok &= [ka[owner][i] for i in la] == [kb[owner][i] for i in lb]
            check(f'{arm}: {part} supporting lines are the same ORIGINAL rows as A', ok)

    # Story-row content: subsets in original order, exactly as declared.
    for v, plan in enumerate(plans):
        keeps = {arm: F.arm_keep(plan, arm) for arm in F.ARM_NAMES}
        check(f'visit {v}: 24 fact lines, 16 kept blind',
              len(plan.facts) == 24 and len(plan.kept16) == 16,
              f'{len(plan.facts)}/{len(plan.kept16)}, others={len(plan.others)}')
        check(f'visit {v}: A = 16 facts only', keeps['A'] == plan.kept16)
        check(f'visit {v}: C = all 24 facts', keeps['C'] == sorted(plan.facts))
        check(f'visit {v}: B = A + all filler', keeps['B'] == sorted(set(plan.kept16) | set(plan.others)))
        check(f'visit {v}: D = the whole story',
              keeps['D'] == sorted(set(plan.facts) | set(plan.others))
              and len(keeps['D']) == sum(1 for row in plan.full if row))
        check(f'visit {v}: A subset of B, C; C subset of D; B subset of D',
              set(keeps['A']) < set(keeps['B']) and set(keeps['A']) < set(keeps['C'])
              and set(keeps['C']) < set(keeps['D']) and set(keeps['B']) < set(keeps['D']))
        check(f'visit {v}: kept rows keep their original order and content',
              all([plan.full[old] for old in keeps[arm]] ==
                  [row for k, row in enumerate(plan.full) if k in set(keeps[arm])]
                  for arm in F.ARM_NAMES))

    # Only the memory tensor differs; row counts follow the arm.
    rows = {arm: batches[arm].canonical.memory.shape[1] for arm in F.ARM_NAMES}
    check('row counts: A < C < D and A < B < D',
          rows['A'] < rows['C'] < rows['D'] and rows['A'] < rows['B'] < rows['D'], json.dumps(rows))
    check('A keeps exactly 16 rows per visit', rows['A'] == 16)

    # Every record is answerable from every arm's eligible rows, by the evaluator.
    for arm, b in batches.items():
        paths = A.truth_paths(b.canonical)
        check(f'{arm}: evaluator re-derives every canonical answer',
              [p[-1]['target'] for p in paths] == b.canonical_targets.answer.tolist())
        paths = A.truth_paths(b.monolithic)
        check(f'{arm}: evaluator re-derives every monolithic answer',
              [p[-1]['target'] for p in paths] == b.monolithic_targets.answer.tolist())

    # Identical initialisation per seed across arms.
    prints = {arm: C.fingerprint(A.new_model(DEV_SEED)) for arm in F.ARM_NAMES}
    check('identical model initialisation per seed across arms', len(set(prints.values())) == 1)

    # The plan is arm-independent: it is drawn before any arm exists.
    r1, v1 = streams(); F.plan_batch(r1, v1, 3)
    r2, v2 = streams(); F.plan_batch(r2, v2, 3)
    check('plan_batch is deterministic given its two streams',
          r1.getstate() == r2.getstate() and v1.getstate() == v2.getstate())


# -------------------------------------------------------------------------------- blind

def group_blind():
    """Arm A must BE grow-blind's early phase, not merely resemble it."""
    visits = 6
    rng_a, vrng_a = streams()
    plans, info = F.plan_batch(rng_a, vrng_a, visits)
    arm_a = F.materialise(plans, 'A', info['records'], info['census'])

    S.configure_variant('grow-blind', seed=None)
    S.STATE['vrng'] = random.Random(f'fable-startup-factorial:{DEV_SEED}')
    S.STATE['step'] = 0                       # fraction 0 => the early phase
    rng_b = random.Random(1101)
    blind = S.training_batch_blind(rng_b, visits, frozenset())

    for part in ('canonical', 'monolithic'):
        x, xb = getattr(arm_a, part), getattr(blind, part)
        y = arm_a.canonical_targets if part == 'canonical' else arm_a.monolithic_targets
        yb = blind.canonical_targets if part == 'canonical' else blind.monolithic_targets
        check(f'arm A == grow-blind: {part} memory', same(x.memory, xb.memory))
        check(f'arm A == grow-blind: {part} questions', same(x.questions, xb.questions))
        check(f'arm A == grow-blind: {part} owner', same(x.owner, xb.owner))
        check(f'arm A == grow-blind: {part} eligible', same(x.eligible, xb.eligible))
        check(f'arm A == grow-blind: {part} answers', same(y.answer, yb.answer))
        check(f'arm A == grow-blind: {part} supporting lines', same(y.lines, yb.lines))
    check('arm A == grow-blind: world stream consumed identically',
          rng_a.getstate() == rng_b.getstate())
    check('arm A == grow-blind: variant stream consumed identically',
          vrng_a.getstate() == S.STATE['vrng'].getstate())

    # The world stream is consumed exactly as by the registered base recipe.
    r1 = random.Random(1101)
    F.plan_batch(r1, random.Random('x'), 3)
    F.plan_batch(r1, random.Random('x'), 3)
    r2 = random.Random(1101)
    V.ORIGINAL_BATCH(r2, 3, frozenset())
    V.ORIGINAL_BATCH(r2, 3, frozenset())
    check('world stream matches the registered base recipe batch for batch',
          r1.getstate() == r2.getstate())

    # grow-blind's honesty properties are inherited.
    census = info['census']
    check('census accounts for every generator question',
          census['kept_generator_one_hop'] + census['replaced_one_hop'] == 2*visits
          and census['kept_generator_two_hop'] + census['replaced_two_hop']
          + census['degraded_two_hop'] == 2*visits, json.dumps(census))
    terminals = [rec for plan in plans for rec in plan.records if rec['kind'] == 'terminal']
    check('relation 10 is never a two-hop terminal', all(r['q'][2] != 10 for r in terminals))
    check('every record is a visible-token question',
          all(rec['q'][0] == QUESTION and rec['q'][-1] == ANSWER
              and F.ENTITY_MIN <= rec['q'][1] < F.ENTITY_MAX
              for plan in plans for rec in plan.records))


# --------------------------------------------------------------------------------- step

def group_step():
    """The step must be ``fable_operator_variants._step_e0`` with an injected lr."""
    plans, info = plans_once(visits=4)
    batch = F.materialise(plans, 'C', info['records'], info['census'])
    mine, theirs = A.new_model(DEV_SEED), A.new_model(DEV_SEED)
    check('two fresh models of one seed are identical',
          C.fingerprint(mine) == C.fingerprint(theirs))
    om, ot = A.T.optimizer_for(mine), A.T.optimizer_for(theirs)
    for step in range(3):
        F.training_step(mine, om, batch, V.lr_at(step))
        V._step_e0(theirs, ot, batch, step)
    check('training_step == registered _step_e0 after 3 updates',
          C.fingerprint(mine) == C.fingerprint(theirs))
    check('lr_constant == the registered lr in the constant phase',
          all(F.lr_constant(s) == V.lr_at(s) for s in (0, 1, 99, 100, 2499, 3999)))
    check('lr_extend: warmup, flat to 16,000, linear to 1e-4 at 18,000',
          F.lr_extend(0) == 1e-5 and F.lr_extend(99) == 1e-3 and F.lr_extend(15999) == 1e-3
          and abs(F.lr_extend(17999) - (1e-3 + (1e-4-1e-3)*1999/2000)) < 1e-12,
          f'{F.lr_extend(0)}, {F.lr_extend(17999)}')
    row = F.training_step(mine, om, batch, 1e-3)
    check('training_step reports loss and accuracy',
          0. <= row['train_acc'] <= 1. and row['train_loss'] > 0., json.dumps(row))


# --------------------------------------------------------------------------------- diag

def group_diag():
    probe = F.build_probe(DEV_SEED, 'A', visits=4)
    model = A.new_model(DEV_SEED)

    # (1) the mask really selects the supporting line's tokens, and nothing else.
    x, y = probe.batch.canonical, probe.batch.canonical_targets
    per_line = x.memory.ne(0).sum(-1)[x.owner]
    check('supporting-line mask has exactly that line\'s tokens',
          same(probe.mask.sum(-1), per_line.gather(1, y.lines[:, :1]).squeeze(1)))
    total = (per_line * x.eligible).sum(-1) + 1
    check('uniform baseline = line tokens / (eligible tokens + 1)',
          bool((probe.uniform - per_line.gather(1, y.lines[:, :1]).squeeze(1).double()
                / total.double()).abs().max() < 1e-12))

    # Uniform attention really does produce the uniform baseline: replace the trace.
    with torch.no_grad():
        logits, mass = F.correct_line_mass(model, x, probe.mask)
    check('mass is per step and per head', mass.shape[1:] == (model.steps, model.heads),
          str(tuple(mass.shape)))
    check('mass is a probability mass', bool((mass >= -1e-6).all() and (mass <= 1+1e-6).all()))
    check('an untrained model sits near the uniform baseline',
          bool((mass.mean(( 1, 2)).double() / probe.uniform).mean() < 3.),
          f'ratio={float((mass.mean((1, 2)).double() / probe.uniform).mean()):.3f}')

    # (2) POISON TEST: diagnostics must not touch parameters or gradients.
    for p in model.parameters():
        p.grad = torch.full_like(p, 7.)
    before_params = C.fingerprint(model)
    before_grads = [p.grad.clone() for p in model.parameters()]
    row = F.diagnostics(model, probe, eta=1e-2)
    check('diagnostics leave every parameter bit-identical', C.fingerprint(model) == before_params)
    check('diagnostics leave every .grad bit-identical',
          all(same(p.grad, g) for p, g in zip(model.parameters(), before_grads)))
    for p in model.parameters():
        p.grad = None

    # (3) end-to-end: a logged run and a silent run agree bit-for-bit.
    plans, info = plans_once(visits=4)
    batch = F.materialise(plans, 'A', info['records'], info['census'])
    loud, quiet = A.new_model(DEV_SEED), A.new_model(DEV_SEED)
    ol, oq = A.T.optimizer_for(loud), A.T.optimizer_for(quiet)
    for step in range(4):
        F.training_step(loud, ol, batch, F.lr_constant(step))
        F.diagnostics(loud, probe, eta=1e-2)
        F.training_step(quiet, oq, batch, F.lr_constant(step))
    check('a fully logged run equals a silent run bit-for-bit',
          C.fingerprint(loud) == C.fingerprint(quiet))

    # (4) the routing gradient is the real directional derivative of the mass.
    fresh = A.new_model(DEV_SEED)
    eta = 1e-3
    out = F.routing_gradient(fresh, probe, eta)
    predicted = out['routing_directional_all'] * eta
    check('routing: finite difference matches the directional derivative at small eta',
          abs(out['routing_delta_all'] - predicted) <= 0.05*abs(predicted) + 2e-6,
          f"delta={out['routing_delta_all']:.3e} predicted={predicted:.3e}")
    check('routing reports both gradient norms and a cosine',
          out['routing_grad_norm_loss'] > 0 and out['routing_grad_norm_mass_all'] > 0
          and -1.0001 <= out['routing_cosine_all'] <= 1.0001, json.dumps(
              {k: out[k] for k in ('routing_grad_norm_loss', 'routing_grad_norm_mass_all',
                                   'routing_cosine_all')}))
    check('routing leaves the model untouched', C.fingerprint(fresh) == C.fingerprint(A.new_model(DEV_SEED)))

    # (5) the prediction distribution is reported honestly.
    check('prediction distribution keys present',
          {'distinct_predictions', 'top1_share', 'prediction_entropy',
           'one_hop_acc_by_relation'} <= set(row),
          f"distinct={row['distinct_predictions']} top1={row['top1_share']}")
    check('one-hop accuracy is reported per relation',
          set(row['one_hop_acc_by_relation']) == {'8', '9', '10'})
    check('distinct predictions <= probe records',
          1 <= row['distinct_predictions'] <= row['probe_records'])

    # A degenerate constant predictor scores top1_share 1.0 and entropy 0.
    class Constant(torch.nn.Module):
        steps, heads = model.steps, model.heads

        def forward(self, inputs, *, trace=False):
            logits, attention = model(inputs, trace=True)
            out = torch.full_like(logits, -10.)
            out[:, 52] = 10.
            return (out, attention) if trace else out

    degenerate = F.probe_report(Constant(), probe)
    check('a constant predictor reads as 1 distinct prediction, entropy 0',
          degenerate['distinct_predictions'] == 1 and degenerate['top1_share'] == 1.
          and degenerate['prediction_entropy'] == 0.)


# ------------------------------------------------------------------------------- panels

def group_panels():
    chunks = F.fresh_one_hop_chunks('unit', n=64, entities=6, fact_lines=16,
                                    filler_fraction=0., namespace='unit-test')
    x, answers = chunks[0]
    check('fresh probe: one-hop questions only',
          x.questions.shape[1] == 4 and bool((x.questions[:, 0] == QUESTION).all()))
    check('fresh probe: 16 kept rows, no filler', x.memory.shape[1] == 16)
    lines = F.supporting_lines(x)
    check('supporting-line locator agrees with the evaluator',
          all(x.memory[o, l, 3].item() == a for o, l, a in
              zip(x.owner.tolist(), lines.tolist(), answers.tolist())))
    big = F.fresh_one_hop_chunks('unit16', n=32, entities=16, fact_lines=24,
                                 filler_fraction=1., namespace='unit-test')
    xb, ab = big[0]
    check('16-person worlds are supported at one hop',
          xb.memory.shape[0] == 32 and int(ab.numel()) == 32
          and [p[-1]['target'] for p in A.truth_paths(xb)] == ab.tolist(),
          f'rows per visit = {xb.memory.shape[1]}')
    model = A.new_model(DEV_SEED)
    result = F.score_one_hop(model, chunks)
    check('score_one_hop reports accuracy, mass and the uniform baseline',
          result['n'] == 64 and 0. <= result['accuracy'] <= 1.
          and result['correct_line_mass'] > 0 and result['uniform_line_mass'] > 0,
          json.dumps({k: result[k] for k in ('n', 'accuracy', 'correct_line_mass',
                                             'uniform_line_mass')}))
    check('sweep covers 2 fact sizes x 3 filler fractions x 2 world sizes',
          len(F.SWEEP_CELLS) == 12
          and {c['fact_lines'] for c in F.SWEEP_CELLS} == {16, 24}
          and {c['filler_fraction'] for c in F.SWEEP_CELLS} == {0., .5, 1.}
          and {c['entities'] for c in F.SWEEP_CELLS} == {6, 16})

    # The registered c1 panel is readable and unchanged; nothing is written there.
    manifest = json.loads((BASE/'artifacts/fable-operator-grow-blind-20260920'
                           / 'astra_canonical_operator_launch.json').read_text())
    c1, row = F.registered_c1(manifest)
    check('registered c1 loads read-only, sha verified, 512 one-hop questions',
          sum(int(a.numel()) for _, a in c1) == 512 and row['cutoff'] == 487)
    scored = F.score_one_hop(model, c1[:1])
    check('c1 scores through the same one-hop path', scored['n'] == 32, json.dumps(scored))


# ------------------------------------------------------------------------------- resume

def group_resume():
    folder = Path(tempfile.mkdtemp(prefix='factorial-resume-'))
    try:
        kw = dict(updates=6, flat=4, visits=3, log_every=2, probe_visits=2,
                  routing_eta=1e-2, forbidden=frozenset(), arm='D', quiet=True)
        whole = F.extend_chunk(folder/'whole', DEV_SEED, chunk_updates=6, **kw)
        split = F.extend_chunk(folder/'split', DEV_SEED, chunk_updates=3, **kw)
        check('a chunk stops at its budget', split['step'] == 3 and not split['done'],
              json.dumps({k: split[k] for k in ('step', 'first_step', 'done')}))
        second = F.extend_chunk(folder/'split', DEV_SEED, chunk_updates=3, **kw)
        check('resume continues from the saved update',
              second['first_step'] == 3 and second['step'] == 6 and second['done'])
        check('a split run equals an unsplit run bit-for-bit',
              whole['fingerprint'] == second['fingerprint'],
              f"{whole['fingerprint'][:16]} vs {second['fingerprint'][:16]}")
        w = torch.load(folder/'whole/resume-000006.pt', map_location='cpu', weights_only=False)
        s = torch.load(folder/'split/resume-000006.pt', map_location='cpu', weights_only=False)
        check('resume restores both data streams exactly',
              w['rng']['world'] == s['rng']['world'] and w['rng']['variant'] == s['rng']['variant'])
        check('resume restores the optimizer exactly',
              all(torch.equal(w['optimizer']['state'][k][f], s['optimizer']['state'][k][f])
                  for k in w['optimizer']['state'] for f in ('exp_avg', 'exp_avg_sq')))
        check('the split run logged the same probe rows',
              [r['update'] for r in w['rows']] == [r['update'] for r in s['rows']]
              and all(a['train_loss'] == b['train_loss'] for a, b in zip(w['rows'], s['rows'])),
              f"{[r['update'] for r in w['rows']]}")
        different = F.extend_chunk(folder/'other', DEV_SEED+1, chunk_updates=6, **kw)
        check('a different seed gives a different result',
              different['fingerprint'] != whole['fingerprint'])
    finally:
        shutil.rmtree(folder, ignore_errors=True)


GROUPS = dict(arms=group_arms, blind=group_blind, step=group_step, diag=group_diag,
              panels=group_panels, resume=group_resume)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', default=None, choices=list(GROUPS))
    chosen = ap.parse_args().only
    data.bootstrap()
    for name, fn in GROUPS.items():
        if chosen and name != chosen:
            continue
        print(f'--- {name} ---', flush=True)
        fn()
    print(f'ALL {CHECKS} CHECKS PASSED', flush=True)
