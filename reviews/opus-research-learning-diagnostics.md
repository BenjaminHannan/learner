# Opus research handoff: locate D's learning bottleneck

> Superseded for execution by
> [milestone 2: answer path](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-execution-02-answer-path.md).
> Retained as research context. Do not add this prompt's runs to that milestone's
> training budget or begin a retrieval-first sweep.

You implement and run; Astra designs and reviews; Ben owns vision and spending.
Read design/research/2026-09-18-improvement-research.md and the current spec's
overriding sections. Apply this as an addendum to opus-execution-02-learning.md,
after the correctness milestone has been reviewed. Do not run two agents on
overlapping files. Preserve existing models, artifacts and originals.

This adds precision to the existing learning milestone, not an extra tuning
budget: at most two focused training adjustments and **30 minutes of training
total across that milestone**. Mac CPU/MPS only. No BensPC, rental, paid service,
credentials, or long-term architecture replacement. Explain findings to Ben in
simple language before the technical details.

## Start with measurements, not changes

1. On several fixed nondegenerate toy batches, differentiate the answer loss
   alone. Record gradient existence and norm for heads.query, writer.key,
   writer.value, reader and decoder. Inspect hard own-retrieval, with fixed
   random state. A scalar loss containing zero-weight auxiliary terms may give
   zero tensors where a direct answer-only backward gives None: distinguish
   absent paths, zero gradients and finite nonzero gradients. Ensure at least
   one retrieval is allowed; otherwise that diagnostic has a different cause.
2. Trace selected cards, actually inserted cards, ASK decisions, HALT decisions,
   and answer quality by loop. Existing answer(max_loops=K) still halts early;
   introduce an explicitly named fixed-loop diagnostic if needed. In current
   code, K loops have at most K−1 reads. Do not compare a zero-read one-loop run
   with a multi-read run and call the difference pure extra reasoning.
3. Compare gold-cards/fixed-loops, own-cards/fixed-loops, and own-cards/learned
   halting on the same evaluation visits. Treat gold as privileged diagnostic
   input; never feed it into a primary verdict. If ASK is forced, add a separate
   row rather than silently disabling two gates in one comparison.
4. Measure separate language-loss and answer-loss gradient sizes/directions on
   shared parameters. Toy filler is random; its next-token prediction may be
   wasted effort. Both losses are averaged, so do not assume token counts alone
   prove one dominates. Compare language-loss weights 1 and 0 only if this is
   one of the two chosen adjustments. Log computation even for zero-weight losses.

## Evidence-driven repair

Fix ordinary implementation bugs first. If discrete retrieval is the obstacle,
add the spec's D-soft variant separately. Use a differentiable weighted read
from only eligible previous cards plus NULL; prove answer errors reach query
and key projections. State the number of read rows, treatment of entity binding,
and what differs from D. Count changed parameters, FLOPs and actual time.
Keep a matched control for any change beyond the retrieval mechanism.

For an answer-only variant, do not merely set w_ask=0. Remove every dependence of
training behavior on gold evidence: card selection, early-answer loss scaling,
loop counts, stopping and any teacher-card path. A diagnostic may measure gold
recall afterward. Test that replacing/permuting gold metadata changes neither
training loss nor gradients with identical input, targets and random state.

The target remains ≥95% held-out toy accuracy, with fresh random bindings.
Evaluate D-noask and a cards-only intervention keeping names and reader state.
The recurrent reader may itself solve the toy: report that result honestly.
Never force D-noask to chance by withholding its permitted history.

If either adjustment fails within the budget, return the failure and hypothesis;
do not add more mechanisms or extend training. Run the existing bounded CPU
smoke after a repair and preserve all pass/fail results.

Return reviews/opus-research-learning-<unique-id>.md plus exact artifact paths,
commands, seeds, source hashes, changed files, gradients, learning curves,
read-only checks, and costs. Separate observed facts from explanations still
being tested. No rental cost; remaining lifetime cap unchanged.
