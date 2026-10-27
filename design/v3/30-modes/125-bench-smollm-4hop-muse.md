# Doc 125 — same-metric bench: borrowed SmolLM2-360M vs the joined-up agent (Muse)

## Why this comparison exists

The demo needs one honest table: the borrowed 360M model (our exp-66
baseline, run exactly as in exp 66) against our joined-up notebook agent,
on both splits, graded by one scorer. Before this, the two sides were
scored by different scorers on different splits — any gap could be
scoring artefact. Exp 125 removes that: scorer v2 everywhere.

## Design (additive only; nothing existing edited)

- New script `scripts/fable_bench125_run.py` (prefix `fable_bench125_`).
  It vendors scorer v2 verbatim from `scripts/fable_bench113_run.py`
  (`classify_v2`, `extract_answer`, `norm`, abstain list) and reuses the
  prompt/decoding contract from `scripts/fable_bench66_baselines.py`
  (`build_prompt`, `bm25_top3`, `greedy_answer`, same system line, same
  greedy <= 16 tokens, same seed). Both source files are imported or
  copied-from, never modified.
- Fable-Edit-200 SmolLM2 cells are re-scores of exp 66's saved answer
  strings — no model re-run, so no run-to-run noise on that split.
- Fresh 4-hop SmolLM2 cells are new model runs with
  `local_files_only=True` (the SmolLM2 snapshot was already in the local
  HF cache; the run works fully offline, no downloads).
- Loop cells are aggregates read from the sealed exp-113/113b row JSONs.
- PASSMARKS.md sealed (`SEAL.sha256.txt`) and ledger block P125.1–P125.6
  appended before the registered run.

## What the scorer does to a general model (known upfront, stated in the seal)

Scorer v2 was built for loop replies. Its abstain detector is the loop's
own decline/clarify wording on word boundaries. SmolLM2 was instructed
(by the exp-66 system line) to say "unknown" — which is not in that
list — and abstain items carry empty gold lists, so exact match is
impossible there. Consequence, predicted before running: ~0 abstains for
SmolLM2, with every hedged reply counted wrong. The table should be read
with that asymmetry in mind; it is the price of "one scorer", applied
without favour.

## Results in one paragraph

On Fable-Edit-200: loops 200/200 right behaviour with 0 wrong;
SmolLM2 in-context 52 exact / 148 wrong, RAG-lite 41/159. On fresh
4-hop: loop113/b 145 correct / 50 abstain / 5 wrong; SmolLM2 in-context
52/0/148, RAG-lite 33/0/167. Retrieval helps nothing here: top-3 BM25
over 8-sentence 4-hop items drops bridge facts, so RAG-lite trails
in-context on both splits.

## Two caveats that keep the claims honest

1. C1 failed (52 vs 67, diff -15): v2 "correct" on free text is
   stricter than "mentions gold". The gap between exact and
   contains-gold (15 on the in-context arm) is mostly answers that name
   the gold alongside extra words, or answer a bridge entity instead of
   the question. Same-scorer does not mean same-difficulty across model
   families.
2. SmolLM2's 52/200 on 4-hop matches its 52/200 on Fable-Edit exactly,
   despite 4 hops being structurally harder. The 4-hop split uses
   celebrity entities (Derek Shepherd, The Beatles), so part of that 52
   is likely pretraining memory answering directly, bypassing the taught
   chain. This bench does not separate taught-vs-known for the borrowed
   model; the agent side is clean by construction (empty notebook).

## Ledger scorecard

P125.1 TRUE (52 in [44,64]). P125.2 TRUE (41 in [30,50]). P125.3 FALSE
(52 vs band [8,35] — under-predicted; the model is better at 4-hop
guessing than I credited). P125.4 FALSE (33 vs [4,25] — same reason).
P125.5 TRUE-as-forecast (C1 fails as I expected at p 0.30 for holding).
P125.6 TRUE (727 s < 1800 s). Brier sum ≈ 0.09+0.16+0.25+0.25+0.09+0.0025.

## What it means / what it does not mean

Same questions, same scorer: the purpose-built notebook agent answers or
abstains honestly on both splits (0 wrong on Fable-Edit, 5 wrong on fresh
4-hop), while the borrowed general model guesses often and abstains never
(under this scorer). It does not mean the agent is "smarter" in general:
this is the agent's home turf (taught facts + hop loop), a 360M model is
not a frontier model, and pretraining leakage flatters the 4-hop column.
