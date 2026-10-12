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
B3G2 = 'B3G2'
B3 = 'B3'                       # B3 group 1 (B3-GROUP1-BUILD): loaded and reported apart (b3_report); the B2 marks above never read it
RUNG_RUNGS = ['3M', '10M', '30M', '100M']
SEEDS = [400, 401, 402, 403, 404, 405]
LOCAL = re.compile(r'^8a-(3M|10M|30M|100M)-s(\d+)$')
VAST = re.compile(r'^8a-(3M|10M|30M|100M)-s(\d+)-(B2|PT|LLM|PUB|B3|B3G2)$')


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
            if (base in ARMS or base in (B3, B3G2)) and LOCAL.match(parent):
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
    rep['b3'] = b3_report(runs, seeds)
    rep['b3g2'] = b3_report(runs, seeds, B3G2)
    five = [m['ok'] for m in marks]
    verdict = 'PASS' if five == [True] * len(five) else ('FAIL' if False in five else 'incomplete')
    return dict(verdict=verdict, marks=marks, proved_wrong=wrong, stop_rules=stop, reported=rep, seeds=list(seeds))


def b3_report(runs, seeds, arm=B3):
    """B3's items (report-only; nothing here is a mark): per rung, over the seeds that have a B3 run: pooled-5 exact, rounds used at the model's own stop
    (h1 block), the rounds at which calls happen (histogram), calls per row, rows whose call a full tape refused, and exact match per input-length bucket
    (<= 280, 281-700, 701-1,300, 1,301-2,000 letters) on every dev split that has rows there. Counts are summed over seeds."""
    out = {}
    for rung in RUNG_RUNGS:
        rs = [(s, runs[(rung, arm, s)]) for s in seeds if (rung, arm, s) in runs]
        if not rs:
            continue
        agg = dict(seeds=[s for s, _ in rs], pooled5=A.stats({s: A.P5(r, None) for s, r in rs}), rounds_mean={s: A.g(r, 'extra', 'h1', 'pooled5', 'mean') for s, r in rs},
                   tape_full_rows=0, call_rounds={}, calls_per_row={}, by_length={}, plan=[])
        for s, r in rs:
            b = A.g(r, 'extra', 'b3') or {}
            agg['plan'].append(b.get('plan'))
            for sp, d in (b.get('splits') or {}).items():
                agg['tape_full_rows'] += d.get('tape_full_rows', 0)
                for key in ('call_rounds', 'calls_per_row'):
                    for k, v in d.get(key, {}).items():
                        agg[key][k] = agg[key].get(k, 0) + v
                for bk, v in d.get('by_length', {}).items():
                    e = agg['by_length'].setdefault(sp, {}).setdefault(bk, [0, 0.0])
                    e[0] += v['n']
                    e[1] += v['n'] * v['exact'] / 100
        if arm == B3G2:     # group 2's sealed items (models/b3g2.py g2_evals and Tool's / H1's evals), per seed: B3G2-1 to B3G2-6
            agg['g2'] = {s: dict(
                pooled5=A.P5(r, None), chain5=A.g(r, 'chain5', 'intact', 'exact'), leak_loops0=A.g(r, 'chain5', 'loops:0', 'exact'), donor=A.g(r, 'lesions', 'donor', 'in_dist'),
                loops32=A.g(r, 'chain5', 'loops:32', 'exact'), tool_off_program=A.g(r, 'extra', 'noexec', 'program_families'), tool_off_n=A.g(r, 'extra', 'noexec', 'n'),
                inverse=A.g(r, 'extra', 'g2', 'inverse'), dev_rows=A.g(r, 'extra', 'g2', 'dev_rows'), agreement=A.g(r, 'extra', 'g2', 'agreement'),
                writer=A.g(r, 'extra', 'g2', 'writer'), train_counts=A.g(r, 'extra', 'g2', 'train_counts'), call_acc=A.g(r, 'extra', 'op_acc'), call_text=A.g(r, 'extra', 'call_text'),
                write_copy=A.g(r, 'extra', 'write_copy_u'), opswap=A.g(r, 'extra', 'opswap'), cap_hits=r.get('cap_hits'), h1_chain5=A.g(r, 'extra', 'h1', 'chain5'),
                steps_unparsed=A.g(r, 'cap_hits', 'steps_unparsed'), no_trace=A.g(r, 'cap_hits', 'no_trace'), writer_over=A.g(r, 'cap_hits', 'writer_over'),
                tape_entry_over=A.g(r, 'cap_hits', 'tape_entry_over')) for s, r in rs}
        agg['by_length'] = {sp: {bk: dict(n=n_, exact=100 * c / n_) for bk, (n_, c) in sorted(d.items())} for sp, d in agg['by_length'].items()}
        out[rung] = agg
    return out


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


def show_b3(res):
    for rung, d in (res['reported'].get('b3g2') or {}).items():
        print(f"  B3G2 {rung}: pooled-5 {fmt(d['pooled5']['mean'])}  per seed: " + json.dumps({s: {k: v.get(k) for k in ('chain5', 'leak_loops0', 'tool_off_program', 'steps_unparsed', 'no_trace', 'writer_over')} for s, v in d['g2'].items()}, default=str))
    for rung, d in (res['reported'].get('b3') or {}).items():
        print(f"  B3 {rung}: pooled-5 {fmt(d['pooled5']['mean'])}  tape-full rows {d['tape_full_rows']}  calls/row {d['calls_per_row']}  call rounds {d['call_rounds']}")
        for sp, bs in d['by_length'].items():
            print(f"    {sp}: " + '  '.join(f"{bk} letters {v['exact']:.1f} (n {v['n']})" for bk, v in bs.items()))


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
    show_b3(res)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1, default=str)
    return res


if __name__ == '__main__':
    main()
