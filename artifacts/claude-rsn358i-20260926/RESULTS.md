# rsn-358i RESULTS (builder, 2026-09-26, rental rent-358i, RTX 5090)

## Verdict: INCONCLUSIVE

G0 validity is NOT met: loop seed 4 scores 122/300 on grids5 (practised size), so on seed 4 the loop arm
reaches >= 210/300 in only 1 of the 3 practised-size kinds (sums4 298; grids5 122; numbers4 1).
PASSMARKS.md: anything not PASS with G0 unmet is INCONCLUSIVE. G1 FAIL, G2 FAIL, G3 PASS.
The proved-wrong clause did NOT trigger (it needs G0 met).

## Marks (300 items per test; PASSMARKS.md 2026-09-26)

| mark | result |
|---|---|
| G0 validity (every seed, both arms >= 210/300 in >= 2 of sums4/grids5/numbers4) | FAIL -> INCONCLUSIVE. Plain s1: 300/299/0 OK; s2: 300/300/0 OK; s3: 300/297/2 OK; s4: 300/300/3 OK. Loop s1: 299/256/0 OK; s2: 299/239/2 OK; s3: 300/269/0 OK; s4: 298/122/1 NOT (1 of 3). |
| G1 bigger (4-seed mean loop-plain >= +30 on >= 2 of sums6/grids6/numbers5 and >= -10 on third; AND > 0 on >= 3/4 seeds on each of those >= 2 tests) | FAIL. Means: sums6 +41.25 (pass); grids6 -83.00 (fail); numbers5 -0.50 (fail). Only 1 of 3 hits +30. Per-seed diffs: sums6 +32/+46/+19/+68 (4/4 > 0); grids6 -50/-90/-19/-173 (0/4); numbers5 0/0/-1/-1 (0/4). |
| G2 practised (4-seed mean loop-plain >= -10 on each of sums4/grids5/numbers4) | FAIL. sums4 -1.00 (pass); grids5 -77.50 (fail); numbers4 -0.50 (pass). |
| G3 stop (on >= 3/4 seeds: loop own-stop >= loop fixed-16 - 5 on each bigger test, and mean rounds sums6 > sums4) | PASS 4/4. s1: 220>=217, 180>=172, 0>=-5; 6.28>5.71. s2: 255>=253, 158>=144, 0>=-5; 6.13>5.56. s3: 196>=189, 218>=185, 0>=-5; 5.87>5.16. s4: 285>=278, 63>=56, 0>=-5; 6.21>5.58. |
| Overall | INCONCLUSIVE (G0 unmet; G1/G2 fail, G3 pass) |

Proved-wrong clause ("for this design": G0 met AND mean loop-plain <= +5 on all three bigger tests):
G0 is not met, so NOT triggered regardless of counts (means are sums6 +41.25, grids6 -83.00, numbers5 -0.50).

## Per-seed tables (n = 300; plain right, loop right at own stop, loop - plain)

Seed 1:

| test | role | plain | loop (own stop) | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 299 | -1 |
| sums6 | bigger | 188 | 220 | +32 |
| sums8 | report | 133 | 163 | +30 |
| grids5 | practised | 299 | 256 | -43 |
| grids6 | bigger | 230 | 180 | -50 |
| grids7 | report | 136 | 104 | -32 |
| numbers4 | practised | 0 | 0 | 0 |
| numbers5 | bigger | 0 | 0 | 0 |
| sums10 | report | 93 | 140 | +47 |
| sums12 | report | 65 | 97 | +32 |

Seed 2:

| test | role | plain | loop (own stop) | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 299 | -1 |
| sums6 | bigger | 209 | 255 | +46 |
| sums8 | report | 116 | 197 | +81 |
| grids5 | practised | 300 | 239 | -61 |
| grids6 | bigger | 248 | 158 | -90 |
| grids7 | report | 149 | 81 | -68 |
| numbers4 | practised | 0 | 2 | +2 |
| numbers5 | bigger | 0 | 0 | 0 |
| sums10 | report | 60 | 162 | +102 |
| sums12 | report | 44 | 120 | +76 |

Seed 3:

