"""Checks for scripts/fable_dispatcher_v4.py.  Plain script; no pytest.

Run:
    python3.12 -B tests/test_fable_dispatcher_v4.py

Knobs (all optional):
    FABLE_V4_ORACLE_N=64    units per cell for the action-space sufficiency check
                            (default 64 -- the registered panel size -- on a THROWAWAY
                            panel namespace; lower it to make the file faster)
    FABLE_V4_SKIP_SMOKE=1   skip the 20-update-per-arm training smoke
    FABLE_V4_TMP=<dir>      where the smoke runs write

Nothing here reads, writes or scores against the frozen registered panels at
artifacts/fable-dispatcher-v3-20260920/panels.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v3 as V3                                            # noqa: E402
import fable_dispatcher_v4 as V4                                            # noqa: E402

torch = V4.torch
OPERATOR = ('/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/'
            'astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt')

PASSED = 0
FAILED = []


def check(name, function):
    global PASSED
    started = time.monotonic()
    try:
        detail = function()
    except Exception as exc:                                    # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}  [{time.monotonic() - started:.1f}s]' + (f'  {detail}' if detail else ''),
          flush=True)


# --------------------------------------------------------------------------- fixtures


def _batch(hops=4, n=6, people=16, seed='v4-batch'):
    """A hand-built batch of distinct-chain questions plus an oracle lookup table."""
    units = []
    for index in range(n):
        rng = random.Random(f'{seed}:{hops}:{index}')
        while True:
            world = V3.build_world(rng, people)
            askers = V3.distinct_askers(world, hops)
            if askers:
                break
        asker = rng.choice(askers)
        units.append(dict(index=index, kind='single',
                          a=V3.make_side(world, asker, hops, V3.HELDOUT_REL)))
    inputs, questions = V3.pack_side(units, 'a')
    operator = V4.OracleOperator()
    table = operator.table(inputs, list(range(len(units))))
    tokens, present = V4.pad_questions(questions)
    return units, tokens, present, table, torch.arange(len(units))


def _training_batch(seed='v4-train', visits=3, hops=(1, 2, 3)):
    rng = random.Random(f'{V4.TRAIN_NAMESPACE}:{seed}')
    inputs, questions, owners, answers, _meta = V3.training_visits(rng, visits, 6, hops)
    reps, visit_of = V4.representatives(owners)
    operator = V4.OracleOperator()
    table = operator.reachable_table(inputs, reps)
    tokens, present = V4.pad_questions(questions)
    return tokens, present, table, visit_of, answers


# --------------------------------------------------------------------------- v3-repro exactness


def test_v3_repro_parameters_identical():
    for seed in (0, 1, 2, 996001):
        torch.manual_seed(seed)
        three = V1.Dispatcher(width=32, absolute_positions=False)
        torch.manual_seed(seed)
        four = V4.build_model(width=32, flags=V4.flags_for_arm('v3-repro'))
        a, b = three.state_dict(), four.state_dict()
        assert sorted(a) == sorted(b), (sorted(a), sorted(b))
        for key in a:
            assert torch.equal(a[key], b[key]), f'seed {seed}: parameter {key} differs'
        assert four.parameters_count() == three.parameters_count() == 15522
    return '4 seeds, byte-identical state dicts, 15,522 parameters'


def test_v3_repro_logits_identical():
    """Same batch, same seed, same generator: every recorded logit and state is equal.

    Two runs per version.  A random controller picks an illegal subject almost at once,
    which ends every episode at step 0 and records nothing, so the LOGIT comparison runs
    under the correct forcing policy (legal actions, six recorded steps); a second,
    completely free sampled run then compares the whole `Rollout`.
    """
    units, tokens, present, table, visit_of = _batch(hops=6, n=6)
    hops = torch.tensor([6] * len(units), dtype=torch.long)
    traces, free = {}, {}
    for label in ('v3', 'v4'):
        torch.manual_seed(97)
        model = (V1.Dispatcher(width=32) if label == 'v3'
                 else V4.build_model(flags=V4.flags_for_arm('v3-repro')))
        record = []
        run = (lambda *a, **k: V3.rollout_v3(*a, **k)) if label == 'v3' else \
            (lambda *a, **k: V4.rollout_v4(*a, flags=V4.flags_for_arm('v3-repro'), **k))
        run(model, tokens, present, table, visit_of, 16, mode='greedy',
            policy=V3.correct_policy(hops, tokens.shape[1]), record=record)
        traces[label] = record
        generator = torch.Generator().manual_seed(4242)
        free[label] = run(model, tokens, present, table, visit_of, 16, mode='sample',
                          generator=generator)
    ra, rb = traces['v3'], traces['v4']
    assert len(ra) == len(rb) == 6, (len(ra), len(rb))
    for step, (x, y) in enumerate(zip(ra, rb)):
        for head in ('subject', 'operation', 'stop', 'state'):
            assert torch.equal(x[head], y[head]), f'step {step}: {head} differs'
        assert torch.equal(x['active'], y['active'])
        assert y['gate'] is None, 'the v3-repro arm must log no write gate'
    ea, eb = free['v3'], free['v4']
    assert ea.status == eb.status and ea.transcripts == eb.transcripts
    assert ea.pointers == eb.pointers
    assert torch.equal(ea.answer, eb.answer) and torch.equal(ea.calls, eb.calls)
    assert torch.equal(ea.logprob, eb.logprob) and torch.equal(ea.entropy, eb.entropy)
    assert torch.equal(ea.decisions, eb.decisions)
    return f'{len(ra)} recorded steps bitwise equal, plus an identical free sampled episode'


def test_v3_repro_gradients_and_update_identical():
    """One full RLOO update: identical gradients and identical AdamW parameter update."""
    tokens, present, table, visit_of, answers = _training_batch()
    k, beta, call_cost = 8, 0.2, 0.01
    repeat = torch.arange(tokens.shape[0]).repeat_interleave(k)
    after, grads = {}, {}
    for label in ('v3', 'v4'):
        torch.manual_seed(31)
        model = (V1.Dispatcher(width=32) if label == 'v3'
                 else V4.build_model(flags=V4.flags_for_arm('v3-repro')))
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, betas=(.9, .99), eps=1e-8,
                                      weight_decay=.01)
        generator = torch.Generator().manual_seed(9_000_000)
        if label == 'v3':
            episodes = V3.rollout_v3(model, tokens[repeat], present[repeat], table,
                                     visit_of[repeat], 4, mode='sample', generator=generator)
        else:
            episodes = V4.rollout_v4(model, tokens[repeat], present[repeat], table,
                                     visit_of[repeat], 4, mode='sample', generator=generator,
                                     flags=V4.flags_for_arm('v3-repro'))
        reward = (episodes.answer == answers[repeat]).float()
        loss, _shaped, _entropy = V3.policy_gradient_loss(episodes, reward, k, call_cost, beta)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grads[label] = {n: p.grad.detach().clone() for n, p in model.named_parameters()}
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        after[label] = {n: p.detach().clone() for n, p in model.named_parameters()}
    assert sorted(grads['v3']) == sorted(grads['v4'])
    for name in grads['v3']:
        assert torch.equal(grads['v3'][name], grads['v4'][name]), f'gradient {name} differs'
        assert torch.equal(after['v3'][name], after['v4'][name]), f'updated {name} differs'
    return f'{len(after["v3"])} tensors: identical gradients and identical AdamW step, tolerance 0'


# --------------------------------------------------------------------------- the replaced features


def test_replaced_features_are_deleted_from_the_module():
    both = V4.build_model(flags=V4.flags_for_arm('reg+ctx'))
    names = dict(both.named_parameters())
    for dead in ('recent.weight', 'offset_op.weight', 'offset_subject.weight'):
        assert dead not in names, f'{dead} still exists in the reg+ctx model'
    assert not hasattr(both, 'recent') and not hasattr(both, 'offset_op')
    assert not hasattr(both, 'offset_subject')
    reg = V4.build_model(flags=V4.flags_for_arm('reg'))
    assert not hasattr(reg, 'recent') and hasattr(reg, 'offset_op')
    ctx = V4.build_model(flags=V4.flags_for_arm('ctx'))
    assert hasattr(ctx, 'recent') and not hasattr(ctx, 'offset_op')
    return 'reg deletes the recency embedding, ctx deletes both offset embeddings'


def _mid_episode_state(cap=4, hops=5, n=4):
    """A realistic mid-episode feature state: three results in the transcript and both
    previous pointers set, i.e. the situation in which v3's two hints carry the most."""
    units, tokens, present, table, visit_of = _batch(hops=hops, n=n)
    batch = tokens.shape[0]
    results = torch.tensor([[60, 57, 55, 0]] * batch, dtype=torch.long)
    n_results = torch.full((batch,), 3, dtype=torch.long)
    previous_op = torch.full((batch,), 3, dtype=torch.long)
    previous_subject = torch.full((batch,), 1, dtype=torch.long)
    return (tokens, present, results, n_results, previous_op, previous_subject, cap)


