# rsn-358c1 RESULTS (builder, 2026-09-26, Mac CPU, $0)

## Verdict: FAIL (stop fix NOT NEEDED; loop-beats-plain FAIL)

- Stop fix: K2 is vacuous on both seeds (the v2 stop never falls 10+ below the fixed
  budget on any graded family), so per PASSMARKS-c1.md the stop fix is NOT NEEDED.
  K1 and K3 are still reported and both FAIL (seed 1 sums6; seed 2 sums6 and grids6
  by 1 for K1, sums6 for K3).
- Loop beats plain: V is met on both seeds, but K4 passes seed 1 and fails seed 2
  (loop with the answer-cell stop loses bigger sums to plain by 38 on seed 2).
- The "proved wrong" clause did NOT trigger (no K3 miss exceeds 10; no graded family
  has a v2 loss of 10+ on both seeds at all).

## Per-seed, per-family counts (n = 300 per check set; every count on "check")

Columns: budget = fixed round budget picked on "pick"; fixed = loop right at budget;
v2 = loop right at v2 stop; ans = loop right at answer-cell stop; plain = plain right;
mv2/mans = mean stop rounds (1-indexed); any = right at any of the 48 rounds.

Seed 1 (runs/stop358c1-s1.json):

| family | role | budget | fixed | v2 | ans | plain | mv2 | mans | any |
|---|---|---|---|---|---|---|---|---|---|
| sums4 | graded (practised) | 1 | 300 | 300 | 300 | 300 | 7.15 | 3.00 | 300 |
| grids5 | graded (practised) | 8 | 256 | 257 | 257 | 255 | 14.20 | 10.73 | 257 |
| sums6 | graded (bigger) | 8 | 255 | 251 | 247 | 202 | 8.56 | 3.55 | 276 |
| grids6 | graded (bigger) | 12 | 260 | 261 | 261 | 198 | 10.82 | 9.51 | 261 |
| numbers5 | graded (bigger) | 16 | 0 | 0 | 0 | 0 | 9.96 | 5.61 | 1 |
| sums8 | report-only | 4 | 92 | 82 | 95 | 80 | 9.97 | 4.40 | 141 |
| grids7 | report-only | 32 | 204 | 195 | 195 | 113 | 8.53 | 8.53 | 204 |

Seed 2 (runs/stop358c1-s2.json):

| family | role | budget | fixed | v2 | ans | plain | mv2 | mans | any |
|---|---|---|---|---|---|---|---|---|---|
| sums4 | graded (practised) | 1 | 300 | 300 | 300 | 300 | 6.64 | 3.00 | 300 |
| grids5 | graded (practised) | 8 | 262 | 262 | 262 | 253 | 14.23 | 10.59 | 264 |
| sums6 | graded (bigger) | 8 | 235 | 232 | 221 | 259 | 7.92 | 3.52 | 264 |
| grids6 | graded (bigger) | 24 | 258 | 254 | 254 | 176 | 11.12 | 9.02 | 260 |
| numbers5 | graded (bigger) | 2 | 0 | 0 | 0 | 0 | 9.50 | 5.34 | 0 |
| sums8 | report-only | 8 | 101 | 102 | 90 | 140 | 9.77 | 4.76 | 135 |
| grids7 | report-only | 48 | 192 | 176 | 175 | 105 | 8.04 | 7.86 | 192 |

## Marks (PASSMARKS-c1.md, graded families only: sums4, grids5, sums6, grids6, numbers5)

