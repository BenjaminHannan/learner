# Two-step problems (two chained calculator calls), fast lane, marks fixed before training (2026-10-03)

Recipe unchanged otherwise: frozen LFM2.5-1.2B contextual reader, 9.2M core, 4 loops, copy path (the last valid call's result token embedding
is a 9th prefix vector), never-repeating stream, 3000 x 16 updates, lr 1e-3. Changes needed for the task: the call head can point at 3 literals
(x, y, z) and at the result slots of calls 1 and 2; 70% two-step training items (x op1 y, then that result op2 z) and 30% one-step items.
Training wording: gen_two.py TRAIN frames (pruned of any frame sharing a sentence or 6-gram with the eval frames). Eval: EVAL-TWO-v1.json, 96 two-step
questions (48 final answers unseen as training answers, 48 seen), different story wording, no authored/sealed check (fast lane: simple held-out split).
Final answers in training are only the 60 train answers T; intermediate results can be any two-digit value (so a held-out value can appear as an
intermediate in training but never as a final answer). Operand triples of eval are excluded from training. 6 seeds (0-5), one box.

Reported per run: call-1 right, call-2 right, both right (chain), final-answer accuracy on all, on unseen finals, on seen finals; share of wrong
unseen finals that equal a training answer.
HOLDS: mean chain rate >= 80% AND mean unseen-final accuracy >= 75% AND < 20% of wrong unseen finals equal a training answer.
FAILS: mean chain rate < 50% OR mean unseen-final accuracy < 40%.
Between: anything else; partial, no claim.
Known limit: one operation pair set (add/subtract), two-digit values only, a calculator that does the arithmetic exactly.
Per-question rows (96 x 6 = 576) copied back and counted before the box is destroyed.
