#!/usr/bin/env python3
"""INDEPENDENT auditor for the novelty-19 data side.

Reads the on-disk artifacts with `torch.load` and decodes the neutral block schema
HERE -- it never calls `fable_novelty19_data.decode_block`, `op_names`,
`composite_r10`, `generation_gate` or `r10_exposure`.  The only frozen project code it
uses is the grammar/interpreter (`fable_dispatcher_v3`, `fable_dispatcher`,
`astra_canonical_operator.visible_signature`), as instructed.

Usage:
  independent_checks.py --stream S --memory M --buffers B --dev-panels D [--json OUT]
"""
import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parent.parent.parent.parent
sys.path.insert(0, str(WORKTREE / 'scripts'))

import fable_dispatcher_v3 as V3                               # noqa: E402
import fable_dispatcher as V1                                  # noqa: E402

A = V3.A
torch = V3.torch                                               # runtime.local.json roots
QUESTION, ANSWER, WORLD, LINK = V3.QUESTION, V3.ANSWER, V3.WORLD, V3.LINK
R8, R9, R10 = 8, 9, 10
NAME = {LINK: 'LINK', 8: '8', 9: '9', 10: '10'}
ALPHA = ('BOS', 'LINK', '8', '9', '10', 'EOS')
AI = {n: i for i, n in enumerate(ALPHA)}

RESULT = {}


def note(key, value):
    RESULT[key] = value
    return value


# ----------------------------------------------------------------- my own decoder
def load_blocks(path):
    payload = torch.load(Path(path), weights_only=False)
    return payload['meta'], payload['blocks']


def my_stories(block):
    """Rebuild the visible rows from `rows`/`row_count` with no builder help."""
    out = []
    for i, n in enumerate(block['row_count'].tolist()):
        story = []
        for j in range(n):
            row = block['rows'][i, j].tolist()
            while row and row[-1] == 0:
                row.pop()
            story.append(row)
        out.append(story)
    return out


def my_questions(block):
    """Raw question token lists, straight from the `question` tensor."""
    return [[t for t in block['question'][q].tolist() if t]
            for q in range(block['question'].shape[0])]


def my_ops(question):
    """Operation string of a raw question, entity names removed -- my own parse.

    A well-formed question is [QUESTION, person, op..., ANSWER].  Anything else is
    reported instead of being silently normalised.
    """
    if len(question) < 4 or question[0] != QUESTION or question[-1] != ANSWER:
        return None
    return [NAME.get(t, f'?{t}') for t in question[2:-1]]


def composite10(names):
    return len(names) >= 2 and names[-1] == '10'


# ----------------------------------------------------------------- 1. leakage
def scan_source(label, stories, questions, owners):
    """Every operation string + a full malformed/type census for one corpus."""
    types = Counter()
    malformed = []
    r10_composite = []
    for q, question in enumerate(questions):
        names = my_ops(question)
        if names is None or any(n.startswith('?') for n in names):
            malformed.append((q, question))
            continue
        key = ' '.join(names)
        types[key] += 1
        if composite10(names):
            r10_composite.append((q, key))
    cells = Counter()
    for q, question in enumerate(questions):
        names = my_ops(question) or []
        cells[f'c={len(names)},r={names[-1] if names else "?"}'] += 1
    return dict(label=label, questions=len(questions), types=dict(types),
                length_relation_cells=dict(cells), malformed=len(malformed),
                composite_r10_hits=r10_composite[:20],
                composite_r10_count=len(r10_composite),
                c45_r10_count=sum(1 for q in questions
                                  if (n := my_ops(q)) and len(n) in (4, 5) and n[-1] == '10'))


def sigs_of(stories, questions, owners):
    return {A.visible_signature(stories[owners[q]], questions[q])
            for q in range(len(questions))}


# ----------------------------------------------------------------- 2. transitions
def my_counts(all_names):
    counts = [[0] * 6 for _ in range(6)]
    for names in all_names:
        states = ['BOS'] + list(names) + ['EOS']
        for a, b in zip(states[:-1], states[1:]):
            counts[AI[a]][AI[b]] += 1
    return counts


