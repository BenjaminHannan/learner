# rent-q404 STOPPED by owner (Redirect) — 2026-09-26 16:17:31 UTC

Owner order: Month-end; see origin/main:artifacts/claude-q404-20260926/ADDENDUM-q404-redirect.md.
The job's result is kept but not scored (q-404 has no verdict; not a FAIL).

## Local processes stopped (plain `kill`, no `kill -9` needed)
- PID 4529: `bash .../handoff/kit/mimo/rungo4.sh /Users/ben-hannan/premonition-watch/queue/rent-q404.md`
- PID 4563: `opencode run ... --title mimo:rent-q404.go1.4529 ...` (child of 4529)
- Recheck after kill: both PIDs gone. No process was `kill -9`d.
- Not touched: PID 9640 (`mimo:000-stop-q404`, this stop task; matched grep only via embedded task text), PIDs 280/282/315 (rent-brd9), PPID 4527 (watcher). No pythonw 13036 exists (checked `ps -p 13036`: absent).
- Note: orphaned child PID 7728 (rent-q404's vastai poll loop, finite 6x45s, read-only) survived reparented to init; left alone (command line never matched; self-terminates).

## Vast instance destroyed
- Instance id: 52775380, label exactly `claude-monthend-q404` (exactly 1 such instance of 11 total; none destroyed besides this one).
- GPU: 1x RTX 5090. Status at destroy: running/running.
- Start: 1790438897 = 2026-09-26 16:08:17 UTC. Destroy confirmed: 2026-09-26 16:16:46 UTC (`show instances`: 10 left, target absent).
- Hours: 509 s = 0.14 h. dph: 0.5037037037 ($0.5037/h). Cost = dph x hours = $0.07.

## Copy-back (file counts only; no run row or panel opened, quoted, or read)
- Remote `~/tree` absent entirely; `artifacts/claude-q404-20260926/{run,score,logs}` all absent on the instance (probed via `vastai copy` channel; direct ssh port-forward was down instance-side).
- Copied back: run/ 0 files, score/ 0 files, logs/ 0 files. Nothing existed to keep; nothing scored.

## Deviations
1. OPUS-RULES.txt not found (scratchpad dir in /private/tmp/claude-502/.../76c622f5.../ is empty); proceeded on the key points quoted in the task.
2. Direct ssh to the instance failed (vast port-forward down); used `vastai copy` + rsync list-only instead. No secrets printed.
3. Ledger line uses the prescribed wording; precise counts are in this file (0 files existed).
