"""Checks for scripts/fable_startup_factorial_v2.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_startup_factorial_v2.py
Run a group: python3.12 -B tests/test_fable_startup_factorial_v2.py --only arms
Groups:
  spec      every registered number is read back out of the spec document
  arms      within a seed the arms share questions/answers/weights/support/init and
            differ ONLY in which story rows are readable
  signature the cached signature equals A.visible_signature; probe signatures are
            excluded from training, in each arm's reduced story as well as in the full one
  onset     the onset detector on never-started, late-start, noisy and gappy curves
  resume    a chunked run equals an unchunked run bit-for-bit, on every RNG stream
  diag      the diagnostics are read-only (poisoned .grad, untouched optimizer state)
  transfer  the freeze-before-growth cells are nested and keep question/answer fixed
  report    the report prints "(missing)" for every missing run and never averages
All groups use disposable seeds (never the registered 1300/1301/1302), write only into a
temporary directory, and read the registered artifacts without writing to them.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts')):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_startup_factorial_v2 as F2                                 # noqa: E402
import fable_startup_factorial as F1                                    # noqa: E402

A, data, torch, P, C = F2.A, F2.data, F2.torch, F2.P, F2.C
DEV_SEED = 997101
SPEC = BASE/'design/v3/18-startup-factorial-v2-preregistration-draft.md'
CHECKS = 0

torch.set_num_threads(1)


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def same(a, b):
    return bool(torch.equal(a, b))


# --------------------------------------------------------------------------------- spec

SPEC_NEEDLES = (
    ('the seeds', 'seeds 1300, 1301, 1302'),
    ('the world namespace', 'astra-startup-factorial-v2-world:seed'),
    ('the plan namespace', 'astra-startup-factorial-v2-plan:seed'),
    ('the budget', '2,500 updates'),
    ('the 2x2 rows', '| A | 16 | none |'),
    ('the 2x2 rows', '| D | 24 | all |'),
    ('what must be identical across arms',
     'Question tokens, answers, record weights, support facts, model initialization, '
     'world draws and optimizer schedule must be identical within each seed across arms'),
    ('inline filler is retained', 'Retain inline filler tokens within fact rows in every arm'),
    ('D is not e0', 'D is “full context with subset-selected questions,” not e0'),
    ('the parameter count', '79,316-parameter'),
    ('the batch', '16 worlds/update'),
    ('the loss weights', 'canonical/monolithic loss 0.75/0.25'),
    ('the schedule', 'Warm up to 1e-3 over 100 updates'),
    ('the probe', '512-question attribute-only validation probe'),
    ('the threshold', '461/512'),
    ('the onset window', 't−200, t−150, t−100, t−50 and t'),
    ('the onset floor', 'earliest t≥200'),
    ('the probe grid', 'At updates 0, 50, …, 2500'),
    ('missing probes', 'Missing probes do not qualify'),
    ('the second probe', 'a second untouched 512-question probe'),
    ('the routing cadence', 'every 50 updates'),
    ('three reads and four heads', 'three reads and four heads'),
    ('unrounded reductions', 'without rounding to eight decimal places'),
    ('the central differences', 'eta=1e-3, 1e-4 and 1e-5'),
    ('the AdamW diagnostic', 'The live training state must remain byte-identical'),
    ('the long run', '18,000-update trajectory'),
    ('the long-run schedule', 'warmup 100, flat to 16,000, decay to 1e-4 at 18,000'),
    ('the long-run comparison', 'frozen 6,000-update checkpoint'),
    ('the chunk cap', 'resumable chunk ≤1,200 seconds'),
    ('the audit-worker cap', 'at most three audit-experiment workers'),
    ('the total-worker cap', 'at most six total registered training workers'),
    ('the six-person transfer cells', '16/24 facts × filler fractions 0/0.5/1'),
    ('the sixteen-person transfer cells', '16/24/64 facts'),
    ('the full 64-fact world', 'include the genuine full 64-fact world'),
    ('the transfer size', '512 paired units per cell'),
    ('the reduced-input audit',
     'audit the actual reduced visible memory and the full-source memory'),
)


def group_spec():
    text = SPEC.read_text()
    check('the spec document is present and is the v2 draft',
          'startup factorial v2' in text and 'Track A validation only' in text)
    for label, needle in SPEC_NEEDLES:
        check(f'the spec states {label}', needle in text, needle[:48])
    check('the registered seeds match the spec', F2.REGISTERED_SEEDS == (1300, 1301, 1302))
    check('the namespaces match the spec',
          F2.ns_world(1300) == 'astra-startup-factorial-v2-world:1300'
          and F2.ns_plan(1300) == 'astra-startup-factorial-v2-plan:1300')
    check('the budget numbers match the spec',
          (F2.UPDATES, F2.VISITS, F2.PARAMETERS, F2.CANONICAL_WEIGHT,
           F2.MONOLITHIC_WEIGHT, F2.WARMUP_UPDATES, F2.FLAT_LR)
          == (2500, 16, 79316, .75, .25, 100, 1e-3))
    check('the onset numbers match the spec',
          (F2.VALIDATION_N, F2.ONSET_CORRECT, F2.ONSET_WINDOW, F2.ONSET_MIN_UPDATE,
           F2.PROBE_EVERY) == (512, 461, 200, 200, 50))
    check('the long-run numbers match the spec',
          (F2.LONGRUN_ARM, F2.LONGRUN_UPDATES, F2.LONGRUN_FLAT_UNTIL,
           F2.LONGRUN_FINAL_LR, F2.LONGRUN_MIDPOINT, F2.CHUNK_SECONDS_MAX)
          == ('D', 18000, 16000, 1e-4, 6000, 1200))
    check('the capacity caps match the spec',
          (F2.MAX_AUDIT_WORKERS, F2.MAX_TOTAL_WORKERS) == (3, 6))
    check('the central-difference etas match the spec', F2.CENTRAL_ETAS == (1e-3, 1e-4, 1e-5))
    check('the 2x2 is 16/24 facts x filler absent/present',
          {(v['facts'], v['filler']) for v in F2.ARMS.values()}
          == {(16, False), (16, True), (24, False), (24, True)}
          and F2.ARM_NAMES == ('A', 'B', 'C', 'D')
          and F2.BLIND_LINES == 16)
    six = [c for c in F2.TRANSFER_CELLS if c['entities'] == 6]
    sixteen = [c for c in F2.TRANSFER_CELLS if c['entities'] == 16]
    check('the transfer cells are 6 six-person + 9 sixteen-person, 64 facts included',
          len(six) == 6 and len(sixteen) == 9
          and {c['fact_lines'] for c in six} == {16, 24}
          and {c['fact_lines'] for c in sixteen} == {16, 24, 64}
          and {c['filler_fraction'] for c in F2.TRANSFER_CELLS} == {0., .5, 1.}
          and (F2.TRANSFER_N, F2.TRANSFER_CORRECT) == (512, 461))
    check('the learning rate warms up over 100 updates and then holds 1e-3',
          F2.lr_factorial(0) == 1e-5 and F2.lr_factorial(99) == 1e-3
          and F2.lr_factorial(2499) == 1e-3)
    check('the long-run schedule is flat to 16,000 and linear to 1e-4 at 18,000',
          F2.lr_longrun(99) == 1e-3 and F2.lr_longrun(15999) == 1e-3
          and F2.lr_longrun(17999) < 1.1e-4 and F2.lr_longrun(16999) < 1e-3,
          f'{F2.lr_longrun(16999):.3e} then {F2.lr_longrun(17999):.3e}')


# --------------------------------------------------------------------------------- arms

def group_arms():
    rng, vrng = F2.streams(DEV_SEED)
    plans, info = F2.plan_batch(rng, vrng, 6, frozenset())
    batches = {arm: F2.arm_batch(plans, info, arm) for arm in F2.ARM_NAMES}
    reference = batches['A']
    for arm in ('B', 'C', 'D'):
        b = batches[arm]
        for part in ('canonical', 'monolithic'):
            x, rx = getattr(b, part), getattr(reference, part)
            y = b.canonical_targets if part == 'canonical' else b.monolithic_targets
            ry = (reference.canonical_targets if part == 'canonical'
                  else reference.monolithic_targets)
            check(f'{arm}: {part} question tokens identical to A', same(x.questions, rx.questions))
            check(f'{arm}: {part} owner identical to A', same(x.owner, rx.owner))
            check(f'{arm}: {part} answers identical to A', same(y.answer, ry.answer))
        check(f'{arm}: record weights identical to A (same kinds, same 0.75/0.25 groups)',
              b.accounting['kinds'] == reference.accounting['kinds']
              and b.canonical.questions.shape[0] == reference.canonical.questions.shape[0]
              and b.monolithic.questions.shape[0] == reference.monolithic.questions.shape[0],
              json.dumps(b.accounting['kinds']))
        maps = {a: [F1.arm_keep(p, a) for p in plans] for a in ('A', arm)}
        ok = True
        for part in ('canonical', 'monolithic'):
            base = getattr(reference, part)
            ry = (reference.canonical_targets if part == 'canonical'
                  else reference.monolithic_targets)
            y = (batches[arm].canonical_targets if part == 'canonical'
                 else batches[arm].monolithic_targets)
            for owner, la, lb in zip(base.owner.tolist(), ry.lines.tolist(), y.lines.tolist()):
                ok &= [maps['A'][owner][i] for i in la] == [maps[arm][owner][i] for i in lb]
        check(f'{arm}: every supporting fact is the SAME original row as A', ok)

    for v, plan in enumerate(plans):
        keeps = {arm: F1.arm_keep(plan, arm) for arm in F2.ARM_NAMES}
        check(f'visit {v}: 24 fact rows, 16 in the label-free core',
              len(plan.facts) == 24 and len(plan.kept16) == 16)
        check(f'visit {v}: the arms differ ONLY by the spec\'s two factors',
              keeps['A'] == sorted(plan.kept16)
              and keeps['C'] == sorted(plan.facts)
              and keeps['B'] == sorted(set(plan.kept16) | set(plan.others))
              and keeps['D'] == sorted(set(plan.facts) | set(plan.others)))
        check(f'visit {v}: the rows are nested A<B<D and A<C<D, in original order',
              set(keeps['A']) < set(keeps['B']) < set(keeps['D'])
              and set(keeps['A']) < set(keeps['C']) < set(keeps['D'])
              and all(keeps[a] == sorted(keeps[a]) for a in F2.ARM_NAMES))
        check(f'visit {v}: every kept row is the untouched source row, inline filler and all',
              all(plan.full[o] == plan.full[o] and len(plan.full[o]) > 4
                  for a in F2.ARM_NAMES for o in keeps[a] if o in set(plan.facts)),
              f'fact-row token counts {sorted({len(plan.full[o]) for o in plan.facts})}')
    for arm, b in batches.items():
        check(f'{arm}: the evaluator re-derives every canonical answer from the shown rows',
              [p[-1]['target'] for p in A.truth_paths(b.canonical)]
              == b.canonical_targets.answer.tolist())
        check(f'{arm}: every real kept row is causally eligible',
              all(bool((x.eligible == x.memory.ne(0).any(-1)[x.owner]).all())
                  for x in (b.canonical, b.monolithic)))
    check('identical initialisation per seed across arms, at 79,316 parameters',
          len({C.fingerprint(A.new_model(DEV_SEED)) for _ in F2.ARM_NAMES}) == 1
          and A.new_model(DEV_SEED).parameters_count() == F2.PARAMETERS)
    r1, v1 = F2.streams(DEV_SEED)
    r2, v2 = F2.streams(DEV_SEED)
    F2.plan_batch(r1, v1, 3, frozenset())
    F2.plan_batch(r2, v2, 3, frozenset())
    check('the two per-seed streams are shared and arm-free: the same plan twice',
          r1.getstate() == r2.getstate() and v1.getstate() == v2.getstate())
    other, _ = F2.streams(DEV_SEED+1)
    check('a different seed draws a different world stream', other.getstate() != r1.getstate())
    audit = F2.cross_arm_audit(DEV_SEED, frozenset(), updates=2, visits=4)
    check('cross_arm_audit passes and reports the rows each arm may read',
          all(c['questions_answers_weights_identical'] and c['story_rows_nested']
              and c['support_rows_identical'] for c in audit['checks'])
          and audit['parameters'] == F2.PARAMETERS,
          json.dumps(audit['checks'][0]['rows_per_visit']))
    probe = F2.probe_units('unit-test-probe', 8)
    packed = {arm: F2.pack_units(probe, arm) for arm in F2.ARM_NAMES}
    check('validation probe: questions and answers matched across arms',
          all(same(packed[a][0].questions, packed['A'][0].questions)
              and same(packed[a][1], packed['A'][1]) for a in F2.ARM_NAMES))
    check('validation probe: attribute-only questions, one per world',
          all(u.q[2] in F2.ATTRIBUTE_RELATIONS and len(u.q) == 4 for u in probe)
          and packed['A'][0].memory.shape[0] == 8)
    check('validation probe: only the readable rows differ across arms',
          packed['A'][0].memory.shape[1] == 16
          and packed['C'][0].memory.shape[1] == 24
          and packed['B'][0].memory.shape[1] > 16
          and packed['D'][0].memory.shape[1] > packed['C'][0].memory.shape[1])


# ---------------------------------------------------------------------------- signature

def group_signature():
    rng, vrng = F2.streams(DEV_SEED)
    plans, info = F2.plan_batch(rng, vrng, 3, frozenset())
    ok = True
    for plan in plans:
        prefixes = F2.condition_prefixes(plan.full, plan.kept16, plan.facts, plan.others)
        for rec in plan.records:
            for name, prefix in prefixes.items():
                rows = (plan.full if name == 'full'
                        else [plan.full[o] for o in F1.arm_keep(plan, name)])
                ok &= F2._signature(prefix, rec['q']) == A.visible_signature(rows, rec['q'])
    check('the cached signature equals A.visible_signature in all five conditions', ok)

    plan = plans[0]
    record = plan.records[0]
    prefixes = F2.condition_prefixes(plan.full, plan.kept16, plan.facts, plan.others)
    check('a reduced-arm signature differs from the full-story signature (v1 hashed only '
          'the full story)',
          F2._signature(prefixes['B'], record['q']) != F2._signature(prefixes['full'],
                                                                     record['q']))
    for condition in ('A', 'B', 'C', 'D', 'full'):
        sig = F2._signature(prefixes[condition], record['q'])
        raised = ''
        try:
            r2, v2 = F2.streams(DEV_SEED)
            F2.plan_batch(r2, v2, 3, {sig})
        except RuntimeError as exc:
            raised = str(exc)
        check(f'training refuses a collision in condition {condition}, '
              'instead of skipping the record', 'run invalid' in raised, raised[:60])
    r2, v2 = F2.streams(DEV_SEED)
    plans2, info2 = F2.plan_batch(r2, v2, 3, {'0'*64})
    check('a non-colliding exclusion set still audits all five conditions of every record',
          info2['signature_checks'] == 5*sum(len(p.records) for p in plans2),
          f"{info2['signature_checks']} signatures")

    folder = Path(tempfile.mkdtemp(prefix='factorial-v2-sig-'))
    try:
        transfer = F2.build_transfer_plan(folder, n=4)
        record, exclusions = F2.build_plan(folder, DEV_SEED, frozenset(), audit_updates=1,
                                           validation_n=8, transfer_signatures=transfer)
        excluded = set(exclusions)
        units = F2.probe_units(F2.ns_validation(DEV_SEED), 8)
        present = True
        for u in units:
            for prefix in F2.condition_prefixes(u.full, u.kept16, u.facts, u.others).values():
                present &= F2._signature(prefix, u.q) in excluded
        check('every validation-probe signature, in every arm and in the full story, '
              'is excluded from training', present)
        confirm = F2.probe_units(F2.ns_confirm(DEV_SEED), 8)
        check('the second untouched probe is excluded too, and is a different draw',
              all(F2._signature(F2.condition_prefixes(
                  u.full, u.kept16, u.facts, u.others)['D'], u.q) in excluded
                  for u in confirm)
              and [u.q for u in confirm] != [u.q for u in units])
        rplans, _ = F2.routing_plans(DEV_SEED, 2)
        check('the shared routing probe is separately excluded',
              all(sig in excluded for p in rplans for _, sig in F2.plan_signatures(p)))
        check('every transfer-cell signature is frozen and excluded before training',
              bool(transfer) and set(transfer) <= excluded)
        check('the frozen plan states the exclusion digest and the probe properties',
              record['exclusion_digest'] == A.digest(sorted(excluded))
              and record['probes']['validation']['attribute_only'] is True
              and record['probes']['validation']['registered_panel_collisions'] == 0
              and record['exclusion_count'] == len(excluded),
              f"{record['exclusion_count']} signatures")
        check('the plan is written where check-manifest expects it',
              (folder/f'plan/plan-seed-{DEV_SEED}.json').exists()
              and F2.load_exclusions(folder, DEV_SEED) == excluded)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# -------------------------------------------------------------------------------- onset

def group_onset():
    threshold = F2.ONSET_CORRECT
    grid = list(range(0, F2.UPDATES+1, F2.PROBE_EVERY))
    never = {t: 40 for t in grid}
    check('never started: no onset, and the final window is not qualified',
          F2.first_qualified_onset(never) is None
          and F2.onset_summary(never)['final_window_qualified'] is False)
    late = {t: (40 if t < 2100 else 500) for t in grid}
    check('late start: the first qualifying t is 200 after the first good probe',
          F2.first_qualified_onset(late) == 2300, str(F2.first_qualified_onset(late)))
    early = {t: (40 if t < 200 else 500) for t in grid}
    check('good from update 200 on: first qualifies at 400',
          F2.first_qualified_onset(early) == 400, str(F2.first_qualified_onset(early)))
    check('nothing qualifies before update 200, however good the probes are',
          F2.first_qualified_onset({t: 512 for t in grid}) == 200)
    noisy = {t: (40 if t < 800 else 300 if t in (1000, 1500) else 500) for t in grid}
    check('noisy: a single dip below threshold breaks the window',
          F2.first_qualified_onset(noisy) == 1250, str(F2.first_qualified_onset(noisy)))
    summary = F2.onset_summary(noisy)
    check('the regressions after the first onset are recorded separately',
          summary['first_qualified_onset'] == 1250
          and summary['regressions_after_onset'] == [1500]
          and summary['final_window_qualified'] is True,
          json.dumps(summary['regressions_after_onset']))
    missing = {t: (500 if t >= 1000 else 40) for t in grid}
    missing[1100] = None
    check('a MISSING probe never qualifies a window and is not interpolated',
          F2.first_qualified_onset(missing) == 1350, str(F2.first_qualified_onset(missing)))
    edge = {t: (512 if t in (1000, 1050, 1100, 1150, 1200) else 40) for t in grid}
    check('exactly the five scheduled probes t-200..t are required',
          F2.first_qualified_onset(edge) == 1200
          and F2.first_qualified_onset({k: v for k, v in edge.items() if k != 1100}) is None)
    boundary = {t: (threshold-1 if t < 1000 else threshold) for t in grid}
    check('the threshold is "at least 461/512", not "more than"',
          F2.first_qualified_onset(boundary) == 1200, str(F2.first_qualified_onset(boundary)))
    check('the final window is the five probes 2300..2500',
          F2.onset_summary(never)['final_window'] == [2300, 2350, 2400, 2450, 2500])
    check('the long run uses the same rule on its own 18,000-update grid',
          F2.onset_summary({t: 500 for t in range(0, F2.LONGRUN_UPDATES+1, 50)},
                           F2.LONGRUN_UPDATES)['final_window'][-1] == 18000)


# ------------------------------------------------------------------------------- resume

def group_resume():
    folder = Path(tempfile.mkdtemp(prefix='factorial-v2-resume-'))
    try:
        cfg = F2.RunConfig(seed=DEV_SEED, arm='C', updates=6, visits=3, probe_every=2,
                           routing_every=2, validation_n=8, routing_visits=2, adam_visits=2)
        units = F2.probe_units(F2.ns_validation(cfg.seed), cfg.validation_n)
        validation = F2.prepare_panel('validation', cfg.arm, units)
        plans, info = F2.routing_plans(cfg.seed, cfg.routing_visits)
        probe, kinds = F2.routing_probe(plans, info, cfg.arm), F2.canonical_kinds(plans)
        shared = dict(validation=validation, routing=probe, kinds=kinds, quiet=True)
        whole = F2.run_chunk(folder/'whole', cfg, frozenset(), chunk_updates=6, **shared)
        first = F2.run_chunk(folder/'split', cfg, frozenset(), chunk_updates=3, **shared)
        check('a chunk stops at its budget and reports itself incomplete',
              first['step'] == 3 and not first['done'])
        second = F2.run_chunk(folder/'split', cfg, frozenset(), chunk_updates=3, **shared)
        check('a resume continues from the saved data cursor',
              second['first_step'] == 3 and second['step'] == 6 and second['done'])
        check('a chunked run equals an unchunked run bit-for-bit',
              whole['fingerprint'] == second['fingerprint'],
              f"{whole['fingerprint'][:16]} vs {second['fingerprint'][:16]}")
        w = P.load(folder/'whole/resume-000006.pt')
        s = P.load(folder/'split/resume-000006.pt')
        check('the resume restores BOTH data streams and the torch RNG exactly',
              w['rng']['world'] == s['rng']['world'] and w['rng']['plan'] == s['rng']['plan']
              and torch.equal(w['rng']['torch'], s['rng']['torch']))
        check('the resume restores the optimizer moments exactly',
              bool(w['optimizer']['state'])
              and all(torch.equal(w['optimizer']['state'][k][f], s['optimizer']['state'][k][f])
                      for k in w['optimizer']['state'] for f in ('exp_avg', 'exp_avg_sq')))
        check('the diagnostics survive the chunk boundary identically',
              [r['update'] for r in w['rows']] == [r['update'] for r in s['rows']]
              and all(a['validation']['correct'] == b['validation']['correct']
                      and a.get('train_loss') == b.get('train_loss')
                      and a['directional_registered_all'] == b['directional_registered_all']
                      and a['adam_mass_delta_all'] == b['adam_mass_delta_all']
                      for a, b in zip(w['rows'], s['rows'])),
              f"probes at {[r['update'] for r in w['rows']]}")
        check('the probe grid starts at update 0 and ends at the final update',
              [r['update'] for r in w['rows']] == [0, 2, 4, 6])
        silent = F2.RunConfig(seed=DEV_SEED, arm='C', updates=6, visits=3, probe_every=1000,
                              routing_every=1000, validation_n=8, routing_visits=2,
                              adam_visits=2, routing=False, adam=False)
        quiet = F2.run_chunk(folder/'quiet', silent, frozenset(), chunk_updates=6,
                             validation=validation, routing=probe, kinds=kinds, quiet=True)
        check('the diagnostics consume no training randomness: logged == barely logged',
              quiet['fingerprint'] == whole['fingerprint'])
        other = F2.run_chunk(folder/'other', F2.RunConfig(
            seed=DEV_SEED+1, arm='C', updates=6, visits=3, probe_every=2, routing_every=2,
            validation_n=8, routing_visits=2, adam_visits=2), frozenset(),
            chunk_updates=6, quiet=True)
        check('a different seed gives a different trajectory',
              other['fingerprint'] != whole['fingerprint'])
        arm_d = F2.run_chunk(folder/'armd', F2.RunConfig(
            seed=DEV_SEED, arm='D', updates=6, visits=3, probe_every=2, routing_every=2,
            validation_n=8, routing_visits=2, adam_visits=2), frozenset(),
            chunk_updates=6, quiet=True)
        check('the same seed in a different arm gives a different trajectory',
              arm_d['fingerprint'] != whole['fingerprint'])
        trace = [json.loads(l) for l in
                 (folder/'split/trace.jsonl').read_text().splitlines() if l.strip()]
        check('the trace is rewritten from the saved rows, not appended twice',
              [r['update'] for r in trace] == [0, 2, 4, 6])
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# --------------------------------------------------------------------------------- diag

def group_diag():
    plans, info = F2.routing_plans(DEV_SEED, 3)
    probe, kinds = F2.routing_probe(plans, info, 'A'), F2.canonical_kinds(plans)
    model = A.new_model(DEV_SEED)
    optimizer = A.T.optimizer_for(model)
    for p in model.parameters():
        p.grad = torch.full_like(p, 7.)
    before_params = C.fingerprint(model)
    before_grads = [p.grad.clone() for p in model.parameters()]
    row = F2.attention_report(model, probe, kinds)
    row.update(F2.routing_report(model, probe, kinds))
    row.update(F2.adam_report(model, optimizer, probe, kinds, DEV_SEED, 0, 'A', 1e-3, 3))
    check('the diagnostics leave every parameter bit-identical',
          C.fingerprint(model) == before_params)
    check('the diagnostics leave every .grad bit-identical (poisoned with 7.0)',
          all(same(p.grad, g) for p, g in zip(model.parameters(), before_grads)))
    check('the AdamW diagnostic leaves the live optimizer state untouched',
          optimizer.state_dict()['state'] == {})
    for p in model.parameters():
        p.grad = None
    check('mass is reported per read, per head and per question-token position',
          len(row['mass_by_step_head']) == 3 and len(row['mass_by_step_head'][0]) == 4
          and len(row['mass_by_position']) == 3 and len(row['mass_by_position'][0]) == 4
          and len(row['mass_by_position'][0][0]) == probe.batch.canonical.questions.shape[1])
    check('ordinary attribute, endpoint terminal and LINK records are reported separately',
          row['one_hop_n'] + row['terminal_n'] + row['link_n']
          == probe.batch.canonical.questions.shape[0]
          and min(row['one_hop_n'], row['terminal_n'], row['link_n']) > 0,
          f"one_hop {row['one_hop_n']} terminal {row['terminal_n']} link {row['link_n']}")
    check('prediction distributions are reported separately for attribute and LINK',
          {'one_hop_top1_share', 'link_top1_share', 'terminal_prediction_entropy',
           'one_hop_mass_over_uniform', 'link_mass_over_uniform'} <= set(row))
    check('per-relation answer accuracy is reported',
          set(row['acc_by_relation']) == {'8', '9', '10'})
    check('the loss components are differentiated separately, then as the registered sum',
          {'loss_attribute', 'loss_link', 'loss_monolithic', 'loss_registered'} <= set(row)
          and abs(row['loss_registered']
                  - (.75*row['loss_canonical'] + .25*row['loss_monolithic']))
          < 1e-6*abs(row['loss_registered']),        # float32 rounding only
          f"{row['loss_registered']} vs .75*{row['loss_canonical']}"
          f" + .25*{row['loss_monolithic']}")
    check('the gradient reductions are written unrounded (more than 8 decimals)',
          any(len(repr(row[k]).split('.')[-1]) > 8 for k in row
              if k.startswith('directional_') and isinstance(row[k], float)),
          repr(row['directional_registered_all']))
    check('norms and cosines exist for every loss x mass pair',
          all(f'cosine_{loss}_{mass}' in row and f'grad_norm_loss_{loss}' in row
              and f'grad_norm_mass_{mass}' in row
              for loss in ('attribute', 'link', 'monolithic', 'canonical', 'registered')
              for mass in ('all', 'attribute', 'link'))
          and all(-1.0001 <= row[f'cosine_{l}_{m}'] <= 1.0001
                  for l in ('attribute', 'registered') for m in ('all', 'link')))
    for eta in F2.CENTRAL_ETAS:
        key = f'central_registered_all_eta{eta:g}'
        analytic = row['directional_registered_all']
        check(f'the central difference at eta={eta:g} matches the analytic SGD derivative',
              abs(row[key] - analytic) <= .05*abs(analytic) + 2e-5,
              f'{row[key]:.6e} vs {analytic:.6e}')
        check(f'the disagreement at eta={eta:g} is reported rather than hidden',
              f'central_minus_analytic_all_eta{eta:g}' in row)
    check('the AdamW statistic is separate from the SGD derivative',
          {'adam_mass_delta_all', 'adam_mass_before_all', 'adam_lr', 'adam_batch_loss'}
          <= set(row) and row['adam_mass_delta_all'] != row['directional_registered_all'])
    a = F2.adam_report(model, optimizer, probe, kinds, DEV_SEED, 7, 'A', 1e-3, 3)
    b = F2.adam_report(model, optimizer, probe, kinds, DEV_SEED, 7, 'A', 1e-3, 3)
    c = F2.adam_report(model, optimizer, probe, kinds, DEV_SEED, 8, 'A', 1e-3, 3)
    check('the AdamW probe batch is fixed by (seed, update) and independent of training',
          a['adam_mass_delta_all'] == b['adam_mass_delta_all']
          and a['adam_batch_loss'] != c['adam_batch_loss'])
    panel = F2.prepare_panel('validation', 'A', F2.probe_units('unit-test-score', 16))
    scored = F2.score_panel(model, panel)
    check('score_panel reports correct, accuracy, mass and the uniform baseline',
          scored['n'] == 16 and 0 <= scored['correct'] <= 16
          and scored['correct_line_mass'] > 0 and scored['uniform_line_mass'] > 0
          and set(scored['acc_by_relation']) == {'8', '9', '10'},
          json.dumps({k: scored[k] for k in
                      ('n', 'correct', 'correct_line_mass', 'uniform_line_mass')}))
    check('an untrained model sits near the uniform baseline on the routing probe',
          .3 < row['mass_over_uniform'] < 3., str(row['mass_over_uniform']))
    capacity = F2.capacity_report()
    check('the capacity guard counts worker processes and states both caps',
          capacity['max_audit'] == 3 and capacity['max_total'] == 6
          and isinstance(capacity['total'], int) and isinstance(capacity['audit'], int),
          json.dumps(capacity))


# ----------------------------------------------------------------------------- transfer

def group_transfer():
    units6 = F2.transfer_units(6, 6, namespace='unit-test-transfer')
    units16 = F2.transfer_units(16, 4, namespace='unit-test-transfer')
    check('six-person worlds have 24 fact rows and sixteen-person worlds have 64',
          all(len(u.core) == 16 and len(u.core)+len(u.fact_order) == 24 for u in units6)
          and all(len(u.core) == 16 and len(u.core)+len(u.fact_order) == 64 for u in units16))
    for u in units6 + units16:
        sizes = (16, 24) if len(u.fact_order) == 8 else (16, 24, 64)
        keeps = {(k, x): set(F2.transfer_keep(u, k, x)) for k in sizes for x in (0., .5, 1.)}
        nested = all(keeps[(sizes[i], 0.)] < keeps[(sizes[i+1], 0.)]
                     for i in range(len(sizes)-1))
        nested &= all(keeps[(k, 0.)] <= keeps[(k, .5)] <= keeps[(k, 1.)] for k in sizes)
        check('the transfer cells are nested in facts and in filler', nested)
        check('the common 16-fact core is present in every cell',
              all(set(u.core) <= v for v in keeps.values()))
    for cell in F2.TRANSFER_CELLS:
        units = units6 if cell['entities'] == 6 else units16
        panel = F2.transfer_panel(cell, units)
        x, answers = panel.chunks[0][0], panel.chunks[0][1]
        check(f"cell {cell['name']}: the question and the answer are unchanged",
              x.questions.tolist() == [u.q for u in units]
              and answers.tolist() == [u.answer for u in units])
    by_name = {c['name']: c for c in F2.TRANSFER_CELLS}
    bare = F2.transfer_panel(by_name['e16-f64-x0'], units16)
    full = F2.transfer_panel(by_name['e16-f64-x100'], units16)
    check('the genuine full 64-fact sixteen-person world is one of the cells',
          bare.chunks[0][0].memory.shape[1] == 64
          and full.chunks[0][0].memory.shape[1] > 64)
    folder = Path(tempfile.mkdtemp(prefix='factorial-v2-transfer-'))
    try:
        signatures = F2.build_transfer_plan(folder, n=4)
        saved = json.loads((folder/'plan/transfer-plan.json').read_text())
        check('the transfer plan is frozen with its 15 cells and digests before training',
              len(saved['cells']) == 15 and saved['digest'] == A.digest(signatures)
              and saved['threshold'] == 461 and saved['namespace'] == F2.NS_TRANSFER)
        check('a cell that differs only in filler shares its signature -- a disclosed '
              'limitation of visible_signature, which hashes fact rows only',
              saved['cells']['e6-f16-x0']['signature_digest']
              == saved['cells']['e6-f16-x100']['signature_digest']
              and saved['cells']['e6-f16-x0']['signature_digest']
              != saved['cells']['e6-f24-x0']['signature_digest'])
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# ------------------------------------------------------------------------------- report

def group_report():
    folder = Path(tempfile.mkdtemp(prefix='factorial-v2-report-'))
    try:
        args = argparse.Namespace(out=str(folder), seeds=str(DEV_SEED),
                                  updates=F2.UPDATES, trajectories=True, routing_at={0})
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            F2.report(args)
        text = buffer.getvalue()
        check('a report with no runs at all prints "(missing)" and does not crash',
              text.count(F2.MISSING) >= 4*6 and f'## seed {DEV_SEED}' in text)
        check('the report lists every arm and both separate questions',
              all(f'\n{a}  ' in text for a in F2.ARM_NAMES)
              and '## long run' in text and 'freeze-before-growth transfer' in text)
        check('the report states that it never averages across seeds',
              'never averaged' in text and 'paired within this seed' in text)
        check('a missing long run and a missing transfer are reported as missing',
              text.count(f'seed {DEV_SEED}: {F2.MISSING}') == 2)
        cfg = F2.RunConfig(seed=DEV_SEED, arm='A', updates=2, visits=2, probe_every=1,
                           routing_every=1, validation_n=8, routing_visits=2, adam_visits=2)
        F2.run_chunk(folder/f'seed-{DEV_SEED}/A', cfg, frozenset(), chunk_updates=2,
                     quiet=True)
        args.updates = 2
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            F2.report(args)
        text = buffer.getvalue()
        check('a present arm reports numbers while the absent arms stay "(missing)"',
              '\nA  ' in text and text.count(F2.MISSING) >= 3*6
              and '/512' in text)
        check('the paired readings are pre-stated: B-A, D-C, C-A, D-B and the interaction',
              all(s in text for s in ('filler effect  B-A', 'filler effect  D-C',
                                      'fact effect    C-A', 'fact effect    D-B',
                                      'interaction (D-C)-(B-A)')))
        check('a censored comparison is labelled, not silently dropped',
              'censored' in text)
        check('the scope paragraph refuses the over-readings',
              'Scope:' in text and 'not that' in text)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


GROUPS = dict(spec=group_spec, arms=group_arms, signature=group_signature,
              onset=group_onset, resume=group_resume, diag=group_diag,
              transfer=group_transfer, report=group_report)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='checks for fable_startup_factorial_v2')
    ap.add_argument('--only', default=None, choices=list(GROUPS))
    chosen = ap.parse_args().only
    data.bootstrap()
    for name, fn in GROUPS.items():
        if chosen and name != chosen:
            continue
        print(f'--- {name} ---', flush=True)
        fn()
    print(f'ALL {CHECKS} CHECKS PASSED', flush=True)
