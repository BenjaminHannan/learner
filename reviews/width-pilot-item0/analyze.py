import sys, json, hashlib, itertools, re
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, '/home/user/wtfar')
L = '/tmp/claude-0/-home-user/7b4cc9f0-8b9c-5e78-99b7-c110382faf97/scratchpad/far-data/learn/'
from domain import panel as P
from domain.far import learn_probe as LP, sheet_probe as SP
from domain.tools import sheet as sheet_tool
from domain import mode
ld = lambda p: [json.loads(l) for l in open(p) if l.strip()]
tr, ev = ld(L + 'train-rows-l5.jsonl'), ld(L + 'eval-rows-l5.jsonl')
print('train', len(tr), 'eval', len(ev))
print('\n== 3a counts')
for name, rows in (('train', tr), ('eval', ev)):
    print(name, 'by split', dict(Counter(r['split'] for r in rows)))
    c = Counter((r['split'], r.get('layout')) for r in rows)
    for k, v in sorted(c.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))): print('  ', k, v)
    ck = Counter((r['split'], r['kind']) for r in rows)
    for s in dict.fromkeys(r['split'] for r in rows):
        print('   kinds in', s, {k[1]: v for k, v in ck.items() if k[0] == s})
print('ids unique', len({r['id'] for r in tr + ev}) == len(tr + ev))
ho = [r for r in ev if r['split'] == 'HO']
print('HO n', len(ho), 'layouts', Counter(r['layout'] for r in ho), 'kinds', Counter(r['kind'] for r in ho))
split = json.load(open(L + '../learn/pair-split-l3.json')) if False else None
train_pairs, held_pairs = LP.pair_split()
tp = set(map(frozenset, train_pairs)); hp = set(map(frozenset, held_pairs))
for cell in ('S5', 'S', 'HP', 'HO', 'HPO'):
    rs = [r for r in ev if r['split'] == cell]
    npair = Counter('train' if frozenset((r['kind'], r['partner'])) in tp else 'held' if frozenset((r['kind'], r['partner'])) in hp else '?' for r in rs)
    ops = Counter(r['layout'] for r in rs)
    print(f'  eval {cell}: n {len(rs)} layouts {dict(ops)} pairs {dict(npair)} unique(kind,partner) ordered {len({(r["kind"], r["partner"]) for r in rs})} unique unordered {len({frozenset((r["kind"], r["partner"])) for r in rs})}')

print('\n== 3b format: steps from the sheet tool (what make_rows hands to mode.make_row)')
cons = json.load(open(mode.CONST_PATH))
print('cons max_calls', cons['max_calls'], 'batch', cons['batch'], 'lr', cons['lr'])
def pre(r):
    res = sheet_tool.evaluate(r['prompt']); calls = [tuple(s) for s in res['steps']]; ans = res['value']
    if not ans or len(ans) > mode.MAX_ANS: return 'answer_len', calls, ans
    if not calls: return 'zero_steps', calls, ans
    if len(calls) > cons['max_calls']: return 'caps_calls', calls, ans
    if any(c[3] == '?' or c[3].startswith('-') or c[1].startswith('-') or c[2].startswith('-') for c in calls): return 'calc_?_or_negative', calls, ans
    if calls[-1][3] != ans: return 'final_mismatch', calls, ans
    if any(mode.step_text(*c) is None for c in calls): return 'no_row_form', calls, ans
    return None, calls, ans
fam = lambda r: r['split'] + ('|' + r['layout'] if r.get('layout') else '')
drops = defaultdict(Counter); nst = defaultdict(Counter); same = Counter()
for r in tr + ev:
    why, calls, ans = pre(r)
    k = ('train ' if r in tr else 'eval ') if False else ''
for name, rows in (('train', tr), ('eval', ev)):
    drops = defaultdict(Counter); nst = defaultdict(Counter); mism = 0; ansfinal = 0
    for r in rows:
        why, calls, ans = pre(r)
        drops[fam(r)][why or 'ok'] += 1
        nst[fam(r)][len(calls)] += 1
        mism += (ans != r['answer']) + (len(calls) != r['n_steps'])
        ansfinal += (calls[-1][3] == r['answer']) if calls else 0
    print(name, 'row answer/n_steps disagree with tool re-eval:', mism, '; last call result == answer in', ansfinal, 'of', len(rows))
    for f in sorted(drops): print('  ', f, 'pre-model make_row filters:', dict(drops[f]), '| n calls:', dict(sorted(nst[f].items())))
ex = [r for r in tr if r['split'] == 'F4-two'][0], [r for r in tr if r['split'] == 'F0-near'][0]
for r in ex:
    why, calls, ans = pre(r)
    print('example', r['split'], r['prompt'], '->', r['answer']); print('   steps:', [mode.step_text(*c) for c in calls])
print('step ops used (train):', Counter(c[0] for r in tr for c in pre(r)[1]))

