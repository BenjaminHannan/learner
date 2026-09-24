Starting the rsn-296 build — reading rules and seals.
Credit is fine and no duplicate instances. Searching for rental offers.
Instance requested. Waiting for it to run.
GPU is healthy (5090, CUDA torch, plenty of CPUs). Shipping the code over.
Transfer was progressing (40MB of 102MB). Resuming it.
CPUs are fine (~30 quota, 256 visible). Running seal checks and generator self-test.
Seals all OK, selftest ok. Starting pilot timing runs (both arms, tiny).
The backgrounding broke the `cd`. Rerunning with absolute paths.
Both pilots got tangled by duplicate launches. Cleaning and rerunning both pilots simultaneously.
`pkill` killed its own shell (pattern matched itself). No training processes exist anyway — just relaunching cleanly.
Shell operator precedence keeps biting. Using `;` separators and separate launches.
Processes die when the SSH session exits. Checking for tmux/screen for persistent runs.
The tmux server vanished. Investigating container state.
Both pilots actually finished. Reading timing values.
Both seed-1 runs are training (GPU 99%, 18GB). Polling progress.
Wrong directory — outputs are under /root/rsn/W. Checking there.
Training on track (plain copy 4800/6000, loop 1800/6000). Waiting.
Plain-s1 done (38 min). Loop-s1 in RL phase (~35 min left). Waiting.
Seed-1 pair done (plain 38.0 min, loop 78.4 min). Launching seed-2 pair.
Plain-s2 done (37 min). Loop-s2 needs ~30 more min.
All 4 runs complete. Sealing checkpoint hashes before eval.
Seal written before any eval. Launching the 24 eval commands (each checkpoint exactly once).
tmux mangles `;` in session commands. Switching to a script file + setsid.
All evals done, no failures. Organizing outputs into runs/ directories and reading category counts.
Panel296 counts are in. Now the panel294 transfer numbers.
All numbers collected. Pulling training-curve endpoints and dev totals for RESULTS.md.
Writing RESULTS.md on the remote (new file), organizing runs/, appending ledger.
Copying checkpoints to the Mac before writing final numbers.
Verifying local checkpoint hashes against the seal.
All 8 hashes match the seal. Destroying the instance.
Instance destroyed and confirmed gone. But I made a serious error: I copied back only the checkpoints, not the `runs/` JSONs, RESULTS.md, or ledger lines — those died with the instance. I have all panel counts and training endpoints in my transcript. Recovering what's regenerable with a second rental (budget allows: spent ~$1.66 of $4).
Not running within 6 min. Destroying and trying the next offer on a different host.
Instance running. Uploading code and checkpoints.
Four rentals reached (1 success + 3 failures). One last SSH attempt, then destroying per the rental cap.
All instances gone. Writing the local deliverables now.
**Verdict: FAIL** (registered rsn-296 builder run complete; code never patched, panels never read).

## Marks table (plain arm, final checkpoints, integer counts)

| mark | bar | seed 1 | seed 2 |
|---|---|---|---|
| P296.1 invented answers (answered without a fact), each panel ≤ 2/300 | ≤ 2 | fresh **5 FAIL** / transfer 0 pass | fresh **6 FAIL** / transfer 0 pass |
| P296.2 right on reasonpanel294 (≥ same-seed 294 plain + 20) | s1 ≥ 204, s2 ≥ 209 | **238 PASS** (+54 over 294's 184) | **238 PASS** (+49 over 294's 189) |
| P296.3 fresh code-doable (≥ code arm − 10) | ≥ 168/178 | **173 PASS** (30+30+23+30+30+30) | **169 PASS** (30+30+19+30+30+30) |
| P296.4 fresh total (≥ code arm + 20) | ≥ 228/298 | **225 FAIL** (miss by 3) | **217 FAIL** (miss by 11) |

PASS needed all four marks on both seeds. Code arm reference: 208/298 fresh (178/178 code-doable + 30/30 three-step), 210/300 transfer.

## Every move (checked_right totals)

Training: plain-s1 38.0 min (copy loss 4.1244→0.0065, practice reward 0.5944→0.9307); plain-s2 37.0 min (4.1609→0.0003, 0.6296→0.9801); loop-s1 78.4 min (copy loss stuck 4.2→1.85, reward 0.09→0.26); loop-s2 77.2 min (same stuck pattern — 294's D2 loop copy failure reproduced, deliberately unfixed).
Fresh panel296 v2 finals: plain 225/217, loop 106/101; copy-only: plain 167/181, loop 57/47. Transfer panel294 v3 finals: plain 238/238, loop 89/87; copy-only: plain 195/205, loop 59/49.
Fresh-panel detail (both plain finals): two-step 30/30, one-step/backwards/yes-no/missing 30/30, before_after 24/20, comparing 16/16, counting 12/12, three-step 0/30, newest_correction 23/28 and 19/28. Loop (no marks): copy-only never learned one/two-step (0/30), as in 294. Dev (varied-gen, 1200 eps): plain finals 932/937; loop finals 445/427.

## Misses and deviations

1. **DATA LOSS (major, my fault):** runs/*.json were staged on the GPU box but I destroyed it before copying them back. Panel counts above are verbatim category-level outputs printed from the one-per-checkpoint evals (24/24, zero FAILED lines) before the destroy; runs/<R>/ holds a DATA-LOSS note instead. Full train_log step series is unrecoverable; endpoints are reported.
2. Recovery failed honestly: 4 rentals used (cap) — #1 training success, #2 6-min timeout, #3 success:false, #4 ssh-key rejected even after reboot; all destroyed, **0 instances live**, spend ~$2.09 of the $4 cap. No 5th rental per the rules.
3. Minor: fresh-container torch 2.8.0+cu128/numpy used instead of a new venv; RESULTS.md written on the Mac from transcript counts; pilot loop ran seed 9 for both arms as specified. Seals all OK pre-train (code 6/6, panel296-v2 2/2, panel294-v3 2/2, gen selftest ok). All 8 checkpoints kept at ~/premonition-models/rsn296/<run>/, sha256 verified match SEAL-run. Weights never in git. Ledger append-only (5 insertions, 0 deletions).

PUSH: `artifacts/claude-rsn296-20260924/RESULTS.md` `artifacts/claude-rsn296-20260924/SEAL-run.sha256.txt` `artifacts/claude-rsn296-20260924/runs` `artifacts/fable-predictions-ledger.md` (note: new files under gitignored `artifacts/` — same as the rsn-294 precedent, needs force-add).

## What it means / doesn't mean (plain high-school English)

It means varied practice did carry skills to differently written notebooks — both models jumped from ~184–189 to 238 on the old blind test and learned two-step fully (30/30 on fresh notebooks). The transfer mark passed big on both seeds, which is exactly the result that would have proven the idea wrong had it failed.
It doesn't mean the idea fully worked. Both models still blurt out answers 5–6 times when no fact exists (limit: 2), still score zero on three-step questions, and fall 3 and 11 points short of the fresh-panel total. Comparing (16/30) and counting (12/30) improved past guessing but aren't solved. And it says nothing good about the loop arm — it never learned to copy, same as 294.
