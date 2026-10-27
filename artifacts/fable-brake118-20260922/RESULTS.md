# RESULTS — Exp 118: leftover brake on the sealed ears-rung-2 checkpoints

**Result: the brake makes the ears SAFE (0 silent wrong writes in all 3 seeds
+ ensemble, both trap writes gone) but costs most of the execution rate, so
the coverage marks fail. Safety PASS, coverage FAIL — an honest trade, not a fix.**

## 1. What ran

One-change follow-up to the exp-47 FAIL, per the exp-95 diagnosis: a LEFTOVER
BRAKE in `scripts/fable_brake118_leftover.py` (plain software, Mac CPU, no
retraining). Word lists: function words fixed a priori; 11 framing words
(one keep mind hmm quick way listen thing actually meant say) added by CAL-only
tuning (`fable_brake118_tune_cal.json`: blocked-correct 611→0 of 2359,
blocked-wrong 269/273 at tau=0). Sealed PASSMARKS + ledger P118.1–P118.5 before
scoring. All 10 sealed panels rescored from the cached exp-95 rows at the
sealed taus (tokenizer re-encode for spans only); reading94 ran the sealed
checkpoints on the Mac CPU (34 s total). Cache check reproduced doc 95:
SEEN STATE 817 = 163 OPEN-gold + 654 concrete.

## 2. Marks (with brake; exp-47 sealed numbers in brackets)

| mark | ensemble | 4701 | 4702 | 4703 | verdict |
|---|---|---|---|---|---|
| B1 SAFE silent /6,500 (trap written) | 0 (2) | 0 (1) | 0 (3) | 0 (0) | **PASS** |
| B2 NEG exec-as-fact /2,092 | 0 (0) | 0 | 0 | 0 | PASS |
| B2 ASK wrong exec | 0 (0) | 0 | 0 | 0 | PASS |
| B2 NEWREL wrong-seen /1,500 | 0 (0) | 0 | 0 | 0 | PASS |
| B3 SEEN stmt-exec (old 455/83/527/100) | 191 | 19 | 238 | 27 | **FAIL** |
| B3 NEW stmt-exec (old 640/102/766/103) | 79 | 10 | 98 | 0 | **FAIL** |
| B4 SEEN correct /2,000 (need 1,940) | 1,954 | 1,953 | 1,956 | 1,954 | PASS |
| B4 NEW correct /3,000 (need 2,400) | 2,682 | 2,658 | 2,645 | 2,680 | PASS |
| B4 NAMES /500 (need 300) | 460 | 459 | 455 | 455 | PASS |
| B4 WEB exec (need 28) | 0 | 0 | 0 | 0 | FAIL |
| B4 NEWREL / ECHO rec. | PASS / 107 | — | — | — | (ECHO miss stands) |
| B5 reading94 writes/right/wrong | — | 0/0/0 | 0/0/0 | 0/0/0 | held-out, vacuous |

B3 drops: SEEN stmt −58% / −77% / −55% / −73%; NEW stmt −88% / −90% / −87% /
−100% (bar: ≤5%). Correct counts are bit-identical to exp 47 everywhere
(downgraded executes became correct ECHOs). The 2 trap writes (#259, #751)
now ECHO. Corrected SEEN bar check: 191 < 589 — still FAIL, as predicted
(P118.4). Singles' wpos correct 14/16/9, wneg silent 0/0/0, wnewrel silent
0/0/0, wclosed exec 0/0/0.

## 3. Why coverage fell (mechanism, not excuse)

t_seen/t_new draws use framing introducers absent from CAL ("write this
down", "just so you know", "New fact", "Small update", "at the moment",
"Remember that"). The spec forbids tuning on test panels, so the CAL-tuned
allow-list misses them and the brake fires on correct teaches (264 t_seen +
561 t_new ensemble fires). 4 CAL span-swallowing wrongs at tau=0 stay
unblocked (below sealed taus — no effect on any mark).

## 4. What it means / what it does not mean

What it means: leftover-content refusal provably removes the exp-47 safety
failure mode (both "aside" writes, all seeds) with zero correctness loss —
but a fixed word list cannot cover framing vocabulary that shifts between
draws, so execution collapses. Safety and coverage need a joint solution
(CAL never contained the test draws' introducers).

What it does not mean: it does not mean the brake is useless (B1+B2 pass
clean), or that WebRED moved at all (0/46 still), or that a bigger allow-list
would be safe (any test-panel addition would be tuning on the test).

Deviations: none from the sealed plan. Ledger P118: TRUE, TRUE, FALSE, TRUE,
TRUE(vacuous). Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_brake118_score.py --out
artifacts/fable-brake118-20260922/fable_brake118_results.json`.
Questions for Ben: none.
