# Two-step problems: varied wording (V) and ordered operation read (O), marks fixed before training (2026-10-03, fast lane)

Arms, 6 seeds each (0-5), same recipe as the two-step baseline (copy path, 4 loops, 3000 x 16 updates, lr 1e-3, 70% two-step + 30% one-step items):
 - BASE: two-step training wording = gen_two TRAIN frames only (narrative); mean-pooled action/pointer read.
 - V: BASE plus procedurally composed table-layout, question-first and distance-with-units frames in training (gen_two2.weak_train).
 - O: BASE wording, but each loop reads the question with its own learned attention query (loop-indexed ordered read) instead of the mean.
 - VO: both.
Eval (all four arms, scored once per run): EVAL-TWO-v2.json = 96 two-step questions with the earlier eval wording (old frames) + 96 HELD-OUT variants of
table / question-first / distance structures whose wording is not in any training frame (gen_two2.disjointness(): 0 shared 6-grams, 0 shared sentences,
saved in results/DISJOINTNESS-TWO.json). Finals: half unseen answers (held-out values), half seen. Simple held-out split, no sealing (fast lane).
HEADLINE: chain rate (both calls right) on all 192 questions, per seed; paired gain of an arm over BASE on the same seed.
PASS (per arm): paired mean gain >= +15 points AND 95% t-interval (n=6, t=2.571) lower bound > 0.
FAILS (per arm): paired mean gain < +5 points. Between: partial, no claim.
Reported: chain rate on old frames vs the three held-out structures separately, call-1 and call-2 rates, chain rate by second operation (ADD/SUB),
unseen-final accuracy, seed spread. Rows (192 x 24 = 4608) copied back and counted before boxes are destroyed.
Prior for BASE-like training on the old eval: chain 39.9%, second-SUB calls 0%.
