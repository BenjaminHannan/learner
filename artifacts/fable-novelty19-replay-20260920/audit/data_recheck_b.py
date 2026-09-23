#!/usr/bin/env python3
"""Data re-check, part B: the lockout, confirmation world exclusion, rulings 1-6."""
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))

import independent_checks as IC                        # noqa: E402
import fable_dispatcher_v3 as V3                       # noqa: E402
torch = V3.torch
import fable_confirmation_panels as CP                 # noqa: E402
import fable_novelty19_data as N                       # noqa: E402

S = HERE / 'scratch2'
SEEDS = (9991,)
out = {}


# ------------------------------------------------------------------ my own world signature
def my_world_signature(rows, where=None):
    """Canonical question-free fact-set signature of the rows VISIBLE to a question."""
    visible = [r for i, r in enumerate(rows) if r and (where is None or i < where)]
    return CP.world_signature(CP.fact_tuples(visible))


def training_worlds(folder, kind):
    """(all-rows signatures, visible-rows signatures, where==row_count?) of an artifact."""
    allsig, vis, where_eq = set(), set(), True
    paths = sorted(Path(folder).glob('*.pt'))
    for path in paths:
        _meta, blocks = IC.load_blocks(path)
        for block in blocks:
            stories = IC.my_stories(block)
            counts = block['row_count'].tolist()
            for k, owner in enumerate(block['owner'].tolist()):
                rows = stories[owner]
                where = int(block['where'][k])
                allsig.add(my_world_signature(rows))
                vis.add(my_world_signature(rows, where))
                if where != counts[owner]:
                    where_eq = False
    return dict(kind=kind, files=len(paths), all_row_signatures=len(allsig),
                visible_row_signatures=len(vis), where_equals_row_count=where_eq,
                _all=allsig, _vis=vis)


art = {}
for label, folder in (('awake', S / 'awakeB'), ('memory', S / 'memB'), ('buffers', S / 'bufB')):
    art[label] = training_worlds(folder, label)
train_all = set().union(*(a['_all'] for a in art.values()))
train_vis = set().union(*(a['_vis'] for a in art.values()))

# ------------------------------------------------------------------ 1. lockout matrix
exp = S / 'exp9991'
shutil.rmtree(exp, ignore_errors=True)
exp.mkdir(parents=True)
for key, src in (('stream', S / 'awakeB'), ('memory', S / 'memB'), ('buffers', S / 'bufB')):
    (exp / N.EXPERIMENT_LAYOUT[key].format(seed=9991)).symlink_to(src.resolve())
(exp / N.EXPERIMENT_LAYOUT['dev_panels']).symlink_to((S / 'dev').resolve())
(exp / N.EXPERIMENT_LAYOUT['operator_history']).symlink_to((S / 'ophist').resolve())

H = 'cd' * 32
good = dict(schema=N.DEV_PASSED_SCHEMA, seeds=[9991], report_sha256=H,
            dev_panels=dict(path=str((S / 'dev').resolve()),
                            manifest_sha256=N.sha(S / 'dev' / 'manifest.json')),
            awake_checkpoints={k: H for k in N.checkpoint_keys('awake', SEEDS)},
            offline_checkpoints={k: H for k in N.checkpoint_keys('offline', SEEDS)})


def variant(**changes):
    doc = json.loads(json.dumps(good))
    for key, value in changes.items():
        if value is None:
            doc.pop(key, None)
        else:
            doc[key] = value
    return doc


cases = {}
bad_panels = variant()
bad_panels['dev_panels'] = dict(path=str((S / 'dev').resolve()), manifest_sha256='ab' * 32)
short_awake = variant()
short_awake['awake_checkpoints'] = {'D-9991': H}
not_hex = variant()
not_hex['offline_checkpoints'] = dict(short_awake and
                                      {k: 'not-a-hash' for k in
                                       N.checkpoint_keys('offline', SEEDS)})
for label, body in (('missing', None),
                    ('empty', ''),
                    ('not-json', 'nonsense'),
                    ('empty-object', '{}'),
                    ('wrong-schema', json.dumps(variant(schema='other'))),
                    ('wrong-seeds', json.dumps(variant(seeds=[1900, 1901, 1902]))),
                    ('no-report-hash', json.dumps(variant(report_sha256=None))),
                    ('panel-hash-mismatch', json.dumps(bad_panels)),
                    ('missing-checkpoints', json.dumps(short_awake)),
                    ('checkpoints-not-sha', json.dumps(not_hex)),
                    ('valid', json.dumps(good))):
    flag = exp / 'DEV-PASSED.json'
    flag.unlink(missing_ok=True)
    if body is not None:
        flag.write_text(body)
    try:
        cases[label] = dict(accepted=True, value=N.validate_dev_passed(exp, seeds=SEEDS))
    except SystemExit as err:
        cases[label] = dict(accepted=False, message=str(err)[:150])
