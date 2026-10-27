# Experiment 65 — PASSMARKS (Fable-Edit-200, notebook arm, structured input)

Sealed before the registered run. Seed 6500. Data
`data/open/bench65/fable_edit_200.jsonl` (200 items: 100 MQuAKE-Remastered
CF-3k two-hop single-edit, 50 reversal ours-fictitious, 50 abstention
ours-fictitious). Arm feeds TRIPLES, not English, because the ears are still
in training (rung 1 registered FAIL on coverage; rung 2 in progress).

| Mark | Bar (integer counts) |
|------|----------------------|
| N1 MQuAKE two-hop | >= 90/100 correct, <= 2 wrong (rest MISS, never wrong) |
| N2 reversal | 50/50 correct, both directions |
| N3 abstention | 50/50 abstain, 0 wrong answers |
| N4 wall-clock | whole run < 10 min on Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 |

Scoring: exact match after normalisation (lowercase, strip punctuation,
collapse whitespace). Abstain = any non-OK status (MISSING_FACT /
BROKEN_CHAIN / UNKNOWN_ENTITY / AMBIGUOUS). WRONG = OK status with a value
outside the gold set. A registered FAIL stays a FAIL.

## What it means

If all four marks pass, the notebook + reasoner install a counterfactual
edit (append-then-supersede), walk two hops symmetrically, and abstain
structurally instead of guessing — on structured input.

## What it does not mean

It does not show English understanding: this arm bypasses the ears. The
English-input arm awaits ears rung 2.
