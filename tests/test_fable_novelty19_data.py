"""Checks for scripts/fable_novelty19_data.py.  Plain script; no pytest.

Run:
    python3.12 -B tests/test_fable_novelty19_data.py

These are the DATA-SIDE preflight checks of section 9 of
`design/v3/19-novelty-experiment-preregistration-draft.md`: empirical counts match only
awake strings, the length cap rejects rather than repairs, zero composite r=10 exposure,
identical world bytes and order across arms, swapped r=8/9 labels do not change
exclusion logic, candidate failures and fallbacks are reproducible from the seed, the
pair-edit rules hold, the stream is deterministic and chunk-invariant, and the neutral
record round-trips into exactly the tensors the frozen dispatcher-v4 and baseline-v2
training code would have produced for the same world and question.

Everything runs on tiny disposable fixtures at seeds >= 999000.  The registered seeds
1900/1901/1902 and the real development panels are NEVER generated here.  No model is
built, no checkpoint is loaded and no `test.pt` is touched.
"""
from __future__ import annotations

import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_dispatcher_v3 as V3                                            # noqa: E402
import fable_baseline_transformer as B1                                     # noqa: E402
import fable_baseline_transformer_v2 as B2                                  # noqa: E402
import fable_confirmation_panels as CP                                      # noqa: E402
import fable_novelty19_data as N                                            # noqa: E402

torch = N.torch
A = N.A

FIXTURE_SEED = 999101           # disposable; well above B2.DEV_SEED_FLOOR
FIXTURE_NAMESPACE = 'astra-novelty19-devfixture-999101'

PASSED = 0
FAILED = []
SKIPPED = []
TEMP = []
_CACHE = {}


def check(name, function):
    global PASSED
    try:
        detail = function()
    except _Skip as skip:
        SKIPPED.append((name, str(skip)))
        print(f'skip  {name}: {skip}', flush=True)
        return
    except Exception as exc:                                    # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


class _Skip(Exception):
    pass


def scratch(name):
    folder = Path(tempfile.mkdtemp(prefix=f'novelty19-{name}-'))
    TEMP.append(folder)
    return folder


def history_fixture():
    """A DISPOSABLE 2-update operator-history reconstruction.

    The registered wave is 6,000 updates (~21 s); two updates exercise the same code
    path in milliseconds.  `complete` is false for it, so it can never back a
    registered namespace -- which is itself one of the checks below.
    """
    if 'history' not in _CACHE:
        root = scratch('history')
        N.build_operator_history(root / 'operator-history', updates=2, progress=False)
        _CACHE['history'] = root / 'operator-history'
    return _CACHE['history']


def panels_fixture():
    """A tiny dev-panel folder, used as the mandatory exclusion source everywhere.

    One primary (N) cell and one ordinary (F) cell, so `forbidden-worlds-primary.json`
    is populated and the training-side world guard has something to enforce.
    """
    if 'panels' not in _CACHE:
        root = scratch('devpanels')
        N.build_dev_panels(root / 'panels', n=16, namespace=FIXTURE_NAMESPACE,
                           cells={k: N.DEV_CELLS[k] for k in ('N-c4-p6', 'F-c1-r8')},
                           operator_history=history_fixture(),
                           require_full_history=False, progress=False)
        _CACHE['panels'] = root / 'panels'
    return _CACHE['panels']


def fixture():
    """One shared tiny stream + memory + buffers, built once."""
    if 'fixture' not in _CACHE:
        root = scratch('fixture')
        panels = panels_fixture()
        N.build_awake_stream(root / 'stream', FIXTURE_SEED, 12, chunk=4,
                             dev_panels=panels, progress=False)
        N.build_memory(root / 'memory', FIXTURE_SEED, root / 'stream', worlds=64)
        N.build_buffers(root / 'buffers', FIXTURE_SEED, root / 'memory',
                        dev_panels=panels, offline_updates=8, progress=False)
        _CACHE['fixture'] = root
    return _CACHE['fixture']


# --------------------------------------------------------------------------- schema


def test_record_schema_round_trips():
    stories, items, namespaces, source = N.awake_update(FIXTURE_SEED, 0)
    block = N.encode_block('awake', FIXTURE_SEED, 0, namespaces, stories, items, source)
    back = N.decode_block(block)
    assert back['stories'] == stories, 'story rows did not survive the block'
    keys = ('owner', 'question', 'chain', 'hops', 'terminal', 'answer', 'support', 'where')
    for original, decoded in zip(items, back['items']):
        for key in keys:
            assert original[key] == decoded[key], (
                f'{key} changed: {original[key]} != {decoded[key]}')
    assert len(back['items']) == N.AWAKE_VISITS * N.AWAKE_QUESTIONS_PER_WORLD
    return f'{len(stories)} worlds, {len(items)} questions, all {len(keys)} item keys equal'


def test_record_feeds_the_baseline_packer_exactly():
    """`pack_batch` on the record == `pack_batch` on `training_items`' own output."""
    rng = random.Random(f'{N.NS_AWAKE}:{FIXTURE_SEED}:0:0')
    want_stories, want_items = B1.training_items(rng, visits=1, people=N.AWAKE_PEOPLE,
                                                 hops_choices=N.AWAKE_CALLS,
                                                 questions_per_world=4, support=True)
    want = B1.pack_batch(want_stories, want_items, 'steps', support=True)
    stories, items, namespaces, source = N.awake_update(FIXTURE_SEED, 0, visits=1)
    record = N.decode_block(N.encode_block('awake', FIXTURE_SEED, 0, namespaces, stories,
                                           items, source))
    got = N.baseline_batch(record, 'steps', support=True)
    for field in ('owner', 'seq', 'seq_valid', 'q_len', 'target', 'support'):
        assert torch.equal(getattr(got, field), getattr(want, field)), f'{field} differs'
    for field in ('rows', 'flat', 'flat_row', 'flat_valid', 'lens', 'source'):
        assert torch.equal(getattr(got.story, field), getattr(want.story, field)), \
            f'story.{field} differs'
    assert got.questions == want.questions and got.outputs == want.outputs
    return f'{len(want_items)} questions, 6 batch tensors + 6 story tensors identical'


def test_record_feeds_the_dispatcher_packer_exactly():
    """`A.data.pack` on the record == what `V3.training_visits` builds for the same RNG."""
    rng = random.Random(f'{N.NS_AWAKE}:{FIXTURE_SEED}:0:0')
    want, questions, owners, answers, meta = V3.training_visits(
        rng, visits=1, people=N.AWAKE_PEOPLE, hops_choices=N.AWAKE_CALLS,
        questions_per_world=4)
    stories, items, namespaces, source = N.awake_update(FIXTURE_SEED, 0, visits=1)
    record = N.decode_block(N.encode_block('awake', FIXTURE_SEED, 0, namespaces, stories,
                                           items, source))
    got = N.dispatcher_inputs(record)
    fields = [f for f in ('memory', 'questions', 'owner', 'eligible')
              if isinstance(getattr(want, f, None), torch.Tensor)]
    for field in fields:
        assert torch.equal(getattr(got, field), getattr(want, field)), f'Inputs.{field} differs'
    assert [it['question'] for it in record['items']] == questions
    assert [it['owner'] for it in record['items']] == owners
    assert torch.equal(torch.tensor([it['answer'] for it in record['items']]), answers)
    assert [it['hops'] for it in record['items']] == [m['hops'] for m in meta]
    return (f'Inputs.{{{", ".join(fields)}}} identical; questions, owners, answers and '
            f'hops identical to training_visits')


def test_baseline_and_dispatcher_streams_agree():
    """The two frozen generators consume one RNG identically -- the whole reason a
    single byte-identical awake stream can serve D and T."""
    a = random.Random('agreement-probe')
    b = random.Random('agreement-probe')
    stories, items = B1.training_items(a, visits=3, people=6, hops_choices=(1, 2, 3),
                                       questions_per_world=4)
    _, questions, owners, answers, meta = V3.training_visits(
        b, visits=3, people=6, hops_choices=(1, 2, 3), questions_per_world=4)
    assert [it['question'] for it in items] == questions
    assert [it['owner'] for it in items] == owners
    assert [it['answer'] for it in items] == answers.tolist()
    assert a.random() == b.random(), 'the two generators left the RNG in different states'
    return '3 worlds x 4 questions identical and the RNG ends in the same state'


# --------------------------------------------------------------------------- stream


