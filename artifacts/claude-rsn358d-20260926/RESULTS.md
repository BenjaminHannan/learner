# rsn-358d results (GPU builder run, 2026-09-26, label rent-358d)

## Verdict: INCONCLUSIVE (G0 validity gate not met on either seed)

G0 needs BOTH arms at >= 210/300 on practised-size tests in at least 2 of 3 kinds
(sums4, grids5, numbers4). The loop arm clears only sums4 on both seeds
(seed 3: 300/109/1; seed 4: 298/91/1), so per PASSMARKS-v2.md the run is
INCONCLUSIVE (undertrained at practised size), neither PASS nor FAIL, on both seeds.
The proved-wrong clause needs G0 met, so it is not triggered either.

Question (from PASSMARKS.md): does the loop (thinks in rounds, learned stop) solve
BIGGER puzzles than it practised better than its plain same-size twin, with the ONE
change vs 358a v2 that 4-number practice is all 75,972 puzzles (1,520 hands, every
reachable target 1-99) instead of only the 1,062 target-24 puzzles?
Code sealed and never edited (see Seal). Tests are the same sealed files 358a used
(artifacts/claude-rsn358a-20260925/tests/), each eval run exactly once per checkpoint.
Fresh seeds 3 and 4, both arms retrained, 60,000 steps, batch 256.

## Marks (per PASSMARKS-v2.md, all counts /300)

G0 validity (>= 210 in >= 2 of sums4/grids5/numbers4, both arms):

| seed | plain (sums4/grids5/numbers4) | loop (sums4/grids5/numbers4) | G0 |
|---|---|---|---|
| 3 | 300/236/16 (2 kinds) | 300/109/1 (1 kind) | NOT MET -> INCONCLUSIVE |
| 4 | 300/241/10 (2 kinds) | 298/91/1 (1 kind) | NOT MET -> INCONCLUSIVE |

G1 bigger tests loop-minus-plain (need >= +30 on >= 2 of 3, not below -10 on third):

| seed | sums6 | grids6 | numbers5 | G1 |
|---|---|---|---|---|
| 3 | 131-239 = -108 | 58-187 = -129 | 0-0 = 0 | FAIL |
| 4 | 94-153 = -59 | 36-186 = -150 | 0-1 = -1 | FAIL |

G2 practised-size loop-minus-plain (need >= -10 on each):

| seed | sums4 | grids5 | numbers4 | G2 |
|---|---|---|---|---|
| 3 | 300-300 = 0 | 109-236 = -127 | 1-16 = -15 | FAIL |
| 4 | 298-300 = -2 | 91-241 = -150 | 1-10 = -9 | FAIL |

G3 stop picks the length (loop own-stop >= loop fixed-16 - 5 on each bigger test;
mean rounds sums6 > mean rounds sums4):

| seed | sums6 own vs fix16 | grids6 own vs fix16 | numbers5 own vs fix16 | mean sums6 vs sums4 | G3 |
|---|---|---|---|---|---|
| 3 | 131 vs 137 (need >= 132) FAIL | 58 vs 57 pass | 0 vs 0 pass | 6.08 > 5.09 pass | FAIL |
| 4 | 94 vs 88 (need >= 83) pass | 36 vs 36 pass | 0 vs 0 pass | 6.50 > 5.60 pass | PASS |

Proved-wrong clause ("thinking in rounds lets a small net carry a method to bigger
puzzles than it practised" is proved wrong if G0 met and loop-plain <= +5 on all
three bigger tests on both seeds): NOT TRIGGERED (G0 not met on either seed).

Overall: INCONCLUSIVE seed 3, INCONCLUSIVE seed 4. Not a PASS, not a FAIL.

## Per-seed table of every test (plain | loop own stop | loop - plain), n = 300 each

Seed 3:

| test | role | plain | loop own stop | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 300 | 0 |
| grids5 | practised | 236 | 109 | -127 |
| numbers4 | practised | 16 | 1 | -15 |
| sums6 | bigger | 239 | 131 | -108 |
| grids6 | bigger | 187 | 58 | -129 |
| numbers5 | bigger | 0 | 0 | 0 |
| sums8 | report | 120 | 21 | -99 |
| grids7 | report | 69 | 10 | -59 |

Seed 4:

| test | role | plain | loop own stop | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 298 | -2 |
| grids5 | practised | 241 | 91 | -150 |
| numbers4 | practised | 10 | 1 | -9 |
| sums6 | bigger | 153 | 94 | -59 |
| grids6 | bigger | 186 | 36 | -150 |
| numbers5 | bigger | 1 | 0 | -1 |
| sums8 | report | 33 | 6 | -27 |
| grids7 | report | 73 | 3 | -70 |

