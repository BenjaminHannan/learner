Building the F1 reply layer — setting up the sealed pilot and verification runs.
The original spec file is missing — I'll work from the stated requirements and map out the current implementation.
Setup mapped. Now building the F1 agent: 292t plus 241b's exact rewriter mixin as the outermost layer.
Pre-seal fix to my own new file: the pre-upgrade check must not require the mouth yet.
F1 runs. Checking why stats attr is missing:
Mouth layer verified live (route A rewrites firing, fixed lines passthrough). Now the 60+ dev turns and pilot.
Pilot clean on stores (0 diffs) with 1 legacy fallback to inspect:
Suites are fast (~1 min). Inspecting row schemas to build the F1 scorer:
Now writing the F1 suite runner and scorer (new files):
Config is behaviorally identical. Now the verdict-flipping moves:
sessions152 is fully reply-only (57/57). The GATE hit is bench-only. Inspecting:
Now the NEW-1 bench driver (mirrors 241b's sealed `--scorer241b` swap):
NEW-1 resolves the flips. Verifying the 10 ids specifically:
Now the joinpanel regression scorer (mechanical only, ids/counts, never item text):
Now the M5 wall script:
Wiring NEW-1 + mouth logging into the registered runall (pre-seal edit of my own file):
Pre-seal verification: compile all new scripts and dry-test the scorers on synthetic fixtures:
Scorers verified. Writing PASSMARKS with numbered predictions:
Sealing every new file:
Pilot record refreshed. Sealing:
Seal 41/41 OK (load spiking to 149 — other work on the machine; disk fine). Appending predictions to the ledger:
Seal + ledger done. Starting registered runs (once each). Load is extreme right now — the sealed runner will wait for quiet:
Regression PASS with a surprise (0 reply diffs). Checking route distribution mechanically (counts only, no item text):
24 route-A mouth entries but 0 reply diffs is contradictory — verifying directly:
Legacy coverage noted (5 suite + 20 joinpanel, all byte-identical fallbacks). Now convbench-f0, both arms, once:
All 13 convbench changes route-A attributed, 0 store diffs. Now M5 — checking if the machine is quiet:
Load 67 — launching the M5 wall in background to wait for quiet (script enforces load1<40, 6h budget):
While the wall waits for quiet, verifying seal integrity post-registered-runs:
Seal intact, registered marks green. Drafting RESULTS.md (M5 pending wall):
Wall still waiting (load 91). Checking additive-only compliance meanwhile:
Only the ledger modified (append-only ✓). Waiting on the wall — polling:
Machine went quiet — wall run 0 (F1) done in 44.0s. Continuing to poll:
M5 PASS (ratio 0.994). Finalizing RESULTS.md, ledger outcome, and seal check:
All green. Pushing the specified paths:
`artifacts/` is gitignored but precedent force-adds (292t's artifacts are tracked). Force-adding per the PUSH instruction:
Push is blocked by environment permissions. Committing locally so the staged work is preserved:
VERDICT: registered PASS on all mechanical marks (M2, M3, M5). M1/M4 not run here — director-queued blind graders. No "Wrong if" clause tripped: 0 unfaithful lines, 0 store changes, judge not run.

Marks table (integer counts):

| mark | bar | got |
|---|---|---|
| M2 unfaithful lines | 0 | 0 (all route-A pass brake; legacy fallbacks byte-identical) |
| M2 store/event changes (suites, probes, joinpanel, convbench) | 0 | 0 |
| M3 sessions152 moves | reply-only | 57/57 reply-only |
| M3 bench moves (NEW-1) | reply-only, GATE clean | 648/648 reply-only, GATE clean |
| M3 rt136 | reply-only | 52 reply-only, 0 other-field diffs, gate clean |
| M3 rt143 (124 rows) | 0 triples/expected diffs | 0; reply-text diffs only |
| M3 verifier vp/vs | reply-only | 63 + 11 reply-only, 0 stored/ev diffs |
| joinpanel292t regression (90 turns) | 0 store diffs | 0 store, 0 reply diffs (byte-identical), probes 0/0 |
| convbench-f0 (286 turns) | changed lines all route A, 0 store | 13 changed, 13/13 route A, 0 store/event diffs |
| M5 wall (3+3 alternated, load1<40 each) | median ratio ≤1.05 | 50.12 vs 50.42 s, ratio 0.994, PASS |
| M1 grammar ≥99% / M4 ≥70% wins | director-graded | not run here |
| S1 NEW-1 anchor | == frozen on base | 721/721 agree |

Every move: suite/probe/conv moves are reply-text-only, each a 241b route-A rewrite (mouth logs: suites 7590 A/247 pass/5 legacy; conv 65 A/223 pass/0 legacy; joinpanel 24 A/50 pass/20 legacy; dev 37 A/38 pass/1 legacy). Every miss: (1) PF1.3 count missed — 13 convbench changes vs 50–130 predicted (fewer visible changes; most 292t lines are clarify/fixed passthrough or already-A-form, verified by A-identical renders on dev lines); (2) frozen-harness bench pilot showed 10 new WRONG — all one mechanism: 241b's sealed articles ("the United Kingdom", "a basketball coach", etc.) break the frozen byte-verbatim confirm needle so the driver skips "yes" (confirms 2→1 once, 1→0 nine times); NEW-1 matches all 10, 10/10 resolved with base-identical confirms; both numbers reported. Deviations D1–D8 in PASSMARKS.md, notably: 292t's instance-installed stack shadows class mixins (proven: 241b's mixin alone never runs), so F1 installs outermost-as-instance running 241b's exact render_line; bench uses 241b's sealed NEW-1 (mirrors --scorer241b); setup deviations — OPUS-RULES.txt absent at its path, one early `git log`, panel/bench dir-name listings only, config diff descriptive-only. Seal 41/41 OK before and after runs; only the ledger modified (appended); no existing file edited.

What it means in plain English: the better sentence-writer bolts onto the new model cleanly — it only rewords, never changes facts or decisions. What it doesn't mean: F1 is not conversational yet — only 13 of 286 everyday replies visibly change, because most are "I don't understand" lines no rewording can fix; that's the ear line's job.

Push status: commit 83f77071a is staged+committed locally on claude/card-experiment-handoff-7c5b27, but `git push` is denied by environment permissions — the director (or someone with push rights) must push: artifacts/claude-f1-20260923, scripts/claude_loopf1_agent.py, scripts/claude_f1_*, artifacts/fable-predictions-ledger.md.
