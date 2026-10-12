# Domain run analysis: sheet seed 310

- Run: `/tmp/claude-0/bq/runs/sheet-p200-s310-even-dp128`
- Parent: `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt`
- Final: `/tmp/claude-0/bq/runs/sheet-p200-s310-even-dp128/night_8/checkpoint.pt` (night 8, stop: nights_reached)
- One seed only (seed 310). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +12.38 pts (2.14 -> 14.52) | pass >= +30; proved wrong < +10 (seed 310, one seed only) | FAIL |
| DM2 far, scored kinds (After minus Before) | +0.00 pts (1.07 -> 1.07) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 310, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.00 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS (by construction: add-on off outside its tool) |
| DM4 audit and constants | rows 4816, panel overlap 0, decontam dropped 0 by kind {}, zero-step 0, bad source 0; audit exit 0; constants hash match True | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PASS |
| DM5 stop night N=8 | score(N) 14.52, best 14.52 (night 8), rise over last night +0.95 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PASS |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: no; DM2 met: no.
- DM3 detail: in_dist 90.22 -> 81.91; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (no, unknown: motivator_day). Checked by event type only.
- Learned (summary, reported): []. Not learned: ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 2.14 |  |
| 1 | 4.76 | +2.62 |
| 2 | 6.19 | +1.43 |
| 3 | 9.76 | +3.57 |
| 4 | 10.00 | +0.24 |
| 5 | 11.90 | +1.90 |
| 6 | 10.00 | -1.90 |
| 7 | 13.57 | +3.57 |
| 8 | 14.52 | +0.95 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 0.00 -> 0.00 | 0.00 -> 0.00 | 0.00 -> 3.85 | 10.00% | 6 | 0 | 1 / 58 |
| MAX | yes | 1.67 -> 26.67 | 0.00 -> 2.50 | 3.85 -> 30.77 | 10.00% | 9 | 0 | 0 / 69 |
| MIN | yes | 13.33 -> 36.67 | 5.00 -> 5.00 | 7.69 -> 42.31 | 10.00% | 9 | 0 | 2 / 86 |
| PRODUCT | yes | 0.00 -> 5.00 | 0.00 -> 0.00 | 3.85 -> 11.54 | 10.00% | 12 | 0 | 1 / 69 |
| cell arithmetic | yes | 0.00 -> 8.33 | 0.00 -> 0.00 | 0.00 -> 7.69 | 10.00% | 20 | 0 | 0 / 192 |
| division | yes | 0.00 -> 13.33 | 2.50 -> 0.00 | 7.69 -> 19.23 | 10.00% | 5 | 0 | 4 / 56 |
| MOD | no (A2) | 10.00 -> 6.67 | 2.50 -> 0.00 | 8.00 -> 8.00 | 10.00% | 27 | 0 | 0 / 0 |
| ABS | yes | 0.00 -> 11.67 | 0.00 -> 0.00 | 0.00 -> 4.00 | 10.00% | 30 | 0 | 5 / 177 |
| COUNTIF | no (A2) | 6.67 -> 0.00 | 0.00 -> 0.00 | 4.00 -> 0.00 | 10.00% | 9 | 0 | 0 / 0 |
| IF | no (A2) | 6.67 -> 11.67 | 7.50 -> 0.00 | 4.00 -> 12.00 | 10.00% | 1 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.8537.
- R3 wasted practice: 0.0% of the last day's mix went to kinds whose own quiz never rose above night 0: none.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- log has event types outside the mode list: ['motivator_day']
- undone nights: none (the check events in the log hold each night's drop)
