Locked on 261b — rebuilding the sealed arm plus the hold-back guard, then running the blind panel once.
I've got the 261 baseline and the diagnosis. Now mapping the sealed pipeline pieces for the 261b rebuild.
The decision note and 261's sealed numbers are in hand. Setting up the work plan.
Now checking the BensPC compute setup — GPU state and llama-server.
GPU is idle. Checking the required binaries and model files on BensPC.
The BensPC shell is cmd — semicolons don't separate commands there. Retrying with cmd syntax.
No server running — I'll start my own when the GPU waves begin. First, the local dev reproduction.
All dev inputs are local. Reproducing 261's sealed theta sweep now.
Sweep matches so far. Verifying the full curve against the sealed file.
Step 1 verified — pipeline matches 261's sealed dev numbers exactly. Now designing the guard from the relation table.
Guard design is clear. Reading the 257 panel checker to adapt the loader for e261b.
Loader pattern confirmed. Writing the 261b guard module now — particles from the decision note, exemptions from table v2.
Guard holds 8 of 1098 on 261's dev — all false holds in base. Inspecting what spans those are (dev data, local only).
Same numbers. Checking the gold-frame parser format before writing the new dev set.
Format confirmed. Writing the new dev-turn generator with fresh fictional names.
Fixing a name-offset mismatch in the typo block — turn and gold must share names.
Dev set written (24 typo + 24 lowercase, self-checks pass). Now setting up the BensPC GPU wave — verifying the checkpoint hash and scp first.
Checkpoint hash matches. Starting llama-server on BensPC now.
Server launched (PID 25900). Waiting for the model to load.
Binary works — the backgrounded process was likely killed on session close. Relaunching detached via Win32_Process.
Detached launch OK (PID 7924). Waiting for model load.
Still dying with empty log — likely the cmd quoting. Retrying without redirection.
Server alive (PID 19652, 13.5GB). Waiting for load completion.
Model is on GPU (13.7GB). Testing the endpoint with a probe.
Server shape matches the sealed parser. Checking 261's exact inference flags before mirroring them.
Mirroring 261's flags. Building the turns file and uploading.
Ear inference done (sha OK). Downloading preds and building checker queries.
Guard held 0 on the new turns. Checking what the ear actually emitted — did it glue any typos?
Now the scorer wrapper with Ruling 1.
Scorer written. Piloting it on a synthetic fixture — first checking the raw/preds formats.
Fixture bug — wrote JSON array instead of JSONL. Fixing.
My ID regex (copied pattern) wrongly rejects 100–109. Fixing with a correct one.
Pilot confirms Ruling 1 and the guard both work. Testing the schema-mismatch path.
All plumbing piloted. Copying the dev evidence into the 261b artifacts dir.
Now writing PASSMARKS. Checking the ledger format first.
Seal verified 15/15. Appending ledger predictions.
Panel is sealed. Verifying its seal from the repo root.
Panel seal OK (2/2, 150 lines). Extracting turns (schema check included).
Schema OK. Uploading turns and running ear inference on BensPC.
Mac load is 105 — above the 60 limit. Waiting before the Mac-side arm B run.
Load under 60 and my seal intact (15/15). Running arm B (once).
Arm B done. Scoring (once, sealed driver).
Registered run complete — verdict FAIL. Extracting the full breakdown (counts and categories only).
Server still up — retrying with taskkill on the exact PID.
Compute is clean. Writing RESULTS.md.
Verdict: registered FAIL. Arm A (261's A + span guard, theta 0.25, prompt B, scorer with Ruling 1) on the blind 150-item panel: M1 pass, M2 FAIL, M3 FAIL, M3b FAIL, M4 pass, M5 pass, M6 pass.

Marks table, arm A (integer counts):

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | no_save saves <= 1 | 1 | yes |
| M2 | wrong saves <= 1 | 9 | NO |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 98/135 = 72.6% (B 0/135 = 0.0%) | NO |
| M3b | UNSURE <= 12% of gold TEACH | 23/135 = 17.0% (15 checker + 8 guard) | NO |
| M4 | exact ASK recall >= 90% | 38/40 = 95.0% | yes |
| M5 | median ear+checker+guard <= 800 ms | 367.5 (p90 701.4, max 1065.5) | yes |
| M6 | every A frame byte-identical in A261 | 0 mismatches | yes |

Every move and miss. Pre-seal: (1) reproduced 261's dev sweep byte-equal from sealed files (theta 0.25, 1085/1180 = 91.9%, 13 wrong). (2a) Guard on 261's dev: 1098 checker-saved frames, 8 held (0.7%), all 8 false holds of one category (title-style lowercase-"of" subjects). (2b) 48 own dev turns (24 typo + 24 lowercase): checker saved 53, guard held 0; ear glued typos into spans twice (once capitalised, once garbage the checker held); all 24 lowercase saved, 0 held. Panel run (each arm once): A 1/9/98/38, A261 1/16/99/38 (M3b 11.1%), A_brake 4/34/99, A_raw 6/57/99, A_gate 2/18/76, A_nocanon 1/19/95, B 0/2/0. Guard held 8 panel frames (7 good typo-glued holds, 1 false hold costing 1 recall); 9 wrongs (2 job-title, 1 food, 2 lowercase relation-word values, 1 home misread, 1 appositive location, 1 plural-relative vehicle, 1 no-save language save). Ruling 1 converted zero frames (panel already lists species words as aliases). R10 recall 4/20 caps M3; R13 5/12 with 6 good guard holds. Predictions: P261b.1/.5/.6/.7/.9 right; P261b.2/.3/.4 wrong; P261b.8 resolves FAIL.

Deviations: D1 prompt B inherited from 261. D2 panel never opened pre-seal; post-seal 2/2 OK, schema check passed, every arm once; 257/261 panels never run. D3 first llama launch died silently, relaunched detached (PID 19652), stopped by exact PID afterward, GPU idle confirmed, other processes untouched. D4 M5 excludes beam time. D5 no-Ruling-1 rescore is local recomputation only. Sealed files unchanged (my seal 15/15 OK; only ledger appended; no commits/pushes per standing rules — deliverables sit at artifacts/claude-earcheck261b-20260923, scripts/claude_earcheck261b_*.py, artifacts/fable-predictions-ledger.md).

What it means: the guard does its one job (7 of 8 holds correct) but the run still fails three marks — the ear misses too many facts (plural relatives 4/20) and the checker approves confident misreads, and the guard's extra holds flipped M3b from pass to fail. What it doesn't mean: the guard is useless (M1/M4/M5/M6 pass); Ruling 1 is wrong (just redundant here); the ear regressed (this panel is harder); a higher theta would work (both theta curves flat on recall). Full detail: artifacts/claude-earcheck261b-20260923/RESULTS.md.