print('\n== 3c dose')
usable = [r for r in tr if pre(r)[0] is None]
print('train rows', len(tr), 'pre-model usable', len(usable), '(model-dependent verify() drop not testable here)')
for f_name, sel in (('joined F4-two', lambda r: r['split'] == 'F4-two'), ('F0-near', lambda r: r['split'] == 'F0-near')):
    for lab, rows in (('all', [r for r in tr if sel(r)]), ('pre-usable', [r for r in usable if sel(r)])):
        up = len({r['prompt'] for r in rows})
        sk = len({P.skeleton(r['prompt'].split(';', 1)[1]) for r in rows})
        s = f'  {f_name} [{lab}]: rows {len(rows)} unique prompts {up} unique formula skeletons {sk}'
        if f_name.startswith('joined'):
            s += f' | unique ordered (kind,partner)x layout {len({(r["kind"], r["partner"], r["layout"]) for r in rows})} unique unordered pair x layout {len({(frozenset((r["kind"], r["partner"])), r["layout"]) for r in rows})} unique ordered (kind,partner) {len({(r["kind"], r["partner"]) for r in rows})}'
        else:
            s += f' | unique kinds {len({r["kind"] for r in rows})}'
        print(s)
print('  possible: 14 unordered pairs x 5 layouts = 70; 28 ordered (kind,partner) x 5 = 140')
print('  joined rows per layout (usable):', dict(Counter(r['layout'] for r in usable if r['split'] == 'F4-two')))
# exact visit counts under the trainer's batch_order with the default run seed
for rows, tag in ((tr, 'all 12000'), (usable, 'pre-usable only')):
    n = len(rows); visits = np.zeros(n, int)
    for ni in LP.batch_order(n, 64, 4000, LP.SEED):
        for i in ni: visits[i] += 1
    j = np.array([r['split'] == 'F4-two' for r in rows])
    comb = defaultdict(int)
    for r, v in zip(rows, visits):
        if r['split'] == 'F4-two': comb[(r['kind'], r['partner'], r['layout'])] += v
    print(f'  batch_order(seed {LP.SEED}) over {tag} rows: total slots {visits.sum()} = epochs {visits.sum()/n:.3f} over rows; per-row visits min/max {visits.min()}/{visits.max()}; joined slots {visits[j].sum()} ({visits[j].sum()/visits.sum():.3f}); joined slots per unique joined prompt {visits[j].sum()/j.sum():.2f}; per observed ordered combo x layout: mean {np.mean(list(comb.values())):.1f} (n combos {len(comb)}, min {min(comb.values())}, max {max(comb.values())})')
print('  nominal: 4000x64 = 256000 slots; /12000 rows = 21.33 passes; joined 6000 rows -> 128000 slots')
for n_c in (140, 70):
    print(f'  128000 joined slots / {n_c} combos = {128000/n_c:.0f} slots per combo = {128000/n_c/ (6000/n_c):.2f} passes over each combo`s rows (same 21.33 passes; each combo has ~{6000/n_c:.1f} unique rows)')

print('\n== 3d HO sha256 (canonical json.dumps(r)+newline, file order)')
b = ''.join(json.dumps(r) + '\n' for r in ho).encode()
print('HO cell sha256', hashlib.sha256(b).hexdigest(), 'bytes', len(b))
lines = [l for l in open(L + 'eval-rows-l5.jsonl') if '"split": "HO"' in l]
print('equals raw file lines of HO:', ''.join(lines).encode() == b, 'HO contiguous in file:', [i for i, r in enumerate(ev) if r['split'] == 'HO'][0], '..', [i for i, r in enumerate(ev) if r['split'] == 'HO'][-1])
for cell in ('S5', 'S', 'HP', 'HPO'):
    rs = [r for r in ev if r['split'] == cell]
    print(' ', cell, hashlib.sha256(''.join(json.dumps(r) + '\n' for r in rs).encode()).hexdigest()[:16])

print('\n== 3e overlap')
trp = {r['prompt'] for r in tr}
for cell in ('S5', 'S', 'HP', 'HO', 'HPO'):
    rs = [r for r in ev if r['split'] == cell]
    print(f'  eval {cell} prompts in train prompts: {sum(r["prompt"] in trp for r in rs)} of {len(rs)}')
print('  eval prompts duplicated within eval:', len(ev) - len({r["prompt"] for r in ev}))
trlay = Counter(r['layout'] for r in tr if r['split'] == 'F4-two')
print('  train layouts', dict(trlay), '; HO layout (K)*(J) in train layouts:', '(K)*(J)' in trlay)
print('  train prompts containing ")*(":', sum(')*(' in p for p in trp), '; HO prompts containing ")*(":', sum(')*(' in r['prompt'] for r in ho), 'of', len(ho))
body = lambda p: p.partition(';')[2].strip().lstrip('=')
trsk = {P.skeleton(body(r['prompt'])) for r in tr}
print('  HO formula skeletons (digits->d, A/B->c) also in training:', sum(P.skeleton(body(r['prompt'])) in trsk for r in ho), 'of', len(ho), '; unique HO skeletons', len({P.skeleton(body(r['prompt'])) for r in ho}))
print('  HO ordered (kind,partner) seen in training joined rows:', sum((r['kind'], r['partner']) in {(x['kind'], x['partner']) for x in tr if x['split']=='F4-two'} for r in ho), 'of', len(ho))
for r in ho[:3]: print('   HO ex:', r['prompt'], '->', r['answer'], r['n_steps'], 'steps')
for lay in LP.L5_LAYOUTS:
    r = [x for x in tr if x.get('layout') == lay][0]; print('   train', lay, ':', r['prompt'])
# HO formula minus brackets vs. K*J
bare = lambda p: body(p).replace('(', '').replace(')', '')
