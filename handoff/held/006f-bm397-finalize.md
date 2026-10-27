COMMON RULES (the benchmarks thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>`. Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, report in your final reply). Edit no file. If something breaks, stop and report the exact error and full traceback; do not patch.
GPU: shared (BensPC, alongside whatever job is running; $0). Or, if the Director prefers, run it as an extra lane inside rent-bm391 before that rental launches: same commands, with DATA and BASE as defined there.
SHARING: before anything, run nvidia-smi and report total/used/free memory. If free memory is under 5 GB, stop with SHARE-STOP and run nothing. Never touch another process; stop only your own, by exact PID. If your log shows CUDA out of memory, stop and report OOM.

YOUR TASK: bm-397, a copy-only answer finaliser on existing LoCoMo replies. Read origin/main:artifacts/claude-bm397-20260926/PLAN.md. The benchmark files are public test sets; the script reads them. You never open, print or quote a question, an answer or a reply (count rows only). Nothing is trained. Run ONCE.

Needs: the plain MiniCPM5-1B (BASE, revision 87179e5c1f455ef22e6223592d2d61351b525bfc, already on BensPC; no download) and bm-390's data folder DATA (the one bm-390 used on BensPC, holding locomo10.json; report its sha256; it must be the file whose sha256 the bm-390 fetch printed for locomo10.json). Windows: run Python through the same venv and line-ending wrapper bm-390 used (W in artifacts/claude-bm390-20260925/RESULTS-benspc3.md).

1. From a tree of origin/main + origin/builder-outbox (builder-outbox first, main on top): `sha256sum -c artifacts/claude-bm397-20260926/SEAL.sha256.txt` and `sha256sum -c artifacts/claude-bm397-20260926/drafts.sha256.txt`, every line OK, else stop with SEAL-MISMATCH.
2. `python -B scripts/claude_bm397_finalize.py selftest` must end with "BM397-SELFTEST PASS 7/7".
3. Copy artifacts/claude-bm390-20260925/run2/locomo_T.jsonl and artifacts/claude-bm395-20260925/run/locomo_E20.jsonl into a new folder DRAFTS.
4. ONCE: `python -B scripts/claude_bm397_finalize.py run --data DATA --runs DRAFTS --arms T,E20 --model BASE --out artifacts/claude-bm397-20260926/run`. Expect two JSON lines (arm TF, then E20F), rows 1986 each. Expect roughly 10-40 minutes.
5. RESULTS-run.md (a NEW file) in artifacts/claude-bm397-20260926/, counts only: nvidia-smi before; seal and self-test lines; DATA's locomo10.json sha256; both JSON lines verbatim; the row count and sha256 of each output file; wall time; any traceback in full.
PUSH: artifacts/claude-bm397-20260926/run artifacts/claude-bm397-20260926/RESULTS-run.md
