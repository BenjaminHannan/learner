Top-up run starting — checking duplicate gate, wait queue, and route files.
Duplicate gate clear (no `topup/` on builder-outbox) and pilot4 already finished (RESULTS committed as `8c56bf74e`), so no wait. Setting up the work tree.
`uv` needs direct invocation (zsh doesn't word-split `$PY`). Retrying with explicit path.
Split gives `to_redo: 1755` as expected. Now the hash checks.
All 5 hashes match. Running selftests and system checks.
Sessions before: 5. Starting the wording run (W=3, up to 150 min).
All counts consistent. Writing results to the worktree.
Verdict: STOPPED-TIME — 1,440 of 1,755 redo dialogs worded, 0 failures; needs one follow-up resume run for the remaining ~315.

Gates: DUPLICATE clear (no `topup/` on builder-outbox at fetch). WAIT satisfied, no waiting (pilot4 already finished, RESULTS committed as `8c56bf74e`). Fresh start, log `topup.log`, report `RESULTS-mac.md`.

| # | Check | Count / value |
|---|---|---|
| 1 | Seeds generated (seed 4027, n 2400) | 2,400 dialogs, 16,816 turns |
| 2 | Split to_redo (expected 1,755) | 1,755 (raw_rows 1,021, parsed_kept 645) |
| 3 | Hash checks (5/5 must match) | 5/5 OK |
| 4 | Selftests (oclow + topup) | 2/2 pass |
| 5 | Wording calls (W=3, batch 40) | 1,440 calls, 1,360 parsed, 0 skipped, 0 failed, 36 batches |
| 6 | "call failed" lines in topup.log | 0 |
| 7 | raw_new.jsonl lines / parsed¬null / parsed-null / distinct ids | 1,440 / 1,360 / 80 / 1,440 |
| 8 | Sessions before → after (count only) | 5 → 7 |
| 9 | Disk free | 50 GB (floor 3 GB, OK) |
| 10 | Totals line verbatim | `{"calls": 1440, "parsed": 1360, "skipped": 0, "failed_calls": 0, "batches": 36, "stopped": "time", "minutes": 151.6}` |

Moves: fetched `main` + `builder-outbox`; built temp tree via `git archive`; seeded; split; selftested; ran wording 22:13:27→00:45:03 UTC (~151.6 min, inside 170-min cap); copied `raw_new.jsonl` + `topup.log` + `RESULTS-mac.md` into `artifacts/claude-y1t-20260926/topup/`, `git add -f` staged all 3; removed temp dir (confirmed gone). No branch checkout, no commit, no push — watcher pushes.

Misses: none from errors (0 failed calls). The miss is time: 315 dialogs unworded when `--max-minutes 150` stopped the run.

Deviations (2, both reported in RESULTS-mac.md): (a) spec's archive set lacks `design/v3/60-listener/relation-names.txt`, which the seed script requires — extracted that path into the temp dir only; (b) `$PY` string doesn't word-split under zsh, so `uv` was invoked by explicit path with identical flags.

What it means in plain English: the top-up re-wording worked cleanly — about 9.5 dialogs a minute with zero failures — but the clock ran out before all 1,755 were done. The 1,440 finished wordings are saved and staged; a follow-up run resumes from `raw_new.jsonl` per step 1 and should finish the last ~315 in ~35 min. The +2 session count is other concurrent route users, untouched. No keys/configs ever read.

PUSH: `artifacts/claude-y1t-20260926/topup`
