"""Part 1c/1d: difficulty tiers. Exact instance counts under the generation filters, and random-policy
acceptance on 2000 instances drawn uniformly from each tier (STRICT/STOP exact, LENIENT Monte Carlo).
Filters: F1 target not equal to any given number; F2 no shortcut (no proper subset of >= 2 numbers
reaches the target, so stopping early or ignoring a number can never hit it); F3 'order-forced'
(some valid-looking orders overflow/underflow, i.e. fewer valid trees than the sign pattern allows)."""
import itertools, json, zlib
import numpy as np
from common import canonical_trees, eval_tree, exact_random_strict, mc_random, passk, quantiles

MAXTREES = {2: 1, 3: 3, 4: 15}

def proper_subset_reach(X, umax=99):
    N, k = X.shape
    out = np.zeros((N, 100), dtype=bool)
    rows = np.arange(N)
    for size in range(2, k):
        ct = canonical_trees(size)
        for cols in itertools.combinations(range(k), size):
            Xs = X[:, list(cols)]
            for e, m, s in ct:
                v, ok = eval_tree(e, Xs, umax)
                ok &= (v >= 0) & (v < 100)
                out[rows[ok], v[ok]] = True
    return out

TIERS = {
    # name: (k, lo, hi, require_no_shortcut, require_order_forced)
    "W  warm-up   k=2, 2..60":                 (2, 2, 60, False, False),
    "P  practice  k=3, 2..40, no shortcut":    (3, 2, 40, True, False),
    "P' practice  k=3, 2..60, no shortcut":    (3, 2, 60, True, False),
    "T  transfer  k=4, 2..60, no shortcut":    (4, 2, 60, True, False),
    "T+ transfer  k=4, 2..60, no shortcut, order-forced": (4, 2, 60, True, True),
    "k3 all (reference) 2..40":                (3, 2, 40, False, False),
    "k4 all (reference) 2..60":                (4, 2, 60, False, False),
}

if __name__ == "__main__":
    res = {}
    for name, (k, lo, hi, nosc, forced) in TIERS.items():
        d = np.load("counts_umax99_k%d_r%d-%d.npz" % (k, lo, hi))
        X, traj, trees, sgn = d["X"], d["traj"], d["trees"], d["sgn"]
        solv = traj > 0
        tgt = np.arange(100)[None, :]
        not_in = ~(X[:, :, None] == tgt[:, None, :]).any(1)
        keep = solv & not_in
        if nosc:
            keep &= ~proper_subset_reach(X)
        if forced:
            keep &= trees < MAXTREES[k] * sgn
        si, ti = np.nonzero(keep)
        rng = np.random.default_rng(zlib.crc32(name.encode()))
        pick = rng.choice(len(si), size=min(2000, len(si)), replace=False)
        nums, tg = X[si[pick]], ti[pick]
        ex = np.array([exact_random_strict(list(map(int, n)), int(t)) for n, t in zip(nums, tg)])
        ls = []
        for c in range(0, len(tg), 250):
            ls.append(mc_random(nums[c:c + 250], tg[c:c + 250], 4096, rng)[2])
        ls = np.concatenate(ls)
        res[name] = {
            "distinct_canonical_instances": int(keep.sum()),
            "distinct_number_sets_with_an_instance": int(keep.any(1).sum()),
            "share_of_all_instances": float(keep.mean()),
            "order_forced_share_within_tier": float((trees[keep] < MAXTREES[k] * sgn[keep]).mean()),
            "unique_sign_pattern_share": float((sgn[keep] == 1).mean()),
            "mean_trajectories": float(traj[keep].mean()), "mean_trees": float(trees[keep].mean()),
            "strict": {"mean": float(ex[:, 0].mean()), "median": float(np.median(ex[:, 0])),
                       "p10_p90": [float(np.quantile(ex[:, 0], .1)), float(np.quantile(ex[:, 0], .9))],
                       "pass@8": passk(ex[:, 0], 8), "pass@32": passk(ex[:, 0], 32)},
            "stop": {"mean": float(ex[:, 1].mean()), "pass@8": passk(ex[:, 1], 8), "pass@32": passk(ex[:, 1], 32)},
            "lenient_mc": {"mean": float(ls.mean()), "pass@8": passk(ls, 8), "pass@32": passk(ls, 32)},
        }
        print(name, json.dumps(res[name]), flush=True)
    json.dump(res, open("part1_tiers.json", "w"), indent=1)
