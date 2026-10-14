# Domain run analysis: sheet seed 200

- Run: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/runs/screen-s200-NKsoft30-n3`
- Parent: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/parents/s200/checkpoint.pt`
- Final: `/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/local/runs/screen-s200-NKsoft30-n3/night_3/checkpoint.pt` (night 3, stop: max_nights)
- One seed only (seed 200). Seed-based bars say so.
- Scored kinds (7): SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS
- Unscored, A2 (run log deviation event (A2); ops ['cmp', 'mod']): MOD ['mod'], COUNTIF ['add', 'cmp', 'max'], IF ['add', 'cmp', 'max', 'mul', 'sub']

## Marks

| Mark | Value | Bar | Verdict |
|---|---|---|---|
| DM1 near, scored kinds (After minus Before) | +37.38 pts (2.14 -> 39.52) | pass >= +30; proved wrong < +10 (seed 200, one seed only) | PASS |
| DM2 far, scored kinds (After minus Before) | -0.71 pts (1.07 -> 0.36) | pass >= +10; "<= +2 on both seeds" is proved wrong (seed 200, one seed only) | FAIL (<= +2 on this seed: PROVED WRONG needs seed 201 also <= +2 (one seed only)) |
| DM3 harm: in_dist drop | +0.59 pts (fired: seq_next) | pass: in_dist drop <= 1.5 and no family fired; proved wrong: drop > 5 | FAIL |
| DM4 audit and constants | rows ?, panel overlap ?, decontam dropped n/a (v1) by kind n/a, zero-step ?, bad source ?; audit exit None; constants hash match False | pass: audit exits clean and log constants hash = domain/constants.json; FAIL: more than 2% of the run tool's panel rows also in training (dropped), or any zero-step or bad-source row; proved wrong: any row from a v1 panel, or a constants hash that differs from the file (per-domain setting) | PROVED WRONG |
| DM5 stop night N=3 | score(N) 39.52, best 39.52 (night 3), rise over last night +12.38 | pass: score(N) >= best - 3 and rise <= 3; proved wrong: rise > 5, or >= 4 nights past the best with DM3 not passing | PROVED WRONG |

- Ben's hair-miss rule (one question = 0.24 pts near, 0.36 pts far): DM1 met: yes; DM2 met: no.
- DM3 detail: in_dist 90.22 -> 89.63; harm.py pass = False.
- DM5 nights after the stop do not exist: "would it have kept rising" is not measured. Rise is the scored near score, not the quiz.
- DM4 also needs no person step in the log: every event type in the log is one the mode writes (yes). Checked by event type only.
- Learned (summary, reported): ['MIN']. Not learned: ['SUM', 'MAX', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF'].

## DM5 curve (scored near, pooled, percent)

| night | near | change |
|---|---|---|
| 0 (parent) | 2.14 |  |
| 1 | 16.90 | +14.76 |
| 2 | 27.14 | +10.24 |
| 3 | 39.52 | +12.38 |

## Per kind (undo rows: this kind's training rows from nights that were undone; try counts from the try events)

| kind | scored | near parent -> final | far parent -> final | own quiz night 0 -> last | last-day mix share | last-day kept | undo rows | try own / tool |
|---|---|---|---|---|---|---|---|---|
| SUM | yes | 0.00 -> 33.33 | 0.00 -> 0.00 | 3.85 -> 50.00 | 10.33% | 89 | 0 | 15 / 214 |
| MAX | yes | 1.67 -> 73.33 | 0.00 -> 0.00 | 11.54 -> 65.38 | 16.99% | 107 | 0 | 12 / 206 |
| MIN | yes | 13.33 -> 81.67 | 5.00 -> 0.00 | 19.23 -> 80.77 | 19.65% | 131 | 0 | 25 / 245 |
| PRODUCT | yes | 0.00 -> 25.00 | 0.00 -> 0.00 | 3.85 -> 50.00 | 11.66% | 98 | 0 | 22 / 199 |
| cell arithmetic | yes | 0.00 -> 11.67 | 0.00 -> 0.00 | 0.00 -> 38.46 | 7.66% | 158 | 0 | 1 / 569 |
| division | yes | 0.00 -> 35.00 | 2.50 -> 2.50 | 15.38 -> 42.31 | 10.33% | 72 | 0 | 11 / 193 |
| MOD | no (A2) | 10.00 -> 6.67 | 2.50 -> 2.50 | 8.00 -> 8.00 | 2.39% | 42 | 0 | 0 / 0 |
| ABS | yes | 0.00 -> 16.67 | 0.00 -> 0.00 | 0.00 -> 24.00 | 10.70% | 242 | 0 | 32 / 607 |
| COUNTIF | no (A2) | 6.67 -> 0.00 | 0.00 -> 2.50 | 20.00 -> 0.00 | 6.54% | 84 | 0 | 0 / 0 |
| IF | no (A2) | 6.67 -> 15.00 | 7.50 -> 2.50 | 4.00 -> 20.00 | 3.77% | 1 | 0 | 0 / 0 |

## A8 (reported, not gated)

- R2 self-knowledge (Spearman, 10 kinds, own final quiz vs panel near at the final night): 0.924.
- R3 wasted practice: 6.54% of the last day's mix went to kinds whose own quiz never rose above night 0: COUNTIF.
- R1 pick gain: not computed here (needs the even-mix control run).

## Notes

- DM4 audit could not run: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/offline/panel/rpn.v2.jsonl'
- undone nights: none (the check events in the log hold each night's drop)