def test_no_recency_and_no_offset_reaches_the_network():
    """With both flags on, poisoning the two replaced feature channels must be a no-op."""
    flags = V4.flags_for_arm('reg+ctx')
    state = _mid_episode_state()
    tokens, present, cap = state[0], state[1], state[6]
    torch.manual_seed(5)
    model = V4.build_model(flags=flags)
    context = model.candidate_context(model.question_context(tokens, present), cap)
    features = V4.candidate_features_v4(*state, flags, context)
    assert bool((features['recent'] == 0).all()), 'the recency channel is not inert'
    for name in ('offset_op', 'offset_subject'):
        assert bool((features[name] == V4.OFFSET_NA).all()), f'{name} is not inert'
    base = model.candidate_keys(features)
    torch.manual_seed(1234)
    for trial in range(8):
        poisoned = dict(features)
        poisoned['recent'] = torch.randint(0, 2, features['recent'].shape)
        poisoned['offset_op'] = torch.randint(0, V4.OFFSET_SLOTS, features['offset_op'].shape)
        poisoned['offset_subject'] = torch.randint(0, V4.OFFSET_SLOTS,
                                                   features['offset_subject'].shape)
        after = model.candidate_keys(poisoned)
        assert torch.equal(base, after), f'trial {trial}: a poisoned replaced feature moved the keys'
    # ... and the identical poison DOES move v3's keys, so the check has teeth
    torch.manual_seed(5)
    three = V1.Dispatcher(width=32)
    v3_features = V3.candidate_features_v3(*state)
    v3_base = three.candidate_keys(v3_features)
    for name, high in (('recent', 2), ('offset_op', V4.OFFSET_SLOTS),
                       ('offset_subject', V4.OFFSET_SLOTS)):
        moved = dict(v3_features)
        moved[name] = torch.randint(0, high, v3_features[name].shape)
        assert not torch.equal(v3_base, three.candidate_keys(moved)), \
            f'poisoning {name} left v3 unchanged; the poison is not a real poison'
    return '8 random poisons of recent/offset_op/offset_subject: keys bit-identical (v3 all move)'


