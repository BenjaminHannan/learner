"""Checks for the eval-only scale probe. Plain script; no test framework.

Run:  PY -B tests/test_fable_scale_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import fable_scale_probe as S          # noqa: E402

A, C, torch = S.A, S.C, S.torch

CHECKS = 0


def check(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED: {label}')
    print(f'ok  {CHECKS:2d}  {label}', flush=True)


def small(people=6, k=3, relation='heldout', mult=1, n=32, tag='test'):
    level = dict(id=f'{tag}-p{people}-k{k}-{relation}-f{mult}', people=people, k=k,
                 relation=relation, filler_mult=mult, axes=['test'], n=n)
    return level, *S.build_level(level)


def main():
    S.configure()

    # ------------------------------------------------------------ 1. world structure
    import random
    for people in (2, 6, 12, 16):
        for mult in (1, 8):
            rng = random.Random(f'world-structure:{people}:{mult}')
            rows, ents, attr, friend = S.build_world(rng, people, mult)
            links = [r for r in rows if len(r) >= 4 and r[0] == S.WORLD
                     and S.ENTITY_MIN <= r[1] < S.ENTITY_MAX and r[2] == S.LINK]
            subjects = [r[1] for r in links]
            assert len(links) == people, (people, mult, len(links))
            assert sorted(subjects) == sorted(S.VOCAB_SIZE + e for e in ents)
            assert len(set(subjects)) == people
            assert all(S.ENTITY_MIN <= r[3] < S.ENTITY_MAX for r in links)
            assert all(r[3] != r[1] for r in links), 'nobody links to themselves'
            attrs = [(r[1], r[2]) for r in rows if len(r) >= 4 and r[0] == S.WORLD
                     and S.ENTITY_MIN <= r[1] < S.ENTITY_MAX and S.FIRST_REL <= r[2] < S.FIRST_REL + S.RELATIONS]
            assert len(attrs) == len(set(attrs)) == people * S.RELATIONS
            fillers = [r for r in rows if not (S.ENTITY_MIN <= r[1] < S.ENTITY_MAX)]
            assert len(fillers) >= S.BASE_DISTRACTORS * mult
    check(True, 'world builder: exactly one LINK per person, one attribute per (person, relation)')

    # scaling the filler multiplier really scales the irrelevant lines
    sizes = []
    for mult in S.FILLER_MULTS:
        rng = random.Random(f'filler-scale:{mult}')
        rows, ents, *_ = S.build_world(rng, 6, mult)
        sizes.append(len([r for r in rows if not (S.ENTITY_MIN <= r[1] < S.ENTITY_MAX)]))
    check(all(b > a for a, b in zip(sizes, sizes[1:])) and sizes[-1] > 4 * sizes[0],
          f'filler multiplier scales irrelevant lines: {sizes}')

    # ------------------------------------------------------------ 2. interpreter == truth_paths
    for people, k, relation in ((6, 1, 'practised'), (6, 4, 'heldout'), (12, 7, 'practised'),
                                (16, 10, 'heldout')):
        level, chunks, questions = small(people, k, relation, n=32, tag='interp')
        for chunk in chunks:
            x = chunk['inputs']
            paths = A.truth_paths(x)
            memory = x.memory.tolist()
            for i, (owner, eligible, q) in enumerate(
                    zip(x.owner.tolist(), x.eligible.tolist(), x.questions.tolist())):
                assert S.interpret(memory[owner], eligible, q) == paths[i]
        assert all(len(q['truth_path']) == k for q in questions)
    check(True, 'built panels: independent interpreter equals A.truth_paths on every question')

    report = S.audit_registered()
    check(sum(r['questions_checked'] for r in report.values()) == 2048
          and all(r['mismatches'] == 0 for r in report.values()),
          f'registered panels: 0 mismatches over {sum(r["questions_checked"] for r in report.values())} questions')

    # ------------------------------------------------------------ 3. question token layout
    for k in (1, 2, 5, 10):
        for relation in ('practised', 'heldout'):
            level, chunks, questions = small(6, k, relation, n=32, tag='layout')
            for q in questions:
                tokens = q['question']
                assert len(tokens) == k + 3, (k, tokens)
                assert tokens[0] == S.QUESTION and tokens[-1] == S.ANSWER
                assert S.ENTITY_MIN <= tokens[1] < S.ENTITY_MAX
                assert tokens[2:2 + k - 1] == [S.LINK] * (k - 1)
                terminal = tokens[-2]
                if relation == 'heldout':
                    assert terminal == S.HELDOUT_REL, (relation, terminal)
                else:
                    assert terminal in S.PRACTISED_RELS, (relation, terminal)
                assert q['operations'] == tokens[2:-1]
                assert len(q['truth_path']) == k
                assert all(S.ENTITY_MIN <= t < S.ENTITY_MAX for t in q['truth_path'][:-1])
                assert S.FIRST_REL + S.RELATIONS + 1 <= q['truth_path'][-1] < S.VOCAB_SIZE
    check(True, 'k-hop question layout: [QUESTION, ent, LINK*(k-1), relation, ANSWER] and typed truth path')

    # ------------------------------------------------------------ 4. cycle / distinct bookkeeping
    stages = [dict(entity=52, operation=S.LINK, target=53),
              dict(entity=53, operation=S.LINK, target=52),
              dict(entity=52, operation=8, target=12)]
    stats = S.chain_stats(stages)
    assert stats == dict(chain=[52, 53, 52], distinct_people=2, revisits=True), stats
    stats = S.chain_stats(stages[:2])
    assert stats == dict(chain=[52, 53], distinct_people=2, revisits=False), stats

    seen_revisit = seen_simple = False
    for people, k in ((6, 6), (16, 10)):
        level, chunks, questions = small(people, k, 'practised', n=64, tag='cycles')
        for q in questions:
            chain = q['chain']
            assert len(chain) == k
            assert chain[0] == q['subject']
            assert q['distinct_people'] == len(set(chain))
            assert q['revisits'] == (len(set(chain)) != k)
            # the chain must follow the link facts, and the walk must be a true functional walk
            for a, b in zip(chain, chain[1:]):
                assert b in range(S.ENTITY_MIN, S.ENTITY_MAX)
            assert chain[1:] == q['truth_path'][:k - 1]
            seen_revisit |= q['revisits']
            seen_simple |= not q['revisits']
    check(seen_revisit and seen_simple,
          'cycle/distinct bookkeeping matches the walk, and both splits are populated')

    # ------------------------------------------------------------ 5. no label/path leakage
    level, chunks, questions = small(6, 4, 'heldout', n=32, tag='leak')
    x = chunks[0]['inputs']
    metas = chunks[0]['meta']
    fields = tuple(S.data.Inputs.__dataclass_fields__)
    check(fields == ('memory', 'questions', 'owner', 'eligible'),
          f'Inputs carries exactly the four visible tensors: {fields}')

    model, fingerprint, _ = S.load_checkpoint(1)
    seen = []

    def observer(inputs, logits):
        seen.append((inputs, logits.argmax(-1).tolist()))

    result = A.execute(model, x, observer=observer)
    assert len(seen) == 4
    for inputs, _pred in seen:
        assert inputs.memory is x.memory, 'executor re-used the untouched visible memory tensor'
        assert inputs.questions.shape[1] == 4
        q = inputs.questions.tolist()
        assert all(row[0] == S.QUESTION and row[3] == S.ANSWER for row in q)
    depth0 = [row[1] for row in seen[0][0].questions.tolist()]
    assert depth0 == [m['subject'] for m in metas], 'depth 0 entity is the visible question subject'
    for d in range(3):
        supplied = [row[1] for row in seen[d + 1][0].questions.tolist()]
        available = [t for t in seen[d][1] if S.ENTITY_MIN <= t < S.ENTITY_MAX]
        assert sorted(supplied) == sorted(available), (d, supplied, available)
    check(True, 'A.execute: every canonical entity is the model\'s own previous emission, never gold')

    answers = {m['target'] for m in metas}
    supplied_tokens = {t for inputs, _ in seen for row in inputs.questions.tolist() for t in row}
    check(not (answers & supplied_tokens), 'no gold answer token is ever fed back into a canonical call')

    # Reconstruct the executor's active sets and confirm each supplied entity is the
    # model's own emission, including where that emission is WRONG (no silent repair).
    active, repairs = list(range(len(metas))), 0
    for d in range(3):
        emissions = [result['emitted'][i][d] for i in active]
        active = [i for i, t in zip(active, emissions) if S.ENTITY_MIN <= t < S.ENTITY_MAX]
        expected = [result['emitted'][i][d] for i in active]
        supplied = [row[1] for row in seen[d + 1][0].questions.tolist()]
        assert supplied == expected, (d, supplied, expected)
        for i, value in zip(active, supplied):
            gold = metas[i]['truth_path'][d]
            if value != gold:
                repairs += 1
            assert value == result['emitted'][i][d]
    check(True, f'supplied entities equal the model\'s own emissions in call order '
                f'({repairs} of them differ from gold on seed 1)')

    # The same property under real errors: seed 0 is under-trained, so wrong entities
    # must be carried forward rather than silently replaced by the gold path.
    level0, chunks0, questions0 = small(16, 5, 'heldout', n=64, tag='leak0')
    x0, metas0 = chunks0[0]['inputs'], chunks0[0]['meta']
    weak, weak_fp, _ = S.load_checkpoint(0)
    seen0 = []
    result0 = A.execute(weak, x0, observer=lambda i, l: seen0.append((i, l.argmax(-1).tolist())))
    active, carried = list(range(len(metas0))), 0
    for d in range(4):
        emissions = [result0['emitted'][i][d] for i in active]
        active = [i for i, t in zip(active, emissions) if S.ENTITY_MIN <= t < S.ENTITY_MAX]
        supplied = [row[1] for row in seen0[d + 1][0].questions.tolist()]
        assert supplied == [result0['emitted'][i][d] for i in active], d
        carried += sum(1 for i, v in zip(active, supplied) if v != metas0[i]['truth_path'][d])
    assert C.fingerprint(weak) == weak_fp
    check(carried > 0, f'under-trained seed 0: {carried} wrong entities carried forward unrepaired')

    calls = []
    native_forward = model.forward

    def recording_forward(inputs, **kw):
        calls.append(inputs)
        return native_forward(inputs, **kw)

    model.forward = recording_forward
    try:
        A.execute(model, x)
        model(x)
    finally:
        model.forward = native_forward
    check(all(type(c).__name__ == 'Inputs' and not hasattr(c, 'answer') and not hasattr(c, 'gold')
              for c in calls) and len(calls) == 5,
          f'model.forward received only Inputs objects on all {len(calls)} calls')

    rows_per_world = metas[0]['memory_rows']
    tail = x.memory[:, rows_per_world:, :]
    check(int(tail.abs().sum()) == 0 and tail.shape[1] == S.QUESTIONS_PER_WORLD,
          'the question rows held in memory are all-zero: no question text is stored as a fact')
    own_line = [rows_per_world + (m['index'] % S.QUESTIONS_PER_WORLD) for m in metas]
    check(all(not bool(x.eligible[i][line]) and not bool(x.eligible[i][line:].any())
              for i, line in enumerate(own_line)),
          'eligibility stops strictly before each question line')
    memory_tokens = set(x.memory.flatten().tolist())
    check(S.ANSWER not in memory_tokens and S.QUESTION not in memory_tokens,
          'no QUESTION/ANSWER token appears anywhere in the memory tensor')

    # ------------------------------------------------------------ 6. weights unchanged
    before = {s: S.load_checkpoint(s)[1] for s in S.SEEDS}
    models = {}
    for s in S.SEEDS:
        m, f, sha = S.load_checkpoint(s)
        models[s] = (m, f, sha)
        assert f == before[s]
        S.score_level(m, chunks)
        assert C.fingerprint(m) == f, f'weights changed for seed {s}'
    check(True, f'all three checkpoints: fingerprint identical before and after scoring')

    saved_now = {s: C.sha(S.SCREEN / f'astra_canonical_operator_seed-{s}/final.pt') for s in S.SEEDS}
    check(all(models[s][2] == saved_now[s] for s in S.SEEDS),
          'checkpoint files on disk are byte-identical after the probe')

    # ------------------------------------------------------------ 7. determinism
    for people, k, relation, mult in ((6, 2, 'practised', 1), (16, 5, 'heldout', 1), (6, 3, 'heldout', 4)):
        a = small(people, k, relation, mult, n=64, tag='det')
        b = small(people, k, relation, mult, n=64, tag='det')
        assert S.panel_hash(a[1]) == S.panel_hash(b[1])
        assert [q['truth_path'] for q in a[2]] == [q['truth_path'] for q in b[2]]
    different = S.panel_hash(small(6, 2, 'practised', 1, n=64, tag='det')[1]) != \
        S.panel_hash(small(6, 2, 'practised', 1, n=64, tag='other')[1])
    check(different, 'regeneration is deterministic per level id, and distinct ids differ')

    print(f'ALL {CHECKS} CHECKS PASSED', flush=True)


if __name__ == '__main__':
    main()
