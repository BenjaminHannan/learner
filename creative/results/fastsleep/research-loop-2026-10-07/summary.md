# Research loop status  (2026-10-07T20:49:37)
Goal: Get B2's C2 first-try score (5 held-out rule kinds, greedy, no test-time search) to 70% on unseen questions, learning from the night's practice pool, within 5 hours of M1 Pro GPU compute (counted FLOPs), without harming old skills
Metric: c2_right (max) | dev seeds/trial 2 | noise sigma 1.941 | min detectable delta 1.681
Guards: chain5_harm<=2; flops_tf<=10000
Segment 2 | phase done | branch research/get-b2-s-c2-first-try-score-5-held-out-r-20261007-1437
Baseline: dev 71.1914 +/- 2.2183 | holdout 71.7285 +/- 1.8417
Incumbent: dev 71.1914 (trial #base, 543d8b87) | +0.0000 vs baseline
Last holdout-confirmed: #base 543d8b87 holdout 71.7285 (+0.0000 vs baseline) | holdout calls 1/12
Trials 1 | keep 0 | near-miss 0 | discard 1 | crash 0 | runtime 4.15 h / 6.5 h
Arms (kept/tried): literature 0/0 | tune 0/0 | bold 0/0 | simplify 0/0 | combine 0/1
Due: nothing

Last trials (newest last):
  #    arm         outcome     delta     hypothesis
  7    combine     discard     -0.4883   Top-up (segment 1 near-miss #5, now compliant): every distinct found p
