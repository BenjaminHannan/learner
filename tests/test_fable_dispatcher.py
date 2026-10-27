"""Checks for the learned-dispatcher pilot.  Run as a plain script:

    PY -B tests/test_fable_dispatcher.py

Prints one line per check and finally `ALL N CHECKS PASSED`.  No registered training,
no GPU, no network; every temporary artefact goes to a caller-supplied --scratch
directory (default: a fresh directory under the system temp area).
"""
from __future__ import annotations

import argparse
import inspect
from pathlib import Path
import random
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import fable_dispatcher as D                                                # noqa: E402

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


def sample_units():
    return [D.make_unit('d1', 3), D.make_unit('d2', 3), D.make_unit('d3', 3), D.make_unit('d4', 3)]


def fixed_policy(step, tokens, results, n_results):
    """Left-to-right reference policy.  It reads only the question tokens it is given and
    its own transcript; the executor supplies no length, hop count or unread pointer."""
    batch, width = tokens.shape
    subject = torch.full((batch,), width + step - 1, dtype=torch.long)
    subject = torch.where(torch.full((batch,), step) == 0, torch.ones(batch, dtype=torch.long),
                          subject)
    operation = torch.full((batch,), 2 + step, dtype=torch.long)
    following = tokens.gather(1, (operation + 1).clamp(max=width - 1)[:, None]).squeeze(1)
    return subject, operation, (following == D.ANSWER).long()


# --------------------------------------------------------------------------- checks


@check('the dispatcher is never handed a story tensor (signature introspection)')
def test_no_story_in_signatures():
    banned = ('memory', 'inputs', 'story', 'eligible', 'facts', 'hops', 'hop_count',
              'question_length', 'length', 'lengths', 'owner', 'answer', 'gold', 'target')
    own = {name: value for name, value in vars(D.Dispatcher).items()
           if inspect.isfunction(value) and not name.startswith('__')}
    ok(set(own) >= {'question_state', 'candidate_keys', 'subject_logits', 'operation_logits',
                    'advance', 'stop_logits'}, f'unexpected dispatcher surface: {sorted(own)}')
    for name, method in own.items():
        for parameter in inspect.signature(method).parameters:
            ok(parameter not in banned,
               f'Dispatcher.{name} takes a forbidden argument {parameter!r}')
    for parameter in inspect.signature(D.candidate_features).parameters:
        ok(parameter not in ('memory', 'inputs', 'story', 'eligible', 'facts', 'hops'),
           f'candidate_features takes a forbidden argument {parameter!r}')
    model = D.Dispatcher()
    for key in model.state_dict():
        ok(not any(word in key for word in ('memory', 'story', 'eligible')),
           f'dispatcher parameter {key} mentions the story')


@check("permuting or zeroing the story leaves the dispatcher's step-1 logits unchanged")
def test_step_one_independent_of_story():
    units = sample_units()
    inputs, questions = D.pack_side(units, 'a')
    tokens, present = D.pad_questions(questions)
    model = D.Dispatcher()
    model.eval()

    def step_one_logits():
        state = model.question_state(tokens, present)
        features = D.candidate_features(tokens, present,
                                        torch.zeros(len(units), D.MAX_CALLS, dtype=torch.long),
                                        torch.zeros(len(units), dtype=torch.long),
                                        torch.full((len(units),), -1),
                                        torch.full((len(units),), -1),
                                        model.absolute_positions)
        keys = model.candidate_keys(features)
        subject = model.subject_logits(state, keys, features['present'])
        chosen = keys[torch.arange(len(units)), subject.argmax(-1)]
        return subject, model.operation_logits(state, chosen, keys, features['present'])

    with torch.no_grad():
        base = step_one_logits()
    oracle = D.OracleOperator()
    table = oracle.table(inputs, list(range(len(units))))
    scrambled = table[torch.randperm(len(units))]
    zeroed = torch.zeros_like(table)
    with torch.no_grad():
        again = step_one_logits()
    ok(torch.equal(base[0], again[0]) and torch.equal(base[1], again[1]),
       'step-1 logits are not deterministic')
    # and the first action taken is the same whatever the operator's table says
    first = []
    for candidate in (table, scrambled, zeroed):
        with torch.no_grad():
            result = D.rollout(model, tokens, present, candidate, torch.arange(len(units)),
                               mode='greedy')
        first.append([pointer[0][:2] for pointer in result.pointers])
    ok(first[0] == first[1] == first[2],
       'the dispatcher\'s first action depends on the story through the operator table')


