Starting the y1f GPU run — fetching branches and reading the required docs.
No duplicates found and disk is clear — now checking rental status and GPU availability.
Credit is $8.60 and the cheapest 5090 is $0.41/hr — checking the rental options against the budget.
Spec confirmed against the queue file — now checking the seal and prior run details.
Rental 1 live (contract 52770475, $0.406/hr) — waiting for it to reach running.
Rental 1 failed to leave loading (host proxy error, 6 min) — destroying and re-renting on a different host.
Rental 2 also stuck in loading with the same host proxy error — destroying and trying a third host.
Rental 3 is progressing (image building, no proxy error) — waiting for running state.
Rental 3 running — setting up SSH and streaming the code tree.
Image torch (2.2.1) is too old for transformers 5 and predates Blackwell — upgrading torch per the rent-kit note.
Torch 2.13+cu129 live — finishing setup and downloading the model.
Seal 8/8 OK, selftest ok — launching the run.
The run hit a missing C compiler (triton) — inspecting the full log to confirm.
gcc installed — relaunching the run.
Run finished — all 71 asks plus pick/summary JSON. Copying results back now.
Checksums match — destroying the rental.
All artifacts verified — writing the results file and ledger line.
Fixing a transcription slip in the copied JSON line (duplicated key).
Both JSON lines verified exact — appending the ledger line.
VERDICT: COMPLETE — y1f ran clean on an RTX 5090 rental, all artifacts copied back and verified, rental destroyed. Per PLAN.md rules the outcome is NO-GO (winner L0|p382 with 15/56, below the 25 bar).

Integer counts
- Duplicate gate: 0 gpu dirs on origin/main, 0 on origin/builder-outbox, 0 live claude-memory-y1f at start — passed.
- SEAL: 8/8 OK. Selftest: 1/1 ("selftest ok").
- Rentals: 3 of max 4. Rental 1 (52770475, $0.406) ~6 min stuck loading, host docker-registry proxy error, destroyed. Rental 2 (52771466, $0.406) ~6 min, same error, destroyed. Rental 3 (52772214, $0.4963, RTX 5090) running, used, destroyed; 0 claude-memory-y1f live after.
- Run: 71/71 `[y1f]` lines, process exited on its own. Rows: 528/528 expected (8×71 minus 40 never_told gold-skips). Files copied 3/3, sha256 match 3/3 (rows 226973 B, summary 13975 B, log 4161 B).
- Money: ~$0.04 + ~$0.04 + ~$0.14 = ~$0.23 of $0.30 budget. Credit at gate: 8.599180226269851. Wall: run ~3 min (15:56:51Z–15:59Z); rental 3 ~17 min, under the 60-min cap.
- Pick (script's own): eligible 5 of 8 configs; winner L0|p382 (answerable right 15, wrong 11, never_told idk 9); go false. Best raw-greedy gold: L1|gold|raw 27/56, so the proved-wrong clause does NOT trigger. MiniCPM commit 87179e5c1f455ef22e6223592d2d61351b525bfc, matches expected.

Every deviation
1. Torch upgrade: image torch was 2.2.1, which transformers 5.17 refuses (needs ≥2.5). Upgraded to 2.13.0+cu129, uninstalled torchvision/torchaudio after, per the rent-kit's TORCH UPGRADE note. Import check passed.
2. First launch crashed before ask 1: torch 2.13's triton `bmm_outer_product` kernel needed a C compiler; image had none. Exact tail: `RuntimeError: Failed to find C compiler...` via `triton_kernels.py line 76, in bmm_outer_product` from the Llama rotary-embedding forward. Environment-only fix (`apt-get install -y gcc`), code untouched, relaunched clean. Reported here, not patched.
3. Skipped the all-MiniLM-L6-v2 download (task: no other model; y1f needs only MiniCPM5-1B).
4. Skipped the rent-kit route122 import check (y1f uses no 0.2c agent, reader, or store).
5. RESULTS-gpu.md: I mistyped one key while hand-copying the summary line, caught it, and verified both JSON lines are now byte-exact copies of log lines 76–77 (valid JSON, keys pick / answerable_right+answerable_wrong+never_told_idk).

What it means in plain English: showing the model its own past words quiz-style (L1) gets many more answers right raw (27 vs 0) but also makes up far too many wrong ones, so by the pre-written honesty rules the old layout wins by default and nothing goes forward — the next step is teaching the model to read, not rearranging the prompt.

PUSH: artifacts/claude-y1f-20260926/gpu artifacts/claude-y1f-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md (ledger line appended; artifacts/ files on disk, git-ignored, for the watcher to force-add).
