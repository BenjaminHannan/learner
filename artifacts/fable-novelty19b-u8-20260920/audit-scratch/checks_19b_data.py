#!/usr/bin/env python3
"""Independent 19b DATA checks: buffers and panels parsed from disk by my own code.

Re-uses only my own exp-19 audit decoder (`independent_checks.py`) and the frozen
grammar/interpreter modules.  The 19b builder's own audit is never consulted.
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP2 = HERE.parent
ROOT = EXP2.parent.parent
EXP19 = ROOT / 'artifacts' / 'fable-novelty19-replay-20260920'
sys.path.insert(0, str(EXP19 / 'audit'))
sys.path.insert(0, str(ROOT / 'scripts'))

import independent_checks as IC                       # noqa: E402
import fable_dispatcher_v3 as V3                      # noqa: E402
import fable_confirmation_panels as CP                # noqa: E402

SEEDS = (1900, 1901, 1902)
out = {}

# ------------------------------------------------------------------ 1. buffers
buf = {}
for seed in SEEDS:
    per_arm = {}
    for arm in ('U5', 'U8'):
        meta, blocks = IC.load_blocks(EXP2 / f'buffers-{seed}' / f'buffer-{arm}.pt')
        assert len(blocks) == 1
        block = blocks[0]
        stories = IC.my_stories(block)
        questions = IC.my_questions(block)
        owners = block['owner'].tolist()
        names = [IC.my_ops(q) for q in questions]
        per_arm[arm] = dict(meta=meta, block=block, stories=stories,
                            questions=questions, owners=owners, names=names)
    buf[seed] = per_arm

rows = {}
for seed, per_arm in buf.items():
    r = {}
    for arm, d in per_arm.items():
        lengths = Counter(len(n) for n in d['names'])
        endings = Counter(n[-1] for n in d['names'])
        comp = [n for n in d['names'] if len(n) >= 2 and n[-1] == '10']
        r[arm] = dict(
            questions=len(d['questions']), worlds=len(d['stories']),
            malformed=sum(1 for n in d['names'] if n is None or any(x.startswith('?') for x in n)),
            length_support=sorted(lengths), length_histogram=dict(sorted(lengths.items())),
            ending_histogram=dict(sorted(endings.items())),
            composite_r10=len(comp),
            declared_arm_calls=d['meta'].get('arm_calls'),
            kind=d['meta'].get('kind'), seed=d['meta'].get('seed'))
    # world bytes and owner order identical across arms?
    r['identical_world_rows'] = per_arm['U5']['stories'] == per_arm['U8']['stories']
    r['identical_owner_order'] = per_arm['U5']['owners'] == per_arm['U8']['owners']
    rows[seed] = r
out['buffers'] = rows
out['buffers_zero_composite_r10_all_seeds'] = all(
    rows[s][a]['composite_r10'] == 0 for s in SEEDS for a in ('U5', 'U8'))
out['buffers_support_claim'] = {
    s: dict(U5_within_1_5=set(rows[s]['U5']['length_support']) <= {1, 2, 3, 4, 5},
            U8_within_1_8=set(rows[s]['U8']['length_support']) <= set(range(1, 9)),
            U8_reaches_8=8 in rows[s]['U8']['length_support'])
    for s in SEEDS}

# ---- terminal rule: r in {8,9,10} at c=1, {8,9} otherwise, both arms ---------
bad_terminal = {}
for seed, per_arm in buf.items():
    for arm, d in per_arm.items():
        bad = [(''.join(n)) for n in d['names']
               if not ((len(n) == 1 and n[-1] in ('8', '9', '10'))
                       or (len(n) >= 2 and n[-1] in ('8', '9')))]
        if bad:
            bad_terminal[f'{seed}-{arm}'] = bad[:5]
out['terminal_rule_violations'] = bad_terminal

# ---- the one-change claim, recomputed from the frozen RNG keys ---------------
NS_LENGTH = 'astra-novelty19-uniform-v1'
NS_BIND = 'astra-novelty19-bind-v1'


def law(key, calls):
    rng = random.Random(key)
    c = rng.choice(list(calls))
    t = rng.choice(['8', '9', '10']) if c == 1 else rng.choice(['8', '9'])
    return ['LINK'] * (c - 1) + [t]


# every accepted sampled item must equal its own arm's law on the shared key, and
# a slot accepted by BOTH arms must carry the same start person
pair = {}
for seed in SEEDS:
    src = {}
    for arm in ('U5', 'U8'):
        doc = json.loads((EXP2 / f'buffers-{seed}' / 'audit.json').read_text())
        src[arm] = doc  # only for the fallback count; sources come from the block below
    # decode the per-item source rows straight out of the block
    import fable_novelty19_data as N  # frozen module: decode only
    law_mismatch, start_mismatch, shared = 0, 0, 0
    by_key = {}
    for arm in ('U5', 'U8'):
        dec = N.decode_block(buf[seed][arm]['block'])
        for s in dec['source']:
            if s['candidate'] is None:
                continue
            key = f'{NS_LENGTH}:{seed}:{s["memory_index"]}:{s["candidate"]}'
            calls = (1, 2, 3, 4, 5) if arm == 'U5' else (1, 2, 3, 4, 5, 6, 7, 8)
            if ' '.join(law(key, calls)) != s['operation_string']:
                law_mismatch += 1
            bind = random.Random(f'{NS_BIND}:{seed}:{s["memory_index"]}:{s["candidate"]}')
            people = sorted({int(r[0]) for r in buf[seed][arm]['stories'][s['memory_index']]})
            by_key.setdefault((s['memory_index'], s['candidate']), {})[arm] = s
    for slot, row in by_key.items():
        if len(row) == 2:
            shared += 1
            if len({r['start'] for r in row.values()}) != 1:
                start_mismatch += 1
    pair[seed] = dict(shared_slots=shared, law_mismatches=law_mismatch,
                      start_mismatches=start_mismatch)
out['paired_streams_recomputed'] = pair

# ---- U5 item identity with experiment 19's U --------------------------------
import fable_novelty19_data as N                      # noqa: E402


def item_view(rec):
    return [dict(owner=int(it['owner']), question=list(it['question']),
                 chain=[list(s) for s in it['chain']], hops=int(it['hops']),
                 terminal=int(it['terminal']), answer=int(it['answer']),
                 operation_string=src['operation_string'], start=int(src['start']),
                 candidate=src['candidate'], sampled=bool(src['sampled']))
            for it, src in zip(rec['items'], rec['source'])]


u5 = {}
for seed in SEEDS:
    mine = N.decode_block(buf[seed]['U5']['block'])
    old = N.load_buffer(EXP19 / f'buffers-{seed}', 'U')
    a, b = item_view(mine), item_view(old)
    u5[seed] = dict(items=len(a), other_items=len(b),
                    identical_items=bool(a == b),
                    identical_world_rows=bool(mine['stories'] == old['stories']),
                    item_view_sha256=N.digest_of(a),
                    other_item_view_sha256=N.digest_of(b))
out['u5_vs_experiment19_u'] = u5

# ---- stream mapping sha, recomputed --------------------------------------
import fable_novelty19b_data as B                     # noqa: E402
out['stream_mapping_sha256'] = B.STREAM_MAPPING_SHA256
out['stream_mapping_recomputed'] = N.digest_of(B.STREAM_MAPPING)

# ------------------------------------------------------------------ 2. panels
man = json.loads((EXP2 / 'dev-panels' / 'manifest.json').read_text())
cells = sorted(man['cells'])
panel = {}
distinct_fail, answer_fail, ending_fail, n_fail = [], [], [], []
people_report = {}
for cell in cells:
    doc = json.loads((EXP2 / 'dev-panels' / f'{cell}.json').read_text())
    units = doc['units']
    if len(units) != 64:
        n_fail.append((cell, len(units)))
    answers = Counter()
    endings = set()
    worst = 0
    for i, unit in enumerate(units):
        sides = ['a'] + (['b'] if unit['kind'] == 'pair' else [])
        for side in sides:
            u = unit[side]
            visited = [int(step[0]) for step in u['chain']]
            if len(visited) != len(set(visited)):
                distinct_fail.append((cell, i, side))
            worst = max(worst, len(visited))
        answers[unit['a']['answer']] += 1
        endings.add(int(unit['a']['question'][-2]))
    if sorted(answers) != list(range(12, 28)) or set(answers.values()) != {4}:
        answer_fail.append((cell, dict(answers)))
    if len(endings) != 1:
        ending_fail.append((cell, sorted(endings)))
    people_report[cell] = dict(units=len(units), hops=doc['hops'],
                               people=doc['people'], endings=sorted(endings),
                               max_visited=worst)
out['panels'] = dict(
    cells=len(cells), cell_list_matches_38=len(cells) == 38,
    units_not_64=n_fail,
    all_visited_distinct=not distinct_fail, distinct_failures=distinct_fail[:8],
    answer_balanced_all=not answer_fail, answer_failures=answer_fail[:4],
    single_ending_all=not ending_fail, ending_failures=ending_fail[:4],
    per_cell=people_report)

# ---- panel worlds vs every excluded source, recomputed ----------------------
panel_worlds, panel_qs = set(), set()
for cell in cells:
    doc = json.loads((EXP2 / 'dev-panels' / f'{cell}.json').read_text())
    for unit in doc['units']:
        for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
            u = unit[side]
            rowset = [r for i, r in enumerate(u['memory']) if r and i < u['where']]
            panel_worlds.add(CP.world_signature(CP.fact_tuples(rowset)))

train_worlds = set()
for seed in SEEDS:
    for arm in ('U5', 'U8'):
        d = buf[seed][arm]
        for owner in set(d['owners']):
            train_worlds.add(CP.world_signature(CP.fact_tuples(
                [r for r in d['stories'][owner] if r])))
out['panels_vs_19b_buffers'] = dict(
    panel_worlds=len(panel_worlds), buffer_worlds=len(train_worlds),
    overlap=len(panel_worlds & train_worlds))

print(json.dumps(out, indent=1, default=str)[:7000])
(HERE / 'checks-19b-data.json').write_text(json.dumps(out, indent=1, default=str))
