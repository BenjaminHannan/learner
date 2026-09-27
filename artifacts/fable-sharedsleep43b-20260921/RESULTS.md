# Experiment 43B — shared-gradient sleep vs plain replay — RESULTS (marks in PASSMARKS.md, sealed before the run)

Wave: 15 jobs, 6 at a time, about 18 min, Mac CPU. Base = 43A `randpos` (G0 valid in all seeds). V0 valid in all seeds (old skills before sleep 1.000 / 0.993 / 0.980).
Log: 100 raw episodes, 10 wrong on purpose, 20 held out; 3,000 updates; identical data in every arm.
Scored object = checkpoint with lowest held-out loss. That rule picked update 250 (the first check) in ALL 15 runs.

Selected checkpoint (seeds 4102 / 4103 / 4104):

| Arm | fresh | noisy episodes memorised | old skills | gradient energy kept | sleep seconds |
|---|---|---|---|---|---|
| plain | 0.350 / 0.225 / 0.170 | 0.57 / 0.00 / 0.33 | 0.988 / 0.978 / 0.990 | 1.00 | 210 |
| sign | 0.370 / 0.215 / 0.285 | 0.00 / 0.13 / 0.00 | 0.984 / 0.972 / 0.995 | 0.35-0.42 | 226 |
| snr | 0.280 / 0.130 / 0.250 | 0.29 / 0.13 / 0.22 | 0.990 / 0.980 / 0.977 | 0.51-0.54 | 526 |
| subspace | 0.380 / 0.185 / 0.200 | 0.00 / 0.00 / 0.11 | 0.983 / 0.995 / 0.995 | 0.62-0.73 | 242 |
| rank4 | 0.365 / 0.300 / 0.360 | 0.00 / 0.00 / 0.00 | 0.985 / 0.981 / 0.991 | 1.00 | 437 |

Final update (3,000), for information: fresh plain 0.425/0.160/0.180, sign 0.405/0.300/0.320, snr 0.325/0.185/0.210, subspace 0.480/0.220/0.235, rank4 0.505/0.315/0.435; noisy episodes memorised 0.57-1.00 in every arm.
Long inputs: lengths 9-10 <= 0.005 and length 12 = 0.000 in every arm and seed.

| Mark | sign | snr | subspace | rank4 |
|---|---|---|---|---|
| H1 fresh >= plain + 0.15, 3/3 | FAIL 0/3 | FAIL 0/3 | FAIL 0/3 | FAIL 1/3 |
| H2 noise <= plain - 0.30 and fresh kept, 3/3 | FAIL 2/3 | FAIL 0/3 | FAIL 1/3 | FAIL 2/3 |
| H3 old skills within 0.02 | 2/3 (seed 4103: -0.021) | 3/3 | 3/3 | 3/3 |
| H4 long 9-10 >= 0.50 (any arm) | FAIL | FAIL | FAIL | FAIL (plain too) |

Sealed decision rule -> no gradient filter and no rank limit joins Sleep-vNext.

What it means: on this toy, combining group gradients by sign agreement, signal-to-noise shrinking or a shared subspace did not let sleep learn from fewer or noisier experiences than plain replay. The rank-4 limit was the most consistent arm (never worse than plain, zero noise memorised at the selected step) but missed its mark.
What it does not mean: (1) H2 could not pass in seed 4103 because plain had already memorised no noise at update 250 — the mark had a floor problem, so "filters do nothing against noise" is NOT shown; by the final update every arm had memorised most of the noise. (2) The held-out-loss rule stopping at update 250 everywhere means all arms were compared very early in learning; loss on 20 episodes (2 of them wrong) is a poor selector. (3) The randomised-position base learns the new skill from 80 episodes much worse than the registered base did from 100 (0.17-0.35 vs 0.42-0.76), so base choice and hold-out both changed versus Experiment 42; Experiment 42 stays the baseline and is not re-interpreted. (4) Three seeds, one toy.
