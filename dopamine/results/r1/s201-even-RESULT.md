# Domain run analysis: sheet seed 201

- Run: `/mnt/project-files/dopamine/r1/sheet-s201-even`
- Parent: `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s201/T1SDR_s201/checkpoint.pt`
- Final: `/mnt/project-files/dopamine/r1/sheet-s201-even/night_8/checkpoint.pt` (night 8, stop: fixed_nights_control)
- One seed only (seed 201). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +55.95 pts (0.95 -> 56.90) | pass >= +30; proved wrong < +10 (seed 201, one seed only) | PASS |
| DM2 far, scored kinds (After minus Before) | +0.71 pts (0.36 -> 1.07) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 201, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.00 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS (by construction: add-on off outside its tool) |
| DM4 audit and constants | rows 9914, panel overlap 0, decontam dropped 0 by kind {}, zero-step 0, bad source 0; audit exit 0; constants hash match True | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PASS |
| DM5 stop night N=8 | score(N) 56.90, best 56.90 (night 8), rise over last night +8.33 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PROVED WRONG |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: yes; DM2 met: no.
- DM3 detail: in_dist 90.88 -> 80.88; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (yes). Checked by event type only.
- Learned (summary, reported): []. Not learned: ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 0.95 |  |
| 1 | 20.48 | +19.52 |
| 2 | 30.00 | +9.52 |
| 3 | 37.38 | +7.38 |
| 4 | 41.19 | +3.81 |
| 5 | 49.52 | +8.33 |
| 6 | 46.90 | -2.62 |
| 7 | 48.57 | +1.67 |
| 8 | 56.90 | +8.33 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 1.67 -> 50.00 | 0.00 -> 0.00 | 0.00 -> 53.85 | 10.00% | 69 | 0 | 140 / 452 |
| MAX | yes | 0.00 -> 75.00 | 0.00 -> 2.50 | 3.85 -> 73.08 | 10.00% | 80 | 0 | 138 / 423 |
| MIN | yes | 1.67 -> 78.33 | 2.50 -> 2.50 | 3.85 -> 73.08 | 10.00% | 67 | 0 | 131 / 431 |
| PRODUCT | yes | 0.00 -> 43.33 | 0.00 -> 0.00 | 0.00 -> 65.38 | 10.00% | 72 | 0 | 122 / 431 |
| cell arithmetic | yes | 0.00 -> 41.67 | 0.00 -> 0.00 | 0.00 -> 57.69 | 10.00% | 196 | 0 | 15 / 1583 |
| division | yes | 1.67 -> 63.33 | 0.00 -> 2.50 | 0.00 -> 76.92 | 10.00% | 67 | 0 | 158 / 312 |
| MOD | no (A2) | 1.67 -> 13.33 | 0.00 -> 0.00 | 4.00 -> 4.00 | 10.00% | 189 | 0 | 0 / 0 |
| ABS | yes | 1.67 -> 46.67 | 0.00 -> 0.00 | 4.00 -> 60.00 | 10.00% | 170 | 0 | 317 / 1165 |
| COUNTIF | no (A2) | 0.00 -> 1.67 | 0.00 -> 2.50 | 0.00 -> 8.00 | 10.00% | 109 | 0 | 0 / 0 |
| IF | no (A2) | 0.00 -> 5.00 | 0.00 -> 5.00 | 0.00 -> 16.00 | 10.00% | 5 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.8389.
- R3 wasted practice: 0.0% of the last day's mix went to kinds whose own quiz never rose above night 0: none.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- undone nights: none (the check events in the log hold each night's drop)
