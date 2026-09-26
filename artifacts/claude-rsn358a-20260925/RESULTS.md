# rsn-358a RESULTS (builder, 2026-09-26, BensPC RTX 5070 Ti, shared GPU, $0)

## Verdict: FAIL

G0 is met on both seeds, but G1 passes on seed 1 and fails on seed 2
(PASS needs G0+G1+G2+G3 on BOTH seeds). The "proved wrong" clause did NOT trigger.

## Marks (300 items per test; PASSMARKS-v2.md)

| mark | seed 1 | seed 2 |
|---|---|---|
| G0 validity (both arms >=210/300 practised-size in >=2 of 3 kinds) | MET: sums 300/300, grids 240/243, numbers 1/3 -> 2 of 3 | MET: sums 300/300, grids 244/248, numbers 2/4 -> 2 of 3 |
| G1 bigger: loop - plain (sums6 / grids6 / numbers5; need >= +30 on 2 of 3 and >= -10 on third) | PASS: +59 / +67 / 0 | FAIL: -11 / +76 / +2 (only grids6 hits +30; sums6 -11 breaks the -10 floor) |
| G2 practised-size: loop - plain (each >= -10) | PASS: 0 / +3 / +2 | PASS: 0 / +4 / +2 |
| G3 stop picks the length (own-stop >= fixed-16 - 5 each bigger test; mean rounds sums6 > sums4) | PASS: 256>=251, 270>=266, 1>=-4; 8.82 > 7.14 | PASS: 244>=239, 265>=262, 2>=-4; 8.01 > 6.52 |
| Overall | G0+G1+G2+G3 pass | G1 fails |

Proved-wrong clause ("thinking in rounds lets a small net carry a method to bigger puzzles"):
needs G0 met AND loop-plain <= +5/300 on ALL three bigger tests on BOTH seeds.
Seed 1 has +59 (sums6) and +67 (grids6); seed 2 has +76 (grids6). NOT triggered.

## Per-seed tables (plain right, loop right at own stop, loop - plain; n = 300)

Seed 1:

| test | role | plain | loop (own stop) | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 300 | 0 |
| sums6 | bigger | 197 | 256 | +59 |
| sums8 | report | 78 | 88 | +10 |
| grids5 | practised | 240 | 243 | +3 |
| grids6 | bigger | 203 | 270 | +67 |
| grids7 | report | 92 | 192 | +100 |
| numbers4 | practised | 1 | 3 | +2 |
| numbers5 | bigger | 1 | 1 | 0 |

Seed 2:

| test | role | plain | loop (own stop) | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 300 | 0 |
| sums6 | bigger | 255 | 244 | -11 |
| sums8 | report | 142 | 94 | -48 |
| grids5 | practised | 244 | 248 | +4 |
| grids6 | bigger | 189 | 265 | +76 |
| grids7 | report | 88 | 173 | +85 |
| numbers4 | practised | 2 | 4 | +2 |
| numbers5 | bigger | 0 | 2 | +2 |

## Loop rounds detail (report; right_v1_rule is report-only, never graded)

Seed 1 loop (mean rounds | right at 1/2/4/8/12/16/24/32/48 | any round | v1 rule | own-stop right):

| test | mean | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | any | v1 | own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 7.14 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 |
| sums6 | 8.82 | 177 | 220 | 265 | 260 | 257 | 256 | 251 | 251 | 251 | 286 | 177 | 256 |
| sums8 | 9.93 | 46 | 69 | 83 | 89 | 84 | 82 | 79 | 77 | 76 | 135 | 46 | 88 |
| grids5 | 15.78 | 101 | 186 | 237 | 243 | 243 | 243 | 243 | 243 | 243 | 245 | 214 | 243 |
| grids6 | 9.57 | 51 | 156 | 240 | 261 | 269 | 271 | 272 | 272 | 272 | 273 | 211 | 270 |
| grids7 | 9.07 | 16 | 80 | 144 | 186 | 196 | 199 | 200 | 200 | 200 | 200 | 86 | 192 |
| numbers4 | 8.59 | 2 | 1 | 1 | 3 | 3 | 3 | 3 | 3 | 3 | 4 | 2 | 3 |
| numbers5 | 9.79 | 1 | 0 | 0 | 1 | 2 | 1 | 2 | 3 | 3 | 6 | 1 | 1 |

