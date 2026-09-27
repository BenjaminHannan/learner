# Canonical-operator variant `e0` — no supporting-line attention loss anywhere

Written 2026-09-20 EDT, before any `e0` run. Drafted by the build agent from Ben's brief.
**Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## Question

Does the canonical lookup learn from answers alone, once the scaled initialization and
the v3r learning-rate decay are in place? Every result so far has trained with
`premonition_token_evidence.loss_for`, i.e. answer cross-entropy **plus** 0.5 x a
supporting-line attention term that tells the model which memory line to read. That term
is a form of process supervision. If the lookup survives without it, the supervision was
scaffolding rather than the mechanism; if it collapses, the attention target is load
bearing and should be named as such in every claim.

## The ONE change versus v3r

The evidence term carries weight zero for all eight records per visit. Each record keeps
its answer cross-entropy, and the canonical/monolithic split stays at .75/.25 — which is
exactly the eight-record mean. Concretely the per-group loss becomes
`F.cross_entropy(model(x), targets.answer)` instead of `E.loss_for(model, x, y)[0]`.

The batch itself is untouched: `astra_canonical_operator.training_batch` is called
verbatim, so gold intermediate entities are still used to construct the LINK and terminal
records, and the evidence line indices are still computed and carried — they simply never
enter the loss. This is deliberately a loss-only ablation, so any difference from v3r is
attributable to the attention term and nothing else.

## Everything else is identical to v3r

Model, init, AdamW settings, clipping, lr-decay schedule, 6,000 updates, 16 visits per
update, `random.Random(1101)` consumed identically, the semantic overlap `forbidden`
check, eight records per visit, zero three-hop / 12-person / held-out-composition
training, final-checkpoint-only scoring of R and M on the same ten panels with the same
cutoffs, training cap 1,500 s, work/terminate deadlines 1,740/1,770 s, incomplete =
failed. No extra randomness is drawn, so the variant RNG is unused here.

## Predictions (score as written)

1. One-hop (c1) is close to v3r: the answer signal alone is enough for a single lookup.
2. The R policy on two-hop cells (c2, c3, c4, c5) is the discriminating measurement. If
   the attention term was scaffolding, c2 stays at or near v3r; if it was the mechanism,
   c2 falls well below its 487 cutoff and the native LINK diagnostics drop with it.
3. M stays below 128/512 on c3-c6 and s3 in every seed.
4. If e0 passes all ten cutoffs in all three seeds, the evidence term should be dropped
   from the main line and every past claim that relied on it re-read.

Success = R meets all ten cutoffs in every seed of wave 1 (seeds 0, 1, 2). Wave 2
(seeds 3, 4, 5) is reported the same way and never averaged with wave 1. A failure here
is informative, not a defect: it localizes the supervision the lookup depends on.

## Fable's amendments before freeze (2026-09-20 ~09:20 EDT, before any run)
Roster: seeds 0,1,2. Pass marks: Astra's ten cutoffs for R in every seed. Context (shown): Recipe A (answer-only, unscaled init, constant lr, monolithic questions only) reached ~9% even on one-hop; e0 differs from it by scaled init, lr decay and the canonical eight-record stream with gold intermediates.
Predictions: I expect e0 to FAIL (one-hop c1 below 487/512 in at least two seeds) — about 60% confidence; if it passes, the supporting-line loss was scaffolding and every later variant should drop it. Reading either way is about the evidence loss only; gold intermediates are still supplied here.
