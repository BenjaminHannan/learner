Copy-only hunt for brd-8w — first the rules, then the search.
The brief path is empty — checking the fallback rules copy.
Rules noted. Now running the folder search.
The broad find timed out — narrowing the search to likely spots first.
Found one candidate. Now checking /private/tmp.
Search complete — one match. Inspecting it (names/sizes only) and copying.
Copy verified — 10/10 files, sizes match. Writing the report.
Done. `artifacts/` is gitignored in this worktree (pre-existing `.gitignore`, left untouched per additive-only), and standing rules forbid commits/pushes — so the deliverables live on disk as ordered. Final report:

**REPORT — find and publish brd-8w files (2026-09-26)**

1. **Search** (polymarket skipped; full-depth finds):
   - `~/Desktop/projects` → 1 match: `beautiful-model/.claude/worktrees/pull-from-main-629dc4/artifacts/claude-brd8w-20260926` — 10 files, newest mtime 2026-09-26 09:24:09
   - `~/premonition-watch` → none
   - `/private/tmp` → none (full-depth, clean)
   - Total matches on the Mac: **1**
2. **Selection:** the single candidate wins by default (most files = 10; no tie).
3. **Copy:** copied as-is to `artifacts/claude-brd8w-20260926/` in worktree `card-experiment-handoff-7c5b27`. Skip rules: 0 files over 5 MB (largest 13,537 bytes), 0 weights (`*.pt`/`*.safetensors`/`*.bin`). Copied 10/10, destination sizes re-verified identical: `PASSMARKS-brd8w.md` (5802), `RESULTS-brd8w.md` (3196), `test_puzzles.jsonl` (13537), `gpu/seed0/` ×3 (2811/5062/9977), `gpu/seed1/` ×3 (2798/5035/9970), `gpu/seed2/log.txt` (2726). No contents opened or quoted.
   - `artifacts/claude-find-brd8w-20260926/REPORT.md` written (sections 1–3 above).

Deviations/misses: one — the brief path `.../76c622f5.../scratchpad/briefs/OPUS-RULES.txt` did not exist (that scratchpad dir is empty); used standing rules from `/private/tmp/opus-rules.txt` instead. No rerun, no edits, no rent, nothing deleted, $0. PUSH: `artifacts/claude-find-brd8w-20260926/REPORT.md` + `artifacts/claude-brd8w-20260926`. DISK: 0.