def test_repeated_link_candidates_are_separated_only_by_the_new_encoder():
    """The reviewer's diagnosis, and the fix, as one measurement.

    In a k-hop question the k-1 LINK positions carry the same token.  Without the
    offsets (v3's --no-offsets ablation) their candidate keys are IDENTICAL, so the
    operation pointer cannot tell them apart.  The contextual encoder must separate
    them -- at k = 8, a length the training stream never contains.
    """
    hops = 8
    units, tokens, present, table, visit_of = _batch(hops=hops, n=4)
    batch, width = tokens.shape
    cap = 4
    results = torch.zeros(batch, cap, dtype=torch.long)
    n_results = torch.zeros(batch, dtype=torch.long)
    none = torch.full((batch,), -1, dtype=torch.long)
    link_positions = [p for p in range(2, 2 + hops - 1)]
    assert all(int(tokens[0, p]) == V4.LINK for p in link_positions), tokens[0].tolist()

    # v3's --no-offsets ablation, exactly: the repeated LINK keys are literally equal
    torch.manual_seed(5)
    blind = V1.Dispatcher(width=32)
    previous = torch.full((batch,), 3, dtype=torch.long)
    features = V3.candidate_features_v3(tokens, present, results, n_results, previous, previous,
                                        cap, no_offsets=True)
    keys = blind.candidate_keys(features)
    for p in link_positions[1:]:
        assert torch.equal(keys[:, link_positions[0]], keys[:, p]), \
            'v3 without offsets should give every repeated LINK the same key'

    torch.manual_seed(5)
    model = V4.build_model(flags=V4.flags_for_arm('reg+ctx'))
    context = model.candidate_context(model.question_context(tokens, present), cap)
    features = V4.candidate_features_v4(tokens, present, results, n_results, none, none, cap,
                                        V4.flags_for_arm('reg+ctx'), context)
    keys = model.candidate_keys(features)
    gaps = []
    for i, p in enumerate(link_positions):
        for q in link_positions[i + 1:]:
            gap = float((keys[:, p] - keys[:, q]).detach().abs().max())
            assert gap > 1e-6, f'the encoder gave LINK positions {p} and {q} the same key'
            gaps.append(gap)
    return (f'k=8: {len(link_positions)} repeated LINK positions collide without the encoder, '
            f'all {len(gaps)} pairs separated with it (min gap {min(gaps):.3g})')


