"""Checks for scripts/fable_baseline_transformer_v2.py.

Plain script.  Run it; it prints one line per check and ends with
`ALL N CHECKS PASSED` or raises.  Nothing here runs a registered experiment or a
registered seed; every training loop is <= 5 updates on a development seed, and
everything written lands in a temporary directory.

The load-bearing ones:

  CHECK GROUP "operator rescale"  -- the rescale applied to the baseline IS the
      function object `astra_canonical_operator` calls on every canonical operator,
      the two init arms of one seed share their random DRAWS exactly, and nothing but
      `nn.Linear.weight` moves.
  CHECK GROUP "v1 parity"         -- with `--init default --evidence-aux 0` and v1's
      namespace, v2 reproduces v1 BITWISE after 5 updates, and the v2 loss TENSOR is
      bitwise equal to v1's for evidence_aux in {0, 0.5}.
  CHECK GROUP "per-role metrics"  -- a prediction that gets END and every intermediate
      person right but every terminal answer wrong scores high aggregate token
      accuracy and ZERO terminal accuracy.  That is the failure mode the audit found
      in v1's reporting, and this is the check that it can no longer hide.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_baseline_transformer as B                                      # noqa: E402
import fable_baseline_transformer_v2 as B2                                  # noqa: E402
import astra_canonical_operator as AOP                                      # noqa: E402

V3 = B.V3
torch = B.torch
nn = B.nn
F = B.F

PANELS = ROOT / 'artifacts' / 'fable-dispatcher-v3-20260920' / 'panels'
DEV_SEED = 990120

CHECKS = 0


def check(label, condition, detail=''):
    global CHECKS
    if not condition:
        raise AssertionError(f'{label} FAILED {detail}')
    CHECKS += 1
    print(f'  ok  {label}{(" -- " + detail) if detail else ""}')


def banner(text):
    print(f'\n{text}')


def tiny_batch(seed=DEV_SEED, worlds=2, questions=2, support=False):
    rng = random.Random(f'{B2.OVERFIT_NAMESPACE}:{seed}')
    stories, items = B.training_items(rng, worlds, B2.REGISTERED_PEOPLE, B.TRAIN_HOPS,
                                      frozenset(), questions, support=support)
    return B.pack_batch(stories, items, 'steps', support=support), items


# --------------------------------------------------------------------------- rescale


def check_rescale():
    banner('operator rescale -- the same function, the same draws')
    check('the rescale used is the operator\'s own function object',
          B2.RESCALE is AOP.I.rescale and B2.RESCALE_QUALNAME ==
          'premonition_token_initialization_probe.rescale',
          B2.RESCALE_QUALNAME)

    default = B2.build_model(1200, 'default')
    rescaled = B2.build_model(1200, 'operator-rescale')
    again = B2.build_model(1200, 'operator-rescale')
    check('operator-rescale is deterministic at a fixed seed',
          B2.fingerprint(rescaled) == B2.fingerprint(again))

    linears = dict(B2.linear_weights(default))
    rlinears = dict(B2.linear_weights(rescaled))
    check('the baseline has the expected Linear modules',
          len(linears) == B2.LAYERS * 6 and set(linears) == set(rlinears),
          f'{len(linears)} Linear modules')

    exact, signs, stds = True, True, []
    for name, module in linears.items():
        want = module.weight * B2.rescale_factor(module.in_features)
        got = rlinears[name].weight
        exact &= bool(torch.equal(got, want))
        signs &= bool(torch.equal(got.sign(), module.weight.sign()))
        stds.append((float(got.std()), 1 / math.sqrt(3 * module.in_features)))
    check('every Linear weight is EXACTLY the v1 draw x 1/(sqrt(3*fan_in)*0.02)', exact)
    check('the rescaling preserves every draw\'s sign, i.e. the draws are unchanged', signs)
    check('the rescaled standard deviations match 1/sqrt(3*fan_in)',
          all(abs(got - want) / want < .12 for got, want in stds),
          ', '.join(f'{got:.4f} vs {want:.4f}' for got, want in stds[:3]) + ', ...')
    check('the rescaled std is ~4x the v1 std 0.02 at fan-in 48',
          3.5 < (1 / math.sqrt(3 * 48)) / .02 < 4.5,
          f'{(1 / math.sqrt(3 * 48)) / .02:.2f}x')

    moved, still = [], []
    ds, rs = default.state_dict(), rescaled.state_dict()
    linear_weight_names = {f'{name}.weight' for name in linears}
    for key in sorted(ds):
        (moved if not torch.equal(ds[key], rs[key]) else still).append(key)
    check('ONLY Linear weights move: no embedding, no bias, no LayerNorm, no output bias',
          set(moved) == linear_weight_names,
          f'{len(moved)} moved, {len(still)} unchanged')
    check('every bias is zero in both arms, so rescaling biases would be a no-op anyway',
          all(bool(module.bias.eq(0).all()) for module in linears.values()))

    parameters = default.parameters_count()
    check('the parameter count is unchanged by the init arm',
          parameters == rescaled.parameters_count() == B.BaselineTransformer().parameters_count(),
          f'{parameters} parameters')


def check_arms():
    banner('the 2x2 the draft registers')
    check('the arm table is exactly the draft\'s',
          B2.ARMS == {'I0-H0': ('default', 0.0), 'I0-H1': ('default', 0.5),
                      'I1-H0': ('operator-rescale', 0.0), 'I1-H1': ('operator-rescale', 0.5)})
    check('I1-H1 is nominated as primary in advance', B2.PRIMARY_ARM == 'I1-H1')
    check('the registered seeds are the draft\'s', B2.REGISTERED_SEEDS == (1200, 1201, 1202))
    check('the world RNG namespace is the draft\'s', B2.TRAIN_NAMESPACE == 'astra-baseline-v2-fit')
    check('the gate thresholds are the draft\'s',
          B2.FIT_GATE == {'fit-k1-prac': 487, 'fit-k1-held': 487,
                          'fit-k2-prac': 461, 'fit-k3-prac': 461})
    check('the registered budget is the draft\'s 6,000 x (16 worlds x 4 questions), 6 people',
          (B2.REGISTERED_UPDATES, B2.REGISTERED_VISITS, B2.REGISTERED_QUESTIONS_PER_WORLD,
           B2.REGISTERED_PEOPLE) == (6000, 16, 4, 6))
    check('v2 exposes no new position/depth/curriculum knob beyond v1\'s',
          B2.REGISTERED_POSITIONS == 'line' and
          not any(name.startswith('sinusoid') or 'position_function' in name
                  for name in dir(B2)),
          'sinusoidal / shared position functions are the draft\'s SEPARATE later diagnostic')


def check_paired_stream():
    banner('the four arms see identical worlds, questions, targets and ordering')
    seeds = {}
    for label, aux in (('hint-off', 0.), ('hint-on', .5)):
        rng = random.Random(f'{B2.TRAIN_NAMESPACE}:1200')
        drawn = []
        for _ in range(3):
            stories, items = B.training_items(rng, 4, 6, B.TRAIN_HOPS, frozenset(), 4,
                                              support=bool(aux))
            batch = B.pack_batch(stories, items, 'steps', support=bool(aux))
            drawn.append((batch.story.flat.clone(), batch.seq.clone(), batch.target.clone(),
                          batch.owner.clone(), [it['hops'] for it in items]))
        seeds[label] = drawn
    same = all(torch.equal(a[i], b[i]) for a, b in zip(seeds['hint-off'], seeds['hint-on'])
               for i in range(4)) and \
        all(a[4] == b[4] for a, b in zip(seeds['hint-off'], seeds['hint-on']))
    check('turning the supporting-line hint on does not perturb the data stream', same,
          'so an init x hint cell pair differs only by init and hint, never by data')

    other = random.Random(f'{B2.TRAIN_NAMESPACE}:1201')
    stories, items = B.training_items(other, 4, 6, B.TRAIN_HOPS, frozenset(), 4)
    batch = B.pack_batch(stories, items, 'steps')
    check('a different registered seed really is a different stream',
          not torch.equal(batch.seq, seeds['hint-off'][0][1]))


# --------------------------------------------------------------------------- roles


def check_roles():
    banner('per-role metrics -- token accuracy can no longer hide a lookup failure')
    batch, items = tiny_batch(worlds=4, questions=4)
    roles = B2.role_grid(batch)
    hops = B2.hops_vector(items)
    scored = batch.target.ne(-100)
    check('every scored position has a role and every unscored one has none',
          bool(roles.ne(0).eq(scored).all()))

    ok = True
    for i, out in enumerate(batch.outputs):
        base = int(batch.q_len[i]) - 1
        want = [B2.ROLE_INTERMEDIATE] * (len(out) - 2) + [B2.ROLE_TERMINAL, B2.ROLE_END]
        ok &= [int(roles[i, base + j]) for j in range(len(out))] == want
        ok &= int(batch.target[i, base + len(out) - 2]) == int(items[i]['answer'])
        ok &= int(batch.target[i, base + len(out) - 1]) == B.END
    check('roles are intermediate* -> terminal -> END, and the terminal target IS the answer', ok)
    check('a 1-hop question has no intermediate role',
          all(int(roles[i].eq(B2.ROLE_INTERMEDIATE).sum()) == items[i]['hops'] - 1
              for i in range(len(items))))

    vocab = B.VOCAB
    perfect = F.one_hot(batch.target.clamp(min=0), vocab).float() * 30.
    counts = B2.role_counts(perfect, batch, roles, hops)
    check('an oracle prediction scores every role at 1.0',
          all(h == t for h, t in counts.values() if t),
          json.dumps({k: v for k, v in counts.items()}))

    # END and every intermediate person right, every terminal answer wrong
    sabotage = batch.target.clone()
    sabotage[roles.eq(B2.ROLE_TERMINAL)] = (sabotage[roles.eq(B2.ROLE_TERMINAL)] + 1) % vocab
    logits = F.one_hot(sabotage.clamp(min=0), vocab).float() * 30.
    bad = B2.role_counts(logits, batch, roles, hops)
    token_ratio = bad['token'][0] / bad['token'][1]
    check('a pure lookup failure still scores high AGGREGATE token accuracy',
          token_ratio > .5, f'token accuracy {token_ratio:.3f}')
    check('...but terminal-answer accuracy is 0 and one-hop-answer accuracy is 0',
          bad['terminal'][0] == 0 and bad['one_hop_terminal'][0] == 0 and
          bad['multi_hop_terminal'][0] == 0)
    check('...while END and intermediate-person accuracy stay at 1.0',
          bad['end'][0] == bad['end'][1] and bad['intermediate'][0] == bad['intermediate'][1],
          'exactly the v1 reporting artefact the audit identified')
    check('exact sequence accuracy is 0 under that sabotage',
          bad['sequence'][0] == 0 and bad['one_hop_sequence'][0] == 0)
    check('the one-hop terminal stratum is the 1-hop subset of the terminal stratum',
          bad['one_hop_terminal'][1] + bad['multi_hop_terminal'][1] == bad['terminal'][1] ==
          len(items) and bad['one_hop_terminal'][1] == sum(1 for it in items if it['hops'] == 1))


# --------------------------------------------------------------------------- v1 parity


def check_loss_parity():
    banner('v1 parity -- the differentiable graph is v1\'s, op for op')
    for aux_weight in (0., .5):
        batch, items = tiny_batch(worlds=3, questions=3, support=bool(aux_weight))
        model = B2.build_model(DEV_SEED, 'default')
        want_loss, want_token, want_row, want_aux = B.teacher_forced_loss(
            model, batch, evidence_aux=aux_weight)
        got_loss, got_aux, counts = B2.teacher_forced_loss_v2(
            model, batch, evidence_aux=aux_weight, roles=B2.role_grid(batch),
            hops=B2.hops_vector(items))
        check(f'the v2 loss is BITWISE equal to v1\'s at evidence_aux={aux_weight}',
              torch.equal(got_loss, want_loss) and got_aux == want_aux,
              f'{float(got_loss):.12f}')
        check(f'the v2 aggregate token/sequence counts match v1\'s ratios at '
              f'evidence_aux={aux_weight}',
              abs(counts['token'][0] / counts['token'][1] - want_token) < 1e-9 and
              abs(counts['sequence'][0] / counts['sequence'][1] - want_row) < 1e-9)
        if aux_weight:
            check('the hint really is added (the losses differ from the hint-free loss)',
                  float(got_loss) != float(B.teacher_forced_loss(model, batch)[0]))


def check_bitwise_run_parity():
    banner('v1 parity -- 5 updates, every parameter, bitwise')
    with tempfile.TemporaryDirectory() as folder:
        one, two = Path(folder) / 'v1', Path(folder) / 'v2'
        B.main(['train', '--seed', str(DEV_SEED), '--updates', '5', '--visits', '4',
                '--out', str(one), '--log-every', '1'])
        B2.main(['train', '--seed', str(DEV_SEED), '--updates', '5', '--visits', '4',
                 '--init', 'default', '--evidence-aux', '0',
                 '--train-namespace', B.TRAIN_NAMESPACE, '--out', str(two), '--log-every', '1'])
        a = torch.load(one / 'baseline.pt', map_location='cpu', weights_only=False)
        b = torch.load(two / 'baseline.pt', map_location='cpu', weights_only=False)
        keys = sorted(a['state_dict'])
        check('the v1 and v2 checkpoints have the same parameter set',
              keys == sorted(b['state_dict']))
        check('every parameter is BITWISE identical after 5 updates',
              all(torch.equal(a['state_dict'][k], b['state_dict'][k]) for k in keys),
              f'{len(keys)} tensors')
        v1log = [json.loads(line) for line in (one / 'train_log.jsonl').read_text().split('\n')
                 if line]
        v2log = [json.loads(line) for line in (two / 'train_log.jsonl').read_text().split('\n')
                 if line]
        check('every logged loss is bitwise identical',
              [r['loss'] for r in v1log] == [r['loss'] for r in v2log],
              f'{len(v1log)} log lines')
        check('v2 additionally logs gradient norm and the four per-role accuracies',
              all(set(('grad_norm', 'end_accuracy', 'intermediate_accuracy', 'terminal_accuracy',
                       'one_hop_terminal_accuracy', 'sequence_accuracy')) <= set(r)
                  for r in v2log))
        record = json.loads((two / 'training.json').read_text())
        check('the v2 record freezes the starting states and source hashes',
              all(record.get(k) for k in ('initial_weight_fingerprint',
                                          'data_rng_initial_state_sha256',
                                          'torch_rng_after_init_sha256', 'source_sha256',
                                          'v1_source_sha256', 'v3_source_sha256')))


def check_init_arms_end_to_end():
    banner('the two init arms of one seed differ ONLY by the rescaling')
    with tempfile.TemporaryDirectory() as folder:
        runs = {}
        for init in B2.INIT_CHOICES:
            out = Path(folder) / init
            B2.main(['train', '--seed', str(DEV_SEED), '--updates', '2', '--visits', '2',
                     '--init', init, '--evidence-aux', '0', '--out', str(out), '--log-every', '1'])
            runs[init] = json.loads((out / 'training.json').read_text())
        check('the two arms record different initial weight fingerprints',
              runs['default']['initial_weight_fingerprint'] !=
              runs['operator-rescale']['initial_weight_fingerprint'])
        check('the two arms record the SAME data RNG starting state',
              runs['default']['data_rng_initial_state_sha256'] ==
              runs['operator-rescale']['data_rng_initial_state_sha256'])
        check('the two arms record the same torch RNG state after construction',
              runs['default']['torch_rng_after_init_sha256'] ==
              runs['operator-rescale']['torch_rng_after_init_sha256'],
              'so the DRAWS are identical and only the scale differs')
        check('the recorded rescale function is the operator\'s',
              runs['operator-rescale']['rescale_is_operator_function'] is True and
              runs['operator-rescale']['rescale_function'] ==
              'premonition_token_initialization_probe.rescale')
        check('--arm resolves to the draft\'s cells',
              B2.resolve_arm(type('n', (), dict(arm='I1-H1', init=None, evidence_aux=None))()) ==
              ('I1-H1', 'operator-rescale', 0.5))


def check_exclusions():
    banner('frozen exclusion union')
    rng = random.Random(f'{B2.TRAIN_NAMESPACE}:1200')
    stories, items = B.training_items(rng, 1, 6, B.TRAIN_HOPS, frozenset(), 1)
    signature = B2.A.visible_signature(stories[0], items[0]['question'])
    raised = False
    try:
        B.training_items(random.Random(f'{B2.TRAIN_NAMESPACE}:1200'), 1, 6, B.TRAIN_HOPS,
                         frozenset({signature}), 1)
    except RuntimeError as exc:
        raised = 'overlap' in str(exc)
    check('a training draw whose semantics are in the exclusion union INVALIDATES the run',
          raised, 'never silently skipped, so the frozen RNG stream cannot shift')
    with tempfile.TemporaryDirectory() as folder:
        one = Path(folder) / 'a.json'
        two = Path(folder) / 'b.json'
        one.write_text(json.dumps(['x', 'y']))
        two.write_text(json.dumps(['y', 'z']))
        union, record = B2.exclusion_union([str(one), str(two)])
        check('the union de-duplicates and records every source file and its sha256',
              union == frozenset({'x', 'y', 'z'}) and record['count'] == 3 and
              len(record['sources']) == 2 and record['sources'][1]['new'] == 1 and
              all(len(s['sha256']) == 64 for s in record['sources']))
        check('a panel DIRECTORY resolves to its forbidden-semantics.json',
              B2.read_exclusion(PANELS)[0].name == 'forbidden-semantics.json')


# --------------------------------------------------------------------------- panels


def check_fit_panels():
    banner('development-fit and confirmation panels')
    with tempfile.TemporaryDirectory() as folder:
        fit_dir = Path(folder) / 'fit'
        B2.build_fit_panels(fit_dir, B2.FIT_PANEL_NAMESPACE, 8, [str(PANELS)])
        manifest, cells, forbidden = B2.load_fit_panels(fit_dir)
        check('the fit panel has the draft\'s four cells',
              manifest['cell_order'] == list(B2.FIT_CELL_ORDER) and
              set(manifest['cells']) == set(cells) == set(B2.FIT_CELL_ORDER))
        check('every unit is a six-person full story with a 1/2/3-hop question',
              all(len(cells[c]['units']) == 8 and
                  all(u['a']['hops'] == B2.FIT_CELLS[c]['hops'] and
                      len(u['a']['people']) == B2.FIT_CELLS[c]['hops'] and
                      sum(1 for row in u['a']['memory'] if row) == u['a']['where']
                      for u in cells[c]['units'])
                  for c in B2.FIT_CELL_ORDER))
        prac = [u['terminal'] for u in cells['fit-k1-prac']['units']]
        check('the one-hop practised cell has EQUAL relation strata',
              sorted(prac) == [8] * 4 + [9] * 4, f'{sorted(prac)}')
        check('the one-hop held-out cell is relation 10 throughout',
              all(u['terminal'] == B.HELDOUT_REL for u in cells['fit-k1-held']['units']))
        check('relation 10 is never a multi-hop terminal, and multi-hop chains are distinct',
              all(u['terminal'] in B.PRACTISED_RELS and u['a']['distinct']
                  for c in ('fit-k2-prac', 'fit-k3-prac') for u in cells[c]['units']))
        signatures = [B2.A.visible_signature(
            [r for i, r in enumerate(u['a']['memory']) if r and i < u['a']['where']],
            u['a']['question']) for c in B2.FIT_CELL_ORDER for u in cells[c]['units']]
        check('every unit signature is unique across all four cells',
              len(set(signatures)) == len(signatures) == 32)
        _, v3forbidden = B2.read_exclusion(PANELS)
        check('no fit-panel signature overlaps the frozen v3 panels',
              not (set(signatures) & set(v3forbidden)))
        check('the exclusion file the panel publishes is exactly those signatures',
              forbidden == frozenset(signatures))
        check('the manifest records the rejection rule, the attempt ceiling and the gate',
              manifest['panel_attempts'] == 256 and manifest['gate'] == B2.FIT_GATE and
              'No model, no correctness' in manifest['rejection_rule'])

        replay = Path(folder) / 'fit-replay'
        B2.build_fit_panels(replay, B2.FIT_PANEL_NAMESPACE, 8, [str(PANELS)])
        check('the panel build is exactly replayable from (namespace, cell, index, attempt)',
              all(json.loads((fit_dir / f'{c}.json').read_text())['units'] ==
                  json.loads((replay / f'{c}.json').read_text())['units']
                  for c in B2.FIT_CELL_ORDER))

        confirm = Path(folder) / 'confirm'
        B2.build_fit_panels(confirm, B2.CONFIRM_PANEL_NAMESPACE, 8, [str(PANELS), str(fit_dir)])
        _, _, confirm_signatures = B2.load_fit_panels(confirm)
        check('the untouched confirmation panel is disjoint from the development-fit panel',
              not (confirm_signatures & forbidden) and len(confirm_signatures) == 32)
        return


def check_gate():
    banner('the lookup prerequisite, reported as an explicit per-seed gate')
    def cells(a1, s1, a2, s2, a3, s3, a4, s4):
        values = [(a1, s1), (a2, s2), (a3, s3), (a4, s4)]
        return {c: dict(n=512, answers=a, strict=s)
                for c, (a, s) in zip(B2.FIT_CELL_ORDER, values)}

    full = B2.gate_report(cells(512, 512, 512, 512, 512, 512, 512, 512))
    check('a perfect seed clears both gates', full['one_hop_lookup_gate'] and full['fit_gate'])
    edge = B2.gate_report(cells(487, 487, 487, 487, 461, 461, 461, 461))
    check('exactly the draft\'s thresholds pass', edge['fit_gate'])
    for index, label in enumerate(('answers', 'strict')):
        args = [487, 487, 487, 487, 461, 461, 461, 461]
        args[index] -= 1
        short = B2.gate_report(cells(*args))
        check(f'one-hop {label} at threshold-1 FAILS the lookup gate',
              not short['one_hop_lookup_gate'] and not short['fit_gate'] and
              not short['composition_claims_licensed'])
    lookup_only = B2.gate_report(cells(512, 512, 512, 512, 460, 512, 512, 512))
    check('lookup can pass while composition fails -- and only then is a composition claim '
          'licensed',
          lookup_only['one_hop_lookup_gate'] and not lookup_only['fit_gate'] and
          lookup_only['composition_claims_licensed'] and
          not lookup_only['composition_cells_pass'])
    broken = B2.gate_report(cells(460, 512, 512, 512, 512, 512, 512, 512))
    check('a seed that cannot do ordinary lookup does NOT license a composition claim',
          not broken['composition_claims_licensed'],
          'the audit\'s requirement, as a reported boolean')


def check_fit_end_to_end():
    banner('the fit command runs end to end on an almost-untrained model')
    with tempfile.TemporaryDirectory() as folder:
        fit_dir = Path(folder) / 'fit'
        B2.build_fit_panels(fit_dir, B2.FIT_PANEL_NAMESPACE, 4, [str(PANELS)])
        run = Path(folder) / 'run'
        B2.main(['train', '--arm', 'I1-H1', '--seed', str(DEV_SEED), '--updates', '2',
                 '--visits', '2', '--exclude', str(PANELS), '--exclude', str(fit_dir),
                 '--out', str(run), '--log-every', '1'])
        B2.main(['fit', '--run', str(run), '--panels', str(fit_dir), '--block', '4'])
        report = json.loads((run / 'fit' / 'fit.json').read_text())
        check('the fit report names the arm, seed, checkpoint hash and panel namespace',
              report['arm'] == 'I1-H1' and report['seed'] == DEV_SEED and
              len(report['checkpoint_sha256']) == 64 and
              report['panel_namespace'] == B2.FIT_PANEL_NAMESPACE)
        check('every cell is scored with greedy answers, strict paths and no-END counts',
              all(set(('answers', 'strict', 'no_end', 'need')) <= set(report['cells'][c])
                  for c in B2.FIT_CELL_ORDER))
        check('per-role teacher-forced metrics are reported per cell',
              all(set(f'{k}_accuracy' for k in B2.ROLE_KEYS) <= set(report['teacher_forced'][c])
                  for c in B2.FIT_CELL_ORDER))
        check('the equal-relation one-hop strata are reported',
              sorted(report['one_hop_relation_strata']['fit-k1-prac']) == ['8', '9'] and
              sorted(report['one_hop_relation_strata']['fit-k1-held']) == ['10'])
        check('an untrained model does not clear the gate',
              report['gate']['one_hop_lookup_gate'] is False and
              report['gate']['fit_gate'] is False)
        check('inference cost is recorded', report['inference_flops'] > 0)
        refused = False
        try:
            B2.main(['fit', '--run', str(run), '--panels', str(fit_dir), '--block', '4'])
        except (FileExistsError, SystemExit):
            refused = True
        check('a second fit into the same directory is refused', refused)

        confirm = Path(folder) / 'confirm'
        B2.build_fit_panels(confirm, B2.CONFIRM_PANEL_NAMESPACE, 4, [str(PANELS), str(fit_dir)])
        sealed = False
        try:
            B2.main(['fit', '--run', str(run), '--panels', str(confirm), '--block', '4'])
        except SystemExit:
            sealed = True
        check('the confirmation panel is refused without the explicit --confirmation flag',
              sealed, 'only a fit-qualified configuration proceeds')


def check_overfit():
    banner('the tiny-fixed-batch overfit check')
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / 'overfit'
        B2.main(['overfit', '--out', str(out), '--worlds', '2', '--questions-per-world', '2',
                 '--max-updates', '3', '--seed', str(DEV_SEED), '--log-every', '1'])
        report = json.loads((out / 'overfit.json').read_text())
        check('both inits are run on the SAME fixed batch',
              [r['init'] for r in report['results']] == list(B2.INIT_CHOICES) and
              report['questions'] == 4)
        check('each init reports whether it memorised and after how many updates',
              all(set(('memorised', 'updates_to_memorise', 'updates_applied', 'final')) <= set(r)
                  for r in report['results']))
        check('the report states that memorisation is not generalization',
              'not evidence of generalization' in report['interpretation'])
        refused = False
        try:
            B2.main(['overfit', '--out', str(Path(folder) / 'x'), '--seed', '1200'])
        except SystemExit:
            refused = True
        check('a registered seed is refused for the development overfit check', refused)


def main():
    check_rescale()
    check_arms()
    check_paired_stream()
    check_roles()
    check_loss_parity()
    check_bitwise_run_parity()
    check_init_arms_end_to_end()
    check_exclusions()
    check_fit_panels()
    check_gate()
    check_fit_end_to_end()
    check_overfit()
    print(f'\nALL {CHECKS} CHECKS PASSED')


if __name__ == '__main__':
    B.configure()
    main()
