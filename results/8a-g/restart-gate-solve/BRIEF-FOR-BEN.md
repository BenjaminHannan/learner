# Restart check (trace A): what's wrong with it, the fix, and the one decision for you (2026-10-17)

**The short version.** The accum-8 run was stopped by a check whose limit was set before anyone measured how much an honest restart drifts on your card. The record says the 0.0282 it saw is most likely honest drift. There is a ~10-minute test that settles it, already built into the supervisor. It needs your go to halt the (already stopped) supervisor first. Nothing is deleted.

**What trace A is for.** The supervisor stops the run on purpose at update 150 and restarts it from the save at update 100. Trace A checks that the save held everything, so the restarted run is a genuine continuation. The graphics card never adds numbers in exactly the same order twice. So even two perfect continuations drift apart a little. The real question is whether the restart is further from the original than one honest rerun is from another. The 0.02 limit was picked from a CPU test that had zero drift, so it was a guess.

**What I propose (a recommendation; changing any bar is your call):**
1. **While the run is going:** stop the run only for things a broken save shows immediately. That means the first redone update not matching exactly (it matched exactly at accum 4), the next two updates drifting by more than 0.005, NaN, or the loss not falling. I tested this on the CPU by breaking the save on purpose in eight ways. Every break showed up in those first three updates, while the average drift missed one of them completely. So the average and largest drift get written down, not used to stop the run.
2. **Before the result counts:** run the probe. It restarts from the save at update 200 twice and compares the two restarts with each other (that is the honest drift) and with the original run. The result counts only if the original-vs-restart drift is no bigger than about twice the restart-vs-restart drift. If that one check is borderline, two more restarts (about 10 more minutes) settle it before anyone calls the run broken. The limit then comes from your card's measured drift, not from a guess.
3. If you'd rather keep a hard limit on the average while the run is going: **0.05 for accum 8**, until the probe has measured the real drift. 0.0282 is under it.

**My verdict on 0.0282:** inside honest drift. That is **likely, not yet proven.** Accum 4 drifted 0.0167 on the same card, and the diagnosis says doubling the micro-batches should raise drift by 1.4-2×. That predicts 0.024-0.033, and 0.0282 is right in the middle. The probe turns "likely" into "shown" or "wrong". The rule for reading the probe was written down and committed before any probe number exists.

**What I found that needs care before the probe runs:**
- The probe command in the README points at a folder holding the **accum-4** save. Run as written for accum 8, it would give a false FAIL. Copy accum-8's own step-200 save into a new folder first. The draft code adds a guard against this.
- If the accum-8 run is ever continued, its step-200 save gets deleted (only the newest two are kept). So copy it before anything else happens.

**Decisions that are yours:**
1. **Go to halt the supervisor so the probe can run** (removes `ARMED.txt`; deletes nothing; about 10 minutes of card time; $0).
2. Whether to adopt the new check (points 1-2 above), or the 0.05 limit.
3. If the probe passes: continue the accum-8 run from update 300 (the cheapest option; the pack already supports it), or start it fresh.

**Not recommended:** making the GPU deterministic or switching to fp32 just to pass this check. Either one slows training by an untested amount, changes the recipe, and isn't needed for what the result is compared against. Seed-to-seed differences are far bigger than this drift.

**What would prove me wrong:** the two probe restarts come out **exactly identical** to each other but different from the original. Then the drift isn't the card's rounding at all, and something about restarting really does change the run.