out['lockout'] = dict(cases=cases,
                      all_bad_refused=all(not v['accepted'] for k, v in cases.items()
                                          if k != 'valid'),
                      valid_accepted=cases['valid']['accepted'])

# ------------------------------------------------------------------ 2. confirmation panels
(exp / 'DEV-PASSED.json').write_text(json.dumps(good))
conf = S / 'confirm9991'
shutil.rmtree(conf, ignore_errors=True)
subset = ['N-c4-p6', 'E-c5-link', 'F-c1-r8', 'L-c6-prac']
cells = {c: N.DEV_CELLS[c] for c in subset}
built = N.build_dev_panels(conf, n=64, namespace=N.NS_CONFIRM, cells=cells,
                           cell_order=subset, confirmation=True, experiment=exp,
                           seeds=SEEDS, progress=False)
conf_manifest = json.loads((conf / 'manifest.json').read_text())
conf_worlds, conf_units = set(), 0
for cell in subset:
    panel = json.loads((conf / f'{cell}.json').read_text())
    for unit in panel['units']:
        conf_units += 1
        for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
            conf_worlds.add(my_world_signature(unit[side]['memory'], unit[side]['where']))
dev_worlds = set()
for cell in N.DEV_CELL_ORDER:
    panel = json.loads((S / 'dev' / f'{cell}.json').read_text())
    for unit in panel['units']:
        for side in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
            dev_worlds.add(my_world_signature(unit[side]['memory'], unit[side]['where']))

out['confirmation_world_exclusion'] = dict(
    confirmation_units=conf_units, confirmation_world_signatures=len(conf_worlds),
    training_world_signatures_all_rows=len(train_all),
    training_world_signatures_visible_rows=len(train_vis),
    where_equals_row_count={k: v['where_equals_row_count'] for k, v in art.items()},
    all_rows_equal_visible_rows={k: v['_all'] == v['_vis'] for k, v in art.items()},
    overlap_confirmation_x_training_allrows=len(conf_worlds & train_all),
    overlap_confirmation_x_training_visible=len(conf_worlds & train_vis),
    overlap_confirmation_x_development=len(conf_worlds & dev_worlds),
    overlap_development_x_training_allrows=len(dev_worlds & train_all),
    overlap_development_x_training_visible=len(dev_worlds & train_vis),
    manifest_training_exclusion=conf_manifest['training_exclusion'] and dict(
        questions=conf_manifest['training_exclusion']['questions'],
        worlds=conf_manifest['training_exclusion']['worlds'],
        sources=[s['name'] for s in conf_manifest['training_exclusion']['sources']]),
    manifest_dev_passed=conf_manifest['dev_passed'],
    operator_history_world_union=conf_manifest['operator_history']['world_union_sha256'])

# does the confirmation build REFUSE when an artifact never published its exclusions?
hidden = exp / N.EXPERIMENT_LAYOUT['buffers'].format(seed=9991)
saved_link = hidden.readlink()
hidden.unlink()
(hidden).mkdir()
try:
    N.build_dev_panels(S / 'confirm-should-fail', n=8, namespace=N.NS_CONFIRM,
                       cells={'F-c1-r8': N.DEV_CELLS['F-c1-r8']}, cell_order=['F-c1-r8'],
                       confirmation=True, experiment=exp, seeds=SEEDS, progress=False)
    out['confirmation_world_exclusion']['unpublished_artifact_refused'] = False
except SystemExit as err:
    out['confirmation_world_exclusion']['unpublished_artifact_refused'] = True
    out['confirmation_world_exclusion']['unpublished_message'] = str(err)[:150]
finally:
    shutil.rmtree(S / 'confirm-should-fail', ignore_errors=True)
    hidden.rmdir()
    hidden.symlink_to(saved_link)

# ------------------------------------------------------------------ 3. partial history
probe = {}
try:
    N.build_dev_panels(S / 'ph1', n=8, namespace=N.NS_DEV,
                       cells={'F-c1-r8': N.DEV_CELLS['F-c1-r8']}, cell_order=['F-c1-r8'],
                       operator_history=S / 'ophist', require_full_history=False,
                       progress=False)
    probe['fixture_history_under_dev_namespace'] = 'ACCEPTED'
except SystemExit as err:
    probe['fixture_history_under_dev_namespace'] = str(err)[:130]
shutil.rmtree(S / 'ph1', ignore_errors=True)
try:
    N.build_dev_panels(S / 'ph2', n=8, namespace=N.NS_CONFIRM,
                       cells={'F-c1-r8': N.DEV_CELLS['F-c1-r8']}, cell_order=['F-c1-r8'],
                       operator_history=S / 'ophist', require_full_history=False,
                       confirmation=True, experiment=exp, seeds=SEEDS, progress=False)
    probe['fixture_history_under_confirm_namespace'] = 'ACCEPTED'
