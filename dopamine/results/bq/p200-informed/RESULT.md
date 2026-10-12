# Domain run analysis: sheet seed 310

- Run: `/tmp/claude-0/bq/runs/sheet-p200-s310-informed`
- Parent: `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt`
- Final: `/tmp/claude-0/bq/runs/sheet-p200-s310-informed/night_8/checkpoint.pt` (night 8, stop: nights_reached)
- One seed only (seed 310). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +25.95 pts (2.14 -> 28.10) | pass >= +30; proved wrong < +10 (seed 310, one seed only) | FAIL |
| DM2 far, scored kinds (After minus Before) | -1.07 pts (1.07 -> 0.00) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 310, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.00 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS (by construction: add-on off outside its tool) |
| DM4 audit and constants | rows 6144, panel overlap 0, decontam dropped 0 by kind {}, zero-step 0, bad source 0; audit exit 0; constants hash match True | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PASS |
| DM5 stop night N=8 | score(N) 28.10, best 28.10 (night 8), rise over last night +3.81 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | FAIL |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: no; DM2 met: no.
- DM3 detail: in_dist 90.22 -> 82.65; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (no, unknown: motivator_day). Checked by event type only.
- Learned (summary, reported): []. Not learned: ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 2.14 |  |
| 1 | 7.38 | +5.24 |
| 2 | 10.71 | +3.33 |
| 3 | 15.24 | +4.52 |
| 4 | 17.86 | +2.62 |
| 5 | 15.00 | -2.86 |
| 6 | 24.76 | +9.76 |
| 7 | 24.29 | -0.48 |
| 8 | 28.10 | +3.81 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 0.00 -> 23.33 | 0.00 -> 0.00 | 0.00 -> 38.46 | 14.29% | 24 | 0 | 7 / 175 |
| MAX | yes | 1.67 -> 68.33 | 0.00 -> 0.00 | 3.85 -> 69.23 | 14.29% | 24 | 0 | 11 / 169 |
| MIN | yes | 13.33 -> 48.33 | 5.00 -> 0.00 | 7.69 -> 57.69 | 14.29% | 23 | 0 | 6 / 170 |
| PRODUCT | yes | 0.00 -> 18.33 | 0.00 -> 0.00 | 3.85 -> 30.77 | 14.29% | 27 | 0 | 9 / 197 |
| cell arithmetic | yes | 0.00 -> 5.00 | 0.00 -> 0.00 | 0.00 -> 11.54 | 14.29% | 73 | 0 | 0 / 576 |
| division | yes | 0.00 -> 16.67 | 2.50 -> 0.00 | 7.69 -> 23.08 | 14.29% | 20 | 0 | 13 / 152 |
| MOD | no (A2) | 10.00 -> 6.67 | 2.50 -> 0.00 | 8.00 -> 12.00 | 0.00% | 0 | 0 | 0 / 0 |
| ABS | yes | 0.00 -> 16.67 | 0.00 -> 0.00 | 0.00 -> 24.00 | 14.29% | 65 | 0 | 19 / 544 |
| COUNTIF | no (A2) | 6.67 -> 0.00 | 0.00 -> 0.00 | 4.00 -> 8.00 | 0.00% | 0 | 0 | 0 / 0 |
| IF | no (A2) | 6.67 -> 15.00 | 7.50 -> 2.50 | 4.00 -> 4.00 | 0.00% | 0 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.924.
- R3 wasted practice: 0.0% of the last day's mix went to kinds whose own quiz never rose above night 0: none.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- log has event types outside the mode list: ['motivator_day']
- undone nights: none (the check events in the log hold each night's drop)