@check('the executor solves 1-, 2- and 3-hop with a fixed policy and the oracle operator')
def test_interface_is_sufficient():
    units = sample_units()
    inputs, questions = D.pack_side(units, 'a')
    tokens, present = D.pad_questions(questions)
    table = D.OracleOperator().table(inputs, list(range(len(units))))
    model = D.Dispatcher()
    result = D.rollout(model, tokens, present, table, torch.arange(len(units)), policy=fixed_policy)
    for i, unit in enumerate(units):
        ok(result.status[i] == 'answered', f'unit {i} did not answer: {result.status[i]}')
        ok(int(result.answer[i]) == unit['a']['answer'],
           f'unit {i}: {int(result.answer[i])} != {unit["a"]["answer"]}')
        ok(int(result.calls[i]) == len(unit['a']['chain']),
           f'unit {i}: {int(result.calls[i])} calls for a {len(unit["a"]["chain"])}-hop chain')


@check('a policy that stops too early or too late fails')
def test_wrong_stop_fails():
    units = sample_units()
    inputs, questions = D.pack_side(units, 'a')
    tokens, present = D.pad_questions(questions)
    table = D.OracleOperator().table(inputs, list(range(len(units))))
    model = D.Dispatcher()

    def early(step, tokens, results, n_results):
        subject, operation, _ = fixed_policy(step, tokens, results, n_results)
        return subject, operation, torch.ones(tokens.shape[0], dtype=torch.long)

    def late(step, tokens, results, n_results):
        subject, operation, _ = fixed_policy(step, tokens, results, n_results)
        return subject, operation, torch.zeros(tokens.shape[0], dtype=torch.long)

    stopped_early = D.rollout(model, tokens, present, table, torch.arange(len(units)), policy=early)
    multi = [i for i, unit in enumerate(units) if len(unit['a']['chain']) > 1]
    ok(multi, 'the fixture needs a multi-hop unit')
    for i in multi:
        ok(int(stopped_early.answer[i]) != units[i]['a']['answer'],
           f'unit {i} was still correct after stopping one call in')
    stopped_late = D.rollout(model, tokens, present, table, torch.arange(len(units)), policy=late)
    for i, unit in enumerate(units):
        ok(stopped_late.status[i] != 'answered' or int(stopped_late.answer[i]) != unit['a']['answer'],
           f'unit {i} was still correct after refusing to stop')


@check('an invalid action ends the episode immediately, with no repair')
def test_invalid_action():
    units = sample_units()
    inputs, questions = D.pack_side(units, 'a')
    tokens, present = D.pad_questions(questions)
    table = D.OracleOperator().table(inputs, list(range(len(units))))
    model = D.Dispatcher()

    def bad_subject(step, tokens, results, n_results):
        _, operation, stop = fixed_policy(step, tokens, results, n_results)
        return torch.zeros(tokens.shape[0], dtype=torch.long), operation, stop

    def bad_operation(step, tokens, results, n_results):
        subject, _, stop = fixed_policy(step, tokens, results, n_results)
        return subject, torch.ones(tokens.shape[0], dtype=torch.long), stop

    for name, policy in (('subject', bad_subject), ('operation', bad_operation)):
        result = D.rollout(model, tokens, present, table, torch.arange(len(units)), policy=policy)
        for i in range(len(units)):
            ok(result.status[i] == 'invalid_action', f'bad {name}: status {result.status[i]}')
            ok(int(result.calls[i]) == 0, f'bad {name}: the executor still made a call')
            ok(int(result.answer[i]) == 0, f'bad {name}: the executor returned an answer')
            ok(len(result.transcripts[i]) == 0, f'bad {name}: a transcript entry was appended')


