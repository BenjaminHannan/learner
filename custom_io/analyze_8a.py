"""Stage 8a marks (whole-model-roadmap/8A-SPEC-2026-10-07.md section 7 plus addenda A2, E), computed exactly as written.

  python -m custom_io.analyze_8a --results DIR [DIR...] [--seeds 400,401,402,403,404,405] [--out FILE.json]

Reads every RESULT.json under the dirs. Two layouts are understood:
  PC (local_runner):  .../8a-<rung>-s<seed>/<ARM>/RESULT.json        ARM = B2 | PT | LLM | PUB
  Vast fallback:      .../8a-<rung>-s<seed>-<ARM>/RESULT.json
Only status 'ok' runs count; anything missing gives 'n/a' (never a crash). Metric: pooled-5 (micro exact over in_dist+answer+frame+vocab+variant,
analyze.P5). Differences are per-seed paired over the seeds both runs have; mean +- t x sd / sqrt(n) (analyze.stats).

Marks (pass needs all of them):
  1  B2 grows: pooled-5 gain >= +3.0 from 3M to 10M and from 10M to 30M, each with its 95% CI above 0
  2  its lead holds: mean (B2 - PT) at 30M >= mean (B2 - PT) at 3M - 1.0
  3  still ahead at 30M: B2 - PT >= +3.0 on at least 5 of 6 seeds
  4  starts good: 3M B2 mean >= 72.0 (else stop before 10M)
  5  ends good: 30M B2 - public model >= +2.0 mean, CI lower bound above 0 (public model = the PUB arm, no calculator)
Guard: B2 chain-5 >= 99 at every rung (read as the rung's mean over seeds; any seed under 99 is listed in the report).
Proved wrong: 3M-to-30M gain < +2.0; 30M lead < half the 3M lead (as written, 0.5 x the 3M lead); good enough: B2 30M mean below the public model's.
Stop rule (stage plan): 10M mean minus 3M mean below 0 -> no 30M.
Reported, not gated: leak (loops:0 in_dist) and donor drop per rung (+ the 30M-minus-3M leak flag at > 5 points), LLM arm and B2 - LLM, public model with calculator,
every split per rung, params, caps and rows touched, hours and cost.
"""
import argparse, json, os, re
from custom_io import analyze as A

RUNGS = ['3M', '10M', '30M']
ARMS = ['B2', 'PT', 'LLM', 'PUB']
SEEDS = [400, 401, 402, 403, 404, 405]
LOCAL = re.compile(r'^8a-(3M|10M|30M)-s(\d+)$')
VAST = re.compile(r'^8a-(3M|10M|30M)-s(\d+)-(B2|PT|LLM|PUB)$')


def load(dirs):
    """-> runs {(rung, arm, seed): RESULT dict}, boxes {(rung, seed): box.json dict}, skipped [(path, why)]."""
    runs, boxes, skipped = {}, {}, []
    for d in dirs:
        for root, _, fs in os.walk(d):
            base, parent = os.path.basename(root), os.path.basename(os.path.dirname(root))
            if 'box.json' in fs and LOCAL.match(base):
                m = LOCAL.match(base)
                boxes[(m.group(1), int(m.group(2)))] = json.load(open(os.path.join(root, 'box.json')))
            if 'RESULT.json' not in fs:
                continue
            key = None
            if base in ARMS and LOCAL.match(parent):
                m = LOCAL.match(parent)
                key = (m.group(1), base, int(m.group(2)))
            elif VAST.match(base):
                m = VAST.match(base)
                key = (m.group(1), m.group(3), int(m.group(2)))
            if key is None:
                continue
            try:
                r = json.load(open(os.path.join(root, 'RESULT.json')))
            except Exception as e:
                skipped.append((root, f'unreadable: {e}'))
                continue
            if r.get('status') != 'ok':
                skipped.append((root, f"status {r.get('status')}"))
                continue
            runs[key] = r
    return runs, boxes, skipped


def per_seed(runs, rung, arm, fn, seeds, les=None):
    return {s: (fn(runs[(rung, arm, s)], les) if (rung, arm, s) in runs else None) for s in seeds}