def test_context_encoder_has_no_per_index_parameter():
    """No parameter's shape depends on the question length, and the encoder runs at any
    length -- the property the abandoned absolute-position arm did not have."""
    model = V4.build_model(flags=V4.flags_for_arm('ctx'))
    assert not hasattr(model, 'absolute'), 'v4 must carry no per-slot position embedding'
    allowed = {32, 64, 96, 48, 16, 2, 68, 3 * 32}
    for name, parameter in model.named_parameters():
        assert set(parameter.shape) <= allowed, f'{name} {tuple(parameter.shape)}'
    shapes = {}
    for hops in (1, 3, 8):
        units, tokens, present, _table, _visit = _batch(hops=hops, n=3)
        context = model.question_context(tokens, present)
        assert context.shape == (tokens.shape[0], tokens.shape[1], 32)
        shapes[hops] = tokens.shape[1]
    qs = [[V4.QUESTION, 55, V4.LINK, V4.LINK, 9, V4.ANSWER],
          [V4.QUESTION, 61, V4.LINK, V4.LINK, 8, V4.ANSWER]]
    width = len(qs[0])
    tight = torch.tensor(qs, dtype=torch.long)
    tight_mask = torch.ones(2, width, dtype=torch.bool)
    padded = torch.zeros(2, 12, dtype=torch.long)
    mask = torch.zeros(2, 12, dtype=torch.bool)
    padded[:, :width] = tight
    mask[:, :width] = True
    context = model.question_context(padded, mask)
    assert bool((context[:, width:] == 0).all()), 'padded positions must be zeroed'
    # same batch size, so any difference is the padding itself and not a BLAS path
    assert torch.equal(model.question_context(tight, tight_mask), context[:, :width]), \
        'right padding changed a real position'
    return f'no length-shaped parameters; widths {shapes}; padding inert and position-exact'


# --------------------------------------------------------------------------- the register


def test_write_gate_is_in_the_unit_interval_and_logged():
    flags = V4.flags_for_arm('reg+ctx')
    units, tokens, present, table, visit_of = _batch(hops=5, n=6)
    torch.manual_seed(17)
    model = V4.build_model(flags=flags)
    gates, record = [], []
    hops = torch.tensor([5] * len(units), dtype=torch.long)
    V4.rollout_v4(model, tokens, present, table, visit_of, 8, mode='greedy',
                  policy=V3.correct_policy(hops, tokens.shape[1]), flags=flags,
                  gates=gates, record=record)
    assert gates, 'no write gate was logged'
    assert len(gates) == len(record)
    for row, logged in zip(record, gates):
        assert row['gate'] is not None and torch.equal(row['gate'], logged['gate'])
        assert row['gate'].shape == (len(units),)
        assert bool((logged['gate'] > 0).all()) and bool((logged['gate'] < 1).all()), \
            'a write gate left the open unit interval'
    summary = V4.gate_summary(gates)
    assert 0 < summary['min'] <= summary['mean'] <= summary['max'] < 1
    assert summary['n'] == sum(int(row['active'].sum()) for row in gates)
    off = V4.build_model(flags=V4.flags_for_arm('ctx'))
    empty = []
    V4.rollout_v4(off, tokens, present, table, visit_of, 8, mode='greedy',
                  flags=V4.flags_for_arm('ctx'), gates=empty)
    assert empty == [], 'a non-register arm logged a gate'
    return (f'{summary["n"]} gate values in (0,1); mean {summary["mean"]:.3f}, '
            f'range [{summary["min"]:.3f}, {summary["max"]:.3f}]')


