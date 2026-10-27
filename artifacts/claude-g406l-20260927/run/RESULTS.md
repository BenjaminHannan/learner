# g406b-L RESULTS (partial) — Luna labels, pilot PASS, full run time-stopped

Label: madeup-g406l. GPU: no (Mac CPU). LOAD-LIGHT: yes.
Mode: --mode two, --workers 1, --attempts 3, --max-failed 60.
Helper: scripts/claude_luna_codex.py via Ben's Codex plan (model gpt-6-luna), ONE at a time.

## Verdict: partial — pilot PASS, full run INCONCLUSIVE on 220/240 packets (time-stopped)

- Pilot gate: PASS (10/10 usable, 0 limit errors, exit 0). Full run started.
- Full run stopped with "time" (max-minutes 45 hit at 48.9 min): 220/240 packets usable, 0 failed rows.
- Count on best_b.jsonl (220 usable packets): V false, G1 true, G2 true, G3 true, proved_wrong false → verdict INCONCLUSIVE.
- Counts only. No transcript text. No Luna reply text.

## Origin / tree

- TREE commit (origin/main at start): aa34f14d1ba050d78b360c6e1357b45fb3f7af9d
- At 06:24:45 UTC origin/main was e49be974d0cc4ac5b04e2ec112dd1e2cfcb5efa9 (moved during run; work used aa34f14).
- Archive from origin/main: scripts, artifacts/claude-g406l-20260927, artifacts/claude-mu405-20260926/JUDGE-claims405.md, artifacts/claude-mu405b-20260926/judge.
- Extra deviation (needed for --selftest): also extracted artifacts/claude-mu402-20260926/JUDGE-claims.md from same origin/main commit aa34f14 (G.build_prompt rubric). SEAL does not cover it. No other extra files.
- Work dir D: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.dhGZGcKiq1 (removed after copy; confirmed gone — see below).
- Worktree out: artifacts/claude-g406l-20260927/run/ (luna_b.jsonl, pilot.log, luna_b.log, best_b.jsonl, verdict_b.json, arms_b.json).
- Never checked out or pushed a branch. Never read/list/printed/copied/committed anything under ~/.codex. Helper sandbox unchanged.
- Python: `uv run --offline --no-project --python 3.12 python -B` (stdlib only).

## Dates (date -u) and uptimes

- 2026-09-27 05:28:13 UTC — fetch done. uptime: 1:28 up 3 days, 15:21, 4 users, load averages: 84.29 59.50 50.47
- 2026-09-27 05:28:19 UTC — worktree check. uptime: 1:28 up 3 days, 15:21, load 94.52 62.03 51.41. df /: /dev/disk3s1s1 460G used 12G avail 33G (28%).
- 2026-09-27 05:28:25 UTC — TREE archive done.
- 2026-09-27 05:28:28 UTC — seal check.
- 2026-09-27 05:29:35 UTC — pre-pilot check. uptime load 90.47 68.47 54.78.
- 2026-09-27 05:31:55 UTC — pilot_start.txt.
- 2026-09-27 05:34:39 UTC — pilot done (pilot_end.txt same).
- 2026-09-27 05:34:47 UTC — full run started (PID 82254, full_start.txt).
- Polls (alive unless noted): 05:39:51 UTC alive (10 rows); 05:44:55 UTC alive (40 rows); 05:49:57 UTC alive (70 rows); 05:55:00 UTC alive (70 rows); 06:00:04 UTC alive (100 rows); 06:05:08 UTC alive (130 rows); 06:10:12 UTC alive (160 rows); 06:15:15 UTC alive (160 rows); 06:20:18 UTC alive (190 rows).
- 2026-09-27 06:24:22 UTC — full run not-alive (finished, stopped time). 220 rows.
- 2026-09-27 06:24:36 UTC — error-prefix count. uptime: 2:24 up 3 days, 16:17, 4 users, load 65.99 62.26 81.71.
- 2026-09-27 06:24:45 UTC — worktree copy done. uptime load 74.06 64.11 82.14.

## SEAL (from $D, must print OK on every line)

```
artifacts/claude-g406l-20260927/PASSMARKS.md: OK
artifacts/claude-mu405-20260926/JUDGE-claims405.md: OK
artifacts/claude-mu405b-20260926/judge/keys/claims_key.json: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j1.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j2.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j3.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j4.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j5.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j6.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j7.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j8.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j1.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j2.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j3.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j4.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j5.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j6.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j7.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j8.jsonl: OK
scripts/claude_g406l_luna.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_g406_2_glm.py: OK
scripts/claude_g406_glm.py: OK
scripts/claude_g406_count.py: OK
```

## SELFTESTS (each ok, else would have stopped)