## Loop right at fixed rounds and at any round (loop arm only, /300)

Seed 3 (own stop / 1 / 2 / 4 / 8 / 12 / 16 / 24 / 32 / 48 / any):

| test | own | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | any |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 300 | 294 | 298 | 300 | 299 | 299 | 299 | 299 | 299 | 299 | 300 |
| sums6 | 131 | 86 | 121 | 133 | 136 | 137 | 137 | 139 | 139 | 139 | 169 |
| sums8 | 21 | 10 | 18 | 22 | 21 | 23 | 23 | 23 | 23 | 23 | 34 |
| grids5 | 109 | 86 | 98 | 104 | 110 | 108 | 108 | 108 | 108 | 108 | 118 |
| grids6 | 58 | 35 | 48 | 53 | 58 | 58 | 57 | 57 | 57 | 57 | 67 |
| grids7 | 10 | 0 | 1 | 8 | 8 | 10 | 10 | 10 | 10 | 10 | 14 |
| numbers4 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| numbers5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Seed 4 (own stop / 1 / 2 / 4 / 8 / 12 / 16 / 24 / 32 / 48 / any):

| test | own | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | any |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 298 | 295 | 299 | 298 | 298 | 298 | 298 | 298 | 298 | 298 | 300 |
| sums6 | 94 | 88 | 93 | 94 | 91 | 90 | 88 | 89 | 89 | 89 | 125 |
| sums8 | 6 | 8 | 13 | 9 | 5 | 5 | 5 | 5 | 5 | 5 | 20 |
| grids5 | 91 | 76 | 84 | 92 | 91 | 89 | 89 | 89 | 89 | 89 | 108 |
| grids6 | 36 | 35 | 38 | 37 | 34 | 35 | 36 | 36 | 36 | 36 | 54 |
| grids7 | 3 | 1 | 2 | 1 | 2 | 3 | 3 | 3 | 3 | 3 | 4 |
| numbers4 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 |
| numbers5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Loop mean rounds used (seed 3): sums4 5.09, sums6 6.08, sums8 7.43, grids5 33.85,
grids6 43.63, grids7 48.00, numbers4 48.00, numbers5 48.00.
Loop mean rounds used (seed 4): sums4 5.60, sums6 6.50, sums8 7.29, grids5 34.60,
grids6 47.04, grids7 48.00, numbers4 48.00, numbers5 48.00.
(right_v1_rule, report only: s3 sums4 294, sums6 86, sums8 10, grids5 98, grids6 52,
grids7 10, numbers4 1, numbers5 0; s4 sums4 295, sums6 88, sums8 8, grids5 82,
grids6 35, grids7 1, numbers4 1, numbers5 0.)

## numbers4 / numbers5 called out (the point of the 358d change)