def test_register_starts_neutral_and_then_moves():
    """r starts at the learned zero `register_start`, so step 0 is v3's computation; after
    the first call the register must actually change the pointer query."""
    flags = V4.flags_for_arm('reg')
    torch.manual_seed(23)
    model = V4.build_model(flags=flags)
    assert bool((model.register_start == 0).all())
    batch = 4
    state = torch.randn(batch, 32)
    register = model.initial_register(batch)
    assert torch.equal(model.pointer_state(state, register), state), \
        'the first step must be numerically v3'
    result = torch.randint(V4.ENTITY_MIN, V4.ENTITY_MAX, (batch,))
    moved, gate = model.update_register(state, register, result)
    assert not torch.equal(moved, register), 'the register never moved'
    assert gate.shape == (batch,)
    assert not torch.equal(model.pointer_state(state, moved), state), \
        'the moved register does not reach the pointer query'
    keys = torch.randn(batch, 7, 32)
    slots = torch.ones(batch, 7, dtype=torch.bool)
    assert not torch.equal(model.subject_logits(state, keys, slots),
                           model.subject_logits(model.pointer_state(state, moved), keys, slots)), \
        'the register does not change the subject logits'
    assert torch.equal(model.stop_logits(state), model.stop_logits(state))
    return 'r starts at zero (step 0 == v3), moves after the first call, reaches the queries'


# --------------------------------------------------------------------------- no story tokens


def test_dispatcher_never_sees_story_tokens():
    """Structural: no entry point takes a story.  Dynamic: the only story-derived value
    that changes anything is the result token of a call the model actually made."""
    forbidden = ('memory', 'eligible', 'hops', 'inputs', 'answer_token', 'gold')
    signature = inspect.signature(V4.rollout_v4).parameters
    assert set(signature) & set(forbidden) == set(), sorted(signature)
    assert sorted(p for p in signature if p not in ('mode', 'generator', 'policy', 'flags',
                                                    'record', 'gates')) == \
        ['cap', 'model', 'present', 'table', 'tokens', 'visit_of'], sorted(signature)
    for name, method in inspect.getmembers(V4.DispatcherV4, inspect.isfunction):
        if name.startswith('_'):
            continue
        assert not set(inspect.signature(method).parameters) & set(forbidden), name

    flags = V4.flags_for_arm('reg+ctx')
    units, tokens, present, table, visit_of = _batch(hops=4, n=6)
    torch.manual_seed(29)
    model = V4.build_model(flags=flags)
    clean = V4.rollout_v4(model, tokens, present, table, visit_of, 8, mode='greedy', flags=flags)
    # every lookup the model's OWN greedy episode actually performed
    touched = torch.zeros_like(table, dtype=torch.bool)
    calls = 0
    for i, transcript in enumerate(clean.transcripts):
        for subject, op, _result in transcript:
            touched[int(visit_of[i]), subject - V4.ENTITY_MIN, int(V1.OP_INDEX[op])] = True
            calls += 1
    assert calls > 0, 'the episode made no calls, so the test would be vacuous'
    torch.manual_seed(31)
    noise = torch.randint(0, V4.VOCAB, table.shape, dtype=table.dtype)
    noisy = torch.where(touched, table, noise)
    changed = int((noisy != table).sum())
    assert changed > 0
    dirty = V4.rollout_v4(model, tokens, present, noisy, visit_of, 8, mode='greedy', flags=flags)
    assert clean.transcripts == dirty.transcripts, 'an uncalled story fact changed the episode'
    assert torch.equal(clean.answer, dirty.answer) and clean.status == dirty.status
    assert clean.pointers == dirty.pointers
    return (f'no story argument on any entry point; {changed} randomised never-called lookup-table '
            f'entries left all {calls} calls and every pointer identical')


