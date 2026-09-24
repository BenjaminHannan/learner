# EXP mut-0 — PASSMARKS (sealed 2026-09-24, before any run)

The SLEEP mark must fail closed. ONE change only, additive (new files,
no existing file edited or deleted).

## 0. Problem (director-checked 2026-09-24 01:55 UTC)

- `scripts/fable_marks123_all.py:696-716` `suite_sleep()` returns
  `"pass": True` in BOTH branches while always skipping (skipped=True,
  reason recorded, no Z1-Z5 world ever driven).
- `make_daemon` sets `sleep_threshold=100000` (line 102), so no suite
  ever sleeps.
- `scripts/fable_sleepsmoke206.py` is called from none of
  `scripts/claude_292_runall.sh`, `claude_292t_runall.sh`,
  `claude_f1_runall.sh` (verified on origin/builder-outbox: the 292t
  and F1 copies are byte-identical to this worktree's; none references
  sleepsmoke206; there is no 273 runall on builder-outbox).

## 1. The change (all new files, sealed here)

- `scripts/claude_marks_mut0.py` imports `fable_marks123_all`
  read-only (never edited) and wraps `suite_sleep`: whenever the
  wrapped call skips, the wrapper returns `pass=False`,
  `status="NOT-RUN"` (and rewrites `sleep-report.json` so). A full
  run-all verdict that includes SLEEP shows `NOT-RUN` instead of
  `PASS` for the SLEEP row, and the overall verdict is `NOT-RUN`
  (never `PASS`) while SLEEP is NOT-RUN. Overall is `FAIL` if any
  non-SLEEP suite fails.
- `scripts/claude_292t_runall_mut0.sh` = copy of the sealed 292t
  runall (same agent, config, base rows, scorer) plus two steps: the
  mut0 SLEEP suite and `fable_sleepsmoke206.py`, then a combined
  `mut0-verdict.json` (via the mut0 runner's `--runall-verdict`).
- `scripts/claude_273_runall_mut0.sh` = the 292t runall structure
  pointed at the 273 agent (`scripts/claude_loop273_agent.py`,
  builder-outbox, identical to this worktree's copy) with the 292t
  config (`artifacts/claude-join292t-20260923/loop292t-config.json`,
  the config 273's recorded run used), same 292 base rows, same
  sealed 292t scorer. 273 has no prior runall of its own; its
  prediction is byte-identical rows to 292t (timing-only change).
  Output filenames keep the scorer's frozen `-292t` suffixes; the
  rows inside are 273's (declared here, not hidden).
- `scripts/claude_f1_runall_mut0.sh` = copy of the sealed F1 runall
  (same agent, config, NEW-1 bench path, mouth logging, scorer) plus
  the mut0 SLEEP suite, sleepsmoke206, and `mut0-verdict.json`.

CPU only. At most 4 parallel processes; `uptime` / `df -g /` checked
before heavy steps (inherited `waitload` in each runall).

## 2. Marks (fixed now)

- **M1 unit:** `suite_sleep` via mut0 on the 292t agent returns
  `pass=False`, `status=NOT-RUN`; the original returns `pass=True`
  (both reported).
- **M2 smoke ran:** each of the three new run-all scripts runs
  `fable_sleepsmoke206.py` to completion on its arm; per world the
  report records wall seconds and a verdict. Smoke verdict rule
  (fixed here): PASS iff `sleeps_logged>=1` AND `installed` true AND
  `sleep_overwrote_taught==0` AND `taught_good==taught_total`; else
  FAIL. PASS or FAIL are both reportable — the mark is that it RAN
  and was recorded honestly (report file exists with all fields).
- **M3 no behaviour change:** every non-SLEEP suite verdict in each
  mut0 run is identical to the last recorded run-all results:
  292t vs `artifacts/claude-join292t-20260923/run/regscore292t.json`,
  F1 vs `artifacts/claude-f1-20260923/run/regscoref1.json`,
  273 vs 292t's recorded regscore (273 predicts identical rows).
  Compared field-by-field (move-id lists, counts, gates, probe
  diffs); timing fields ignored.

Measured and reported (not a mark): sleep wall seconds per sleep on
273 = smoke world wall seconds / `sleeps_logged`.

## 3. Commands (from the repo root, each registered run once)

- M1: mut0 `--suite sleep` on the 292t agent vs original
  `--suite sleep` (out: `artifacts/claude-mut0-20260924/m1unit/`).
- M2/M3: `bash scripts/claude_292t_runall_mut0.sh
  artifacts/claude-mut0-20260924/run292t`,
  `bash scripts/claude_273_runall_mut0.sh
  artifacts/claude-mut0-20260924/run273`,
  `bash scripts/claude_f1_runall_mut0.sh
  artifacts/claude-mut0-20260924/runf1` (each once).
- Run dirs are local evidence (not pushed); counts fold into
  `results.json`.

## 4. Verdict rule

mut-0 holds iff M1 (fail-closed + original-passes both shown), M2
(3/3 smokes ran and honestly recorded), and M3 (all non-SLEEP
verdicts identical) all hold. Any sealed-file change after the seal
= FAIL. No re-seal, no silent re-runs.

## 5. Setup deviations

- OPUS-RULES.txt absent at its stated /private/tmp path (no such
  file/dir; `scratchpad/` holds no `briefs/`); the COMMON RULES in
  the task message are followed instead (same deviation class as
  F1 D8).
- No TEST-ONLY panel is opened: comparison uses scorer outputs and
  id lists only; no item text is read, quoted, or tuned on.