except SystemExit as err:
    probe['fixture_history_under_confirm_namespace'] = str(err)[:130]
shutil.rmtree(S / 'ph2', ignore_errors=True)
# an incomplete manifest
part = S / 'ophist-partial'
shutil.rmtree(part, ignore_errors=True)
part.mkdir()
man = json.loads((S / 'ophist' / 'manifest.json').read_text())
man['complete'] = False
man['updates'] = 10
(part / 'manifest.json').write_text(json.dumps(man))
for name in (N.FORBIDDEN_QUESTIONS, N.FORBIDDEN_WORLDS):
    shutil.copy(S / 'ophist' / name, part / name)
try:
    N.load_operator_history(part, require_full=True)
    probe['incomplete_history_refused'] = False
except SystemExit as err:
    probe['incomplete_history_refused'] = True
    probe['incomplete_message'] = str(err)[:150]
try:
    N.load_operator_history(None)
    probe['no_history_refused'] = False
except SystemExit:
    probe['no_history_refused'] = True
shutil.rmtree(part, ignore_errors=True)
probe['world_union_sha256'] = json.loads(
    (S / 'ophist' / 'manifest.json').read_text())['world_union_sha256']
probe['expected'] = '0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a'
probe['matches'] = probe['world_union_sha256'] == probe['expected']
out['operator_history'] = probe

# ------------------------------------------------------------------ 4. ruling 1 gate
audit_doc = json.loads((S / 'bufB' / 'audit.json').read_text())
gate = audit_doc['generation_gate']
mem = N.load_memory(S / 'memB')
g_rec = N.load_buffer(S / 'bufB', 'G')
world_sig = {}
for i, story in enumerate(g_rec['stories']):
    world_sig[i] = CP.world_signature(CP.fact_tuples(story))
pairs, worlds_per, fallback_pairs = defaultdict(set), defaultdict(set), defaultdict(set)
for k, item in enumerate(g_rec['items']):
    src = g_rec['source'][k]
    names = ' '.join(IC.my_ops(list(item['question'])))
    calls = len(item['question']) - 3
    rel = item['question'][-2]
    key = f'c={calls},r={rel}'
    owner = item['owner']
    sig = (world_sig[owner], tuple(int(t) for t in item['question']))
    if src.get('sampled'):
        pairs[key].add(sig)
        worlds_per[key].add(world_sig[owner])
    else:
        fallback_pairs[key].add(sig)
structures = {f'c={c},r={r}': (c, r) for c, r in N.GENERATION_GATE_STRUCTURES}
mine = {k: dict(distinct_question_instances=len(pairs[k]), distinct_worlds=len(worlds_per[k]),
                fallback_instances=len(fallback_pairs[k])) for k in structures}
reported = {k: dict(distinct_question_instances=v.get('distinct_question_instances'),
                    distinct_worlds=v['distinct_worlds'],
                    awake_instances=v['awake_instances'],
                    reading=v.get('reading'), required=v['required'], passed=v['passed'])
            for k, v in gate['structures'].items()}
out['ruling1_generation_gate'] = dict(
    reading=N.GATE_READING, my_recount=mine, reported=reported,
    counts_agree=all(mine[k]['distinct_question_instances']
                     == reported[k]['distinct_question_instances']
                     and mine[k]['distinct_worlds'] == reported[k]['distinct_worlds']
                     for k in structures),
    zero_awake_instances=all(v['awake_instances'] == 0 for v in reported.values()),
    passed=gate['passed'], fallbacks_excluded=True,
    total_fallbacks={a: audit_doc['per_arm'][a]['fallbacks'] for a in audit_doc['arms']})

# ------------------------------------------------------------------ 5. ruling 6 + shortcuts
FEATURES = ('answer_from_ending', 'answer_from_start_entity', 'answer_from_row_count',
            'answer_from_where', 'answer_from_people_visited', 'answer_from_calls',
            'answer_from_distinct_people', 'answer_from_index_mod_2')
