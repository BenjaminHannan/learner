# rsn-358c1 blind recount (VERIFY-c1)

Recounter: Claude (blind recount, 2026-09-26). Read-only. No training, no tests, no rerun, no GPU. Never opened
artifacts/claude-rsn358a-20260925/tests/. Sources: PASSMARKS-c1.md and scripts/claude_rsn358c1_stop.py on
origin/main (commit bac2b85e7); runs/stop358c1-s{1,2}.json and .log on origin/builder-outbox (commit aeb16b79a),
read before RESULTS-c1.md.

## Verdict: recount AGREES with the builder

- **Stop fix: NOT NEEDED.** On no graded family, on either seed, is the v2 stop 10 or more below the fixed budget
  (largest gap 4), so K2 has nothing to recover. K1 FAIL on both seeds, K3 FAIL on both seeds (reported anyway).
- **Loop beats plain: FAIL.** V is met on both seeds. K4 PASS on seed 1, FAIL on seed 2 (sums6 loop 221 vs plain 259, -38).
- **Proved wrong: not triggered on the literal reading.** One reading of clause (b) would trigger it. See disagreement D3.
- Every count in RESULTS-c1.md's two tables matches the JSON exactly (checked by script, 7 families x 8 columns x 2 seeds).
  The two .log files match the JSON line for line.

## Marks (graded: sums4, grids5, sums6, grids6, numbers5; all counts out of 300 on "check")

Differences are answer-cell minus the reference. The "miss" in brackets is how far below the pass line the count falls.

| mark | seed 1 | seed 2 |
|---|---|---|
| V (plain and loop-fixed >= 210 on sums4, grids5) | MET: plain 300 / 255, fixed 300 / 256 | MET: plain 300 / 253, fixed 300 / 262 |
| K1 ans - fixed >= -3 | FAIL: sums4 0, grids5 +1, **sums6 -8** (miss 5), grids6 +1, numbers5 0 | FAIL: sums4 0, grids5 0, **sums6 -14** (miss 11), **grids6 -4** (miss 1), numbers5 0 |
| K2 fixed - v2 gaps (need >= 10 to count) | none: 0, -1, 4, -1, 0 -> nothing to recover | none: 0, 0, 3, 4, 0 -> nothing to recover |
| K3 ans - v2 >= -3 | FAIL: sums4 0, grids5 0, **sums6 -4** (miss 1), grids6 0, numbers5 0 | FAIL: sums4 0, grids5 0, **sums6 -11** (miss 8), grids6 0, numbers5 0 |
| K4 ans - plain | PASS: sums6 +45, grids6 +63, numbers5 0; sums4 0, grids5 +2 | FAIL: **sums6 -38**, grids6 +78, numbers5 0; sums4 0, grids5 +9 |
| Stop fix | NOT NEEDED (K1 FAIL, K3 FAIL) | NOT NEEDED (K1 FAIL, K3 FAIL) |
| Loop beats plain | V + K4 pass | K4 fails -> overall FAIL |

Proved-wrong clause:
- (a) "on every family where v2 lost >= 10, answer-cell recovers < 1/4 of the gap, both seeds": no graded family
  qualifies on either seed, so the clause is empty. Read as intended (it needs cases), it is not triggered.
- (b) "K3 fails by more than 10 anywhere": the largest shortfall below the K3 pass line is 8 (seed 2 sums6: 221 vs
  line 229), so it is not triggered. But answer-cell is 11 below v2 there (221 vs 232). See D3.

Report-only (does not affect any mark): seed 1 sums8 v2 gap 10, answer-cell +13 over v2 (recovers more than the whole
gap); seed 1 grids7 gap 9; seed 2 grids7 gap 16, answer-cell -1 vs v2 (recovers none of it); seed 2 sums8 answer-cell
-12 vs v2 and -50 vs plain.

## Disagreements with RESULTS-c1.md

No count disagrees. Every per-family number, every mark and both verdicts match. Points of wording and interpretation:

- **D1 (wording, plain-English section).** "lost answers on bigger sums both times (5 and 11 answers)". 5 and 11 are
  the K1 shortfalls below the pass line (fixed - 3), not the answers lost. Answers actually lost on sums6:
  seed 1, 8 vs fixed and 4 vs v2; seed 2, 14 vs fixed and 11 vs v2. The "Every miss" section has the right numbers
  (except it says "cost 4-8 answers", which is correct).
- **D2 (timestamps).** "s1 finished 00:02:45Z, s2 finished 00:04:48Z". These are Mac local times (EDT, -04:00), not
  UTC. The file times in the builder transcript are 00:02:45 and 00:04:48 local. The commit is 00:09:37-04:00. So the
  runs finished about 04:03 and 04:05 UTC. This is after the marks were committed to main (02:15 UTC) and after 358a's
  results commit (03:06 UTC). The order is fine, but the "Z" labels are wrong.
- **D3 (interpretation, proved-wrong clause b).** The builder reads "K3 fails by more than 10" as the shortfall below the
  K3 line: 8, so not triggered. If it is read as "answer-cell more than 10 below v2", seed 2 sums6 (-11) triggers it.
  I agree with the builder's reading as the literal one: in K1/K3 "fails by" is measured from the pass line. The marks
  should still have said which reading they meant, because the result lands between the two. Neither registered
  verdict depends on it.
- **D4 (framing).** The headline "Verdict: FAIL" is an overall label that PASSMARKS-c1.md does not define. The marks
  define two separate verdicts (stop fix: NOT NEEDED; loop beats plain: FAIL), and RESULTS gives both right after the headline.
- **D5 (small process point).** RESULTS D6 says "no existing file was edited or deleted". The builder-outbox commit
  aeb16b79a also modifies the repo-root .DS_Store (a macOS metadata file, 6148 -> 6148 bytes, content changed).
  The ledger append is allowed. This is harmless but not strictly additive.

Claims beyond the numbers, checked:
- "matching 358a's seed-2 sums6 pattern" / "fails exactly the way 358a failed it": 358a RESULTS.md (builder-outbox)
  has seed 2 sums6 loop 244 vs plain 255 (-11), which broke the same -10 floor. The direction matches. The size here
  is larger (-38).
- "the Mac copy 005t verified in its D6": the builder transcript quotes 005t's D6 (Mac checkpoint copy with sha256
  matching the seals). Not rechecked beyond that.

## Checks

- **Checkpoint hashes vs SEAL-run.sha256.txt.** Done before the runs. The builder transcript shows `shasum -a 256` of
  ~/premonition-models/rsn358a/{loop-s1,plain-s1,loop-s2,plain-s2}/final.pt. loop-s1 c9f4934f...3ca2c4, plain-s1
  2747d641...218b89 and loop-s2 05fda081...25d2eb match SEAL-run exactly. (SEAL-run exists on origin/builder-outbox,
  not on origin/main. The brief allowed either.) I cannot re-hash the checkpoint files from here.
- **The 65-character plain-s2 typo.** The recorded string is 2400fc1f...0791b7f**aa**f07...9583 (65 chars). The real
  hash is 2400fc1f78388ca84d52060ef0be0791b7faf07acdf1a03fa0cb80a2f7739583 (64). I confirmed that deleting exactly one
  character (index 35 or 36, the doubled "a") gives the real hash, and no other change is needed. This matches the
  known-typo rule. It was applied to plain-s2 only and recorded as deviation D3.
- **Code seal.** I recomputed sha256 of all 7 files in SEAL-c1.sha256.txt from origin/main blobs, and all 7 match.
  The builder ran from a git-archive extract of origin/main (7/7 OK, smoke ok).
- **Mac CPU.** Both JSONs record ckpt paths under /Users/ben-hannan/, which is the Mac. The script picks
  `"cuda" if torch.cuda.is_available() else "cpu"` and never uses MPS, so on a Mac it can only have run on the CPU.
  Moving from BensPC to the Mac is an allowed fallback (evaluation only, no training). CPU and GPU arithmetic could
  flip a rare argmax, but nothing here is near a mark boundary for that reason. The nearest case is seed 2 grids6
  K1, which misses by 1.