def analytic_length_distribution(counts):
    """Exact accept probability per c under the builder's own sampling rules.

    Reimplemented here from the SPEC's rules (BOS-start, <=7 draws after BOS,
    reject >5 calls / LINK-terminated / empty), not from the builder's code.
    """
    def p(a, b):
        row = counts[AI[a]]
        tot = sum(row)
        return row[AI[b]] / tot if tot else 0.0
    out = {}
    # c = 1: BOS -> terminal -> EOS
    for r in ('8', '9', '10'):
        out[f'c=1,r={r}'] = p('BOS', r) * p(r, 'EOS')
    for c in range(2, 8):
        base = p('BOS', 'LINK') * (p('LINK', 'LINK') ** (c - 2))
        for r in ('8', '9', '10'):
            out[f'c={c},r={r}'] = base * p('LINK', r) * p(r, 'EOS')
    return out


# ----------------------------------------------------------------- main checks
def check_awake(stream, limit=None):
    folder = Path(stream)
    index = json.loads((folder / 'index.json').read_text())
    stories_all, questions_all, owners_all, names_all = [], [], [], []
    sigs = set()
    hash_ok = True
    updates = 0
    for entry in index['chunks']:
        path = folder / entry['name']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hash_ok = hash_ok and (digest == entry['sha256'])
        _, blocks = load_blocks(path)
        for block in blocks:
            updates += 1
            st = my_stories(block)
            qs = my_questions(block)
            ow = block['owner'].tolist()
            base = len(stories_all)
            stories_all.extend(st)
            questions_all.extend(qs)
            owners_all.extend([o + base for o in ow])
            for q in qs:
                names_all.append(my_ops(q))
            for row in block['signature'].tolist():
                sigs.add(bytes(row).hex())
    census = scan_source('awake', stories_all, questions_all, owners_all)
    # independently recompute every stored signature from rows+question
    recomputed = sigs_of(stories_all, questions_all, owners_all)
    return dict(index_hashes_match=hash_ok, updates=updates, seed=index['seed'],
                census=census, stored_signatures=len(sigs),
                recomputed_signatures=len(recomputed),
                signatures_agree=(recomputed == sigs),
                names=names_all, stories=stories_all, questions=questions_all,
                owners=owners_all, signatures=sigs)


def check_memory(memory, awake):
    folder = Path(memory)
    _, blocks = load_blocks(folder / 'worlds.pt')
    block = blocks[0]
    st, qs = my_stories(block), my_questions(block)
    ow = block['owner'].tolist()
    table = json.loads((folder / 'transition-counts.json').read_text())
    names = [my_ops(q) for q in qs]
    mine = my_counts(names)
    total_transitions = sum(len(n) + 1 for n in names)
    integer_only = all(isinstance(c, int) for row in table['counts'] for c in row)
    census = scan_source('memory', st, qs, ow)
    my_sigs = sigs_of(st, qs, ow)
    ws = {bytes(r).hex() for r in block['world_signature'].tolist()}
    return dict(worlds=len(st), questions=len(qs), distinct_world_signatures=len(ws),
                counts_match_my_recount=(mine == table['counts']),
                my_counts=mine,
                counts_are_integers=integer_only,
                no_smoothing_total_matches=(sum(sum(r) for r in mine) == total_transitions),
                total_transitions=total_transitions,
                census=census,
                questions_subset_of_awake=my_sigs.issubset(awake['signatures']),
                signatures=my_sigs, names=names, stories=st)


