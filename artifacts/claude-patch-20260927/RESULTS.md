# Result status

Written 2026-09-27T22:38:12Z. **No maze verdict yet.**

**Shown:** the rank-eight patch net is built and the eight construction checks
passed in fp32 on the local Apple GPU. Independent Sol recount agrees with the
weight inventory and 20 of 20 recorded nonzero matrix gradients. Total size is
1,652,767 coefficients, 0.428% above our no-label loop, including the 4,096
persistent A/B coefficients. See CHECKS.md and BLIND-RECOUNT.md.

**Running:** the sealed wider-practice qualification pilot, followed automatically
by two seeds of patch, ordinary loop, learning-to-learn loop, and plain only if
qualification passes. Candidate kinds: sums, Latin grids, sorting, reversing,
counting, bracket completion. Source commit: `fd250b3be`.

**Untested:** few-example maze advantage, keeping old kinds after maze supports,
sleep absorption with the patch removed, and whether wider practice helps the
loop. There is no trained inference-speed claim yet. No contender is promoted.
The next test is the registered six-kind qualification gate, not a maze trial.

The last pull and tracked-file check found no test-chat PROTOCOL.md or
RACE-PASSMARKS.md committed to main. Do not run a race or invent its pass marks.
No ADDENDUM-wide-practice.md has been committed against an absent protocol.

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