Seed 2 loop:

| test | mean | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | any | v1 | own |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 6.52 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 |
| sums6 | 8.01 | 178 | 201 | 235 | 249 | 245 | 244 | 243 | 243 | 243 | 269 | 178 | 244 |
| sums8 | 9.72 | 39 | 62 | 86 | 95 | 94 | 92 | 93 | 93 | 93 | 122 | 39 | 94 |
| grids5 | 15.74 | 126 | 206 | 243 | 249 | 248 | 248 | 248 | 248 | 248 | 249 | 232 | 248 |
| grids6 | 10.35 | 79 | 156 | 237 | 261 | 265 | 267 | 267 | 269 | 270 | 270 | 199 | 265 |
| grids7 | 7.91 | 27 | 84 | 140 | 173 | 181 | 182 | 185 | 187 | 187 | 187 | 68 | 173 |
| numbers4 | 8.75 | 1 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 8 | 1 | 4 |
| numbers5 | 9.84 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 3 | 0 | 2 |

Rounds histograms (own stop; rounds -> count, sums to 300):
- s1 sums4: 4:15 5:45 6:60 7:65 8:50 9:31 10:20 11:8 12:5 14:1
- s1 sums6: 4:1 5:13 6:31 7:43 8:55 9:56 10:34 11:30 12:20 13:10 14:5 16:1 19:1
- s1 sums8: 4:2 5:4 6:11 7:42 8:36 9:43 10:39 11:47 12:36 13:20 14:5 15:8 16:1 17:4 19:1 23:1
- s1 grids5: 5:2 6:26 7:58 8:76 9:50 10:19 11:5 12:4 13:1 14:1 48:58
- s1 grids6: 3:43 4:66 5:24 6:27 7:35 8:26 9:24 10:10 11:8 12:7 13:1 14:1 17:1 18:1 19:1 21:1 48:24
- s1 grids7: 3:16 4:65 5:46 6:27 7:25 8:27 9:28 10:14 11:11 12:7 13:7 14:6 15:1 16:1 17:1 20:1 22:1 48:16
- s1 numbers4: 4:4 5:15 6:37 7:55 8:46 9:51 10:28 11:28 12:20 13:8 14:4 15:1 16:3
- s1 numbers5: 5:6 6:24 7:35 8:45 9:41 10:54 11:28 12:24 13:12 14:11 15:11 16:2 18:2 20:1 21:2 23:1 24:1
- s2 sums4: 4:16 5:60 6:96 7:61 8:40 9:16 10:5 11:2 12:3 18:1
- s2 sums6: 5:23 6:52 7:67 8:60 9:32 10:27 11:18 12:12 13:4 14:3 16:1 17:1
- s2 sums8: 5:6 6:17 7:37 8:46 9:50 10:42 11:33 12:26 13:20 14:9 15:4 16:6 17:2 18:2
- s2 grids5: 3:2 5:3 6:24 7:69 8:69 9:37 10:21 11:13 12:2 13:1 15:1 48:58
- s2 grids6: 3:52 4:45 5:36 6:26 7:17 8:13 9:16 10:19 11:11 12:5 13:12 14:10 15:4 16:2 17:2 18:2 19:1 21:1 22:1 24:1 48:24
- s2 grids7: 3:14 4:62 5:49 6:40 7:37 8:25 9:18 10:10 11:12 12:7 13:6 14:3 15:4 16:2 17:1 20:1 27:1 48:8
- s2 numbers4: 4:1 5:11 6:38 7:59 8:51 9:46 10:32 11:18 12:12 13:20 14:7 15:3 18:1 19:1
- s2 numbers5: 5:4 6:11 7:44 8:42 9:49 10:52 11:24 12:33 13:19 14:6 15:4 16:5 18:5 19:1 20:1

## Training curves (every 5,000 steps; dev = right/200 on fresh dev sums4 + grids5)