| test | role | plain | loop (own stop) | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 300 | 0 |
| sums6 | bigger | 177 | 196 | +19 |
| sums8 | report | 65 | 121 | +56 |
| grids5 | practised | 297 | 269 | -28 |
| grids6 | bigger | 237 | 218 | -19 |
| grids7 | report | 130 | 121 | -9 |
| numbers4 | practised | 2 | 0 | -2 |
| numbers5 | bigger | 1 | 0 | -1 |
| sums10 | report | 27 | 104 | +77 |
| sums12 | report | 7 | 74 | +67 |

Seed 4:

| test | role | plain | loop (own stop) | loop - plain |
|---|---|---|---|---|
| sums4 | practised | 300 | 298 | -2 |
| sums6 | bigger | 217 | 285 | +68 |
| sums8 | report | 146 | 258 | +112 |
| grids5 | practised | 300 | 122 | -178 |
| grids6 | bigger | 236 | 63 | -173 |
| grids7 | report | 142 | 15 | -127 |
| numbers4 | practised | 3 | 1 | -2 |
| numbers5 | bigger | 1 | 0 | -1 |
| sums10 | report | 112 | 238 | +126 |
| sums12 | report | 89 | 218 | +129 |

4-seed means (right/300):

| test | plain mean | loop mean | loop - plain mean |
|---|---|---|---|
| sums4 | 300.00 | 299.00 | -1.00 |
| sums6 | 197.75 | 239.00 | +41.25 |
| sums8 | 115.00 | 184.75 | +69.75 |
| grids5 | 299.00 | 221.50 | -77.50 |
| grids6 | 237.75 | 154.75 | -83.00 |
| grids7 | 139.25 | 80.25 | -59.00 |
| numbers4 | 1.25 | 0.75 | -0.50 |
| numbers5 | 0.50 | 0.00 | -0.50 |
| sums10 | 73.00 | 161.00 | +88.00 |
| sums12 | 51.25 | 127.25 | +76.00 |

## Loop at fixed rounds (right/300; own = learned stop; any = right at any of the probed rounds)

Seed 1 loop:

| test | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | own | any | mean rounds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 296 | 298 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 5.71 |
| sums6 | 211 | 216 | 222 | 219 | 222 | 222 | 222 | 222 | 222 | 220 | 238 | 6.28 |
| sums8 | 148 | 156 | 162 | 160 | 159 | 159 | 159 | 159 | 159 | 163 | 179 | 6.70 |
| grids5 | 71 | 132 | 181 | 231 | 251 | 257 | 262 | 266 | 262 | 256 | 273 | 13.24 |
| grids6 | 34 | 75 | 121 | 155 | 166 | 177 | 184 | 184 | 182 | 180 | 198 | 26.14 |
| grids7 | 5 | 25 | 62 | 83 | 96 | 100 | 95 | 95 | 96 | 104 | 115 | 35.00 |
| numbers4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12.90 |
| numbers5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.23 |
| sums10 | 123 | 129 | 140 | 137 | 137 | 136 | 136 | 136 | 136 | 140 | 157 | 7.05 |
| sums12 | 88 | 95 | 101 | 96 | 95 | 95 | 95 | 95 | 95 | 97 | 109 | 7.46 |

Seed 2 loop:

| test | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | own | any | mean rounds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 289 | 299 | 300 | 299 | 298 | 298 | 298 | 298 | 298 | 299 | 300 | 5.56 |
| sums6 | 238 | 252 | 257 | 256 | 258 | 258 | 259 | 259 | 259 | 255 | 279 | 6.13 |
| sums8 | 194 | 209 | 213 | 188 | 187 | 187 | 188 | 186 | 186 | 197 | 237 | 6.45 |
| grids5 | 73 | 123 | 177 | 213 | 220 | 225 | 231 | 239 | 240 | 239 | 250 | 19.41 |
| grids6 | 29 | 77 | 116 | 142 | 146 | 149 | 155 | 157 | 160 | 158 | 168 | 28.85 |
| grids7 | 12 | 26 | 52 | 68 | 71 | 72 | 80 | 82 | 83 | 81 | 96 | 37.48 |
| numbers4 | 2 | 2 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 2 | 3 | 7.67 |
| numbers5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6.96 |
| sums10 | 162 | 174 | 171 | 160 | 158 | 158 | 157 | 157 | 157 | 162 | 203 | 7.06 |
| sums12 | 128 | 125 | 127 | 117 | 113 | 111 | 112 | 112 | 112 | 120 | 160 | 7.35 |