def check_buffers(buffers, memory_stories, counts):
    folder = Path(buffers)
    manifest = json.loads((folder / 'manifest.json').read_text())
    arms = manifest['arms']
    data = {}
    for arm in arms:
        path = folder / f'buffer-{arm}.pt'
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _, blocks = load_blocks(path)
        b = blocks[0]
        st, qs = my_stories(b), my_questions(b)
        ow = b['owner'].tolist()
        data[arm] = dict(block=b, stories=st, questions=qs, owners=ow,
                         sha_on_disk=digest,
                         sha_matches_manifest=(digest == manifest['files'][path.name]),
                         census=scan_source(f'buffer-{arm}', st, qs, ow),
                         signatures=sigs_of(st, qs, ow))
    first = arms[0]
    fairness = dict(arms=arms)
    for arm in arms[1:]:
        fairness[f'rows_identical_{first}_vs_{arm}'] = bool(
            torch.equal(data[first]['block']['rows'], data[arm]['block']['rows']))
        fairness[f'row_count_identical_{first}_vs_{arm}'] = bool(
            torch.equal(data[first]['block']['row_count'], data[arm]['block']['row_count']))
        fairness[f'owner_order_identical_{first}_vs_{arm}'] = bool(
            torch.equal(data[first]['block']['owner'], data[arm]['block']['owner']))
        fairness[f'world_sig_identical_{first}_vs_{arm}'] = bool(
            torch.equal(data[first]['block']['world_signature'],
                        data[arm]['block']['world_signature']))
        fairness[f'namespaces_identical_{first}_vs_{arm}'] = (
            list(data[first]['block']['namespaces']) == list(data[arm]['block']['namespaces']))
        fairness[f'stories_equal_memory_{arm}'] = (data[arm]['stories'] == memory_stories)
    fairness['sizes'] = {a: len(data[a]['questions']) for a in arms}
    fairness['sizes_equal'] = len({len(data[a]['questions']) for a in arms}) == 1
    fairness['stories_equal_memory_' + first] = (data[first]['stories'] == memory_stories)

    # labels: relabel EVERY buffer question with the frozen interpreter, twice over
    relabel = {}
    for arm in arms:
        b, st, qs, ow = (data[arm]['block'], data[arm]['stories'], data[arm]['questions'],
                         data[arm]['owners'])
        bad_answer = bad_chain = 0
        for q in range(len(qs)):
            rows = st[ow[q]]
            eligible = [True] * len(rows)
            chain = V3.interpret(rows, eligible, qs[q])
            alt = V1.walk(V1.fact_table(rows, eligible), qs[q])
            stored_answer = int(b['answer'][q])
            c = int(b['calls'][q])
            stored_chain = [[int(b['people'][q, s]), int(b['ops'][q, s]),
                             int(b['chain_result'][q, s])] for s in range(c)]
            if chain != alt or chain[-1][2] != stored_answer:
                bad_answer += 1
            if chain != stored_chain:
                bad_chain += 1
        relabel[arm] = dict(answer_mismatches=bad_answer, chain_mismatches=bad_chain)

    # U uniformity
    u = data.get('U')
    u_report = None
    if u is not None:
        cs = Counter(len(my_ops(q)) for q in u['questions'])
        rs = Counter((len(my_ops(q)), my_ops(q)[-1]) for q in u['questions'])
        u_report = dict(calls_histogram={str(k): v for k, v in sorted(cs.items())},
                        r10_at_c_ge_2=sum(v for (c, r), v in rs.items() if r == '10' and c >= 2),
                        cell_histogram={f'c={c},r={r}': v for (c, r), v in sorted(rs.items())})

    # generation gate, BOTH readings, from the audit.json source list
    audit = json.loads((folder / 'audit.json').read_text())
    gate = {}
    g = data.get('G')
    if g is not None:
        src = audit['per_arm']['G']
        srcs = json.loads((folder / 'buffer-G.pt').with_suffix('.pt').name and '[]')  # noqa
        _, gblocks = load_blocks(folder / 'buffer-G.pt')
        gsource = gblocks[0]['source']
        for calls, rel in ((4, 8), (4, 9), (5, 8), (5, 9)):
            key = ' '.join(['LINK'] * (calls - 1) + [str(rel)])
            inst, worlds, raw = set(), set(), set()
            for q, s in enumerate(gsource):
                if not s.get('sampled'):
                    continue
                names = my_ops(g['questions'][q])
                if ' '.join(names) != key:
                    continue
                inst.add((s['memory_index'], tuple(g['questions'][q])))
                worlds.add(s['memory_index'])
                raw.add(tuple(g['questions'][q]))
            gate[f'c={calls},r={rel}'] = dict(
                reading_A_world_question_instances=len(inst),
                reading_B_distinct_raw_question_tokens=len(raw),
                distinct_worlds=len(worlds),
                reading_A_passes=bool(len(inst) >= 16 and len(worlds) >= 16),
                reading_B_passes=bool(len(raw) >= 16 and len(worlds) >= 16))
        gate['builders_reported'] = audit['generation_gate']['structures']
        # fallbacks / candidate accounting
        gate['G_sampled'] = sum(1 for s in gsource if s.get('sampled'))
        gate['G_fallbacks'] = sum(1 for s in gsource if not s.get('sampled'))
        gate['G_candidates_used_max'] = max(
            (s['candidate'] for s in gsource if s.get('candidate') is not None), default=None)

    # accepted-length distribution vs the analytic prediction from the counts
    pred = analytic_length_distribution(counts)
    total_valid = sum(v for k, v in pred.items())
    n = len(data['G']['questions']) if 'G' in data else 0
    expected = {k: round(v / total_valid * n, 1) for k, v in pred.items() if v > 0}
    observed = data['G']['census']['length_relation_cells'] if 'G' in data else {}
    length = dict(analytic_raw_probability=pred, expected_if_iid_given_accept=expected,
                  observed=observed, buffer_questions=n,
                  rejected_probability_mass=round(1 - total_valid, 6))

    order = json.loads((folder / 'offline-order.json').read_text())
    rebuilt = []
    for u in range(order['updates']):
        rng = random.Random(f'astra-novelty19-offline-order-v1:{order["seed"]}:{u}')
        rebuilt.append([rng.randrange(order['worlds']) for _ in range(order['visits'])])
    shared = dict(order_reproducible=(rebuilt == order['order']),
                  updates=order['updates'], visits=order['visits'],
                  single_shared_order_file=True,
                  order_files_present=sorted(p.name for p in folder.glob('offline-order*')))

    return dict(data=data, fairness=fairness, relabel=relabel, uniform=u_report,
                gate=gate, length=length, offline_order=shared,
                manifest_hashes_ok=all(data[a]['sha_matches_manifest'] for a in arms))


