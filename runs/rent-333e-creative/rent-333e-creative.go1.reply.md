Renting a GPU for the registered run — pulling fresh instructions and marks first.
No duplicate found — mapping the code and data sources for the GPU run.
Found the panel layout and routing bars — checking the rental setup and credit.
Cheapest 5090 fits the $1.50 budget — building the code package for upload.
Package verified — securing the GPU instance.
Pre-flight clear — creating the rental.
GPU is live — uploading the code and preparing the environment.
Environment ready — starting the sealed verification and precheck.
Seal and unit tests pass — launching the full two-arm run.
Both arms finished clean — retrieving the results.
Files verified — finalizing timing and costs before shutdown.
Instance destroyed under budget — writing the final results file.
Results complete — doing a final compliance sweep.
Verdict: RAN — rent-333e-creative REGISTERED run of 333e completed, 1 rental, both arms scored. No drift, no duplicate, under budget.

Marks table (integer counts, bars from PASSMARKS-333e.md / PASSMARKS.md):

| Mark | Bar | run-e1 | run-e2 | Verdict |
|---|---|---|---|---|
| P333.1 events (P) | 0 | 0 | 0 | PASS both |
| P333.2 controls equal B | ≥29/30 | 30/30 | 30/30 | PASS both |
| E.1 e1 creative routed | ≥34/40 | 40/40 | - | PASS |
| E.1b e1 controls routed | ≤2/30 | 0/30 | - | PASS |
| Precheck dev creative | ≥37/40 (expect 39) | 39/40 | - | no drift |
| Precheck controls teach+ask | ≤3/30 (expect 2) | 0/10 + 2/20 = 2/30 | - | no drift |
| Bank creative | expect 4/5 | 4/5 | - | match |
| Bank other | expect 2/91 | 1/29+1/14+0/8+0/5+0/35 = 2/91 | - | match |
| think-rows | expect 0 | 0/70 | 0/70 | match |
| Rows arm_B/P/T | 70 each | 70/70/70 | 70/70/70 | ok |

Printed summaries:
- e1: {"P333.1":0,"P333.2":30,"P_controls_routed":0,"P_creative_routed":40,"P_fallbacks":3,"P_ms_creative_median":1063.0}
- e2: {"P333.1":0,"P333.2":30,"P_controls_routed":0,"P_creative_routed":40,"P_fallbacks":0,"P_ms_creative_median":458.7}
P333.3-5 and E.2/E.2b need blind judges — judge_creative.jsonl unopened, judged later.

Every move:
- git fetch -q origin main builder-outbox ok. DUPLICATE check: no run-e1 on builder-outbox, proceed correct. Read PASSMARKS-333e.md first.
- Tree: git archive builder-outbox + main (main on top), self122_head.pt sha 5ca02173… match, tree.tgz 157 MB.
- Credit $5.49 start, label rent-333e-creative, budget $1.50. No live rent-333e. Offer search re-run before create.
- Create 1: offer RTX 5090, contract 52480261, success:true, running ~3 min, ssh ok. 0 other rentals. HOST-FAIL not hit.
- Setup: torch 2.8.0+cu128 True, pip install ok, BASE snapshot 87179e5c… match expected, second model ok, route122 smoke ok, no reader needed.
- On rental: SEAL.sha256 3/3 OK, 333e tests 2/2 OK, 333d tests 2/2 OK. SEAL-code-333e 9/9 written BEFORE running.
- Precheck DEV-only exact match, no PRECHECK-DRIFT.
- e1 first line `cre333e: arm e1…` pass, wall ~63s. e2 first line `cre333e: arm e2…` pass, wall ~40s. All under setsid/nohup log.
- Score prep: arm_B ddc490cf… and arm_T b694b051… sha identical before/after copy and after copy-back. Score both exit 0.
- Counts 0/70 both, never quoted.
- Copy back 14 files, local sha = remote sha all 14, BEFORE destroy. Destroyed 20:47:22Z, 0 rent-333e live confirmed. Ledger appended via cat >>.
- RESULTS-333e.md created new in D. No judge file opened, no reply quoted.

Misses/deviations: none. dph $0.5037 vs search $0.469 (vast fee/disk), still ~$0.10 total (~0.205h, 20:35:04Z-20:47:22Z), under $1.50. No code edits, no torch upgrade needed.

Common-rules report: additive only (new RESULTS/SEAL/PRECHECK/run-e1/run-e2, ledger append, no edits/deletes); fictional names only (no names written, no notebook/ writes); TEST-ONLY panel never opened item-by-item/tuned/quoted — only run via specified wrapper/scorer; final reply is this report.

What it means (high-school English): both new routers passed the easy checks — they caused zero notebook messes, kept all 30 control chats identical to baseline, and routed all 40 creative asks with zero control misfires. Whether the writing is actually good needs the blind judge later.
What it doesn't mean: this doesn't prove e2 beats e1 or beats the plain writer, and doesn't prove usefulness — those need the unopened judge packets.

PUSH: artifacts/claude-cre333-20260924/RESULTS-333e.md artifacts/claude-cre333-20260924/SEAL-code-333e.sha256.txt artifacts/claude-cre333-20260924/PRECHECK-333e.json artifacts/claude-cre333-20260924/run-e1 artifacts/claude-cre333-20260924/run-e2 artifacts/fable-predictions-ledger.md
