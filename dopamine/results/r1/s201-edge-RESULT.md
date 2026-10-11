# Domain run analysis: sheet seed 201

- Run: `/mnt/project-files/dopamine/r1/sheet-s201-edge`
- Parent: `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s201/T1SDR_s201/checkpoint.pt`
- Final: `/mnt/project-files/dopamine/r1/sheet-s201-edge/night_8/checkpoint.pt` (night 8, stop: nights_reached)
- One seed only (seed 201). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +52.62 pts (0.95 -> 53.57) | pass >= +30; proved wrong < +10 (seed 201, one seed only) | PASS |
| DM2 far, scored kinds (After minus Before) | +0.71 pts (0.36 -> 1.07) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 201, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.00 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS (by construction: add-on off outside its tool) |
| DM4 audit and constants | rows 10241, panel overlap 0, decontam dropped 0 by kind {}, zero-step 0, bad source 0; audit exit 0; constants hash match True | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PASS |
| DM5 stop night N=8 | score(N) 53.57, best 53.57 (night 8), rise over last night +2.38 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PASS |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: yes; DM2 met: no.
- DM3 detail: in_dist 90.88 -> 81.99; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (no, unknown: motivator_day, motivator_head, motivator_pick). Checked by event type only.
- Learned (summary, reported): ['MAX', 'MIN']. Not learned: ['SUM', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 0.95 |  |
| 1 | 20.48 | +19.52 |
| 2 | 32.62 | +12.14 |
| 3 | 36.67 | +4.05 |
| 4 | 40.48 | +3.81 |
| 5 | 47.14 | +6.67 |
| 6 | 51.67 | +4.52 |
| 7 | 51.19 | -0.48 |
| 8 | 53.57 | +2.38 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 1.67 -> 48.33 | 0.00 -> 0.00 | 0.00 -> 65.38 | 10.00% | 62 | 0 | 123 / 444 |
| MAX | yes | 0.00 -> 83.33 | 0.00 -> 0.00 | 3.85 -> 88.46 | 10.00% | 79 | 0 | 120 / 538 |
| MIN | yes | 1.67 -> 73.33 | 2.50 -> 5.00 | 3.85 -> 92.31 | 10.00% | 68 | 0 | 142 / 472 |
| PRODUCT | yes | 0.00 -> 45.00 | 0.00 -> 0.00 | 0.00 -> 69.23 | 10.00% | 99 | 0 | 155 / 514 |
| cell arithmetic | yes | 0.00 -> 38.33 | 0.00 -> 0.00 | 0.00 -> 65.38 | 10.00% | 231 | 0 | 9 / 1465 |
| division | yes | 1.67 -> 45.00 | 0.00 -> 0.00 | 0.00 -> 73.08 | 10.00% | 55 | 0 | 204 / 341 |
| MOD | no (A2) | 1.67 -> 0.00 | 0.00 -> 0.00 | 4.00 -> 12.00 | 10.00% | 172 | 0 | 0 / 0 |
| ABS | yes | 1.67 -> 41.67 | 0.00 -> 2.50 | 4.00 -> 68.00 | 10.00% | 193 | 0 | 297 / 1321 |
| COUNTIF | no (A2) | 0.00 -> 0.00 | 0.00 -> 2.50 | 0.00 -> 4.00 | 10.00% | 61 | 0 | 0 / 0 |
| IF | no (A2) | 0.00 -> 3.33 | 0.00 -> 7.50 | 0.00 -> 4.00 | 10.00% | 4 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.862.
- R3 wasted practice: 0.0% of the last day's mix went to kinds whose own quiz never rose above night 0: none.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- log has event types outside the mode list: ['motivator_day', 'motivator_head', 'motivator_pick']
- undone nights: none (the check events in the log hold each night's drop)
