# rv-387 blind recount (2026-09-26, read-only; counted from per_grid rows)

## 1. Seal and check-load
`sha256sum -c artifacts/claude-rv387-20260926/SEAL.sha256.txt` (exit 0):
`scripts/claude_rv387.py: OK` / `PASSMARKS.md: OK` / `tests/grids7.jsonl: OK` / `tests/grids6.jsonl: OK`.
Also `git diff 2d54b5992 HEAD` on those 4 paths is empty. check-load.jsonl says `"check": "OK"` for all 4 (loop arm, cuda, 6,438,302 weights):
s1 f916b8b562379c583d9e98164f65d7dbdc95610a3b1df07b7c8d078c42745832 · s2 1f9b68c113c8749ce0414486b546b4ef64d89bfb166b887c6e3f707048e858c5
s3 7bb0a62fd5c2ae63cac389c54c8d83d1cdc6949fb9b12f0a043a334169959fa4 · s4 088f49d1cf9f8ed52689ef500ca21b9ff63102e586198e926ad4882def66cb26
Each JSON's ckpt/sha256 matches its check-load line, and these match 358i's SEAL-run.sha256.txt. log.txt: check-load exit=0 for seeds 1-4.

## 2. Counts (per_grid, 300 grids each; every summary field solved/rounds/guesses/backs matches the rows: 24/24)
| test | seed | KEEP | GUESS | BACK | B-K | B-G | go-backs (BACK) | guesses (BACK) | max rounds |
|---|---|---|---|---|---|---|---|---|---|
| grids7 | 1 | 120 | 131 | 131 | +11 | 0 | 0 | 947 | 48 |
| grids7 | 2 | 100 | 117 | 117 | +17 | 0 | 0 | 1054 | 48 |
| grids7 | 3 | 141 | 152 | 152 | +11 | 0 | 0 | 946 | 48 |
| grids7 | 4 | 37 | 51 | 51 | +14 | 0 | 0 | 1384 | 48 |
| grids6 | 1 | 192 | 214 | 214 | +22 | 0 | 0 | 449 | 48 |
| grids6 | 2 | 155 | 194 | 194 | +39 | 0 | 0 | 640 | 48 |
| grids6 | 3 | 220 | 241 | 241 | +21 | 0 | 0 | 424 | 48 |
| grids6 | 4 | 72 | 95 | 95 | +23 | 0 | 0 | 1115 | 48 |
Max rounds is over all 3 arms; no grid exceeds 48. Every unsolved row has rounds = 48. log.txt's 24 summary lines equal the JSON summaries.

## 3. Verdict on grids7 (4 seeds ran, so not NOT RUN)
- PASS needs B-K >= 15 AND B-G >= 10 in >= 3 seeds. s1: 11/0 no; s2: 17/0 no (B-G fails); s3: 11/0 no; s4: 14/0 no. **0 of 4 -> not PASS.**
- PROVED WRONG needs BACK <= KEEP in >= 3 seeds. s1 131>120, s2 117>100, s3 152>141, s4 51>37. **0 of 4 -> not PROVED WRONG.**
- **Verdict: neither = no clear result.** Caveat (shown): the whole BACK-over-KEEP gain comes from guessing; going back never fired.

## 4. GUESS vs BACK rows
Identical, row for row (solved, rounds, guesses, backs, q), in all 8 seed x test cells (0 differing rows of 300). Only `sec` differs once (s3 grids7: 9 vs 8).

## 5. GUESS vs KEEP (grids GUESS solved that KEEP did not / KEEP solved that GUESS did not)
| test | s1 | s2 | s3 | s4 |
|---|---|---|---|---|
| grids7 | 11 / 0 | 18 / 1 | 12 / 1 | 14 / 0 |
| grids6 | 24 / 2 | 39 / 0 | 24 / 3 | 23 / 0 |
Lost grids (e.g. s3 grids7 #183: KEEP solved at round 44; GUESS made 5 guesses, unsolved) are ones where a wrong early guess was never undone.

## 6. Predictions
- **P387.1** (GUESS < KEEP on grids7 in most seeds): **wrong.** GUESS > KEEP in 4/4 seeds (+11, +17, +11, +14). The same holds on grids6 (+22, +39, +21, +23).
- **P387.2** (BACK > GUESS in most seeds): **wrong.** BACK = GUESS in 4/4 (B-G = 0 everywhere).
- **P387.3** (open whether BACK beats KEEP by 15): this is an open question, not a directional call. Answer: +15 is reached in 1/4 seeds (s2 +17). Its context (358a nets solved 173-192/300 7x7) does not carry over. KEEP with 358i's nets is 37-141 here. Those nets and grids differ, and I did not check the 358a figure (untested).
- **P387.4** (BACK goes back rarely or never, BACK ~ GUESS, PASS unlikely): **right.** 0 go-backs in all 8 cells despite 424-1384 guesses per cell. BACK is identical to GUESS, and PASS is not reached. Timing: the note was committed 15:05:35 UTC. That is before START.txt (15:34:55Z) and before the raw-results commit 432cfea71 (15:39:56 UTC), which descends from it (shown).

## 7. Odd things
- shown: backs = 0 across ~6,800 guesses. In code, a go-back fires only if q at a later check round < q at the snapshot, and guesses are made only when q < 0.5. End q on unsolved grids is higher with guessing than without (grids7 mean: s1 0.208 vs 0.076, s2 0.166 vs 0.066, s4 0.159 vs 0.067). suggested: writing a symbol raises q, so the trigger cannot fire. This is the mechanism the first rehearsal note describes.
- shown: seed 4 is far weaker than the others (grids7 KEEP 37 vs 100-141; grids6 72 vs 155-220). The load check still passes for it. Cause untested.
- shown: GUESS-arm rows with 0 guesses exactly equal the KEEP rows (all 8 cells), as expected. Many KEEP solves happen before the first check at round 8 (grids7: 89, 72, 92, 34 of the KEEP solves). Guessing cannot touch those grids.
- suggested (from code + rows): a guess written at round 48 is counted but never tested, because the loop ends right after it. About 132/150/134/204 unsolved grids7 rows end with q < 0.5 and 6 guesses. So roughly 14-15% of guesses are inert, and the guess totals overstate the useful guesses.
- shown: in grids6 GUESS, unsolved grids end with mean q ~0.60 (s1, s3) and q >= 0.5 on 46-73 unsolved grids per seed. The stop head signals "done" on wrong grids once a guess is on the page. How this affects later check rounds is untested.
- shown: NOTE-rehearsal-2 (commit ba72f9b5a, 15:44:09 UTC) says it was written "before any 358i result", but the rv-387 raw-results commit is its ancestor. Whether its author had seen the results is untested. This does not affect P387.4, which is in the first note.
- untested: PASSMARKS says the seal is checked before the run, but log.txt has no seal-check line. It passes now.
- shown (code): check-load compares only argmax predictions after 5 rounds on one grid (grids6[0]). It does not compare q.
