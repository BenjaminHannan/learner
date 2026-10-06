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

## The chosen plan (please attack it)
"Teacher, then goodbye": keep our own thinker and use the 1.2B only during training.
- Student: our from-scratch design B2 (character reader with 2 conv layers, a looped controller that writes small
  programs for an exact calculator or copies words from the question, a copy talker). At 10.8M weights about 80% of
  it is the looped thinker (estimated from the code).
- Teacher data: the 1.2B writes one-sentence passages, a paraphrase and two questions in 60 question kinds (the 6
  kinds we already practise plus 54 new ones such as owner, helper, winner, fear, pronoun reference), then answers
  each question from the passage and from the paraphrase. Rows are kept only when both answers match and the answer
  appears in the passage. 200,000 rows. A script drops any row that touches the 12 held-out test kinds (counting,
  location, cause, time, attribute, instrument, speech, weather, price, direction, duration, origin) or their words.
- Control: the same student trained on 200,000 rows from our hand-written generator (6 kinds only), and a plain
  transformer of the same size trained on the teacher data.
- Marks fixed in advance (2 seeds, then 6): teacher-data student minus generator student on the 12 held-out kinds
  >= +15 points on both seeds (proved wrong below +5); feeding another question's thinker state drops it to <= 10%;
  B2 minus the plain transformer >= +3.
- Rejected alternative ("cut open"): keep the 1.2B's first 2 layers as reader and last 2 as talker, and loop its
  middle 12 layers as the thinker (as in McLeish et al. 2025, "retrofitted recurrence"). The thinker becomes 66% of
  the weights, but our own thinker is retired and the model is more borrowed, so the owner turned it down.

## What I want from you
1. Is "teacher, then goodbye" the right first move for this goal? What would you do instead, and why?
2. The biggest risk you see in the plan (for example: a 10.8M model cannot learn enough English from 200,000 short
   rows; 1.2B-written questions are too samey or too wrong; 60 kinds are still too few for transfer to new kinds).
3. One change at a time: propose at most three tests, each with pass marks fixed in advance and the result that would
   prove it wrong.
4. A plain-language summary (a few sentences) for a high-school senior.
