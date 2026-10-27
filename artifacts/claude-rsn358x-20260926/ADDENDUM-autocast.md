# rsn-358x addendum: loop arms trained under the autocast cache bug (sleep research thread, 2026-09-26 20:02 UTC)

The registered verdict stands and is not rewritten: FAIL, proved-wrong clause fired (origin/builder-outbox b579be424, RESULTS.md).

**Recount (sleep research, from carry_summary.json on b579be424):** steps-to-bar (first dev check with maze7 >= 150/200; 5000 = never by 4,000 steps)
- loop-pre 5000 / 5000 / 5000 / 5000; loop-fresh 5000 / 5000 / 5000 / 5000;
- plain-pre 750 / 750 / 1000 / 750; plain-fresh 2000 / 2000 / 2000 / 2000.
- X0 met, X1 FAIL (ratio 1.00), X2 FAIL (ratio 6.15). Agrees with the builder.

**What is now known:**
- The run used torch 2.8.0+cu128 on a rental RTX 5090 (RESULTS.md line 124), and scripts/claude_rsn358x_run.py:77-107 runs loop_train's no-grad rounds inside the bf16 autocast block. That is the configuration rsn-358i2 confirmed as the bug.
- Both loop starts were hit: loop-fresh trained under the bug in this run, and loop-pre started from 358i's checkpoints, which were also trained under it.
- Loop-fresh never reaching the bar while plain-fresh reaches it at 2,000 steps on every seed is what the bug predicts.
- So the proved-wrong claim applies only to loops trained under the bug. Whether a correctly trained loop carries practice over is untested. The rerun on BensPC (after 358i2's loops, which it can start from) is on the Director's board.
