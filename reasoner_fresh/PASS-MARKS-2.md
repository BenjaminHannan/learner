# Pass marks for the copy-path change, fixed before training (2026-10-03, fast lane; eval form unchanged and sealed)

Change (one): arm C = arm B (never-repeating stream) plus a direct copy path: the frozen LM's own embedding of the
calculator's result token (zeros if the call was invalid) is added as a 9th prefix vector, next to the 8 pooled ones.
Compared with arm B re-run (pooled exit only). Same eval form, same 3000 x 16 updates, lr 1e-3, seeds 0 and 1.

PASS (both seeds): C unseen-answer final accuracy >= 50%; C beats the B re-run by >= 25 points; C unseen >= 70% of C seen;
C seen accuracy not more than 5 points below B re-run seen.
FALSIFIED: C unseen <= 15% on both seeds (copy path alone does not remove the lookup).
Between: partial, no claim. Per-question rows are copied back and counted (192 per run) before the box is destroyed.
Note: with the result handed over directly, accuracy is bounded by the right-call rate (~90% in the first test), so
'seen' and 'unseen' should both land near it if copying works.
