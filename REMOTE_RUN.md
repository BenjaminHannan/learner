# Conservative BensPC remote workflow

This workflow targets the already-verified Tailscale/SSH host alias `benspc` and the existing Windows Python executable:

`C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe`

It intentionally uses only `ssh` and `scp`. It does not install or download anything, assumes no `rsync` on Windows, never deletes remote project data during sync, and never kills or stops pre-existing processes. SSH is detached from stdin so it cannot consume the sync file-list pipe. Every SSH/SCP connection uses `BatchMode=yes`, a 10-second `ConnectTimeout`, a 15-second `ServerAliveInterval`, and `ServerAliveCountMax=2`, so both connection setup and a dead established transport fail finitely instead of hanging indefinitely.

## 1. Read-only preflight

From the local project root:

```sh
sh scripts/remote_benspc.sh preflight
```

Preflight performs no remote writes. It verifies the fixed Python path, `nvidia-smi`, the selected GPU, current free VRAM, and whether the remote project path already exists. The default Pilot VRAM floor is 12000 MiB. Low VRAM is reported as `PILOT_GPU_READY=false` / `PILOT_GPU_STATUS=LOW_VRAM`; preflight itself still succeeds so the status check cannot block non-GPU preparation. Missing Python, missing `nvidia-smi`, or an invalid GPU query still fails the status command.

Useful overrides:

```sh
BENSPC_MIN_FREE_MIB=14000 sh scripts/remote_benspc.sh preflight
BENSPC_GPU_INDEX=0 sh scripts/remote_benspc.sh preflight
```

## 2. Sync without deleting remote data

The default destination is `C:/Users/benja/beautiful-model`:

```sh
sh scripts/remote_benspc.sh sync
```

Sync does not query or gate on GPU state. It creates missing destination directories and copies local regular files with `scp`. It never issues a remote delete and does not use `rsync --delete` or any equivalent. Existing remote files with matching project-relative names are updated; unrelated or stale remote files are left in place.

Generated/local runtime state is not copied: `.budget/`, `.runtime/`, `.git/`, `__pycache__/`, `artifacts/`, and any directory named `cache/` are pruned. The current project filename set uses conservative characters that survive the local shell, `scp`, Windows OpenSSH, and PowerShell command parsing without an extra quoting layer; sync rejects a future project-relative filename outside that set instead of attempting an ambiguous copy. `runtime.local.json` is copied as project source, but remote execution does **not** use its Mac-specific paths.

To use a different destination, keep it under the verified Windows profile and avoid spaces or shell metacharacters:

```sh
BENSPC_REMOTE_PROJECT=C:/Users/benja/beautiful-model-pilot sh scripts/remote_benspc.sh sync
```

## 3. Fast CPU tests

After a sync:

```sh
sh scripts/remote_benspc.sh test
```

The remote helper does **not** query or enforce the VRAM floor for this action. It runs from the project root with the fixed Python executable and `CUDA_VISIBLE_DEVICES=-1`, so tests remain available while GPU memory is busy. It executes every portable Python model/task/storage test. `test_remote_runner.py` is intentionally local-only because it tests the POSIX `sh` coordinator with fake `ssh`/`scp` binaries, which native Windows does not provide. If `tests/` or the portable test modules do not exist, the command fails instead of reporting a misleading zero-test success.

## 4. Explicitly time-boxed pilot

The Pilot wrapper is limited to 600 seconds and invokes the real current `run.py` entry point using a temporary Windows runtime JSON instead of the Mac-only `runtime.local.json`:

```sh
sh scripts/remote_benspc.sh pilot
```

With no extra arguments, it passes no invented subcommand, so the current `run.py` takes its real default path (currently the same audit behavior as `run.py audit`). Extra `run.py` arguments are passed through as conservative CLI tokens, for example:

```sh
BENSPC_PILOT_SECONDS=600 sh scripts/remote_benspc.sh pilot pilot --device=cuda --steps=10000 --seconds=480 --tiers=1,2 --eval-worlds=4
BENSPC_PILOT_SECONDS=600 sh scripts/remote_benspc.sh pilot pc-reader --device=cuda --steps=10000 --seconds=480 --tiers=2,3 --eval-worlds=8
```

