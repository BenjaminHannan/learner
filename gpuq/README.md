# gpuq

Small stdlib-only (Python 3.9+) job queue for a Linux box with NVIDIA GPUs. Goal: GPUs never sit idle,
even for a week with nobody watching.

## Install
```
cp -r gpuq ~/gpuq-code && cd ~/gpuq-code
nohup ./run_daemon.sh >/dev/null 2>&1 &      # restarts the daemon forever; or use gpuq.service / tmux
./gpuq.py status
```
`GPUQ_HOME` (default `~/gpuq`) holds `pending/ running/ done/ failed/ logs/ out/<job>/ filler/ state.json daemon.log`.
The daemon loops every 15 s (`--tick`), finds GPUs from `nvidia-smi -L` (`--gpus 0,1` overrides) and
takes a lock so only one daemon runs. Restarting it does not kill jobs: live ones are adopted, dead ones
in `running/` go back to `pending/` (attempt+1) or `failed/` when retries are used up.

## Job file
A bash script with header comments:
```
#!/usr/bin/env bash
# gpuq: name=addendum15-R8      required; letters, digits . _ -
# gpuq: priority=90             higher first; ties -> older submit first (default 0)
# gpuq: gpus=1                  1 or 2 (default 1)
# gpuq: hours=10                wall limit; process group killed at hours*1.1 -> failed, rc=timeout (default 24)
# gpuq: owner=sleep thread
# gpuq: retries=1               auto-requeue on nonzero rc this many times (default 0)
# gpuq: mem_gb=20               informational
python train.py --out "$GPUQ_OUT"
```
The job runs as `bash JOBFILE` in its own process group, cwd = `$GPUQ_OUT`, with `CUDA_VISIBLE_DEVICES`,
`GPUQ_OUT` (`$GPUQ_HOME/out/<name>/`), `GPUQ_NAME`, `GPUQ_ATTEMPT`, `GPUQ_HOME`. Output appends to
`logs/<name>.log`. On exit `$GPUQ_OUT/_gpuq.json` records start/end/rc/gpu/attempt.

Scheduling is strict priority order. If the head job cannot start (e.g. it needs 2 GPUs and one is busy),
nothing behind it starts, so a freed GPU is kept for it (a filler runs there meanwhile). A GPU using more
than 2 GB for a process not started by gpuq is treated as busy for that loop.

## Fillers (never idle)
Put executable `*.sh` files with the same header in `$GPUQ_HOME/filler/` (1 GPU each). When a GPU is free and no
pending job can use it, the highest-priority filler runs, over and over, with `GPUQ_FILLER_RUN=1,2,3...`
(persisted in state.json) so it can pick seed N, N+1... Output: `out/filler-<name>/run<k>/`.
Fillers are preemptible: when a real job can use the slot the filler gets SIGTERM, 60 s later SIGKILL
(`--grace`), then the job starts. A filler that exits nonzero waits 30 s before rerunning.
If `filler/` has nothing usable, a built-in keepalive (torch matmul loop, else `sleep 300`) runs, with a loud
`WARNING queue empty` in `daemon.log` and an `$GPUQ_HOME/ALERT_EMPTY` file (removed once real work runs).

## Commands
```
gpuq.py submit JOB.sh [--priority N]   gpuq.py status [--json]      gpuq.py render-md QUEUE.md
gpuq.py cancel NAME                    gpuq.py requeue NAME         gpuq.py daemon [--gpus 0,1 --tick 15]
```
Pull results: `rsync -av box:gpuq/out/ ./out/` (and `box:gpuq/logs/`). Cron-friendly:
`* * * * * GPUQ_HOME=~/gpuq ~/gpuq-code/gpuq.py render-md ~/QUEUE.md`.

Tests (no GPU needed): `python -m unittest gpuq/test_gpuq.py -v` from the repo root.
