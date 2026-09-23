# Experiment 45 — results (registered wave, seeds 4102–4106, 3 words, 150 sleep runs, ~75 s per seed)

Installs out of 15 word-seed cells (every install had fresh-village accuracy >= 0.99; wrong installs = 0 everywhere):

| Wrong answers in 20 | plain loss | robust loss |
|---|---|---|
| 0 | 15 | 15 |
| 2 | 0 | 10 |
| 4 | 0 | 2 |
| 6 | 0 | 0 |
| 20 | 0 | 0 |

Robust rejections at 2 wrong (best cross-validated match): 4102 boss_of_spouse 0.65, 4102 doctor_of_mothers_friend 0.15,
4103 doctor_… 0.65, 4104 boss_… 0.65, 4106 doctor_… 0.65. Per seed installs at 2 wrong: 4102 1/3, 4103 2/3, 4104 2/3,
4105 3/3, 4106 2/3.
Marks: N1 PASS (0 wrong installs / 150). N2 PASS 15/15. N3 FAIL (10/15, needed 12). N4 PASS 0/15.

Diagnostic after the wave (measurement only, enumerate.json): scoring all 729 hard chains with the same robust
likelihood, the true word is the single best chain in 15/15 cells at 2, 4 AND 6 wrong answers, by a margin of 3.5–4.7
nats per episode over the runner-up; at 20 wrong no chain stands out (best loss 5.77 vs the 6.40 ceiling).

What it means: the noise-tolerant loss turns "a 10%-wrong teacher can never teach" (0/15) into "usually can" (10/15)
with no wrong word ever installed. The remaining rejections are NOT missing signal: the right chain is there to be
found even with 30% wrong answers. The weak part is the soft router's optimiser inside small folds plus a gate that
compares against noisy labels.
What it does not mean: not dependable yet (N3 failed); 729-chain enumeration is a control and does not scale to a big
skill bank; the 10% allowance was matched to the true noise rate; toy only.
