Building your QA checker and follow-up — reading specs and baselines.
Your baselines aren't on main — pulling the local sealed records instead.
A 264 build already exists here — checking what's sealed before duplicating work.
Core wiring mapped — now checking how the last GPU run reached BensPC.
BensPC pings but SSH needs the right login — hunting down the connection docs.
Found the BensPC alias — verifying the SSH route.
BensPC is up and the GPU looks idle. Now tracing how prior waves moved files to BensPC.
BensPC's copy isn't a git repo — checking what prior waves synced over.
Now reading the 261 checker pipeline pieces I'll wrap for 270b.
Pipeline understood. Checking dev-run mechanics and the 264 seal state.
264 verified 23/23 seal OK — that half of the task is done, nothing to rebuild. Now preflighting BensPC for the 270b build.
Preflight is green (binary, model, ckpt, torch+CUDA, GPU idle, port 8082 free). Now writing the 270b normaliser — the one change.
Core rewrite cases pass (the 2 "MISS" lines were wrong expectations in my throwaway check — `my`/`who` correctly stay lowercase per 270's rule). Now checking the sealed scorer's match semantics before writing dev gold.
Scorer semantics clear. Writing the devset generator (148 own-wording turns).
Fixing a few devset issues (placeholder name, ASK subjects, occupation casing, digit name).
Devset generated (148 turns). Checking `arm_set`'s turn usage before writing the wave scripts.
Writing the wave scripts (turns builder, qbuild wrapper, dev scorer).
Clean holds at 0/24. Checking which casual/trap items didn't fire (expecting only the 4 D1-suppressed traps).
Generator bug: several "lowercase" turns leak capitalised values. Fixing.
All 16 questions normalise correctly. Now setting up the BensPC dev wave — first checking prior wave's infer args.
Checksum matches, GPU idle. Launching ear inference for the 296 dev turns.
Ear wave clean (296/296, sha OK). Fetching preds and building checker queries per arm.
Queries built (A:104, A261b:103). Starting my own llama-server on port 8082 via encoded PowerShell.
That escaping is fragile — redoing it with exact file content instead.
Server started (PID 20880). Shipping checks over and waiting for the model to load.
Server healthy, model resident. Smoke-testing the checker client before the full wave.
Smoke test passes (YES p=0.93, NO p=0.004, 0 fallbacks). Running both checker waves.
GPU idle, foreign processes untouched. Scoring the dev wave.
Dev is stable. Getting the exact M3 trap ids for the record.
Trap anatomy is clear. Pulling final dev numbers for PASSMARKS.
The fix moves exactly the intended class. Writing PASSMARKS.
Seal is 18/18 OK. Appending ledger predictions.
Panel seal 2/2 OK (load is high locally, so keeping this Mac's work light — heavy lifting stays on BensPC). Opening the blind panel for the first time.
Panel turns ready (200, clean 0/30 passthrough). Shipping to BensPC for the registered ear wave.
Stop command was malformed — regenerating it properly.
Both arms ran once, server stopped, GPU idle. Scoring.
V2 verdict: FAIL (M1 margin, M3, M5). Gathering the remaining forensics for RESULTS.
All evidence in hand. Getting pYES values for the wrong-save frames, then writing RESULTS.
## Final report (build/verification agent, 2026-09-23)

### EXP 264 — verdict: registered FAIL (already complete in this worktree; verified, not rebuilt)
Seal rechecked 23/23 OK; RESULTS.md + ledger P264.1–P264.9 already filed. Arm A (QA checker): M1 2 (bar ≤1) FAIL, M2 5 FAIL, M3 81/125=64.8% FAIL, M3b 30.4% FAIL, M4 37/40=92.5% pass, M5 median 880.1ms FAIL, M6 0 mismatches pass. Nothing was edited, re-run, or re-sealed.

### EXP 270b — verdict: registered FAIL (M1 margin, M3, M5 fail; M2, M4, M6 pass)

Marks table, arm A vs A261b (261b's A exactly), each arm run ONCE (200-turn ear pass, 75+70 checker queries, 0 fallbacks; panel seal 2/2 OK; sealed 18/18 OK after):

| Mark | Bar | A | A261b | Pass? |
|---|---|---|---|---|
| M1 | casual exact ≥30/40 and ≥A261b+15 | 37/40 | 31/40 (margin +6) | NO |
| M2 | casual_q ASK ≥12/15 | 14/15 | 15/15 | yes |
| M3 | lower_trap wrong saves ≤1 | 2 | 3 | NO |
| M4 | clean 30/30 identical | 30/30 | — | yes |
| M5 | 0 new wrong saves | 3 | — | NO |
| M6 | median normaliser ms ≤20 | 0.0096 (max 0.11) | — | yes |

Every move/miss: M1 A misses 3 (u270-020 flipped-role pet/fish frame both arms; u270-033 A saves nothing; u270-040 capitalised-phrase subject save) — all 3 also missed by A261b, whose 6 extra misses are garbage/nothing raw reads the normaliser fixes (002/011/025/036/038 + disclosed scorer-artifact 003: true A 36, true margin +5). M2 miss: u270-054 (hometown/grow-up shape, capitalised verb glued into ASK subject). M3 wrongs: u270-061 hunter-occupation decoy (pYES 0.511), u270-068 may-occupation decoy (pYES 0.266); A261b additionally saves 064/070 color decoys. M5 new: 040 (capitalisation-span garbage), 061 (shared decoy error, value spans differ), 068 (capitalised decoy save where raw saved nothing). Clean 30/30 byte-identical frames; no TEST-ONLY panel opened; typepanel270 never opened.

Deviations: D1–D6 per PASSMARKS (D1 check-tail suppression carried; D3 panel runner/scorer written post-seal from observed schema; D4 panel unopened pre-seal except listing+SEAL hashes). D7 post-seal scorer fix with diff: v1's symmetric strip-one-s wrongly missed 5 correct s-name frames (M1 32→37, M2 12→14, M5 8→3 on re-score of recorded rows; arms never re-ran; v1 file kept). D8: u270-003 arm-A HIT is a disclosed scorer artifact (sealed S_NAMES270b lacks "iris"). D9: llama-server on port 8082 (PIDs 20880 dev, 19776 panel), each stopped by exact PID, GPU idle after; foreign stub 17056 and pythonw untouched; one malformed stop command rejected with no effect. D10: Mac load 45–172, all heavy compute remote. PUSH set in place, unpushed per OPUS-RULES (results + code + ledger lines P270b.1–8 + OUTCOME filed).

What it means: the normaliser's core job works — messy typing the ear garbles now saves correctly (37 vs 31), questions pass (14/15), clean turns are byte-identical (30/30), cost is ~0.01 ms. But the panel counts glued raw spans as hits too, so the lead is +6 not +15; two decoy words still save fake jobs; and capitalisation backfires on 3 items.

What it doesn't mean: the keep-s fix isn't broken (every strip/double-s item exact on A); capitalisation isn't net harmful (+6 recall vs 3 damaged items); traps aren't hopeless (13/15 decoys save nothing); v1 wasn't the verdict (v2 corrects 5 mis-scored frames on the same recorded run).
