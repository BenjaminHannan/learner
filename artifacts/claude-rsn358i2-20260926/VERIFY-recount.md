# rsn-358i2 blind recount (sleep research thread, 2026-09-26 20:02 UTC)

## Verdict: SUSPECT CONFIRMED (V0, M1, M2 and M3 all met; proved-wrong not triggered). Agrees with the builder.

The autocast weight cache is what stopped 358i's loop from learning on the torch 2.8 rental. With the cache off, the same loop, code and schedule learn grids in the first 10,000 steps on every seed.

**Counted from:** the raw run files on origin/builder-outbox commit 624bfb13e (runs/loop-s{1..4}/tests.json, train_log.jsonl, train_summary.json), before reading the builder's RESULTS.md. Plain = 358i's runs/plain-s{1..4}/tests.json on origin/main, as PASSMARKS.md says. Marks: PASSMARKS.md in this folder. SEAL-code.sha256.txt: 19/19 lines match origin/main. I did not open the test folder.

| mark | rule | count | result |
|---|---|---|---|
| V0 | steps_block_nograd = 0 in every train_summary.json | 0 / 0 / 0 / 0 (60,000 steps seen on each seed) | met |
| M1 | dev grids5 at step 10,000 >= 100/200 on >= 3 of 4 seeds | 195 / 198 / 197 / 200 (358i loop: 0 / 1 / 2 / 1) | met, 4 of 4 |
| M2 | 4-seed mean loop - plain on grids5 >= -10 | 300.00 - 299.00 = +1.00 (358i: -77.5) | met |
| M3 | 4-seed mean loop - plain on grids6 >= -10 | 289.50 - 237.75 = +51.75 (358i: -83) | met |
| proved wrong | M1 <= 20 on >= 3 seeds AND grids5 gap <= -50 | 0 seeds; +1.00 | not triggered |

## Report-only rows (per seed, of 300)

| test | loop s1-s4 | plain s1-s4 | mean gap |
|---|---|---|---|
| sums4 | 300 300 300 300 | 300 300 300 300 | +0.00 |
| sums6 | 299 299 298 297 | 188 209 177 217 | +100.50 |
| sums8 | 273 274 276 278 | 133 116 65 146 | +160.25 |
| sums10 | 219 244 232 250 | 93 60 27 112 | +163.25 |
| sums12 | 164 202 193 198 | 65 44 7 89 | +138.00 |
| grids5 | 300 300 300 300 | 299 300 297 300 | +1.00 |
| grids6 | 292 296 283 287 | 230 248 237 236 | +51.75 |
| grids7 | 186 241 173 177 | 136 149 130 142 | +55.00 |
| numbers4 | 2 0 0 2 | 0 0 2 3 | -0.25 |
| numbers5 | 1 0 1 0 | 0 0 1 1 | +0.00 |

358t-style G0-G3 against plain (report only here): G0 met (sums4 and grids5 >= 210 on every seed of both arms); G1 met (sums6 +100.50, grids6 +51.75, numbers5 +0.00; loop ahead on sums6 and grids6 on 4 of 4 seeds); G2 met; G3 met on 4 of 4 seeds, and mean rounds on sums6 (7.22-8.22) are above sums4 (6.43-6.81) on every seed.

## Caveats, written into the verdict
1. **Two machines.** The loop ran on BensPC (RTX 5070 Ti, torch 2.11.0+cu128). Plain is 358i's run on a torch 2.8 rental RTX 5090. Plain never runs no-grad rounds, so the bug cannot touch it, but GPU, torch version and numerics differ. The loop-minus-plain rows are therefore **suggested**, not shown, until plain seeds 1-4 are rerun on BensPC (sealed next, $0).
2. **What is shown:** the fix. The loop learns grids early (M1) on every seed with the cache off, where it did not with the cache on. That comparison is loop vs loop, and it still crosses machines, but the CPU test (artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md) shows the mechanism directly.
3. **Neither net learned number puzzles** (0-3 of 300 on both arms), so numbers rows say nothing about loop vs plain.
4. grids5 is at the ceiling for both arms (300 vs 299), so M2 only says "no longer behind".
5. Seed 1's first attempt died at about 11,000 steps when the builder stopped its parent process; it restarted clean, and only the clean run is counted.

The builder's plain-English line "learns exactly as fast as plain" undersells M1 (loop 195-200 vs 358i plain's 160-174 at step 10,000); the numbers above are the record.
