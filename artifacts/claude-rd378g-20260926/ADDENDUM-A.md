# Addendum (2026-09-26 18:14 UTC): the shared trainer gained one logging line; the new version is accepted

scripts/claude_lis300_train.py changed at f99793d78 (Reading facts, 17:15 UTC, asked by the Thread manager after the
torch autocast finding): after the first backward it counts the trainable weights with no gradient, prints the count and
writes it to summary.json as "grad_none_after_first_backward". Nothing else changed: same data loading, loss, optimizer,
schedule, clipping, saving and merge (checked in the diff 3316b3ba2..f99793d78). The count should be 0; a rental job
reports it. This file's seal records the new hash; it replaces the trainer's line in the earlier seal, and every other
line of the earlier seal still has to pass. No training had used the old version for this test.
