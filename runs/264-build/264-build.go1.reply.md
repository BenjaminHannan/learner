Building your QA checker — wiring the prompts and scoring harness.
I've got the design for the three-question check. Now mapping the previous runs to build the new arms.
I've reviewed the guard and scoring setup. Now digging into the checker details and test setup.
Core checker logic is clear. Now looking at the test infrastructure and data flows.
I need the remote compute details and the relation mappings for the new checker.
Remote GPU is free and I've got the table structure. Now checking the dev data I'll validate against.
No server running — I'll start the model server for the dev runs.
The first launch didn't stick. Retrying with the corrected command.
Server is up. Now reproducing the previous results before building the new checker.
Dev baseline reproduced exactly. Now designing the three-question checker.
Checker core is written. Now the scoring wrapper and test scaffolding.
Scorer is ready. Now figuring out how to run the ear model for the new dev cases.
Found the model paths. Now setting up the dev runs.
Compute environment checks out. Now writing the new dev cases for relation traps.
Dev set written — 32 trap and stale-value turns. Now the analysis harness.
Everything staged on the remote box. Running the ear model over the new dev turns.
Missing a dependency on the remote side — uploading the rest and retrying.
Ear predictions are in. Piloting the QA questions before the full dev wave.
Explicit triggers fix pretend/plan cases. Now examining the remaining check-question leaks.
The decide-first wording holds all check-questions while keeping plain facts intact. Locking that in.
Prompts finalized and uploaded. Running the full dev wave now — this takes a while.
The relation question is holding back too many true facts. Inspecting what it actually returns.
Mapping and wording updated. Re-running just the relation questions.
Owner wording fixed both directions. Applying it and re-running those questions.
Check-questions are now the main leak. Looking at which phrasings get through.
Explicit so-check trigger holds 8/8 with plain facts intact. Adopting it across both questions.
Check-questions fully held now. Chasing the remaining relation false-holds.
Mapping is stable with no new leaks. Now dissecting results on my own trap turns.
Final wording tweak in place. Re-running the affected questions one last time before sealing.
Tuning is done — the trap leaks are structural, not wording. Computing final dev recall for the predictions.
Pilot input was unrealistic — checking how the ear actually phrases speaker subjects.
Scorer verified. Testing schema rejection, then writing up predictions.
All artifacts consistent. Finalizing the dev reports and writing predictions.
Predictions written. Sealing the build.
Panel is sealed. Verifying and starting the registered run.
Ear done — 150 turns. Building both checker query sets and running them.
Mac is busy with other agents' work. Waiting for load to drop before the CPU arm.
All arms complete. Scoring the registered run.
Results are in. Stopping the model server and confirming the GPU is idle.
Final verification before the report.
Verdict: registered FAIL. Arm A (QA checker) on the blind 150-turn panel: M1 FAIL, M2 FAIL, M3 FAIL, M3b FAIL, M4 pass, M5 FAIL, M6 pass. Overall FAIL.

Marks table, arm A (integer counts):

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | no_save saves <= 1 | 2 | NO |
| M2 | wrong saves <= 1 | 5 | NO |
| M3 | TEACH recall >= 85% and >= B+30 | 81/125 = 64.8% (B 2/125 = 1.6%) | NO |
| M3b | held back <= 12% of gold TEACH | 38/125 = 30.4% | NO |
| M4 | ASK recall >= 90% | 37/40 = 92.5% | yes |
| M5 | median per turn <= 800 ms | 880.1 (p90 1826.8, max 2664.2) | NO |
| M6 | every A frame byte-identical in A_brake | 0 mismatches | yes |

Every move, every miss: A_brake (ear alone) reads 95/125 with 30 wrongs. A261b (YES/NO checker) gets 94/125 with 6 wrongs. Arm A (QA) gets 81/125 with 5 wrongs — so the QA swap trades 13 true facts for 1 fewer wrong save versus YES/NO. Per-fact wrong rates: A 5/86 = 0.0581, A261b 6/100 = 0.0600, A_brake 30/125 = 0.2400, B 9/11 = 0.8182. Per-turn: A 5/110 = 0.0455, A261b same, A_brake 21/110, B 9/110. The 5 wrong saves: 2 no-save check turns, 1 plain fine-grained confusion, 1 relation-trap pass, 1 stale-value pass (categories only, nothing quoted). Holds: 37 QA + 1 guard; misses concentrate in plural relatives (3/14), typo names (4/16), relation traps (4/8), stale values (4/6). Predictions: P264.2/.5/.6/.7/.8/.9 ranges right; P264.1 range right but bar missed (2 vs 1); P264.3 off by 0.2 (64.8 vs 65–78); P264.4 off by 0.4 (30.4 vs 20–30).

Deviations: D1 prompt wording v5 (decide-first, single-word relation, de-anchored owner — all dev-piloted, logged); D2 mapping D-rel-map (ancestors, possessive-strip, head-noun, pet-family, date/country truncations — trap-safe, dev wrongs unchanged); D3 blind protocol kept (panel never opened pre-seal; both seals rechecked OK after runs: mine 23/23, panel 2/2); D4 llama-server relaunch via Win32_Process, stopped by exact PID 1424 (force needed, session 0), GPU idle 282 MiB, pythonw 13036 untouched; D5 sequential QA (1 server slot); D6 writer comma-joined the notes tags, so the sealed space-split loader missed R11/R13/R14/R17 rows — run stays VALID (schema passed; marks aggregate by family), per-tag table re-bucketed post-seal by a new script that never reads turn/gold text, all spec quotas verified met; D7/D8/D9 every arm ran exactly once, no other panel run, nothing quoted.

What it means (plain English): three questions means three chances to say no — the checker holds back 30 of every 100 true facts while barely reducing wrong saves, costs 13 hits to save 1 wrong versus YES/NO, and three model calls push the middle turn to 880 ms against an 800 ms bar. It does catch pretend, plan and check-question turns and never invents frames.

What it doesn't mean: the ear didn't get worse (ear alone 95/125; YES/NO arm 94/125 on the same harder panel), questions are untouched (37/40), and no cutoff tweak can fix it — there is no threshold, the holds come from three agreeing questions, not one number.
