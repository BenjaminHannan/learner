"""(a) cold-start: DEV gate (>=13 of 128) passes but practice count (<100 of 1024) fails, same true coverage c.
(b) G1 false-fail: true coverage unchanged, seed SD 5 on coverage, 3 W seeds, paired puzzles (puzzle noise mostly cancels).
(c) S2 power: T2 W-R must be >= half of T1 W-R and T2 interval above 0; full retention assumed.
(d) 3-seed range on shared DEV puzzles at seed SD 5."""
import numpy as np
from scipy import stats
rng = np.random.default_rng(11)
print('(a) cold start')
for c in (0.06, 0.08, 0.09, 0.10, 0.11, 0.12, 0.14):
    pd = stats.binom.sf(12, 128, c); pp = stats.binom.cdf(99, 1024, c)
    print('  true coverage %.2f: P(DEV>=13) %.2f  P(practice<100) %.2f  P(both) %.2f' % (c, pd, pp, pd * pp))
print('(b) G1')
R = 400000
for sd in (3, 5):
    m = rng.normal(0, sd, (R, 3)).mean(1) + rng.normal(0, 1.0, R)  # small residual paired puzzle noise
    print('  seed SD %d: P(mean W < N-2 | no true change) = %.3f' % (sd, (m < -2).mean()))
print('(c) S2 (seed-level Welch t interval, 3 v 3; T1 and T2 seeds independent draws, conservative)')
def welch_lo(a, b):
    va, vb = a.var(1, ddof=1) / 3, b.var(1, ddof=1) / 3
    se = np.sqrt(va + vb); df = (va + vb) ** 2 / (va ** 2 / 2 + vb ** 2 / 2)
    return a.mean(1) - b.mean(1) - stats.t.ppf(0.975, df) * se
for g in (8, 10, 12, 15, 20):
    s = np.sqrt(25 + 1.0)
    W1 = rng.normal(g, s, (R, 3)); R1 = rng.normal(0, s, (R, 3))
    W2 = rng.normal(g, s, (R, 3)); R2 = rng.normal(0, s, (R, 3))
    t1 = W1.mean(1) - R1.mean(1); t2 = W2.mean(1) - R2.mean(1)
    ok = (t2 >= t1 / 2) & (welch_lo(W2, R2) > 0)
    cond = (t1 >= 8) & (W1.min(1) > R1.mean(1))  # S2 only runs after PASS (L2 part)
    print('  true W-R %2d, full retention: P(S2 passes | L2 passed) = %.2f' % (g, ok[cond].mean()))
print('(d) range of 3 R seeds on shared DEV puzzles')
for sd in (5, 6, 7):
    x = rng.normal(0, np.sqrt(sd ** 2 + 0.5), (R, 3)); r = x.max(1) - x.min(1)
    print('  seed SD %d: 95th pct range %.1f  P(range>19) %.3f' % (sd, np.quantile(r, .95), (r > 19).mean()))
