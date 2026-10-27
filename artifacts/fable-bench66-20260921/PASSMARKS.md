# bench66 PASSMARKS — sealed BEFORE the registered run (2026-09-22)

Baselines for Fable-Edit-200: HuggingFaceTB/SmolLM2-360M-Instruct (Apache-2.0),
Mac CPU only, OMP_NUM_THREADS=1. All three arms are fed the item's ORIGINAL
English sentences (never the gold answer at inference). Greedy decode, ≤ 16 new
tokens. n = min(200, items in data/open/bench65/fable_edit_200.jsonl); if that
file never appears, a 20-item synthetic stand-in with the same schema is used
(declared as a deviation).

These are predictions ABOUT the baseline (what we expect to observe), not bars
we want it to pass.

| id | sealed claim | falsified by |
|---|---|---|
| K1 | Every arm reports integer counts (correct / abstain / wrong) per type (mquake2hop, reversal, abstain_unknown, abstain_broken). | any arm × type cell missing or non-integer |
| K2 | Per-arm abstention wrong-answer count is reported (abstain items answered with a non-gold, non-abstaining string). | wrong-answer count missing for any arm |
| K3 | Total wall-clock for all three arms < 45 min. | run takes ≥ 45 min |
| K4 | No arm sees the gold answer at inference (prompts contain only teaching sentences + question; fine-tune touches only teaching sentences). | any prompt or training text contains the gold string |

Probabilistic forecasts (also appended to artifacts/fable-predictions-ledger.md
as P66.1–P66.6 before the run):

- P66.1: IN-CONTEXT overall exact-match ≤ 30%. p = 0.70.
- P66.2: RAG-lite exact-match ≥ IN-CONTEXT exact-match. p = 0.60.
- P66.3: reversal-type exact-match ≤ 20% in every arm. p = 0.75.
- P66.4: abstention recall < 100% in every arm (≥ 1 abstain item guessed, i.e. wrong-answer count > 0 in ≥ 1 arm). p = 0.80.
- P66.5: total wall-clock < 45 min (K3 holds). p = 0.85.
- P66.6: FINE-TUNE exact-match on mquake2hop ≤ IN-CONTEXT (20 steps on sentences does not install QA answers). p = 0.70.

Scoring rules (fixed): normalise = lowercase, strip articles/punctuation/extra
space. Correct = normalised gold == normalised answer (exact) — 'contains gold'
recorded separately. Abstain = answer contains 'unknown' / "i don't know" /
'not' AND contains no gold. WRONG = non-abstaining and not gold.

## What it means

If the run matches K1–K4, we have a complete, honestly-timed, leak-free
baseline table that bench65's notebook arm can be fairly compared against.

## What it does not mean

Sealing these marks proves nothing about the notebook or the model — they are
bookkeeping and forecasts about a baseline that has not run yet; a PASS here is
a completed measurement, not a capability claim.
