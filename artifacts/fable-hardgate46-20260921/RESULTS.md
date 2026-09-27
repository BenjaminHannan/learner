# Experiment 46 — results (two registered batches, seeds 4102–4106 and fresh 4107–4111; 3 words; 120 sleep runs)

Installs out of 15 per batch (every install: 60-start audit 0 disagreements, fresh accuracy 1.00):

| Wrong answers in 20 | batch 1 | batch 2 (fresh seeds) | Exp 45 robust (for reference) |
|---|---|---|---|
| 0 | 15 | 15 | 15 |
| 2 | 15 | 15 | 10 |
| 4 | 15 | 15 | 2 |
| 20 | 0 | 0 | 0 |

Wrong installs: 0 / 120. Marks: H1 PASS, H2 PASS, H3 PASS (both batches), H4 PASS (both batches), H5 PASS. Confirmed.

What it means: snapping the router to its single best chain before the install check removes Experiment 45's leftover
failures completely. A teacher who is wrong 1 time in 5 can still teach a new word from 20 examples, and nonsense is
still refused every time, with no wrong word ever installed.
What it does not mean: the 10% noise allowance in the loss was matched to the true noise (a wrong-rate sweep is a
separate experiment); 20 wrong of 20 is the only "nonsense" tested; the soft router before the snap may not scale to
100+ skills (GPT's warning); toy village, no language.