def test_stream_is_deterministic():
    root = scratch('determinism')
    panels = panels_fixture()
    first = N.build_awake_stream(root / 'a', FIXTURE_SEED, 4, chunk=4,
                                 dev_panels=panels, progress=False)
    second = N.build_awake_stream(root / 'b', FIXTURE_SEED, 4, chunk=4,
                                  dev_panels=panels, progress=False)
    index_a = json.loads((root / 'a' / 'index.json').read_text())
    index_b = json.loads((root / 'b' / 'index.json').read_text())
    assert first['complete'] and second['complete']
    assert [c['sha256'] for c in index_a['chunks']] == [c['sha256'] for c in index_b['chunks']]
    other = N.build_awake_stream(root / 'c', FIXTURE_SEED + 1, 4, chunk=4,
                                 dev_panels=panels, progress=False)
    index_c = json.loads((root / 'c' / 'index.json').read_text())
    assert [c['sha256'] for c in index_c['chunks']] != [c['sha256'] for c in index_a['chunks']]
    return f'same seed -> {index_a["chunks"][0]["sha256"][:16]}, other seed differs'


def _all_records(folder):
    out = []
    for path in sorted(Path(folder).glob('*.pt')):
        _, blocks = N.load_chunk(path)
        out.extend(N.decode_block(block) for block in blocks)
    return sorted(out, key=lambda r: r['index'])


def test_chunked_equals_unchunked():
    root = scratch('chunking')
    panels = panels_fixture()
    N.build_awake_stream(root / 'whole', FIXTURE_SEED, 6, chunk=6, dev_panels=panels,
                         progress=False)
    N.build_awake_stream(root / 'split', FIXTURE_SEED, 6, chunk=2, dev_panels=panels,
                         progress=False)
    whole = _all_records(root / 'whole')
    split = _all_records(root / 'split')
    assert len(whole) == len(split) == 6
    for one, two in zip(whole, split):
        assert one['stories'] == two['stories'] and one['items'] == two['items']
        assert one['namespaces'] == two['namespaces'] and one['index'] == two['index']
    return '6 updates identical whether written as 1 chunk or 3'


def test_resume_skips_existing_chunks():
    root = scratch('resume')
    panels = panels_fixture()
    N.build_awake_stream(root / 's', FIXTURE_SEED, 6, chunk=2, budget=0.0,
                         dev_panels=panels, progress=False)
    partial = sorted(p.name for p in (root / 's').glob('*.pt'))
    again = N.build_awake_stream(root / 's', FIXTURE_SEED, 6, chunk=2,
                                 dev_panels=panels, progress=False)
    assert partial, 'the first wave wrote nothing to resume from'
    assert set(partial) <= set(again['skipped']), 'a finished chunk was regenerated'
    assert again['complete'] and (root / 's' / 'index.json').exists()
    return f'{len(partial)} chunk(s) kept, {len(again["written"])} written on resume'


def test_iter_awake_api():
    root = fixture()
    seen = list(N.iter_awake(FIXTURE_SEED, 2, 5, root / 'stream'))
    assert [r['index'] for r in seen] == [2, 3, 4]
    assert all(len(r['stories']) == N.AWAKE_VISITS for r in seen)
    assert all(len(r['items']) == N.AWAKE_VISITS * 4 for r in seen)
    assert all(r['namespaces'][0] == N.awake_namespace(FIXTURE_SEED, r['index'], 0)
               for r in seen)
    batch = N.baseline_batch(N.merge_records(seen))
    assert batch.owner.max().item() == N.AWAKE_VISITS * 3 - 1
    return 'iter_awake(seed, 2, 5) yields updates 2,3,4 and merges into one batch'


def test_exclusion_collision_aborts():
    """A collision INVALIDATES the run: `training_items` raises, never skips."""
    stories, items, _, _ = N.awake_update(FIXTURE_SEED, 0, visits=1)
    signature = A.visible_signature(stories[0], items[0]['question'])
    try:
        N.awake_update(FIXTURE_SEED, 0, frozenset({signature}), visits=1)
    except RuntimeError as exc:
        assert 'overlap' in str(exc) or 'invalid' in str(exc), str(exc)
        return f'RuntimeError on a planted collision: {exc}'
    raise AssertionError('a planted exclusion collision was silently skipped')


def test_swapping_practised_labels_does_not_change_exclusion_logic():
    """Relabelling r=8 <-> r=9 must move the signature set wholesale, not shrink it:
    exclusion is by semantics, never by a privileged relation identity."""
    stories, items, _, _ = N.awake_update(FIXTURE_SEED, 3, visits=2)
    swap = {N.FIRST_REL: N.FIRST_REL + 1, N.FIRST_REL + 1: N.FIRST_REL}
    original, swapped = set(), set()
    for it in items:
        rows = stories[it['owner']]
        original.add(A.visible_signature(rows, it['question']))
        flipped_rows = [[swap.get(t, t) if i == 2 else t for i, t in enumerate(row)]
                        for row in rows]
        flipped_q = [swap.get(t, t) if 0 < i < len(it['question']) - 1 else t
                     for i, t in enumerate(it['question'])]
        swapped.add(A.visible_signature(flipped_rows, flipped_q))
    assert len(original) == len(swapped) == len(items), 'relabelling collapsed signatures'
    assert not (original & swapped) or len(original & swapped) < len(original), \
        'relabelling left the signature set unchanged'
    forbidden = frozenset(swapped)
    N.awake_update(FIXTURE_SEED, 3, forbidden, visits=2)     # must NOT raise
    return (f'{len(items)} questions: swapped labels give {len(swapped)} signatures, '
            f'{len(original & swapped)} shared, and do not trip the real exclusion')


# --------------------------------------------------------------------------- memory


def test_counts_match_only_awake_strings():
    root = fixture()
    _, mem, table = N.load_memory(root / 'memory')
    counts = [[0] * len(N.ALPHABET) for _ in N.ALPHABET]
    for item in mem['items']:
        for a, b in N.transitions_of(N.op_names(item['question'][2:-1])):
            counts[N.ALPHABET_INDEX[a]][N.ALPHABET_INDEX[b]] += 1
    assert counts == table['counts'], 'the stored table is not the awake corpus'
    total = sum(len(N.op_names(it['question'][2:-1])) + 1 for it in mem['items'])
    assert sum(sum(r) for r in counts) == total, 'a transition was invented or dropped'
    assert table['smoothing'] == 'none'
    zeros = [(a, b) for i, a in enumerate(N.ALPHABET) for j, b in enumerate(N.ALPHABET)
             if counts[i][j] == 0]
    assert ('LINK', '10') in zeros, 'LINK->10 must be an empty edge in an awake corpus'
    assert ('BOS', 'EOS') in zeros and ('BOS', 'BOS') in zeros
    salted = [list(row) for row in counts]
    salted[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['10']] += 1
    assert salted != table['counts'], 'a planted pseudocount went unnoticed'
    return (f'{len(mem["items"])} awake strings -> {total} transitions, '
            f'{len(zeros)} zero edges, LINK->10 among them')


def test_every_nonzero_edge_traces_to_an_awake_question():
    root = fixture()
    _, mem, table = N.load_memory(root / 'memory')
    edges = [(i, j) for i in range(len(N.ALPHABET)) for j in range(len(N.ALPHABET))
             if table['counts'][i][j]]
    for i, j in edges:
        key = f'{N.ALPHABET[i]}->{N.ALPHABET[j]}'
        trace = table['traces'][key]
        item = mem['items'][trace['question_index']]
        names = N.op_names(item['question'][2:-1])
        assert ' '.join(names) == trace['operation_string']
        assert (N.ALPHABET[i], N.ALPHABET[j]) in N.transitions_of(names), \
            f'{key} traced to a question that does not contain it'
        assert trace['namespace'].startswith(N.NS_AWAKE)
    return f'{len(edges)} nonzero edges, each traced to a real awake question'


def test_memory_is_first_distinct_worlds_in_encounter_order():
    root = fixture()
    manifest, mem, _ = N.load_memory(root / 'memory')
    signatures = [it['world_signature'] for it in mem['items'][::4]]
    assert len(set(signatures)) == len(signatures) == manifest['worlds']
    stream_order, seen = [], set()
    for record in N.iter_awake(FIXTURE_SEED, 0, 10 ** 9, root / 'stream'):
        for slot in range(len(record['stories'])):
            signature = record['items'][slot * 4]['world_signature']
            if signature in seen:
                continue
            seen.add(signature)
            stream_order.append(signature)
            if len(stream_order) == manifest['worlds']:
                break
        if len(stream_order) == manifest['worlds']:
            break
    assert stream_order == signatures, 'memory is not the stream order'
    return f'{manifest["worlds"]} worlds, encounter order preserved'


# --------------------------------------------------------------------------- proposals


