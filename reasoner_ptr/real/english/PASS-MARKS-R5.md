# English, new kinds of question: pass marks (fixed 2026-10-04 before any training run)

Ask: coordinator relay 05:32 UTC 10-04. Test kinds of question that never appear in the generated practice: hold out whole families and/or write new kinds. Fix the split and marks before training, use 6 paired seeds, and use the same bare-LM 8-shot bar. Keep about $1 of vast credit in reserve.

## Two runs per seed (seeds 0 to 5), both the round-4 recipe
Both runs use allptr, 2000 updates of 16 rows, and `--gen 8000`.

- **full:** practice covers all six families, exactly as in round 4.
- **lofo (leave two families out):** `--drop-fams explicit_negation_with_positive_alternative,two_simple_relations_combined`. Those two families are removed from both the bank rows and the generator. They were chosen before training by `random.Random(20261005).sample(sorted(families), 2)`.

## Test sets
- **NEW-KINDS-R5.json** (sha256 eafb2a556ba8…): written for this round by a helper agent and checked by script. It has six new families never in any practice: counting_quantity, location_tracking, cause_reason, time_when, attribute_lookup and instrument_purpose. There are 8 passages per family and 2 questions each, asked of source_text and of the paraphrase, so 192 questions.
- **FRESH-EN-R3.json:** unchanged. Its 64 questions from the two dropped families are lofo's held-out-family test.

## Bare-LM bar
lm_fewshot is the frozen 1.2B instruct model with the same 8 bank examples as round 4, run once (deterministic). The 8 examples include one from each of the six old families and none of the new kinds. The bar is lm_fewshot's exact accuracy on the same questions.

## Judged A: full on NEW-KINDS (192 questions) against lm_fewshot on NEW-KINDS
- **PASS:** the lower bound of the 95% t-interval of (seed score − bar) is above 0 (df 5, t = 2.571).
- **FALSIFIED:** a mean below bar − 10.
- **In between:** anything else.

## Judged B: lofo on the 64 fresh questions of the two dropped families against lm_fewshot on those 64
- **PASS:** the lower bound of the interval of (seed score − bar) is above 0.
- **FALSIFIED:** a mean below bar − 10.
- **In between:** anything else.

## Read, not judged
- lofo − full on the 64 dropped-family questions, paired: the cost of never practising a kind.
- lofo − full on the other 128 fresh questions.
- full on FRESH compared with round 4, a reproducibility check.
- lofo on NEW-KINDS.
- "contains" accuracy.
- Per-family scores on NEW-KINDS.
- The share of wrong answers that are bank answers.
