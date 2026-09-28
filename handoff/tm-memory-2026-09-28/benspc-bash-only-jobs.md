---
name: benspc-bash-only-jobs
description: Tested patterns for BASH-ONLY (no builder) BensPC GPU jobs from the Mac: cmd.exe quoting, Git Bash scripts as files, Windows tar, GPU gate, taskkill /T (probes 09-27)
metadata:
  type: reference
  modified: 2026-09-27T11:03:29.427Z
---
Tested on BensPC 2026-09-27 by 000-bash-probe173 and 000-bash-probe173b (runs/ on builder-outbox). The working script is handoff/queue/173-rv390-358i2-pc-d.md (58e672671).
- The ssh shell is cmd.exe. `where bash` finds WindowsApps bash.exe (WSL), so never use a bare `bash`. Git Bash lives at "C:\Program Files\Git\bin\bash.exe".
- cmd /c keeps quotes only when the line holds exactly two quote chars around an exe: `"C:\Program Files\Git\bin\bash.exe" C:/path/script.sh arg1 arg2` works. Avoid `-c "..."`, which adds a second quote pair.
- DON'T pipe a script into Git Bash's stdin (`bash.exe -s <<EOF`). In 3 of 4 calls the first ~17 bytes arrived as garbage ("@<byte>" lines), so the start of the script was lost. Ship scripts as files instead.
- Windows tar via cmd.exe was byte-exact both ways (sha256 checked):
  - in: `git archive ... | ssh benspc "mkdir C:\Users\benja\X && tar -xf - -C C:\Users\benja\X"`
  - out: `ssh -n benspc "tar -cf - -C C:\Users\benja\X rel/path" | tar -x -C .`
  - Use `-f -`. On the Mac, set COPYFILE_DISABLE=1 and LC_ALL=C (Mac cut failed with "Illegal byte sequence" on remote output). A 31 MB tree took about 3 min to go in.
- GPU gate: nvidia-smi --query-compute-apps lists dwm.exe, Discord and about 25 other C+G apps even when the GPU is idle, so never gate on "any process listed". Use the watcher's reading instead: memory.used (about 332 MiB when idle) plus `tasklist /FI "IMAGENAME eq python.exe" /NH`.
- The venv python.exe is a launcher with a child base python.exe (2 processes per run). In Git Bash, `/proc/$!/winpid` gives the launcher. `MSYS_NO_PATHCONV=1 taskkill /T /F /PID <launcher>` killed launcher and child (0 python.exe left). Git Bash needs MSYS_NO_PATHCONV=1 for tasklist/taskkill /FI /PID args.
- Native runs started with `&` plus `wait` inside a script stay alive while that ssh session is open. When ssh closes, they die (the 175 builder saw this), so the budget must end the runs before the BASH-ONLY 75 min alarm.
- cmd one-liners that work: `if exist C:\X (echo A) else (echo B)`, `rmdir /s /q C:\X`, `powershell -NoProfile -Command "(Get-PSDrive C).Free"`, `type C:\Users\benja\GPU-BUSY.txt`.
- Watcher publish used `find -size -5M` (rounds up to whole MiB: only files of 4 MiB or less pushed) until the Director fixed it to `-5120k` in b03ed54ef (09-27 ~11:44 UTC): now files just under 5 MiB are pushed.
- venv torch is 2.11.0+cu128. C: had about 4.1 GB free on 09-27.
- MAC bash: plain python3 under the watcher's bash is a broken x86 binary ('Bad CPU type', 000-bash-vastcredit-1250 err.txt, 09-27). Use PYBIN=$(uv python find 3.12) as the k1h bash jobs do. vast rentals from bash: see handoff/held/rent-rv390b-p1.md (e49a455c5): uv python for JSON, 3 host tries, destroy on EXIT and ALRM traps.
Related: [[pipeline-builders-0927]], [[mac-job-80min-shell-kill]], [[revert-and-retry-line]].