def test_length_cap_rejects_and_never_repairs():
    """A six-call proposal is thrown away whole: never truncated, never terminated."""
    counts = [[0] * 6 for _ in range(6)]
    counts[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['LINK']] = 1
    counts[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['LINK']] = 1    # never terminates
    names, reason = N.propose_string(random.Random(0), counts)
    assert reason == 'overrun', reason
    assert names == ['LINK'] * N.MAX_DRAWS_AFTER_BOS, names
    assert len(names) > N.MAX_BUFFER_CALLS, 'the overrun was silently shortened'
    six = [[0] * 6 for _ in range(6)]
    six[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['LINK']] = 1
    six[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['LINK']] = 5
    six[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['8']] = 0
    seen = set()
    for candidate in range(400):
        got, why = N.propose_string(random.Random(candidate), six)
        seen.add(why)
        assert why is not None or len(got) <= N.MAX_BUFFER_CALLS
    assert seen == {'overrun'}, seen
    dead = [[0] * 6 for _ in range(6)]
    dead[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['LINK']] = 1
    assert N.propose_string(random.Random(1), dead)[1] == 'empty_row'
    stub = [[0] * 6 for _ in range(6)]
    stub[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['EOS']] = 1
    assert N.propose_string(random.Random(1), stub)[1] == 'no_attribute_terminus'
    trail = [[0] * 6 for _ in range(6)]
    trail[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['LINK']] = 1
    trail[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['EOS']] = 1
    assert N.propose_string(random.Random(1), trail)[1] == 'no_attribute_terminus'
    return 'overrun, empty row, empty string and dangling LINK all rejected whole'


def test_five_call_string_is_accepted_at_the_cap():
    counts = [[0] * 6 for _ in range(6)]
    counts[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['LINK']] = 1
    counts[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['LINK']] = 1
    counts[N.ALPHABET_INDEX['8']][N.ALPHABET_INDEX['EOS']] = 1
    lengths = set()
    for candidate in range(200):
        counts[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['8']] = 1
        names, reason = N.propose_string(random.Random(candidate), counts)
        if reason is None:
            lengths.add(len(names))
    assert lengths and max(lengths) == N.MAX_BUFFER_CALLS, lengths
    return f'accepted lengths {sorted(lengths)}; the cap itself is reachable'


def test_composite_r10_is_rejected_before_labels():
    counts = [[0] * 6 for _ in range(6)]
    counts[N.ALPHABET_INDEX['BOS']][N.ALPHABET_INDEX['LINK']] = 1
    counts[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['10']] = 1      # a planted bug
    counts[N.ALPHABET_INDEX['10']][N.ALPHABET_INDEX['EOS']] = 1
    root = fixture()
    _, mem, _ = N.load_memory(root / 'memory')
    histograms = N._new_histograms()
    chosen, fallbacks = N.propose_for_world(
        FIXTURE_SEED, 0, mem['stories'][0], counts, arm='G', questions_per_world=4,
        awake_items=mem['items'][:4], histograms=histograms)
    assert histograms['rejected'].get('composite_r10') == N.CANDIDATES_PER_WORLD, \
        histograms['rejected']
    assert len(fallbacks) == 4 and all(not p['sampled'] for p in chosen), \
        'a composite r=10 proposal reached the buffer'
    assert not any(N.composite_r10(p['names']) for p in chosen)
    assert all(N.composite_r10(k.split()) for k in histograms['proposed'])
    assert not histograms['accepted'], 'a rejected type was still counted as accepted'
    return (f'{N.CANDIDATES_PER_WORLD}/64 composite r=10 candidates rejected, all four '
            f'slots fell back to awake questions')


def test_candidate_failures_and_fallbacks_are_reproducible():
    root = fixture()
    _, mem, table = N.load_memory(root / 'memory')
    runs = []
    for _ in range(2):
        histograms = N._new_histograms()
        chosen, fallbacks = N.propose_for_world(
            FIXTURE_SEED, 7, mem['stories'][7], table['counts'], arm='G',
            questions_per_world=4, awake_items=mem['items'][28:32], histograms=histograms)
        runs.append((json.dumps(histograms, sort_keys=True),
                     json.dumps(chosen, sort_keys=True), json.dumps(fallbacks, sort_keys=True)))
    assert runs[0] == runs[1], 'the same seed gave a different candidate schedule'
    other = N._new_histograms()
    N.propose_for_world(FIXTURE_SEED + 1, 7, mem['stories'][7], table['counts'], arm='G',
                        questions_per_world=4, awake_items=mem['items'][28:32],
                        histograms=other)
    assert json.dumps(other, sort_keys=True) != runs[0][0], 'the seed does not matter'
    return 'identical histograms, picks and fallbacks on replay; different on a new seed'


def test_uniform_arm_length_distribution():
    seen = {}
    for candidate in range(4000):
        names = N.uniform_string(random.Random(f'{N.NS_UNIFORM}:0:0:{candidate}'))
        seen[(len(names), names[-1])] = seen.get((len(names), names[-1]), 0) + 1
    calls = sorted({c for c, _ in seen})
    assert calls == list(N.UNIFORM_CALLS), calls
    assert {r for c, r in seen if c == 1} == {'8', '9', '10'}
    assert {r for c, r in seen if c > 1} == {'8', '9'}, 'r=10 appeared at c>1'
    return f'c in {calls}; r=10 only at c=1'


# --------------------------------------------------------------------------- buffers


def test_arms_share_identical_world_bytes_and_order():
    root = fixture()
    arms = {arm: N.load_buffer(root / 'buffers', arm) for arm in ('R', 'G', 'U')}
    first = arms['R']
    for name, rec in arms.items():
        assert rec['stories'] == first['stories'], f'{name} has different world bytes'
        assert rec['namespaces'] == first['namespaces'], f'{name} has a different world order'
        assert [it['owner'] for it in rec['items']] == [it['owner'] for it in first['items']]
        assert [it['world_signature'] for it in rec['items']] \
            == [it['world_signature'] for it in first['items']]
        assert len(rec['items']) == len(rec['stories']) * 4
    questions = {name: [it['question'] for it in rec['items']] for name, rec in arms.items()}
    assert questions['R'] != questions['G'] and questions['G'] != questions['U'], \
        'the arms are not actually different curricula'
    return (f'{len(first["stories"])} worlds byte-identical across R/G/U; only the '
            f'questions differ')


def test_buffer_labels_come_from_the_fixed_interpreter():
    root = fixture()
    for arm in ('R', 'G', 'U'):
        rec = N.load_buffer(root / 'buffers', arm)
        for it in rec['items'][:200]:
            rows = rec['stories'][it['owner']]
            assert N.label_question(rows, it['question']) == it['chain'], f'{arm} label drift'
            assert it['answer'] == it['chain'][-1][2]
            assert it['support'] == B1.support_rows(rows, it['chain'])
            assert all(index >= 0 for index in it['support']), 'a step has no visible row'
    return 'both independent interpreters and the support rows agree on 200 items per arm'


def test_zero_composite_r10_exposure_everywhere():
    root = fixture()
    audit = json.loads((root / 'buffers' / 'audit.json').read_text())
    assert audit['composite_r10_exposure']['zero_exposure'] is True
    _, mem, table = N.load_memory(root / 'memory')
    for name in ('awake_stream_types', 'memory_questions'):
        assert audit['composite_r10_exposure']['sources'][name]['count'] == 0
    assert table['counts'][N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['10']] == 0
    for arm in ('R', 'G', 'U'):
        rec = N.load_buffer(root / 'buffers', arm)
        bad = [it for it in rec['items'] if N.composite_r10(N.op_names(it['question'][2:-1]))]
        assert not bad, f'{arm} exposes composite r=10'
    stream = N.awake_signatures(root / 'stream', FIXTURE_SEED)
    assert not [t for t in stream['types'] if N.composite_r10(t.split())]
    return (f'stream ({stream["questions"]} q), counts, memory and all three buffers: '
            f'no composite r=10 type')


def test_generation_gate_shape():
    root = fixture()
    audit = json.loads((root / 'buffers' / 'audit.json').read_text())
    gate = audit['generation_gate']
    assert sorted(gate['structures']) == ['c=4,r=8', 'c=4,r=9', 'c=5,r=8', 'c=5,r=9']
    for row in gate['structures'].values():
        assert row['awake_instances'] == 0, 'a gate structure occurs in awake practice'
        assert row['required'] == N.GENERATION_GATE_MIN
        assert row['distinct_questions'] > 0, 'the sampler produced none of this structure'
        assert row['distinct_worlds'] <= row['distinct_questions']
    assert set(gate['awake_operation_types']) == {'8', '9', '10', 'LINK 8', 'LINK 9',
                                                  'LINK LINK 8', 'LINK LINK 9'}
    return ('all four never-asked structures generated on a 64-world fixture: '
            + ', '.join(f'{k}={v["distinct_questions"]}'
                        for k, v in sorted(gate['structures'].items())))


