"""Re-check of v2 marks under a per-puzzle model (CPU only, assumptions labelled).
Per-try luck: puzzle i has base success q_i ~ Beta(mu*k,(1-mu)*k) (k=1, as maths 3c 'beta1');
seed s of an arm has additive effect u_s ~ N(0, SD) points; arm gain g points (W only).
p_is = clip(q_i + (g+u_s)/100, 0, 1); luck_is = Binomial(32, p_is)/32. W and R share puzzles (paired).
Interval = design's two-level bootstrap: resample 3 seeds within each arm, then puzzles (paired), 95% percentile.
Compared with a seed-level Welch t interval (3 v 3)."""
import numpy as np
from scipy import stats
rng = np.random.default_rng(7)
n, S, SD, B = 256, 3, 5.0, 400

def arm(q, g, S):
    u = rng.normal(0, SD, S)
    p = np.clip(q[None, :] + (g + u[:, None]) / 100, 0, 1)
    return rng.binomial(32, p) / 32 * 100  # (S, n) points

def boot_interval(W, R):
    sw = rng.integers(0, W.shape[0], (B, W.shape[0])); sr = rng.integers(0, R.shape[0], (B, R.shape[0]))
    pj = rng.integers(0, n, (B, n))
    Wm = W[sw].mean(1); Rm = R[sr].mean(1)          # (B, n)
    d = np.take_along_axis(Wm - Rm, pj, 1).mean(1)
    return np.quantile(d, [0.025, 0.975])

def welch_interval(W, R):
    a, b = W.mean(1), R.mean(1)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1) + 1e-12)
    t = stats.t.ppf(0.975, max(df, 1))
    m = a.mean() - b.mean()
    return np.array([m - t * se, m + t * se])

def run(mu, g, E=1500):
    k = 1.0
    out = dict(L2=0, L2_noint=0, boot_lo_gt0=0, boot_up_lt5=0, welch_up_lt5=0, cover_boot=0, cover_welch=0)
    for _ in range(E):
        q = rng.beta(mu * k, (1 - mu) * k, n)
        W = arm(q, g, S); R = arm(q, 0, S)
        d = W.mean() - R.mean()
        bi = boot_interval(W, R); wi = welch_interval(W, R)
        every = (W.mean(1) > R.mean()).all()
        out['L2_noint'] += (d >= 8) & every
        out['L2'] += (d >= 8) & every & (bi[0] > 0)
        out['boot_lo_gt0'] += bi[0] > 0
        out['boot_up_lt5'] += bi[1] < 5
        out['welch_up_lt5'] += wi[1] < 5
        # true W-R on this puzzle set ~ g (clipping aside)
        out['cover_boot'] += bi[0] <= g <= bi[1]
        out['cover_welch'] += wi[0] <= g <= wi[1]
    return {k2: v / E for k2, v in out.items()}

for mu in (0.10, 0.30):
    for g in (0, 3, 5, 8, 10, 15):
        r = run(mu, g)
        print('base %2d%% gain %2d: ' % (mu * 100, g) + '  '.join('%s %.3f' % kv for kv in r.items()), flush=True)
