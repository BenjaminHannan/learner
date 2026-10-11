# Domain run analysis: sheet seed 200

- Run: `/mnt/project-files/dopamine/r1/sheet-s200-progress`
- Parent: `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt`
- Final: `/mnt/project-files/dopamine/r1/sheet-s200-progress/night_7/checkpoint.pt` (night 7, stop: nights_reached)
- One seed only (seed 200). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +45.00 pts (2.14 -> 47.14) | pass >= +30; proved wrong < +10 (seed 200, one seed only) | PASS |
| DM2 far, scored kinds (After minus Before) | -1.07 pts (1.07 -> 0.00) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 200, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.00 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS (by construction: add-on off outside its tool) |
| DM4 audit and constants | rows 9804, panel overlap 0, decontam dropped 0 by kind {}, zero-step 0, bad source 0; audit exit 0; constants hash match True | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PASS |
| DM5 stop night N=7 | score(N) 47.14, best 47.62 (night 6), rise over last night -0.48 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PASS |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: yes; DM2 met: no.
- DM3 detail: in_dist 90.22 -> 83.82; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (no, unknown: motivator_day, motivator_head, motivator_pick). Checked by event type only.
- Learned (summary, reported): ['MAX']. Not learned: ['SUM', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 2.14 |  |
| 1 | 17.86 | +15.71 |
| 2 | 27.62 | +9.76 |
| 3 | 35.00 | +7.38 |
| 4 | 40.95 | +5.95 |
| 5 | 46.19 | +5.24 |
| 6 | 47.62 | +1.43 |
| 7 | 47.14 | -0.48 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 0.00 -> 31.67 | 0.00 -> 0.00 | 3.85 -> 65.38 | 10.00% | 68 | 0 | 103 / 486 |
| MAX | yes | 1.67 -> 68.33 | 0.00 -> 0.00 | 3.85 -> 80.77 | 10.00% | 50 | 0 | 106 / 468 |
| MIN | yes | 13.33 -> 78.33 | 5.00 -> 0.00 | 3.85 -> 76.92 | 10.00% | 46 | 0 | 105 / 489 |
| PRODUCT | yes | 0.00 -> 48.33 | 0.00 -> 0.00 | 0.00 -> 61.54 | 10.00% | 70 | 0 | 64 / 486 |
| cell arithmetic | yes | 0.00 -> 38.33 | 0.00 -> 0.00 | 0.00 -> 53.85 | 10.00% | 295 | 0 | 7 / 1486 |
| division | yes | 0.00 -> 33.33 | 2.50 -> 0.00 | 23.08 -> 61.54 | 10.00% | 104 | 0 | 148 / 314 |
| MOD | no (A2) | 10.00 -> 6.67 | 2.50 -> 2.50 | 16.00 -> 20.00 | 10.00% | 148 | 0 | 0 / 0 |
| ABS | yes | 0.00 -> 31.67 | 0.00 -> 0.00 | 4.00 -> 52.00 | 10.00% | 197 | 0 | 254 / 1192 |
| COUNTIF | no (A2) | 6.67 -> 0.00 | 0.00 -> 0.00 | 4.00 -> 4.00 | 10.00% | 42 | 0 | 0 / 0 |
| IF | no (A2) | 6.67 -> 18.33 | 7.50 -> 10.00 | 4.00 -> 12.00 | 10.00% | 4 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.8598.
- R3 wasted practice: 10.0% of the last day's mix went to kinds whose own quiz never rose above night 0: COUNTIF.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- log has event types outside the mode list: ['motivator_day', 'motivator_head', 'motivator_pick']
- undone nights: none (the check events in the log hold each night's drop)