- **TEST-ONLY.** The builder's git-archive listing printed only the names of the 358a tests/ files. The script builds
  fresh pick/check sets (seeds 36000+ / 36100+) and never reads tests/.

## Design notes (what makes a mark easier or harder than it looks)

- **What "answer cells" means for sums.** A sums item is a 3 x (n+1) grid: row 0 = a, row 1 = b, row 2 = the answer
  slots, all n+1 of them (leading positions must be BLANK). Grading (`check_sum`) reads only row 2. So for sums the
  answer-cell rule compares exactly the graded row, and the v2 rule also compares the model's untrained outputs on the
  two operand rows. The only thing that can separate the two rules on sums is flicker in the operand rows. For grids,
  the answer cells are the blank cells, and the givens are excluded.
- **The answer-cell stop hits its floor on sums.** The earliest stop is round 3 (index 2). The mean is 3.00 on sums4 on
  both seeds, so all 300 items stopped at round 3. It is 3.55 / 3.52 on sums6 and 4.40 / 4.76 on sums8, against
  v2's 7.15 / 6.64 (sums4) and 8.56 / 7.92 (sums6). So on sums the answer row is often identical over rounds 1-3 with
  q > 0.5, while the answer still improves later (sums6 fixed-round counts climb 183 -> 252 (s1) and 188 -> 221 -> 235
  (s2) between rounds 1, 4 and 8). The answer-cell stop behaves roughly like 3-4 fixed rounds: seed 2 sums6
  answer-cell 221 equals fixed-4 exactly. This is the mechanism behind the sums6 K1/K3 misses (suggested, not
  shown item by item). "Settled for 3 rounds" is a weak signal when the rule may already stop at round 3.
- **On grids the two rules agree on correctness.** Answer-cell stops 1-4 rounds earlier on average (10.73 vs 14.20,
  9.51 vs 10.82, 10.59 vs 14.23, 9.02 vs 11.12), with identical right-counts on grids5/grids6 on both seeds.
- **Ceiling and floor families.** sums4 is 300/300 for every arm, stop and budget on both seeds (fixed budget = 1
  round). numbers5 is 0 almost everywhere (any-round best 1 and 0). Both pass K1/K3 trivially and add nothing to K4.
  So K1/K3 really test three families (grids5, sums6, grids6). K4's "+30 on 2 of 3 bigger" really requires +30 on
  both sums6 and grids6, which is harder than "2 of 3" suggests.
- **V is easy here.** The lowest V count is 253.
- **K2 never had a case.** The premise (v2 stops too early and loses 10+) did not reproduce on any graded fresh set.
  The largest graded gap is 4. The only 10+ gaps are report-only (seed 1 sums8 10, seed 2 grids7 16), and they point
  in opposite directions (answer-cell +13 over v2 vs -1). So the question "is answer-cell stability the fix?" is not
  answered, and RESULTS says so correctly.
- **The fixed-budget reference is picked on "pick", not "check".** Ties go to fewer rounds. On check this usually sits
  a little below the best check budget (seed 2 sums6: budget 8 = 235 vs 239 at 32/48; seed 2 grids6: 24 = 258 vs 259),
  which makes K1 slightly easier than "match the best budget". numbers5's budget (16 vs 2) is noise on 0-3 right.
- **The K1/K3 tolerance of 3 is tight but paired.** Same items and same checkpoint, so it is not sampling noise
  between sets. The sums6 misses (-8/-4 and -14/-11) are well outside it. seed 2 grids6 K1 (-4, miss by 1) is the
  only borderline one.
- **Compute.** As the marks already say, the loop runs all 48 rounds and plain runs one pass, so K4 compares the same
  weights, not the same compute. Stop rounds are not savings.
