Starting lis-300 build — reading rules and specs first.
Files are on origin/main. Reading the remaining specs and scripts.
Code reviewed. Now checking BensPC GPU availability.
BensPC is up, GPU idle (15.4 GB free). Checking its Python/torch env.
71.8 GB free on C:. Setting up the venv and work dirs on BensPC now.
TLS cert env issue on BensPC. Checking env vars.
TLS fixed. Installing the training stack (torch CUDA + transformers + peft + safetensors + HF hub) — this is a big download.
Install complete: torch 2.14.0, transformers 5.17.0, peft 0.21.0. Verifying CUDA in the venv.
CPU-only torch wheel — need the CUDA build from the PyTorch index.
Reinstall is downloading now (blocked as expected). Polling the log.
CUDA works. Now packaging the code + data for BensPC via git archive.
No Unix tools on cmd — I'll write a small seal-check script on the Mac and copy it over.
SEAL all OK (14/14). Building the training data.
Classic cmd trailing-space gotcha — retrying with quoted set.
Model downloaded (2.16 GB). Getting the commit hash.
Commit `87179e5c`. Now launching training detached (writes log, survives SSH exit).
No python running — the detached launch didn't survive. Testing detach behavior with a trivial probe first.
My tool timeout hit (10 min) while training runs. Checking whether it survived on BensPC.
Training survived and is computing (97% util, 225W). Checking progress.
Step 1840/4002 at ~10 min, ~4877 tok/s. ETA ~12 more min. Updating todos and waiting.
Training finished. Reading the summary.
Dev read done. Running the threshold sweep.
Files were written (the counter display had a short-circuit bug). Verifying per-file counts.
Per-src dev numbers captured. Saving the sweep table to file and pulling it down.
T=0.995 confirmed. Creating THRESHOLD.txt and dev_sweep.txt (new files), then sealing before the panel.
Seal written before panel. Now step 6 — verifying the panel key seal first (without opening any items).
Key seal OK (2/2). Writing a rows-maker that never prints turn text.
240 rows, schema as expected. Running the reader on the panel — once.
Panel read once (240 rows). Checking key schema (field names only) before scoring.
All counts reconcile (240 turns, 137 gold writes, 71 hits). Pulling the score files.
Copying the merged model to the Mac (2.16 GB) while I draft RESULTS.md.
Model hash matches. Writing RESULTS.md.
Final check: PUSH set complete, worktree has only additions.
Verdict: FAIL (P300.2 recall 71/137 = 51.8%, bar ≥85%; also under 75%, so the PASSMARKS "proved wrong" clause trips).

Marks table (arm A = reader + compiler at T = 0.995, 240 blind panel turns, run once on BensPC RTX 5070 Ti):

| Mark | Bar | Integer counts | Result |
|---|---|---|---|
| P300.1 wrong-save turns | ≤ 1 of 240 | 1 of 240 | PASS |
| P300.2 exact recall of gold writes | ≥ 85% | 71 of 137 (51.8%) | FAIL |
| P300.3 ASK read correctly | ≥ 90% | 38 of 40 (95.0%) | PASS |
| P300.4 our/we ask whose | ≥ 90% | 20 of 20 (100%) | PASS |
| P300.5 unparseable outputs | ≤ 2% | 0 of 240 | PASS |
| P300.6 median read ms | ≤ 1,500 | median 1492.45, p90 2051.0, max 3115.1 | PASS |

Every move / miss (category level only, nothing quoted):
- The 1 wrong-save turn is in pronoun-ambiguous (a no-save turn). All no-save families otherwise had 0 wrong turns: negation 12, check 12, suppose 10, plan 10, reported 8, chat 8, our-we 20 turns with 0 gold writes.
- Recall hits by family at T: tell-single 11/14, tell-multi 8/21, tell-plural 11/17, tell-appositive 6/20, tell-verb 7/12, tell-typo 5/8, tell-self 6/8, correct 7/17, short-answer 4/8, pronoun-clear 6/12; 66 gold facts held back.
- ASK misses: 2, both in question-twohop (3/5); wh 12/12, inverse 8/8, yesno 8/8, lowercase 7/7.
- Report-only: wrong facts per saved fact 1/72 at T (7/140 at T=0); per turn 1/240 at T (7/240 at T=0). At T=0: recall 133/137 (97.1%), 7 wrong turns (5 pronoun-ambiguous, 1 tell-verb, 1 tell-typo), turn-exact 98/102.
- Training: 4002/4002 steps, 21.78 min, 4851.9 tok/s, dev loss 0.0842, batch 16, no OOM. Base MiniCPM5-1B commit 87179e5c, safetensors sha256 7ab8fd86…; merged sha256 112880d6…, kept at ~/premonition-models/lis300-merged/ (hash verified) and on BensPC. Dollars spent: $0 (BensPC free, no rental).

Deviations (environment only; sealed code imported and run unmodified, never patched):
1. Windows cp1252 default broke opus jsonl reads → set PYTHONUTF8=1 (env only).
2. BensPC's system REQUESTS_CA_BUNDLE points at a deleted file → pointed at the venv certifi bundle (env only).
3. Fresh venv got CPU-only torch → installed torch 2.11.0+cu128 from the PyTorch cu128 index into the NEW venv (pip install explicitly allowed). Final: torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0.
4. `start`-detached processes die when SSH closes (probe proved it), so training ran in the foreground of one SSH call and survived a client-side timeout server-side.
5. Batch-8 fallback not needed; 150-min cap never bound. Seals: data 14/14 OK, key 2/2 OK, SEAL-run written before the panel.

What it means (plain high-school English): the home-trained 1B listener can read — with the safety gate off it gets 133 of 137 facts, asks whose on all 20 our/we turns, and reads 38 of 40 questions. But the dev-picked safety rule (save only at 99.5% sure) throws away half the true facts (66 of 137) and still lets 1 wrong save through, so safe-and-useful was not reached together.

What it doesn't mean: it doesn't mean the reader is a bad reader (97.1% ungated), and it doesn't mean the test leaked (N–Z names never trained on, seals checked, panel run exactly once). One diagnosis-driven follow-up (lis-301+) is allowed.

PUSH files are on disk: artifacts/claude-lis300-20260923/{RESULTS.md,THRESHOLD.txt,SEAL-run.sha256.txt,dev_sweep.txt,panel_score.json,panel_score_T0.json,train_summary.json,train_log.jsonl} plus 6 appended ledger lines P300.1–P300.6.