loop-s1 (6,438,302 weights, 32.2 min, cuda):
- 5000: min 2.9, ce 0.5341, exact_by_kind grids4 0.667 grids5 0.561 numbers3 0.155 numbers4 0.008 sums1 1.0 sums2 0.945 sums3 0.715 sums4 0.517; dev 161/161
- 10000: min 5.6, ce 0.1964, kinds 0.699 0.699 0.823 0.561 0.999 0.993 0.986 0.928; dev 198/176
- 15000: min 8.2, ce 0.1176, kinds 0.73 0.766 0.945 0.859 1.0 0.997 0.995 0.977; dev 200/171
- 20000: min 10.9, ce 0.1002, kinds 0.741 0.783 0.977 0.907 1.0 0.999 0.999 0.989; dev 200/174
- 25000: min 13.5, ce 0.0887, kinds 0.744 0.772 0.983 0.952 1.0 1.0 1.0 0.998; dev 199/178
- 30000: min 16.2, ce 0.0816, kinds 0.718 0.792 0.993 0.969 1.0 1.0 0.999 0.988; dev 200/175
- 35000: min 18.9, ce 0.0754, kinds 0.751 0.799 0.999 0.985 1.0 1.0 1.0 0.991; dev 200/180
- 40000: min 21.5, ce 0.0699, kinds 0.738 0.781 1.0 1.0 1.0 1.0 1.0 0.999; dev 200/174
- 45000: min 24.2, ce 0.0671, kinds 0.743 0.803 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/175
- 50000: min 26.9, ce 0.0674, kinds 0.746 0.782 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/176
- 55000: min 29.5, ce 0.0607, kinds 0.742 0.812 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/174
- 60000: min 32.2, ce 0.0606, kinds 0.741 0.815 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/173

plain-s1 (6,385,149 weights, 25.9 min, cuda):
- 5000: min 2.4, ce 0.2857, kinds 0.681 0.509 0.576 0.113 1.0 0.997 0.999 0.976; dev 200/106
- 10000: min 4.5, ce 0.0909, kinds 0.739 0.644 0.965 0.894 1.0 1.0 1.0 1.0; dev 200/138
- 15000: min 6.6, ce 0.0776, kinds 0.754 0.711 0.986 0.964 1.0 1.0 0.993 0.995; dev 200/153
- 20000: min 8.8, ce 0.0706, kinds 0.762 0.751 0.995 0.983 0.999 1.0 0.99 0.977; dev 188/162
- 25000: min 10.9, ce 0.0638, kinds 0.765 0.789 0.994 0.985 1.0 1.0 1.0 1.0; dev 200/165
- 30000: min 13.1, ce 0.061, kinds 0.761 0.805 0.998 0.994 1.0 1.0 1.0 1.0; dev 200/165
- 35000: min 15.3, ce 0.0624, kinds 0.765 0.827 0.999 0.993 1.0 1.0 1.0 1.0; dev 200/172
- 40000: min 17.5, ce 0.0558, kinds 0.76 0.827 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/172
- 45000: min 19.6, ce 0.0554, kinds 0.77 0.837 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/174
- 50000: min 21.7, ce 0.0559, kinds 0.758 0.834 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/174
- 55000: min 23.8, ce 0.0533, kinds 0.759 0.841 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/173
- 60000: min 25.9, ce 0.0535, kinds 0.755 0.841 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/174

loop-s2 (6,438,302 weights, 32.9 min, cuda):
- 5000: min 3.6, ce 0.5596, kinds 0.689 0.674 0.106 0.002 0.997 0.977 0.82 0.728; dev 178/141
- 10000: min 6.5, ce 0.2017, kinds 0.728 0.676 0.863 0.457 1.0 0.995 0.998 0.957; dev 199/163
- 15000: min 9.1, ce 0.138, kinds 0.736 0.75 0.894 0.85 1.0 0.999 0.998 0.991; dev 200/164
- 20000: min 11.7, ce 0.1036, kinds 0.724 0.76 0.966 0.95 1.0 1.0 0.993 0.975; dev 200/167
- 25000: min 14.4, ce 0.0938, kinds 0.744 0.781 0.984 0.932 1.0 1.0 0.999 0.995; dev 200/166
- 30000: min 17.0, ce 0.0844, kinds 0.725 0.745 0.991 0.975 1.0 1.0 0.999 0.995; dev 200/164
- 35000: min 19.6, ce 0.0762, kinds 0.761 0.797 0.998 0.994 1.0 1.0 1.0 1.0; dev 200/161
- 40000: min 22.3, ce 0.0722, kinds 0.754 0.774 1.0 0.998 1.0 1.0 1.0 1.0; dev 200/162
- 45000: min 24.9, ce 0.0741, kinds 0.759 0.816 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/165
- 50000: min 27.6, ce 0.0721, kinds 0.76 0.817 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/171
- 55000: min 30.2, ce 0.0701, kinds 0.742 0.812 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/166
- 60000: min 32.9, ce 0.0614, kinds 0.742 0.812 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/167

