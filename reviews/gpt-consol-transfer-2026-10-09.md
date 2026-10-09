# Prompt for GPT (web): why does a consolidation sleep improve old skills less than plain practice? (10-09)

Paste everything below the line. It stands alone; GPT cannot see the repo.

---

I am training a tiny program-writing model and need a second opinion on one result. Please label every claim **shown** (follows from the numbers below),
**suggested** (plausible, not shown) or **untested**. Keep to this small-model setting; do not generalise to large language models or to any other project. This is one of the small card/puzzle experiments; keep it separate from the larger "village" model, which is a different project and is not described here.

## The setup, in words

- The model is about 3.3M trained parameters: a reader, a small looped "thinker" and a talker. It answers by writing a short program that an outside calculator runs. It was trained on 200,000 "skills" rows from 34 families (arithmetic, lookups, short stories, rule-from-examples puzzles and so on).
- Before any sleep, each model goes through a fixed "parent build": a warm-up plus "stepping stone" training. Call the raw model B2 and the built model N.
- A **day**: N tries 896 practice questions of a new kind ("C2": examples like `21 -> 115; 16 -> 90; 14 -> 80. Now 27 -> ?`, from 5 rule kinds) 32 times each, at a sampling temperature it picks itself. Answers whose program fits every example are kept, about 180-360 per model, plus about 610-730 more found by a chain-search tool.
- The **sleep** ("fd"): 256 optimiser updates, fresh AdamW, peak lr 1e-3, warm-up then cosine. Each update has 1,024 rows. Half are **fresh dreams**: a found program is run on new inputs to write a new prompt, so no day row is ever read twice. The other half are **fresh skills rows**, also never repeated. The loss is a per-row mean over the whole batch. The model checks its own fit rate on 128 held practice questions every 32 updates and keeps its best checkpoint.
- The **control** ("rp"): the same 256 updates, schedule and optimiser, and exactly the same skills rows in the same order (512 per update), with the dream half removed. Batch 512, so each skills row carries twice the weight it has in the sleep's batch.

## Results (six models, s200-s205; skills = 6,800 held-out DEV rows, 200 per family; intervals are paired 95% bootstraps over rows)

| | B2 (raw) | N (built) | after sleep (fd) | control (rp) |
|---|---|---|---|---|
| C2 first try, holdout (512 questions) | - | - | 76.1% (71.3 to 78.3) | - |
| skills in_dist, mean of six | 90.16 | 87.87 | 88.39 | 89.98 |
| fewshot_number_rule | 35.5 | 15.2 | 17.8 | 36.3 |
| seq_next | 83.6 | 69.9 | 71.0 | 80.8 |
| rule_apply | 90.6 | 80.2 | 82.8 | 89.7 |

- fd - N in_dist, pooled over six models: +0.52 [0.31, 0.74]. No family drops by more than 5 points on any model.
- rp - N: +2.11 [1.88, 2.32]. fd - rp: -1.58 [-1.79, -1.37], below 0 on all six models.
- An earlier two-model screen at 128 updates gave the same picture: rp - N +1.26 / +1.68, fd - rp -1.01 / -1.21.
- Earlier work on the same models found that re-reading a small fixed set of 1,024 skills rows 16 times at lr 1e-3 hurt skills (-3.7 to -4.1 in_dist). The same number of updates on fresh rows helped (+1.8 to +2.3).

## Questions

1. Two explanations for fd - rp < 0: (a) **dilution**: in the sleep each skills row carries half the weight per step, so it is simply less practice; (b) **interference**: the dream half's gradients pull against the skills half, mostly on the rule-from-examples families that share a format with C2. Which do the numbers favour, and what single cheap experiment would tell them apart? (For example, a control with the dream half replaced by a second set of fresh skills rows at batch 1,024, against the sleep.)
2. The task asked for "old skills improve through transfer from the new skills". Is there any design that could show real backward transfer here, given that plain practice already repairs the parent build's damage? What control would make such a claim convincing?
3. What is the smallest change to the sleep that should keep the C2 gain (holdout at least 71.3%) AND bring skills in_dist back to B2's level, without breaking these rules: the model must run its sleep itself (no per-night human settings); no new teacher model; no answer-only training targets?

For each proposal, give **one change at a time**, its pass marks fixed in advance, and the result that would prove it wrong. End with a short plain-language summary that a high-school senior could follow.
