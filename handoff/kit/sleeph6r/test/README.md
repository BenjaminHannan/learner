# Dry-run tests for kit sleeph6r

Written 2026-09-28 by helper H7. Nothing here rents anything, reads any key, or contacts vast.

## What the tests use
- `bin/vastai`, `bin/ssh`, `bin/python`, `bin/nvidia-smi`, `bin/pip`, `bin/date`, `bin/sleep`, `bin/caffeinate` are FAKES. `run-tests.sh` puts them first on `PATH`. The fake `python` answers `smoke` and `run` in shape only; it is not the real script.
- The "rental" is a real folder `/root/r` on the test box. The harness makes it, marks it with `.h7-fake-rental`, and refuses to touch a `/root/r` without that marker.
- Time is a virtual clock (`FAKE_SPEED=300`: one real second is five virtual minutes, see `bin/date` and `bin/sleep`), so a rental that "runs" for hours takes minutes. Faults are injected with small files under `$FAKE/` (a hung upload, a file that changes after the manifest, a lost host, and so on).
- The kit scripts run UNCHANGED. They are pointed at test folders only through their own environment overrides (`GH6V`, `MPUH6`, `KEYH6`, `PYMH6`).
- Queue jobs are run from the fenced `bash` blocks of the real queue files (`handoff/queue/h7-dirh6-*.md`), with `PIN` set to a fake repo's commit.
- The fake project is a git repo with a bare origin in the scratch folder. It is built from the real sealed files, with random stand-in checkpoints whose sha256 lines go into a fake `SEAL-run.sha256.txt`. (Scenario 2 force-pushes inside that fake origin only.)

## Run
```
TMPDIR=<a scratch folder> bash handoff/kit/sleeph6r/test/run-tests.sh          # all scenarios
TMPDIR=<a scratch folder> bash handoff/kit/sleeph6r/test/run-tests.sh 7 13     # some
```
Linux only. Needs `git`, `python3`, `pgrep`, and permission to make `/root/r`. Delete the `h7test.*` scratch folder afterwards. A full run takes about 4 minutes of real time. `OUTPUT.txt` is the output of one full run.

## Scenarios
| # | What it shows |
|---|---|
| 0 | static checks: bash syntax, no bash-4 syntax, no `timeout` command, no vast key read, offers ranking |
| 1 | happy path: start, guard, 30-minute snapshot, 4 runs finish, verified copy-back, destroy by exact id, a foreign instance left alone, collect, a second start refused |
| 2 | start refusals, nothing rented: credit under $4, a Mac checkpoint that does not match its seal, a live instance with the label, a verdict already on main, a sealed script that changed, a pin not on origin/main, no offer that fits |
| 3 | an upload hangs on the first host: cut off, that rental destroyed, second host used |
| 4 | the braces launch returns in 17 ms; the unbraced form blocks until the job ends (the 358u lesson) |
| 5 | `drive.sh` stops with FAILED on torch 2.8, on a failed smoke test, on compute capability 7.5, on a failed pip install; the guard copies logs back and destroys |
| 6 | one seed dies: recorded as DIED, the other three finish, copy-back still verified |
| 7 | money stop at $3: runs halted by exact pid, partial copy-back verified, destroyed |
| 8 | time cap (1.5 x the estimate) and stall stop (30 minutes, no log growth, idle GPU) |
| 9 | drive.sh stuck before the first LAUNCH: prelaunch stop after 45 minutes |
| 10 | host lost: the rental is stopped (not destroyed) and the Director is flagged; collect uses the snapshot and says so |
| 11 | a file changes after the manifest: retry passes; a permanent mismatch keeps the rental stopped, not destroyed |
| 12 | destroy and stop refuse an id this task did not create |
| 13 | start job killed: (a) TERM to `vstart.sh` (what a process-group kill does) destroys the rental; (b) SIGALRM to the job wrapper only (what the watcher's 75-minute alarm does) leaves `vstart.sh` running and it finishes by itself |
| 14 | no host answers ssh three times in a row: all three destroyed, HOST-FAIL; then create failing on every offer |
| 15 | the read-only Mac input check job (`000-bash-h7-dirh6-inputs`): all four match, then a tampered checkpoint is caught and named |

## What this does NOT show
- The real `vastai` and `ssh`, real GPUs, a real torch, or the real `scripts/claude_dir_h6_sleeplen.py` (it has never been run; there is no torch on the test box, only a compile check).
- macOS bash 3.2 (only a grep for bash-4 syntax; no shellcheck here).
- Real timing (the clock is virtual).