def check_dev_panels(panels, awake, memory, buffers, legacy_union):
    folder = Path(panels)
    manifest = json.loads((folder / 'manifest.json').read_text())
    forbidden = set(json.loads((folder / 'forbidden-semantics.json').read_text()))
    cells = {}
    all_sem, all_tensor = set(), set()
    problems = []
    for cell in manifest['cell_order']:
        panel = json.loads((folder / f'{cell}.json').read_text())
        units = panel['units']
        answers = Counter(u['a']['answer'] for u in units)
        # answer implied by index?
        implied = all(u['a']['answer'] == 12 + (u['index'] % 16) for u in units)
        # the unit payload a model can see
        leaks = []
        for u in units:
            visible = set(json.dumps(u['a']['memory']).split()) if False else None
            for key in ('index', 'target_answer', 'namespace', 'attempts'):
                if key in u:
                    leaks.append(key)
            break
        # distinct-people rule + terminal + hop count, recomputed from the question
        hop_bad = term_bad = distinct_bad = ans_bad = 0
        for u in units:
            side = u['a']
            q = side['question']
            names = my_ops(q)
            if names is None or len(names) != panel['hops']:
                hop_bad += 1
                continue
            if panel['fixed_terminal'] not in (None, 'balanced'):
                if names[-1] != str(panel['fixed_terminal']):
                    term_bad += 1
            elif panel['fixed_terminal'] == 'balanced' and names[-1] not in ('8', '9'):
                term_bad += 1
            rows = [r for i, r in enumerate(side['memory']) if r and i < side['where']]
            eligible = [True] * len(rows)
            chain = V3.interpret(rows, eligible, q)
            people = [step[0] for step in chain]
            if len(set(people)) != len(people):
                distinct_bad += 1
            if chain[-1][2] != side['answer']:
                ans_bad += 1
        pair = None
        if panel['kind'] == 'pair':
            same = diff = 0
            for u in units:
                if u['a']['answer'] == u['b']['answer']:
                    same += 1
                else:
                    diff += 1
            pair = dict(answer_same=same, answer_changed=diff,
                        invariant_expected=panel['invariant'],
                        correct=(same == len(units) if panel['invariant']
                                 else diff == len(units)))
        for u in units:
            for side in ['a'] + (['b'] if panel['kind'] == 'pair' else []):
                rows = [r for i, r in enumerate(u[side]['memory'])
                        if r and i < u[side]['where']]
                all_sem.add(A.visible_signature(rows, u[side]['question']))
                all_tensor.add(A.tensor_signature(rows, u[side]['question']))
        cells[cell] = dict(n=panel['n'], hops=panel['hops'], people=panel['people'],
                           fixed_terminal=panel['fixed_terminal'], kind=panel['kind'],
                           answer_values=len(answers),
                           answer_counts=sorted(set(answers.values())),
                           chance_per_cell=round(max(answers.values()) / panel['n'], 4),
                           answer_equals_12_plus_index_mod_16=implied,
                           unit_keys_present=sorted(set(units[0]) - {'a', 'b'}),
                           hop_mismatch=hop_bad, terminal_mismatch=term_bad,
                           repeated_people=distinct_bad, answer_mismatch=ans_bad,
                           pair=pair)
        if hop_bad or term_bad or distinct_bad or ans_bad:
            problems.append(cell)
    overlap = dict(
        vs_legacy=len(all_sem & legacy_union),
        vs_awake=len(all_sem & awake['signatures']),
        vs_memory=len(all_sem & memory['signatures']),
        vs_buffers={a: len(all_sem & buffers['data'][a]['signatures'])
                    for a in buffers['data']},
    )
    return dict(cells=cells, cell_count=len(cells), problems=problems,
                semantic_signatures=len(all_sem), tensor_signatures=len(all_tensor),
                forbidden_file_matches=(all_sem == forbidden),
                all_units_unique=(len(all_sem) == sum(
                    c['n'] * (2 if c['kind'] == 'pair' else 1) for c in cells.values())),
                overlap=overlap)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stream', required=True)
    ap.add_argument('--memory', required=True)
    ap.add_argument('--buffers', required=True)
    ap.add_argument('--dev-panels', required=True)
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    legacy = set()
    for rel in ('artifacts/fable-dispatcher-v3-20260920/panels/forbidden-semantics.json',
                'artifacts/fable-baseline-transformer-v2-20260920/fit-panels/'
                'forbidden-semantics.json',
                'artifacts/fable-baseline-transformer-v2-20260920/confirm-panels/'
                'forbidden-semantics.json',
                'artifacts/fable-confirmation-panels-20260920/dispatcher/'
                'forbidden-semantics.json',
                'artifacts/fable-confirmation-panels-20260920/operator/'
                'forbidden-semantics.json'):
        legacy |= set(json.loads((WORKTREE / rel).read_text()))
    pilot = WORKTREE / ('artifacts/fable-dispatcher-pilot-20260920/panels/'
                        'forbidden-semantics.json')
    pilot_sigs = set(json.loads(pilot.read_text())) if pilot.exists() else None

    awake = check_awake(args.stream)
    memory = check_memory(args.memory, awake)
    buffers = check_buffers(args.buffers, memory['stories'],
                            json.loads((Path(args.memory) /
                                        'transition-counts.json').read_text())['counts'])
    dev = check_dev_panels(args.dev_panels, awake, memory, buffers, legacy)

    counts = memory['my_counts']

    def p(a, b):
        row = counts[AI[a]]
        return row[AI[b]] / sum(row) if sum(row) else None

    out = dict(
        awake=dict({k: v for k, v in awake.items()
                    if k not in ('names', 'stories', 'questions', 'owners', 'signatures')}),
        memory={k: v for k, v in memory.items()
                if k not in ('signatures', 'names', 'stories')},
        transition_probabilities=dict(
            BOS_to_LINK=p('BOS', 'LINK'), LINK_to_LINK=p('LINK', 'LINK'),
            LINK_to_10=p('LINK', '10'), LINK_to_8=p('LINK', '8'), LINK_to_9=p('LINK', '9'),
            BOS_to_10=p('BOS', '10'), ten_to_EOS=p('10', 'EOS'),
            ten_row_total=sum(counts[AI['10']]),
            empty_rows=[ALPHA[i] for i, r in enumerate(counts) if sum(r) == 0]),
        buffers=dict(fairness=buffers['fairness'], relabel=buffers['relabel'],
                     uniform=buffers['uniform'], gate=buffers['gate'],
                     length=buffers['length'], offline_order=buffers['offline_order'],
                     manifest_hashes_ok=buffers['manifest_hashes_ok'],
                     census={a: buffers['data'][a]['census'] for a in buffers['data']}),
        dev_panels=dev,
        legacy_union_size=len(legacy),
        pilot_panel_present=pilot.exists(),
        pilot_overlap_with_legacy_union=(len(pilot_sigs & legacy)
                                         if pilot_sigs is not None else None),
        pilot_size=(len(pilot_sigs) if pilot_sigs is not None else None),
    )
    text = json.dumps(out, indent=2, default=str)
    if args.json:
        Path(args.json).write_text(text)
    print(text)


if __name__ == '__main__':
    main()
