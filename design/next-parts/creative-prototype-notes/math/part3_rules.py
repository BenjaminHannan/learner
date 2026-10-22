"""Part 3 alternative rules (untested idea, for 'what is needed'): with more seeds the brief's
'every B seed beats every control seed' clause gets stricter, so compare:
 R1 brief: mean diff >= M and min(B) > max(C)
 R2: mean diff >= M and min(B) > mean(C)
 R3: mean diff >= M only
Greedy metric, same noise model as part3_power.py."""
import json, itertools
import numpy as np
from part3_power import greedy_scores
rng = np.random.default_rng(13)
rules = {"R1": lambda B, C, M: (B.mean(1) - C.mean(1) >= M) & (B.min(1) > C.max(1)),
         "R2": lambda B, C, M: (B.mean(1) - C.mean(1) >= M) & (B.min(1) > C.mean(1)),
         "R3": lambda B, C, M: (B.mean(1) - C.mean(1) >= M)}
res = {}
for sigma, S, n in itertools.product((3, 5), (2, 3, 4), (192, 256, 384)):
    sims = {}
    for base in (10, 30, 50):
        for gain in (0, 15):
            sims[(base, gain)] = (greedy_scores(rng, n, base, gain, sigma, S), greedy_scores(rng, n, base, 0, sigma, S))
    for rname, rule in rules.items():
        for M in (8, 9, 10, 11, 12):
            fp = max(float(rule(*sims[(b, 0)], M).mean()) for b in (10, 30, 50))
            pw = min(float(rule(*sims[(b, 15)], M).mean()) for b in (10, 30, 50))
            res["sd%d S%d n%d %s M%d" % (sigma, S, n, rname, M)] = (fp, pw)
            if fp <= 0.05 and pw >= 0.80:
                print("OK  seedSD=%d seeds=%d n=%d %s M=%d  false max %.1f%%  power+15 min %.0f%%" % (sigma, S, n, rname, M, 100 * fp, 100 * pw))
json.dump(res, open("part3_rules.json", "w"), indent=1)
