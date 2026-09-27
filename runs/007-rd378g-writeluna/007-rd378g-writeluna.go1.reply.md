Writing the lost batches with Luna — first checking seals and pilot gates.
No duplicates found — setting up the sealed workspace.
Seals verified — running self-tests and the format pilot.
Pilot hit the tool timeout while Luna calls were timing out — checking whether the process survived.
Pilot relaunched under nohup (PID 58598) — polling.
Try 2 also timed out (3×300s). Final try 3 running — continuing to poll.
Checking push conventions before committing the pilot log.
Worktree gitignores `artifacts/` — force-adding the pilot log.
Push is blocked by environment policy — verifying the prepared commit instead.
All verification done — final state check.
PILOT-FAIL

1. COMMIT: `e10b39b4b4cf3fa9fc38baeb1f00806c9591e839`. Ran everything from `/tmp/rd378g-luna.fiie1S` (archive of that commit + the 3 builder-outbox files, `uv run --offline --no-project --python 3.12 python -B`, stdlib only). Duplicate gate: 4/4 absent (no glm2N/pilot-log on origin/main or origin/builder-outbox) — proceeded.
2. SEAL: 13/13 OK (ADD-I 5, ADD-F 1, ADD-E 3, ADD-D 4, exit 0 on all four).
3. Selftests: 3/3 ok — "luna bound ok"; "rd378g writemore selftest 1/1 ok"; "rd378g tagwriter selftest 1/1 ok". Wall: ~1s.
4. PILOT (batch 18, nohup, polled to completion, 05:34:00Z–06:20:33Z, wall ~46min): batch 18 skipped after 3 tries. Pilot JSON line verbatim:
`{"dialogs": 90, "kept_from_before": 90, "new_dialogs": 0, "new_by_kind": {"chat": 0, "overheard": 0}, "batches_skipped": [18], "new_turns": 0, "new_notes": 0, "new_empty_turns": 0}`
"batch 18 ok" lines: 0. "call failed" lines: 3. Every one of the 9 Luna attempts (3 tries × 3 codex attempts) died as `RuntimeError: luna call failed after 3 tries: timeout after 300s` — zero usable replies, so this is a route loss, not a format signal. A first foreground attempt (05:02–05:32Z) showed the same pattern (3×300s timeouts on try 1) before my 30-min tool cap killed it; it was discarded, never saved. Likely cause: heavy concurrent Luna load on this Mac (lis320-luna with 3 workers, g406l-luna, and sibling 006-gate3luna all running codex exec calls simultaneously).
5. WRITE: not run (PILOT-FAIL rule). 6. TAG: not run. No second JSON line exists.
7. Worktree has only `artifacts/claude-rd378g-20260926/pilot-luna/pilot-log.txt` (8 lines, byte-identical to tmp; pilot's notes_w1.jsonl NOT copied). Committed locally as `e22e4b6bf`. Outbox push commit prepared as `09fb73b8b` (parent = outbox tip, 1 file, +8 lines) but NOT pushed: this environment denies `git push*`. To land it: `git push origin 09fb73b8bd93f280fb6a45ce55e4be2adfad03cf:builder-outbox` (rebase first if the tip moved). No writes to repo-root notebook/. No scripts edited. No stray writemore process remains.

Counts: seals 13/13 OK; selftests 3/3; pilot Luna attempts 9/9 timed out; dialogs 90 kept, 0 new; call-failed 3; batch-ok 0; steps 5–6 runs 0; files pushed 0 (blocked).
