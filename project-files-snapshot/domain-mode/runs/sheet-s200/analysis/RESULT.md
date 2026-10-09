# Domain run analysis: sheet seed 200

- Run: `/mnt/project-files/domain-mode/runs/sheet-s200`
- Parent: `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt`
- Final: `/mnt/project-files/domain-mode/runs/sheet-s200/night_7/checkpoint.pt` (night 7, stop: quiz_rise_below_1_over_2_nights)
- One seed only (seed 200). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | -0.48 pts (3.33 -> 2.86) | pass >= +30; proved wrong < +10 (seed 200, one seed only) | PROVED WRONG |
| DM2 far, scored kinds (After minus Before) | -0.71 pts (1.07 -> 0.36) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 200, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +2.06 pts (fired: passage_qa, seq_next) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | FAIL |
| DM4 audit and constants | rows 7996, panel overlap 0, zero-step 0, bad source 0; audit exit 0; constants hash match True | pass: audit exits clean and log constants hash = domain/constants.json; proved wrong: any panel row or a constants hash that differs from the file (per-domain setting) | PASS |
| DM5 stop night N=7 | score(N) 2.86, best 3.57 (night 4), rise over last night -0.24 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PASS |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: no; DM2 met: no.
- DM3 detail: in_dist 90.22 -> 88.16; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (yes). Checked by event type only.
- Learned (summary, reported): ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'ABS']. Not learned: ['MOD', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 3.33 |  |
| 1 | 3.33 | +0.00 |
| 2 | 2.14 | -1.19 |
| 3 | 3.33 | +1.19 |
| 4 | 3.57 | +0.24 |
| 5 | 3.33 | -0.24 |
| 6 | 3.10 | -0.24 |
| 7 | 2.86 | -0.24 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 0.00 -> 1.67 | 0.00 -> 0.00 | 0.00 -> 100.00 | 14.55% | 98 | 58 | 146 / 455 |
| MAX | yes | 3.33 -> 11.67 | 2.50 -> 0.00 | 3.85 -> 100.00 | 1.00% | 4 | 82 | 61 / 258 |
| MIN | yes | 11.67 -> 0.00 | 0.00 -> 0.00 | 15.38 -> 100.00 | 1.00% | 10 | 63 | 119 / 219 |
| PRODUCT | yes | 0.00 -> 0.00 | 2.50 -> 0.00 | 7.69 -> 100.00 | 28.11% | 210 | 57 | 234 / 528 |
| cell arithmetic | yes | 1.67 -> 1.67 | 0.00 -> 0.00 | 3.85 -> 100.00 | 1.00% | 16 | 191 | 25 / 1015 |
| division | yes | 5.00 -> 3.33 | 0.00 -> 2.50 | 23.08 -> 96.15 | 1.00% | 8 | 70 | 113 / 188 |
| MOD | no (A2) | 8.33 -> 1.67 | 5.00 -> 0.00 | 20.00 -> 12.00 | 22.14% | 508 | 0 | 0 / 0 |
| ABS | yes | 1.67 -> 1.67 | 2.50 -> 0.00 | 12.00 -> 100.00 | 1.00% | 21 | 193 | 31 / 508 |
| COUNTIF | no (A2) | 3.33 -> 0.00 | 0.00 -> 0.00 | 20.00 -> 4.00 | 8.05% | 91 | 0 | 0 / 0 |
| IF | no (A2) | 11.67 -> 3.33 | 12.50 -> 10.00 | 12.00 -> 20.00 | 22.14% | 58 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): -0.0179.
- R3 wasted practice: 8.05% of the last day's mix went to kinds whose own quiz never rose above night 0: COUNTIF.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- undone nights: [1] (the check events in the log hold each night's drop)