| mark | seed 1 | seed 2 |
|---|---|---|
| V validity (plain and loop-fixed each >= 210/300 on sums4 and grids5) | MET: sums4 300/300, grids5 255/256 | MET: sums4 300/300, grids5 253/262 |
| K1 answer-cell >= fixed - 3, all five | FAIL: sums4 300>=297, grids5 257>=253, sums6 247>=252 MISS by 5, grids6 261>=257, numbers5 0>=-3 | FAIL: sums4 300>=297, grids5 262>=259, sums6 221>=232 MISS by 11, grids6 254>=255 MISS by 1, numbers5 0>=-3 |
| K2 where fixed - v2 >= 10: ans - v2 >= half the gap rounded up | NOT NEEDED: no graded family has fixed - v2 >= 10 (gaps: sums4 0, grids5 -1, sums6 4, grids6 -1, numbers5 0) | NOT NEEDED: gaps sums4 0, grids5 0, sums6 3, grids6 4, numbers5 0 |
| K3 answer-cell >= v2 - 3, all five | FAIL: sums4 300>=297, grids5 257>=254, sums6 247>=248 MISS by 1, grids6 261>=258, numbers5 0>=-3 | FAIL: sums4 300>=297, grids5 262>=259, sums6 221>=229 MISS by 8, grids6 254>=251, numbers5 0>=-3 |
| K4 loop(ans) - plain: >= +30 on 2 of sums6/grids6/numbers5 and >= -10 on third; >= -10 on sums4, grids5 | PASS: sums6 +45 (247-202), grids6 +63 (261-198), numbers5 0 (0-0); sums4 0, grids5 +2 | FAIL: sums6 -38 (221-259) breaks the -10 floor; grids6 +78 (254-176), numbers5 0 (0-0); sums4 0, grids5 +9 |

Stop fix verdict: NOT NEEDED (K2 vacuous both seeds); K1 FAIL both seeds, K3 FAIL both seeds.
Loop-beats-plain verdict: FAIL (V met both seeds; K4 PASS seed 1, FAIL seed 2).

Proved-wrong clause ("answer-cell stability is the fix"): needs (a) on every family where v2
lost >= 10, answer-cell recovers less than a quarter of the gap, on both seeds, or (b) any K3
miss by more than 10. (a) is false: no graded family loses >= 10 on either seed (largest graded
v2 gap is 4: seed 1 sums6, seed 2 grids6). (b) is false: the largest K3 miss is 8 (seed 2 sums6;
seed 1 sums6 misses by 1). NOT triggered.

Report-only notes (not graded): seed 1 sums8 v2 gap is exactly 10 (92 fixed vs 82 v2) and
answer-cell recovers all of it plus 3 (95); seed 2 grids7 v2 gap is 16 (192 vs 176) with
answer-cell at 175. Neither affects any mark.

## Precondition and seal (all verified before running)

- Checkpoints used: ~/premonition-models/rsn358a/{loop-s1,plain-s1,loop-s2,plain-s2}/final.pt
  (the Mac copy 005t verified in its D6; this machine has no C:/ path).
  sha256: loop-s1 c9f4934f...3ca2c4 MATCH; plain-s1 2747d641...18b89 MATCH;
  loop-s2 05fda081...25d2eb MATCH (all exact, 64 chars).
- plain-s2 real sha256 is 2400fc1f78388ca84d52060ef0be0791b7faf07acdf1a03fa0cb80a2f7739583
  (64 chars). The recorded string in SEAL-run.sha256.txt (local and origin/builder-outbox,
  identical) has 65 chars with one doubled "a" ("...b7faaf07..."); deleting that one character
  (index 35 or 36, same result) gives the real hash exactly. Accepted per the known-typo rule;
  this is the only accepted deviation, and it is for plain-s2 only.
- SEAL: `git archive origin/main scripts artifacts/claude-rsn358c-20260926
  artifacts/claude-rsn358a-20260925` extracted to /tmp; `shasum -a 256 -c
  artifacts/claude-rsn358c-20260926/SEAL-c1.sha256.txt` -> 7/7 OK
  (claude_rsn358c1_stop.py, claude_rsn358c2_run.py, claude_rsn358a2_run.py,
  claude_rsn358a_run.py, claude_rsn358a_envs.py, claude_blurt1.py, PASSMARKS-c1.md).
- Smoke: `python -B scripts/claude_rsn358c1_stop.py smoke` -> "smoke ok" (from the sealed extract).
- Runs: exactly ONCE per seed from the sealed extract with the required venv command
  (OMP/MKL threads 1, uv offline, python 3.12, torch + numpy). s1 finished 00:02:45Z,
  s2 finished 00:04:48Z (~2 min each). Logs: runs/stop358c1-s1.log and -s2.log, 7 lines each
  (one printed line per family, kept verbatim). JSONs: runs/stop358c1-s1.json (3791 bytes),
  runs/stop358c1-s2.json (3802 bytes).
