# Prompt for GPT (web): making the "thinker" the big part of a reader / thinker / talker model (2026-10-05)

Paste everything below the line into GPT. It cannot see the repo, so the prompt carries the numbers.

---

I am building a small question-answering model and want a second opinion on its architecture. Please label every
claim **shown** (you can point to a published result), **suggested** (reasoned) or **untested** (a guess). Keep the
two lines of work below separate: the "sandwich" model built around a borrowed language model, and the small
from-scratch models.

## Today's model (the sandwich)
- **Hearer/reader:** a frozen LiquidAI LFM2.5-1.2B-Instruct (1,170,340,608 weights: a 134M tied word table plus 16
  layers, 10 short-convolution layers and 6 attention layers, width 2048). It reads the question; we take its last
  hidden state for every question token.
- **Door + thinker:** a small projection (2048 -> 32 -> 256) and a ~9M-weight looped "core" (256 wide, 4 fixed
  rounds, mixture-of-experts feed-forward whose router never learns, so about 1.6M weights are live).
- **Talker:** the same frozen 1.2B again. It gets 8 vectors from the core, then every question word again, then
  writes the answer.
- So the thinker is under 1% of the weights and about 1-2% of the work (estimate).

## What we measured (all shown, 6 paired seeds unless noted)
| test | result |
|---|---|
| Today's model, practised question kinds written by people | 92.2% exact |
| Today's model, two sets of never-practised kinds (384 Qs) | 78.2% |
| Bare 1.2B with 8 examples, same sets | 75.0% practised; 67.7% and 77.6% on the two new-kind sets |
| Talker given only the core's vectors (no question words) | 18.9% overall (was 82.9%) |
| Talker given another question's core vectors, new kinds | 73.2%, same as with the right vectors (73.2%); 334 of 384 answers unchanged (1 seed) |
| Swap reader/talker for LFM2.5-350M | 66.1% vs 92.6% |
| Tiny copy-the-words talker instead of the LM | 13.6% on new kinds vs 78.2% (97.4% on practised kinds in generated wording) |
| Grow the core (fair scaling) | +1.9 points |
| Time to first answer token | 2.97x the bare LM at batch 1 |
| Separate from-scratch line, 3.3M weights, 2 seeds: thinker writes small programs, exact calculator runs them, copy talker | 73.7 vs 67.7 for a same-size transformer that writes worked steps (held-out splits of a synthetic skills set) |
| In the sandwich, a "plan route" (thinker picks numbers and ops, exact calculator computes) | 89.7% held-out over the 8 hardest families (chain questions 156 of 160); swapping plans between questions drops chain answers to 2-3 of 160, so the thinker decides them |

Reading: on new kinds the 1.2B talker answers by re-reading the question; the thinker barely matters there.

## The goal
The owner wants the thinker to be most of the model, with the reader and talker small parts that only read and
talk. Long run: nothing pretrained, and the whole model should beat 1-2B models at the same total size (the borrowed
LM counts toward size). Hardware: one RTX 5070 Ti (16 GB) and an M1 Pro laptop; short cloud rentals are possible.

## Our proposed plan (please attack it)
"Cut the big model open": reader = word table + layers 0-1, thinker = layers 2-13 run as a loop (2-3 rounds, with
the reader output joined back in each round through a learned adapter, as in McLeish et al. 2025 "retrofitted
recurrence"), talker = layers 14-15. One pass, so the talker only sees what came through the thinker. Thinker =
774M of 1,170M weights (66%), 86% of the layer passes at 2 rounds. Train only the thinker layers on our practice set
(8000 generated questions, 2000 updates of 16).
First test (no training): skip each layer, and repeat each layer, on 576 questions, to find where reading ends and
talking starts. Second test: the cut-open model vs today's model, marks fixed in advance (practised >= 89, new kinds
>= 75, thinker switched off <= 10%, first token <= 2.0x the bare LM).
Alternatives we ranked lower: distilling into a thinker-heavy student; building everything from scratch (fine at
3-100M, far too costly at 1B for us); growing the small core (+1.9 only).

## What I want from you
1. Is "cut open and loop the middle" the right first move for this goal? What would you do instead, and why?
2. The biggest risk you see in the plan (for example: a 2-layer talker cannot write answers without re-reading the
   question; looping a hybrid conv/attention model; 8000 examples being far too few to retrain 774M weights).
3. One change at a time: propose at most three tests, each with pass marks fixed in advance and the result that would
   prove it wrong.
4. A plain-language summary (a few sentences) for a high-school senior.
