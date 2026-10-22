"""Part 3: pass probability of the rule
   mean(B) - mean(C) >= M points  AND  every B seed > every C seed
for a fresh set of n puzzles, S seeds per arm.
GREEDY: each seed's true rate = base + gain(B only) + N(0, sigma_seed), clipped to [0,1];
        score = Binomial(n, rate)/n. Models are scored independently (no shared-puzzle correlation:
        this is conservative, shared puzzle difficulty would cancel part of the noise in B - C).
PASS@8 (32 samples per puzzle, puzzle is the unit): each seed's true pass@8 level = base + gain +
        N(0, sigma_seed); puzzle-sampling noise ~ Normal(0, sqrt(V/n)), V = per-puzzle variance of the
        unbiased pass@8 estimate. V = L(1-L) is an upper bound (any [0,1] score with mean L);
        'beta k=1' and 'beta k=4' put per-puzzle success p_i ~ Beta(mu*k, (1-mu)*k) (assumed).
        A full per-puzzle simulation checks the normal shortcut for a few cells."""
import json, itertools
import numpy as np
from scipy.stats import betabinom
from scipy.special import comb

REPS = 200000
NS = (128, 192, 256, 384, 512)
MS = (8, 10, 12)
GAINS = (0, 5, 10, 15)
BASES = (10, 30, 50)
SIGMAS = (3, 5)
SEEDS = (2, 3)

def decide(B, C, M):
    """B, C: [reps, S] scores in points."""
    return (B.mean(1) - C.mean(1) >= M) & (B.min(1) > C.max(1))

def greedy_scores(rng, n, base, gain, sigma, S):
    rate = np.clip((base + gain + rng.normal(0, sigma, size=(REPS, S))) / 100, 0, 1)
    return rng.binomial(n, rate) / n * 100

# ---- pass@8 per-puzzle variance under Beta heterogeneity ----
F8 = 1 - np.array([comb(32 - c, 8, exact=True) for c in range(33)], dtype=float) / comb(32, 8, exact=True)

def level_and_var(mu, kappa):
    pmf = betabinom.pmf(np.arange(33), 32, mu * kappa, (1 - mu) * kappa)
    L = float(pmf @ F8)
    return L, float(pmf @ F8 ** 2 - L ** 2)

def var_at_level(L, kappa):
    if kappa is None:
        return L * (1 - L)
    lo, hi = 1e-6, 1 - 1e-6
    for _ in range(60):
        mid = (lo + hi) / 2
        if level_and_var(mid, kappa)[0] < L: lo = mid
        else: hi = mid
    return level_and_var((lo + hi) / 2, kappa)[1]

VCACHE = {}
def pass8_scores(rng, n, base, gain, sigma, S, kappa):
    lvl = np.clip((base + gain + rng.normal(0, sigma, size=(REPS, S))) / 100, 0.001, 0.999)
    # variance evaluated on a grid of levels (interpolated)
    key = kappa
    if key not in VCACHE:
        grid = np.linspace(0.001, 0.999, 200)
        VCACHE[key] = (grid, np.array([var_at_level(g, kappa) for g in grid]))
    grid, vg = VCACHE[key]
    V = np.interp(lvl, grid, vg)
    return np.clip(lvl + rng.normal(0, 1, size=lvl.shape) * np.sqrt(V / n), 0, 1) * 100

def full_pass8_check(rng, n, base, gain, sigma, S, kappa, M, reps=4000):
    """Per-puzzle simulation (32 samples per puzzle) for one cell, to check the normal shortcut."""
    out = []
    for _ in range(reps):
        scores = {}
        for arm, g in (("B", gain), ("C", 0)):
            s_list = []
            for _s in range(S):
                L = np.clip((base + g + rng.normal(0, sigma)) / 100, 0.001, 0.999)
                lo, hi = 1e-6, 1 - 1e-6
                for _i in range(40):
                    mid = (lo + hi) / 2
                    if level_and_var(mid, kappa)[0] < L: lo = mid
                    else: hi = mid
                mu = (lo + hi) / 2
                p = rng.beta(mu * kappa, (1 - mu) * kappa, size=n)
                c = rng.binomial(32, p)
                s_list.append(F8[c].mean() * 100)
            scores[arm] = np.array(s_list)
        out.append(scores["B"].mean() - scores["C"].mean() >= M and scores["B"].min() > scores["C"].max())
    return float(np.mean(out))

if __name__ == "__main__":
    rng = np.random.default_rng(7)
    res = {"greedy": {}, "pass8": {}}
    for metric, kappas in (("greedy", (None,)), ("pass8", (None, 1.0, 4.0))):
        for kappa in kappas:
            for n, base, gain, sigma, S in itertools.product(NS, BASES, GAINS, SIGMAS, SEEDS):
                if metric == "greedy":
                    B = greedy_scores(rng, n, base, gain, sigma, S); C = greedy_scores(rng, n, base, 0, sigma, S)
                    tag = "greedy"
                else:
                    B = pass8_scores(rng, n, base, gain, sigma, S, kappa); C = pass8_scores(rng, n, base, 0, sigma, S, kappa)
                    tag = "pass8_" + ("bound" if kappa is None else "beta%g" % kappa)
                for M in MS:
                    res["greedy" if metric == "greedy" else "pass8"]["%s|n%d|b%d|g%d|s%d|S%d|M%d" % (tag, n, base, gain, sigma, S, M)] = float(decide(B, C, M).mean())
            print("done", metric, kappa, flush=True)
    # checks of the normal shortcut for pass@8 (beta k=1), a few cells
    checks = {}
    for (n, base, gain, sigma, M) in ((192, 30, 0, 3, 8), (192, 30, 15, 3, 10), (256, 50, 15, 5, 10)):
        full = full_pass8_check(rng, n, base, gain, sigma, 2, 1.0, M)
        approx = res["pass8"]["pass8_beta1|n%d|b%d|g%d|s%d|S2|M%d" % (n, base, gain, sigma, M)]
        checks["n%d b%d g%d s%d M%d" % (n, base, gain, sigma, M)] = {"full_sim_4000": full, "normal_shortcut_200k": approx}
    res["pass8_shortcut_checks"] = checks
    res["pass8_variance_vs_bound"] = {("L=%d" % L): {"bound": L / 100 * (1 - L / 100),
                                      "beta1": var_at_level(L / 100, 1.0), "beta4": var_at_level(L / 100, 4.0)}
                                      for L in (10, 30, 50, 65)}
    json.dump(res, open("part3_power.json", "w"), indent=1)
    print(json.dumps(checks, indent=1)); print(json.dumps(res["pass8_variance_vs_bound"], indent=1))