numbers4 (held-out 4-number hands, target 24; 358a reference from PASSMARKS.md:
both arms solved ~0-5 of 300 new hands): plain 16 (seed 3) and 10 (seed 4);
loop 1 and 1. The 75,972-puzzle pool lifted the plain arm above 358a's 0-5 range
but not the loop arm, which stayed at 1/300 on every fixed round count too.
numbers5 (fresh 5-number hands): plain 0 and 1; loop 0 and 0 (all rounds 0).
Prediction audit (PASSMARKS.md said numbers4 rises for both arms maybe into the
tens, numbers5 stays low): half right — plain rose, loop did not; numbers5 stayed
low as predicted. Training memorisation is gone (final train exact numbers4:
plain 0.278/0.273, loop 0.001/0.001 — far from 358a's 100% practice accuracy),
but generalisation did not replace it.

## Training (report only)

Final train exact_by_kind (60,000 steps):
loop-s3: grids4 0.548, grids5 0.350, numbers3 0.457, numbers4 0.001,
  sums1 1.000, sums2 1.000, sums3 1.000, sums4 0.990 (ce 0.4963, dev sums4 199/200, grids5 63/200).
plain-s3: grids4 0.745, grids5 0.831, numbers3 1.000, numbers4 0.278,
  sums1 1.000, sums2 1.000, sums3 1.000, sums4 1.000 (ce 0.1823, dev 200/200, 159/200).
loop-s4: grids4 0.537, grids5 0.308, numbers3 0.569, numbers4 0.001,
  sums1 1.000, sums2 1.000, sums3 1.000, sums4 0.991 (ce 0.4365, dev 200/200, 77/200).
plain-s4: grids4 0.748, grids5 0.829, numbers3 1.000, numbers4 0.273,
  sums1 1.000, sums2 1.000, sums3 1.000, sums4 1.000 (ce 0.1631, dev 200/200, 164/200).
Weights: loop 6438302, plain 6385149 (both ~6.4M as specified).

## Compute: GPU, minutes, dollars

GPU: NVIDIA GeForce RTX 5090, 32607 MiB (all four trainings ran AT ONCE on the one
GPU; nvidia-smi showed 87-90% util and ~8028/32607 MiB used — memory never close
to full, so no split into pairs was needed).
Minutes per run (train_summary.json, includes ~0.5 min pool build):
loop-s3 35.2, plain-s3 29.6, loop-s4 35.3, plain-s4 29.6.
Wall clock: launched ~03:56Z; plain-s3/plain-s4 final.pt 04:21Z; loop-s3/loop-s4
final.pt 04:26Z; all four evals finished by ~04:31Z (each eval ran exactly once
per checkpoint).
Dollars: rental 2 dph_total $0.4852 x 0.82 h (03:44:46Z-04:34:03Z) = ~$0.40;
rental 1 was stopped (storage only, ~$0.01). Total ~$0.41, within the $0.80 budget
and below the $0.70 stop line. Time from first rental 03:39:42Z to destroy
04:34:03Z = 54 min, within the 1 h 30 min cap (1 h 25 min stop line never hit).

## Seal (code never edited; errors: none)

- `sha256sum -c artifacts/claude-rsn358d-20260926/SEAL-code.sha256.txt`: all 6 lines OK.
- `python -B scripts/claude_rsn358a_envs.py selftest`: "selftest ok: 1362 four-hands
  (1062 practice, 300 held out), 1346 three-hands".
- `python -B scripts/claude_rsn358d_run.py pool`: exactly "pool 75972 four-number
  puzzles over 1520 hands; 300 held-out hands excluded; target-24 puzzles in pool:
  1062" (pool built in ~20-30 s per process).
- Checkpoint seals (SEAL-run.sha256.txt, recorded BEFORE evals, all 64 hex chars):
  loop-s3 4a667212cf739e76b246979fbef54561df907059345ac3b2f4770b87b1eb6f96,
  plain-s3 c87340dac412fa8e63150636e8765ed9e14ad605db911fd2bbb52426a44f27fc,
  loop-s4 7d8b8779c2cddb7293fd6a7ab36acc7ecaeaec1e14cb033eb2e7f2eca94b63fe,
  plain-s4 e4c537ead03ab26c66103c572fd459766355024091f421b4a1d4ba0165ea9ee6.
  (Paths in the file are W/<run>/final.pt relative to the rental extract root.)
- Nothing broke: no patch, no re-run, no second eval of any checkpoint.
  tests.json counts match the eval logs exactly (verified per run).

## Every deviation

1. Rental 1 (offer 46753295, RTX 5090, $0.446/hr search price) never started: the
   host's docker could not pull the image ("proxyconnect tcp: dial tcp
   127.0.0.1:7890: connect: connection refused"). Restarted once, same error, then
   destroyed it. Rental 2 (offer 44173691, RTX 5090, reliability 0.9984, billed
   dph_total $0.4852) worked first try. 2 rentals of max 3.
2. Billed dph $0.4852 slightly above the $0.469 search estimate (disk/fees); total
   still ~$0.41, inside budget.
3. Checkpoints NOT copied to the Mac: `df -g /` showed 7 GB available, below the
   required 8 GB free-after-copy, so final.pt files were discarded with the rental
   after their sha256 was recorded (as the task allows).
4. Only the four specified files per run were copied into runs/<R>/ (train_log.jsonl,
   train_summary.json, tests.json, <R>.log); the separate eval stdout logs
   (W/<R>-eval.log, same counts as tests.json) stayed on the rental and were
   discarded with it.
5. First `git archive | ssh tar -x` pipe hit the local 120 s tool timeout on close,
   but the extract had completed (27 MB, all files verified present).
6. No TOO-SLOW branch: the 14-minute projection showed all four finishing (~04:38Z
   worst case) before the 05:09:42Z cap, so seed 4 ran to completion.
7. I destroyed exactly my own two instances (52687426, 52687818, both labelled
   rent-358d) and confirmed rent-358d is gone; no other instance was touched.

## What it means / doesn't mean (plain high-school English)

This run cannot say whether thinking-in-rounds beats the plain twin, because the
looping net never got good enough at the normal-size puzzles to qualify (it scored
only 109 and 91 out of 300 on the normal-size grid puzzles, where 210 was the bar).
What DID show up clearly: the plain net learned the bigger puzzles far better
(6-digit sums 239 vs 131 on seed 3; 6x6 grids 187 vs 58), and giving both nets 70x
more number practice cured memorising without creating real skill (held-out number
puzzles: plain 16 and 10, loop 1 and 1 out of 300). Those gaps are facts about this
one run, not proof about all such nets.
