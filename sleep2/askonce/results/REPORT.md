# Ask once, then remember: result

| arm | H new | H know | H full | R all | silent | ask(full) | ask(know) | ask(general) | ARC | recall |
|---|---|---|---|---|---|---|---|---|---|---|
| P | 16.2 | 61.2 | 92.5 | 70.5 | 50.0 | 1.4 | 20.0 | 1.0 | 88.4 | 3.0 |
| A+ | 0.0 | 93.8 | 100.0 | 80.2 | 70.0 | 0.0 | 0.0 | 1.0 | 83.8 | 24.0 |
| B | 0.0 | 92.5 | 100.0 | 79.8 | 70.0 | 0.0 | 0.0 | 1.5 | 84.9 | 21.5 |
| B-sft | 0.0 | 93.1 | 100.0 | 80.2 | 75.0 | 0.0 | 0.0 | 1.0 | 85.0 | 22.0 |

| pass mark (B vs A+) | result | detail |
|---|---|---|
| 1 H new ambiguity: arm >= A+ + 8, p<0.05, positive in both seeds | FAIL | +0.0 pts, p=1.0, per seed [0.0, 0.0] |
| 2 R overall: arm >= A+ + 3 and ask-rate on fully specified <= A+ + 3 | FAIL | -0.5 pts (p=0.7266); ask on full 0.0 vs A+ 0.0 |
| 3 Knowable: arm >= A+ - 2 | PASS | -1.3 pts |
| 4 ARC within 1, recall within 2, general ask <= A+ + 3 | FAIL | ARC 84.9 vs 83.8; recall 21.5 vs 24.0; general ask 1.5 vs 1.0 |
| 5 B >= B-sft + 3 on new ambiguity | FAIL | +0.0 pts (p=1.0) |

| marks 1-4 for B-sft (vs A+) | result | detail |
|---|---|---|
| 1 H new ambiguity: arm >= A+ + 8, p<0.05, positive in both seeds | FAIL | +0.0 pts, p=1.0, per seed [0.0, 0.0] |
| 2 R overall: arm >= A+ + 3 and ask-rate on fully specified <= A+ + 3 | FAIL | +0.0 pts (p=1.0); ask on full 0.0 vs A+ 0.0 |
| 3 Knowable: arm >= A+ - 2 | PASS | -0.3 pts |
| 4 ARC within 1, recall within 2, general ask <= A+ + 3 | FAIL | ARC 85.0 vs 83.8; recall 22.0 vs 24.0; general ask 1.0 vs 1.0 |

Secondary: slot-clustered bootstrap 95% CI for B - A+ on new ambiguity: [+0.0, +0.0] points (20 slots).

Result that proves the idea wrong (any one): B <= A+ + 3 on new ambiguity: YES; B's Split R change < 0: YES; B more than 5 below A+ on knowable: no

All five marks hold for B: **False**. Decision under the prereg rule (B-sft replaces B when it also meets marks 1-4): **adopt none**. Diagnostic (A+ matches B everywhere, so the useful part is the memory, ship it without ask-training): True.
Adoption on a simulated world is provisional: the Step 0 gate on real logs (at least 5 events per night, tagger precision >= 0.8) must pass before any real-use decision.
Knowable eval items whose slot actually reached the memory (knowable_effective): 134 of 150 (marks use all of them).
Tagger on the simulated logs: precision 1.0, recall 0.944.

B slice share per night (the slice is sized on the median night, so it is not a fixed 15%; it is equal across arms):

| night | B slice share | pairs in B / available | regret dropped (memory had the answer) |
|---|---|---|---|
| 1 | 11.9% | 11 / 11 | 0 |
| 2 | 2.7% | 1 / 1 | 0 |
| 3 | 14.3% | 4 / 7 | 0 |
| 4 | 13.7% | 6 / 6 | 0 |
| 5 | 13.4% | 6 / 7 | 2 |

Per-night training trajectory for B (DPO margin should rise, anchor KL should stay small; skipped = fp16 loss-scale skips):

| seed | night | DPO margin | DPO acc | anchor KL | SFT loss | skipped |
|---|---|---|---|---|---|---|
| 1 | 1 | 0.78019 | 1.0 | 0.04941 | 2.37468 | 0 |
| 1 | 2 | 0.17872 | 1.0 | 0.07622 | 1.53406 | 0 |
| 1 | 3 | 0.36726 | 1.0 | 0.07912 | 1.26757 | 0 |
| 1 | 4 | 0.20269 | 0.66667 | 0.06683 | 1.22012 | 0 |
| 1 | 5 | 0.3166 | 0.66667 | 0.06597 | 1.10065 | 0 |
| 2 | 1 | 0.63123 | 0.90909 | 0.04762 | 2.35014 | 0 |
| 2 | 2 | 0.33071 | 1.0 | 0.07819 | 1.45804 | 0 |
| 2 | 3 | 0.47922 | 0.75 | 0.07677 | 1.21586 | 0 |
| 2 | 4 | 0.3274 | 0.66667 | 0.0653 | 1.16592 | 0 |
| 2 | 5 | 0.62902 | 0.66667 | 0.05901 | 1.06988 | 0 |

## In plain language (for Ben)

We trained the assistant overnight in a made-up world. One version practised asking a short question when it was about to guess (B), another version only studied your past answers more (A+), and a third copied the good questions without the practice step (B-sft). The test is whether practising to ask makes it better at spotting a brand-new 'Sam' it has never met, without nagging you on clear requests. It did not clear the marks, so we do not adopt it. A+ ties B almost everywhere, so the useful part is just the small note of your past answers: keep that, skip the ask-training. This is only a simulated world on one small model, so it says nothing yet about real use.