# --------------------------------------------------------------------------- action space


def test_action_space_still_suffices_on_every_cell():
    """A blank model under the correct forcing policy: is the v4 action space still
    enough to walk every one of the 25 cell types perfectly?  Throwaway panel, so this
    never touches the frozen registered panels.
    """
    n = int(os.environ.get('FABLE_V4_ORACLE_N', '64'))
    panels = V4.throwaway_panels(n=n)
    assert len(panels) == 25, len(panels)
    operator = V4.OracleOperator()
    detail = []
    for arm in V4.ARMS:
        flags = V4.flags_for_arm(arm)
        torch.manual_seed(5)
        model = V4.build_model(flags=flags)
        for cell, panel in panels.items():
            cfg = V3.CELLS[cell]
            sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
            rows = {}
            for side in sides:
                hops_of = lambda hops, width: V3.correct_policy(hops, width)
                rows[side] = V4.score_side_v4(model, operator, panel['units'], side,
                                              V4.EVAL_CAP, flags, hops_of)
            counts = V3.aggregate(rows, len(panel['units']), cfg)
            assert counts['strict'] == n, f'{arm} {cell}: strict {counts["strict"]}/{n}'
            assert counts['answers'] == n, f'{arm} {cell}: answers {counts["answers"]}/{n}'
            assert counts['over_cap'] == 0 and counts['invalid'] == 0, f'{arm} {cell}: {counts}'
        detail.append(arm)
    return f'throwaway panel, {n}/{n} strict on all 25 cells for all arms: {", ".join(detail)}'


# --------------------------------------------------------------------------- smoke + scoring


def _smoke_args(arm, out, seed=996001, updates=20):
    return argparse.Namespace(arm=arm, operator='oracle', seed=seed, updates=updates, out=str(out),
                              time_cap=600, panels=None, visits=4, train_hops='1,2,3',
                              train_people=6, train_cap=4, k=8, width=32, lr=3e-3, warmup=100,
                              clip=1.0, entropy=.2, entropy_final=.02, call_cost=0.01)


_SMOKE = {}


def _run_smoke(root):
    if _SMOKE:
        return _SMOKE
    for arm in V4.ARMS:
        out = Path(root) / f'smoke-{arm.replace("+", "-")}'
        V4.train(_smoke_args(arm, out))
        record = json.loads((out / 'training.json').read_text())
        _SMOKE[arm] = (out, record)
    return _SMOKE


def test_twenty_update_smoke_per_arm():
    if os.environ.get('FABLE_V4_SKIP_SMOKE'):
        return 'skipped by FABLE_V4_SKIP_SMOKE'
    runs = _run_smoke(TMP)
    lines = []
    for arm, (out, record) in runs.items():
        assert record['updates'] == 20 and record['complete']
        assert record['flags'] == V4.flags_for_arm(arm).as_dict()
        assert record['operator_weights_unchanged']
        log = [json.loads(line) for line in (out / 'train_log.jsonl').read_text().splitlines()]
        assert log, f'{arm}: empty training log'
        has_gate = 'mean_write_gate' in log[0]
        assert has_gate == V4.flags_for_arm(arm).learned_register, \
            f'{arm}: gate logging does not match the arm'
        if has_gate:
            assert 0 < log[0]['mean_write_gate'] < 1
        lines.append(f'{arm} {record["dispatcher_parameters"]}p '
                     f'{record["updates_per_second"]:.2f}u/s')
    assert runs['v3-repro'][1]['dispatcher_parameters'] == 15522
    return '; '.join(lines)


