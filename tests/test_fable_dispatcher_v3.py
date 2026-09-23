"""Checks for scripts/fable_dispatcher_v3.py.  Plain script; no pytest.

Run:
    python3.12 -B tests/test_fable_dispatcher_v3.py
    FABLE_V3_PANELS=<panel dir> python3.12 -B tests/test_fable_dispatcher_v3.py

By default the interface-sufficiency checks build their own small panels (n = 6 per
cell) so the file stays fast.  With FABLE_V3_PANELS pointing at a frozen panel
directory they run against the real 64-unit cells instead, which is the 64/64 form of
the check.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v3 as V3                                            # noqa: E402

torch = V3.torch
OPERATOR = ('/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/'
            'astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt')

PASSED = 0
FAILED = []


def check(name, function):
    global PASSED
    try:
        detail = function()
    except Exception as exc:                                    # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


def small_panels(n=6):
    """Every cell, n units each, audited exactly as `build_panels` audits them."""
    panels = {}
    for cell in V3.CELL_ORDER:
        units = []
        for index in range(n):
            unit = V3.make_unit(cell, index)
            problems = V3.audit_unit(unit)
            if problems:
                raise AssertionError(f'{cell}:{index}: {problems}')
            unit.pop('rejections', None)
            units.append(unit)
        panels[cell] = dict(cell=cell, n=n, units=units)
    return panels


_PANEL_CACHE = {}


def load_or_build_panels():
    if 'value' not in _PANEL_CACHE:
        folder = os.environ.get('FABLE_V3_PANELS')
        if folder:
            _manifest, panels, _ = V3.load_panels(folder)
            _PANEL_CACHE['value'] = (panels, f'frozen panels {folder}')
        else:
            _PANEL_CACHE['value'] = (small_panels(), 'freshly built n=6 panels')
    return _PANEL_CACHE['value']


# --------------------------------------------------------------------------- worlds


def test_world_builder():
    for trial in range(40):
        rng = random.Random(f'world-builder:{trial}')
        people = (6, 12, 16)[trial % 3]
        world = V3.build_world(rng, people)
        assert len(world.ents) == people == len(set(world.ents))
        assert all(V3.ENTITY_MIN <= e < V3.ENTITY_MAX for e in world.ents)
        assert set(world.friend) == set(world.ents)
        assert all(world.friend[e] != e and world.friend[e] in world.ents for e in world.ents)
        rows = V3.render(world)
        assert rows == V3.render(world), 'rendering is not deterministic'
        links, attrs = {}, {}
        for row in rows:
            assert row[0] == V3.WORLD and row[-1] == V3.NEWLINE
            if len(row) < 4 or not V3.ENTITY_MIN <= row[1] < V3.ENTITY_MAX:
                continue
            if row[2] == V3.LINK:
                assert row[1] not in links, 'a person has two LINK facts'
                assert V3.ENTITY_MIN <= row[3] < V3.ENTITY_MAX
                links[row[1]] = row[3]
            else:
                assert V3.FIRST_REL <= row[2] < V3.FIRST_REL + V3.RELATIONS
                assert (row[1], row[2]) not in attrs
                attrs[(row[1], row[2])] = row[3]
        assert set(links) == set(world.ents), 'not exactly one LINK fact per person'
        assert links == world.friend
        assert len(attrs) == people * V3.RELATIONS, 'missing an attribute fact'
    return 'one LINK and three attributes per person, 6/12/16 people'


def test_distinct_chain_sampler():
    """`distinct_askers` must be exactly right for every (people, hops), and must
    actually find askers in the regimes v3 uses.

    A pairwise-distinct k-chain is a simple path of length k-1 in a random functional
    graph, so it exists for every k <= N but becomes rare as k approaches N (k = N needs
    a Hamiltonian path).  v3 only ever asks for k <= 3 at N = 6 and k <= 8 at N = 16,
    and the yields below are the acceptance rates the panel/stream builders pay.
    """
    used = {6: 3, 16: 8}          # the only (people, hops) regimes v3 builds
    yields = {}
    for people in (6, 12, 16):
        for hops in range(1, min(people, 9) + 1):
            found, trials = 0, 24
            for trial in range(trials):
                rng = random.Random(f'distinct:{people}:{hops}:{trial}')
                world = V3.build_world(rng, people)
                askers = V3.distinct_askers(world, hops)
                for a in world.ents:
                    chain = V3.chain_people(world.friend, a, hops)
                    assert len(chain) == hops
                    assert (a in askers) == (len(set(chain)) == hops), \
                        'distinct_askers disagrees with the chain it reports'
                found += bool(askers)
            yields[f'p{people}-k{hops}'] = found / trials
            if hops <= used.get(people, 0):
                # the builders resample the world until an asker exists, so what matters
                # is that the acceptance rate is high enough for that loop to be cheap
                assert found / trials >= 0.25, \
                    f'only {found}/{trials} {people}-person worlds had a distinct {hops}-chain'
    worst = min((yields[f'p{p}-k{k}'], f'p{p}-k{k}')
                for p, kmax in used.items() for k in range(1, kmax + 1))
    return f'predicate exact for every (N, k); worst yield in the used regimes: ' \
           f'{worst[1]} {worst[0]:.2f}'


def test_interpreters_agree():
    checked = 0
    for cell in V3.CELL_ORDER:
        for index in range(3):
            unit = V3.make_unit(cell, index)
            for name in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
                side = unit[name]
                eligible = V3.side_eligible(side)
                mine = V3.interpret(side['memory'], eligible, side['question'])
                theirs = V1.walk(V1.fact_table(side['memory'], eligible), side['question'])
                assert mine == theirs == side['chain']
                assert side['chain'][-1][2] == side['answer']
                checked += 1
    return f'{checked} sides, two independent interpreters == recorded chain'


def test_all_cells_audit_clean():
    panels = small_panels(n=4)
    semantic, tensors = set(), set()
    for cell, panel in panels.items():
        cfg = V3.CELLS[cell]
        for unit in panel['units']:
            assert not V3.audit_unit(unit)
            assert len(unit['a']['chain']) == cfg['hops']
            for sem, ts in V3.unit_signatures(unit):
                assert sem not in semantic, 'duplicate semantic signature'
                assert ts not in tensors, 'duplicate tensor signature'
                semantic.add(sem)
                tensors.add(ts)
    return f'{len(panels)} cells, {len(semantic)} distinct visible semantics'


def test_pair_twins():
    for cell, expected in (('pair-link', 1), ('pair-value', 2), ('pair-irrelevant', 2)):
        cfg = V3.CELLS[cell]
        for index in range(6):
            unit = V3.make_unit(cell, index)
            assert unit['kind'] == 'pair'
            assert V3.memory_diffs(unit['a']['memory'], unit['b']['memory']) == expected
            same = unit['a']['answer'] == unit['b']['answer']
            assert same == cfg['invariant'], f'{cell}: answer change is wrong'
            assert unit['a']['question'] == unit['b']['question']
            assert len(set(unit['a']['people'])) == V3.PAIR_HOPS
            assert len(set(unit['b']['people'])) == V3.PAIR_HOPS
    return 'changed-link 1 token, changed-value/irrelevant 2 tokens, answers as required'


# --------------------------------------------------------------------------- stream


def test_training_stream():
    rng = random.Random(f'{V3.TRAIN_NAMESPACE}:900201')
    seen = {1: 0, 2: 0, 3: 0}
    for _ in range(6):
        inputs, questions, owners, answers, meta = V3.training_visits(rng, 16, 6, (1, 2, 3))
        assert len(questions) == 16 * V3.QUESTIONS_PER_WORLD
        assert len(set(owners)) == 16
        assert sorted(owners) == [v for v in range(16) for _ in range(V3.QUESTIONS_PER_WORLD)]
        for q, row in zip(questions, meta):
            hops = row['hops']
            assert hops in (1, 2, 3), f'hop count {hops} outside the listed lengths'
            seen[hops] += 1
            assert len(q) == 3 + hops
            assert q[2:-1][:-1] == [V3.LINK] * (hops - 1)
            terminal = q[-2]
            assert terminal == row['terminal']
            if hops >= 2:
                assert terminal != V3.HELDOUT_REL, \
                    'relation 10 appeared as a multi-hop training terminal'
                assert terminal in V3.PRACTISED_RELS
                assert len(set(row['people'])) == hops, 'a multi-hop training chain repeats a person'
            else:
                assert terminal in (*V3.PRACTISED_RELS, V3.HELDOUT_REL)
        truth = V1.walk(V1.fact_table(inputs.memory.tolist()[owners[0]],
                                      inputs.eligible.tolist()[0]), questions[0])
        assert truth[-1][2] == int(answers[0])
    assert all(count > 0 for count in seen.values())
    return f'6 batches, hop histogram {seen}, relation 10 never a multi-hop terminal'


def test_training_stream_respects_hop_list():
    for choices in ((1, 2), (3,), (1, 3)):
        rng = random.Random(f'{V3.TRAIN_NAMESPACE}:hoplist:{choices}')
        _inputs, questions, _owners, _answers, meta = V3.training_visits(rng, 4, 6, choices)
        got = {row['hops'] for row in meta}
        assert got <= set(choices), f'{got} outside {choices}'
        assert all(len(q) == 3 + row['hops'] for q, row in zip(questions, meta))
    return 'hop counts never exceed the listed lengths'


def test_training_worlds_have_one_link_each():
    rng = random.Random(f'{V3.TRAIN_NAMESPACE}:links')
    inputs, _questions, _owners, _answers, _meta = V3.training_visits(rng, 4, 6, (1, 2, 3))
    for memory in inputs.memory.tolist():
        owners = [row[1] for row in memory
                  if row[0] == V3.WORLD and row[2] == V3.LINK
                  and V3.ENTITY_MIN <= row[1] < V3.ENTITY_MAX]
        assert len(owners) == len(set(owners)) == 6
    return 'every training world: six people, one LINK each'


# --------------------------------------------------------------------------- caps


def _batch_for_caps(hops=6, n=8):
    """A batch of distinct-chain `hops`-hop questions in 16-person worlds."""
    units = []
    for index in range(n):
        rng = random.Random(f'cap-batch:{hops}:{index}')
        while True:
            world = V3.build_world(rng, 16)
            askers = V3.distinct_askers(world, hops)
            if askers:
                break
        asker = rng.choice(askers)
        units.append(dict(index=index, kind='single',
                          a=V3.make_side(world, asker, hops, V3.HELDOUT_REL)))
    inputs, questions = V3.pack_side(units, 'a')
    operator = V3.OracleOperator()
    table = operator.table(inputs, list(range(len(units))))
    tokens, present = V3.pad_questions(questions)
    return units, tokens, present, table, torch.arange(len(units))


def _never_stop(hops, width):
    inner = V3.correct_policy(hops, width)

    def policy(step, tokens, results, n_results):
        out = inner(step, tokens, results, n_results)
        batch = tokens.shape[0]
        out['stop'] = (torch.zeros(batch, dtype=torch.long),
                       torch.ones(batch, dtype=torch.bool))
        return out
    return policy


def test_cap4_and_cap16_logits_identical():
    units, tokens, present, table, visit_of = _batch_for_caps(hops=6)
    torch.manual_seed(7)
    model = V3.Dispatcher(width=32)
    hops = torch.tensor([len(u['a']['chain']) for u in units], dtype=torch.long)
    width = tokens.shape[1]
    traces = {}
    for cap in (4, 16):
        record = []
        V3.rollout_v3(model, tokens, present, table, visit_of, cap, mode='greedy',
                      policy=_never_stop(hops, width), record=record)
        traces[cap] = record
    assert len(traces[4]) == 4, f'expected four recorded steps at cap 4, got {len(traces[4])}'
    assert len(traces[16]) >= 4
    keep = width + 4
    for step in range(4):
        a, b = traces[4][step], traces[16][step]
        assert torch.equal(a['state'], b['state']), f'step {step}: recurrent state moved'
        assert torch.equal(a['stop'], b['stop']), f'step {step}: stop logits moved'
        for head in ('subject', 'operation'):
            assert a[head].shape[1] == width + 4 and b[head].shape[1] == width + 16
            assert torch.equal(a[head], b[head][:, :keep]), f'step {step}: {head} logits moved'
            extra = b[head][:, keep:]
            assert bool(torch.isinf(extra).all() and (extra < 0).all()), \
                f'step {step}: the extra {head} slots are not masked out'
    return 'steps 1..4 bitwise identical; extra cap-16 slots are -inf'


def test_cap_equivalence_end_to_end():
    units, tokens, present, table, visit_of = _batch_for_caps(hops=3)
    torch.manual_seed(11)
    model = V3.Dispatcher(width=32)
    runs = {cap: V3.rollout_v3(model, tokens, present, table, visit_of, cap, mode='greedy')
            for cap in (4, 16)}
    four, sixteen = runs[4], runs[16]
    for i in range(len(units)):
        if four.status[i] == 'over_cap':
            continue
        assert four.status[i] == sixteen.status[i]
        assert four.transcripts[i] == sixteen.transcripts[i]
        assert int(four.answer[i]) == int(sixteen.answer[i])
    return 'episodes that finish within four calls are unchanged at cap 16'


def test_over_cap_is_a_failure():
    units, tokens, present, table, visit_of = _batch_for_caps(hops=5)
    torch.manual_seed(3)
    model = V3.Dispatcher(width=32)
    hops = torch.tensor([len(u['a']['chain']) for u in units], dtype=torch.long)
    episodes = V3.rollout_v3(model, tokens, present, table, visit_of, 3, mode='greedy',
                             policy=_never_stop(hops, tokens.shape[1]))
    assert all(s == 'over_cap' for s in episodes.status), episodes.status
    assert all(int(a) == 0 for a in episodes.answer)
    return 'a never-stopping episode ends over_cap with no answer'


# --------------------------------------------------------------------------- policies


def _blank_model():
    """A randomly initialised dispatcher.  Under a fully forcing policy it is never
    consulted, so the numbers below measure the INTERFACE, not any trained model."""
    torch.manual_seed(5)
    return V3.Dispatcher(width=32)


def _score_with_policy(model, panels, operator, factory, cap=V3.EVAL_CAP):
    out = {}
    for cell, panel in panels.items():
        cfg = V3.CELLS[cell]
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        rows = {s: V3.score_side(model, operator, panel['units'], s, cap,
                                 policy_factory=factory) for s in sides}
        out[cell] = V3.aggregate(rows, len(panel['units']), cfg)
    return out


def test_correct_policy_is_sufficient():
    panels, where = load_or_build_panels()
    model = _blank_model()
    factory = lambda hops, width: V3.correct_policy(hops, width)
    detail = []
    for label, operator in (('oracle', V3.OracleOperator()),
                            ('frozen', V3.make_operator(OPERATOR))):
        counts = _score_with_policy(model, panels, operator, factory)
        sizes = set()
        for cell, row in counts.items():
            n = len(panels[cell]['units'])
            sizes.add(n)
            assert row['strict'] == n, f'{label} {cell}: strict {row["strict"]}/{n}'
            assert row['answers'] == n, f'{label} {cell}: answers {row["answers"]}/{n}'
            assert row['over_cap'] == 0 and row['invalid'] == 0, f'{label} {cell}: {row}'
        detail.append(f'{label} {len(counts)} cells all {sorted(sizes)}/{sorted(sizes)} strict')
    return f'{where}; ' + ', '.join(detail)


def test_first_result_policy_separates_the_rules():
    panels, where = load_or_build_panels()
    model = _blank_model()
    factory = lambda hops, width: V3.correct_policy(hops, width, use_first_result=True)
    counts = _score_with_policy(model, panels, V3.OracleOperator(), factory)
    short, long = [], []
    for cell, row in counts.items():
        n = len(panels[cell]['units'])
        if V3.CELLS[cell]['hops'] <= 2:
            assert row['loose'] == n and row['answers'] == n, f'{cell}: {row}'
            short.append(cell)
        else:
            assert row['loose'] == 0, f'{cell}: the first-result rule still walked the true path'
            assert row['answers'] < n, f'{cell}: the first-result rule answered {row["answers"]}/{n}'
            long.append(cell)
    assert short and long
    return (f'{where}; first-result rule: {len(short)} cells with k<=2 perfect, '
            f'{len(long)} cells with k>=3 never on the true path')


# --------------------------------------------------------------------------- ablations


def test_ablation_flags_touch_only_their_own_feature():
    units, tokens, present, table, visit_of = _batch_for_caps(hops=4, n=4)
    batch, width = tokens.shape
    cap = 4
    results = torch.zeros(batch, cap, dtype=torch.long)
    results[:, 0] = 55
    results[:, 1] = 57
    n_results = torch.full((batch,), 2, dtype=torch.long)
    previous_op = torch.full((batch,), 3, dtype=torch.long)
    previous_subject = torch.full((batch,), 1, dtype=torch.long)
    args = (tokens, present, results, n_results, previous_op, previous_subject, cap, False)
    base = V3.candidate_features_v3(*args)
    assert base['recent'].sum() > 0 and (base['offset_op'] != V3.OFFSET_NA).any()
    no_recent = V3.candidate_features_v3(*args, no_recent=True)
    no_offsets = V3.candidate_features_v3(*args, no_offsets=True)
    for key in base:
        if key == 'recent':
            assert bool((no_recent[key] == 0).all()), 'the recent flag was not zeroed'
            assert not torch.equal(base[key], no_recent[key])
        else:
            assert torch.equal(base[key], no_recent[key]), f'--no-recent-flag moved {key}'
    for key in base:
        if key in ('offset_op', 'offset_subject'):
            assert bool((no_offsets[key] == V3.OFFSET_NA).all()), f'{key} is not the N/A slot'
            assert not torch.equal(base[key], no_offsets[key])
        else:
            assert torch.equal(base[key], no_offsets[key]), f'--no-offsets moved {key}'
    absolute = V3.candidate_features_v3(tokens, present, results, n_results, previous_op,
                                        previous_subject, cap, True)
    assert 'absolute' in absolute and 'offset_op' not in absolute
    return 'each flag changes exactly its own feature and nothing else'


# --------------------------------------------------------------------------- v1 equivalence


def test_v3_rollout_matches_v1_at_cap_four():
    """v1's WORLD STREAM cannot be reproduced bit-for-bit -- v1 draws its worlds from
    `toy_ladder.visit`, whose random draws and line layout differ from v3's own builder,
    and v1 cannot make 16-person worlds or chains past three hops at all.  So the check
    is the one the handoff names as the fallback: on an IDENTICAL hand-built batch the
    executor and the policy-gradient step are the same function.
    """
    rng = random.Random(f'{V3.TRAIN_NAMESPACE}:v1-equivalence')
    inputs, questions, owners, answers, _meta = V3.training_visits(rng, 4, 6, (1, 2))
    reps, visit_of = V3.representatives(owners)
    operator = V3.OracleOperator()
    table = operator.reachable_table(inputs, reps)
    tokens, present = V3.pad_questions(questions)
    torch.manual_seed(13)
    model = V3.Dispatcher(width=32)
    k = 4
    repeat = torch.arange(len(questions)).repeat_interleave(k)
    episodes = {}
    for label, run in (('v1', V1.rollout), ('v3', V3.rollout_v3)):
        generator = torch.Generator().manual_seed(4242)
        if label == 'v1':
            episodes[label] = run(model, tokens[repeat], present[repeat], table,
                                  visit_of[repeat], mode='sample', generator=generator)
        else:
            episodes[label] = run(model, tokens[repeat], present[repeat], table,
                                  visit_of[repeat], V1.MAX_CALLS, mode='sample',
                                  generator=generator)
    a, b = episodes['v1'], episodes['v3']
    assert torch.equal(a.answer, b.answer) and torch.equal(a.calls, b.calls)
    assert torch.allclose(a.logprob, b.logprob, atol=0, rtol=0)
    assert torch.allclose(a.entropy, b.entropy, atol=0, rtol=0)
    assert a.status == b.status and a.transcripts == b.transcripts and a.pointers == b.pointers
    reward = (a.answer == answers[repeat]).float()
    beta = 0.2
    mean_entropy = a.entropy.sum() / a.decisions.sum().clamp_min(1)
    v1_loss = -(V1.rloo_advantage(reward, k).detach() * a.logprob).mean() - beta * mean_entropy
    v3_loss, shaped, v3_entropy = V3.policy_gradient_loss(b, reward, k, 0.0, beta)
    assert torch.equal(shaped, reward), 'call cost 0 must leave the signal bitwise the reward'
    assert float(v1_loss.detach()) == float(v3_loss.detach()), \
        (float(v1_loss.detach()), float(v3_loss.detach()))
    assert float(mean_entropy.detach()) == float(v3_entropy.detach())
    grads = []
    for loss in (v1_loss, v3_loss):
        model.zero_grad(set_to_none=True)
        loss.backward(retain_graph=True)
        grads.append([p.grad.detach().clone() for p in model.parameters()])
    model.zero_grad(set_to_none=True)
    assert all(torch.equal(x, y) for x, y in zip(*grads)), 'the gradients differ'
    return 'identical episodes, identical loss and identical gradients at cap 4, call cost 0'


def test_call_cost_carried_over():
    reward = torch.tensor([1., 0., 1., 0.])
    calls = torch.tensor([2, 3, 1, 4])
    assert torch.equal(V3.shaped_signal(reward, calls, 0.0), reward)
    assert V3.shaped_signal is V3.V2.shaped_signal
    shaped = V3.shaped_signal(reward, calls, 0.01)
    assert torch.allclose(shaped, reward - 0.01 * calls.float())
    return 'v2.shaped_signal, unchanged'


# --------------------------------------------------------------------------- operator audit


def test_operator_answers_the_audited_chains():
    operator = V3.make_operator(OPERATOR)
    before = operator.fingerprint
    total = correct = 0
    for cell in ('k1-held', 'k3-held', 'k5-held', 'k8-held', 'k8-prac', 'p6-k3-held'):
        units = [V3.make_unit(cell, i) for i in range(8)]
        hits = V3.operator_on_chains(operator, units, 'a')
        assert len(hits) == len(units)
        assert all(len(h) == V3.CELLS[cell]['hops'] for h in hits)
        total += sum(len(h) for h in hits)
        correct += sum(sum(h) for h in hits)
    assert operator.fingerprint == before, 'the operator weights moved'
    assert correct == total, f'the frozen operator missed {total - correct}/{total} stages'
    return f'frozen operator {correct}/{total} chain stages correct, weights unchanged'


def test_diagnose_intervention_is_bounded_to_the_true_chain():
    units, tokens, present, table, visit_of = _batch_for_caps(hops=3, n=4)
    hops = torch.tensor([3] * len(units), dtype=torch.long)
    width = tokens.shape[1]
    policy = V3.intervention_policy('force_subject', hops, width)
    inside = policy(2, tokens, torch.zeros(len(units), 8, dtype=torch.long),
                    torch.full((len(units),), 2, dtype=torch.long))
    beyond = policy(3, tokens, torch.zeros(len(units), 8, dtype=torch.long),
                    torch.full((len(units),), 3, dtype=torch.long))
    assert bool(inside['subject'][1].all()), 'step 2 of a 3-hop chain must be forced'
    assert not bool(beyond['subject'][1].any()), 'step 3 must be free (the v2 artefact)'
    assert 'operation' not in inside and 'stop' not in inside
    return 'force_subject binds only while step < hops'


# --------------------------------------------------------------------------- run


CHECKS = [
    ('world builder', test_world_builder),
    ('distinct-chain sampler', test_distinct_chain_sampler),
    ('interpreters agree with the recorded truth', test_interpreters_agree),
    ('every cell audits clean, no duplicate semantics', test_all_cells_audit_clean),
    ('twin pairs are exact', test_pair_twins),
    ('training stream', test_training_stream),
    ('training stream respects --train-hops', test_training_stream_respects_hop_list),
    ('training worlds have one LINK per person', test_training_worlds_have_one_link_each),
    ('cap 4 and cap 16 give identical step-1..4 logits', test_cap4_and_cap16_logits_identical),
    ('cap equivalence end to end', test_cap_equivalence_end_to_end),
    ('over_cap is a failure', test_over_cap_is_a_failure),
    ('a correct policy is sufficient through eight hops', test_correct_policy_is_sufficient),
    ('the first-result rule is separable', test_first_result_policy_separates_the_rules),
    ('ablation flags touch only their own feature',
     test_ablation_flags_touch_only_their_own_feature),
    ('v3 executor and update == v1 at cap 4', test_v3_rollout_matches_v1_at_cap_four),
    ('call cost carried over from v2', test_call_cost_carried_over),
    ('frozen operator answers the audited chains', test_operator_answers_the_audited_chains),
    ('diagnose interventions are bounded', test_diagnose_intervention_is_bounded_to_the_true_chain),
]


def main():
    V3.configure()
    for name, function in CHECKS:
        check(name, function)
    if FAILED:
        print(json.dumps(dict(failed=[name for name, _ in FAILED])), flush=True)
        raise SystemExit(f'{len(FAILED)} CHECKS FAILED')
    print(f'ALL {PASSED} CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
