# Sleep-1: can a night of premonition-style sleep teach Qwen new facts? (pre-registration, 2026-10-24 ~00:15Z)

Labels: shown / suggested / untested. Not the village model, not the card experiments: this is the borrowed Qwen
model on its own. Ben's direction (2026-10-23 23:57Z): apply premonition's ideas to Qwen3.8-27B instead of training
Qwen on our quiz tasks. Prototype on Qwen/Qwen3.5-2B (same architecture and tokenizer as the 27B), then 27B.

## Question
A plain LLM forgets everything taught in a chat when the chat ends. Premonition's sleep should turn a day's teaching
into lasting, usable knowledge without damaging old skills. Does it, and does it beat a plain fine-tune on the
same facts?

## Data (code-generated, fictional names only, fixed seed 0)
- 60 fictional people/places in chains, giving 120 taught facts over 6 relations (e.g. "X's mentor is Y",
  "Y lives in Z"). Each fact is taught once, in one fixed sentence (the "day").
- Tests, never trained on in any arm, asked with the facts NOT in context:
  - forward: the fact asked with a question wording not used in teaching (120 items);
  - reverse: asked from the other side, using each relation's inverse (120 items);
  - two-hop: questions that chain two taught facts (60 items).
- Old skills: ARC-Easy (first 500 test questions, multiple choice scored by answer-letter log-likelihood).

## Arms (one change between neighbours)
- S0 base, no facts in context (floor; should be near 0).
- IC base, facts pasted in context (ceiling for "knows the facts").
- S1 plain fine-tune: LoRA on the 120 teaching sentences only (same steps, lr, rank as S2).
- S2 premonition sleep: S1's teaching sentences, plus "dreams". The model, with the day's facts in its context,
  writes paraphrases and questions with answers about them (both directions). It then answers each of its own
  questions again with the facts in context, and only pairs whose answer matches the source fact are kept. LoRA
  trains on the kept pairs, with a KL guard: replayed general prompts keep the model close to the pre-sleep model's
  outputs. No test question or test wording is ever shown to the dreamer.
- Gate (reported, not an arm): S2's LoRA is kept only if ARC-Easy drops <= 2 points.

## Pass marks (fixed now)
- M1 recall: S2 forward >= 70% AND S2 >= S1 + 15 points.
- M2 reversal: S2 reverse >= 40% (plain fine-tunes are known to fail reversal).
- M3 two-hop: S2 >= S1 + 10 points.
- M4 old skills: S2 ARC-Easy >= base - 2.0 points.
**Wrong if** S2 <= S1 on forward and reverse (the dreams add nothing over a plain fine-tune), or S2 loses
more than 5 ARC-Easy points (the sleep damages the model).

Scoring: greedy answer, correct if it contains the target name (names are unique invented words). One seed.
Budget: one Vast A100 run, cap $4.