def test_offline_order_is_shared_and_reproducible():
    order = json.loads((fixture() / 'buffers' / 'offline-order.json').read_text())
    rebuilt = N.offline_order(FIXTURE_SEED, updates=order['updates'], visits=order['visits'],
                              worlds=order['worlds'])
    assert rebuilt == order['order'], 'the shared world order is not reproducible'
    assert order['namespace'] == N.NS_ORDER
    assert all(len(row) == order['visits'] for row in order['order'])
    assert all(0 <= w < order['worlds'] for row in order['order'] for w in row)
    other = N.offline_order(FIXTURE_SEED + 1, updates=order['updates'],
                            visits=order['visits'], worlds=order['worlds'])
    assert other != order['order']
    return f'{order["updates"]} updates x {order["visits"]} worlds reproduce exactly'


# --------------------------------------------------------------------------- panels


def test_development_cell_table():
    assert len(N.DEV_CELLS) == 32
    assert sorted(N.DEV_CELL_ORDER) == sorted(N.DEV_CELLS)
    assert len(set(N.DEV_CELL_ORDER)) == 32
    sizes = {k: sum(1 for c in N.DEV_CELLS if c.startswith(k + '-'))
             for k in ('N', 'E', 'F', 'P', 'H', 'L')}
    assert sizes == dict(N=4, E=3, F=7, P=8, H=4, L=6), sizes
    for name, cfg in N.DEV_CELLS.items():
        assert cfg['distinct'] is True, f'{name} tolerates a cycling chain'
        assert (cfg['kind'] == 'pair') == name.startswith('E-')
        assert cfg['fixed_terminal'] in (N.FIRST_REL, N.FIRST_REL + 1, N.HELDOUT_REL,
                                         'balanced'), name
    heldout = [n for n, c in N.DEV_CELLS.items() if c['fixed_terminal'] == N.HELDOUT_REL]
    assert len(heldout) == 4 + 3 + 1 + 4 + 3, heldout      # N + E + F-c1-r10 + H + L-held
    assert not set(N.DEV_CELLS) & set(V3.CELLS), 'a new cell name shadows a frozen v3 cell'
    return f'32 cells, families {sizes}, no name collides with v3'


def test_registered_cells_context_is_clean():
    before = dict(V3.CELLS)
    with N.registered_cells():
        assert 'N-c4-p6' in V3.CELLS
        assert sorted(V3.CELL_ORDER) == sorted(before), 'v3 CELL_ORDER was mutated'
    assert V3.CELLS == before, 'the v3 cell table was not restored'
    return f'{len(before)} v3 cells restored exactly'


