# Domain run analysis: sheet seed 200

- Run: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/runs/sheet-s200-kf99n-kl30`
- Parent: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/parents/s200/checkpoint.pt`
- Final: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/runs/sheet-s200-kf99n-kl30/night_11/checkpoint.pt` (night 11, stop: quiz_rise_below_1_over_2_nights)
- One seed only (seed 200). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +63.10 pts (2.14 -> 65.24) | pass >= +30; proved wrong < +10 (seed 200, one seed only) | PASS |
| DM2 far, scored kinds (After minus Before) | -0.36 pts (1.07 -> 0.71) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 200, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.22 pts (fired: none) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | PASS |
| DM4 audit and constants | rows ?, panel overlap ?, decontam dropped n/a (v1) by kind n/a, zero-step ?, bad source ?; audit exit None; constants hash match False | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PROVED WRONG |
| DM5 stop night N=11 | score(N) 65.24, best 65.24 (night 11), rise over last night +0.71 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PASS |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: yes; DM2 met: no.
- DM3 detail: in_dist 90.22 -> 90.00; harm.py pass = True.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (yes). Checked by event type only.
- Learned (summary, reported): ['MAX', 'PRODUCT', 'cell arithmetic', 'division']. Not learned: ['SUM', 'MIN', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 2.14 |  |
| 1 | 13.57 | +11.43 |
| 2 | 22.62 | +9.05 |
| 3 | 35.95 | +13.33 |
| 4 | 42.62 | +6.67 |
| 5 | 50.24 | +7.62 |
| 6 | 53.10 | +2.86 |
| 7 | 58.10 | +5.00 |
| 8 | 61.19 | +3.10 |
| 9 | 63.57 | +2.38 |
| 10 | 64.52 | +0.95 |
| 11 | 65.24 | +0.71 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 0.00 -> 55.00 | 0.00 -> 0.00 | 3.85 -> 69.23 | 6.54% | 36 | 0 | 275 / 701 |
| MAX | yes | 1.67 -> 90.00 | 0.00 -> 2.50 | 11.54 -> 92.31 | 6.54% | 33 | 0 | 185 / 599 |
| MIN | yes | 13.33 -> 85.00 | 5.00 -> 2.50 | 19.23 -> 73.08 | 1.00% | 7 | 0 | 126 / 556 |
| PRODUCT | yes | 0.00 -> 56.67 | 0.00 -> 0.00 | 3.85 -> 80.77 | 23.17% | 151 | 0 | 286 / 689 |
| cell arithmetic | yes | 0.00 -> 60.00 | 0.00 -> 0.00 | 0.00 -> 84.62 | 17.63% | 332 | 0 | 36 / 2942 |
| division | yes | 0.00 -> 61.67 | 2.50 -> 0.00 | 15.38 -> 84.62 | 6.54% | 34 | 0 | 290 / 424 |
| MOD | no (A2) | 10.00 -> 6.67 | 2.50 -> 2.50 | 8.00 -> 8.00 | 1.00% | 18 | 0 | 0 / 0 |
| ABS | yes | 0.00 -> 48.33 | 0.00 -> 0.00 | 0.00 -> 68.00 | 18.29% | 288 | 0 | 310 / 2268 |
| COUNTIF | no (A2) | 6.67 -> 0.00 | 0.00 -> 0.00 | 20.00 -> 8.00 | 12.53% | 121 | 0 | 0 / 0 |
| IF | no (A2) | 6.67 -> 16.67 | 7.50 -> 0.00 | 4.00 -> 16.00 | 6.76% | 4 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.9207.
- R3 wasted practice: 12.53% of the last day's mix went to kinds whose own quiz never rose above night 0: COUNTIF.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- DM4 audit could not run: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/offline/panel/rpn.v2.jsonl'
- undone nights: none (the check events in the log hold each night's drop)