@check('the four-call cap ends a fifth call as a failure')
def test_call_cap():
    units = [D.make_unit('d4', 5)]
    inputs, questions = D.pack_side(units, 'a')
    tokens, present = D.pad_questions(questions)
    table = D.OracleOperator().table(inputs, list(range(len(units))))
    model = D.Dispatcher()

    def never_stop(step, tokens, results, n_results):
        batch = tokens.shape[0]
        return (torch.ones(batch, dtype=torch.long), torch.full((batch,), 2, dtype=torch.long),
                torch.zeros(batch, dtype=torch.long))

    result = D.rollout(model, tokens, present, table, torch.arange(len(units)), policy=never_stop)
    ok(result.status[0] == 'over_cap', f'status {result.status[0]}')
    ok(int(result.calls[0]) == D.MAX_CALLS, f'{int(result.calls[0])} calls, expected {D.MAX_CALLS}')
    ok(int(result.answer[0]) == 0, 'an over-cap episode still returned an answer')


@check('the cached operator table equals direct calls exactly')
def test_cache_matches_direct(scratch):
    torch.manual_seed(4242)
    model = A_random_operator()
    path = Path(scratch) / 'random-operator.pt'
    torch.save(dict(state_dict=model.state_dict(),
                    architecture=dict(vocab=68, width=48, heads=4, steps=3)), path)
    operator = D.FrozenOperator(path)
    units = sample_units()
    inputs, _ = D.pack_side(units, 'a')
    reps = list(range(len(units)))
    table = operator.table(inputs, reps)
    rng = random.Random(7)
    probes = 0
    for row, rep in enumerate(reps):
        for entity in rng.sample(range(D.ENTITY_MIN, D.ENTITY_MAX), 4):
            for j, op in enumerate(D.OPS):
                direct = D.direct_call(operator, inputs, entity, op, rep)
                ok(int(table[row, entity - D.ENTITY_MIN, j]) == direct,
                   f'cache {int(table[row, entity - D.ENTITY_MIN, j])} != direct {direct} '
                   f'for ({entity}, {op}) in story {row}')
                probes += 1
    ok(probes >= 60, f'only {probes} probes')
    oracle = D.OracleOperator()
    otable = oracle.table(inputs, reps)
    for row, rep in enumerate(reps):
        for entity in range(D.ENTITY_MIN, D.ENTITY_MAX):
            for j, op in enumerate(D.OPS):
                ok(int(otable[row, entity - D.ENTITY_MIN, j])
                   == D.direct_call(oracle, inputs, entity, op, rep),
                   'the oracle cache disagrees with an oracle direct call')


def A_random_operator():
    return D.A.CanonicalOperator()


@check('the reachability-restricted cache gives bit-identical episodes to the full grid')
def test_reachable_table_equivalent(scratch):
    torch.manual_seed(808)
    path = Path(scratch) / 'reach-operator.pt'
    torch.save(dict(state_dict=A_random_operator().state_dict(),
                    architecture=dict(vocab=68, width=48, heads=4, steps=3)), path)
    operator = D.FrozenOperator(path)
    rng = random.Random(f'{D.TRAIN_NAMESPACE}:900009')
    model = D.Dispatcher()
    compared = 0
    for _ in range(3):
        inputs, questions, owners, _answers = D.training_visits(rng, 6)
        reps, visit_of = D.representatives(owners)
        full = operator.table(inputs, reps)
        restricted = operator.reachable_table(inputs, reps)
        touched = restricted != 0
        ok(bool((full[touched] == restricted[touched]).all()),
           'the restricted cache disagrees with the full grid where it computed a value')
        ok(int(touched.sum()) < full.numel(), 'the restricted cache computed the whole grid')
        tokens, present = D.pad_questions(questions)
        for seed in (1, 2, 3):
            a = D.rollout(model, tokens, present, full, visit_of, mode='sample',
                          generator=torch.Generator().manual_seed(seed))
            b = D.rollout(model, tokens, present, restricted, visit_of, mode='sample',
                          generator=torch.Generator().manual_seed(seed))
            ok(a.transcripts == b.transcripts and a.status == b.status
               and torch.equal(a.answer, b.answer) and torch.equal(a.calls, b.calls),
               'the restricted cache changed an episode')
            compared += len(questions)
    ok(compared >= 200, f'only {compared} episodes compared')


