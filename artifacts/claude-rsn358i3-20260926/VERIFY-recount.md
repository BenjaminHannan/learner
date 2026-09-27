# rsn-358i3 blind recount (sleep research thread, 2026-09-27 00:53 UTC)

## Verdict: PASS (V0, G0, G1, G2, G3 all met; proved-wrong not triggered). Agrees with the builder.

**What is now shown:** the bug-fixed 358i loop (2 x d512) beats its same-size plain twin (8 x d256, about 6.4M weights each) on bigger puzzles than it practised: sums6 and grids6, fresh seeds 5-8, both nets trained on the same machine (BensPC, torch 2.11.0+cu128). This holds for these puzzle kinds at this size. Number puzzles were learned by neither net.

**Counted from:** raw runs/*/tests.json and train_summary.json on origin/builder-outbox c06390585, before reading the builder's RESULTS.md. Marks: PASSMARKS.md (358t's PASSMARKS-v2 G0-G3 word for word). SEAL-code.sha256.txt 19/19 OK on main; SEAL-run has 12 lines.

| mark | count | result |
|---|---|---|
| V0 | steps_block_nograd 0 / 0 / 0 / 0 (60,000 steps each) | met |
| G0 | sums4 300 and grids5 298-300 on every run of both arms | met |
| G1 | mean loop - plain: sums6 +124.00, grids6 +52.00, numbers5 +0.00; loop ahead on sums6 and grids6 on 4 of 4 seeds | met |
| G2 | sums4 +0.00, grids5 +1.50, numbers4 +0.75 | met |
| G3 | own stop >= fixed-16 - 5 on every bigger test on 4 of 4 seeds; mean rounds sums6 > sums4 on every seed | met |
| proved wrong | needs every bigger gap <= +5 | not triggered |

Per seed (loop / plain, of 300), s5-s8:
- sums6: 299/218, 296/125, 289/179, 296/162.
- grids6: 296/248, 294/241, 284/234, 295/238.
- Report only: grids7 mean gap +67.75, sums8 +185.75, sums10 +160.75, sums12 +129.50.

**Report only, the machine check:** plain seeds 1-4 retrained on BensPC vs 358i's rental plain seeds 1-4 differ by at most 10 per test (sums12 +9.75, sums10 +8.00, all else within 3.00). Against BensPC plain, the 358i2 loop gaps are sums6 +102.00 and grids6 +54.00 (vs +100.50 and +51.75 against rental plain). So the 358i2 rows now also stand on one machine.

**Builder deviations read:**
- The first two launches died when the SSH session closed, and were restarted with a launch method that survives disconnect. Only clean runs were counted.
- GPU-BUSY was left to the watcher.
- Each eval ran once per checkpoint.
None changes the count.

**Prediction was PASS 70%.** This clears the exit rule's CONTINUE branch for the loop design, and it is the verified loop PASS that 358b3 (the chat-puzzle gate) was waiting for.
