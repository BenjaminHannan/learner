Starting the pilot run — fetching the queue and verifying seals.
Seals and selftests passed — running the route leak check.
Share slot secured (N=11, W=5) — launching the 60 wording calls.
Wording done (60 calls, 54 parsed) and route verified — running the keeper checks.
All artifacts copied — writing the results summary.
Done. Verdict: PASS — all gates green, pilot6 artifacts on disk, nothing pushed (watcher pushes PUSH path).

What I did, in order:
1. `git fetch -q origin main`; origin/main = dd55fca2f79a302d055cb96b9a42b47a1130f92a. Extracted via `git archive` to /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.ajcbxnUwPs (never checked out a branch).
2. Seals: ADDENDA-5, 6, 7, 8 — every file OK.
3. Selftests: glm_oclow ok (4/4, variant low on the run line, no network); seed_cr OK (400 dialogs); check_cr OK (1 kept, 1 dropped); check_we OK (1 kept, 1 dropped); check_we2 OK (bare 'me and' no longer drops); rawcheck 4/4 ok.
4. Leak check (1 call): `{"exit": 0, "reply_ok": true, "left_after_cleanup": 0}`, exit 0 — continued.
5. Seeds (seed 326, n=60, ask-back, avoid lists): `{"dialogs": 60, "turns": 423, ... "correct_ref": 21 ...}` (full intents line in RESULTS.md).
6. Share: Sun Sep 27 00:38:14 UTC 2026, uptime load 86.45 81.03 87.62, N=11 (`opencode run` procs), W=5. No wait needed.
7. Wording (workers 5, max 40 min): start 00:38:16 UTC, end 00:41:56 UTC (3.7 min per tool). Totals verbatim: `{"calls": 60, "parsed": 54, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 3.7}`. "call failed" lines: 0, no errors. 6 unparsed (00001, 00005, 00016, 00025, 00045, 00046). Dialogs/min: 16.22.
8. Rawcheck: `{"rawcheck": "OK", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "not_in_seeds": 0}` — continued.
9. check_we2: kept 311 / turns 423, dropped 68 (dialog_unparsed 44, group_speaker 18, must_missing 17, assert_hedged 15, ...); correct_ref kept 17, dropped 4; correct kept 21/dropped 5. Style line: glm_kept 311 turns, median 18 words, p90 26 (full check.json + style line verbatim in RESULTS.md; counts only, no GLM text quoted).
10. Copied seeds/raw/kept/drops/check/style/glm.log + wrote RESULTS.md into artifacts/claude-lis320-20260926/pilot6/ (8 files). Removed tmp dir — confirmed gone (`No such file or directory`).

Misses/deviations: none. No stop conditions hit; no flags added (only the in-script --variant low); stdlib-only python via `uv run --offline --no-project --python 3.12 python -B`; no opencode config/auth read or committed; TEST-ONLY panels never read; fictional names only; GPU no, $0.

What it means in plain English: the new wording route is fast (60 prompts in under 4 minutes vs 1.5–7.5 min per call before) and clean (zero failed calls, zero route mismatches, zero leaks). Of 423 turns, 311 survived the quality filters; the narrowed group-speaker check dropped 18 turns. The correction-row families held up: 17 of 21 seeded correct_ref turns kept. Nothing was trained; this was a measurement run.

PUSH: artifacts/claude-lis320-20260926/pilot6
