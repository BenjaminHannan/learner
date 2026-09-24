Registered rsn-299 panel run — verifying rules, seals, and time window.
Seals and panel located on origin/main. Now checking how prior dev runs reached the GPU machine.
GPU confirmed. BensPC is Windows, so I'll use Windows-compatible commands to check its state.
No BASE alias in the script itself — checking how the dev runs resolved it on BensPC.
Found a venv under lis300. Verifying it has CUDA torch and transformers.
All preflight checks done. Starting the registered run — building a fresh archive on the Mac first.
Fresh tree extracted. Running the two seal verifications from its root.
Both seals fully OK. Running the tool selftest.
Junction ready. Launching arm P (run 1 of 3).
Arm P failed at tokenizer load — missing sentencepiece/tiktoken backend. Investigating what's installed (no code changes, no network).
Searching BensPC for all Python venvs that could have run the dev passes.
Clean state. Launching arm P with the resolved snapshot path.
Arm P complete (n=60). Launching arm T.
Arm T complete. Running the score command (run 3 of 3).
Files arrived. Computing timing/call aggregates locally (numbers only, no item text).
Writing RESULTS.md (new file, additive-only).
Work complete. Final report for the director:

**Verdict: FAIL** — rsn-299 registered panel run finished cleanly (60/60 items both arms, no crashes, no re-runs), but P299.1 missed: the exact calculator added only +4 right of 60, bar was +12. P299.2 PASS, P299.3 PASS. 2 of 3 marks → registered FAIL.

**Marks table (integer counts, from OUT/panel-score.json, n=60)**

| mark | count | bar | result |
|---|---|---|---|
| P299.1 T right − P right | 32 − 28 = +4 | ≥ 12 | FAIL |
| P299.2 arith errors in T steps | 0 | 0 | PASS |
| P299.3 T wrong vs P wrong | 27 vs 29 | T ≤ P | PASS |

Per-category right/unsure/wrong, P then T — ARITH(14): 9/0/4 → 9/0/4; TIME(10): 1/0/8 → 6/0/4; COUNT(10): 5/0/5 → 5/0/5; COMPARE(10): 4/0/6 → 5/0/5; PLAN(10): 7/1/2 → 5/0/5; UNSURE(6): 2/0/4 → 2/0/4. (Remainders are "none": P 2, T 1. Neither arm ever said "not sure", unsure=0/6 both.) Totals: P 28/1/29, T 32/0/27, arith_errors 0 both. Median sec/item: P 1.105, T 1.00. T made 84 calculator calls, median 1/item, 15 rows with 0 calls. Model commit 87179e5c1f455ef22e6223592d2d61351b525bfc (sole hub-cache snapshot, so necessarily dev4's). GPU: NVIDIA GeForce RTX 5070 Ti, idle before run. GPU compute ≈ 2.7 min + loads, inside window 08:23–08:30 ET.

**Every move:** git archive origin/main@fe907ba → scp → fresh BensPC dir; SEAL-code 5/5 OK; thinkpanel SEAL OK; tool selftest "selftest ok"; snapshot_download resolved (local only); P run once (60 rows); T run once (60 rows); score once; OUT copied back (3 files, 60+60 rows verified); local numeric aggregates only; wrote RESULTS.md. No panel item opened, printed, or quoted, ever.

**Misses:** none — zero missing cases, zero mid-run failures, zero re-runs of completed arms. One omitted report-only stat (router-to-think-path count) — would need an extra TEST-ONLY pass beyond the authorized once-each runs, so deliberately not computed; affects no mark.

**Deviations:** (1) Mac 1-min load 61.7 > 60 during transfer; proceeded since all heavy work ran on BensPC's idle GPU (Mac did seconds of tar/scp). (2) `--model BASE`: brief defines BASE as the snapshot_download result; a literal `BASE` junction broke file reads (junction + hub relative symlinks → FileNotFoundError at tokenizer init, no files written, junction removed), so I passed the exact returned snapshot path. Same bytes/hash, code untouched. (3) sha256sum via Git-for-Windows (no native Windows one). (4) Ledger untouched by me (its `M` flag predates this session).

**What it means:** the calculator worked perfectly (0 slips) but barely helped (+4, not +12) — this 1B's errors are mostly wrong setups and never abstaining, not arithmetic slips. **What it doesn't mean:** not a verdict on calculators in general, bigger models, other prompts, or retries — none tested here.

**PUSH:** artifacts/claude-rsn299-20260924/run artifacts/claude-rsn299-20260924/RESULTS.md
