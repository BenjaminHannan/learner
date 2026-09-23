Building exp 265 — reading the one-change rule and reusing 261b.
Found 261b sealed + failed; now mapping the 265 delta.
Architecture clear. Now studying how 264 wired BensPC + arms.
Looking up the exact BensPC run commands from 257's records.
Mac load 66 (above 60) — GPU work goes to BensPC; keeping Mac side light. SSH works.
Transport works. Checking code + model assets on BensPC.
No ssh in sealed code — orchestration is manual via bash. Checking model deps for BensPC staging.
Staging is clear. Now reading the checker prompt + qbuild wiring.
Full picture assembled. Writing the 265 code now.
Now the scorer — the core of the 265 marks.
`M261.arm_set` needs `nc:` keys too — adding them to qbuild (mirroring 261).
Now the dev set generator (44 own-wording turns).
Core logic verified. Running a CPU plumbing pilot with synthetic preds.
Pilot file mistake (JSON array vs JSONL), not a code bug. Fixing.
Plumbing works. Verifying ask detection on the pilot.
Code paths verified. Starting dev GPU phase — probing BensPC python first.
Preds exist — pulling them back.
Detached launch works. Starting llama-server.
llama-server PID 27936. Waiting for health.
Server healthy. Staging checker inputs and running 102 queries.
Dev scored. Digging into the 2 missed asks and 3 mixed misses.
WMI-terminate verified for end-of-run. Writing PASSMARKS.
Seal 16/16 OK. Appending ledger predictions.
Sealed + ledger done. Polling for the blind panel seal.
Panel sealed already. Verifying and running the registered wave once.
Seal intact. Stopping the server by exact PID.
Server stopped, GPU idle. Writing RESULTS.
Verdict: registered FAIL. Arm A on the blind ourpanel265 (80 items, every arm run once): M1 FAIL, M2 FAIL, M3 pass, M4 pass, M5 pass.

Marks table (arm A, integer counts):

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | 0 group-owned facts saved, >= 27/30 turns ask whose | 0 saves; 14/30 ask | NO |
| M2 | >= 12/15 mixed exactly right | 5/15 | NO |
| M3 | first_person: 0 lost vs A261b | 0 lost (15 hits vs 15, gold 20) | yes |
| M4 | named: 15/15 byte-identical to A261b | 15/15 | yes |
| M5 | 0 new wrong saves vs A261b | 0 new (A wrong 13, A261b wrong 35) | yes |

Wrong-save rates (report-only): A 13 wrong / 54 saved per-fact, 12/80 turns per-turn. A261b 35/76, 30/80. B (138i+228) 5/6, 5/80 turns (1 hit; abstains almost everywhere). A wrongs by family: group_owner 2, mixed 1, first_person 8, named 2.

Every move and miss:
- 23 group-subject frames diverted to the fixed ask-whose reply on 20 turns (14 group + 6 mixed), 0 writes from any of them. The rule fired every time it saw a group subject (23/23).
- 16 group turns never asked: on 10 the ear surfaced no bare group-word subject (2 no-frame, 8 name/other subjects); on 6 the ear surfaced one but the brake dropped it.
- 9 mixed turns never asked (7 brake-dropped group frames, 2 no group surfaced). Mixed teach hits still 15/15 with 1 wrong frame; only 5/15 have both exact saves and the ask.
- 5 first-person gold frames missed identically by both arms (ear-level). 2 stray saves on group turns (non-group subjects). All 13 A wrongs are shared with A261b.
- Predictions: P265.1 (ask 24-28) wrong at 14; P265.2 (11-14 exact) wrong at 5; P265.3/4/5 right; P265.6 (~25% ALL) resolves to FAIL; P265.7 latency band right (median 373.4 ms, p90 679.5, max 1320.6; ear median 211.3; checker 172 queries, 0 fallbacks, median 283.1).

Deviations: D1 counts-guard forced ALL=false on dev only (read marks directly). D2 panel never opened pre-seal; seal 2/2 OK, schema check passed, each arm once; 257/261/261b never run. D3 server started detached (launcher PID 27936, server PID 30076, 261b flags), left running between waves, stopped at end by WMI terminate on both exact PIDs (taskkill is session-0 denied), GPU back to idle 282 MiB; pythonw 13036 untouched. D4 diverted frames still spend a checker query (keeps A261b exact). D5 M5 = per-turn multiset difference. Seal rechecked 16/16 OK after all runs. No re-runs; misses are systematic, not flake.

What it means (plain high-school English): the new rule works perfectly — every "our/we" fact it sees gets saved as nothing and answered with "whose is this?", 23 out of 23 times. The failure is one step earlier: on about half the group-worded turns, the reader doesn't hand the rule a clean "our" subject (it reads the ownership some other way, or its safety filter drops the frame), so the rule never gets its chance. Normal "I/my" and named-person facts are completely untouched.

What it doesn't mean: it doesn't mean the rule is wrong or that asking breaks other things (M3/M4/M5 all pass, zero new wrong saves). It doesn't mean a stricter checker cutoff would fix it (the misses don't depend on the cutoff at all). It doesn't mean the ear got worse (on plainly worded group turns it asks 12/14; the blind panel just phrases ownership in trickier ways than my dev set covered — my dev gap, reported, not tuned).
