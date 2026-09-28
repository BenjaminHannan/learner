# Result status

Updated 2026-09-28T05:11:51Z. **Both patch seeds fail the grid practice gate; no maze verdict.**

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

**Shown:** patch seed 927401 completed all 18,000 source batches and 2,000
episodes. On the sealed verification panels it scored sums 300 of 300, grids
278 of 300, sorting 297 of 300, reversing 289 of 300, counting 298 of 300,
and brackets 300 of 300. Grids required 285 of 300, so this implementation is
not race-eligible under the registered recipe. Independent Sol raw recount
confirmed all six scores and panel identities (FIRST-ARM-RECOUNT.md). All eight trained construction
checks passed, including 20 of 20 finite nonzero matrix gradients.

**Suggested:** stopping contributes to this source failure: grid accuracy at
fixed depth 48 is 288 of 300. The saved trajectories correct ten grid answers
that were wrong at the learned stop, with no grid answers changing from correct
to wrong; those ten stopped at rounds 6–12. See patch-927401/stop-diagnostic.json.
This diagnostic cannot replace the registered eligibility score. No stopping rule, budget, or
training recipe is changed in response to these results.

**Shown:** the ordinary loop on paired seed 927401 has completed the same
source training and scored grids 274 of 300. The patch scored 278 of 300,
four more, while both missed the 285-of-300 gate. Its other five kinds passed
their absolute marks. FIRST-PAIR-STATUS.json records all six paired counts.

**Shown:** the episodic loop control on seed 927401 scored grids 282 of 300,
versus the patch’s 278 of 300. Both scored 288 of 300 at fixed 48 rounds,
and both failed the learned-stop grid gate. The patch is within nine of 300
of both own loop controls on every kind. The controls received the same 18,000
source batches and 2,000 episodes. FIRST-PRIMARY-CONTROL-STATUS.json records
the six paired scores.

**Shown:** seed 927401's plain control also finished and scored grids 164 of
300. Thus every seed-1 arm misses the grid gate: patch 278, ordinary loop 274,
episodic loop 282, plain 164, each of 300 against 285. All four arms pass the
other five kinds' absolute marks; the patch stays within nine of 300 of both
paired loop controls on every kind. The first seed's complete counts are in
SEED1-STATUS.json. This registered run cannot enter the maze race.

**Shown:** patch seed 927402 finished its registered 18,000 source batches and
2,000 episodes. It scored sums 300 of 300, grids 272 of 300, sorting 296 of
300, reversing 293 of 300, counting 298 of 300, and brackets 300 of 300 on
sealed verification. Grids again miss 285 of 300. Fixed depth 48 reaches only
280 of 300 grids for this seed. All eight trained construction checks passed.
A separate raw-row recount of its development and verification files matched
every reported selected and fixed-48 count (SECOND-PATCH-RECOUNT.json). This
recount was done by the lead; the requested separate Sol blind audit follows
the full two-seed run.

**Shown:** the ordinary loop on seed 927402 scored grids 272 of 300, exactly
the patch's 272 of 300. Its other five verification kinds also pass their
absolute marks. The patch is within nine of 300 of this control on every kind,
but both miss the grid gate. SECOND-PAIR-RECOUNT.json independently grades all
development and verification raw rows for both arms and matches the recorded
selected and fixed-48 counts. No maze advantage follows from a tied source
score.

**Shown:** the seed-2 episodic loop scored grids 260 of 300, versus the patch's
272 of 300. Both miss 285 of 300; the patch remains within nine of this
control on all six kinds, and both pass the other five absolute marks.
SECOND-PRIMARY-CONTROL-RECOUNT.json regrades all development and verification
raw rows for the patch and episodic loop, including fixed-48 counts.

**Running:** the last seed-2 plain control on the same qualified curriculum.
It will complete the registered comparison but cannot reverse the patch seeds'
failure.

**Untested:** few-example maze advantage, keeping old kinds after maze supports,
sleep absorption with the patch removed, and whether wider practice helps the
loop. There is no trained inference-speed claim yet. No contender is promoted.
The remaining registered work is the two-seed practice comparison. The known
first-seed grid failure already prevents a race under this registration.

The ruler protocol and marks subsequently arrived at `3acb5d18a`, with its
pre-maze execution corrections through `aeb524cd0`. ADDENDUM-wide-practice.md records
our wider source practice, unchanged Test A thresholds, and the user's local
GPU requirement. The design race also requires the ruler to pass V1–V3. Its original plain
baselines failed the grid guard; ADDENDUM-3 registers matched 12,000-step
qualification and a fresh guard before any maze scores. Our sealed source
training recipe is unchanged.
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