def diff(a, b):
    """{seed: a - b} where both exist."""
    return {s: A.sub(a.get(s), b.get(s)) for s in a}


def mean(d):
    v = [x for x in d.values() if x is not None]
    return sum(v) / len(v) if v else None


def mk(i, desc, value, ok, **kw):
    return dict(id=i, desc=desc, value=value, ok=ok, **kw)


def ge(v, thr):
    return 'n/a' if v is None else v >= thr


def analyze(runs, boxes=None, seeds=SEEDS):
    boxes = boxes or {}
    P5, C5, IND = A.P5, A.C5, A.SPL('in_dist')
    p5 = {(r, a): per_seed(runs, r, a, P5, seeds) for r in RUNGS for a in ARMS}
    st = {k: A.stats(v) for k, v in p5.items()}
    marks, wrong = [], []

    # 1: B2 grows
    g1, g2 = A.stats(diff(p5[('10M', 'B2')], p5[('3M', 'B2')])), A.stats(diff(p5[('30M', 'B2')], p5[('10M', 'B2')]))
    def grows(s):
        return 'n/a' if s['n'] < 2 or s['ci'] is None else (s['mean'] >= 3.0 and s['ci'][0] > 0)
    ok1 = A.allof([grows(g1), grows(g2)])
    marks.append(mk(1, 'B2 grows: pooled-5 gain >= +3.0 (CI above 0) 3M->10M and 10M->30M', dict(gain_3_10=g1, gain_10_30=g2), ok1))
    # 2, 3: the lead over PT
    lead = {r: diff(p5[(r, 'B2')], p5[(r, 'PT')]) for r in RUNGS}
    ls = {r: A.stats(lead[r]) for r in RUNGS}
    l3, l30 = ls['3M']['mean'], ls['30M']['mean']
    marks.append(mk(2, 'lead holds: mean (B2 - PT) at 30M >= that at 3M - 1.0', dict(lead_3M=l3, lead_30M=l30), 'n/a' if None in (l3, l30) else l30 >= l3 - 1.0))
    n30 = [v for v in lead['30M'].values() if v is not None]
    marks.append(mk(3, 'still ahead at 30M: B2 - PT >= +3.0 on >= 5 of 6 seeds', dict(seeds_ok=sum(v >= 3.0 for v in n30), seeds=len(n30), per_seed=lead['30M']),
                    'n/a' if len(n30) < len(seeds) else sum(v >= 3.0 for v in n30) >= 5))
    # 4, 5: good enough
    m3 = st[('3M', 'B2')]['mean']
    marks.append(mk(4, 'starts good: 3M B2 pooled-5 mean >= 72.0', m3, ge(m3, 72.0)))
    pub = diff(p5[('30M', 'B2')], p5[('30M', 'PUB')])
    ps = A.stats(pub)
    marks.append(mk(5, 'ends good: 30M B2 - public model >= +2.0, CI lower bound above 0', ps,
                    'n/a' if ps['n'] < 2 or ps['ci'] is None else (ps['mean'] >= 2.0 and ps['ci'][0] > 0)))
    # guard
    c5 = {r: per_seed(runs, r, 'B2', C5, seeds) for r in RUNGS}
    c5m = {r: mean(c5[r]) for r in RUNGS}
    guard = A.allof([ge(c5m[r], 99.0) for r in RUNGS])
    marks.append(mk('guard', "B2 chain-5 >= 99 at every rung (rung mean; seeds under 99 listed)", dict(mean=c5m, seeds_under_99={r: [s for s, v in c5[r].items() if v is not None and v < 99] for r in RUNGS}), guard))

    # proved wrong
    tot = A.stats(diff(p5[('30M', 'B2')], p5[('3M', 'B2')]))
    if tot['mean'] is not None:
        wrong.append(dict(line='B2 3M-to-30M gain under +2.0 (flat)', value=tot['mean'], hit=tot['mean'] < 2.0))
    if None not in (l3, l30):
        wrong.append(dict(line='30M lead over PT under half the 3M lead', value=dict(lead_3M=l3, lead_30M=l30), hit=l30 < 0.5 * l3))
    m30, mp = st[('30M', 'B2')]['mean'], st[('30M', 'PUB')]['mean']
    if None not in (m30, mp):
        wrong.append(dict(line='good enough: B2 30M mean below the public model\'s', value=dict(b2=m30, public=mp), hit=m30 < mp))
    d10 = A.stats(diff(p5[('10M', 'B2')], p5[('3M', 'B2')]))['mean']
    stop = dict(stop_before_10M=None if m3 is None else m3 < 72.0, no_30M=None if d10 is None else d10 < 0)

    # reported
    rep = dict(splits={r: {a: {s: A.stats(per_seed(runs, r, a, A.SPL(s), seeds))['mean'] for s in A.POOL} for a in ARMS} for r in RUNGS},
               leak_loops0={r: A.stats(per_seed(runs, r, 'B2', IND, seeds, 'loops:0'))['mean'] for r in RUNGS},
               donor_drop={r: A.stats({s: (A.sub(IND(runs[(r, 'B2', s)]), A.g(runs[(r, 'B2', s)], 'lesions', 'donor', 'in_dist', 'exact')) if (r, 'B2', s) in runs else None) for s in seeds})['mean'] for r in RUNGS},
               pooled5={f'{r}/{a}': st[(r, a)] for r in RUNGS for a in ARMS},
               b2_minus_llm={r: A.stats(diff(p5[(r, 'B2')], p5[(r, 'LLM')])) for r in RUNGS},
               b2_minus_pt={r: ls[r] for r in RUNGS},
               public_with_calculator=A.stats(per_seed(runs, '30M', 'PUB', A.P5, seeds, 'calc')),
               b2_minus_public_with_calculator=A.stats({s: A.sub(p5[('30M', 'B2')].get(s), A.P5(runs[('30M', 'PUB', s)], 'calc')) if ('30M', 'PUB', s) in runs else None for s in seeds}),
               params={f'{r}/{a}': A.g(runs.get((r, a, seeds[0])) or {}, 'n_params') for r in RUNGS for a in ARMS},
               hours={f'{r}': (round(sum(b.get('wall_s', 0) for k, b in boxes.items() if k[0] == r) / 3600, 2)) for r in RUNGS},
               cost_usd={f'{r}': (round(sum(b.get('cost_usd', 0) or 0 for k, b in boxes.items() if k[0] == r), 2)) for r in RUNGS})
    l3k, l30k = rep['leak_loops0']['3M'], rep['leak_loops0']['30M']
    rep['leak_flag_30M_over_3M_by_5'] = None if None in (l3k, l30k) else l30k - l3k > 5
    caps = {r: A.g(next((b for k, b in boxes.items() if k[0] == r), {}), 'caps') for r in RUNGS}
    rep['caps'] = caps
    five = [m['ok'] for m in marks]
    verdict = 'PASS' if five == [True] * len(five) else ('FAIL' if False in five else 'incomplete')
    return dict(verdict=verdict, marks=marks, proved_wrong=wrong, stop_rules=stop, reported=rep, seeds=list(seeds))


def fmt(v, w=6, p=2):
    return ' ' * (w - 3) + 'n/a' if v is None else f'{v:{w}.{p}f}'


def show(res):
    print('8a verdict:', res['verdict'])
    for m in res['marks']:
        print(f"  mark {m['id']}: {m['ok']}  {m['desc']}")
    for w in res['proved_wrong']:
        print(f"  PROVED WRONG? {w['hit']}  {w['line']}  {json.dumps(w['value'], default=str)}")
    print('  stop rules:', res['stop_rules'])
    r = res['reported']
    for rung in RUNGS:
        print(f"  {rung}: " + ' '.join(f"{a} {fmt(r['pooled5'][f'{rung}/{a}']['mean'])}" for a in ARMS) + f"  leak {fmt(r['leak_loops0'][rung])}  donor drop {fmt(r['donor_drop'][rung])}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--seeds', default=','.join(map(str, SEEDS)))
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    runs, boxes, skipped = load(a.results)
    res = analyze(runs, boxes, [int(x) for x in a.seeds.split(',')])
    res['skipped'] = skipped
    show(res)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1, default=str)
    return res


if __name__ == '__main__':
    main()
