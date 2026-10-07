"""Control for 'chain two notes and check': a blind search with no memory. Breadth-first over value vectors (examples + query) from x and the
constants 1/2/10/100 with B2's ops; each new vector is one candidate; the first that fits the 3 examples is the answer. Budgets in candidates."""
import json, collections, itertools
from creative import fewshot, c2_stones, rules_real as R
from creative.programs import apply
dev = c2_stones._with_nums(R.load_split('creative/data/c2', 'dev'))
OPS = (1, 2, 3, 4, 5, 6, 7)


def solve(p, budget):
    pts = p['xs'] + [p['q']]
    n = len(pts)
    start = [tuple(pts)] + [tuple([c] * n) for c in (1, 2, 10, 100)]
    seen = set(start); pool = list(start); used = 0
    while used < budget:
        new = []
        for a, b in itertools.product(pool, pool):
            for op in OPS:
                v = []
                for i in range(n):
                    r = apply(op, a[i], b[i])
                    if r is None: break
                    v.append(r)
                if len(v) < n: continue
                v = tuple(v)
                if v in seen: continue
                seen.add(v); used += 1; new.append(v)
                if list(v[:-1]) == p['ys']:
                    return v[-1], used
                if used >= budget:
                    return None, used
        if not new:
            return None, used
        pool += new
    return None, used


for budget in (1000, 6000, 50000):
    by = collections.defaultdict(lambda: [0, 0])
    for r in dev:
        p = fewshot.parse(r['prompt'])
        acc = set(map(str, eval(r['accepted']) if isinstance(r['accepted'], str) else r['accepted']))
        a, _ = solve(p, budget)
        by[r['kind']][0] += 1; by[r['kind']][1] += a is not None and str(a) in acc
    print('BLIND', budget, json.dumps({k: round(100 * v[1] / v[0], 1) for k, v in by.items()}), 'pooled', round(100 * sum(v[1] for v in by.values()) / len(dev), 1), flush=True)
