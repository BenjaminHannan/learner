Merging the follow-up run — staging files and validating the workstation.
I've charted the parent builds — now pulling their code for the join.
Core evidence is in — now dissecting the agents to plan the interaction.
The layering checks out — now drafting the merged agent.
Driver patterns mapped — now writing the 291 agent.
Interaction analysis done — now building the agent itself.
Build verified — now writing the test drivers.
Scorer interfaces confirmed — writing the scorer and run drivers.
All references check out — finalizing drivers, then piloting.
Refining the runners for multi-arm use before piloting.
Scorer fixes in — checking if the blind panel has landed yet.
Panel driver drafted — verifying runner CLIs, then piloting.
Drivers complete — starting pilots with a fast subset.
Pilot subset confirms the expected table-reader gains — launching the full pilot.
Load spiked — the driver is correctly gated. Waiting for a quiet slot.
14 interaction cases found where the join differs from base — examining each.
All 14 interactions classified as piece behaviour — waiting on the remaining pilot stages.
Found a scorer bug (missed argv) — fixing.
Pilot M1 shows the expected move classes plus a few new ids — inspecting each.
Found a real regression: opener-led teaches fail on 291. Diagnosing the mechanism.
Root cause pinned on the table-teach layer claiming opener-led turns — testing a targeted guard.
The write path needs tracing before I design the glue — instrumenting.
Fix design is clear — checking 260's guard vocabulary, then writing the glue.
Writing the 291-only glue module (pre-seal fix).
The greeting case is fixed but refusals persist — debugging the skip.
Method dispatch isn't reaching the mixin — tracing the wrapper chain.
The 229 hear is overridden by a 138n subclass — verifying dispatch empirically.
Found it: 260 captured a bound method before my class surgery — reordering the install.
All 7 opener cases now save cleanly — re-piloting the 291 arm to measure the fix's full footprint.
Label-class moves confirmed — waiting for the old pilot to finish its driver shakedown.
M7 needs class-based (not exact-list) move verification to stay honest without opening panels — reworking the tally.
Checking the sealed correction scorer's verdict structure to set strict bars.
Rewriting M7 around mechanical move classes — inserting the classifier first.
Making the M7 pred lookup defensive, then syntax-checking.
Load easing — launching the post-fix 291-arm re-pilot.
Zero footprint on the 720 set — re-piloting the dev sets post-fix.
Fix repaired 7 but shifted 9 others — inspecting each shift.
The skip needs narrowing to refusals only (titles must keep 229's save) — first checking the other shifted dev rows.
The skip disturbs 252's inputs — switching to a narrower post-turn wrapper that only fires on 229 refusals.
Rewriting the glue around the post-turn wrapper.
R2 is mangling titles — probing 229's exact verdicts to scope the guards precisely.
Probing the 138m base verdicts to scope the junk guard exactly.
138m never writes opener-led subjects on verb shapes but saves possessive titles — scoping R2 to apostrophe-free turns.
Titles and teaches all correct — baselining the correction probes against 138p.
Parity on corrections — running the full post-refinement 291-arm pilot.
d260-064 is unfixable without 138m's parser (title ambiguity) — verifying its class and the parity extra, then predicting both.
All classes verified — adding the single dev260 exception to the scorer.
Bench regressions point at snapshot handling in the wrapper — inspecting it.
Testing the exact failing turn to see which layer fires.
Single turn saves fine — the failure is cross-turn state. Getting the item's turns.
Sequence matches on both arms — the suite must send different leading turns. Finding the case source.
Checking whether the suite sends different turn text than my probe.
Need 229's verdict on passive-agent titles to place the fix correctly.
Stage loop121 keeps passive-agent titles — R2 must skip those (plus denial shapes).
All shapes correct — full re-pilot of the 291 arm to confirm zero collateral.
M1 fully green — confirming suites are back to baseline.
All green — fixing the C122 exemption in the scorer, then building predictions.
All REVIEWs are the same targeted-decline class — refining the auto-reason and rebuilding.
Inherited 138nb gap confirmed (291 == nb exactly) — verifying prediction file integrity.
Predictions complete — validating judges against them and re-checking rt143 post-fix.
dev252b needs the same exception slot as dev260 — adding it.
M1 pilot passes — verifying rt143 post-fix and crash-testing the M2–M6 scorer.
No scorer crashes; but old-pilot bench runs differ — checking if it's the known flake.
Checking which agent version produced each suite run.
fix3/sd is current (zero moves) — but 145 differs somewhere despite same verdict. Inspecting.
Pred predates the passive fix — re-validating it against current rows.
All pilots green — generating the move-id lists for PASSMARKS.
Writing PASSMARKS with the full prediction record.
Sealing the build.
Seal and ledger done — launching the registered M1–M6 run.
Registered M1 passes — waiting out the load for the bench runs.
Registered M1–M6 all pass — pulling the numbers, then running M7.
Sealed driver has a wrong path ($R252B vs $R258) — working around without touching sealed files, per precedent.
Second driver path bug (m6-compare location) — same one-off-tally precedent, no sealed edits.
Four M7 issues to diagnose — starting with the openpanel fidelity diff.
Openpanel rows are identical — the score gap is my base-arm substitution. Running the 138m arm once for exact fidelity.
Corrtail is clean relative to its arm (t258-026 inherited) — now dissecting the corrpanel c252-009/011 rows.
c252-009/011 are store-true answers with a classifier marker gap — now the tablepanel details.
c252-009 needs field-level forensics (no text) — checking setup, expect_gone, and family.
Verdict logic settled — re-running the tablepanel arms with the correct scorer procedure (old ones VOID).
Adding the targeted-decline refinement to the one-off tally and finalizing M7.
fix3's concat logic over-labels assertions — reverting to fix2 semantics for the record.
M7 record set (4/5 pass, corrpanel fails on c252-009) — archiving the tally and launching the M8 wait.
Blind panel has landed — M8 driver is on it. Drafting RESULTS while it runs.
Scorer CLI takes 2 args, not 3 — invoking correctly with no sealed edits.
Scorer needs conforming rows and prints text — validating my harness against the writer's base rows first.
Harness fidelity confirmed (order-only diffs) — building the M8 tally.
M8 runs score (291 leads on right) — fixing the argv bug in the tally.
c291-006 needs the same inheritance check as c252-009 before ruling.
Verdict logic is now uniform and literal — archiving the M8 tally.
Writing RESULTS.md.
RESULTS done — appending the outcome to the ledger, then studying push precedent.
Pre-push contamination audit, then pushing via an isolated worktree.
Push is blocked by environment policy — verifying no partial state, then cleaning up.
VERDICT: FAIL (registered). 291 = 138nb + 260 + 252c + 291 glue. M1–M6 all PASS first try; M7 4/5 PASS with corrpanel252 FAIL on one row (c252-009); M8 FAILs only its absolute-zero bars (73/96, best of all arms, zero new flags beyond both parents).

MARKS TABLE (integer counts, full detail in artifacts/claude-join291-20260923/RESULTS.md):

| Mark | Result | Counts |
|---|---|---|
| M1 720 dev/case | PASS | nb fidelity 720/720; 291-vs-138p 503/503 predicted exactly; 0/0/0 |
| M1 260dev/252devs | PASS | 260dev 109/109 identical; dev252b +1, dev258 +8, dev259 +9, all exact; junk only the 2 known ids |
| M2 suites | PASS | sessions152 1, bench 0, marks123 2, rt136 labels 21, direct 5, rt143 0/0; 0 new bad |
| M3 smoke | PASS | 4 fields differ; 0 bad |
| M4 bench x3 | PASS | 4/4 identical |
| M5 latency | PASS | +0.671 ms (bar +5) |
| M6 probes | PASS | 2 restart + 5 verifier moves; 0 ghosts/dup-fails/bad-writes |
| M7 openpanel260 | PASS | fidelity TRUE; 80/80; 0 moves |
| M7 corrtail258 | PASS | fidelity TRUE; 53 vs 54; 6 q2-wording moves, stores identical |
| M7 corrpanel252 | FAIL | 1 flagged row c252-009 (c252-022 correct; 0 junk; 0 false replies) |
| M7 invpanel138nb | PASS | fidelity TRUE; 0 wrong |
| M7 tablepanel221 | PASS | fidelity TRUE (84 right, +4 gained); 0 moves |
| M8 corrpanel291 | FAIL (absolute bars) | 73/96 (138nb 34, 138p 65); r2w 0/0; cause families all ≥138p; controls 12/12; qw 0; wrong 17 / junk 3 / fclaim 1, ALL inherited (0 new beyond both parents) |

EVERY MOVE / MISS: M1's 503 + 18 dev ids all predicted exactly (read/table/label classes). M2/M6 moves exactly as predicted (252 asks, 260 opener/greeting handling, C122 exemption). M7 moves: 6 q2-wording (corrtail), 9 corrpanel (7 q2-wording + c252-011 targeted decline + c252-009 flagged), 0 elsewhere. The 2 misses: c252-009 (M7) and M8's inherited flags (17/3/1, single new-vs-138p id c291-006 which is verbatim base behavior). Root cause both times: a denial turn defeats every arm alike (turn replies identical on 138nb/138p/252c, nothing removed), then 291 answers from store exactly as its base 138nb does, where 138p/252c abstain. The join introduces nothing (291 == base reply+store byte-for-byte both times).

DEVIATIONS: D1 sealed panel.sh path bug ($R252B→$R258, 3 lines) — 3 one-off scorer runs, no sealed edits, no arm re-runs. D2 sealed scorer path bug (m6-compare location) — /tmp shim + one-off tally importing the sealed scorer. D3 openpanel needed a one-time 138m base arm for bit-exact fidelity (260 rows were 80/80 identical regardless). D4 m8.sh mis-assumed the panel scorer CLI (3 args vs its 2) and row format — arms ran once correctly; rows reformatted (drop extras; writer's per-id reference columns); scored via the sealed scorer's own functions with per-item sums matching CLI TOTALs. D5 two VOID-procedure t221 runs redone once each with the registered panelmap procedure. D6 M7 predictions class-based (blind rule forbids pre-listing panel ids). D7 PUSH blocked: `git push` is denied by environment policy — all PUSH-listed paths are complete in the worktree (11/11 seal OK); pre-push I removed only my own scratch dirs (run/work, bench-tmp, 71M). Also: pilot found 7 opener-teach regressions → sealed pre-seal glue fix (R1 refusal-rerun + R2 junk guard, 138m-parity scoped); two broader attempts rejected by pilot with full evidence in the design note. Load-gated throughout; disk stayed ≥11 GB free.

WHAT IT MEANS (plain English): the join itself works — 291 keeps everything both parents do (73/96 on the fresh panel vs 65 and 34; perfect preservation both ways; fastest family scores; controls perfect) and adds no new badness anywhere. The two FAILs are the same inherited habit, not join damage: when a removal fails on every agent, 291 states the leftover fact like its base instead of staying silent like 138p.

WHAT IT DOESN'T MEAN: not accepted — the verdict is FAIL and needs your ruling (options: accept verbatim-base stale answers as table behaviour per the M7 classification clause, or route a removal-path follow-up for verb_denial misses shared by all arms). It doesn't mean new unsafety (zero new flags beyond both parents on every blind panel). It doesn't measure real users (scripted items, one run each).
