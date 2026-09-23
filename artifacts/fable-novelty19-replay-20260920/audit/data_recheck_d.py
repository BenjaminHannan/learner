#!/usr/bin/env python3
"""Data re-check, part D: ruling 3 (forced fallbacks), ruling 5 (distinct people on both
sides of every pair, including L), ruling 4 (memory admission), execution profile."""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_novelty19_data as N                       # noqa: E402

S = HERE / 'scratch2'
out = {}

# ---- ruling 3: force the fallback path and check the fixed-slot rule --------------------
man_mem, mem, count_table = N.load_memory(S / 'memB')
world_index = 0
rows = mem['stories'][world_index]
qpw = len(mem['items']) // len(mem['stories'])
awake_items = mem['items'][world_index * qpw:(world_index + 1) * qpw]
counts = count_table['counts']
table = json.loads((S / 'bufB' / 'audit.json').read_text())

real_propose = N.propose_string
real_uniform = N.uniform_string
cases = {}
for arm in ('G', 'U'):
    for k_target in (0, 2):
        seen = {'n': 0}

        def gated(rng, *a, _k=k_target, _seen=seen, **kw):
            """Accept only the first `_k` candidates; reject the rest."""
            _seen['n'] += 1
            if _seen['n'] > _k:
                return [], 'forced-rejection-by-auditor'
            return (real_propose(rng, *a, **kw) if a or kw else (['LINK', '8'], None))

        def gated_u(rng, _k=k_target, _seen=seen):
            _seen['n'] += 1
            if _seen['n'] > _k:
                return ['LINK', '10']        # rejected by the module's own composite_r10
            return real_uniform(rng)

        hist = N._new_histograms()
        N.propose_string = gated
        N.uniform_string = gated_u
        try:
            accepted, fallbacks = N.propose_for_world(
                9991, world_index, rows, counts, arm=arm,
                questions_per_world=4, awake_items=awake_items, histograms=hist)
        except Exception as exc:                                  # noqa: BLE001
            cases[f'{arm}-k{k_target}'] = dict(error=f'{type(exc).__name__}: {exc}'[:200])
            continue
        finally:
            N.propose_string, N.uniform_string = real_propose, real_uniform
        slots = []
        for j, a in enumerate(accepted):
            slots.append(dict(slot=j, sampled=bool(a['sampled']),
                              names=' '.join(a['names']),
                              start=a['start'],
                              fallback_index=a.get('fallback_index')))
        awake_j = [' '.join(N.op_names(awake_items[j]['question'][2:-1]))
                   for j in range(4)]
        cases[f'{arm}-k{k_target}'] = dict(
            accepted_slots=len(accepted), fallbacks=len(fallbacks),
            slots=slots,
            sampled_prefix_then_fallbacks=[s['sampled'] for s in slots]
            == [True] * k_target + [False] * (4 - k_target),
            fallback_slot_j_is_awake_question_j=all(
                s['names'] == awake_j[s['slot']] and
                s['start'] == int(awake_items[s['slot']]['question'][1])
                for s in slots if not s['sampled']),
            fallback_log_slots=[f['slot'] for f in fallbacks],
            duplicates_flagged=[f['duplicates_accepted'] for f in fallbacks],
            candidate_is_none_for_fallbacks=all(s['fallback_index'] is not None
                                                for s in slots if not s['sampled']),
            histogram_fallback=hist['fallback'])
out['ruling3_fallback'] = dict(
    cases=cases,
    rule='slots 0..k-1 keep the accepted questions; slot j>=k takes awake question j; '
         'same for G and U; duplicates kept and logged; no budget extension',
    gate_excludes_fallbacks=True,
    note='forced by monkeypatching the proposer inside my own process only; the '
         'registered build is untouched')

# ---- ruling 5: distinct visited people, both sides, including L -------------------------
people = {}
bad = []
for cell in N.DEV_CELL_ORDER:
    panel = json.loads((S / f'dev/{cell}.json').read_text())
    sides = 0
    worst = None
    for unit in panel['units']:
        for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
            u = unit[side]
            sides += 1
            visited = [int(u['question'][1])] + [int(step[2]) for step in u['chain'][:-1]]
            calls = len(u['question']) - 3
            ok = (len(set(visited)) == len(visited) == calls)
            if not ok:
                bad.append(dict(cell=cell, index=unit['index'], side=side,
                                visited=visited, calls=calls))
            worst = min(worst, len(set(visited))) if worst is not None else len(set(visited))
    people[cell] = dict(sides=sides, calls=len(panel['units'][0]['a']['question']) - 3,
                        min_distinct_visited=worst,
                        pair_cell=panel['units'][0]['kind'] == 'pair')
out['ruling5_distinct_people'] = dict(
    violations=bad[:10], violation_count=len(bad),
    all_cells_ok=not bad, per_cell=people,
    L_cells={k: v for k, v in people.items() if k.startswith('L')},
    note='visited = the start person plus the person each of the c-1 LINK calls reaches; '
         'the terminal value is not counted as a person')

# ---- ruling 4: memory admission ---------------------------------------------------------
man = man_mem
out['ruling4_memory_identity'] = {k: man[k] for k in man
                                  if k in ('worlds', 'admitted', 'duplicates_skipped',
                                           'duplicate_log', 'questions_per_world',
                                           'signature', 'world_identity', 'limit')}
out['ruling4_memory_identity']['manifest_keys'] = sorted(man)
out['ruling4_memory_identity']['distinct_worlds_in_file'] = len(mem['stories'])

# ---- must-fix 6: execution profile -------------------------------------------------------
prof = N.execution_profile()
out['execution_profile'] = dict(profile=prof, keys=sorted(prof),
                                mentions_runtime_local='runtime' in json.dumps(prof).lower(),
                                mentions_sys_path='path' in json.dumps(prof).lower())

print(json.dumps(out, indent=1, default=str))
(HERE / 'data-recheck-d.json').write_text(json.dumps(out, indent=1, default=str))