@check('RLOO is reward-increasing on a two-armed toy')
def test_rloo_gradient():
    torch.manual_seed(11)
    logits = torch.nn.Parameter(torch.zeros(2))
    optimizer = torch.optim.SGD([logits], lr=.5)
    generator = torch.Generator().manual_seed(5)
    k = 8
    before = float(torch.softmax(logits.detach(), 0)[1])
    for _ in range(60):
        distribution = torch.distributions.Categorical(logits=logits.expand(k, 2))
        arms = torch.multinomial(distribution.probs, 1, generator=generator).squeeze(-1)
        reward = (arms == 1).float()
        advantage = D.rloo_advantage(reward, k)
        loss = -(advantage.detach() * distribution.log_prob(arms)).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    after = float(torch.softmax(logits.detach(), 0)[1])
    ok(after > before + .2, f'RLOO did not raise the rewarded arm: {before:.3f} -> {after:.3f}')
    reward = torch.tensor([1., 1., 1., 1.])
    ok(float(D.rloo_advantage(reward, 4).abs().max()) == 0.,
       'RLOO gives a nonzero advantage when every episode is rewarded')
    reward = torch.tensor([1., 0., 0., 0.])
    advantage = D.rloo_advantage(reward, 4)
    ok(float(advantage[0]) > 0 and all(float(x) < 0 for x in advantage[1:]),
       'RLOO advantages have the wrong sign')


@check('the training stream holds no three-hop and no held-out two-hop question')
def test_training_stream():
    spec, _ = D.spec_and_visit()
    rng = random.Random(f'{D.TRAIN_NAMESPACE}:900001')
    seen = dict(one_hop=0, practised_two_hop=0)
    for _ in range(6):
        _inputs, questions, owners, _answers = D.training_visits(rng, 8)
        ok(len(questions) == 32, f'{len(questions)} questions from 8 visits')
        for q in questions:
            ops = q[2:-1]
            ok(len(ops) in (1, 2), f'a {len(ops)}-hop training question appeared')
            ok(q[0] == D.QUESTION and q[-1] == D.ANSWER, 'malformed training question')
            if len(ops) == 1:
                seen['one_hop'] += 1
            else:
                ok(ops[0] == D.LINK, f'two-hop question without a link: {q}')
                ok(ops[1] != spec.relation(spec.heldout_relation),
                   f'held-out two-hop composition in the training stream: {q}')
                seen['practised_two_hop'] += 1
        ok(len(set(owners)) == 8, 'visits were lost')
    ok(seen['one_hop'] > 0 and seen['practised_two_hop'] > 0, f'stream is degenerate: {seen}')


@check('the training stream refuses a question whose visible semantics match a panel unit')
def test_forbidden_overlap():
    rng = random.Random(f'{D.TRAIN_NAMESPACE}:900002')
    _inputs, questions, owners, _answers = D.training_visits(rng, 4)
    memory_rng = random.Random(f'{D.TRAIN_NAMESPACE}:900002')
    inputs, questions, owners, _ = D.training_visits(memory_rng, 4)
    memory = inputs.memory.tolist()
    eligible = inputs.eligible.tolist()
    rows = [row for row, keep in zip(memory[owners[0]], eligible[0]) if keep and any(row)]
    signature = D.A.visible_signature(rows, questions[0])
    replay = random.Random(f'{D.TRAIN_NAMESPACE}:900002')
    raised = False
    try:
        D.training_visits(replay, 4, frozenset({signature}))
    except RuntimeError as error:
        raised = 'overlap' in str(error)
    ok(raised, 'the training stream did not refuse a forbidden panel semantic')


