Resuming the ear-check build — verifying prior work and picking up where it left off.
Server is healthy and panels are sealed — now inspecting the prior builder's work.
Manifests line up (1005 + 202 = 1207 checks). Now verifying which prompt variant produced the sealed theta.
Dev ear predictions check out (CUDA, correct checkpoint). Now probing the BensPC remote setup.
Staged files are byte-identical to local — provenance is clean. Checking ledger format and ear checkpoint hash next.
Checkpoint hash matches. Setting up the work plan and running a final pre-seal plumbing pilot on synthetic data.
Plumbing pilot passes. Testing the schema-mismatch exit path.
Exit 3 confirmed. All pilots pass — writing PASSMARKS now.
Seal verified 18/18. Appending ledger predictions.
150 turns extracted. Staging the GPU run on BensPC.
Ear inference complete — 150 turns, correct checkpoint, no slowdown. Pulling predictions back.
Arm B is light (110 items, ms each). Running it now.
All arms in — scoring the registered run once.
Now the report-only GPU pass over the 257 panel.
Seal intact (18/18 OK). Writing RESULTS.
GPU memory released (13682 → 271 MiB). Final verification pass.
VERDICT: registered FAIL on M2 and M3. Arm A (v4.1 ear + canonicaliser + brake + entailment checker at sealed theta 0.25) on the blind 150-item panel, every arm run once: M1 pass, M2 FAIL with 9 wrong saves (bar ≤ 1), M3 FAIL with 95/122 = 77.9% (bar ≥ 85%), M3b/M4/M5/M6 all pass.

MARKS TABLE (integer counts, arm A unless noted):

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | no_save saves ≤ 1 | 1 | yes |
| M2 | wrong saves ≤ 1 | 9 | NO |
| M3 | TEACH recall ≥ 85% and ≥ B+30 | 95/122 = 77.9% (B 13/122 = 10.7%, diff +67.2) | NO |
| M3b | UNSURE ≤ 12% of gold TEACH | 6/122 = 4.9% | yes |
| M4 | ASK recall ≥ 90% | 39/40 = 97.5% | yes |
| M5 | median ear+checker ms ≤ 800 | median 344.7, p90 700.9, max 1026.0 | yes |
| M6 | every A frame byte-identical in A_brake | 0 mismatches | yes |

Every arm (M1 / M2 / M3 / M4): A_raw 5/25/95/122/39/40; A_brake 5/19/95/122/39/40; A_gate 1/8/79/122 (64.8%)/39/40; A 1/9/95/122/39/40; A_nocanon 1/12/92/122/39/40; B 0/1/13/122. Zero stray TEACH saves on question families in all ear arms.

EVERY MOVE (checker vs brake, arm A): M1 5→1 saves, M2 19→9 wrongs. The 10 correct hold-backs: 4 pronoun-after-relative claims (pYES 0.02–0.04), 3 plan/goal claims (pYES 0.003–0.005), 3 lowercase check-question claims (pYES 0.01–0.19). Recall kept 95/122 (gate kept only 79). Canon fix vs A_nocanon: +3 recall, −3 wrongs.

EVERY MISS: 27 recall misses — 12 from plural-relative turns (R10 4/16: ear emits fewer than half the one-frame-per-person facts, unfixable by any checker), 3 R7 plural-owner, 12 scattered. 9 wrongs passed by the checker, 8 with pYES ≥ 0.68 (6 ≥ 0.94): 3 speaker-pet misattributions (R7×2, R11×1), 2 typo-corrupted facts, 2 stale correction values, 1 plain pet claim, 1 no-save residence at pYES 0.37. Panel theta curve is flat: recall 77.9% from theta 0 to 0.8 while wrongs fall only 19→7 — no cutoff passes both bars. Report-only 257-panel run (once, never tuned): A 3/6/100/112 (89.3%)/M3b 1.8%/39/40 vs 257's sealed A 1/4/78/112 (69.6%)/21.4%/39/40 — checker recovers recall (+20) but adds wrongs (+4 vs recomputed gate's 2); canon alone explains the gate/brake deltas (+2 recall, −2 wrongs).

DEVIATIONS: D1 sealed prompt B rewords the brief's literal question + 2 NO clauses (dev A/B forced it: literal prompt hits ≤1% wrong only at theta 0.9 with ~51% recall; B gives 91.9% at 0.95% wrong). D2 pre-seal panel listing/hashes/line-count only, never item text; panel seal then 2/2 OK. D3 post-seal report-only driver (new file, sealed files untouched, seal rechecked 18/18 OK after all runs). D4 M5 = ear-greedy + checker ms (beam time extra; full-turn GPU medians 139–158 ms). No VRAM spill; ear ckpt hash verified; predictions P261.1/.5/.6/.7/.8 right, .4 pass at range edge (4.9%), .2/.3 ranges wrong.

WHAT IT MEANS: the checker catches the traps it was built for (all 10 hold-backs correct) and saves nearly all true facts the old gate threw away — but it approved 9 confident wrong saves, and a new ear-side miss (plural splitting, 4/16) caps recall below the bar before checking starts. WHAT IT DOESN'T MEAN: checkers are useless (M4/M5/M6 pass, R7–R12 hold-backs all correct); the ear got worse (95/122 here vs 98/112 on the easier old panel — the fresh panel is harder); a higher theta would fix it (curve is flat). Cleanup done: llama-server PID 13444 stopped, port dead, GPU memory 13682→271 MiB.
