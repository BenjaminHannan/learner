Renting twin-B for experiments 338 and 333 — fetching configs and spinning up the GPU.
Confirmed no duplicate run exists — checking rental budget and GPU availability.
Found a suitable 5090 at ~$0.47/hr — building the code bundle for the rental.
Both arms only need the base model, no reader — creating the rental now.
Rental is live — uploading the code and verifying the GPU.
Seals verified and baseline fixed — launching the twin-B reruns for both experiments.
First rerun finished — starting the second experiment arm.
Both twin arms complete — scoring the 338 comparison and running final checks.
Files verified on the Mac — collecting billing details before cleanup.
Rental destroyed — writing the results file and ledger entry.
All deliverables in place — doing a final verification.
VERDICT: DONE — rent-twinb complete, all PUSH files ready. Not a duplicate, no budget stop, no host fail.

Marks table (integer counts; P338.4b/P333.5b themselves are judged later by the thread, not here):

| Item | Count | Bar / expected | Result |
|---|---|---|---|
| 338 arm_T rows (twin b) | 400 | 400 | done |
| 333 arm_T rows (twin b) | 70 | 70 | done |
| 338 replies with `<think` (T) | 0/400 | 0 | as expected |
| 333 replies with `<think` (T) | 0/70 | 0 | as expected |
| empty replies 338-T / 333-T | 0 / 0 | 0 | as expected |
| arm_P sha before/after cp | match (9ea6fee2…) | unchanged | unchanged |
| panel seals 338 / 333 | all OK | all OK | OK |
| first printed line, both runs | `twinb: the plain twin is Twin336b (enable_thinking=False)` | must match | matched |
| 338 score summary | P gave_up 3, ask_known 3/15, distinct 337, ms_med 850.5; T gave_up 0, ask_known 0/15, distinct 348, ms_med 590.2; convs 60 | — | recorded |

Every move:
1. `git fetch -q origin main builder-outbox`; read queue/rent-kit/VERIFY/PASSMARKS via `git show` (worktree not updated, no checkout/merge/push).
2. DUPLICATE check: no `run-twinb` on origin/builder-outbox → proceeded. Credit $6.49 ≥ $1.50 budget.
3. Built code tree (`builder-outbox` + `main`, main wins; self122_head.pt sha 5ca02173… match; 156 MB tgz). No reader (task says none needed).
4. Offer search re-run before create; created 5090 offer 44173708 → contract 52452309 (label rent-twinb, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, 16 vCPU, 80 GB, KR). Running in ~1 min. dph $0.5037.
5. Setup on rental: torch 2.8.0+cu128 CUDA True; installed transformers/safetensors/hub/accelerate/numpy; BASE snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected); route122 preflight ok.
6. Seals on rental: both panels `sha256sum -c` all OK; wrote SEAL-code-twinb.sha256.txt (5 scripts) BEFORE running — hashes match Mac recomputation.
7. Ran 338-T under twinb_wrap (own process, nohup+log): 400 rows, finished 17:06:14Z, wall ~370 s. First line correct.
8. Ran 333-T (own process): 70 rows, 17:06:57–17:08:51Z, wall 114 s. First line correct.
9. 338 score: copied registered arm_P (sha 9ea6fee2… before=after), ran scorer 17:09:38Z (~0 s); summary above. Did NOT open any judge_*.jsonl; never quoted a reply.
10. Counts-only check (step 4): 0 think / 0 empty in both new arm_T files.
11. Copied both run-twinb/ folders + SEAL file back; verified row counts and arm_P sha on Mac. Destroyed instance; 0 rent-twinb live. Hours ~0.32 × $0.5037 ≈ $0.16 (inside $1.50).
12. Wrote new RESULTS-twinb.md; appended one ledger line with `cat >>` (ledger otherwise untouched; no existing file edited).

Misses/deviations:
- None affecting results. Minor: the first ssh start wrapper hit my 60 s tool timeout but the remote process was already running (verified in follow-up poll); 338 start time is approximate (~17:00Z) since the instance is now destroyed — end times are exact file mtimes. Unrelated instances (cairn-full-0/1/2, rent-330c-dev loading) were live on the account; none are mine and none were touched.
- Additive only: new files are run-twinb/ (7 files 338 incl. scorer outputs; 1 file 333), SEAL-code-twinb.sha256.txt, RESULTS-twinb.md, plus the ledger append. Fictional names only (panel-generated names never reproduced). TEST-ONLY panels never read item by item.

What it means (plain high-school English): the fixed plain-twin now answers normally — zero leftover "thinking" blocks and zero blank replies in all 470 new answers, so it is a fair baseline for the rematch. The mechanical scoreboard for the rematch is recorded above.
What it doesn't mean: this does NOT say whether Premonition beats the fixed twin. That call (P338.4b ≥ 30/60, P333.5b ≥ 20/40) needs the blind judges, who haven't voted yet.

PUSH: artifacts/claude-chat338-20260924/RESULTS-twinb.md, artifacts/claude-chat338-20260924/SEAL-code-twinb.sha256.txt, artifacts/claude-chat338-20260924/run-twinb, artifacts/claude-cre333-20260924/run-twinb, artifacts/fable-predictions-ledger.md