@check('every panel cell audits clean, with distinct three-hop chains and local pair edits')
def test_panel_audits():
    for cell, cfg in D.CELLS.items():
        for index in (0, 1, 2, 11):
            unit = D.make_unit(cell, index)
            problems = D.audit_unit(unit)
            ok(not problems, f'{cell}:{index} {problems}')
            side = unit['a']
            ops = side['question'][2:-1]
            ok(len(ops) == cfg['hops'], f'{cell}: {len(ops)} operations')
            if cfg['hops'] == 3:
                people = [side['chain'][0][0], side['chain'][0][2], side['chain'][1][2]]
                ok(len(set(people)) == 3, f'{cell}:{index} chain revisits a person {people}')
                ok(ops == [D.LINK, D.LINK, 10], f'{cell}: three-hop operations {ops}')
            if cfg['kind'] == 'pair':
                diffs = D._memory_diffs(unit['a']['memory'], unit['b']['memory'])
                ok(diffs == (1 if cfg['edit'] == 'link' else 2),
                   f'{cell}:{index} {diffs} differing tokens')
                same = unit['a']['answer'] == unit['b']['answer']
                ok(same == bool(cfg['invariant']),
                   f'{cell}:{index} answers same={same} but invariant={cfg["invariant"]}')
                people_b = [unit['b']['chain'][0][0], unit['b']['chain'][0][2],
                            unit['b']['chain'][1][2]]
                ok(len(set(people_b)) == 3, f'{cell}:{index} twin chain revisits a person')


@check('panel units are unique; a repeated draw is bit-identical')
def test_panel_determinism():
    signatures = set()
    for cell in D.CELLS:
        for index in range(4):
            unit = D.make_unit(cell, index)
            again = D.make_unit(cell, index)
            unit.pop('rejections')
            again.pop('rejections')
            ok(unit == again, f'{cell}:{index} is not reproducible')
            for semantic, tensor in D.unit_signatures(unit):
                ok(semantic not in signatures, f'{cell}:{index} duplicate semantic signature')
                signatures.add(semantic)


@check('the relative-position features carry no absolute index')
def test_relative_features():
    width = 6
    tokens = torch.tensor([[4, 60, 11, 11, 10, 5]])
    present = torch.ones(1, width, dtype=torch.bool)
    results = torch.zeros(1, D.MAX_CALLS, dtype=torch.long)
    zero = torch.zeros(1, dtype=torch.long)
    base = D.candidate_features(tokens, present, results, zero, torch.tensor([2]),
                                torch.tensor([1]))
    shifted = D.candidate_features(tokens, present, results, zero, torch.tensor([3]),
                                   torch.tensor([2]))
    ok('absolute' not in base, 'the primary model exposes an absolute-position feature')
    for name in ('offset_op', 'offset_subject'):
        values = base[name]
        ok(int(values.min()) >= 0 and int(values.max()) <= D.OFFSET_NA,
           f'{name} left the offset table')
        ok(all(int(v) == D.OFFSET_NA for v in values[0, width:]),
           f'{name} gave a transcript result a question offset')
        # shifting the question position and the previous pointer together must not change it
        ok(torch.equal(values[0, 1:width - 1], shifted[name][0, 2:width]),
           f'{name} depends on the absolute index, not the offset')
    unknown = D.candidate_features(tokens, present, results, zero, torch.tensor([-1]),
                                   torch.tensor([-1]))
    for name in ('offset_op', 'offset_subject'):
        ok(all(int(v) == D.OFFSET_NA for v in unknown[name][0]),
           f'{name} invented an offset before any pointer was chosen')
    absolute = D.candidate_features(tokens, present, results, zero, torch.tensor([-1]),
                                    torch.tensor([-1]), absolute_positions=True)
    ok('absolute' in absolute and 'offset_op' not in absolute,
       'the ablation did not replace the relative offsets')
    ok([int(v) for v in absolute['absolute'][0, :width]] == list(range(width)),
       'the ablation is not an absolute position embedding')