Seed 3 loop:

| test | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | own | any | mean rounds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 294 | 299 | 299 | 297 | 296 | 296 | 296 | 296 | 296 | 300 | 300 | 5.16 |
| sums6 | 186 | 188 | 195 | 198 | 194 | 194 | 193 | 193 | 193 | 196 | 215 | 5.87 |
| sums8 | 127 | 121 | 124 | 120 | 121 | 120 | 120 | 120 | 120 | 121 | 149 | 6.13 |
| grids5 | 81 | 132 | 190 | 250 | 264 | 270 | 279 | 281 | 281 | 269 | 281 | 10.52 |
| grids6 | 38 | 80 | 130 | 166 | 177 | 190 | 204 | 212 | 220 | 218 | 223 | 24.72 |
| grids7 | 7 | 23 | 59 | 86 | 102 | 109 | 120 | 128 | 132 | 121 | 134 | 34.62 |
| numbers4 | 1 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 12.18 |
| numbers5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7.55 |
| sums10 | 105 | 101 | 105 | 104 | 103 | 101 | 101 | 101 | 101 | 104 | 125 | 6.66 |
| sums12 | 82 | 70 | 74 | 74 | 74 | 75 | 76 | 76 | 76 | 74 | 94 | 6.87 |

Seed 4 loop:

| test | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | own | any | mean rounds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 292 | 299 | 299 | 298 | 295 | 295 | 295 | 295 | 295 | 298 | 300 | 5.58 |
| sums6 | 253 | 270 | 288 | 285 | 282 | 283 | 283 | 283 | 282 | 285 | 293 | 6.21 |
| sums8 | 205 | 229 | 250 | 258 | 252 | 252 | 249 | 249 | 249 | 258 | 264 | 6.49 |
| grids5 | 70 | 94 | 116 | 119 | 123 | 125 | 125 | 125 | 125 | 122 | 131 | 30.77 |
| grids6 | 30 | 43 | 66 | 64 | 63 | 61 | 62 | 62 | 62 | 63 | 80 | 38.46 |
| grids7 | 8 | 15 | 18 | 17 | 14 | 13 | 13 | 13 | 13 | 15 | 30 | 44.56 |
| numbers4 | 0 | 3 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 3 | 18.52 |
| numbers5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 11.33 |
| sums10 | 172 | 204 | 230 | 236 | 234 | 233 | 232 | 232 | 232 | 238 | 249 | 6.98 |
| sums12 | 141 | 166 | 207 | 221 | 215 | 210 | 209 | 209 | 209 | 218 | 234 | 7.34 |

## Report-only sizes (sums8/sums10/sums12, grids7)

Loop beats plain on every sums size at every seed, and the mean gap grows then holds:
sums8 +69.75, sums10 +88.00, sums12 +76.00 (means). Seed 4 (the grids-collapsed seed) is the best
sums seed at every report size (sums8 258, sums10 238, sums12 218). On grids7 the loop loses to
plain at every seed (mean -59.00); seed 4 grids7 is 15/300 own-stop (30 at any round).

## Comparison with 358a (origin/builder-outbox runs, 2 seeds; BensPC run)

Test files shared byte-identically with 358a: sums4, sums6, sums8, numbers4, numbers5
(verified sha256 identical to origin/main 358a tests). Grids files DIFFER (358i carries the 358g grid
legend fix), so grids counts are not apples-to-apples. sums10/sums12 are new in 358i (no 358a counts).

| test (shared files only) | 358a plain s1/s2 | 358a loop s1/s2 | 358i plain s1/s2/s3/s4 | 358i loop s1/s2/s3/s4 |
|---|---|---|---|---|
| sums4 | 300/300 | 300/300 | 300/300/300/300 | 299/299/300/298 |
| sums6 | 197/255 | 256/244 | 188/209/177/217 | 220/255/196/285 |
| sums8 | 78/142 | 88/94 | 133/116/65/146 | 163/197/121/258 |
| numbers4 | 1/2 | 3/4 | 0/0/2/3 | 0/2/0/1 |
| numbers5 | 1/0 | 1/2 | 0/0/1/1 | 0/0/0/0 |

358a loop-plain on shared bigger sums: s1 +59, s2 -11 (sums6). 358i loop-plain sums6:
+32/+46/+19/+68. 358a report grids (different files, for reference only): 358a loop grids6
270/265 vs plain 203/189; 358i loop grids6 180/158/218/63 vs plain 230/248/237/236.

