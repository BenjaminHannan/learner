# Find + publish brd-8w files (2026-09-26)

Task: director brief 2026-09-26 17:30 UTC. Copy only: no rerun, no edits,
rent nothing, delete nothing, $0. No file contents were opened or quoted;
names and sizes only.

Note: the brief path
`.../76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt`
did not exist (that scratchpad dir is empty). Fell back to the standing
rules in /private/tmp/opus-rules.txt (additive only, fictional names, no
secrets, uv-run python, disk checks, append-only ledger, report-everything).

Disk before heavy steps: 53 GB free (df -g /), load ~61-75. No rent, no run.

## 1. Search

Command (polymarket pruned, per task):

- `find ~/Desktop/projects -path ~/Desktop/projects/polymarket -prune -o
  -type d -name 'claude-brd8w-20260926' -print` (full depth)
- `find ~/premonition-watch -type d -name 'claude-brd8w-20260926'`
  (full depth)
- `find /private/tmp -type d -name 'claude-brd8w-20260926'` (full depth)

| # | Path | Files | Newest mtime |
|---|------|-------|--------------|
| 1 | /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/pull-from-main-629dc4/artifacts/claude-brd8w-20260926 | 10 | 2026-09-26 09:24:09 (RESULTS-brd8w.md) |

- ~/premonition-watch: no match.
- /private/tmp: no match (full-depth find, clean).
- ~/Desktop/projects/polymarket: skipped per task.
- Total matches on the Mac: 1.

## 2. Selection

Only one candidate exists, so it wins by default (most files = 10;
ties: newest mtime — no tie to break).

Source: `.../pull-from-main-629dc4/artifacts/claude-brd8w-20260926`
(5 dirs, 10 files, newest 2026-09-26 09:24:09).

## 3. Copy

Copied as-is to `artifacts/claude-brd8w-20260926/` in this worktree
(`card-experiment-handoff-7c5b27`).

Skip rules applied: files over 5 MB — none present (largest is
13537 bytes); weights (*.pt, *.safetensors, *.bin) — none present.
Skipped: 0 files. Copied: 10 files. Misses/deviations: none.

Copied manifest (relative path + bytes):

- PASSMARKS-brd8w.md — 5802
- RESULTS-brd8w.md — 3196
- test_puzzles.jsonl — 13537
- gpu/seed0/brd8_seed.json — 2811
- gpu/seed0/log.txt — 5062
- gpu/seed0/streams.json — 9977
- gpu/seed1/brd8_seed.json — 2798
- gpu/seed1/log.txt — 5035
- gpu/seed1/streams.json — 9970
- gpu/seed2/log.txt — 2726

Destination file sizes re-listed after copy: identical, 10/10 present.
Source files were not opened, edited, moved, or deleted.
PUSH: artifacts/claude-find-brd8w-20260926/REPORT.md
artifacts/claude-brd8w-20260926
DISK: 0
