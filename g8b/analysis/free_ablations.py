"""8b diagnosis from the saved 8a results (no new runs). Reads results/8a-ladder and results/8a-probe of claude/project-thread-yha868.
  python g8b/analysis/free_ablations.py RESULTS_DIR > g8b/analysis/free_ablations.txt
Prints: (1) training loss by step per arm and rung (6-seed means; B2 split into GEN and mode+word), (2) 3M -> 10M pooled-5 gain on the calculator
families (parser coverage >= 50%) vs the rest, (3) per-family pooled-5 of B2 under every saved lesion (rounds, state, copy, word content, executor)."""
import json, statistics as st, sys
R = sys.argv[1]
L = R + '/8a-ladder'
SPL = ['in_dist', 'answer', 'frame', 'vocab', 'variant']


def curve(p):
    return {e['step']: e for e in (json.loads(x) for x in open(p) if x.startswith('{')) if e.get('event') == 'train'}


def losses(arm, rung, base=L, seeds=range(400, 406)):
    cs = []
    for s in seeds:
        try:
            cs.append(curve(f'{base}/8a-{rung}-s{s}-{arm}/stdout.events.txt'))
        except OSError:
            pass
    out = {}
    for step in [1000, 2000, 4000, 8000, 12000, 16000, 20000, 24000]:
        w = [c[k] for c in cs for k in range(step - 1500, step + 1, 500) if k in c]     # last 4 logged batches up to `step`
        out[step] = (round(st.mean(x['loss'] for x in w), 3), round(st.mean(x.get('gen', 0) for x in w), 3), round(st.mean(x.get('mode', 0) + x.get('word', 0) for x in w), 3))
    return len(cs), out


def pooled(sec):
    acc = {}
    for sp in SPL:
        for f, v in sec[sp]['by_family'].items():
            if 'correct' not in v:
                return None
            a = acc.setdefault(f, [0, 0]); a[0] += v['correct']; a[1] += v['n']
    return acc


print('# 1. training loss (total, GEN part, mode+word part), mean of the last 4 logged batches up to each step')
for arm, rung in [('B2', '3M'), ('B2', '10M'), ('PT', '3M'), ('PT', '10M'), ('LLM', '3M'), ('LLM', '10M')]:
    print(arm, rung, *losses(arm, rung))
for p in ['R', 'W']:
    print('probe', p, '10M', *losses('B2', '10M', base=f'{R}/8a-probe/{p}', seeds=[400, 401]))

cov = json.load(open(f'{L}/8a-10M-s400-B2/RESULT.json'))['extra']['coverage']['by_family']
prog = {f for f, c in cov.items() if c['prog'] >= 50}
print('\n# 2. 3M -> 10M pooled-5 gain, calculator families vs the rest (seeds with all arms: 400 401 402 403 405)')
print('calculator families:', sorted(prog))
for arm in ['B2', 'PT', 'LLM']:
    for grp in ['prog', 'nonprog']:
        lv, gains = [], []
        for s in [400, 401, 402, 403, 405]:
            v = {}
            for rung in ['3M', '10M']:
                acc = pooled(json.load(open(f'{L}/8a-{rung}-s{s}-{arm}/RESULT.json'))['final_eval'])
                c = sum(x[0] for f, x in acc.items() if (f in prog) == (grp == 'prog'))
                n = sum(x[1] for f, x in acc.items() if (f in prog) == (grp == 'prog'))
                v[rung] = 100 * c / n
            lv.append(v['3M']); gains.append(v['10M'] - v['3M'])
        print(f'{arm:4} {grp:8} 3M level {st.mean(lv):5.1f}  gain {st.mean(gains):+.2f} (sd {st.stdev(gains):.2f})')

print('\n# 3. B2 pooled-5 per family under each saved lesion, 6-seed mean')
cols = ['intact', 'loops:0', 'loops:1', 'loops:2', 'loops:24', 'shuffle_state', 'zero_state', 'nocopy', 'nowordc', 'noexec']
for rung in ['3M', '10M']:
    res = {}
    for s in range(400, 406):
        X = json.load(open(f'{L}/8a-{rung}-s{s}-B2/RESULT.json'))
        secs = dict(intact=X['final_eval'], **X['lesions'])
        for name, sec in secs.items():
            p = pooled(sec)
            if p:
                for f, (c, n) in p.items():
                    res.setdefault(name, {}).setdefault(f, []).append(100 * c / n)
    T = {k: {f: st.mean(v) for f, v in d.items()} for k, d in res.items()}
    print('==', rung, 'mode coverage NUM/WORD/GEN %;', ' '.join(f'{c[:8]:>8}' for c in cols))
    for grp, fs in [('calculator', sorted(prog)), ('other', sorted(set(cov) - prog))]:
        print('--', grp)
        for f in fs:
            c = cov[f]
            print(f"{f:20} {c['NUM']:3.0f}/{c['WORD']:3.0f}/{c['GEN']:3.0f}  " + ' '.join(f'{T[k].get(f, float("nan")):8.1f}' for k in cols))