## Compute

GPU: NVIDIA GeForce RTX 5090, 32607 MiB (vast.ai host, South Korea).
Minutes per run (train_summary.json): plain-s1 55.7, plain-s2 55.6, plain-s3 55.6, plain-s4 55.7;
loop-s1 75.3, loop-s2 75.2, loop-s3 75.4, loop-s4 75.4. All 8 trained concurrently on the one GPU
(~91% use, ~20 GB); wall clock first-launch to last-finish ~80 min.
Dollars: rental dph $0.48519. This rental ~1.6 h (~$0.78) plus two failed rentals that never left
loading (~$0.16 total est.); rsn-358i spend ~$0.94, under the $1.50 line and the $1.35 kill line.
Weights: loop 6438302, plain 6385149. Eval: once per checkpoint with the sealed command.

## Deviations (every one)

1. Two extra rentals before the working one (max 3 used): offer 46753300 (US, $0.4481) stuck in
   "loading" 6m45s, destroyed; offer 43165155 (US, $0.4481) stuck in "loading" ~7m, destroyed;
   third rental offer 49025089 (KR, $0.4852) ran. ~$0.16 of the $1.50 line went to the dead rentals.
2. Audit text has an extra clause per line ("checker accepts the stored answer on 300/300" after the
   required "300/300 puzzles show every needed symbol"); the required substring is present on all 4 lines.
3. rv-387 archive was copied to the rental early (during training) to save a later round-trip; its files
   were not touched until the rv-387 section (separate budget/cap below).
4. No code or test file was opened, printed, edited, or re-run beyond the sealed commands; eval ran exactly
   once per checkpoint. tests/ items were never printed (only counts from tests.json).
5. Time/budget kill lines were never reached, so no PIDs were killed and no seed was stopped (no TOO-SLOW).

## Repro

On the rental (no git checkout there): `git archive origin/main scripts
artifacts/claude-rsn358i-20260926` extracted keeping paths; `sha256sum -c
artifacts/claude-rsn358i-20260926/SEAL-code.sha256.txt` 17/17 OK; `python -B
scripts/claude_rsn358a_envs.py selftest` ("selftest ok"); `python -B scripts/claude_rsn358i_run.py
audit` (4 lines with "300/300 puzzles show every needed symbol"); `python -B
scripts/claude_rsn358i_run.py check-mask` ("check-mask ok"). Train: for s in 1 2 3 4, `python -B
scripts/claude_rsn358i_run.py train --arm loop --seed $s --out W/loop-s$s` and same for plain,
all 8 concurrently detached (setsid+nohup), logs W/<R>.log. Seal: sha256 of each final.pt (64 hex)
appended to SEAL-run.sha256.txt before eval. Eval once per ckpt: `python -B
scripts/claude_rsn358i_run.py eval --ckpt W/<R>/final.pt --tests
artifacts/claude-rsn358i-20260926/tests --out W/<R>/tests.json`. Runs copied to
artifacts/claude-rsn358i-20260926/runs/<R>/ (train_log.jsonl, train_summary.json, tests.json, train.log).
SEAL-run.sha256.txt:
f916b8b562379c583d9e98164f65d7dbdc95610a3b1df07b7c8d078c42745832  W/loop-s1/final.pt
1f9b68c113c8749ce0414486b546b4ef64d89bfb166b887c6e3f707048e858c5  W/loop-s2/final.pt
7bb0a62fd5c2ae63cac389c54c8d83d1cdc6949fb9b12f0a043a334169959fa4  W/loop-s3/final.pt
088f49d1cf9f8ed52689ef500ca21b9ff63102e586198e926ad4882def66cb26  W/loop-s4/final.pt
3c0b7983774c38249257f085a8191bfe77858a546cc133b5c72bcdaffb37945b  W/plain-s1/final.pt
7741354a3e1e29f11dce0b92f9eefbe40f7045e3625cdfceab57c658e60a76e7  W/plain-s2/final.pt
62616c0c695d1837107427143882a8abad9377ed6cca038f1bf2bbf1ab2ad2e8  W/plain-s3/final.pt
a67b7177320a2def07236d93316c18e23545a2bad63f7b151981b358c9434304  W/plain-s4/final.pt
