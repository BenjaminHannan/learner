import time, numpy as np
from common import *
for k in (2,3,4):
    ct = canonical_trees(k)
    print(k, "trajectories", sum(m for _,m,_ in ct), "canonical trees", len(ct), "sign patterns", len({s for *_ ,s in ct}))
rng = np.random.default_rng(0)
for nums, t in [((7,12),19), ((7,12),5), ((7,12,30),25), ((7,12,30,40),25), ((5,9,23,31),40)]:
    t0=time.time(); s, st = exact_random_strict(list(nums), t); t1=time.time()
    a,b,c = mc_random(np.array([nums]), np.array([t]), 400000, rng)
    print(nums, t, "exact strict %.5f stop %.5f (%.2fs) | MC strict %.5f stop %.5f lenient %.5f" % (s, st, t1-t0, a[0], b[0], c[0]))
    s2, st2 = exact_random_strict(list(nums), t, pointer='independent')
    a2,b2,c2 = mc_random(np.array([nums]), np.array([t]), 400000, rng, pointer='independent')
    print("   independent: exact %.5f %.5f | MC %.5f %.5f %.5f" % (s2, st2, a2[0], b2[0], c2[0]))