- artifacts/claude-rsn358a-20260925/tests/ (TEST-ONLY) was never opened, printed, tuned on, or
  quoted. The sealed script made its own fresh puzzles (pick seeds 36000+, check seeds 36100+).
  The seal-extract listing showed test filenames only; no test file was ever read.

## Deviations (6)

- D1: the brief's OPUS-RULES.txt path did not exist (that scratchpad dir holds only an empty
  scratchpad/ dir); followed the task text, which states the same rules (additive-only,
  append-only ledger, integer counts, no test peeking), as 005t did in its D4.
- D2: checkpoints read from ~/premonition-models/rsn358a/<run>/final.pt (Mac copy) instead of
  C:/Users/benja/premonition-models/rsn358a/... (a Windows-only path; this machine is macOS).
  All four hashes verified as above before running.
- D3: plain-s2 recorded seal hash has the known 65-char typo; real 64-char hash recorded above,
  accepted per the task's typo rule.
- D4: ran on this Mac's CPU (torch CPU; no NVIDIA GPU on this machine). The task allows CPU
  when the GPU has under 4 GB free; here there is no GPU at all. Evaluation only, no training.
- D5: seal check ran as `shasum -a 256 -c` (macOS has no `sha256sum` binary); same format,
  same result (7/7 OK).
- D6: sealed code is absent from this worktree checkout (scripts/ and
  artifacts/claude-rsn358c-20260926/ exist only on origin/main), so the smoke and both seed runs
  executed from the /tmp git-archive extract; --out pointed at this worktree's
  artifacts/claude-rsn358c-20260926/runs/. Only new files were created (runs/ + this file);
  no existing file was edited or deleted.

## Every miss

- sums6 seed 1: answer-cell 247 vs fixed 255 (K1 miss by 5) and vs v2 251 (K3 miss by 1).
  The early answer-cell stop (mean 3.55 rounds vs v2 8.56) cost 4-8 answers here.
- sums6 seed 2: answer-cell 221 vs fixed 235 (K1 miss by 11) and vs v2 232 (K3 miss by 8);
  loop(ans) - plain is -38 (K4 floor break). Plain won bigger sums on seed 2 at every loop
  measure (fixed 235, v2 232, ans 221 vs plain 259), matching 358a's seed-2 sums6 pattern.
- grids6 seed 2: answer-cell 254 vs fixed 258 (K1 miss by 1); v2 also 254, so K3 holds.
- numbers5 both seeds: loop and plain both score 0 (any-round best is 1 on seed 1, 0 on seed 2),
  so the number puzzles say nothing, as in 358a.
- Report-only: seed 2 sums8 plain 140 beats every loop measure (fixed 101, v2 102, ans 90);
  seed 2 grids7 plain 105 vs loop(ans) 175 (loop still far ahead on grids).

## What it means (plain high-school English)

- The answer-cell stop was supposed to fix the loop quitting too early, but there was almost
  nothing to fix: the old v2 stop already stayed within 4 answers of the best fixed round
  budget on every graded puzzle group, both times. So this experiment cannot tell us whether
  answer-cells are the right fix; the problem it targets barely showed up.
- Where the two stops differed, the new answer-cell stop quit much earlier (about 3-11 rounds
  on average instead of 7-14) and lost answers on bigger sums both times (5 and 11 answers).
  Quitting earlier did not help; on sums it hurt.
- The loop still clearly beats plain on bigger grids both times with the new stop (+63 and +78
  out of 300), but on seed 2 plain wins bigger sums by 38, so the "loop beats plain" bar fails
  exactly the way 358a failed it. One win and one loss means the result does not hold up.
- Neither net learned the number puzzles at all (0 out of 300 both times), so that whole puzzle
  kind says nothing here.

## What it doesn't mean

- It does NOT mean the answer-cell idea is disproved: the proved-wrong clause did not trigger,
  and K2 (the actual test of the idea) never got a graded case to work on.
- It does NOT mean the v2 stop is good: it only means v2 was already close to the fixed budget
  on these fresh sets; the 48 rounds are all computed anyway, so no round savings were measured.
- It does NOT change 358a's registered verdict (FAIL stands whatever this shows, per the
  pass marks); this is a second look at the same checkpoints with one changed rule.
- It does NOT say anything about harder puzzles (sums8/grids7 are report-only) or about giving
  the plain net extra compute some other way (never tested).
