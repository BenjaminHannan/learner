# Experiment 65 — results (2026-09-22): Fable-Edit-200, notebook arm (structured input)

**PASS, all four registered marks, no v2 needed.** PASSMARKS.md was written
and hashed (`SEAL.sha256.txt`, verified OK) before the run; ledger
predictions P65.1–P65.4 were appended before the run; data
`data/open/bench65/fable_edit_200.jsonl` (seed 6500, sha256
`71478e5f…af05`) was built by the previous shift and verified byte-identical
before this run. Selftest 3/3 PASS. One registered run, 0.2 s wall-clock.

This arm feeds TRIPLES, not English, because the ears are still in training
(rung 1 registered FAIL on coverage; rung 2 in progress).

## Marks (integer counts)

| Mark | Bar | Got | Verdict |
|------|-----|-----|---------|
| N1 MQuAKE two-hop | ≥ 90/100, ≤ 2 wrong | 100/100, 0 wrong, 0 MISS | PASS |
| N2 reversal (both directions) | 50/50 | 50/50, 0 wrong | PASS |
| N3 abstention | 50/50 abstain, 0 wrong | 50/50 abstain, 0 wrong | PASS |
| N4 wall-clock, Mac CPU | < 10 min | 0.2 s | PASS |

Per-type table (verdicts; abstain rows report `abstain_ok`):

| Type | n | correct / abstain_ok | wrong | MISS |
|------|---|----------------------|-------|------|
| mquake-twohop | 100 | 100 | 0 | 0 |
| reversal | 50 | 50 | 0 | 0 |
| abstain-absent | 25 | 25 | 0 | 0 |
| abstain-broken | 25 | 25 | 0 | 0 |

Reasoner–contract agreement: 200/200 (status identical to `Notebook.ask` on
every item). Max single-item latency 0.28 ms.

## Failure list

None — WRONG = 0, MISS = 0, so there is no verbatim failure to quote.

## One honest status-label note

Abstention verdicts were all non-OK (hence correct), but the labels split:
absent items → MISSING_FACT 12, UNKNOWN_ENTITY 13; broken-chain items → all
25 MISSING_FACT, never BROKEN_CHAIN (the untaught second-hop relation reads
as a missing fact at hop 2). The bar counted any non-OK status as abstain,
so the mark still passes; a future bar could require BROKEN_CHAIN exactly.

## Predictions (ledger, written before the run)

P65.1 TRUE (100/100, 0 wrong). P65.2 TRUE (50/50). P65.3 TRUE (50/50, 0
wrong). P65.4 TRUE (0.2 s). **4/4 TRUE.**

## Deviations

None from the sealed plan. One inherited note: TwoHopFact.csv was
downloaded and hash-recorded for licence verification but not sampled — the
200-item run is 100 MQuAKE + 50 reversal + 50 abstention, as specified.

## Reproduce

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench65_notebook_arm.py --run
```

## What it means

On structured input, the notebook installs a counterfactual edit so it
supersedes the original (append + correction), walks two hops through the
edited bridge entity, answers both directions of a fact symmetrically, and
abstains instead of guessing when a subject, relation, or chain link is
missing — 200/200 with zero wrong answers.

## What it does not mean

This is a structured-input arm only; it does not show English
understanding, because the triples bypass the ears. The English-input arm
awaits ears rung 2. It also does not compare against any baseline model —
that is experiment 66's job.