def test_score_diagnose_and_interventions_on_a_v4_checkpoint():
    if os.environ.get('FABLE_V4_SKIP_SMOKE'):
        return 'skipped by FABLE_V4_SKIP_SMOKE'
    runs = _run_smoke(TMP)
    panels = V4.throwaway_panels(n=3)
    small = {cell: panels[cell] for cell in ('k1-prac', 'k4-held', 'pair-link')}
    operator = V4.OracleOperator()
    operators = {'trained_operator': operator, 'oracle_operator': operator}
    detail = []
    for arm, (out, _record) in runs.items():
        config, saved, model, flags = V4.load_checkpoint(out)
        assert flags == V4.flags_for_arm(arm) and saved['arm'] == arm
        gates = [] if flags.learned_register else None
        rows = V4.score_side_v4(model, operator, small['k4-held']['units'], 'a', V4.EVAL_CAP,
                                flags, gates=gates)
        assert len(rows) == 3
        for row in rows:
            assert row['status'] in ('answered', 'invalid_action', 'over_cap')
            assert set(row) >= {'strict_path', 'loose_path', 'transcript', 'pointers', 'calls'}
        if gates is not None:
            assert V4.gate_summary(gates) is None or 0 < V4.gate_summary(gates)['mean'] < 1
        report = V4.diagnose_v4(model, operators, small, V4.EVAL_CAP, flags,
                                note='v4 test', tables=V3.TableCache(operators))
        assert sorted(report['cells']) == sorted(small)
        for cell in small:
            row = report['cells'][cell]['trained_operator']
            assert sorted(row) == sorted(V4.INTERVENTIONS)
            n = len(small[cell]['units'])
            for kind, counts in row.items():
                assert 0 <= counts['answers'] <= n and 0 <= counts['strict'] <= n, (kind, counts)
                assert counts['rows'] == n * report['cells'][cell]['sides']
        detail.append(arm)
    return f'load_checkpoint + score_side_v4 + diagnose_v4 (5 interventions) for {len(detail)} arms'


def test_score_helpers_reject_a_flag_mismatch():
    flags = V4.flags_for_arm('reg+ctx')
    units, tokens, present, table, visit_of = _batch(hops=2, n=2)
    model = V4.build_model(flags=V4.flags_for_arm('v3-repro'))
    try:
        V4.rollout_v4(model, tokens, present, table, visit_of, 4, mode='greedy', flags=flags)
    except ValueError as exc:
        assert 'flags' in str(exc)
        return 'a model/flag mismatch raises instead of silently running the wrong arm'
    raise AssertionError('a flag mismatch was accepted')


# --------------------------------------------------------------------------- run


CHECKS = [
    ('v3-repro parameters are byte-identical to v3', test_v3_repro_parameters_identical),
    ('v3-repro logits are identical to v3, tolerance 0', test_v3_repro_logits_identical),
    ('v3-repro gradients and AdamW update are identical',
     test_v3_repro_gradients_and_update_identical),
    ('the replaced embeddings are deleted, not merely unused',
     test_replaced_features_are_deleted_from_the_module),
    ('no recency flag and no offset feature reaches the network',
     test_no_recency_and_no_offset_reaches_the_network),
    ('repeated LINK candidates are separated only by the new encoder',
     test_repeated_link_candidates_are_separated_only_by_the_new_encoder),
    ('the context encoder has no per-index parameter',
     test_context_encoder_has_no_per_index_parameter),
    ('the write gate is in (0,1) and logged', test_write_gate_is_in_the_unit_interval_and_logged),
    ('the register starts neutral and then moves', test_register_starts_neutral_and_then_moves),
    ('the dispatcher never sees story tokens', test_dispatcher_never_sees_story_tokens),
    ('the action space still suffices on every cell', test_action_space_still_suffices_on_every_cell),
    ('20-update smoke per arm', test_twenty_update_smoke_per_arm),
    ('score, diagnose and interventions on v4 checkpoints',
     test_score_diagnose_and_interventions_on_a_v4_checkpoint),
    ('a model/flag mismatch is refused', test_score_helpers_reject_a_flag_mismatch),
]

TMP = None


def main():
    global TMP
    V4.configure()
    TMP = os.environ.get('FABLE_V4_TMP') or tempfile.mkdtemp(prefix='fable-v4-tests-')
    Path(TMP).mkdir(parents=True, exist_ok=True)
    try:
        for name, function in CHECKS:
            check(name, function)
    finally:
        if not os.environ.get('FABLE_V4_TMP'):
            shutil.rmtree(TMP, ignore_errors=True)
    if FAILED:
        print(json.dumps(dict(failed=[name for name, _ in FAILED])), flush=True)
        raise SystemExit(f'{len(FAILED)} CHECKS FAILED')
    print(f'ALL {PASSED} CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