- `scripts/claude_g406l_luna.py selftest-luna`:
```
[g406-2/two] pass 1: 2 written this run, 0 failed
g406l luna selftest 7/7 ok
```
- `scripts/claude_g406l_luna.py --selftest` (tail):
```
[g406-2/two] pass 1: 3 written this run, 2 failed
[g406-2/two] pass 2: 5 written this run, 2 failed
g406-2 selftest 7/7 ok
```
(first attempt without the mu402 rubric failed FileNotFoundError; after extracting that one file from same origin/main commit, reran and got 7/7 ok — reported as deviation above).
- `scripts/claude_g406_count.py --selftest`:
```
g406 count selftest 5/5 ok
```
- `scripts/claude_luna_codex.py --selftest`:
```
selftest ok: model gpt-6-luna, output-file True
```

## PILOT (10 packets, --max-minutes 30, --pilot 10)

- pilot.log (verbatim, 2 lines):
```
[g406-2/two] pass 1: 10 written this run, 0 failed
{"mode": "two", "packets": 10, "usable_before": 0, "written": 10, "failed_this_run": 0, "usable_now": 10, "minutes": 2.6, "stopped": "done"}
```
- pilot-check JSON (exit 0):
```
{"pilot_packets": 10, "rows": 10, "usable": 10, "limit_errors": 0, "pass": true}
```
- PILOTCHECK_EXIT:0
- Verdict: pilot PASS → full run started (same file, pilot rows kept).

## FULL RUN (background, --max-minutes 45)

- Start: `nohup uv run ... --mode two ... --out $O/luna_b.jsonl --workers 1 --attempts 3 --max-failed 60 --max-minutes 45 > $O/luna_b.log 2>&1 &` PID 82254 at 05:34:47 UTC.
- luna_b.log (verbatim, all lines):
```
[g406-2/two] pass 1: 30 written this run, 0 failed
[g406-2/two] pass 1: 60 written this run, 0 failed
[g406-2/two] pass 1: 90 written this run, 0 failed
[g406-2/two] pass 1: 120 written this run, 0 failed
[g406-2/two] pass 1: 150 written this run, 0 failed
[g406-2/two] pass 1: 180 written this run, 0 failed
[g406-2/two] pass 1: 210 written this run, 0 failed
{"mode": "two", "packets": 240, "usable_before": 10, "written": 210, "failed_this_run": 0, "usable_now": 220, "minutes": 48.9, "stopped": "time"}
```
- Last line of luna_b.log (verbatim): `{"mode": "two", "packets": 240, "usable_before": 10, "written": 210, "failed_this_run": 0, "usable_now": 220, "minutes": 48.9, "stopped": "time"}`
- wc -l luna_b.jsonl: 220.
- No kill needed (exited by itself; `kill -0` reported not-alive at 06:24:22 UTC). 70-minute kill rule not triggered.
- error field distinct first-60-chars (counts only, no text):
```
total_rows: 220
ok_rows: 220
distinct_error_prefixes: 1
'' 220
```

## COUNT

- `scripts/claude_g406l_luna.py --glm $O/luna_b.jsonl --best-to $O/best_b.jsonl`:
```
{"packets": 220, "usable": 220}
```
COUNT1_EXIT:0. wc -l best_b.jsonl: 220.
- `scripts/claude_g406_count.py --glm $O/best_b.jsonl --judges artifacts/claude-mu405b-20260926/judge --write $O/verdict_b.json`:
```
{"packets": 240, "usable_packets": 220, "replies": 1100, "judge_either": 158, "judge_both": 122, "glm_flags": 363, "glm_catches_both": 121, "glm_catches_either": 149, "glm_clean": 737, "either_in_glm_clean": 9, "recall_both": 0.992, "recall_either": 0.943, "base_either_rate": 0.1436, "either_rate_in_glm_clean": 0.0122, "either_rate_in_glm_flagged": 0.4105, "yield_clean": 0.67, "kappa_vs_either": 0.465, "V": false, "G1": true, "G2": true, "G3": true, "proved_wrong": false, "verdict": "INCONCLUSIVE", "per_source": {"claude-mu405b-20260926": {"replies": 1100, "either": 158, "both": 122, "glm_flags": 363, "glm_catches_both": 121}}}
```
COUNT2_EXIT:0.
- verdict_b.json matches the line above (packets 240, usable_packets 220, replies 1100, verdict INCONCLUSIVE).
- `--arm-report` (ARM_EXIT:0, verdict_b arms):
```
{"H": {"packets": 57, "replies": 285, "glm": 80, "either": 33, "both": 23, "glm_catches_both": 23}, "N": {"packets": 55, "replies": 275, "glm": 80, "either": 24, "both": 18, "glm_catches_both": 17}, "U": {"packets": 53, "replies": 265, "glm": 144, "either": 83, "both": 72, "glm_catches_both": 72}, "W": {"packets": 55, "replies": 275, "glm": 59, "either": 18, "both": 9, "glm_catches_both": 9}}
```

labeller: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e

## Notes / deviations

- Partial: time-stopped with 220/240 usable; 20 packets have no usable row. No failed rows. Never reworded any prompt.
- Selftest needed one extra rubric file from same commit (see above); otherwise followed TREE list exactly.
- Fictional names: packets use fictional names (no real-user claims quoted here). TEST-ONLY panels never read.
- $D removed after copy (see cleanup command). PUSH path: artifacts/claude-g406l-20260927/run