plain-s2 (6,385,149 weights, 25.8 min, cuda):
- 5000: min 2.3, ce 0.31, kinds 0.68 0.522 0.607 0.117 0.999 0.996 0.979 0.963; dev 185/103
- 10000: min 4.5, ce 0.0943, kinds 0.751 0.647 0.95 0.895 1.0 0.999 0.998 0.977; dev 196/131
- 15000: min 6.6, ce 0.0858, kinds 0.755 0.708 0.966 0.961 1.0 0.999 0.997 0.99; dev 200/138
- 20000: min 8.9, ce 0.073, kinds 0.759 0.757 0.984 0.981 1.0 1.0 1.0 1.0; dev 200/144
- 25000: min 11.0, ce 0.0687, kinds 0.761 0.779 0.999 0.979 1.0 1.0 1.0 1.0; dev 200/152
- 30000: min 13.1, ce 0.0614, kinds 0.763 0.798 0.998 0.985 1.0 1.0 1.0 1.0; dev 200/146
- 35000: min 15.2, ce 0.0634, kinds 0.769 0.822 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/157
- 40000: min 17.3, ce 0.0589, kinds 0.764 0.83 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/158
- 45000: min 19.4, ce 0.0675, kinds 0.762 0.835 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/159
- 50000: min 21.5, ce 0.0631, kinds 0.765 0.842 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/164
- 55000: min 23.7, ce 0.0623, kinds 0.757 0.833 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/163
- 60000: min 25.8, ce 0.0544, kinds 0.755 0.839 1.0 1.0 1.0 1.0 1.0 1.0; dev 200/161

## Checkpoint seals (hashed on BensPC BEFORE each eval; keep-location copies re-verified equal)

- loop-s1: c9f4934f2ab62a0abd0c5103c10785b6286aea9fdafabd06ebbf7727bf3ca2c4 (25764244 bytes)
- plain-s1: 2747d6413abefce568b6cf32217bfbd7ae519b3dd6c322a1c9997bd36c218b89 (25573143 bytes)
- loop-s2: 05fda0818d47316f651a0fc28da1e32815eb8d6d10331a2096346175fe25d2eb (25764244 bytes)
- plain-s2: 2400fc1f78388ca84d52060ef0be0791b7faaf07acdf1a03fa0cb80a2f7739583 (25573143 bytes)
Checkpoints kept at C:/Users/benja/premonition-models/rsn358a/<run>/final.pt; never in git.
Mac copy done: `df -g /` showed 11 GB free (>= 8 GB after the ~103 MB copy), so all 4 final.pt files
were also copied to ~/premonition-models/rsn358a/<run>/final.pt with sha256 matching the seals above.

## Method notes

- Code: unmodified origin/main scripts/claude_rsn358a2_run.py + claude_rsn358a_run.py + claude_rsn358a_envs.py
  + claude_blurt1.py, run through scripts/claude_rsn358a2_shared.py (4 GB GPU cap, env RSN358A_GPU_GB=4).
  Seal SEAL-code-v2 14/14 OK + SEAL-shared-launcher 1/1 OK (full check from git archive locally;
  remote spot-checks via Get-FileHash match); env selftest "selftest ok".
- Each of the 8 sealed tests ran exactly ONCE per final checkpoint (4 evals total). Test items never
  opened, printed, or tuned on; only counts recorded. Pilots (seed 9, 500 steps, loop 0.5 min / plain
  0.5 min after 14 s data-ready; full-run estimate 120x = ~32 min each) never touched the tests.
