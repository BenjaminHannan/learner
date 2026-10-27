# rsn-358a blind recount (VERIFY)

Recounted 2026-09-26 from `origin/builder-outbox` (commit c09fe1b6c) against `PASSMARKS-v2.md` on `origin/main`
(commit 68a7d8672, 2026-09-25 22:52 UTC, before the run). I computed the marks from the four `tests.json` files
before opening RESULTS.md. I did not open anything in `tests/`, run any code, train, or use a GPU.

## Verdict: FAIL (agrees with RESULTS.md)

G0 is met on both seeds. Seed 1 passes G1, G2 and G3. Seed 2 fails G1: only grids6 reaches +30, and sums6 at -11
is also below the -10 floor. PASS needs all marks on both seeds, so this is FAIL. The proved-wrong clause is
not triggered: gaps of +59 and +67 on seed 1 and +76 on seed 2 are all far above +5.

## Marks (integer counts out of 300, from tests.json only)

Each pair is plain / loop. The loop's count is its own-stop `right`.

| mark | seed 1 | seed 2 |
|---|---|---|
| G0: both arms >= 210 on practised tests, at least 2 of 3 kinds | MET (2 of 3). sums4 300/300 yes; grids5 240/243 yes; numbers4 1/3 no | MET (2 of 3). sums4 300/300 yes; grids5 244/248 yes; numbers4 2/4 no |
| G1: loop - plain on sums6 / grids6 / numbers5 | PASS. +59 / +67 / 0 (two >= +30; the third, 0, is >= -10) | FAIL. -11 / +76 / +2 (only one >= +30; sums6 -11 < -10) |
| G2: loop - plain on sums4 / grids5 / numbers4, each >= -10 | PASS. 0 / +3 / +2 | PASS. 0 / +4 / +2 |
| G3a: own stop >= fixed16 - 5 on sums6 / grids6 / numbers5 | PASS. 256 >= 251; 270 >= 266; 1 >= -4 | PASS. 244 >= 239; 265 >= 262; 2 >= -4 |
| G3b: mean rounds sums6 > sums4 | PASS. 8.82 > 7.14 | PASS. 8.01 > 6.52 |
| Seed result | all marks pass | G1 fails |
| Proved wrong (G0 met and all three bigger gaps <= +5) | not met (+59, +67) | not met (+76) |

Raw counts, plain / loop: seed 1: sums6 197/256, grids6 203/270, numbers5 1/1, sums8 78/88, grids7 92/192.
Seed 2: sums6 255/244, grids6 189/265, numbers5 0/2, sums8 142/94, grids7 88/173.
Every test has n = 300 in both arms, and every rounds histogram sums to 300.

## Disagreements with RESULTS.md

I found no disagreement on any graded count, difference, mark or the verdict. The per-seed tables, the loop
rounds tables (mean, fixed 1 to 48, any round, v1, own stop) and all 16 histograms match tests.json exactly. The
training-curve lines match train_log.jsonl except for the first item below.

1. **Transcription slip (not graded):** in the plain-s2 curve at step 35000, RESULTS lists sums4 as `1.0`. The log
   says `0.999`.
2. **The plain-s2 checkpoint hash is malformed.** In both `SEAL-run.sha256.txt` and RESULTS it is
   `2400fc1f78388ca84d52060ef0be0791b7faaf07acdf1a03fa0cb80a2f7739583`, which is 65 hex characters. A sha256 is 64.
   It cannot be the real hash, and a check against the kept file will fail as written. Most likely one character
   was doubled when it was copied. The builder should re-hash `plain-s2/final.pt` and fix the seal. The other three
   hashes are 64 characters. I cannot check any of them against the checkpoints, which are not in git.
