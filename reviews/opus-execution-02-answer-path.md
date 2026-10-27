# Opus milestone 2: reproduce and repair the answer path

Astra's current execution handoff. Ben has authorized Astra to manage this
Premonition conversation in Claude Desktop. You implement/run; Astra researches,
designs and reviews. Explain your conclusions to Ben in plain language first.

## Scope and precedence

Milestone 1 (`m01-20260918-202731`) is accepted for its input-cleaning and
identity safeguards on the submitted report, code review and stored probes;
Astra has not independently rerun its tests. Its full statistical verdict is
still unfinished. Report 108 tests total, one skipped, rather than 108 passes
plus a skip. The skipped learning gate is still a failure to solve, not a pass.
Keep repeated questions excluded from the primary score. They may be reported
separately later, without silently increasing independent sample counts.

This handoff supersedes the prioritization in `opus-execution-02-learning.md`
and `opus-research-learning-diagnostics.md`. Read the current spec, including
section 11, and `design/research/2026-09-18-trainer-handoff.md` before starting.
The earlier trainer reports correct-card retrieval at 100% but answers near
chance, including with correct cards supplied directly. Therefore debug the
answer path before new retrieval mechanisms, TST, halting or language-loss
sweeps. Those historical probes were not archived as runnable experiments;
their conclusions need reproduction, not blind acceptance.

Local Mac CPU/MPS only. No rental, BensPC or paid services. Maximum 30 minutes
TOTAL training for milestone 2, including baselines, probes, controls and
reruns; this replaces, rather than adds to, the earlier milestone-2 budget.
At most two focused experimental architecture adjustments. No unbounded tuning.
The separate conditional TST pilot is NOT activated by this message.
Preserve originals and all artifacts. Do not touch another agent's renderer,
pattern-bank or generator work. Freeze/copy the source and generated data needed
for your runs and hash them; do not compare moving versions between arms.

## First: turn the important old claims into reproducible evidence

Use a unique run ID, source manifest, exact commands, seeds and disjoint train /
validation / final-test episodes with freshly randomized fact bindings. Archive
the actual scripts, logs and checkpoint identities. Do not use the final test
to choose the repair. Use the v2 tokenizer for real village experiments;
explicitly label the toy's synthetic vocabulary as a diagnostic exception.

1. Reproduce baseline D with gold cards preloaded, fixed loops, answer loss
   only. Use the same input and answer path as D, with gold input explicitly
   diagnostic. Audit shifting, valid-row masks, target labels and finite
   gradients before interpreting an optimization failure. The historical
   simpler four-value/one-loop case is a useful fast first check.
2. Recreate the controlled bisection: real initial rows with an oracle clean
   card passed straight to Decoder, versus the same rows with one Think pass.
   All trainable modules, data order, initialization of shared weights and
   budgets must match. This clean-card experiment is privileged and cannot
   count as passing the ordinary D gate. Also evaluate normal writer-produced
   gold cards. Distinguish these two cases in every table.
3. Measure what survives at card value, pre-think row, post-think row, normalized
   decoder memory and cross-attention output. If fitting linear probes, use
   held-out episodes and state whether upstream weights are frozen. A probe
   finding decodable information does not prove the model uses it.
4. Measure valid-row centered spread, mean-row magnitude, pairwise similarity
   after the decoder's exact normalization, and answer sensitivity to card
   values. High raw norms or uniform attention alone do not prove collapse.
   For a causal diagnostic, change a fact's value with its entity/relation
   fixed and regenerate consistent inputs/targets; evaluate paired answers.
   An internal card-value swap is an additional off-distribution diagnostic,
   not a substitute for that consistent-input test.

If a plain implementation bug explains the failure, fix that first, preserve
the original, and use the remaining budget to verify. If the old failure does
not reproduce, report the changed conditions; do not force an architectural
explanation.

## Two focused adjustments, only if the reproduction supports them

Keep baseline D intact and give variants explicit names/config identities.
Choose these in order; stop early if evidence or the remaining budget warrants.

**1. D-think-gated:** gate the entire Think update, including its loop-step
embedding, with a learned scalar initialized at zero:

    output = input + alpha * (original_Think(input, step) - input)

This is a ReZero-inspired diagnostic adapted to our pre-normalized block,
not a claim to reproduce the original ReZero architecture or its guarantees.
Keep masks and invalid rows correct. At alpha=0 the update must be the identity;
gating only attention/MLP while leaving the shared step offset is not this test.
Check that alpha receives a useful gradient. Initially zero gradients in the
gated branch are expected; check whether learning opens the gate afterward.
Log gate values. Keep the original compute in cost accounting even at alpha=0.

**2. D-card-bypass (separate, not combined):** expose the existing pre-think
card rows to the decoder by replacing only the corresponding post-think card
rows; keep the same number of decoder-memory rows, other row types and mask.
No extra gold information, new slot/type identifier, extra rows or auxiliary
loss. This tests whether preserving the retrieved evidence fixes one-fact
answering. It is a diagnostic candidate, not an approved permanent design and
not evidence of multi-step reasoning. Do not combine it with gating in this
milestone. Count any compute differences.

Use common data and paired seeds for comparisons. Start with one development
seed; if a repair looks promising, use the remaining budget for a fresh seed
and untouched test set instead of more hyperparameter trials. Report all runs,
including failures. If time prevents completion, return an incomplete result.

## What counts as progress

First gate: at least 95% held-out accuracy with normal writer-produced gold
cards and fresh random bindings. This establishes usable supplied evidence,
not successful autonomous retrieval. Then, only within the same budget, test
own retrieval and free answer generation with documented ASK/HALT behavior.
Fixed-loop results and learned-halting results must stay separate; K loops
allow at most K-1 reads in the current implementation.

If own retrieval works, compare matched D-noask and a cards-only intervention
that preserves the reader state and name bindings. The recurrent reader sees
full history and may solve the toy itself. Do not force it to chance or claim
the store is necessary unless the causal controls support that conclusion.
Save exact counts and uncertainty, not just rounded percentages.

Run focused regression checks appropriate to any changes, plus the existing
bounded smoke if a usable repair is found. CLI expansion and additional
baselines from the earlier prompt may wait; do not let unrelated engineering
consume this diagnostic milestone. Keep `full_verdict: false` and the existing
read-only, label-free and checkpoint safeguards. No spec gates are weakened.

Return `reviews/opus-milestone-02-<run-id>.md`, with a short explanation for Ben,
the causal evidence and remaining alternatives, all artifact/command paths,
before/after/control metrics, exact training time, changed files, source/data
hashes, regression results and $0 rental cost. Append the decisions log.
STOP after this report for Astra's review; do not start TST or a rental.