- Training: 60,000 steps, batch 256, lr 3e-4, same data stream per seed, one run at a time (sharing rule).
  Total train 116.8 min (32.2 + 25.9 + 32.9 + 25.8), under the 480-minute cap. No OOM anywhere
  (own cap never hit; free GPU memory never below 10 GB).
- GPU: BensPC RTX 5070 Ti 16303 MiB, $0. Start: 404 MiB used, 15570+ MiB free, no compute job.
  pilots/train/eval re-checked after every run; lowest free reading 10342 MiB.

## Deviations (7)

- D1: pilot --out used W/pilot-loop and W/pilot-plain inside the code dir instead of /tmp/pilot-*:
  Windows has no /tmp; timing-only pilots, no effect on results.
- D2: trained ONE at a time, not two (sharing rule S4 overrides the task's "two at a time").
- D3: also copied design/v3/30-modes/358a-loop-vs-plain-general-puzzles.md to BensPC (it is part of
  SEAL-code-v2, needed for a complete remote tree). No sha256sum binary on Windows, so the full
  14/14 check ran locally from `git archive origin/main`, plus remote Get-FileHash spot checks
  (all match) and the env selftest on BensPC.
- D4: the brief's OPUS-RULES.txt path did not exist (both scratchpad dirs empty); followed the
  /tmp/opus-rules.txt copy and the task text, which state the same rules (additive-only, append-only
  ledger, integer counts, no test peeking).
- D5: an unrelated Python310 python.exe (PID 764) briefly held ~2.5 GB of GPU during the
  plain-s1/loop-s2 window (used showed 5654 MiB at one poll, back to ~3 GB later); free VRAM never
  below 10 GB, its log was not visible, and per S3 it was never touched.
- D6: Mac checkpoint copy first deferred (`df -g /` showed 6 GB free, below the 8 GB rule), then done
  after space freed up (11 GB free): all 4 final.pt copied to ~/premonition-models/rsn358a/<run>/ with
  sha256 matching the seals; 11 GB free after the copy.
- D7: first pilot-loop launch (PID 10768) died instantly because W/ did not exist yet for the log
  redirect; created W/ and relaunched cleanly. No training or test contact involved.

## Every miss

- numbers4 (practised size): loop 3, plain 1 (s1); loop 4, plain 2 (s2). numbers5 (bigger):
  loop 1, plain 1 (s1); loop 2, plain 0 (s2). Both arms, both seeds: the number puzzles were
  essentially never solved, even at the practised size, so G0 rests on sums + grids only.
- sums6 seed 2: loop 244 vs plain 255 (-11) -- the single miss that fails G1 (and the -10 floor).
- sums8 seed 2: loop 94 vs plain 142 (-48, report-only).
- Seed variance on the plain arm: sums6 plain 197 (s1) vs 255 (s2), a 58-point swing with
  identical settings except the data seed.

## What it means (plain high-school English)

- The round-thinking net clearly beat its plain twin on bigger grid puzzles both times
  (grids6: +67 and +76 out of 300) and on bigger sums once (+59), while never falling behind on
  the sizes it practised. Extra thinking time turned into bigger solved puzzles in those cases.
- But it failed the bar: on seed 2 the plain twin actually won bigger sums by 11, so the rule
  "pass on both seeds" is not met. One win and one loss means the result does not hold up.
- Neither net learned the number puzzles at all (about 1-4 right out of 300 even on the practised
  size), so that whole puzzle kind says nothing about round-thinking; it says the setup cannot do
  those puzzles yet.

## What it doesn't mean

- It does NOT mean round-thinking is useless: seed 1 passed every mark, and grids6 won big twice.
- It does NOT mean the plain net is better: it lost grids6 badly twice and never won numbers.
- It does NOT prove the idea wrong either: the proved-wrong clause (tiny gaps everywhere, both
  seeds) did not trigger, because several gaps were large.
- It does NOT say anything about harder puzzles (sums8/grids7 are report-only) or about giving the
  plain net extra compute some other way (that was never tested here).
