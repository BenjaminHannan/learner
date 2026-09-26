# rv-390 blind recount (2026-09-26; read-only; no RESULTS/VERIFY file read; no model code run)
Caveat carried from NOTE-nets-hold.md: the 358i loop nets may be undertrained (torch 2.8 bug, not verified here).

## 1. Seal, nets, selftest
- `sha256sum -c SEAL.sha256.txt`: 15/15 OK (scripts claude_rv390, claude_rv387, rsn358i_run, rsn358g_run, rsn358a2_run,
  rsn358a_run, rsn358a_envs; PASSMARKS.md; day/grids6, grids7, p-grids6, p-grids7, sums6, sums8, make-day.json).
- `git log 86a7ddfd1..HEAD` on those 15 paths: no commits. Folder commits since the seal: the two notes only
  (1b3ff1051, 09dd50abd; 2a95e36a2, 034be9045, 491d66925), plus run/ below.
- Shown, odd: run/ is no longer uncommitted. All 21 run/ files were added at 17:38 UTC in c3542bb56 (848c32ce0 before
  a pull --rebase), a commit titled "rv-388 results"; it arrived while I worked; tree now clean. I committed nothing.
- Net sha256 per seed: rv390-sN.json = sigma.json = SEAL-run `W/loop-sN/final.pt` = SOURCES.txt, 4/4 match.
  SOURCES notes a Mac-path deviation; hashes unaffected. Device cuda in all 4.
- Selftest: guess_same_as_rv387 30/30 on all 4 nets (it compares solved, rounds, guesses, q). 4 nets ran.
- Sigma 0.3/0.3/1.0/0.3; re-derived from the practice counts (most p-grids6+p-grids7 solves). Pause rounds
  [217,292,333,445,475] re-derived from random.Random(39090).

## 2. Hard-puzzle tables (hard_solved; recomputed from finds, equal to the json in all 16 set x seed cells)
| set    | seed | hard | KEEP | RESTART | GUESS | K-R | G-K | G-R (report only) |
|--------|------|------|------|---------|-------|-----|-----|-----|
| grids7 | s1 | 183 | 5  | 17 | 24 | -12 | +19 | +7  |
| grids7 | s2 | 223 | 1  | 18 | 34 | -17 | +33 | +16 |
| grids7 | s3 | 177 | 11 | 24 | 32 | -13 | +21 | +8  |
| grids7 | s4 | 275 | 0  | 17 | 14 | -17 | +14 | -3  |
| grids6 | s1..s4 | 108/141/81/226 | 4/3/15/0 | 29/13/39/22 | 17/69/30/52 | -25/-10/-24/-22 | +13/+66/+15/+52 | -12/+56/-9/+30 |
| sums6 (GUESS = transfer row) | s1..s4 | 56/19/82/8 | 0/0/0/0 | 19/11/27/7 | 0/0/0/0 | -19/-11/-27/-7 | 0 | - |
| sums8 (same) | s1..s4 | 109/58/137/18 | 0/0/0/0 | 31/22/27/9 | 0/0/0/0 | -31/-22/-27/-9 | 0 | - |

## 3. Verdicts (PASSMARKS applied literally; unit = hard grids7 puzzle)
- H, KEEP vs RESTART: K-R = -12, -17, -13, -17. PASS needs >= +15 in 3 of 4: 0 seeds. PROVED WRONG needs KEEP <= RESTART
  in 3 of 4: 4 of 4 seeds. **H: PROVED WRONG.**
