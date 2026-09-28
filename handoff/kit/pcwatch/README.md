# pcwatch: a job runner that lives on BensPC (H14, 2026-09-28)

What it is: `watcher.sh`, run in Git Bash on BensPC. Every 120 s it fetches `main` from GitHub over https, finds job files under `handoff/pcqueue/` (or `handoff/queue/`) whose header has `GPU: yes` and `RUNNER: pc`, runs ONE at a time, and pushes results plus `status/pc-watcher.txt` to the branch `pc-outbox`. It needs the Mac for nothing. Mac jobs (no `RUNNER:` line) are ignored.
Why `handoff/pcqueue/`: the Mac watcher launches every file in `handoff/queue/`, so a PC job placed there would also start on the Mac. `pcqueue/` is invisible to it.

## Ben does this once (Git Bash on BensPC)
1. Make a token: GitHub, Settings, Developer settings, Fine-grained tokens, Generate. Repository access: only `learner`. Permissions: Contents = Read and write (Metadata read is added itself). Expiry: 90 days. Copy it.
2. Save it (paste when asked; nothing is shown or printed):
   `mkdir -p ~/pcwatch; read -rsp "token: " T; echo; printf '%s' "$T" > ~/pcwatch/token; printf 'header = "Authorization: Bearer %s"\n' "$T" > ~/pcwatch/curl.cfg; unset T; icacls "$(cygpath -w ~/pcwatch)" /inheritance:r /grant:r "$USERNAME:(OI)(CI)F"`
3. Fetch the runner: `curl -fsSL -K ~/pcwatch/curl.cfg -H "Accept: application/vnd.github.raw" "https://api.github.com/repos/BenjaminHannan/learner/contents/handoff/kit/pcwatch/watcher.sh?ref=main" -o ~/pcwatch/watcher.sh`
4. Start it at every logon: `schtasks /Create /TN pcwatch /SC ONLOGON /F /TR "\"C:\Program Files\Git\bin\bash.exe\" -l \"%USERPROFILE%\pcwatch\watcher.sh\""`
5. Start it now: `schtasks /Run /TN pcwatch`
Stop it: `touch ~/pcwatch/STOP` (delete that file before starting again). After this the runner updates itself from `main`.

## What it does
- Job = the first ```bash block of the job file. It gets env `TREE` (checkout of that main commit, also the working dir), `JOB`, `JOBDIR` (scratch). Results go where the file's `PUSH:` lines say (paths inside `$TREE`; files under 5 MB, never `notebook/`, never weights).
- Job header `TIME CAP: N minutes` is enforced with `timeout` (default 180).
- GPU rule: writes `C:\Users\benja\GPU-BUSY.txt` while a job runs and deletes it after; holds new jobs if that file exists or GPU memory used is over 700 MiB (same as the Mac watcher). A GPU-BUSY.txt left by the crashed Mac job blocks the runner until it is deleted (or names nothing of ours).
- Dead job: a `.running` marker whose process is gone (reboot, kill) is cleared and the job re-run after backoff.
- Retry: job exit 5 (waiting) or 75 (fetch/network failure) is not "done": retried after 5, 10, 20, 40, 60 min, at most 8 tries. Any other exit ends the job (`runs/<job>/<job>.exit`).
- Files on `pc-outbox`: `runs/<job>/` (job file, log, exit) + the PUSH paths, and `status/pc-watcher.txt` (UTC time, GPU util and memory, running, queued, retrying, finished, log tail), pushed every cycle.
- Token: read only by a small helper that git calls; never in a URL, argument or log. Jobs run without that helper, but the token file is readable by anything running as Ben, so only commit job files you have read.

## Question for Ben (through the Director)
What git credentials does BensPC already have for `learner`? If Git Credential Manager already holds a login with push rights, steps 1 and 2 (except `curl.cfg` for step 3, or use `git clone`) are unnecessary: the runner falls back to the PC's own git login when `~/pcwatch/token` is absent. Check without exposing anything: `git config --show-origin credential.helper` and `cmdkey /list | findstr /i git`. Recommendation: skip the probing and make the token; it is 2 minutes and limits the damage to one repo.
Second question: the T3 jobs need the four checkpoints already at `C:/Users/benja/dirt3/ck/s13..s16/final.pt` (weights are never in git). Is that true on the PC now? Check: `ls ~/../dirt3/ck` or `ls /c/Users/benja/dirt3/ck/*/final.pt`. If not, they were never copied there and must be copied once from the Mac; the runner cannot do it.

## Tested / untested (honest)
- Tested on a Linux cloud box with a fake local git remote, `bash handoff/kit/pcwatch/test.sh` (12 of 12 checks): clone, launch, one at a time, results + 5 MB limit + status pushed to `pc-outbox`, exit 75 retried and not marked done, failing job marked done, Mac-only job ignored, stale marker cleared, GPU-BUSY.txt removed.
- UNTESTED: everything Windows (Git Bash, `timeout`, `kill -0` on Windows pids, `icacls`, `schtasks`, the `cygpath` step), the real token and https push, `nvidia-smi` parsing, self-update, a clone of the real repo (about 500 MB of history, disk on the PC not checked), the -pc job scripts themselves (syntax checked only; they need torch, the model and checkpoints).
