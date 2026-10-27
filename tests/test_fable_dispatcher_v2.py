"""Checks for the dispatcher v2 additions.  Run as a plain script:

    PY -B tests/test_fable_dispatcher_v2.py

Prints one line per check and finally `ALL N CHECKS PASSED`.  No registered training,
no GPU, no network; every temporary artefact goes to a caller-supplied --scratch
directory (default: a fresh directory under the system temp area).  Nothing under
artifacts/ is read or written.
"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import fable_dispatcher as D                                                # noqa: E402
import fable_dispatcher_v2 as V2                                           # noqa: E402

torch = D.torch
CHECKS = []


def check(name):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap


def ok(condition, message):
    if not condition:
        raise AssertionError(message)


# --------------------------------------------------------------------------- fixtures


def sample_units(indices=(3,)):
    units = []
    for index in indices:
        units += [D.make_unit('d1', index), D.make_unit('d2', index), D.make_unit('d4', index)]
    return units


def fixture(indices=(3,), side='a'):
    """units, (unit, side) pairs, oracle table, question tokens and true hop counts."""
    units = sample_units(indices)
    pairs = [(unit, side) for unit in units]
    table = V2.operator_table(D.OracleOperator(), pairs)
    questions = [unit[side]['question'] for unit in units]
    hops = torch.tensor([len(unit[side]['chain']) for unit in units], dtype=torch.long)
    return units, pairs, table, questions, hops


def hand_policy(kind, hops, width, left=0):
    """Reference policies written by hand: `good` is correct; the others break exactly
    one component.  None of them reads a story, an answer or a hop count it was not
    handed, and the `hops` they use is the same evaluator-only truth the interventions use."""
    def policy(step, tokens, results, n_results):
        batch = tokens.shape[0]
        here = torch.full((batch,), step, dtype=torch.long)
        subject = torch.where(n_results > 0, width + n_results - 1,
                              torch.full((batch,), left + 1, dtype=torch.long))
        operation = left + 2 + torch.minimum(here, hops - 1)
        stop = (here >= hops - 1).long()
        if kind == 'bad_subject':
            subject = torch.full((batch,), left + 1, dtype=torch.long)
        if kind == 'bad_op':
            operation = torch.full((batch,), left + 2, dtype=torch.long)
        if kind == 'bad_stop':
            stop = torch.zeros(batch, dtype=torch.long)
        if kind == 'loop':
            # always a legal call (the question's own entity and first operation) and never
            # a stop, so the episode runs into the four-call cap instead of failing early
            subject = torch.full((batch,), left + 1, dtype=torch.long)
            operation = torch.full((batch,), left + 2, dtype=torch.long)
            stop = torch.zeros(batch, dtype=torch.long)
        return subject, operation, stop
    return policy


def run(model, pairs, tokens, present, table, policy=None):
    with torch.no_grad():
        return D.rollout(model, tokens, present, table, torch.arange(len(pairs)),
                         mode='greedy', policy=policy)


def train_argv(script_out, call_cost=None, seed=900201, updates=20):
    argv = ['train', '--arm', 'rl', '--operator', 'oracle', '--seed', str(seed),
            '--updates', str(updates), '--out', str(script_out), '--visits', '4', '--k', '4',
            '--time-cap', '120']
    if call_cost is not None:
        argv += ['--call-cost', str(call_cost)]
    return argv


# --------------------------------------------------------------------------- checks


@check('v1 `pick` already honours a per-component None; an intervention leaves the rest free')
def test_per_component_none():
    units, pairs, table, questions, hops = fixture()
    tokens, present = D.pad_questions(questions)
    torch.manual_seed(5)
    model = D.Dispatcher()
    free = run(model, pairs, tokens, present, table)
    forced_op = run(model, pairs, tokens, present, table,
                    V2.intervention_policy('force_operation', hops, tokens.shape[1]))
    forced_subject = run(model, pairs, tokens, present, table,
                         V2.intervention_policy('force_subject', hops, tokens.shape[1]))
    # the subject head is consulted before the operation head, so forcing the operation
    # cannot move the step-1 subject pointer; and vice versa the operation pointer is a
    # function of (state, chosen subject key), so forcing the subject may move it -- what
    # must hold is that a None component is never replaced by anything of ours.
    ok([p[0][0] for p in free.pointers] == [p[0][0] for p in forced_op.pointers],
       'force_operation moved the free subject pointer at step 1')
    ok(all(p for p in forced_subject.pointers), 'no pointers were recorded')
    for kind in V2.INTERVENTIONS:
        if kind == 'none':
            continue
        policy = V2.intervention_policy(kind, hops, tokens.shape[1])
        triple = policy(0, tokens, torch.zeros(len(pairs), D.MAX_CALLS, dtype=torch.long),
                        torch.zeros(len(pairs), dtype=torch.long))
        wanted = {'force_operation': (True, False, False), 'force_subject': (False, True, False),
                  'force_stop': (False, False, True),
                  'force_operation+subject': (True, True, False)}[kind]
        got = (triple[1] is not None, triple[0] is not None, triple[2] is not None)
        ok(got == wanted, f'{kind} forced {got}, expected (op, subject, stop) = {wanted}')


@check('the shaped signal is correct - call_cost * calls, and is the reward itself at C = 0')
def test_shaped_signal():
    units, pairs, table, questions, hops = fixture()
    tokens, present = D.pad_questions(questions)
    torch.manual_seed(7)
    model = D.Dispatcher()
    answers = torch.tensor([unit['a']['answer'] for unit in units])
    made = {}
    for name in ('good', 'loop', 'bad_stop'):
        made[name] = run(model, pairs, tokens, present, table,
                         hand_policy(name, hops, tokens.shape[1]))
    ok(all(s == 'answered' for s in made['good'].status), 'the good policy did not answer')
    ok(all(s == 'over_cap' for s in made['loop'].status), 'no over-cap episode in the fixture')
    ok(all(int(c) == D.MAX_CALLS for c in made['loop'].calls), 'the over-cap fixture is not capped')
    ok(any(s == 'invalid_action' for s in made['bad_stop'].status),
       'no invalid-action episode in the fixture')
    ok(any(int(c) > 0 for i, c in enumerate(made['bad_stop'].calls)
           if made['bad_stop'].status[i] == 'invalid_action'),
       'the invalid-action fixture made no call to be charged for')
    for name, episodes in made.items():
        reward = (episodes.answer == answers).float()
        for cost in (0.0, .01, .25):
            shaped = V2.shaped_signal(reward, episodes.calls, cost)
            wanted = [float(r) - cost * int(c) for r, c in zip(reward, episodes.calls)]
            ok(all(abs(float(x) - y) < 1e-6 for x, y in zip(shaped, wanted)),
               f'{name} at C={cost}: {shaped.tolist()} != {wanted}')
        ok(V2.shaped_signal(reward, episodes.calls, 0.0) is reward,
           'C = 0 did not return the reward tensor itself')
        # a failed episode keeps correct = 0 and is still charged for the calls it made
        for i, status in enumerate(episodes.status):
            if status != 'answered':
                ok(float(reward[i]) == 0., f'{name}: a {status} episode was rewarded')
                ok(abs(float(V2.shaped_signal(reward, episodes.calls, .5)[i])
                       + .5 * int(episodes.calls[i])) < 1e-6,
                   f'{name}: a {status} episode was not charged for its calls')


@check('--call-cost 0 reproduces v1 exactly: same log numbers, same final weights')
def test_bit_identity(scratch):
    one = Path(scratch) / 'identity-v1'
    two = Path(scratch) / 'identity-v2'
    D.main(train_argv(one))
    V2.main(train_argv(two, call_cost=0.0))
    a = [json.loads(line) for line in (one / 'train_log.jsonl').read_text().splitlines()]
    b = [json.loads(line) for line in (two / 'train_log.jsonl').read_text().splitlines()]
    ok(len(a) == len(b) and len(a) >= 1, f'{len(a)} v1 log lines, {len(b)} v2 log lines')
    for x, y in zip(a, b):
        for key in x:
            if key == 'seconds':
                continue
            ok(x[key] == y[key], f'log key {key}: v1 {x[key]!r} != v2 {y[key]!r}')
        ok('mean_shaped' in y and y['mean_shaped'] == y['mean_reward'],
           'v2 did not log mean_shaped, or it differs from the reward at C = 0')
        ok(y['call_cost'] == 0.0, 'v2 did not log call_cost')
    left = torch.load(one / 'dispatcher.pt', map_location='cpu', weights_only=False)
    right = torch.load(two / 'dispatcher.pt', map_location='cpu', weights_only=False)
    ok(set(left['state_dict']) == set(right['state_dict']), 'the checkpoints hold different keys')
    for key in left['state_dict']:
        ok(torch.equal(left['state_dict'][key], right['state_dict'][key]),
           f'final weight {key} differs between v1 and v2 at C = 0')
    ok(torch.equal(left['generator_state'], right['generator_state']),
       'the sampling generator consumed a different number of random values')
    ok(torch.equal(left['torch_rng_state'], right['torch_rng_state']),
       'the global torch RNG consumed a different number of random values')
    ok(left['python_rng_state'] == right['python_rng_state'],
       'the python RNG consumed a different number of random values')
    v1_config = json.loads((one / 'training.json').read_text())
    v2_config = json.loads((two / 'training.json').read_text())
    ok('call_cost' not in v1_config and v2_config['call_cost'] == 0.0,
       'call_cost is not recorded in v2 training.json')
    for key in ('arm', 'seed', 'updates', 'k', 'visits_per_update', 'dispatcher_parameters'):
        ok(v1_config[key] == v2_config[key], f'training.json {key} differs')


@check('with C > 0 the logged mean_reward stays pure correctness and mean_shaped is the signal')
def test_call_cost_logged(scratch):
    out = Path(scratch) / 'cost-run'
    V2.main(train_argv(out, call_cost=.05, seed=900202))
    lines = [json.loads(line) for line in (out / 'train_log.jsonl').read_text().splitlines()]
    ok(lines, 'no log lines')
    for line in lines:
        ok(line['call_cost'] == .05, 'call_cost not logged')
        ok(0. <= line['mean_reward'] <= 1., f'mean_reward left [0, 1]: {line["mean_reward"]}')
        wanted = line['mean_reward'] - .05 * line['mean_calls']
        ok(abs(line['mean_shaped'] - wanted) < 1e-9,
           f'mean_shaped {line["mean_shaped"]} != mean_reward - C*mean_calls {wanted}')
        ok(line['mean_shaped'] < line['mean_reward'], 'the charge did not bite')
    record = json.loads((out / 'training.json').read_text())
    ok(record['call_cost'] == .05, 'training.json did not record call_cost')
    saved = torch.load(out / 'dispatcher.pt', map_location='cpu', weights_only=False)
    ok(saved['call_cost'] == .05, 'the checkpoint did not record call_cost')
    same = Path(scratch) / 'cost-run-zero'
    V2.main(train_argv(same, call_cost=0.0, seed=900202))
    a = torch.load(out / 'dispatcher.pt', map_location='cpu', weights_only=False)['state_dict']
    b = torch.load(same / 'dispatcher.pt', map_location='cpu', weights_only=False)['state_dict']
    ok(any(not torch.equal(a[k], b[k]) for k in a),
       'C > 0 produced the same weights as C = 0; the shaping is inert')


@check('with both arms always correct, C > 0 moves the policy to the cheaper arm and C = 0 does not')
def test_two_armed_call_cost():
    calls = torch.tensor([2., 1.])            # arm 0 costs two calls, arm 1 costs one

    def sweep(cost):
        torch.manual_seed(13)
        logits = torch.nn.Parameter(torch.zeros(2))
        optimizer = torch.optim.SGD([logits], lr=.5)
        generator = torch.Generator().manual_seed(5)
        k = 8
        moves = []
        for _ in range(60):
            distribution = torch.distributions.Categorical(logits=logits.expand(k, 2))
            arms = torch.multinomial(distribution.probs, 1, generator=generator).squeeze(-1)
            reward = torch.ones(k)                                   # both arms always correct
            shaped = V2.shaped_signal(reward, calls[arms], cost)
            advantage = D.rloo_advantage(shaped, k)
            moves.append(float(advantage.abs().max()))
            loss = -(advantage.detach() * distribution.log_prob(arms)).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        return float(torch.softmax(logits.detach(), 0)[1]), max(moves)

    cheap, spread = sweep(.2)
    ok(cheap > .5 + .2, f'C > 0 did not prefer the cheaper arm: {cheap:.3f}')
    flat, zero_spread = sweep(0.)
    ok(zero_spread == 0., f'C = 0 produced a nonzero advantage: {zero_spread}')
    ok(abs(flat - .5) < 1e-6, f'C = 0 moved the policy: {flat:.6f}')


@check('each intervention forces exactly its own component and nothing else')
def test_interventions_are_surgical():
    units, pairs, table, questions, hops = fixture(indices=(3, 9))
    tokens, present = D.pad_questions(questions)
    width = tokens.shape[1]
    torch.manual_seed(17)
    model = D.Dispatcher()
    answers = [unit['a']['answer'] for unit in units]
    multi = [i for i, unit in enumerate(units) if len(unit['a']['chain']) > 1]
    ok(len(multi) >= 4, 'the fixture needs multi-hop units')

    def take(episodes):
        return [[list(step) for step in t] for t in episodes.transcripts]

    good = run(model, pairs, tokens, present, table, hand_policy('good', hops, width))
    ok(all(int(good.answer[i]) == answers[i] for i in range(len(units))),
       'the reference policy is not correct')

    # (a) forcing a component of an already-correct policy changes nothing
    for kind in V2.INTERVENTIONS[1:]:
        composed = run(model, pairs, tokens, present, table,
                       V2.intervention_policy(kind, hops, width,
                                              base=hand_policy('good', hops, width)))
        ok(take(composed) == take(good), f'{kind} changed an already-correct policy')
        ok(composed.status == good.status, f'{kind} changed the status of a correct policy')

    # (b) force_operation repairs a deliberately broken operation pointer, incl. three-hop
    bad_op = run(model, pairs, tokens, present, table, hand_policy('bad_op', hops, width))
    three = [i for i, unit in enumerate(units) if len(unit['a']['chain']) == 3]
    ok(three, 'the fixture needs a three-hop unit')
    ok(all(int(bad_op.answer[i]) != answers[i] for i in three),
       'the broken-operation policy was still right on three-hop')
    fixed = run(model, pairs, tokens, present, table,
                V2.intervention_policy('force_operation', hops, width,
                                       base=hand_policy('bad_op', hops, width)))
    ok(take(fixed) == take(good), 'force_operation did not reproduce the true chain')
    ok(all(int(fixed.answer[i]) == answers[i] for i in range(len(units))),
       'force_operation did not fix the broken-operation policy')

    # (c) force_subject repairs a broken subject and leaves the operations alone
    bad_subject = run(model, pairs, tokens, present, table,
                      hand_policy('bad_subject', hops, width))
    ok(all(int(bad_subject.answer[i]) != answers[i] for i in multi),
       'the broken-subject policy was still right on a multi-hop question')
    fixed = run(model, pairs, tokens, present, table,
                V2.intervention_policy('force_subject', hops, width,
                                       base=hand_policy('bad_subject', hops, width)))
    ok(take(fixed) == take(good), 'force_subject did not reproduce the true chain')

    # (d) force_stop repairs a policy that never stops
    bad_stop = run(model, pairs, tokens, present, table, hand_policy('bad_stop', hops, width))
    ok(all(s != 'answered' for s in bad_stop.status), 'the never-stop policy answered')
    fixed = run(model, pairs, tokens, present, table,
                V2.intervention_policy('force_stop', hops, width,
                                       base=hand_policy('bad_stop', hops, width)))
    ok(take(fixed) == take(good), 'force_stop did not reproduce the true chain')

    # (e) and each intervention touches NOTHING else: forcing the wrong component leaves
    #     the deliberate break in place
    for kind, broken in (('force_operation', 'bad_subject'), ('force_subject', 'bad_op'),
                         ('force_stop', 'bad_op'), ('force_stop', 'bad_subject')):
        base = run(model, pairs, tokens, present, table, hand_policy(broken, hops, width))
        composed = run(model, pairs, tokens, present, table,
                       V2.intervention_policy(kind, hops, width,
                                              base=hand_policy(broken, hops, width)))
        ok(take(composed) == take(base),
           f'{kind} altered the {broken} policy, whose broken component it does not own')
        ok(any(int(composed.answer[i]) != answers[i] for i in multi),
           f'{kind} repaired the {broken} policy it does not own')

    # (f) force_operation+subject owns two components and leaves stopping free
    both = V2.intervention_policy('force_operation+subject', hops, width,
                                  base=hand_policy('bad_stop', hops, width))
    composed = run(model, pairs, tokens, present, table, both)
    ok(all(s != 'answered' for s in composed.status),
       'force_operation+subject overrode the free stop decision')


@check('a re-layout of the question tensor moves no executed call and no pointer but the offset')
def test_layout_variants_are_neutral():
    units, pairs, table, questions, hops = fixture(indices=(3, 9))
    base_tokens, base_present = D.pad_questions(questions)
    base_width = base_tokens.shape[1]
    ok(torch.equal(base_tokens, V2.pad_questions_layout(questions)[0]),
       'pad_questions_layout(0, 0) disagrees with v1 pad_questions')
    ok(torch.equal(base_present, V2.pad_questions_layout(questions)[1]),
       'pad_questions_layout(0, 0) disagrees with v1 present mask')
    deep = 0
    for seed in range(8):
        torch.manual_seed(100 + seed)
        model = D.Dispatcher()
        for left, right in ((1, 0), (2, 0), (0, 2), (2, 3)):
            tokens, present = V2.pad_questions_layout(questions, left, right)
            width = tokens.shape[1]
            ok(int(present.sum()) == int(base_present.sum()), 'padding changed the live positions')
            ok(int((tokens * present).sum()) == int((base_tokens * base_present).sum()),
               'padding changed a live token')
            for policy, label in ((None, 'greedy'),
                                  (V2.intervention_policy('force_operation+subject', hops, width,
                                                          left=left), 'forced')):
                base_policy = None if policy is None else V2.intervention_policy(
                    'force_operation+subject', hops, base_width)
                a = run(model, pairs, base_tokens, base_present, table, base_policy)
                b = run(model, pairs, tokens, present, table, policy)
                ok(a.transcripts == b.transcripts,
                   f'left={left} right={right} ({label}) moved an executed (subject, op) call')
                ok(a.status == b.status and torch.equal(a.calls, b.calls),
                   f'left={left} right={right} ({label}) changed an episode outcome')
                for row, (pa, pb) in enumerate(zip(a.pointers, b.pointers)):
                    ok(len(pa) == len(pb), 'a re-layout changed the number of decisions')
                    for (sa, oa, ta), (sb, ob, tb) in zip(pa, pb):
                        shift = lambda p: p + (left if p < base_width else width - base_width)
                        ok(shift(sa) == sb and shift(oa) == ob and ta == tb,
                           f'left={left} right={right} row {row}: pointer moved by more '
                           f'than the padding ({sa},{oa},{ta}) -> ({sb},{ob},{tb})')
                deep += sum(len(t) >= 2 for t in b.transcripts)
    ok(deep > 0, 'no multi-call episode was compared')
    # a hand-written correct policy stays at 100% under every layout
    answers = [unit['a']['answer'] for unit in units]
    torch.manual_seed(3)
    model = D.Dispatcher()
    for left, right in ((0, 0), (1, 0), (2, 0), (0, 2), (2, 2)):
        tokens, present = V2.pad_questions_layout(questions, left, right)
        result = run(model, pairs, tokens, present, table,
                     hand_policy('good', hops, tokens.shape[1], left=left))
        ok(all(int(result.answer[i]) == answers[i] for i in range(len(units))),
           f'the correct policy lost accuracy at left={left} right={right}')
        ok(all(s == 'answered' for s in result.status),
           f'the correct policy stopped answering at left={left} right={right}')


@check('the layout check has teeth: an absolute-position dispatcher DOES move under left padding')
def test_layout_check_is_not_vacuous():
    units, pairs, table, questions, hops = fixture(indices=(3, 9))
    base_tokens, base_present = D.pad_questions(questions)
    tokens, present = V2.pad_questions_layout(questions, left=2)
    moved = 0
    for seed in range(8):
        torch.manual_seed(300 + seed)
        model = D.Dispatcher(absolute_positions=True)
        a = run(model, pairs, base_tokens, base_present, table)
        b = run(model, pairs, tokens, present, table)
        moved += sum(int(p[0][0] + 2 != q[0][0]) for p, q in zip(a.pointers, b.pointers) if p and q)
    ok(moved > 0, 'left padding moved nothing even for the absolute-position ablation; '
                  'the layout variants cannot detect a position-brittle dispatcher')


@check('a mixed-width batch changes the tensor but not one executed call')
def test_batch_mixed_is_neutral():
    ones = [D.make_unit('d1', i) for i in (1, 2)]
    threes = [D.make_unit('d4', i) for i in (1, 2)]
    oracle = D.OracleOperator()
    for cell_units, other_units in ((threes, ones), (ones, threes)):
        pairs = [(unit, 'a') for unit in cell_units]
        other = [(unit, 'a') for unit in other_units]
        table = V2.operator_table(oracle, pairs)
        partner = V2.operator_table(oracle, other)
        questions = [unit['a']['question'] for unit in cell_units]
        base_tokens, base_present = D.pad_questions(questions)
        hops = torch.tensor([len(unit['a']['chain']) for unit in cell_units])
        mixed, visit, keep = [], [], []
        for i, pair in enumerate(pairs):
            keep.append(len(mixed))
            mixed.append(pair)
            visit.append(i)
            mixed.append(other[i % len(other)])
            visit.append(len(pairs) + (i % len(other)))
        mixed_tokens, mixed_present = V2.pad_questions_layout(
            [unit[s]['question'] for unit, s in mixed])
        ok(mixed_tokens.shape[1] >= base_tokens.shape[1], 'the mixed batch is not wider')
        big = torch.cat((table, partner), 0)
        for seed in range(6):
            torch.manual_seed(200 + seed)
            model = D.Dispatcher()
            forced = V2.intervention_policy('force_operation+subject', hops,
                                            base_tokens.shape[1])
            for policy, mixed_policy in ((None, None),
                                         (forced, None)):
                if policy is not None:
                    hops_mixed = torch.tensor([len(unit[s]['chain']) for unit, s in mixed])
                    mixed_policy = V2.intervention_policy('force_operation+subject', hops_mixed,
                                                          mixed_tokens.shape[1])
                a = run(model, pairs, base_tokens, base_present, table, policy)
                with torch.no_grad():
                    b = D.rollout(model, mixed_tokens, mixed_present, big,
                                  torch.tensor(visit, dtype=torch.long), mode='greedy',
                                  policy=mixed_policy)
                for row, index in enumerate(keep):
                    ok(a.transcripts[row] == b.transcripts[index],
                       'the mixed batch moved an executed call')
                    ok(a.status[row] == b.status[index], 'the mixed batch changed an outcome')


@check('score: --score-out, --diagnose and --layout-variants leave the label-free output alone')
def test_score_outputs(scratch):
    home = Path(scratch) / 'mini'
    saved_n = D.PANEL_N
    D.PANEL_N = 4                       # a scratch panel; the frozen panels are never touched
    try:
        D.build_panels(str(home))
    finally:
        D.PANEL_N = saved_n
    panels = home / 'panels'
    run_dir = Path(scratch) / 'score-run'
    V2.main(train_argv(run_dir, call_cost=.01, seed=900203))
    plain = Path(scratch) / 'posthoc-plain' / 'mini-seed-0' / 'score'
    full = Path(scratch) / 'posthoc' / 'mini-seed-0' / 'score'
    V2.main(['score', '--run', str(run_dir), '--panels', str(panels), '--score-out', str(plain)])
    V2.main(['score', '--run', str(run_dir), '--panels', str(panels), '--score-out', str(full),
             '--diagnose', '--layout-variants'])
    for name in ('scores.json', 'transcripts.json'):
        ok((plain / name).read_bytes() == (full / name).read_bytes(),
           f'{name} is not byte-identical with and without the diagnostic flags')
    ok(not (run_dir / 'score').exists(), '--score-out still wrote inside the run folder')
    ok((full / 'diagnosis.json').exists() and (full / 'layout.json').exists(),
       'the diagnostic files were not written')
    ok(not (plain / 'diagnosis.json').exists(), 'diagnosis.json appeared without --diagnose')
    meta = json.loads((full / 'score_meta.json').read_text())
    ok(meta['post_hoc'] is True and 'POST-HOC' in meta['note'],
       'a --score-out run is not marked post-hoc')
    scores = json.loads((plain / 'scores.json').read_text())
    diagnosis = json.loads((full / 'diagnosis.json').read_text())
    layout = json.loads((full / 'layout.json').read_text())
    for cell, counts in scores['cells'].items():
        for label in ('trained_operator', 'oracle_operator'):
            base = diagnosis['cells'][cell][label]['none']
            ok(base['answers'] == counts[label]['answers'],
               f'{cell} {label}: the un-forced diagnosis disagrees with the normal score '
               f'({base["answers"]} vs {counts[label]["answers"]})')
            ok(base['full_path'] == counts[label]['full_path'],
               f'{cell} {label}: full-path disagrees with the normal score')
            ok(base['over_cap'] == counts[label]['over_cap'],
               f'{cell} {label}: over-cap disagrees with the normal score')
            base = layout['cells'][cell][label]['baseline']
            ok(base['answers'] == counts[label]['answers'],
               f'{cell} {label}: the layout baseline disagrees with the normal score')
            for variant in V2.LAYOUTS:
                row = layout['cells'][cell][label][variant]
                ok(row['identical_executed_calls'],
                   f'{cell} {label}: layout {variant} moved an executed call')
                ok(row['answers'] == base['answers'],
                   f'{cell} {label}: layout {variant} changed the answer count')
    ok(set(diagnosis['cells']) == set(D.CELLS), 'the diagnosis skipped a cell')
    for cell in diagnosis['cells']:
        for kind in V2.INTERVENTIONS:
            row = diagnosis['cells'][cell]['oracle_operator'][kind]
            ok(sum(row['calls_histogram'].values()) == row['rows'],
               f'{cell} {kind}: the call histogram does not cover every row')
    raised = False
    try:
        V2.main(['score', '--run', str(run_dir), '--panels', str(panels), '--score-out',
                 str(plain)])
    except FileExistsError:
        raised = True
    ok(raised, 'score overwrote an existing score directory')
    # and the stdlib-only report reads a post-hoc folder that holds no training.json
    import fable_dispatcher_report_v2 as R2
    R2.main(['report', '--root', str(Path(scratch) / 'posthoc')])
    entry = R2.runs(Path(scratch) / 'posthoc')[0]
    ok(R2.render_diagnosis(entry) and R2.render_layout(entry) and R2.render_histograms(entry),
       'the v2 report printed no diagnosis, layout or histogram section')
    for row in R2.histogram_rows(entry):
        ok(sum(row['counts']) == row['rows'],
           f'{row["cell"]}: the call histogram does not cover every scored side')


@check('forcing operation and subject together solves every cell with the oracle operator')
def test_full_forcing_is_a_ceiling():
    units, pairs, table, questions, hops = fixture(indices=(1, 4, 12))
    tokens, present = D.pad_questions(questions)
    torch.manual_seed(23)
    model = D.Dispatcher()
    policy = V2.intervention_policy('force_stop', hops, tokens.shape[1],
                                    base=V2.intervention_policy('force_operation+subject', hops,
                                                                tokens.shape[1]))
    result = run(model, pairs, tokens, present, table, policy)
    for i, unit in enumerate(units):
        ok(int(result.answer[i]) == unit['a']['answer'],
           f'unit {i}: the fully forced policy missed the answer')
        ok(int(result.calls[i]) == len(unit['a']['chain']), f'unit {i}: wrong number of calls')


# --------------------------------------------------------------------------- driver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', default=None)
    parser.add_argument('--only', default=None,
                        help='run only the checks whose name contains this text')
    args = parser.parse_args()
    D.configure()
    scratch = Path(args.scratch) if args.scratch else Path(tempfile.mkdtemp(prefix='fable-v2-'))
    scratch.mkdir(parents=True, exist_ok=True)
    passed = 0
    try:
        for name, fn in CHECKS:
            if args.only and args.only not in name:
                continue
            if 'scratch' in inspect.signature(fn).parameters:
                fn(scratch)
            else:
                fn()
            passed += 1
            print(f'ok  {name}')
    finally:
        if not args.scratch:
            shutil.rmtree(scratch, ignore_errors=True)
    if not passed:
        raise SystemExit(f'no check matched --only {args.only!r}')
    print(f'ALL {passed} CHECKS PASSED')


if __name__ == '__main__':
    main()
