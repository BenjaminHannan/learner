# Pass marks, fixed before any training (2026-10-03)

Test: does training on never-repeating problems (arm B) fix "right calculator call, wrong final number"
on answers never seen in training, compared with training on a fixed pool of 256 repeated problems (arm A)?
Everything else is identical (same reader, same 9M core, same 4 loops, same updates, same batch, same LR).
2 seeds per arm. Eval form: 96 matched ADD/SUB pairs (192 questions), sealed by hash (SEAL.json).
Cells: answers unseen / seen in training, crossed with train wording / new wording, 24 pairs each.
Final-answer accuracy = the frozen LM's first generated token equals the right two-digit answer, using the
model's own calculator call (no gold at test time). "Unseen" = both answers of the pair are in the 30 held-out values.

Arm void: an arm/seed whose train fit (192 of its own training questions) is below 90% did not fit; reported, not counted.

PASS (arm B stops memorising), all must hold on BOTH seeds:
 1. B final accuracy on unseen-answer questions (96) >= 50%.
 2. B beats A (same seed index) by >= 25 points on unseen-answer questions.
 3. B unseen accuracy >= 70% of B seen accuracy.
FALSIFIED: B unseen accuracy <= 15% on both seeds (or within 10 points of A on both seeds).
IN BETWEEN: anything else; reported as partial, no claim.
Also reported, no mark: right calculator call rate; share of wrong unseen answers that equal a training answer;
pairs both right; per-cell accuracy.
