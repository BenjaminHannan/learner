# bench66 RESULTS — Fable-Edit-200 baselines (SmolLM2-360M-Instruct, 2026-09-22)

**Result first:** the baseline model is weak on exactly the abilities the
notebook claims. In-context exact match 53/200 (26.5%); RAG-lite 38/150 on
answerable items vs in-context 52/150. Abstention is poor: 43 of 50 abstain
items were answered with a confident wrong string in BOTH prompt arms. The
fine-tune arm (last 2 blocks + lm_head, 20 steps, cut to first 60 items as
pre-registered) installed nothing: 1/60 correct on mquake2hop. Marks:
K1 PASS, K2 PASS, K3 PASS (25.1 min), K4 PASS.

## Setup

Model HuggingFaceTB/SmolLM2-360M-Instruct (Apache-2.0, cached), Mac CPU,
OMP_NUM_THREADS=1, seed 6601, greedy decode ≤ 16 new tokens. Data:
`data/open/bench65/fable_edit_200.jsonl` (100 mquake-twohop, 50 reversal,
25 abstain-absent, 25 abstain-broken), fed the ORIGINAL English sentences
from `taught[].sentence_en`. Gold (+ aliases) used only for scoring, never
in a prompt or training text.

## Table: arms × types (correct / abstain / wrong, n)

| arm | mquake2hop (n=100) | reversal (n=50) | abstain_unknown (n=25) | abstain_broken (n=25) |
|---|---|---|---|---|
| incontext | 34 / 3 / 63 | 18 / 1 / 31 | 0 / 3 / 22 | 0 / 4 / 21 |
| raglite | 26 / 4 / 70 | 12 / 1 / 37 | 0 / 3 / 22 | 0 / 4 / 21 |
| finetune (n=60 first items, all mquake2hop) | 1 / 8 / 51 (n=60) | not run | not run | not run |

Overall exact (answer items only): in-context 52/150, RAG-lite 38/150.
'Contains gold' (normalised substring, recorded separately): in-context 39
(two-hop) + 28 (reversal) of 150; raglite 34 + 24.

**Abstention wrong-answer counts (K2):** in-context 43/50, RAG-lite 43/50,
fine-tune 0 (only its first 60 items were mquake2hop, so no abstain item
reached it — the count is 0 because it saw none, not because it abstained).

## Marks

| mark | outcome |
|---|---|
| K1 integer counts per arm × type | PASS (table above; full JSON in results file) |
| K2 abstention wrong-answer count per arm | PASS (reported above) |
| K3 total wall < 45 min | PASS — 1504 s = 25.1 min |
| K4 no gold at inference | PASS — prompts and FT text built only from sentences + question; gold used only in scoring |

Predictions: P66.1 TRUE (26.5% ≤ 30%), P66.2 FALSE (RAG-lite 38/150 <
in-context 52/150 — the shorter prompt hurt), P66.3 FALSE (reversal 36%
in-context > 20%; the curse is weaker than forecast at 360M with both
sentences taught), P66.4 TRUE, P66.5 TRUE, P66.6 TRUE (fine-tune 1/60 ≤
in-context).

## Reading

- **Two-hop (mquake2hop):** 34/100 in-context. The model names a plausible
  entity but not the edited gold (contains-gold only 39/100): the edits are
  counterfactual and the pretrained prior wins. This is the gap the
  notebook's append-not-overwrite store is supposed to close.
- **Reversal:** 18/50 in-context, 12/50 RAG-lite — above chance, far below
  the notebook bar (50/50; both arms teach both directions, so this
  compares lookup symmetry with reading comprehension, not memory).
- **Abstention:** the striking failure — asked about a missing relation or
  broken chain, the model guesses 86% of the time.
- **Fine-tune:** 20 steps installed nothing QA-able (1/60). 20 steps × 200
  items projected 3503 s > the pre-registered 2400 s cut, so FT ran on the
  first 60 items only (fixed order, all mquake2hop — the first 60 of the
  file). Hence "not run" elsewhere.

## Deviations

- Script adapted to bench65's real schema on first sight (sentences from
  `taught[].sentence_en`, gold as list + aliases, type-name mapping);
  logic unchanged.
- 3-item timing/schema probe before the registered run (declared, unscored).
- Ledger collision: another agent's doc-66 experiment also used P66.x; our
  outcomes line is labelled "Outcomes 66 (bench66-baselines)".
- P66.2 and P66.3 FALSE, recorded as FALSE, not re-run.

## Reproduce

```
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  --with transformers python -B scripts/fable_bench66_baselines.py \
  --data data/open/bench65/fable_edit_200.jsonl \
  --out artifacts/fable-bench66-20260921/
```
(env: OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1; ≈ 25 min Mac CPU)

## What it means

This is the fair same-size baseline for bench65's notebook arm: a 360M
instruction model reading the same English sentences gets 34/100 on edited
two-hop questions, 18/50 on reversals, and guesses instead of abstaining on
43/50 unknowns — any notebook score materially above that, from triples, on
the same 200 items, is a real structural advantage, not a model-size
artifact.

## What it does not mean

It does not test the notebook (it never runs here), does not measure ears
(the notebook arm parses no English), and the fine-tune numbers cover only
the first 60 items at 20 steps — they do not show that gradient descent
cannot install facts with more steps or full fine-tuning. Low abstention
recall here is one small greedy decoder, not language models in general.
