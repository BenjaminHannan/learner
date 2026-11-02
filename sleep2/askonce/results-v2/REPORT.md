# Ask once, then remember: result

**Gate (fixed before the run): passed.** A+ asks on 11.2% of H_new vs P 17.5% (gate: A+ >= 8.8%).

| arm | H new | H know | H full | R all | silent | ask(full) | ask(know) | ask(general) | ARC | recall |
|---|---|---|---|---|---|---|---|---|---|---|
| P | 16.2 | 61.2 | 92.5 | 71.0 | 50.0 | 1.4 | 20.0 | 1.0 | 88.4 | 3.0 |
| A+ | 10.0 | 93.1 | 98.8 | 80.5 | 62.5 | 1.8 | 1.7 | 1.5 | 83.9 | 19.0 |
| B | 0.6 | 94.4 | 100.0 | 80.8 | 65.0 | 0.0 | 0.0 | 1.0 | 85.2 | 21.0 |
| B-sft | 1.9 | 98.1 | 100.0 | 81.0 | 62.5 | 0.0 | 0.0 | 1.0 | 83.8 | 19.0 |

| pass mark (B vs A+) | result | detail |
|---|---|---|
| 1 H new ambiguity: arm >= A+ + 8, p<0.05, positive in both seeds | FAIL | -9.4 pts, p=0.0001, per seed [-3.8, -15.0] |
| 2 R overall: arm >= A+ + 3 and ask-rate on fully specified <= A+ + 3 | FAIL | +0.2 pts (p=1.0); ask on full 0.0 vs A+ 1.8 |
| 3 Knowable: arm >= A+ - 2 | PASS | +0.0 pts |
| 4 ARC within 1, recall within 2, general ask <= A+ + 3 | FAIL | ARC 85.2 vs 83.9; recall 21.0 vs 19.0; general ask 1.0 vs 1.5 |
| 5 B >= B-sft + 3 on new ambiguity | FAIL | -1.2 pts (p=0.5) |

| marks 1-4 for B-sft (vs A+) | result | detail |
|---|---|---|
| 1 H new ambiguity: arm >= A+ + 8, p<0.05, positive in both seeds | FAIL | -8.1 pts, p=0.001, per seed [-2.5, -13.8] |
| 2 R overall: arm >= A+ + 3 and ask-rate on fully specified <= A+ + 3 | FAIL | +0.5 pts (p=0.8036); ask on full 0.0 vs A+ 1.8 |
| 3 Knowable: arm >= A+ - 2 | PASS | +3.0 pts |
| 4 ARC within 1, recall within 2, general ask <= A+ + 3 | PASS | ARC 83.8 vs 83.9; recall 19.0 vs 19.0; general ask 1.0 vs 1.5 |

Secondary: slot-clustered bootstrap 95% CI for B - A+ on new ambiguity: [-16.9, -3.8] points (20 slots).

Result that proves the idea wrong (any one): B <= A+ + 3 on new ambiguity: YES; B's Split R change < 0: no; B more than 5 below A+ on knowable: no

All five marks hold for B: **False**. Decision under the prereg rule (B-sft replaces B when it also meets marks 1-4): **adopt none**. Diagnostic (A+ matches B everywhere, so the useful part is the memory, ship it without ask-training): False.
Adoption on a simulated world is provisional: the Step 0 gate on real logs (at least 5 events per night, tagger precision >= 0.8) must pass before any real-use decision.
Knowable eval items whose slot actually reached the memory (knowable_effective): 134 of 150 (marks use all of them).
Tagger on the simulated logs: precision 1.0, recall 0.944.

B slice share per night (the slice is sized on the median night, so it is not a fixed 15%; it is equal across arms):

| night | B slice share | pairs in B / available | regret dropped (memory had the answer) |
|---|---|---|---|
| 1 | 12.2% | 11 / 11 | 0 |
| 2 | 2.8% | 1 / 1 | 0 |
| 3 | 14.2% | 4 / 7 | 0 |
| 4 | 14.5% | 6 / 6 | 0 |
| 5 | 14.3% | 7 / 7 | 2 |

Per-night training trajectory for B (DPO margin should rise, anchor KL should stay small; skipped = fp16 loss-scale skips):

| seed | night | DPO margin | DPO acc | anchor KL | SFT loss | skipped |
|---|---|---|---|---|---|---|
| 1 | 1 | 0.90956 | 1.0 | 0.04893 | 2.27545 | 0 |
| 1 | 2 | 0.23624 | 1.0 | 0.07369 | 1.47287 | 0 |
| 1 | 3 | 0.56807 | 1.0 | 0.07198 | 1.30432 | 0 |
| 1 | 4 | -0.12319 | 0.16667 | 0.06302 | 1.20412 | 0 |
| 1 | 5 | 0.14482 | 0.71429 | 0.0605 | 1.10179 | 0 |
| 2 | 1 | 0.63128 | 0.81818 | 0.04374 | 2.25363 | 0 |
| 2 | 2 | 0.35412 | 1.0 | 0.07252 | 1.45758 | 0 |
| 2 | 3 | 0.19937 | 1.0 | 0.07634 | 1.25055 | 0 |
| 2 | 4 | 0.19226 | 0.33333 | 0.0567 | 1.21303 | 0 |
| 2 | 5 | -0.22478 | 0.14286 | 0.05146 | 1.10752 | 0 |

## In plain language (for Ben)

We trained the assistant overnight in a made-up world. One version practised asking a short question when it was about to guess (B), another version only studied your past answers more (A+), and a third copied the good questions without the practice step (B-sft). The test is whether practising to ask makes it better at spotting a brand-new 'Sam' it has never met, without nagging you on clear requests. It did not clear the marks, so we do not adopt it. This is only a simulated world on one small model, so it says nothing yet about real use.
