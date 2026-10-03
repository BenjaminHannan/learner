"""Part 1a/1d: exact solvability and solution counts over ALL instances (every k-subset of distinct
numbers in the range x every target 0..99). Saves per-instance counts for later sampling."""
import json, time
import numpy as np
from common import solution_counts

def summarize(X, traj, trees, sgn):
    N = X.shape[0]
    tgt = np.arange(100)[None, :]
    in_nums = (X[:, :, None] == tgt[:, None, :]).any(1)          # target equals a given number
    solv = traj > 0
    out = {"number_sets": int(N), "instances": int(N * 100), "solvable": int(solv.sum()),
           "frac_solvable": float(solv.mean()),
           "solvable_target_not_in_numbers": int((solv & ~in_nums).sum()),
           "frac_solvable_target_not_in_numbers": float((solv & ~in_nums).sum() / (~in_nums).sum()),
           "frac_sets_with_any_solvable_target": float(solv.any(1).mean()),
           "mean_solvable_targets_per_set": float(solv.sum(1).mean())}
    for name, a in (("traj", traj), ("trees", trees), ("signs", sgn)):
        v = a[solv].astype(np.int64)
        out[name] = {"mean": float(v.mean()), "median": float(np.median(v)),
                     "p10": float(np.quantile(v, .1)), "p90": float(np.quantile(v, .9)), "max": int(v.max()),
                     "share_eq1": float((v == 1).mean()), "share_2": float((v == 2).mean()),
                     "share_3_4": float(((v >= 3) & (v <= 4)).mean()),
                     "share_5_10": float(((v >= 5) & (v <= 10)).mean()), "share_gt10": float((v > 10).mean())}
    # solvable fraction by target band
    bands = {}
    for lo, hi in ((0, 9), (10, 49), (50, 99)):
        bands["%d-%d" % (lo, hi)] = float(solv[:, lo:hi + 1].mean())
    out["frac_solvable_by_target_band"] = bands
    return out

if __name__ == "__main__":
    res = {}
    for umax in (99, 999):
        for k in (2, 3, 4):
            for lo, hi in ((2, 40), (2, 60)):
                t0 = time.time()
                X, traj, trees, sgn = solution_counts(k, lo, hi, umax)
                key = "umax%d_k%d_r%d-%d" % (umax, k, lo, hi)
                res[key] = summarize(X, traj, trees, sgn)
                res[key]["seconds"] = round(time.time() - t0, 1)
                if umax == 99:
                    np.savez_compressed("counts_%s.npz" % key, X=X, traj=traj, trees=trees, sgn=sgn)
                print(key, json.dumps({kk: res[key][kk] for kk in ("frac_solvable", "solvable", "seconds")}), flush=True)
    json.dump(res, open("part1_counts.json", "w"), indent=1)
