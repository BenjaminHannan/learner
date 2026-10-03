"""Part 1b: uniform random policy on target puzzles.
Main setting: target literal is a reference, ordered DISTINCT pointer pairs, results usable 0..99.
STRICT and STRICT-STOP exact per instance; LENIENT by Monte Carlo (R rollouts per instance; MC STRICT
is also kept as a check against the exact value). Instances: uniform over STRICT-solvable
(numbers, target) pairs. Sensitivities (first 500 instances): usable 0..999, independent pointers,
no target literal."""
import json, sys, time
import numpy as np
from common import exact_random_strict, mc_random, passk, quantiles

def sample_solvable(key, N, rng):
    d = np.load("counts_%s.npz" % key)
    X, traj, trees, sgn = d["X"], d["traj"], d["trees"], d["sgn"]
    si, ti = np.nonzero(traj > 0)
    pick = rng.choice(len(si), size=N, replace=False)
    return X[si[pick]], ti[pick], traj[si[pick], ti[pick]], trees[si[pick], ti[pick]]

def lenient_solvable(X, umax=99):
    """Per (set, target): reachable by some subset of >= 2 numbers (each at most once)."""
    import itertools
    from common import canonical_trees, eval_tree
    N, k = X.shape
    out = np.zeros((N, 100), dtype=bool)
    rows = np.arange(N)
    for size in range(2, k + 1):
        ct = canonical_trees(size)
        for cols in itertools.combinations(range(k), size):
            Xs = X[:, list(cols)]
            for e, m, s in ct:
                v, ok = eval_tree(e, Xs, umax)
                ok &= (v >= 0) & (v < 100)
                out[rows[ok], v[ok]] = True
    return out

def run_variant(nums, tgts, rng, R, umax, target_literal, pointer, chunk=250):
    ex = np.array([exact_random_strict(list(map(int, n)), int(t), umax, target_literal, pointer)
                   for n, t in zip(nums, tgts)])
    mcs, mcst, mcl = [], [], []
    for c in range(0, len(nums), chunk):
        a, b, l = mc_random(nums[c:c + chunk], tgts[c:c + chunk], R, rng, umax, target_literal, pointer)
        mcs.append(a); mcst.append(b); mcl.append(l)
    return ex[:, 0], ex[:, 1], np.concatenate(mcs), np.concatenate(mcst), np.concatenate(mcl)

def summary(p):
    return {"mean": float(np.mean(p)), "quantiles_0_10_25_50_75_90_100": quantiles(p),
            "share_zero": float(np.mean(p == 0)),
            "pass@1": passk(p, 1), "pass@8": passk(p, 8), "pass@32": passk(p, 32)}

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    R = 4096
    res = {}
    for k in (2, 3, 4):
        for lo, hi in ((2, 40), (2, 60)):
            key = "umax99_k%d_r%d-%d" % (k, lo, hi)
            rng = np.random.default_rng(1000 * k + hi)
            nsol = len(np.nonzero(np.load("counts_%s.npz" % key)["traj"] > 0)[0])
            nums, tgts, traj, trees = sample_solvable(key, min(N, nsol), rng)
            t0 = time.time()
            s, st, ms, mst, ml = run_variant(nums, tgts, rng, R, 99, True, "distinct")
            out = {"instances": len(tgts), "rollouts_per_instance_mc": R,
                   "strict_exact": summary(s), "stop_exact": summary(st), "lenient_mc": summary(ml),
                   "check_mc_minus_exact_strict_mean": float(ms.mean() - s.mean()),
                   "check_mc_minus_exact_stop_mean": float(mst.mean() - st.mean())}
            # p versus number of trajectories
            byb = {}
            for lab, lo_, hi_ in (("1", 1, 1), ("2", 2, 2), ("3-4", 3, 4), ("5-8", 5, 8), ("9-12", 9, 12),
                                  ("13-32", 13, 32), ("33-64", 33, 64), ("65-144", 65, 144)):
                m = (traj >= lo_) & (traj <= hi_)
                if m.sum() >= 20:
                    byb[lab] = {"n": int(m.sum()), "strict_mean": float(s[m].mean()), "lenient_mean": float(ml[m].mean())}
            out["by_trajectory_count"] = byb
            # sensitivities on the first 500 instances
            sens = {}
            m = min(500, len(tgts))
            base_s, base_l = s[:m].mean(), ml[:m].mean()
            sens["main_first500"] = {"strict": float(base_s), "stop": float(st[:m].mean()), "lenient": float(base_l)}
            for name, umax, tl, ptr in (("usable_0_999", 999, True, "distinct"),
                                        ("independent_pointers", 99, True, "independent"),
                                        ("no_target_literal", 99, False, "distinct")):
                a, b, _, _, l = run_variant(nums[:m], tgts[:m], rng, 2048, umax, tl, ptr)
                sens[name] = {"strict": float(a.mean()), "stop": float(b.mean()), "lenient": float(l.mean()),
                              "strict_pass@8": passk(a, 8), "strict_pass@32": passk(a, 32)}
            out["sensitivity"] = sens
            # lenient-solvable share over ALL instances, and lenient random hit on strict-UNSOLVABLE instances
            d = np.load("counts_%s.npz" % key)
            X, trajall = d["X"], d["traj"]
            if k >= 3:
                sub = rng.choice(X.shape[0], size=min(20000, X.shape[0]), replace=False)
                ls = lenient_solvable(X[sub])
                st_ = trajall[sub] > 0
                out["lenient_solvable_share_all_instances"] = float(ls.mean())
                out["strict_solvable_share_same_sample"] = float(st_.mean())
                out["lenient_solvable_share_among_strict_unsolvable"] = float(ls[~st_].mean())
                si, ti = np.nonzero(ls & ~st_)
                pk = rng.choice(len(si), size=min(500, len(si)), replace=False)
                _, _, l2 = mc_random(X[sub][si[pk]], ti[pk], 2048, rng)
                out["lenient_random_hit_on_strict_unsolvable_but_lenient_solvable"] = float(l2.mean())
            out["seconds"] = round(time.time() - t0, 1)
            res[key] = out
            print(key, "strict mean %.5f stop %.5f lenient %.5f (mc-exact %.1e) %.0fs" % (
                s.mean(), st.mean(), ml.mean(), out["check_mc_minus_exact_strict_mean"], out["seconds"]), flush=True)
    json.dump(res, open("part1_random.json", "w"), indent=1)
