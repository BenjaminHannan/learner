# Experiment 46 — pass marks (fixed before any registered run)

One change from Experiment 45's robust arm: after every fit (each CV fold and the refit) the router phi is snapped to
its single best chain BEFORE any prediction, score or agreement check. Gate (0.80 / 0.90), loss, optimiser, start,
checkpoints unchanged. Design pick + marks follow GPT xhigh's review (saved as gpt-design-review.md).
Batches judged separately: batch 1 = seeds 4102–4106; batch 2 (confirmation) = fresh seeds 4107–4111. 3 words each.
Wrong answers out of 20: exactly 0, 2, 4, 20.
Disclosed: throwaway seed 9999 installed 3/3 at 0, 2 and 4 wrong, 0/3 at 20 wrong, audit 0 disagreements.

Audit (evaluation only, not part of selection): every installed word is run from all 60 start people of the training
village and compared with the true word. "Wrong install" = installed AND (audit disagreements > 0 OR fresh accuracy < 0.99).

- H1 safety: zero wrong installs over all 120 cells (both batches). One = FAIL of the whole experiment.
- H2 clean: 15/15 installs at 0 wrong, per batch.
- H3 noisy: >= 12/15 installs at 2 wrong, per batch (the mark Experiment 45 failed at 10/15).
- H4 noisier: >= 8/15 installs at 4 wrong, per batch.
- H5 nonsense: 0/15 installs at 20 wrong, per batch.
- Recorded: per fold, whether the hardened chain equals the true chain (optimiser failures vs gate failures).

Reading rule: pass on batch 1 but not batch 2 = "not confirmed". H3 still failing with hardened folds at 0.65 means the
argmax chains themselves are wrong -> next single change is multi-start, not a weaker gate. Toy only; the 10% noise
allowance in the loss matched the true noise; hardening scales (one argmax per stage) but the soft router before it may not.
