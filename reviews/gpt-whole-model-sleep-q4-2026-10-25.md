# Prompt for GPT (web): should nightly "sleep" change every weight a little, and how does that survive a 4-bit model? (2026-10-25)

You cannot see our code. Everything you need is below. Please answer as a careful ML researcher.

## Labels and rules for your answer
- Label every claim **shown** (you can point to a published result or to our numbers below), **suggested** (reasoned but not tested) or **untested**.
- Keep two things apart: (a) the sleep experiments below on small language models (2B to 4B), and (b) any claims about very large models or about how the brain works. Do not use (b) as evidence for (a).
- Propose **one change at a time**. For each change: the exact arm, the pass mark fixed in advance, and the result that would prove the idea wrong.
- End with a plain-language summary of at most 150 words for Ben, a high-school senior who leads the project.

## What the system does
A small local assistant keeps a diary of its chats. Each night a "sleep" job moves facts that keep coming up in the chats into the model's weights, so the model can answer from memory without searching the diary. The night:
1. A note-taker (the model itself, prompted) reads the day's chats and writes (subject, relation, object) notes. A second pass re-reads each chat for pairs of names that no note links yet and asks the model how they are related.
2. Only facts seen on 2 or more days, or marked important, are eligible.
3. "NREM": for each eligible fact the model writes paraphrases and question/answer pairs from the diary text (open book), and we train on them.
4. "REM": the model writes two-step questions that join two facts sharing a name (A works at B; B is in city C; so where does A work... which city), checked so that each kept question really needs both facts.
5. Training is LoRA rank 16 on every attention and MLP projection, with a KL penalty to the original model on generic prompts, then a "SHY" step that shrinks the adapter a little, and a morning gate that undoes the night if general knowledge (ARC-Easy, 100 questions) drops.
6. The diary stays as a searchable backup.
"Work scale" s multiplies the night's training steps and dream counts (s=4 is about 1,200 steps per night by night 3).

## Test world and scores
A synthetic week of chats (7 days, 264 facts, 656 questions). Recall = forward questions about facts mentioned on 2 days or 4 days (classes C2+C4, 200 questions), answered from the weights alone, no diary. Two-hop = 78 questions that need two facts joined. ARC-Easy (500) checks general knowledge. Paired tests are exact McNemar on the same questions. About 94% of C2+C4 facts are eligible for sleep at all (the note-taker's ceiling).

Qwen3.5-2B, Week-2 world:

| arm | recall C2+C4 | two-hop | ARC-Easy |
|---|---|---|---|
| control (LoRA, 1x work) | 53.0 | 2.6 | 93.6 |
| 2x work | 67.5 | | 93.0 |
| 4x work | 76.0 | 5.1 | 92.4 |
| 4x + names re-read | 88.0 / 89.5 (2 seeds) | | 92.6 / 91.6 |
| **adopted: 4x + names re-read + guided two-step dreams** | **91.5 / 91.0** (2 seeds) | **38.5 / 35.9** | 92.2 / 91.8 |

Earlier, Week-1 world (80 facts), one seed each, 1x work, same model:

| arm | recall C2+C4 | ARC-Easy | note |
|---|---|---|---|
| control (LoRA r16) | 56 | 92.4 | |
| 2x work (LoRA) | 66.5 | | |
| every weight trainable, lr 5e-6, same steps, same KL guard and gate | **63.5** | 92.4 | safe; diary reading kept (81 vs 82) |
| every weight trainable, lr 2e-5 | 57.5 | **82.2** | broke general knowledge and diary reading (47 vs 82) |
| only the 1.2% of weights most "tagged" by the night's gradients, lr 2e-5 | 53.5 | 92.0 | safe but no gain |
| every weight in rotating quarters of the layers | 8.5 | | broke |
| LoRA folded into the weights each morning | 51.5 | | |

## The question
Ben's idea: like the brain, sleep should change the whole model, just a little, rather than only an add-on. On Week-1 at 1x work, every-weight at lr 5e-6 beat the LoRA control by 7.5 points with no harm (one seed), but 2x LoRA work beat it (66.5), and it was never tested on top of the adopted recipe.

The deployed model runs 4-bit on a Mac (MLX affine 4-bit, group 64: per group of 64 weights, 16 levels between the group's min and max). A full-precision master would be trained at night and re-quantized to 4-bit each morning. A typical group's step between levels is about 1/15 of the group's range, and an lr 5e-6 night moves most weights by much less than one step. So most of a small whole-model change may round away, while the LoRA path keeps the adapter in 16-bit beside the 4-bit base (and our q4 tests train the adapter on the 4-bit base directly).

Please answer:
1. On top of the adopted recipe (which is near the 94% eligibility ceiling on recall), what could a whole-model small step add that LoRA cannot? Name the metric where you expect a gain (two-hop, reverse questions, updates to changed facts, capacity over many weeks, forgetting of older facts, general knowledge), and why. Label each.
2. Which form of "change everything a little" should be tested first: (a) every weight instead of LoRA at a small lr; (b) LoRA plus a small every-weight step; (c) LoRA each night, then fold a small fraction of it into the full-precision master each morning (a slow "systems consolidation" pathway); (d) something else.
3. How should it survive 4-bit deployment? Options we see: re-quantize from the master each morning and accept that small changes only show once they cross a level; quantization-aware training of the nightly change (straight-through estimator through the 4-bit quantizer) so the change is made of moves that survive rounding; stochastic rounding; keeping a small sparse full-precision delta beside the 4-bit weights. Which is most likely to work at 3-4B and 35B-A3B (mixture of experts) sizes, and what does each cost in memory on an 8 GB Mac?
4. Give one preregistered arm (exact change, pass marks fixed in advance, and the result that would prove it wrong) for the first test, sized for one RTX 5090 run of about 1-2 hours.
5. What published work is most relevant (continual learning with full fine-tuning vs LoRA, "LoRA learns less and forgets less", sleep-like consolidation in neural networks, quantization-aware fine-tuning)? Mark which you are sure exists.

End with the plain-language summary for Ben.