@check('the frozen operator is unchanged by an rl training step, and the run is reproducible')
def test_operator_unchanged_by_training(scratch):
    torch.manual_seed(31337)
    operator_path = Path(scratch) / 'frozen-operator.pt'
    torch.save(dict(state_dict=A_random_operator().state_dict(),
                    architecture=dict(vocab=68, width=48, heads=4, steps=3)), operator_path)
    before = D.FrozenOperator(operator_path).fingerprint
    out = Path(scratch) / 'rl-smoke'
    D.main(['train', '--arm', 'rl', '--operator', str(operator_path), '--seed', '900003',
            '--updates', '2', '--out', str(out), '--visits', '2', '--k', '4', '--time-cap', '120'])
    record = __import__('json').loads((out / 'training.json').read_text())
    ok(record['operator_weights_unchanged'], 'the run did not certify the operator as unchanged')
    ok(record['operator_fingerprint_before'] == before, 'the operator changed before training')
    ok(record['operator_fingerprint_after'] == before, 'the operator changed during training')
    ok(D.sha(operator_path) == D.FrozenOperator(operator_path).sha256,
       'the operator checkpoint file changed on disk')
    ok(record['dispatcher_parameters'] == D.Dispatcher().parameters_count(),
       'the recorded parameter count is wrong')
    raised = False
    try:
        D.main(['train', '--arm', 'rl', '--operator', str(operator_path), '--seed', '900003',
                '--updates', '1', '--out', str(out), '--visits', '2', '--time-cap', '60'])
    except SystemExit as error:
        raised = 'refusing to overwrite' in str(error)
    ok(raised, 'train did not refuse to overwrite an existing run directory')


@check('the dispatcher parameter count is inside the 5k-25k budget')
def test_parameter_budget():
    for absolute in (False, True):
        model = D.Dispatcher(absolute_positions=absolute)
        count = model.parameters_count()
        ok(5_000 <= count <= 25_000, f'absolute_positions={absolute}: {count} parameters')
    ok(D.Dispatcher().parameters_count() == 15_522,
       f'the parameter count moved: {D.Dispatcher().parameters_count()}')


@check('a missing operator checkpoint fails clearly, and test.pt is refused')
def test_operator_errors(scratch):
    raised = False
    try:
        D.make_operator(Path(scratch) / 'does-not-exist.pt')
    except FileNotFoundError as error:
        raised = 'operator checkpoint not found' in str(error)
    ok(raised, 'a missing checkpoint did not fail clearly')
    raised = False
    try:
        D.make_operator(Path(scratch) / 'test.pt')
    except ValueError as error:
        raised = 'prohibited' in str(error)
    ok(raised, 'test.pt was not refused')


@check('the supervised arm teaches the gold pointer sequence, not the answer token')
def test_supervised_gold():
    units = sample_units()
    inputs, questions = D.pack_side(units, 'a')
    tokens, present = D.pad_questions(questions)
    table = D.OracleOperator().table(inputs, list(range(len(units))))
    model = D.Dispatcher()
    gold = D.gold_actions(questions, tokens.shape[1])
    result = D.rollout(model, tokens, present, table, torch.arange(len(units)), gold=gold)
    for i, unit in enumerate(units):
        ok(result.status[i] == 'answered', f'unit {i}: {result.status[i]}')
        ok(int(result.answer[i]) == unit['a']['answer'], f'unit {i}: gold actions missed the answer')
        ok([[s, o] for s, o, _ in result.transcripts[i]]
           == [[s, o] for s, o, _ in unit['a']['chain']],
           f'unit {i}: the gold transcript is not the true chain')
    loss = -result.logprob.mean()
    loss.backward()
    ok(any(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in model.parameters()),
       'the supervised loss produced no gradient')


# --------------------------------------------------------------------------- driver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', default=None)
    args = parser.parse_args()
    D.configure()
    scratch = Path(args.scratch) if args.scratch else Path(tempfile.mkdtemp(prefix='fable-dispatcher-'))
    scratch.mkdir(parents=True, exist_ok=True)
    passed = 0
    try:
        for name, fn in CHECKS:
            if 'scratch' in inspect.signature(fn).parameters:
                fn(scratch)
            else:
                fn()
            passed += 1
            print(f'ok  {name}')
    finally:
        if not args.scratch:
            shutil.rmtree(scratch, ignore_errors=True)
    print(f'ALL {passed} CHECKS PASSED')


if __name__ == '__main__':
    main()