- G, GUESS vs KEEP: G-K = +19, +33, +21, +14; >= +10 in 4 of 4 seeds. **G: PASS.**
- I, per seed (first 40 unfinished grids7, 5 pauses): s1/s2/s3/s4 all have n=40, keep_identical true, keep_pauses 5,
  guess_identical 40/40, messages identical 175/175, 180/180, 180/180, 180/180; max wait (round + pause)
  0.0874 / 0.0891 / 0.1334 / 0.0054 s, all < 1 s, on cuda; wait = round + pause checks out. **I: PASS.**
  (Shown only as the run's own record: I cannot re-run the equality checks.)

## 4. Finds files, checked against day/*.jsonl without the net
- Rows 323 / 385 / 328 / 225 (s1-s4); 0 duplicate (set, idx, arm); 0 shape errors.
- Givens: 0 cells changed where slot != 1, in every row of every set.
- Grids (grids6 + grids7): 0 Latin failures (each s x s row and column holds each 12+name symbol exactly once).
  Also the day files' givens match 12 + names[puz] in all 600 grid items.
- Sums: 159/199/144/54 rows per seed (sums6+sums8); checker not re-implemented. Extra, shown: every row in all four
  files (grids and sums) equals the day item's target in its open cells.
- grids7 finds per arm = json solved: KEEP 16/8/16/7, RESTART 27/25/29/24, GUESS 35/41/37/21 (s1-s4), all equal.
  All other sets also match, including KEEP by-48/after-48 and GUESS by-48.

## 5. Predictions
- P390.1: WRONG as written. "H is not a PASS" held, but "KEEP beats RESTART in most seeds" failed: KEEP won 0 of 4
  seeds (-12 to -17).
- P390.2: RIGHT. GUESS beat KEEP in 4 of 4 seeds (+14 to +33).
- P390.3: RIGHT. Longest wait 0.1334 s.
- P390.4: RIGHT but trivially. GUESS = KEEP on sums in 8 of 8 seed x set cells (same puzzles, same rounds), because GUESS
  wrote 0 guesses on sums. The stated reason (wrong digits never undone) never came into play.
- Seed 4 has the most unfinished grids: RIGHT. grids7 282 vs 194/230/182; grids6 241 vs 120/150/87 (and the most hard).

## 6. Odd things
- Shown: GUESS wrote 0 guesses on sums in all 8 seed x set cells (grids7: 1383/1827/1464/3191). So the sums transfer
  row tests nothing. Why is untested: the code writes only when q < 0.5 at a check round and some open cell's top
  probability is < 0.99, so the net must be sure of itself on sums even when it is wrong (suggested).
- Shown: KEEP rarely solved a hard puzzle. grids7 17 of 858 (2.0%), grids6 22 of 556, sums 0 of 487; seed 4 solved 0 on
  both grid sets. Every KEEP hard solve came by round 149 (grids6: 168). Rounds 150-480 added nothing in any seed.
  Suggested: KEEP's loop settles into a fixed state (untested).
- Shown: KEEP's rounds 1-48 reproduce the day pass: its by-48 solves equal the unfinished-minus-hard puzzles in all 16 cells.
- Report only, shown: GUESS vs RESTART on hard grids7 is +7, +16, +8, -3 (104 vs 76 in total). They overlap little
  (10/4/9/2 puzzles solved by both). 51 of GUESS's 104 came by round 48, so about half is rv-387's in-budget effect
  and not downtime. RESTART's solves spread across all 10 restarts (only 17 of 76 in restart 1).
- Shown: in I, 34/35/35/35 of 40 GUESS runs were actually paused (the rest finished before round 217). The wait
  counts saving the state, not resuming. Both match the sealed wording.
- Suggested: s4's longest round 0.0047 s vs 0.087-0.133 s (s1-s3) and 0.12-0.15 s (every selftest). A one-off stall
  probably sets the maximum. The margin under 1 s is large either way.
- Shown, cosmetic: the sealed script's docstring still says "DRAFT ... Not sealed". ADDENDUM-transfer.md (15:43) promised a BACK
  transfer row; the later sealed PASSMARKS swapped it for GUESS, and the json follows PASSMARKS.

Plain language: working longer on one attempt (KEEP) almost never cracked the hard puzzles; ten fresh starts did
better on every net, and pencilling in best guesses (GUESS) did better still on 3 of 4 nets. Pausing for a message changed nothing.
