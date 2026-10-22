"""Part 3 extra: what is needed when the between-seed SD is 5 points (greedy metric).
Same model as part3_power.py; adds M = 9 and 4 seeds per arm."""
import json, itertools
import numpy as np
from part3_power import greedy_scores, decide
rng = np.random.default_rng(11)
res = {}
for S, n in itertools.product((2, 3, 4), (192, 256, 384)):
    for M in (8, 9, 10):
        fp, pw, p10 = [], [], []
        for base in (10, 30, 50):
            for gain, store in ((0, fp), (15, pw), (10, p10)):
                B = greedy_scores(rng, n, base, gain, 5, S); C = greedy_scores(rng, n, base, 0, 5, S)
                store.append(float(decide(B, C, M).mean()))
        res["S%d n%d M%d" % (S, n, M)] = {"false_max": max(fp), "power15_min": min(pw), "power10_min": min(p10)}
        print("S=%d n=%d M=%d  false pass max %.1f%%  power +15 min %.0f%%  power +10 min %.0f%%%s" % (
            S, n, M, 100 * max(fp), 100 * min(pw), 100 * min(p10), "  OK" if max(fp) <= .05 and min(pw) >= .8 else ""))
json.dump(res, open("part3_extra.json", "w"), indent=1)
