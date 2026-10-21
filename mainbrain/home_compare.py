"""Home self-check against DEV harm: verdicts and summary from saved files (no model needed).

  python -m mainbrain.home_compare --spec SPEC.json --out OUT.json

SPEC: list of dict(name, dev_summary=PATH or [PATHs] (harm_nights outputs; later files override earlier nights), home=PATH (home_check OUT on home-H12.jsonl), rows=PATH (home-H12.jsonl)).
Home verdicts use domain.harm.harm_measure(parent_hits, night_hits, rows, 5.0, 1.5) on the H1 rows, the H2 rows and all rows.
A night is bad when in_dist drop > 1.5 or any family fires. Unique nights skip a night whose home result is reused from an earlier night of the same run.
"""
import argparse
import json
import math

from domain import harm

SETS = ('H1', 'H2', 'H12')


def pearson(x, y):
    n = len(x)
    if n < 2:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def is_bad(drop, fired):
    return drop > 1.5 or bool(fired)


def load_dev(paths):
    if isinstance(paths, str):
        paths = [paths]
    nights = {}
    for p in paths:
        nights.update(json.load(open(p))['nights'])
    return nights


def home_verdicts(parent_hits, night_hits, rows):
    """-> {set name: dict(drop, fired, bad, top)} for H1, H2 and H12; hit strings of '0'/'1' aligned with rows."""
    out = {}
    for name in SETS:
        ix = [i for i, r in enumerate(rows) if name == 'H12' or r.get('half') == name]
        sub = [rows[i] for i in ix]
        hm = harm.harm_measure([int(parent_hits[i]) for i in ix], [int(night_hits[i]) for i in ix], sub, 5.0, 1.5)
        fam = hm['families']
        top = sorted(fam, key=lambda f: -fam[f]['drop'])[:5]
        out[name] = dict(drop=hm['in_dist_drop'], fired=hm['fired'], bad=is_bad(hm['in_dist_drop'], hm['fired']),
                         top={f: {x: fam[f][x] for x in ('a', 'b', 'drop')} for f in top})
    return out


def run_summary(dev, home, rows):
    ph = home['parent']['hits']
    ks = sorted((k for k in dev if k in home['nights']), key=int)
    nights = {}
    for k in ks:
        d, h = dev[k], home['nights'][k]
        v = home_verdicts(ph, h['hits'], rows)
        nights[k] = dict(dev=dict(drop=d['in_dist_drop'], fired=sorted(d['fired']), bad=is_bad(d['in_dist_drop'], d['fired'])),
                         reused_from=h.get('reused_from'), **v)
    return nights


def first_bad_night(nights, key):
    for k in sorted(nights, key=int):
        if nights[k][key]['bad']:
            return int(k)
    return None


def fired_union(nights, key):
    return sorted({f for v in nights.values() for f in v[key]['fired']})


def unique_nights(nights):
    return [k for k in sorted(nights, key=int) if not isinstance(nights[k]['reused_from'], int)]


def overall(runs):
    out = {}
    failing = [r for r in runs.values() if r['dev_first_bad'] is not None]
    for s in SETS:
        caught = sum(1 for r in failing if r[s + '_first_bad'] is not None and r[s + '_first_bad'] <= r['dev_first_bad'] + 1)
        pairs = [(n, f) for n, r in runs.items() for f in r['dev_fired']]
        match = sum(1 for n, f in pairs if f in runs[n][s + '_fired'])
        dd, hd, good, false_alarm = [], [], 0, 0
        for r in runs.values():
            for k in unique_nights(r['nights']):
                v = r['nights'][k]
                dd.append(v['dev']['drop'])
                hd.append(v[s]['drop'])
                if not v['dev']['bad']:
                    good += 1
                    false_alarm += v[s]['bad']
        md = sum(dd) / len(dd) if dd else None
        out[s] = dict(caught=caught, dev_failing_runs=len(failing), pairs=len(pairs), pairs_matched=match,
                      pair_match_rate=match / len(pairs) if pairs else None, dev_good_nights=good, false_alarms=false_alarm,
                      false_alarm_rate=false_alarm / good if good else None, pearson_r=pearson(dd, hd), unique_nights=len(dd),
                      mean_home_drop=sum(hd) / len(hd) if hd else None, mean_dev_drop=md,
                      mean_ratio=(sum(hd) / len(hd)) / md if dd and md else None)
    h1d, h2d, agree, n = [], [], 0, 0
    for r in runs.values():
        for k in unique_nights(r['nights']):
            v = r['nights'][k]
            h1d.append(v['H1']['drop'])
            h2d.append(v['H2']['drop'])
            agree += v['H1']['bad'] == v['H2']['bad']
            n += 1
    out['H1_vs_H2'] = dict(pearson_r=pearson(h1d, h2d), verdict_agreement=agree / n if n else None, unique_nights=n)
    return out


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--spec', required=True)
    a.add_argument('--out', required=True)
    a = a.parse_args(argv)
    spec = json.load(open(a.spec))
    runs = {}
    for s in spec:
        rows = [json.loads(l) for l in open(s['rows'])]
        home = json.load(open(s['home']))
        assert home['ids'] == [r['id'] for r in rows], f"{s['name']}: home ids differ from rows"
        nights = run_summary(load_dev(s['dev_summary']), home, rows)
        r = dict(nights=nights, dev_first_bad=first_bad_night(nights, 'dev'), dev_fired=fired_union(nights, 'dev'))
        for k in SETS:
            r[k + '_first_bad'] = first_bad_night(nights, k)
            r[k + '_fired'] = fired_union(nights, k)
            r[k + '_caught'] = (r['dev_first_bad'] is not None and r[k + '_first_bad'] is not None
                                and r[k + '_first_bad'] <= r['dev_first_bad'] + 1)
        runs[s['name']] = r
    res = dict(runs=runs, overall=overall(runs))
    with open(a.out, 'w') as f:
        json.dump(res, f, indent=1)
    f2 = lambda x: '-' if x is None else f'{x:.2f}'
    print(f"{'run':28s} {'devbad':>6s} {'H1':>4s} {'H2':>4s} {'H12':>4s}  fired DEV | H12")
    for n, r in runs.items():
        print(f"{n:28s} {str(r['dev_first_bad']):>6s} {str(r['H1_first_bad']):>4s} {str(r['H2_first_bad']):>4s} {str(r['H12_first_bad']):>4s}  "
              f"{r['dev_fired']} | {r['H12_fired']}")
    for s in SETS:
        o = res['overall'][s]
        print(f"{s:4s} caught {o['caught']}/{o['dev_failing_runs']}  pairs {o['pairs_matched']}/{o['pairs']}  false alarms {o['false_alarms']}/{o['dev_good_nights']}  "
              f"r {f2(o['pearson_r'])}  mean home/dev {f2(o['mean_home_drop'])}/{f2(o['mean_dev_drop'])}")
    o = res['overall']['H1_vs_H2']
    print(f"H1 vs H2  r {f2(o['pearson_r'])}  verdict agreement {f2(o['verdict_agreement'])} over {o['unique_nights']} nights")


if __name__ == '__main__':
    main()
