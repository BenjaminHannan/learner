# Result status

Updated 2026-09-27T23:23:29Z. **No maze verdict yet.**

**Shown:** the rank-eight patch net is built and the eight construction checks
passed in fp32 on the local Apple GPU. Independent Sol recount agrees with the
weight inventory and 20 of 20 recorded nonzero matrix gradients. Total size is
1,652,767 coefficients, 0.428% above our no-label loop, including the 4,096
persistent A/B coefficients. See CHECKS.md and BLIND-RECOUNT.md.

**Shown:** the independent plain-loop qualification pilot passed all six sealed
kinds: sums 300 of 300, grids 287 of 300, sorting 300 of 300, reversing 296 of
300, counting 300 of 300, and bracket completion 300 of 300. No kind was dropped.
A separate Sol subagent independently regraded all 1,800 raw predictions and
matched the sealed counts and hashes (QUALIFICATION-RECOUNT.json). The
qualification checkpoint is separate from every race contender.

**Running:** two seeds of patch, ordinary loop, learning-to-learn loop, and
plain on the same qualified curriculum. These eight arms must separately pass
the sealed source and relative-retention gates. Source commit: `fd250b3be`.

**Untested:** few-example maze advantage, keeping old kinds after maze supports,
sleep absorption with the patch removed, and whether wider practice helps the
loop. There is no trained inference-speed claim yet. No contender is promoted.
The next test is the registered two-seed practice gate for all eight arms.

The ruler protocol and marks subsequently arrived at `3acb5d18a`, with its
pre-maze execution corrections at `93e9ccba2`. ADDENDUM-wide-practice.md records
our wider source practice, unchanged Test A thresholds, and the user's local
GPU requirement. The design race also requires the ruler to pass V1–V3.
The plug-in and gated race driver are preparation, not maze results.

## Running and resuming

The managed background tool session is 89443; its training PID is 92662.
LAUNCH.json records the start and command. STATUS.json records completion or
failure, background.log holds the output, and each run writes checkpoints every
1,000 source steps and 100 episodes. The launch record also records an initial
detached process that did not remain running; it produced no training output.

Do not start a duplicate while the recorded training PID is alive. If it exits
unexpectedly, inspect STATUS.json and the exact error before resuming the same
sealed command. The runner resumes its own saved optimizer and random states;
it refuses changed sealed sources. Do not remove or rewrite the candidate seal.
Stop a job only by its exact PID. No other chat's files or processes belong here.

After completion, run claude_patch_recount.py against the new raw panels and
have a separate Sol agent review that recount from raw files and marks. Commit
qualification/results and the recount. Check main for the race protocol; if it
is absent and the net is ready, give Ben the requested short report and stop.
If it is present, reconcile it with the sealed source recipe and commit the
wide-practice addendum before any maze run. No race execution is in the source
practice runner.