`BENSPC_PILOT_SECONDS` is restricted to 1–600 seconds. Only Pilot and `launch` enforce `BENSPC_MIN_FREE_MIB`; sync and CPU tests do not depend on free VRAM. Pilot uses the fixed existing Windows Python installation and its already-installed packages (including Torch); the temporary runtime has no dependency import roots and performs no install or download. The helper does not enumerate or terminate existing GPU processes. If the pilot itself exceeds its deadline, it terminates only the exact child PID that this invocation started, then returns failure.

The source defines `smoke`, `pilot`, `evaluate`, and `pc-reader` subcommands. The wrapper never synthesizes one: with no extra arguments, `run.py` follows its default audit path. Keep the wrapper limit larger than the experiment's internal `--seconds` value so the experiment can finish evaluation and write its bounded result before the wrapper deadline.

The Windows runtime JSON (temporary for Pilot, `runtime.json` in the run directory for `launch`) keeps `hard_bytes=100000000000` and `steady_bytes=80000000000` as conservative project/accounted-root bounds. That accounting only sees the remote project plus any explicitly registered roots (none are added by this helper). It therefore does **not** claim or provide host-global 100 GB aggregation across unrelated BensPC directories, other projects, caches, or processes.

## 5. Long detached runs

For runs longer than the Pilot limit:

```sh
sh scripts/remote_benspc.sh launch pc-reader --device=cuda --steps=200000 --seconds=14400 --tiers=2,3
sh scripts/remote_benspc.sh status RUN_ID
sh scripts/remote_benspc.sh fetch RUN_ID
sh scripts/remote_benspc.sh stop RUN_ID
```

- `launch` applies the same argument whitelist and `BENSPC_MIN_FREE_MIB` gate as Pilot, then returns once `run.py` is running and prints `RUN_ID=<UTC timestamp>-<8 random hex>`. Its files live in `<remote project>/.runtime/runs/RUN_ID/`: `stdout.log`, `stderr.log`, `runtime.json`, `run.json` (run_id, pid, process start time, command line, started_at, args) and, after exit, `exit.json` (exit code). A new run directory is created without `-Force`, so an existing run is never overwritten. There is no wall-clock limit; bound the experiment with its own `--seconds`.
- Windows OpenSSH can terminate processes left in the SSH session's job when the connection closes, so `launch` starts a small supervisor (`-Action Supervise` of the same helper) through WMI `Win32_Process.Create`, outside that job. The supervisor starts `run.py` with `CUDA_VISIBLE_DEVICES`, `PYTHONUNBUFFERED=1` and `PYTHONIOENCODING=utf-8`, writes `run.json`, holds the process handle, and writes `exit.json` when `run.py` exits.
- `status` prints `STATE=alive|exited|unknown`, `EXIT_CODE` (or `unknown`), current GPU used/free/total MiB, and the last 20 lines of each log. It changes nothing.
- `fetch` refuses while the run is alive (a snapshot would block the final copy). Afterwards it copies the run directory's files plus every existing `artifacts/<name>` that `run.py` printed to stdout into local `artifacts/benspc/RUN_ID/` (listed artifacts under `artifacts/benspc/RUN_ID/artifacts/`). Existing local files are never overwritten; each copy lands in a `.partial` file first and is renamed only when complete. Listed names are re-validated locally; anything outside `[A-Za-z0-9_.-]` or starting with `.` aborts the fetch.
- `stop` kills only the PID in `run.json`, and only after checking that the live process at that PID has the recorded start time and exact command line. It holds the process handle across the check and the kill, so a reused PID cannot be hit. If the identity does not match, nothing is stopped.
- Every `RUN_ID` argument must be 1-64 characters of `[A-Za-z0-9_-]` and not start with `-`. The local script and the helper both check this.

## Safety defaults

- Host alias: `benspc` (override with `BENSPC_HOST`).
- Remote project: `C:/Users/benja/beautiful-model`.
- GPU index: `0`.
- Minimum free VRAM: `12000` MiB.
- Pilot limit: `600` seconds maximum. Launched runs have no wrapper limit.
- SSH connect timeout: `10` seconds; liveness probe every `15` seconds with at most `2` unanswered probes.
- No remote process cleanup or memory reclamation. The only processes ever stopped are a timed-out Pilot child and a `stop RUN_ID` process whose identity was verified.
- No remote deletion during sync.
- No package installation, dependency download, or model/data download.