shortcut = {}
for cell in N.DEV_CELL_ORDER:
    panel = json.loads((S / 'dev' / f'{cell}.json').read_text())
    units = panel['units']
    ans = [u['a']['answer'] for u in units]
    end = [int(u['a']['question'][-2]) for u in units]
    start = [int(u['a']['question'][1]) for u in units]
    calls = [len(u['a']['question']) - 3 for u in units]
    rows = [len([r for r in u['a']['memory'] if r]) for u in units]
    where = [u['a']['where'] for u in units]
    people = [len({s[0] for s in u['a']['chain']}) for u in units]
    cast = [len({r[0] for i, r in enumerate(u['a']['memory'])
                 if r and i < u['a']['where']}) for u in units]
    parity_idx = [u['index'] % 2 for u in units]
    target_ok = all(u['a']['answer'] == N.target_answer(u['index']) for u in units)
    pair_counts = Counter(zip(ans, end))
    endings = sorted(set(end))
    balanced = (len(endings) == 1
                or (len(pair_counts) == 16 * len(endings)
                    and len(set(pair_counts.values())) == 1))

    def leaks(feature):
        """How much does `feature` narrow the answer?  Reported as the WEIGHTED purity
        sum_f (n_f/N) * max_a P(a|f) together with the number of groups, because a
        feature with 64 distinct values is trivially "pure" and means nothing."""
        groups = defaultdict(list)
        for f, a in zip(feature, ans):
            groups[f].append(a)
        if len(groups) < 2:
            return dict(purity=None, groups=len(groups), informative=False)
        total = sum(len(g) for g in groups.values())
        weighted = sum(Counter(g).most_common(1)[0][1] for g in groups.values()) / total
        base = Counter(ans).most_common(1)[0][1] / total
        return dict(purity=round(weighted, 3), base_rate=round(base, 3),
                    groups=len(groups), largest_group=max(len(g) for g in groups.values()),
                    # a feature is only a usable shortcut if it has few values AND
                    # narrows the answer well beyond the base rate
                    informative=bool(len(groups) <= 16 and weighted > 4 * base))

    def predicts_ending(feature):
        """Weighted purity of the TERMINAL relation given the feature (the ruling-6
        shortcut runs this way round: answer -> which relation ends the chain)."""
        groups = defaultdict(list)
        for f, e in zip(feature, end):
            groups[f].append(e)
        if len(set(end)) < 2:
            return None
        total = sum(len(g) for g in groups.values())
        return round(sum(Counter(g).most_common(1)[0][1] for g in groups.values()) / total, 3)

    shortcut[cell] = dict(
        target_answer_matches_index=target_ok,
        answer_values=len(set(ans)), answer_counts=sorted(Counter(ans).values()),
        endings=endings, answer_ending_balanced=balanced,
        answer_from_ending=leaks(end), ending_from_answer=predicts_ending(ans),
        answer_from_start_entity=leaks(start), answer_from_row_count=leaks(rows),
        answer_from_where=leaks(where), answer_from_people_visited=leaks(people),
        answer_from_calls=leaks(calls),
        answer_from_distinct_people=leaks(cast),
        answer_from_index_mod_2=leaks(parity_idx),   # control: index is not model-visible
        answer_parity_vs_ending={f'parity={a},r={e}': n for (a, e), n in
                                 sorted(Counter((a % 2, e) for a, e in zip(ans, end)).items())}
        if len(endings) > 1 else None,
        answer_halves_vs_ending={f'half={h},r={e}': n for (h, e), n in
                                 sorted(Counter(((a - N.VALUE_MIN) // 8, e)
                                                for a, e in zip(ans, end)).items())}
        if len(endings) > 1 else None,
        manifest_flag=json.loads((S / 'dev' / 'manifest.json').read_text())
        ['cells'][cell]['answer_ending_balanced'])
out['ruling6_stratification'] = dict(
    mixed_ending_cells=[c for c, v in shortcut.items() if len(v['endings']) > 1],
    all_target_answers_match_index=all(v['target_answer_matches_index']
                                       for v in shortcut.values()),
    all_answers_evenly_stratified=all(v['answer_counts'] == [4] * 16
                                      for v in shortcut.values()),
    all_mixed_cells_balanced=all(v['answer_ending_balanced'] for v in shortcut.values()),
    manifest_agrees=all(v['manifest_flag'] == v['answer_ending_balanced']
                        for v in shortcut.values()),
    mixed_ending_balance_table={str(k): v for k, v in N.mixed_ending_balance().items()},
    features=FEATURES,
    informative_features=[(c, k) for c, v in shortcut.items() for k in FEATURES
                          if v[k]['informative']],
    worst_low_cardinality_leak=max(
        (v[k]['purity'] or 0, v[k]['groups'], c, k) for c, v in shortcut.items()
        for k in FEATURES if v[k]['groups'] and v[k]['groups'] <= 16),
    worst_ending_from_answer=max((v['ending_from_answer'] or 0, c)
                                 for c, v in shortcut.items()),
    per_cell=shortcut)

print(json.dumps({k: v for k, v in out.items() if k != 'ruling6_stratification'},
                 indent=1, default=str))
print(json.dumps({k: v for k, v in out['ruling6_stratification'].items() if k != 'per_cell'},
                 indent=1, default=str))
(HERE / 'data-recheck-b.json').write_text(json.dumps(out, indent=1, default=str))
