Building your 280b follow-up — reading the rules and experiment brief.
I've got the 280 baseline and the 280b spec. Now reading the remaining runner infrastructure.
Load is ~50 (under the 60 gate) and disk is fine. Now checking relation vocabulary and suite tooling.
I have the full picture. Setting up the work plan.
Now writing the dev-cases generator (own wording, fictional names).
Cleaning up an awkward line I left in the generator.
Now writing the one-change fix file.
Now the 280b loop agent.
68 dev dialogs written. Quick pure-Python check of the rule against every dev turn before heavy runs.
The "what you do" (no "do" after "what") variant needs a cue pattern.
Rule is clean on dev. Checking writer schema conventions (keys only, never text).
Schema convention confirmed (keys only). Writing the 280b runner and scorer.
Now the dev pilot on both arms.
I put runall content in the panel path — fixing by creating both files properly.
Now the required pre-seal mock-panel end-to-end test.
Mock end-to-end passes. Testing the schema gate with a broken panel.
Schema gate verified. Starting the frozen-suite pilot (checking load first).
Load 74 — above the 60 gate. Waiting for it to drop.
Load is climbing (81) — other agents are busy. Drafting PASSMARKS text while waiting (move predictions to be filled from pilot).
While waiting on load: adding one more cue pattern (`what … you … do` window) for natural wordings like "what is it you do".
Rule behavior looks right on edge cases. Waiting on load for the suite pilot.
Load dropped below the gate. Running suite pilot step 1 (sessions152+bench vs 280 rows).
0 moves on sessions152+bench, GATE clean. Next: rt136 pilot.
rt136 clean. Next: rt143 + verifier probes pilot.
One probe diff (B17) — diagnosing whether it's rule-caused or flake.
Re-running the affected pilot pieces with final code.
All pilot evidence is clean. Writing predictions file and PASSMARKS.
Sealing now.
Seal 15/15 OK. Appending predictions to the ledger.
Launching the registered M2 run in background (single run, polling for completion).
Panel is sealed. Running the registered panel script once.
VOID confirmed. Writing RESULTS.md.
Verdict: VOID on M1 (panel schema mismatch, neither arm ran), PASS on M2.

Marks table (integer counts):

| mark | bar | result |
|---|---|---|
| M1gen | 25/25 general items byte-equal CAN280 on 280b | VOID — 0/50 rows ran (gate exit 3) |
| M1a | 0 unsupported-claim replies on 280b | VOID — not scored |
| M1xy | 0/0/0 canyou/nearmiss/control moves vs 280 | VOID — not scored |
| M3 panel | 0 write diffs, 0 question writes on 280b | VOID — not scored |
| M2 sessions152 | 0 moves, GATE clean | 0 moves, GATE clean — PASS |
| M2 bench 4x200 | 0 moves | 0 — PASS |
| M2 rt136 (145) | 0 field diffs, labels identical to 280's | 0, identical — PASS |
| M2 rt143 (124) | 0 moved | 0 — PASS |
| Probes vp 98 / vs 12 | 0 changes vs 280 | 0 / 0 — PASS |
| Dev 68 dialogs | general 28/28 canon, rest 0 diffs | 28/28, 0 diffs, 0 q-writes |

Every move: none — no registered move exists anywhere (0 suite/probe moves; panel never ran). Every miss: none scored; the only pre-seal diagnostic was verifier probe B17 ("What do you know about me?"), which over-fired the unordered what+do+you cue in pilot — fixed before the seal by ordering the cue (what...you...do), 0-diff in the registered run.

Deviations:
1. M1 is VOID, not FAIL: the blind panel's turn-text field is named `user`; the sealed scorer requires `user_text` (brief's schema named no text field; builder followed 280's convention, proven on the mock). All three sealed steps exited SCHEMA-MISMATCH code 3 in 1 s; 0 rows ran on either arm; nothing scored by hand; seal 15/15 re-verified OK. Keys/counts only: 50 rows, 45 dialogs, categories general 25 / specific 10 / nearmiss 10 / control 5 (spec split exact) — the field name is the sole blocker.
2. PUSH paths are deliverables in place; no commit/push made (hard rule).

What it means: the rule works on all 68 self-built wordings and changes nothing else (frozen suites + probes byte-match 280), but there is no blind grade yet — the test file and the sealed test-taker disagree on one column name.
What it doesn't mean: it doesn't mean PASS or FAIL on the 25 blind items — a VOID run proves nothing. It doesn't mean new skills — only the self-description wording broadened, nothing else changed.
