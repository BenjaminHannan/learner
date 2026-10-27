# rsn-358t pass marks v3 (2026-09-26 17:20 UTC, sleep research thread; fixed before any v3 run)

**Registered state of v2.** 358t v2 (PASSMARKS-v2.md, sealed 657cc4f41) is STOPPED WITH NO VERDICT.
- Its builder exited rc=2 after losing SSH on the third of its 3 rentals (builder-outbox afa29fe17), and no eval ran.
- The rental image was pytorch/pytorch:2.8.0 (its err.txt).
- Its partial logs support the autocast cache bug (artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md): dev at step 5,000 was loop-trm s1 sums4 0/200, grids5 0 (grids5 still 0 at 10k); loop8 s1 67/1; loop8 s2 93/0. 358i's plain at the same step: sums4 >= 190, grids5 100-136.
- On CPU with torch 2.8, a loop-trm segment leaves 8/8 block Linear weights without gradient, and loop8 32/32. So under that bug neither arm could test its idea.

**v3 = v2 with one repair and nothing else.** scripts/claude_rsn358t3_run.py imports 358t unchanged and turns the autocast weight cache off (as in rsn-358i2), with gradient logging.
- The arms, schedule, EMA, seeds, steps, tests and marks G0-G5 are those of PASSMARKS-v2.md, word for word.
- Plain is still 358i's own plain (unaffected by the bug).

**Added validity mark V0:** steps_block_nograd = 0 in every graded run's train_summary.json. Otherwise that test is INCONCLUSIVE.

**Order:** v3 runs only after rsn-358i2 reports. If 358i2 is confirmed or partial, v3 goes ahead. If 358i2 proves the cache suspect wrong, v3 is re-planned before it runs.

**Predictions** (made before any v3 run, higher than v2's 30%/25% because v2's arms could not learn):
- loop-trm PASS 35%;
- loop8 PASS 35%.

**Cost:**
- 10 runs, as in v2: 4 loop-trm, 4 loop8, 2 loop8-trm.
- Rental: about $1.60 cap, like v2. Whether 358t's unspent approved money covers it is Ben's call, through the Thread manager.
- BensPC: $0 if it is free after 358i2. Only on torch 2.11 or later, where the bug does not occur; the flag is harmless there.
