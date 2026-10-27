import json, sys
from collections import defaultdict
def load(p, s="p-grids7"):
    return [r for r in map(json.loads, open(p)) if r["set"] == s]
def withink(rows):
    # dead/live pairs with equal k, pooled over k; ties count half
    g = defaultdict(lambda: ([], []))
    for r in rows: g[r["k"]][r["dead"] == 0].append(r["score"])
    num = den = 0.0
    for k, (d, l) in g.items():
        for a in d:
            for b in l:
                num += 1.0 if a > b else 0.5 if a == b else 0.0; den += 1
    return num / den if den else float("nan"), int(den)
for run, nets in (("run", ["s1","s2","s3","s4","r0"]), ("run-358i2", ["s1","s2","s3","s4"])):
    for s in nets:
        for st in ("p-grids7", "p-grids6"):
            a, n = withink(load(f"{run}/critic-{s}.rows.jsonl", st))
            print(run, s, st, round(a, 3), n)
