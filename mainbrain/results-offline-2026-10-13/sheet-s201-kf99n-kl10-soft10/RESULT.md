# Domain run analysis: sheet seed 201

- Run: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/runs/sheet-s201-kf99n-kl10-soft10`
- Parent: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/parents/s201/checkpoint.pt`
- Final: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/runs/sheet-s201-kf99n-kl10-soft10/night_12/checkpoint.pt` (night 12, stop: max_nights)
- One seed only (seed 201). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +65.48 pts (0.95 -> 66.43) | pass >= +30; proved wrong < +10 (seed 201, one seed only) | PASS |
| DM2 far, scored kinds (After minus Before) | +1.79 pts (0.36 -> 2.14) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 201, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.96 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS |
| DM4 audit and constants | rows ?, panel overlap ?, decontam dropped n/a (v1) by kind n/a, zero-step ?, bad source ?; audit exit None; constants hash match False | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PROVED WRONG |
| DM5 stop night N=12 | score(N) 66.43, best 66.43 (night 12), rise over last night +2.14 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PASS |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: yes; DM2 met: no.
- DM3 detail: in_dist 90.88 -> 89.93; harm.py pass = True.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (yes). Checked by event type only.
- Learned (summary, reported): ['MAX', 'MIN', 'cell arithmetic', 'division', 'ABS']. Not learned: ['SUM', 'PRODUCT', 'MOD', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 0.95 |  |
| 1 | 11.67 | +10.71 |
| 2 | 25.24 | +13.57 |
| 3 | 37.86 | +12.62 |
| 4 | 47.38 | +9.52 |
| 5 | 53.81 | +6.43 |
| 6 | 53.33 | -0.48 |
| 7 | 52.14 | -1.19 |
| 8 | 55.71 | +3.57 |
| 9 | 64.05 | +8.33 |
| 10 | 64.29 | +0.24 |
| 11 | 64.29 | +0.00 |
| 12 | 66.43 | +2.14 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 1.67 -> 56.67 | 0.00 -> 0.00 | 0.00 -> 73.08 | 8.45% | 58 | 0 | 313 / 683 |
| MAX | yes | 0.00 -> 76.67 | 0.00 -> 5.00 | 3.85 -> 84.62 | 1.00% | 5 | 0 | 187 / 596 |
| MIN | yes | 1.67 -> 85.00 | 2.50 -> 7.50 | 0.00 -> 88.46 | 8.45% | 60 | 0 | 260 / 689 |
| PRODUCT | yes | 0.00 -> 65.00 | 0.00 -> 0.00 | 0.00 -> 69.23 | 8.45% | 53 | 0 | 336 / 653 |
| cell arithmetic | yes | 0.00 -> 75.00 | 0.00 -> 0.00 | 0.00 -> 84.62 | 30.80% | 670 | 0 | 52 / 3180 |
| division | yes | 1.67 -> 60.00 | 0.00 -> 2.50 | 0.00 -> 84.62 | 23.35% | 120 | 0 | 467 / 496 |
| MOD | no (A2) | 1.67 -> 6.67 | 0.00 -> 2.50 | 0.00 -> 12.00 | 1.00% | 20 | 0 | 0 / 0 |
| ABS | yes | 1.67 -> 46.67 | 0.00 -> 0.00 | 0.00 -> 84.00 | 1.00% | 23 | 0 | 320 / 2386 |
| COUNTIF | no (A2) | 0.00 -> 0.00 | 0.00 -> 2.50 | 0.00 -> 12.00 | 1.00% | 8 | 0 | 0 / 0 |
| IF | no (A2) | 0.00 -> 11.67 | 0.00 -> 10.00 | 4.00 -> 28.00 | 16.50% | 7 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.8863.
- R3 wasted practice: 0.0% of the last day's mix went to kinds whose own quiz never rose above night 0: none.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- DM4 audit could not run: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/offline/panel/rpn.v2.jsonl'
- undone nights: none (the check events in the log hold each night's drop)
