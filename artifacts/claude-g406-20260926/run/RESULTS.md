# g406 run RESULTS (partial) — label madeup-g406

Status: partial (stopped by failed calls; later task resumes from glm.jsonl).

## Inputs
- origin/main commit: 0cf94a1a826c2af694fb33edda6238fb0cf681bf
- GPU: no (Mac CPU only; GLM 5.3 Flash through Ben's opencode subscription, 4 at a time; $0). No reader, no rental, no BensPC, no OpenRouter.
- Packets: mu-402 claims packets (8 files) + mu-403 claims packets (12 files) = 560 transcripts expected.
- Common rules followed: additive only (created artifacts/claude-g406-20260926/run/ only), fictional names only, TEST-ONLY panels never read, report in final reply.

## Times (date -u)
- start: Sat Sep 26 19:36:01 UTC 2026
- end: Sat Sep 26 20:08:02 UTC 2026
- elapsed wall: ~32.0 min (matches totals JSON minutes 32.0)

## Seal (from temp dir $D, run as cwd $D)
- command: shasum -a 256 -c artifacts/claude-g406-20260926/SEAL.sha256.txt
- result: 45/45 OK, exit 0. All lines printed OK.
- Note: one early attempt ran shasum from the worktree instead of $D and reported 44 unreadable; rerun from $D passed 45/45. No files changed.

## Selftests (uv run --offline --no-project --python 3.12 python -B)
- scripts/claude_g406_glm.py --selftest → g406 selftest 6/6 ok
- scripts/claude_g406_count.py --selftest → g406 count selftest 5/5 ok

## GLM run (step 3, workers 4)
- command: uv run --offline --no-project --python 3.12 python -B scripts/claude_g406_glm.py --packets 'artifacts/claude-mu402-20260926/judge/packets/claims_j*.jsonl' --packets 'artifacts/claude-mu403-20260926/judge/packets/claims_j*.jsonl' --out artifacts/claude-g406-20260926/run/glm.jsonl --workers 4 --max-minutes 150 --max-failed 40 > artifacts/claude-g406-20260926/run/glm.log 2>&1
- glm.log last line verbatim:
{"packets": 560, "already": 0, "written": 80, "unparsed_this_run": 57, "minutes": 32.0, "stopped": "failed"}
- glm.log full (3 lines): two progress lines (40/560 marked 30 unparsed; 80/560 marked 57 unparsed) plus the totals line above.
- wc -l < glm.jsonl: 80
- usable (ok true): 23; unparsed (ok false, flags null): 57
- calls per minute: 80 packets / 32.0 min = 2.5/min total; 23 usable / 32.0 min = 0.72/min usable
- output rows shape: {src, pid, n, flags (list or null), ok, seconds}. No transcript text stored.

## Verdict (step 4, counts only, no transcript quotes)
- command: uv run --offline --no-project --python 3.12 python -B scripts/claude_g406_count.py --glm artifacts/claude-g406-20260926/run/glm.jsonl --judges artifacts/claude-mu402-20260926/judge --judges artifacts/claude-mu403-20260926/judge --write artifacts/claude-g406-20260926/run/verdict.json
- printed line verbatim:
{"packets": 560, "usable_packets": 23, "replies": 113, "judge_either": 11, "judge_both": 8, "glm_flags": 12, "glm_catches_both": 6, "glm_catches_either": 8, "glm_clean": 101, "either_in_glm_clean": 3, "recall_both": 0.75, "recall_either": 0.727, "base_either_rate": 0.0973, "either_rate_in_glm_clean": 0.0297, "either_rate_in_glm_flagged": 0.6667, "yield_clean": 0.894, "kappa_vs_either": 0.661, "V": false, "G1": true, "G2": true, "G3": true, "proved_wrong": false, "verdict": "INCONCLUSIVE", "per_source": {"claude-mu402-20260926": {"replies": 113, "either": 11, "both": 8, "glm_flags": 12, "glm_catches_both": 6}}}
- verdict.json matches the printed line (indented form), sha256 c8295dfb299e9a3f6c8ef6585b963e9fcf5db32c34e25ca2417b2ccee6a07b23.
- glm.jsonl sha256 147818e3d3ce801a0716535ae666e7a5ebda98a4379f7d843649a27c925db2a8 (80 rows).
- interpretation (counts only): V false (23/560 usable < 532 needed) so INCONCLUSIVE; on the 23 usable packets G1/G2/G3 true, proved_wrong false. All 23 usable rows are mu-402 source; 0 mu-403 rows yet.

## Errors and deviations
- stopped=failed: unparsed_this_run 57 exceeded max-failed 40 after 80 packets. Partial per spec.
- Failure mode: 57 rows have flags null, ok false. Success sample shapes normal (e.g. counts of 0/1 flags of length n). No transcript quoted here.
- Helper health: scripts/claude_glm_opencode.py --selftest → selftest ok. Single-packet probe (workers 1, limit 1, same pid that failed under workers 4) succeeded in 17.1s with usable flags. Points to concurrency/load, not auth or prompt.
- Machine load at start: uptime load ~185/183/149, disk free 53 GB (above 3 GB bar). 4 workers on a heavily loaded Mac may have raised timeouts/parse failures.
- No opencode config, auth file, or key was read, printed, copied, or committed. Only sessions created by the helper were deleted by the helper; no other session touched.
- Python ran only as uv run --offline --no-project --python 3.12 python -B (stdlib only).
- No branch checkout or push performed. PUSH path for watcher: artifacts/claude-g406-20260926/run
- Resume note: glm.jsonl has 80 rows; rerunning step 3 with same --out resumes (skips the 80). glm.log here covers only this task's single invocation.

## Files in artifacts/claude-g406-20260926/run/
- glm.jsonl (80 lines)
- glm.log (3 lines)
- verdict.json (indented verdict)
- RESULTS.md (this file)
