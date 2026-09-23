#!/usr/bin/env python3
"""Data re-check, part C: a permutation null for the shortcut scan, a per-item check of
the world-identity the exclusion is built on, and the full lockout refusal messages."""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))

import independent_checks as IC                        # noqa: E402
import fable_dispatcher_v3 as V3                       # noqa: E402
import fable_confirmation_panels as CP                 # noqa: E402
import fable_novelty19_data as N                       # noqa: E402

S = HERE / 'scratch2'
out = {}

# ---- 1. per-ITEM world identity: is the signature the trainer's artifacts publish the
#         same as the signature of the rows a question can actually see? -----------------
per_item = dict(items=0, all_equals_visible=0, where_lt_rowcount=0, published_equals_mine=0,
                published_present=0)
for label, folder in (('awake', S / 'awakeB'), ('memory', S / 'memB'), ('buffers', S / 'bufB')):
    for path in sorted(Path(folder).glob('*.pt')):
        _meta, blocks = IC.load_blocks(path)
        for block in blocks:
            stories = IC.my_stories(block)
            counts = block['row_count'].tolist()
            pub = block.get('world_signature')
            for k, owner in enumerate(block['owner'].tolist()):
                rows = stories[owner]
                where = int(block['where'][k])
                a = CP.world_signature(CP.fact_tuples([r for r in rows if r]))
                v = CP.world_signature(CP.fact_tuples(
                    [r for i, r in enumerate(rows) if r and i < where]))
                per_item['items'] += 1
                per_item['all_equals_visible'] += int(a == v)
                per_item['where_lt_rowcount'] += int(where < counts[owner])
                if pub is not None:
                    per_item['published_present'] += 1
                    mine = bytes(pub[owner].tolist()).hex()
                    per_item['published_equals_mine'] += int(mine == a)
per_item['every_item_visible_identity_matches_full_identity'] = (
    per_item['all_equals_visible'] == per_item['items'])
per_item['published_signature_matches_my_recomputation'] = (
    per_item['published_present'] == 0
    or per_item['published_equals_mine'] == per_item['published_present'])
out['world_identity_per_item'] = per_item

# ---- 2. permutation null for every (cell, feature) -------------------------------------
FEATURES = ('ending', 'start_entity', 'row_count', 'where', 'people_visited', 'calls',
            'distinct_people', 'index_mod_2', 'question_length', 'answer_position_hint')
REPS = 400
rng = random.Random(20260920)


def weighted_purity(feature, answers):
    groups = defaultdict(list)
    for f, a in zip(feature, answers):
        groups[f].append(a)
    total = sum(len(g) for g in groups.values())
    return sum(Counter(g).most_common(1)[0][1] for g in groups.values()) / total


scan, flagged = {}, []
for cell in N.DEV_CELL_ORDER:
    panel = json.loads((S / f'dev/{cell}.json').read_text())
    units = panel['units']
    ans = [u['a']['answer'] for u in units]
    feats = dict(
        ending=[int(u['a']['question'][-2]) for u in units],
        start_entity=[int(u['a']['question'][1]) for u in units],
        row_count=[len([r for r in u['a']['memory'] if r]) for u in units],
        where=[u['a']['where'] for u in units],
        people_visited=[len({s[0] for s in u['a']['chain']}) for u in units],
        calls=[len(u['a']['question']) - 3 for u in units],
        distinct_people=[len({r[0] for i, r in enumerate(u['a']['memory'])
                              if r and i < u['a']['where']}) for u in units],
        index_mod_2=[u['index'] % 2 for u in units],
        question_length=[len(u['a']['question']) for u in units],
        answer_position_hint=[u['a']['memory'][u['a']['where'] - 1][0]
                              if u['a']['where'] else -1 for u in units])
    cell_out = {}
    for name, f in feats.items():
        if len(set(f)) < 2:
            cell_out[name] = dict(groups=1, purity=None, p=None, verdict='constant')
            continue
        obs = weighted_purity(f, ans)
        null = []
        pool = list(ans)
        for _ in range(REPS):
            rng.shuffle(pool)
            null.append(weighted_purity(f, pool))
        p = (1 + sum(1 for x in null if x >= obs)) / (REPS + 1)
        cell_out[name] = dict(groups=len(set(f)), purity=round(obs, 3),
                              null_mean=round(sum(null) / REPS, 3), p=round(p, 4),
                              verdict='ABOVE CHANCE' if p < 0.01 else 'chance')
        if p < 0.01:
            flagged.append(dict(cell=cell, feature=name, purity=round(obs, 3),
                                null_mean=round(sum(null) / REPS, 3), p=round(p, 4),
                                groups=len(set(f))))
    scan[cell] = cell_out
out['shortcut_permutation_scan'] = dict(
    replications=REPS, alpha=0.01, cells=len(scan), features=list(FEATURES),
    n_tests=sum(1 for c in scan.values() for v in c.values() if v['p'] is not None),
    flagged=flagged,
    note='weighted purity sum_f (n_f/N) max_a P(a|f), compared with 400 answer shuffles '
         'that keep the feature fixed; index_mod_2 is a positive control that is not '
         'visible to the model, question_length/calls are model-visible.',
    per_cell=scan)

# ---- 3. full lockout refusal messages ---------------------------------------------------
prev = json.loads((HERE / 'data-recheck-b.json').read_text())
out['lockout_reasons'] = {k: (v['message'].split(': ', 1)[-1][:120] if not v['accepted']
                              else 'ACCEPTED')
                          for k, v in prev['lockout']['cases'].items()}

print(json.dumps({k: v for k, v in out.items() if k != 'shortcut_permutation_scan'}, indent=1))
print(json.dumps({k: v for k, v in out['shortcut_permutation_scan'].items()
                  if k != 'per_cell'}, indent=1))
(HERE / 'data-recheck-c.json').write_text(json.dumps(out, indent=1, default=str))
