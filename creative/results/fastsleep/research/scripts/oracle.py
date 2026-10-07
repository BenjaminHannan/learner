"""Read-only ceilings for 'recall' on DEV: (lit) a stored program solves the question as is; (comp) two stored programs chained, x -> P1 -> P2,
within B2's 7 steps; (hole) a stored shape P with fitted constants, A*P(x)+K, constants built from 1/2/10/100 within 7 steps. Library = the
parent's W programs + the 512 old add/mult notes. The key is read only to score. No model is run."""
import sys, json, collections, itertools
import torch
from creative import fewshot, c2_stones, rules_real as R

from creative import programs as P
from custom_io.models import progparse as pp
DATA = 'creative/data/c2'
dev = c2_stones._with_nums(R.load_split(DATA, 'dev'))
warm = R.warm_records(R.load_split(DATA, 'warm'))[:512]
CONSTS = [1, 2, 10, 100]

# constructible constants: min steps to build v from the 4 constants (exact ops), up to 3 steps
cost = {c: 0 for c in CONSTS}
frontier = dict(cost)
for depth in (1, 2, 3):
    new = {}
    vals = list(cost.items())
    for (a, ca), (b, cb) in itertools.product(vals, vals):
        if ca + cb + 1 != depth and not (ca + cb + 1 <= depth):
            continue
        for v in (a + b, a - b, a * b, (a // b if b and a % b == 0 else None)):
            if v is None or abs(v) > 10 ** 6:
                continue
            c = ca + cb + 1
            if c <= 3 and (v not in cost or cost[v] > c) and (v not in new or new[v] > c):
                new[v] = c
    cost.update(new)


def active(t):
    return sum(1 for o in t.ops if o)


def f_of(t, x, nums):
    n = list(nums); n[6] = x
    vals, valid = P.run(n, t)
    return vals[t.ans] if valid[t.ans] else None


def main(setup_path, which='both'):
    s = torch.load(setup_path, weights_only=False)
    pp._CACHE.update(s['cache'])
    lib = {}
    src = {'both': s['records']['W'] + warm, 'W': s['records']['W'], 'old': warm}[which]
    for r in src:
        t = fewshot.record_try(r)
        lib[(t.ops, t.a, t.b, t.ans)] = t
    lib = list(lib.values())
    out = collections.defaultdict(lambda: collections.Counter())
    for r in dev:
        p = fewshot.parse(r['prompt']); xs, ys, q = p['xs'], p['ys'], p['q']
        acc = set(str(a) for a in eval(r['accepted'])) if isinstance(r['accepted'], str) else set(map(str, r['accepted']))
        k = r['kind']; out[k]['n'] += 1
        pts = xs + [q]
        F = []
        for t in lib:
            if not fewshot.structure(p, t)[0]:
                continue
            v = [f_of(t, x, p['nums']) for x in pts]
            if None in v:
                continue
            F.append((t, tuple(v)))
        lit = any(v[:-1] == tuple(ys) and str(v[-1]) in acc for t, v in F)
        # comp: P2(P1(x)); P2 evaluated on P1's values
        comp = lit
        if not comp:
            for t1, v1 in F:
                for t2, _ in F:
                    if active(t1) + active(t2) > 7:
                        continue
                    v = [f_of(t2, y, p['nums']) for y in v1]
                    if None not in v and tuple(v[:-1]) == tuple(ys) and str(v[-1]) in acc:
                        comp = True; break
                if comp:
                    break
        # hole: A*f(x) + K, f in {x} U shapes
        hole = lit
        if not hole:
            shapes = [(None, tuple(pts), 0)] + [(t, v, active(t)) for t, v in F]
            for t, v, st in shapes:
                if v[0] == v[1]:
                    continue
                num, den = ys[1] - ys[0], v[1] - v[0]
                if num % den:
                    continue
                A = num // den; K = ys[0] - A * v[0]
                if any(A * v[i] + K != ys[i] for i in range(len(ys))) or str(A * v[-1] + K) not in acc:
                    continue
                need = st + (0 if A == 1 else cost.get(A, 99) + 1) + (0 if K == 0 else cost.get(abs(K), 99) + 1)
                if need <= 7:
                    hole = True; break
        # non-oracle: among fitting candidates (lit and comp), take the shortest; ties -> library order. Score that one choice.
        best = None
        for t, v in F:
            if v[:-1] == tuple(ys) and (best is None or active(t) < best[0]):
                best = (active(t), v[-1])
        for t1, v1 in F:
            for t2, _ in F:
                st = active(t1) + active(t2)
                if st > 7 or (best is not None and st >= best[0]):
                    continue
                v = [f_of(t2, y, p['nums']) for y in v1]
                if None not in v and tuple(v[:-1]) == tuple(ys):
                    best = (st, v[-1])
        out[k]['pick'] += best is not None and str(best[1]) in acc
        out[k]['fits'] += best is not None
        out[k]['lit'] += lit; out[k]['comp'] += comp; out[k]['hole'] += hole
    return {k: {m: round(100 * c[m] / c['n'], 1) for m in ('lit', 'comp', 'hole', 'fits', 'pick')} for k, c in out.items()}, len(lib)


if __name__ == '__main__':
    which = sys.argv[1]
    for path in sys.argv[2:]:
        res, n = main(path, which)
        print('ORACLE', which, path.split('/')[-2], n, json.dumps(res), flush=True)
