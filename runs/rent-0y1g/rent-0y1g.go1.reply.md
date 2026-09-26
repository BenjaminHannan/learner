Starting the y1g GPU run — fetching latest instructions and rental kit.
Duplicate check passed and rental options found — securing the cheapest reliable GPU now.
Rental is stuck loading past the limit — destroying it and trying another host.
Second rental also stalled — destroying and trying a different image configuration.
Third rental is running — streaming code and setting up the environment.
Torch upgraded and CUDA verified — downloading the model now.
All checks passed — launching the main run.
Compiler installed — relaunching the run.
Hashes match on both ends — placing artifacts and destroying the rental to stop the clock.
Rental confirmed destroyed — writing up results and ledger.
VERDICT: COMPLETE (not partial, not stalled, not duplicate, not seal-fail). The y1g doubt-diagnosis ran once on DEV on a rented RTX 5090, all 71 asks finished, outputs copied back hash-verified, rental destroyed and confirmed gone.

Integer counts:
- SEAL check: 9 of 9 OK.
- Selftest: printed "selftest ok" (1 of 1).
- [y1g] log lines: 71 of 71 expected; rows file: 71 lines; final JSON verdict lines: 2.
- Script's own DEV verdict (copied by script into RESULTS-gpu.md, not retyped): winner C4, go=false. Answerable right: A0 26, A1 26, C3 16, C4 10, V 10. Answerable wrong-candidates: A0 27, A1 24, C3 5, C4 1, V 5. Never-told "don't know": A0 1, A1 2, C3 6, C4 9, V 9. Doubt signal: C3 true, C4 true, V true, any true.
- Rentals used: 3 of max 4. Rentals destroyed: 3. Live claude-memory-y1g after: 0. Other labels destroyed: 0.
- Spend: ~$0.10 of the $0.30 budget (rental 3, ~0.21 h x $0.4944/hr; rentals 1-2 destroyed while loading, $0). Credit at gate: 9.54.
- Model commit: 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected). GPU: NVIDIA GeForce RTX 5090, instance 52778874. Run wall: ~2 minutes (16:43:00–16:44:30 UTC).
- Code edits: 0. TEST-ONLY banks opened: 0. Weights pushed: 0. Notebook writes: 0. Secrets printed: 0.

Every move: fetched origin/main + builder-outbox; duplicate gate passed (no gpu dir on either branch, no live claude-memory-y1g); streamed code only to rental (30 MB, nothing staged on Mac); torch 2.2.1 was too old for transformers 5.17 so followed the rent-kit's TORCH UPGRADE note (torch 2.14.0+cu130, uninstalled torchvision/torchaudio, import check ok); downloaded only MiniCPM5-1B; checks passed; launched one detached process.

Deviations (2, both env-only, code untouched):
1. Rentals 1 (52776862) and 2 (52777941) never left "loading" within the 6-minute rule; destroyed each by exact id per the rent kit and re-rented. $0 spent on both.
2. First launch on rental 3 crashed on ask 1 inside generate: torch 2.14's triton `bmm_outer_product` kernel needed a C compiler the image lacked (exact traceback in the rental's fail log, not copied back). Installed gcc via apt (environment only, script never edited) and relaunched the identical command; it then completed. Reported here instead of stopping because the failure was toolchain, not the thread's code, and budget allowed one retry.

What it means in plain English: the small model on its own almost never says "I don't know" (2 of 10 never-told, 24 wrong answers), but demanding that its own repeated answers agree cuts wrong answers sharply (C4: 1 wrong, 9 of 10 never-told caught) at the cost of right answers (26 down to 10) — so by the thread's pre-written rules this is a NO-GO for bank E as-is, with all three doubt signals present but too weak to pass. That reading is the script's, not mine; I only ran it.

PUSH (watcher, I pushed nothing myself): artifacts/claude-y1g-20260926/gpu, artifacts/claude-y1g-20260926/RESULTS-gpu.md, artifacts/fable-predictions-ledger.md.
