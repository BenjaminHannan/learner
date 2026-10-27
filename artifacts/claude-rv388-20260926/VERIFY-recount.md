# rv-388 blind recount (2026-09-26, read-only; no model, test or script run; no RESULTS/VERIFY file read)

## Seal
- `sha256sum -c SEAL.sha256.txt`: claude_rv388.py OK, claude_feas24.py OK, claude_feas24b.py OK, PASSMARKS.md OK, cuts.json OK.
- `git log 53d7a6489..HEAD` has 20+ commits, but none touches the 5 sealed files, SEAL.sha256.txt or the rv-388 folder
  (a path-filtered log is empty). `git status` shows no uncommitted change to them either.
- run/ is gitignored, so git does not record the raw output. File times (15:59 to 17:32) are after the 15:06 seal (weak evidence).

## 1. Counts (from per-hand rows; all match the log summary lines: solved, steps, flags, backs)
| seed   | END | JUDGE | PLACEBO | ORACLE | steps E / J / P / O          |
|--------|-----|-------|---------|--------|------------------------------|
| 388101 | 34  | 42    | 37      | 80     | 9739 / 8501 / 9115 / 1044    |
| 388202 | 28  | 35    | 33      | 80     | 10341 / 9181 / 9738 / 1200   |
Every log line has n 80, budget 160, practice false, cuts judge 0.0 and placebo -0.08326 (= cuts.json).

## 2. Validity: no failures
- All 640 rows: steps <= 160; every unsolved row used exactly 160; no unsolved path ends at 24.
- Within each seed all 4 arms have the same 80 distinct hands in the same order. The two seeds share 0 hands.
- All 369 solved rows pass the exact Fraction check: the path starts with the hand's 4 numbers, each state is the one
  before it with two numbers replaced by one +, -, x or / result (no division by zero), and it ends at exactly [24].
- Extra: I rebuilt the hand draw in pure Python (seed-792 shuffle, last 25% = 455 hands, 348 solvable by my own check,
  then the "rv388-test" shuffle). Both seeds match blocks 1 and 2 exactly. None is a practice hand; all are solvable.

## 3. Verdict: NO CLEAR RESULT (neither PASS nor PROVED WRONG)
| seed   | JUDGE-END | >=6? | JUDGE-PLACEBO | >=6? |
|--------|-----------|------|---------------|------|
| 388101 | +8        | yes  | +5            | no   |
| 388202 | +7        | yes  | +2            | no   |
- PASS needs JUDGE-PLACEBO >= 6 in both seeds. It is 5 and 2, so no PASS.
- PROVED WRONG: JUDGE <= END in both seeds is false (+8, +7). Summed JUDGE-PLACEBO = 5 + 2 = +7 > 0, so also false.

## 4. Predictions
- P388.1 (JUDGE beats END by >= 6 in both seeds): RIGHT, +8 and +7.
- P388.2 (JUDGE does not beat PLACEBO by 6 in at least one seed): RIGHT, it fell short in both (+5, +2). As predicted,
  random pruning helped too: PLACEBO beat END by +3 and +5.
- P388.3 (ORACLE >= 75 of 80 in both seeds): RIGHT, 80 and 80 (0 go-backs; 13.1 and 15.0 mean steps per hand).

## 5. Report only (from the log lines): flag events on dead / live states (exact reachability)
| seed   | arm     | 3-number dead / live | 2-number dead / live | entered states in judge training rows |
|--------|---------|----------------------|----------------------|---------------------------------------|
| 388101 | END     | 0 / 0                | 0 / 0                | 35 / 1249 = 2.8%                      |
| 388101 | JUDGE   | 45 / 4               | 401 / 1              | 49 / 914 = 5.4%                       |
| 388101 | PLACEBO | 46 / 13              | 605 / 21             | 36 / 1030 = 3.5%                      |
| 388101 | ORACLE  | 221 / 0              | 422 / 0              | 52 / 97 = 53.6%                       |
| 388202 | END     | 0 / 0                | 0 / 0                | 37 / 1303 = 2.8%                      |
| 388202 | JUDGE   | 72 / 14              | 424 / 0              | 40 / 981 = 4.1%                       |
| 388202 | PLACEBO | 56 / 7               | 598 / 21             | 38 / 1083 = 3.5%                      |
| 388202 | ORACLE  | 381 / 0              | 398 / 0              | 51 / 105 = 48.6%                      |
Solved by one arm but not the other: JUDGE-only vs PLACEBO-only 13 vs 8 (388101), 11 vs 9 (388202). JUDGE-only vs
END-only 14 vs 6, 13 vs 6. Sign test on these discordant hands, both seeds together: JUDGE vs END 27 vs 12, p about
0.02; JUDGE vs PLACEBO 24 vs 17, p about 0.35 (each seed alone: p 0.38 and 0.82).

## 6. Odd things
- SHOWN (code): the log's "calls" numbers are running totals across the arms of one process, and they count only
  cache misses of a shared feature cache that was preloaded (END shows judge_states 0 even though the judge was fitted
  first). So the report-only "judge forward passes per arm" is not in the logs. The per-arm increases (JUDGE 781 / 919,
  PLACEBO +473 / +522, ORACLE +0) are lower bounds on new work, not the passes each arm needed.
- SHOWN (code): flags_by_stage counts set-aside events (one state can be counted more than once). entered_states counts
  distinct states over all 80 hands. END's large "sec" is filling the shared move-score cache. No result changes.
- SHOWN: JUDGE's edge over PLACEBO is on 2-number states (live flags 1 and 0 vs 21 and 21). On 3-number states in
  388202, JUDGE set aside more live states than PLACEBO (14 vs 7). This fits Creative's note that feas-24b is weak on
  3-number states. On practice the judge flagged 0 live states, but here it flagged 5 and 14.
- SHOWN: PLACEBO flagged 1.3-1.5x as often as JUDGE (685 vs 451, 682 vs 510) despite the matched 44.5% cut. SUGGESTED
  cause: the cut was set on END's practice states, but here each arm is scored on the states it picks itself.
- SUGGESTED: JUDGE entered a larger share of training-row states (5.4% and 4.1%) than END or PLACEBO (2.8% and 3.5%).
  Some of its edge may come from states it saw in training. UNTESTED: live-flag accuracy on training vs other states.
  Checking it needs the training set, which only claude_feas24.build can produce, and I did not run it.
- SUGGESTED: the JUDGE-PLACEBO gap (+7 summed) is within chance (p about 0.35). The JUDGE-END gap is stronger, but
  JUDGE still misses 6 hands per seed that END solves.
