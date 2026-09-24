# rsn-350 RESULTS (builder, 2026-09-24)

## Verdict: FAIL

Z1 FAIL on both seeds, Z2 FAIL, Z3 FAIL on both seeds, Z4 PASS on both seeds.
PASS required Z1, Z3 and Z4 on both seeds. The pre-registered "size is the bottleneck is
wrong" condition is met: fresh total <= 296 same-seed + 3 on both seeds (211 <= 228,
209 <= 220) AND three-step 0/30 on both seeds. The 10x trigger (Z1 on both seeds) is NOT met.

## Runs

Plain arm, size 90m = 91,588,629 numbers (train_summary.json "params" on both runs).
Defaults otherwise, changed nothing. Both seeds trained 2-at-a-time on one RTX 5090.

| run | minutes | copy loss first -> last | practice reward first -> last |
|---|---|---|---|
| plain90-s1 | 35.1 | 4.0901 -> 0.0042 | 0.6448 -> 0.8130 |
| plain90-s2 | 35.3 | 4.2522 -> 0.0036 | 0.6202 -> 0.8450 |

(First/last lines of runs/plain90-s*/train_log.jsonl.)

## Panel totals (checked right / raw right)

reasonpanel296 v2, n = 298. 296 plain finals for comparison: s1 225, s2 217.

| ckpt | total checked | total raw |
|---|---|---|
| s1 copy_only | 175 | 173 |
| s1 final | 211 | 207 |
| s2 copy_only | 180 | 176 |
| s2 final | 209 | 206 |

reasonpanel294 v3, n = 300. 296 plain finals: 238 each seed.

| ckpt | total checked | total raw |
|---|---|---|
| s1 copy_only | 206 | 207 |
| s1 final | 227 | 229 |
| s2 copy_only | 204 | 204 |
| s2 final | 229 | 230 |

## Per-category checked-right counts

reasonpanel296 v2 (n: one 30, two 30, backwards 30, yes_no 30, missing 30, correction 28,
before_after 30, comparing 30, counting 30, three_step 30):

| ckpt | one | two | back | yesno | miss | corr | b/a | comp | count | 3-step | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s1 copy_only | 29 | 19 | 30 | 30 | 30 | 20 | 17 | 0 | 0 | 0 | 175 |
| s1 final | 30 | 30 | 30 | 30 | 30 | 19 | 22 | 16 | 4 | 0 | 211 |
| s2 copy_only | 30 | 30 | 30 | 30 | 30 | 21 | 9 | 0 | 0 | 0 | 180 |
| s2 final | 30 | 28 | 30 | 30 | 30 | 22 | 19 | 16 | 4 | 0 | 209 |

296 plain finals for comparison: correction 23/19, before/after 24/20, comparing 16/16,
counting 12/12, three-step 0/0, totals 225/217.

reasonpanel294 v3 (n: one 30, two 30, backwards 30, yes_no 30, missing 30, correction 30,
before_after 30, comparing 30, counting 30, big_notebook 15, three_step 15):

| ckpt | one | two | back | yesno | miss | corr | b/a | comp | count | big | 3-step | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s1 copy_only | 30 | 28 | 30 | 30 | 30 | 30 | 13 | 0 | 0 | 15 | 0 | 206 |
| s1 final | 30 | 30 | 30 | 30 | 30 | 30 | 20 | 12 | 0 | 15 | 0 | 227 |
| s2 copy_only | 30 | 29 | 30 | 30 | 30 | 30 | 10 | 0 | 0 | 15 | 0 | 204 |
| s2 final | 30 | 30 | 30 | 30 | 30 | 30 | 17 | 12 | 5 | 15 | 0 | 229 |

Dev check (fresh generated episodes, seed 777, checked right / n = 1200):
s1 final 881, s2 final 897. Dev counting: s1 12/100, s2 13/100; dev three-step
("value3", never practised): 0/100 both, all "I don't know" after the fact-check.

## Marks Z1-Z4 (integer counts, PASS/FAIL)

| mark | bar | s1 | s2 |
|---|---|---|---|
| Z1 fresh panel296 total | >= 296 + 10 (s1 >= 235, s2 >= 227) | 211, FAIL | 209, FAIL |
| Z2 fresh three-step | >= 6/30 one seed | 0/30, FAIL | 0/30, FAIL |
| Z3 transfer panel294 total | >= 233 each | 227, FAIL | 229, FAIL |
| Z4 invented (checked), 296 panel | <= 2 | 0, PASS | 0, PASS |
| Z4 invented (checked), 294 panel | <= 2 | 0, PASS | 0, PASS |

Z4 detail: missing_fact checked-right is 30/30 on every final on both panels; the 5 raw
answers-without-fact per 296-panel final were all turned into "I don't know" by the
fact-check (checked inventions 0). Copy-only checkpoints also 0 everywhere.

## Money

Instance 52475017 (RTX 5090, 48 vCPU, $0.4956/h incl. storage): created 19:52 UTC,
destroyed 21:44 UTC = ~1.9 h x $0.4956 = ~$0.94. First rental 52474472 (offer 43165155)
never left loading (host docker-proxy error) and was destroyed; billed ~$0. Combined
running total ~$0.94, under the $4 cap. No re-rents after the two above.

## Checkpoints (kept, never pushed)

~/premonition-models/rsn350/plain90-s1/ and plain90-s2/, sha256 verified identical to
SEAL-run.sha256.txt:

6e4a6cd66ec0bf3f097b4e3e7f1c16b4262194d67cba8fca79675a5dd25e6a60  plain90-s1/copy_only.pt
44da9e56e9764f0424e9bfa51e6fe8a9ba5c11c749fb60fb8b8a207b4932d6aa  plain90-s1/final.pt
34587d7ab8486b34b6049bc1263dd2bb1e1c4af7359d747d5f3ffff580cb22b0  plain90-s2/copy_only.pt
52140830b692ce3276b028f5acd2ffbff7b91ced0dc182a04885e3192a1b731a  plain90-s2/final.pt

## What this means / doesn't mean (plain high-school English)

Making the reasoner about 3 times bigger did not make it smarter. Its fresh score went
DOWN (211 and 209 vs 225 and 217 for the smaller model), it still gets 0 out of 30 on
longer chains it never practised, and its transfer score went down too (227 and 229 vs
238). Counting got worse (4/30 vs 12/30). So at this size, "just add numbers" is not the
fix; the bottleneck is elsewhere (what it practises, not how big it is). This does NOT
mean size can never help, only that 3x did not help here. The honesty part still works:
it says "I don't know" instead of inventing answers (0 inventions).
