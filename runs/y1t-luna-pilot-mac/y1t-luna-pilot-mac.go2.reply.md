Ledger has no y1t-luna entries (0 matches) — the unstaged ledger line is another task's (dl-9). No duplication risk. Now verifying the previous agent's completed steps independently in a fresh temp tree.
SEAL 8/8 OK. Running seed generation to verify the three hashes:
All 3 seed hashes match; pick line `"left": 315`. Now selftests + system checks:
W=3 confirmed: `lis320-pilot8-mac.md` (Director, 06:03 UTC) states "WORDING (3 workers, the Director's share)". Now the repo-root seal check and cleanup:
All verification complete, temp trees removed. Everything the previous agent produced checks out.

---

**VERDICT: RAN OK (previous agent finished all 8 steps; I verified every claim independently and reran nothing that costs calls).**

**Marks table (integer counts)**

| Item | Count / value |
|---|---|
| DUPLICATE gate: `origin/builder-outbox` has luna/RESULTS-luna-pilot.md | 0 (absent → not duplicate) |
| SEAL-y1t-add5 check | 8/8 OK, exit 0 |
| Seeds run | 2400 dialogs, 16816 turns |
| Split: raw_rows / parsed_kept / to_redo / unparsed | 1021 / 645 / 1755 / 376 |
| Pick: redo / done / **left** | 1755 / 1440 / **315** |
| Seed sha256 matches expected | 3/3 (42b344fb…, e80e8415…, 6184cd22…) |
| Selftests (y1t luna, y1t routefilter) | 2/2 pass |
| PILOT totals (verbatim, last log line) | `{"calls": 60, "parsed": 60, "skipped": 0, "failed_calls": 0, "batches": 3, "stopped": "done", "minutes": 20.5}` |
| `[y1tluna] call failed` lines | 0 (0 distinct errors) |
| Routefilter line (verbatim) | `{"rows": 60, "empty": 0, "r1": 0, "r2": 0, "kept": 60}` |
| raw_luna.jsonl: lines / parsed non-null / parsed null / distinct ids | 60 / 60 / 0 / 60 |
| Model field | codex/gpt-6-luna (all 60) |
| Files staged in worktree (force-added, PUSH path) | 4 |
| Ledger entries for this label (dup check) | 0 → nothing duplicated |
| Temp trees removed | 2 (prev `tmp.upTJmkoAyJ` + my `y1tver.9oBgSg`, both confirmed gone) |

**Every move:** fetch origin main+builder-outbox (exit 0) → gate check (absent) → read first 14 lines of lis-302-gpu.md + OPUS-RULES → read task file on origin/main (matches assignment) → inspected staged artifacts (4 files, index = worktree) → fresh `git archive` tree → seal 8/8 OK → reran seed/split/pick: all 3 hashes and all printed lines reproduce the RESULTS verbatim → selftests 2/2, `uptime`, `df -g /` (33 GB free) → verified pilot log in place (61 lines, totals JSON, 0 failures; **not rerun**) → reran routefilter on a copy: same counts line, output sha = input sha → counted JSON (60/60/0/60) → W check → removed my temp tree.

**W=3 and why:** task default, and the Director's current Luna share is 3 workers — `handoff/queue/lis320-pilot8-mac.md` says "WORDING (3 workers, the Director's share)". The 03:54 UTC "2 parallel calls for two jobs" lines in g406l/mu407 are those threads' own shares (each runs `--workers 1`), not a global cap; y1t's task (04:09 UTC) still specifies W=3. Pilot ran 06:38:12→06:58:43 UTC (~20.5 min), one run, no rerun.

**Misses:** none.

**Deviations:** (1) I did not rerun the pilot (forbidden) — verified it from the sealed-by-hash log instead; (2) steps 2/3/4/6 were re-executed in a throwaway tree purely as verification — no repo file changed, no Luna call made; (3) RESULTS says the task file "written 03:51 UTC" (the in-text authorship time; its commit is 04:09 UTC) — cosmetic only.

**What it means:** Luna worded the first 60 of the 315 redo dialogs, all 60 parsed, all 60 kept by the route filter, zero failed calls, outputs are in the worktree on the PUSH path and staged. **What it doesn't mean:** nothing here is trained, checked or judged; no dialog text was summarised anywhere; 255 of the 315 redo dialogs remain unwritten; no branch was checked out or pushed (watcher owns the PUSH path).

**Common-rules compliance:** additive only (no existing file edited, ledger untouched), fictional names, TEST-ONLY panels never read, ≤4 parallel processes (≤2 used), files via `git fetch`/`git archive`, no checkout/push, nothing under `~/.codex` or any key read or printed, label y1t-luna-pilot, 60 calls ≤ 60 cap, disk 33 GB ≥ floor.