def test_answer_stratification_is_even_and_outcome_independent():
    values = [N.target_answer(i) for i in range(N.DEV_N)]
    counts = {v: values.count(v) for v in set(values)}
    assert len(counts) == N.VALUE_COUNT and set(counts.values()) == {N.DEV_N // N.VALUE_COUNT}
    assert values == [N.target_answer(i) for i in range(N.DEV_N)], 'not a pure function'
    assert min(values) == N.VALUE_MIN and max(values) == N.VALUE_MIN + N.VALUE_COUNT - 1
    at_512 = [N.target_answer(i) for i in range(N.CONFIRM_N)]
    assert set(at_512.count(v) for v in set(at_512)) == {N.CONFIRM_N // N.VALUE_COUNT}
    return f'{N.DEV_N}/{N.VALUE_COUNT} = {N.DEV_N // N.VALUE_COUNT} units per value, exactly'


def test_dev_units_pass_the_independent_audit():
    made = {}
    with N.registered_cells():
        for cell in ('N-c5-p6', 'N-c4-p16', 'F-c1-r10', 'H-c3-p6', 'P-c5-r9-p16',
                     'L-c6-prac'):
            for index in (0, 5):
                unit, signatures, worlds = N.dev_unit(cell, index,
                                                      namespace=FIXTURE_NAMESPACE)
                assert not V3.audit_unit(unit), V3.audit_unit(unit)
                assert unit['a']['answer'] == N.target_answer(index)
                assert len(set(unit['a']['people'])) == N.DEV_CELLS[cell]['hops'], \
                    'the chain revisits a person'
                assert len(signatures) == 1
                made[(cell, index)] = unit
    # ruling 6: the mixed 8/9 ending is blocked, r(i) = 8 + (i // 16) % 2, so units 0
    # and 5 share an ending; the flip at 16 is checked by the ruling-6 test
    l6 = made[('L-c6-prac', 0)]['a']
    assert l6['terminal'] == N.FIRST_REL and made[('L-c6-prac', 5)]['a']['terminal'] \
        == N.FIRST_REL, 'the balanced L ending no longer follows ruling 6'
    assert made[('F-c1-r10', 0)]['a']['terminal'] == N.HELDOUT_REL
    assert made[('P-c5-r9-p16', 0)]['a']['terminal'] == N.FIRST_REL + 1
    return f'{len(made)} units across six cells: audits clean, answers on target'


def test_pair_rules():
    """Changed LINK and changed endpoint must change the oracle answer; the irrelevant
    edit must not.  All three decided by the interpreter only."""
    detail = []
    with N.registered_cells():
        for cell, invariant, moved in (('E-c5-link', False, 1), ('E-c5-value', False, 2),
                                       ('E-c5-irrelevant', True, 2)):
            for index in (0, 3):
                unit, _, _ = N.dev_unit(cell, index, namespace=FIXTURE_NAMESPACE)
                assert not V3.audit_unit(unit)
                a, b = unit['a'], unit['b']
                assert a['question'] == b['question'], 'the twins ask different questions'
                assert V3.memory_diffs(a['memory'], b['memory']) == moved
                changed = a['answer'] != b['answer']
                assert changed != invariant, f'{cell}: invariance rule broken'
                for side in (a, b):
                    eligible = V3.side_eligible(side)
                    assert V3.interpret(side['memory'], eligible, side['question']) \
                        == side['chain']
                touched = {row[1] for i, (ra, rb)
                           in enumerate(zip(a['memory'], b['memory'])) if ra != rb
                           for row in [a['memory'][i]]}
                if cell == 'E-c5-irrelevant':
                    assert not touched & set(a['people']), 'the irrelevant edit hit the chain'
                if cell == 'E-c5-value':
                    assert a['people'][-1] in touched, 'the value edit missed the endpoint'
                if cell == 'E-c5-link':
                    assert touched <= set(a['people']), 'the link edit was off-chain'
            detail.append(cell)
    return 'link/value/irrelevant rules hold on 2 units each: ' + ', '.join(detail)


def test_dev_panels_write_the_v3_json_format():
    root = scratch('panels')
    out = N.build_dev_panels(root / 'panels', n=16, namespace=FIXTURE_NAMESPACE,
                             cells={k: N.DEV_CELLS[k] for k in ('N-c4-p6', 'E-c5-value')},
                             operator_history=history_fixture(),
                             require_full_history=False, progress=False)
    manifest, panels, forbidden = N.load_dev_panels(root / 'panels')
    v3_keys = {'cell', 'n', 'namespace', 'kind', 'title', 'hops', 'people', 'terminal',
               'distinct', 'invariant', 'edit', 'units', 'rejections'}
    for cell, panel in panels.items():
        assert v3_keys <= set(panel), sorted(v3_keys - set(panel))
        assert len(panel['units']) == 16
        for unit in panel['units']:
            assert {'cell', 'index', 'kind'} <= set(unit)
            for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
                assert {'memory', 'question', 'where', 'answer', 'chain', 'people',
                        'terminal', 'hops', 'distinct'} <= set(unit[side])
        row = manifest['cells'][cell]
        assert row['answer_evenly_stratified'] is True
        assert N.sha(Path(row['path'])) == row['sha256']
    assert out['exclusion_count'] == len(forbidden) == 16 + 32
    assert 'operator_chain_hits' not in panels['N-c4-p6'], 'a model diagnostic leaked in'
    return f'{len(panels)} panels, {len(forbidden)} signatures, v3 keys present'


def test_dev_panels_are_disjoint_from_the_legacy_union():
    root = scratch('disjoint')
    N.build_dev_panels(root / 'panels', n=8, namespace=FIXTURE_NAMESPACE,
                       cells={k: N.DEV_CELLS[k] for k in ('F-c2-r8', 'H-c2-p16')},
                       operator_history=history_fixture(),
                       require_full_history=False, progress=False)
    _, _, forbidden = N.load_dev_panels(root / 'panels')
    legacy, _ = B2.exclusion_union([str(p) for p in N.legacy_exclusion_paths()])
    assert not (forbidden & legacy), 'a new dev unit reuses a frozen panel semantics'
    both, record = N.build_exclusion_union(root / 'panels')
    assert len(both) == len(legacy) + len(forbidden)
    assert len(record['sources']) == len(N.LEGACY_EXCLUSIONS) + 1
    return (f'{len(forbidden)} new signatures disjoint from {len(legacy)} legacy ones '
            f'across {len(record["sources"])} sources')


def _fixture_experiment():
    """An experiment folder in the fixed layout, at the FIXTURE seed.

    `confirmation_exclusions` reads the published forbidden files AND the manifest that
    published them (audit R2-7), so the layout folders carry copies of both.  No
    registered seed is generated anywhere.
    """
    if 'experiment' not in _CACHE:
        root = scratch('experiment')
        src = fixture()
        for key, folder in (('stream', 'stream'), ('memory', 'memory'),
                            ('buffers', 'buffers')):
            target = root / N.EXPERIMENT_LAYOUT[key].format(seed=FIXTURE_SEED)
            target.mkdir(parents=True)
            for name in (N.FORBIDDEN_QUESTIONS, N.FORBIDDEN_WORLDS):
                shutil.copy(src / folder / name, target / name)
            for name in N.ARTIFACT_MANIFESTS:
                if (src / folder / name).exists():
                    shutil.copy(src / folder / name, target / name)
        shutil.copytree(panels_fixture(), root / N.EXPERIMENT_LAYOUT['dev_panels'])
        shutil.copytree(history_fixture(), root / N.EXPERIMENT_LAYOUT['operator_history'])
        _CACHE['experiment'] = root
    return _CACHE['experiment']


def _dev_passed_doc(root, **override):
    panels = root / N.EXPERIMENT_LAYOUT['dev_panels']
    doc = dict(schema=N.DEV_PASSED_SCHEMA, seeds=[FIXTURE_SEED],
               report_sha256='a' * 64,
               dev_panels=dict(path=str(panels),
                               manifest_sha256=N.sha(panels / 'manifest.json')),
               awake_checkpoints={k: 'b' * 64
                                  for k in N.checkpoint_keys('awake', [FIXTURE_SEED])},
               offline_checkpoints={k: 'c' * 64
                                    for k in N.checkpoint_keys('offline', [FIXTURE_SEED])})
    doc.update(override)
    return doc


def test_confirmation_is_locked_behind_dev_passed():
    """AUDIT FIX 3: an empty or malformed DEV-PASSED.json used to be enough."""
    guard = scratch('confirm-guard')
    root = guard / 'experiment'
    shutil.copytree(_fixture_experiment(), root)
    flag = root / 'DEV-PASSED.json'
    history = root / N.EXPERIMENT_LAYOUT['operator_history']
    cells = {'F-c1-r8': N.DEV_CELLS['F-c1-r8']}

    def attempt(out, seeds=(FIXTURE_SEED,), **kw):
        return N.build_dev_panels(guard / out, n=1, namespace=FIXTURE_NAMESPACE,
                                  cells=cells, confirmation=True, experiment=root,
                                  seeds=list(seeds), operator_history=history,
                                  require_full_history=False, progress=False, **kw)

    def refuses(out, want, **kw):
        try:
            attempt(out, **kw)
        except SystemExit as exc:
            assert want in str(exc), f'wrong refusal for {out}: {exc}'
            assert not (guard / out).exists(), f'{out} was created anyway'
            return str(exc)
        raise AssertionError(f'confirmation panels were built despite {out}')

    refused = [refuses('missing', 'no ')]
    flag.write_text('')
    refused.append(refuses('empty', 'is empty'))
    flag.unlink()
    flag.write_text('{"passed": true')
    refused.append(refuses('malformed', 'does not parse'))
    flag.unlink()
    flag.write_text(json.dumps({'passed': True}))
    refused.append(refuses('legacy-flag', 'schema is'))
    flag.unlink()
    doc = _dev_passed_doc(root)
    doc['dev_panels']['path'] = str(root / N.EXPERIMENT_LAYOUT['dev_panels'])
    bad = json.loads(json.dumps(doc))
    bad['dev_panels']['manifest_sha256'] = 'd' * 64
    flag.write_text(json.dumps(bad))
    refused.append(refuses('wrong-panel-hash', 'hashes to'))
    flag.unlink()
    bad = json.loads(json.dumps(doc))
    bad['offline_checkpoints'].pop(sorted(bad['offline_checkpoints'])[0])
    flag.write_text(json.dumps(bad))
    refused.append(refuses('missing-checkpoint', 'is missing'))
    flag.unlink()
    bad = json.loads(json.dumps(doc))
    bad['awake_checkpoints'][sorted(bad['awake_checkpoints'])[0]] = 'not-a-hash'
    flag.write_text(json.dumps(bad))
    refused.append(refuses('bad-hash', 'not sha256'))
    flag.unlink()

    flag.write_text(json.dumps(doc))
    out = attempt('ok')
    manifest = json.loads((Path(out['panels']) / 'manifest.json').read_text())
    assert manifest['kind'] == 'confirmation'
    assert manifest['dev_passed']['report_sha256'] == doc['report_sha256']
    assert manifest['training_exclusion']['questions'] > 0
    assert manifest['training_exclusion']['worlds'] > 0
    assert len(manifest['training_exclusion']['sources']) == 4, 'stream+memory+buffers+panels'
    return (f'{len(refused)} distinct malformed/incomplete lockouts refused, '
            f'the complete one allowed')


def test_confirmation_namespace_needs_the_flag_and_a_full_history():
    guard = scratch('confirm-ns')
    cells = {'F-c1-r8': N.DEV_CELLS['F-c1-r8']}
    try:
        N.build_dev_panels(guard / 'a', n=1, namespace=N.NS_CONFIRM, cells=cells,
                           operator_history=history_fixture(),
                           require_full_history=False, progress=False)
    except SystemExit as exc:
        assert 'explicit --confirmation' in str(exc), str(exc)
    else:
        raise AssertionError('the confirmation namespace was usable without the flag')
    for namespace in (N.NS_DEV, N.NS_CONFIRM):
        try:
            N.build_dev_panels(guard / f'b-{namespace}', n=1, namespace=namespace,
                               cells=cells, confirmation=namespace == N.NS_CONFIRM,
                               experiment=_fixture_experiment(),
                               operator_history=history_fixture(),
                               require_full_history=False, progress=False)
        except SystemExit as exc:
            assert 'partial operator history' in str(exc), str(exc)
        else:
            raise AssertionError(f'{namespace} accepted a partial operator history')
    assert not any(guard.iterdir()), 'a refused run left a folder behind'
    return 'registered namespaces refuse both the missing flag and a partial history'


def test_registered_numbers_are_unchanged():
    assert (N.REGISTERED_SEEDS, N.AWAKE_UPDATES, N.AWAKE_VISITS, N.AWAKE_PEOPLE,
            N.AWAKE_QUESTIONS_PER_WORLD, N.AWAKE_CALLS) == \
        ((1900, 1901, 1902), 6000, 16, 6, 4, (1, 2, 3))
    assert (N.MEMORY_WORLDS, N.CANDIDATES_PER_WORLD, N.MAX_DRAWS_AFTER_BOS,
            N.MAX_BUFFER_CALLS, N.UNIFORM_CALLS) == (1024, 64, 7, 5, (1, 2, 3, 4, 5))
    assert (N.OFFLINE_UPDATES, N.OFFLINE_VISITS, N.AWAKE_CHUNK, N.OFFLINE_CHUNK) == \
        (2000, 16, 750, 500)
    assert (N.DEV_N, N.CONFIRM_N, N.DEV_ATTEMPTS) == (64, 512, 10000)
    assert N.GENERATION_GATE_STRUCTURES == ((4, 8), (4, 9), (5, 8), (5, 9))
    assert N.GENERATION_GATE_MIN == 16
    assert [N.NS_AWAKE, N.NS_PROPOSE, N.NS_BIND, N.NS_UNIFORM, N.NS_ORDER, N.NS_DEV,
            N.NS_CONFIRM] == ['astra-novelty19-awake-v1', 'astra-novelty19-propose-v1',
                              'astra-novelty19-bind-v1', 'astra-novelty19-uniform-v1',
                              'astra-novelty19-offline-order-v1', 'astra-novelty19-dev-v1',
                              'astra-novelty19-confirm-v1']
    assert N.ALPHABET == ('BOS', 'LINK', '8', '9', '10', 'EOS')
    return 'every registered number and namespace matches the preregistration draft'


def _audit(**override):
    root = fixture()
    kw = dict(stream=root / 'stream', memory=root / 'memory', buffers=root / 'buffers',
              dev_panels=panels_fixture(), operator_history=history_fixture(),
              require_full_history=False)
    kw.update(override)
    return N.audit_everything(FIXTURE_SEED, **kw)


def test_audit_verdict():
    verdict = _audit()
    assert set(verdict['checks']) == set(N.EXPECTED_AUDIT_CHECKS), \
        sorted(set(N.EXPECTED_AUDIT_CHECKS) - set(verdict['checks']))
    assert verdict['checks_run'] == verdict['checks_expected'] == len(N.EXPECTED_AUDIT_CHECKS)
    assert verdict['checks_absent'] == []
    # the fixture is deliberately too small for two checks: 64 worlds cannot reach the
    # 16/16 generation gate, and the fixture panel folder holds 2 cells, not 32
    expected_failures = {'generation_gate', 'dev_panel_cell_count'}
    failures = [f for f in verdict['failures'] if f not in expected_failures]
    assert not failures, failures
    assert verdict['checks']['dev_panel_world_exclusions_published']['passed'] is True
    assert verdict['checks']['awake_worlds_disjoint_from_dev_panels']['passed'] is True
    assert verdict['checks']['execution_profiles_agree']['passed'] is True
    return (f'{verdict["checks_run"]}/{verdict["checks_expected"]} disk checks, '
            f'{len(failures)} unexpected failures')


def test_audit_refuses_a_missing_artifact():
    """AUDIT FIX 2: dropping a source used to drop its checks and still pass."""
    for name in ('stream', 'memory', 'buffers', 'dev_panels', 'operator_history'):
        try:
            _audit(**{name: None})
        except SystemExit as exc:
            assert name in str(exc), str(exc)
        else:
            raise AssertionError(f'audit ran without {name}')
    assert len(N.EXPECTED_AUDIT_CHECKS) == len(set(N.EXPECTED_AUDIT_CHECKS))
    return (f'all five artifacts are mandatory; the roster is a fixed '
            f'{len(N.EXPECTED_AUDIT_CHECKS)} checks')


def test_audit_fails_when_an_expected_check_is_absent():
    """The roster, not the caller, decides how many checks a verdict contains."""
    original = N.EXPECTED_AUDIT_CHECKS
    N.EXPECTED_AUDIT_CHECKS = original + ('a_check_nothing_runs',)
    try:
        verdict = _audit()
    finally:
        N.EXPECTED_AUDIT_CHECKS = original
    assert verdict['checks_absent'] == ['a_check_nothing_runs']
    assert 'expected_checks_absent' in verdict['failures']
    assert verdict['passed'] is False
    return 'an unrun expected check fails the verdict instead of shrinking the count'


def test_audit_detects_a_disagreeing_execution_profile():
    """AUDIT FIX 5: manifests of one experiment must share one execution profile."""
    root = scratch('profile')
    shutil.copytree(fixture() / 'memory', root / 'memory')
    path = root / 'memory' / 'manifest.json'
    manifest = json.loads(path.read_text())
    assert manifest['execution_profile']['python'] and manifest['execution_profile']['torch']
    manifest['execution_profile'] = dict(manifest['execution_profile'],
                                         torch='0.0.0+fabricated')
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    verdict = _audit(memory=root / 'memory')
    assert 'execution_profiles_agree' in verdict['failures'], verdict['failures']
    assert verdict['passed'] is False
    return 'a fabricated torch version in one manifest fails the whole audit'


def test_manifests_are_hash_stable():
    """AUDIT FIX 5: no wall-clock field inside a hashed document."""
    root = scratch('stable')
    panels = panels_fixture()
    hashes = []
    for _run in range(2):
        N.build_awake_stream(root / 'stream', FIXTURE_SEED, 2, chunk=2, dev_panels=panels,
                             progress=False)
        N.build_memory(root / 'memory', FIXTURE_SEED, root / 'stream', worlds=8)
        hashes.append((N.sha(root / 'stream' / 'index.json'),
                       N.sha(root / 'memory' / 'manifest.json'),
                       N.sha(root / 'memory' / 'transition-counts.json')))
        index = json.loads((root / 'stream' / 'index.json').read_text())
        manifest = json.loads((root / 'memory' / 'manifest.json').read_text())
        for doc in (index, manifest):
            assert 'created_unix' not in doc and 'seconds' not in doc, sorted(doc)
        meta = N.read_meta(root / 'stream' / 'index.json')
        assert meta and meta['created_unix'] > 0 and meta['seconds'] >= 0
        assert N.read_meta(root / 'memory' / 'manifest.json')['created_unix'] > 0
        shutil.rmtree(root / 'stream')
        shutil.rmtree(root / 'memory')
    assert hashes[0] == hashes[1], 'a manifest hash moved between two identical runs'
    return f'index.json and memory manifest.json reproduce byte-for-byte: {hashes[0][0][:16]}'


# ------------------------------------------------------- audit fixes and rulings


def test_every_artifact_publishes_both_exclusion_levels():
    """AUDIT FIX 1: section 7 excludes WORLDS, not only accepted training questions."""
    root = fixture()
    sizes = {}
    for name, folder in (('stream', root / 'stream'), ('memory', root / 'memory'),
                         ('buffers', root / 'buffers'), ('panels', panels_fixture()),
                         ('operator_history', history_fixture())):
        sets = N.artifact_exclusions(folder)
        assert sets['questions'] and sets['worlds'], name
        assert all(len(s) == 64 for s in list(sets['questions'])[:4]), name
        sizes[name] = (len(sets['questions']), len(sets['worlds']))
    stream = N.awake_signatures(root / 'stream', FIXTURE_SEED)
    published = N.artifact_exclusions(root / 'stream')
    assert stream['signatures'] == published['questions'], 'stream questions unpublished'
    assert stream['worlds'] == published['worlds'], 'stream worlds unpublished'
    worlds, primary = N.dev_panel_worlds(panels_fixture())
    assert primary and primary < worlds, 'the primary (N/E) world file is wrong'
    return ', '.join(f'{k}={q}q/{w}w' for k, (q, w) in sizes.items())


def test_training_material_refuses_a_primary_evaluation_world():
    """AUDIT FIX 1: the N/E world exclusion is ENFORCED, not merely measured."""
    root = fixture()
    worlds, primary = N.dev_panel_worlds(panels_fixture())
    stream = N.awake_signatures(root / 'stream', FIXTURE_SEED)
    assert not (stream['worlds'] & worlds), 'a dev world is in the awake stream'
    blocks = [N.awake_block(FIXTURE_SEED, 0, visits=2)]
    planted = bytes(blocks[0]['world_signature'][1].tolist()).hex()
    assert N.assert_worlds_allowed(blocks, frozenset(), 'no-op') == 0
    assert N.assert_worlds_allowed(blocks, primary, 'clean') == 2
    try:
        N.assert_worlds_allowed(blocks, frozenset({planted}), 'planted')
    except RuntimeError as exc:
        assert 'invalid' in str(exc), str(exc)
    else:
        raise AssertionError('a primary evaluation world was allowed into training data')
    try:
        N.build_awake_stream(scratch('noguard') / 's', FIXTURE_SEED, 1,
                             dev_panels=None, progress=False)
    except SystemExit as exc:
        assert '--dev-panels is required' in str(exc), str(exc)
    else:
        raise AssertionError('a stream was generated with the collision abort disarmed')
    return 'a planted primary world aborts the run; --dev-panels cannot be omitted'


def test_dev_panels_exclude_the_operator_history_worlds():
    """RULING 2 / AUDIT FIX 4: the reconstruction is a freeze prerequisite."""
    manifest = json.loads((history_fixture() / 'manifest.json').read_text())
    assert manifest['updates'] == 2 and manifest['full_run'] is False
    assert manifest['complete'] is False and manifest['no_model_forwards'] is True
    assert manifest['world_union_sha256'] == N.world_union_digest(
        N.artifact_exclusions(history_fixture())['worlds'])
    assert manifest['distinct_training_worlds'] == 2 * N.OPERATOR_HISTORY_VISITS
    try:
        N.load_operator_history(history_fixture())
    except SystemExit as exc:
        assert 'incomplete' in str(exc), str(exc)
    else:
        raise AssertionError('an incomplete reconstruction was accepted')
    try:
        N.load_operator_history(None)
    except SystemExit as exc:
        assert 'freeze prerequisite' in str(exc), str(exc)
    else:
        raise AssertionError('panels were allowed with no reconstruction at all')
    panel_manifest = json.loads((panels_fixture() / 'manifest.json').read_text())
    history = N.artifact_exclusions(history_fixture())
    worlds, _ = N.dev_panel_worlds(panels_fixture())
    _, _, forbidden = N.load_dev_panels(panels_fixture())
    assert panel_manifest['operator_history']['worlds'] == len(history['worlds'])
    assert not (worlds & history['worlds']), 'a panel reuses an operator training world'
    assert not (forbidden & history['questions'])
    return (f'{manifest["distinct_training_worlds"]} reconstructed worlds excluded; '
            f'incomplete and missing reconstructions both refuse')


def test_operator_history_replays_the_archived_rng_stream():
    """The reconstruction consumes the driver's RNG draws in the archived order."""
    import random as _random
    from premonition.toy_ladder import LadderSpec, visit
    A.data.bootstrap()
    spec = LadderSpec()
    rng = _random.Random(N.OPERATOR_HISTORY_RNG_SEED)
    worlds = set()
    for _ in range(N.OPERATOR_HISTORY_VISITS):
        rows, _world, _ = visit(spec, rng, training=True)
        memory = [[] if r.question else list(r.tokens) for r in rows]
        worlds.add(CP.world_signature(CP.fact_tuples([r for r in memory if r])))
    rng.randrange(1 << 30)
    state = rng.getstate()
    mine, _questions, _s = N.reconstruct_operator_history(updates=1)
    assert mine == worlds, 'the reconstruction drew different worlds'
    rng2 = _random.Random(N.OPERATOR_HISTORY_RNG_SEED)
    N.reconstruct_operator_history(updates=1)
    for _ in range(N.OPERATOR_HISTORY_VISITS):
        visit(spec, rng2, training=True)
    rng2.randrange(1 << 30)
    assert rng2.getstate() == state, 'the RNG is left in a different state'
    assert N.OPERATOR_HISTORY_WORLD_UNION_SHA256 == (
        '0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a')
    return f'update 0 reproduces {len(worlds)} worlds and the exact RNG state'


def test_gate_reading_is_ratified_and_reports_both():
    """RULING 1: instances decide; raw tokens and entity coverage are descriptive."""
    assert N.GATE_READING == 'instances'
    gate = json.loads((fixture() / 'buffers' / 'audit.json').read_text())['generation_gate']
    assert gate['reading'] == 'instances' and 'ruling' in gate
    assert gate['memory_worlds_distinct'] is True
    for row in gate['structures'].values():
        assert row['distinct_questions'] == row['distinct_question_instances']
        assert row['distinct_raw_question_tokens'] <= row['distinct_question_instances']
        assert row['distinct_worlds'] <= row['distinct_question_instances']
        assert row['distinct_bound_subjects'] <= N.PANEL_PEOPLE
        assert row['awake_instances'] == 0
    return ('both readings reported: instances '
            + ','.join(str(r['distinct_question_instances'])
                       for r in gate['structures'].values())
            + ' vs raw tokens '
            + ','.join(str(r['distinct_raw_question_tokens'])
                       for r in gate['structures'].values()))


def test_fixed_slot_fallback_is_logged_with_duplicates():
    """RULING 3: fixed-slot, identical for G and U, duplicates kept and logged."""
    audit = json.loads((fixture() / 'buffers' / 'audit.json').read_text())
    for arm in ('G', 'U'):
        row = audit['per_arm'][arm]
        assert row['candidates_per_world'] == N.CANDIDATES_PER_WORLD
        assert 'fallback_duplicates_accepted' in row
        assert row['fallback_duplicates_accepted'] <= row['fallbacks']
        for entry in row['fallback_log']:
            assert set(entry) == {'world_index', 'slot', 'operation_string',
                                  'duplicates_accepted'}
    _, mem, table = N.load_memory(fixture() / 'memory')
    histograms = N._new_histograms()
    chosen, made = N.propose_for_world(
        FIXTURE_SEED, 0, mem['stories'][0], table['counts'], arm='G',
        questions_per_world=8, awake_items=mem['items'][:8], histograms=histograms)
    assert len(chosen) == 8, 'the fixed slots were not filled'
    for slot, pick in enumerate(chosen):
        if not pick['sampled']:
            assert pick['fallback_index'] == slot, 'a fallback moved out of its slot'
    assert sum(histograms['proposed'].values()) == N.CANDIDATES_PER_WORLD, \
        'the attempt budget was extended for a fallback'
    return (f'{len(made)} fallbacks in fixed slots, duplicates logged, '
            f'{N.CANDIDATES_PER_WORLD} candidates drawn regardless')


def test_world_identity_ignores_row_order_and_filler():
    """RULING 4: the question-free fact set is the world."""
    stories, items, _, _ = N.awake_update(FIXTURE_SEED, 1, visits=1)
    rows = stories[0]
    base = CP.world_signature(CP.fact_tuples(rows))
    shuffled = list(rows)
    random.Random(4).shuffle(shuffled)
    assert CP.world_signature(CP.fact_tuples(shuffled)) == base, 'row order changed it'
    padded = list(rows) + [[N.NEWLINE], [N.NEWLINE, 28, 29]]
    assert CP.world_signature(CP.fact_tuples(padded)) == base, 'filler changed it'
    def eligible(row):
        return (len(row) >= 4 and row[0] == N.WORLD
                and N.ENTITY_MIN <= row[1] < N.ENTITY_MAX and 8 <= row[2] <= N.LINK)

    noise = [list(r) for r in rows]
    for row in noise:
        if not eligible(row) and len(row) >= 4:
            row[3] = (row[3] % 20) + 28              # another filler token
            break
    assert CP.world_signature(CP.fact_tuples(noise)) == base, 'a distractor row changed it'
    changed = [list(r) for r in rows]
    for row in changed:
        if eligible(row) and row[2] != N.LINK:
            row[3] = N.VALUE_MIN + ((row[3] - N.VALUE_MIN + 1) % N.VALUE_COUNT)
            break
    else:
        raise AssertionError('the fixture world has no attribute fact to change')
    assert CP.world_signature(CP.fact_tuples(changed)) != base, 'a changed fact did not'
    assert items[0]['question']
    return 'row order and distractor rows ignored; one changed value is a new world'


def test_distinct_people_in_every_cell_including_l():
    """RULING 5: all c visited people distinct, both sides of a pair, L included."""
    assert all(cfg['distinct'] is True for cfg in N.DEV_CELLS.values())
    checked = []
    with N.registered_cells():
        for cell in ('L-c8-held', 'E-c5-link'):
            unit, _, _ = N.dev_unit(cell, 0, namespace=FIXTURE_NAMESPACE)
            for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
                people = unit[side]['people']
                assert len(set(people)) == len(people) == N.DEV_CELLS[cell]['hops'], \
                    f'{cell}.{side} revisits a person'
                assert unit[side]['answer'] not in people, 'the value is not a person'
            checked.append(cell)
    return 'distinct visited people hold in ' + ' and '.join(checked)


def test_mixed_ending_schedule_hides_the_answer():
    """RULING 6: answer parity must not predict the ending in a mixed 8/9 cell."""
    for n in (N.DEV_N, N.CONFIRM_N):
        table = N.mixed_ending_balance(n)
        assert len(table) == N.VALUE_COUNT * 2, table
        assert set(table.values()) == {n // (N.VALUE_COUNT * 2)}, table
        by_ending = {}
        for (value, ending), count in table.items():
            by_ending.setdefault(ending, []).append(value % 2)
        for ending, parities in by_ending.items():
            assert parities.count(0) == parities.count(1), \
                f'ending {ending} still predicts answer parity at n={n}'
    cfg = dict(fixed_terminal='balanced')
    got = [N.cell_terminal(cfg, None, i) for i in range(64)]
    assert got[:16] == [8] * 16 and got[16:32] == [9] * 16
    assert got != [N.PRACTISED_RELS[i % 2] for i in range(64)], 'the old schedule survived'
    with N.registered_cells():
        first, _, _ = N.dev_unit('L-c6-prac', 0, namespace=FIXTURE_NAMESPACE)
        second, _, _ = N.dev_unit('L-c6-prac', 16, namespace=FIXTURE_NAMESPACE)
    assert first['a']['terminal'] == N.FIRST_REL
    assert second['a']['terminal'] == N.FIRST_REL + 1
    assert first['a']['answer'] == second['a']['answer'] == N.target_answer(0)
    return ('r(i) = 8 + (i // 16) % 2: each value appears '
            f'{N.DEV_N // (N.VALUE_COUNT * 2)}x per ending at n=64, '
            f'{N.CONFIRM_N // (N.VALUE_COUNT * 2)}x at n=512')


def test_scoring_refuses_a_partial_cell():
    """AUDIT FIX 7: the answer is a function of the unit index, so a prefix is biased."""
    _, panels, _ = N.load_dev_panels(panels_fixture())
    panel = panels['N-c4-p6']
    assert len(N.whole_cell(panel)) == panel['n']
    assert N.whole_cell(panel, panel['units']) == panel['units']
    for bad in (panel['units'][:4], panel['units'][1:], panel['units'][::2],
                list(reversed(panel['units']))):
        try:
            N.whole_cell(panel, bad)
        except RuntimeError as exc:
            assert 'partial cell' in str(exc), str(exc)
        else:
            raise AssertionError(f'a {len(bad)}-unit subset was accepted for scoring')
    answers = [u['a']['answer'] for u in panel['units'][:4]]
    assert len(set(answers)) == len(answers), 'the prefix is not even a random sample'
    return f'prefixes, suffixes, strides and reorderings of a {panel["n"]}-unit cell refused'


def test_poisoned_count_table_stays_quarantined():
    """AUDIT FIX 7: the composite r=10 quarantine is a PERMANENT preflight fixture."""
    _, mem, table = N.load_memory(fixture() / 'memory')
    counts = [list(row) for row in table['counts']]
    counts[N.ALPHABET_INDEX['LINK']][N.ALPHABET_INDEX['10']] = 10_000
    histograms = N._new_histograms()
    chosen, _ = N.propose_for_world(FIXTURE_SEED, 0, mem['stories'][0], counts, arm='G',
                                    questions_per_world=4,
                                    awake_items=mem['items'][:4], histograms=histograms)
    assert histograms['rejected'].get('composite_r10', 0) > 0, \
        'the poisoned table produced no composite r=10 candidate to reject'
    assert not any(N.composite_r10(pick['names']) for pick in chosen)
    assert all(not N.composite_r10(k.split()) for k in histograms['accepted'])
    proposed = [k for k in histograms['proposed'] if N.composite_r10(k.split())]
    assert proposed, 'the fixture no longer exercises the quarantine'
    return (f'{histograms["rejected"]["composite_r10"]} composite r=10 candidates '
            f'rejected before labelling, {len(proposed)} offending types drawn')


def _attack_experiment(name, mutate):
    """A confirmation-ready experiment folder with ONE exclusion file mutated.

    Everything else is valid -- a complete DEV-PASSED.json included -- so any refusal
    can only come from the exclusion-file check itself.
    """
    guard = scratch(name)
    root = guard / 'experiment'
    shutil.copytree(_fixture_experiment(), root)
    target = root / N.EXPERIMENT_LAYOUT['buffers'].format(seed=FIXTURE_SEED)
    path = target / N.FORBIDDEN_WORLDS
    before = json.loads(path.read_text())
    path.write_text(json.dumps(mutate(list(before)), indent=2))
    doc = _dev_passed_doc(root)
    doc['dev_panels']['path'] = str(root / N.EXPERIMENT_LAYOUT['dev_panels'])
    (root / 'DEV-PASSED.json').write_text(json.dumps(doc))
    return guard, root, target, before


def _confirmation_refuses(guard, root, out='panels'):
    try:
        N.build_dev_panels(guard / out, n=1, namespace=FIXTURE_NAMESPACE,
                           cells={'F-c1-r8': N.DEV_CELLS['F-c1-r8']}, confirmation=True,
                           experiment=root, seeds=[FIXTURE_SEED],
                           operator_history=root / N.EXPERIMENT_LAYOUT['operator_history'],
                           require_full_history=False, progress=False)
    except SystemExit as exc:
        assert not (guard / out).exists(), 'a refused confirmation build left a folder'
        return str(exc)
    raise AssertionError('the confirmation build accepted a mutated exclusion file')


def test_a_truncated_exclusion_file_is_refused():
    """AUDIT RE-CHECK 2 (R2-7): the auditor cut 1,024 world signatures down to 5.

    Shape validation passed and the confirmation build produced panels from the
    narrowed union.  Now every consumer checks the file against the sha256 AND entry
    count recorded by the artifact that published it.
    """
    guard, root, target, before = _attack_experiment('truncate', lambda w: w[:5])
    assert len(before) > 5, 'the fixture is too small to truncate meaningfully'
    try:
        N.artifact_exclusions(target)
    except SystemExit as exc:
        assert 'truncated' in str(exc) and f'{len(before)}' in str(exc), str(exc)
    else:
        raise AssertionError('artifact_exclusions accepted a truncated file')
    try:
        N.confirmation_exclusions(root, [FIXTURE_SEED])
    except SystemExit as exc:
        assert 'truncated' in str(exc), str(exc)
    else:
        raise AssertionError('confirmation_exclusions accepted a truncated file')
    message = _confirmation_refuses(guard, root)
    assert 'truncated' in message, message
    verdict = _audit(buffers=target)
    assert verdict['failures'] == ['exclusion_files_match_their_manifests'], \
        verdict['failures']
    assert verdict['passed'] is False and verdict.get('aborted')
    assert 'buffers' in verdict['checks']['exclusion_files_match_their_manifests']['detail']
    return (f'{len(before)} world signatures cut to 5: refused by the loader, the '
            f'confirmation build and the audit')


def test_a_tampered_exclusion_entry_is_refused():
    """R2-7, the subtler attack: same entry count, one signature swapped out."""
    def swap(worlds):
        # keep the list sorted and the same length, so only the hash can betray it
        worlds[-1] = 'f' * 64
        return sorted(set(worlds))

    guard, root, target, before = _attack_experiment('tamper', swap)
    after = json.loads((target / N.FORBIDDEN_WORLDS).read_text())
    assert len(after) == len(before) and after != before, 'the attack changed the count'
    try:
        N.artifact_exclusions(target)
    except SystemExit as exc:
        assert 'tampered' in str(exc) and 'hashes to' in str(exc), str(exc)
    else:
        raise AssertionError('artifact_exclusions accepted an edited file')
    message = _confirmation_refuses(guard, root)
    assert 'tampered' in message, message

    # and a file padded back to the right length with duplicates
    guard2, root2, target2, before2 = _attack_experiment(
        'tamper-dup', lambda w: [w[0]] * len(w))
    try:
        N.artifact_exclusions(target2)
    except SystemExit as exc:
        assert 'sorted list of distinct' in str(exc), str(exc)
    else:
        raise AssertionError('artifact_exclusions accepted a duplicate-padded file')
    assert 'sorted list of distinct' in _confirmation_refuses(guard2, root2)
    return ('one swapped signature and a duplicate-padded file of the right length '
            'are both refused')


def test_an_exclusion_file_without_its_manifest_is_refused():
    """R2-7: the sha can only be checked against the manifest that published it."""
    guard = scratch('no-manifest')
    root = guard / 'experiment'
    shutil.copytree(_fixture_experiment(), root)
    target = root / N.EXPERIMENT_LAYOUT['memory'].format(seed=FIXTURE_SEED)
    for name in N.ARTIFACT_MANIFESTS:
        if (target / name).exists():
            (target / name).unlink()
    try:
        N.artifact_exclusions(target)
    except SystemExit as exc:
        assert 'no artifact manifest' in str(exc), str(exc)
    else:
        raise AssertionError('an unanchored exclusion file was consumed')
    # and a manifest that never recorded what it published
    stream = root / N.EXPERIMENT_LAYOUT['stream'].format(seed=FIXTURE_SEED)
    index = stream / 'index.json'
    doc = json.loads(index.read_text())
    doc.pop('published_exclusions')
    index.write_text(json.dumps(doc, indent=2))
    try:
        N.artifact_exclusions(stream)
    except SystemExit as exc:
        assert 'no published_exclusions' in str(exc), str(exc)
    else:
        raise AssertionError('a manifest without published_exclusions was trusted')
    return 'a missing manifest and a manifest without published_exclusions both refuse'


def test_panel_manifests_record_the_exclusion_sources_they_consumed():
    """R2-7: the panels name every file they were built against, at its sha256."""
    manifest = json.loads((panels_fixture() / 'manifest.json').read_text())
    consumed = manifest['consumed_exclusions']
    names = [row['name'] for row in consumed]
    assert names.count('operator_history') == 1, names
    assert len(consumed) >= 2 and all(N.HEX64.match(str(row.get('sha256') or
                                                        row.get('questions_sha256')))
                                      for row in consumed), consumed
    history = [row for row in consumed if row['name'] == 'operator_history'][0]
    folder = Path(history['path'])
    assert history['questions_sha256'] == N.sha(folder / N.FORBIDDEN_QUESTIONS)
    assert history['worlds_sha256'] == N.sha(folder / N.FORBIDDEN_WORLDS)
    assert history['verified'] is True and history['manifest'].endswith('manifest.json')
    assert manifest['operator_history']['source'] == history \
        or manifest['operator_history']['source']['path'] == history['path']
    return f'{len(consumed)} consumed exclusion sources recorded with verified sha256s'


def main():
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    for name, function in tests:
        check(name[5:].replace('_', ' '), function)
    for folder in TEMP:
        shutil.rmtree(folder, ignore_errors=True)
    print(f'\n{PASSED} passed, {len(FAILED)} failed, {len(SKIPPED)} skipped', flush=True)
    if FAILED:
        for name, detail in FAILED:
            print(f'  {name}: {detail}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
