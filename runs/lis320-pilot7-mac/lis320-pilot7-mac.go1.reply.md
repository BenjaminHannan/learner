Starting your 60-call Luna pilot — fetching ground truth and seals.
Ground truth pinned — now verifying seals.
Seals passed but selftests need a closer look — inspecting the failure.
Found it — the scripts need to run from the extracted tree. Re-running.
Seeds ready — starting the Luna wording run.
Wording complete — running quality checks.
All checks done — packaging results for handoff.
Files staged — writing the final counts.
Cleanup verified — confirming the handoff package.
VERDICT: DONE — lis320-pilot7 executed fully, all gates ran, files in artifacts/claude-lis320-20260926/pilot7/, temp dir removed. No training, no marks claimed.

MARKS TABLE (integer counts):
- origin/main commit: 8e2590aa8a8b6b4f1ba2ba8388300384b52d2137
- seals: 3 files, all OK (6/6, 6/6, 8/8 lines OK)
- selftests: 5/5 pass (4 code + 1 live Luna call)
- seeds: 60 dialogs, 425 turns
- wording calls: 60 calls, 60 parsed, 0 skipped, 0 failed_calls, 2 batches, 17.5 minutes
- rawcheck2: OK, 60 rows, 0 duplicate_ids, 60 model_ok, 60 temperature_null, 0 dup3_texts, 0 not_in_seeds
- check: 425 turns, 404 kept, 21 dropped
- kept_by_family total: 404 (teach 138, backref 29, correct 23, correct_ref 22, etc. — full in RESULTS.md)
- style: glm_kept turns 404, words_median 10, words_p90 30
- call-failed lines: 0; distinct errors: 0
- TEST-ONLY panels read: 0

EVERY MOVE:
1. git fetch -q origin main; archived origin/main to /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.s26f5jEDyZ, mkdir pilot7, rev-parse recorded.
2. Seals 6/8/9 checked from $D — all OK.
3. Selftests from $D (uv run --offline --no-project --python 3.12 python -B): luna ok, seed_cr OK 400 dialogs, check_we2 OK 1 kept 1 dropped, rawcheck2 7/7 ok, luna_codex live selftest ok: model gpt-6-luna, output-file True.
4. Seeds seed 327 n 60 ask-back with avoid lists → printed JSON verbatim (60 dialogs, 425 turns) in RESULTS.md.
5. Wording workers 3 max-minutes 40 → start Sun Sep 27 05:18:26 UTC 2026 (uptime load 71.14), end Sun Sep 27 05:35:55 UTC 2026 (load 126.70), totals JSON verbatim, 0 call-failed.
6. Rawcheck2 Luna id → OK JSON verbatim (no ROUTE-FAIL).
7. Check_we2 → check.json verbatim (404 kept / 21 dropped), style printed line verbatim.
8. Copied seeds.jsonl, raw.jsonl, kept.jsonl, drops.jsonl, check.json, style.json, glm.log to worktree pilot7 + wrote RESULTS.md (counts only). rm -rf exact $D confirmed gone (ls: No such file or directory).

MISSES/DEVIATIONS:
- First selftest try ran from worktree cwd not $D → 3x `repo not found: set LEARNER_REPO`; reran from $D per task, all passed. Only deviation.
- No failed Luna calls, no timeouts, no route fails, no push/branch actions (watcher pushes PUSH path).

WHAT IT MEANS (plain English):
- The new Luna writer produced all 60 test dialogs without crashing — like swapping a pen and it still writes.
- It does NOT mean the pilot passed its quality thresholds — that decision uses fixed pre-set marks (ADDENDUM-9/PILOT-THRESHOLDS items 1-5 plus human Item 5 read) by others, not this run. Nothing was trained.

PUSH: artifacts/claude-lis320-20260926/pilot7
Dialogs/minute: 60/17.5 ≈ 3.43.
Common-rules report: additive-only kept, fictional names only, TEST-ONLY never read, no ~/.codex/keys touched.