3. **Claim beyond the numbers:** RESULTS says "Neither net learned the number puzzles at all ... the setup cannot
   do those puzzles yet." The training logs show otherwise. At step 60000, `exact_by_kind` is numbers3 = 1.0 and
   numbers4 = 1.0 in all four runs. Both arms solve their practice hands perfectly but get 1 to 5 of the 300
   held-out 4-number hands right. That points to memorising a finite pool, not being unable to fit the task. The
   practice pool is every solvable 1-13 four-number hand minus the 300 held out; `split_four` in
   `scripts/claude_rsn358a_envs.py` proves the two sets disjoint. Status: shown that training is at 1.0 while the
   test is near 0. That this is memorisation is suggested, not tested.
4. **Small wording slip:** "about 1-4 right out of 300" should be 0 to 4. plain-s2 got numbers5 0.
5. **Interpretation, not a count:** "Extra thinking time turned into bigger solved puzzles in those cases." The
   loop's own fixed-round curves support part of this. For example, seed 1 grids6 goes from 51 right at 1 round to
   271 at 16. But the comparison with plain is between two different nets, and the loop also used more compute.
   Treat it as suggested, not shown.
6. **Not checkable from git:** the Mac copy, "each test ran exactly once", GPU readings and the seal checks. I found
   nothing that contradicts them.

## Checks

- `SEAL-run.sha256.txt` exists on builder-outbox, with 4 lines. The plain-s2 line is malformed (item 2 above).
- The RESULTS verdict (FAIL) follows the marks: G0 is met on both seeds and seed 2 fails G1, so the result is FAIL,
  not INCONCLUSIVE.
- train_summary.json for all four runs: steps 60000, batch 256, lr 0.0003 (and warmup 1000, latin_pool 20000),
  which matches the plan. Each log has 120 entries at steps 500 to 60000. The learning rate peaks at about 3.0e-4
  around step 1000 and reaches 0.0 at step 60000, identical across the arms. Weights are loop 6,438,302 and plain
  6,385,149 (+0.8%). Training took loop 32.2 / 32.9 min and plain 25.9 / 25.8 min.

## Design notes (things that make a mark easier or harder than it looks)

- **The numbers kind is dead weight in every mark.** Both arms score close to 0 on numbers4 and numbers5. So:
  - G0 really means "sums4 and grids5 are both >= 210 for both arms".
  - G1 really means "sums6 and grids6 are both >= +30". numbers5 is always the "third" test, and its >= -10 floor
    passes automatically. That makes G1 harder than "2 of 3" suggests: 2 of 2 real tests.
  - G3a on numbers5 passes automatically (fixed16 - 5 is negative).
  - The proved-wrong clause reduces to sums6 and grids6 on both seeds.
- **The numbers split tests memory, not method.** Training exact is 1.0 on a finite list of hands, and the
  held-out hands come from the same small space (1-13, target 24). So numbers4 measures generalising from about a
  thousand memorised hands, not practised-size skill. Per the plan, sums and grids practised tests use fresh seeds
  in huge spaces. For grids5 the training exact (0.81 to 0.84) matches the test (243 to 248 of 300), so there is no
  gap there.
- **Seed noise in the plain arm decides G1 on sums.** Plain sums6 scored 197 (seed 1) and 255 (seed 2), a
  58-point swing. Plain sums8 scored 78 and 142. The loop's sums6 was steadier (256 and 244). With two seeds, the
  sums half of G1 rests largely on plain-arm variance. The grids result (+67, +76) is consistent across seeds.
- **The v2 stop rule was chosen after a sums-only preview at sizes 4, 6 and 8.** PASSMARKS says so. This leans the
  sums marks slightly toward the loop, yet sums6 still failed on seed 2.
- **G3a compares the own stop only against fixed 16 rounds.** The stop is not close to the best round. Seed 1
  sums6: own stop 256, fixed 4 rounds 265, right at any round 286. Also, on grids5 58 of 300 items run to the
  48-round cap on both seeds, which roughly matches the number of wrong grids5 answers (57 and 52). The stop seems
  to fire only when the answer settles, so unsolved grids cost the full 48 rounds. This affects compute, not graded
  counts.
- **sums6 is easier than full 6-digit addition.** `make_sum` makes one operand exactly n digits and draws the
  other's length at random from 1 to n, so many sums6 items add a short number to a 6-digit one.
