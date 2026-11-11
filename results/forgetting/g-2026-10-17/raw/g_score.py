"""Round G scorer: applies PREREG-G.md (fixed before launch) to the worker reports.

Inputs (written by the lead as reports arrive):
  g/reports/<run>.records.json   the 'records' list from 'G REPORT <run> records'
  g/rows/<run>.json              {key: value} from 'G ROWS <run> <key>' messages (hash-checked on save)
Usage: python3 g_score.py [ARM ...]   (default: every arm with both seeds in)
"""
import base64, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = ('93301', '31001')
U, SESOI = 41.6, 5.0
C2_MIN = U - SESOI            # 36.6
READS = (4000, 6000, 8000, 10000, 12000, 14000, 16000)


def load(run):
    p = os.path.join(HERE, 'reports', f'{run}.records.json')
    return {r['step']: r for r in json.load(open(p))} if os.path.exists(p) else None


def rows(run):
    p = os.path.join(HERE, 'rows', f'{run}.json')
    return json.load(open(p)) if os.path.exists(p) else {}


def bits(s, n):
    return [int(c) for c in ''.join(f'{x:08b}' for x in base64.b64decode(s))[:n]]


def ho(r):
    h, n = r['cells']['HO']
    return 100.0 * h / n


def c1(r):
    hb = r.get('harm_big')
    return bool(hb and hb['passes'] and hb['in_dist_drop'] <= 1.0), hb


def worst(hb):
    fd = (hb or {}).get('family_drops') or {}
    return max(fd.items(), key=lambda kv: kv[1]) if fd else (None, None)


def score(arm):
    recs = {s: load(f'g-{arm}-s{s}') for s in SEEDS}
    if not all(recs.values()):
        return None
    out = dict(arm=arm, curve=[], tstar=None)
    for st in READS:
        if not all(st in recs[s] for s in SEEDS):
            continue
        hos = [ho(recs[s][st]) for s in SEEDS]
        cs = [c1(recs[s][st]) for s in SEEDS]
        out['curve'].append(dict(step=st, ho=hos, mean_ho=sum(hos) / 2,
                                 s5=[100.0 * recs[s][st]['cells']['S5'][0] / 420 for s in SEEDS],
                                 drop=[c[1]['in_dist_drop'] if c[1] else None for c in cs],
                                 fired=[c[1]['fired'] if c[1] else None for c in cs],
                                 worst=[worst(c[1]) for c in cs], c1=[c[0] for c in cs]))
    for c in out['curve']:
        if c['mean_ho'] >= C2_MIN:
            out['tstar'] = c['step']
            out['success'] = all(c['c1'])
            break
    if out['tstar'] is None:
        last = {c['step']: c['mean_ho'] for c in out['curve']}
        out['success'] = False
        out['delay_vs_cap'] = ('capped' if 16000 in last and 12000 in last and last[16000] - last[12000] < 2 else 'open')
    else:
        out['delay_vs_cap'] = 'delayed (reached)'
    return out


def contrast(run_x, run_y, key):
    """item-paired drop(X) - drop(Y) on the 6,800 rows at key (e.g. 'big@8000'); normal 95%."""
    X, Y = rows(run_x), rows(run_y)
    if key not in X or key not in Y:
        return None
    n = X[key]['n']
    x, y = bits(X[key]['child'], n), bits(Y[key]['child'], n)
    d = [100 * (b - a) for a, b in zip(x, y)]
    m = sum(d) / n
    se = math.sqrt(sum((v - m) ** 2 for v in d) / (n - 1) / n)
    return round(m, 2), round(m - 1.96 * se, 2), round(m + 1.96 * se, 2)


if __name__ == '__main__':
    arms = sys.argv[1:] or ['G0', 'G1', 'G2', 'G3', 'G4', 'H1']
    for a in arms:
        s = score(a)
        if not s:
            print(a, 'incomplete'); continue
        print(f"== {a}: T*={s['tstar']} success={s['success']} ({s['delay_vs_cap']})")
        for c in s['curve']:
            print(f"  {c['step']:>5}  HO {c['ho'][0]:5.1f}/{c['ho'][1]:5.1f} mean {c['mean_ho']:5.1f}  S5 {c['s5'][0]:5.1f}/{c['s5'][1]:5.1f}"
                  f"  drop6800 {c['drop']}  fired {c['fired']}  worst {c['worst']}  C1 {c['c1']}")
        if a != 'G0':
            for st in (8000, s['tstar']):
                if st:
                    for sd in SEEDS:
                        print(f"  drop({a})-drop(G0) s{sd} @{st}: {contrast(f'g-{a}-s{sd}', f'g-G0-s{sd}', f'big@{st}')}")
