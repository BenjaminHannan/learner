#!/bin/sh
set -eu

# Local coordinator for the already-configured Tailscale/SSH alias "benspc".
# It deliberately uses only ssh/scp: no rsync, package install, download, or
# process-management command is used here.

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
HOST=${BENSPC_HOST:-benspc}
REMOTE_PROJECT=${BENSPC_REMOTE_PROJECT:-C:/Users/benja/beautiful-model}
REMOTE_PYTHON='C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe'
MIN_FREE_MIB=${BENSPC_MIN_FREE_MIB:-12000}
GPU_INDEX=${BENSPC_GPU_INDEX:-0}
PILOT_SECONDS=${BENSPC_PILOT_SECONDS:-600}

# Bound both initial connection setup and an established connection that stops
# responding. These are OpenSSH client options and apply equally to ssh/scp.
SSH_CONNECT_TIMEOUT_SECONDS=10
SSH_SERVER_ALIVE_INTERVAL_SECONDS=15
SSH_SERVER_ALIVE_COUNT_MAX=2

die() {
    printf '%s\n' "remote_benspc: $*" >&2
    exit 2
}

case "$HOST" in
    *[!A-Za-z0-9_.-]*|'') die "BENSPC_HOST contains unsafe characters" ;;
esac

case "$REMOTE_PROJECT" in
    C:/Users/benja/*) ;;
    *) die "BENSPC_REMOTE_PROJECT must stay below C:/Users/benja/" ;;
esac
case "$REMOTE_PROJECT" in
    *[!A-Za-z0-9_./:-]*) die "BENSPC_REMOTE_PROJECT must not contain spaces or shell metacharacters" ;;
esac

validate_gpu_config() {
    case "$MIN_FREE_MIB" in *[!0-9]*|'') die "BENSPC_MIN_FREE_MIB must be a positive integer" ;; esac
    case "$GPU_INDEX" in *[!0-9]*|'') die "BENSPC_GPU_INDEX must be a nonnegative integer" ;; esac
    [ "$MIN_FREE_MIB" -gt 0 ] || die "BENSPC_MIN_FREE_MIB must be positive"
}

validate_pilot_seconds() {
    case "$PILOT_SECONDS" in *[!0-9]*|'') die "BENSPC_PILOT_SECONDS must be an integer from 1 to 600" ;; esac
    [ "$PILOT_SECONDS" -ge 1 ] && [ "$PILOT_SECONDS" -le 600 ] || die "BENSPC_PILOT_SECONDS must be between 1 and 600"
}

ssh_benspc() {
    ssh \
        -n \
        -o BatchMode=yes \
        -o "ConnectTimeout=$SSH_CONNECT_TIMEOUT_SECONDS" \
        -o "ServerAliveInterval=$SSH_SERVER_ALIVE_INTERVAL_SECONDS" \
        -o "ServerAliveCountMax=$SSH_SERVER_ALIVE_COUNT_MAX" \
        "$@"
}

scp_benspc() {
    scp \
        -o BatchMode=yes \
        -o "ConnectTimeout=$SSH_CONNECT_TIMEOUT_SECONDS" \
        -o "ServerAliveInterval=$SSH_SERVER_ALIVE_INTERVAL_SECONDS" \
        -o "ServerAliveCountMax=$SSH_SERVER_ALIVE_COUNT_MAX" \
        "$@"
}

remote_preflight() {
    # Read-only. In particular, no New-Item, Set-Content, process stop, or file
    # transfer happens here. Low VRAM is pilot readiness state, not a failure
    # that could accidentally gate sync or CPU-only tests.
    validate_gpu_config
    ssh_benspc "$HOST" "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"\$ErrorActionPreference='Stop'; \$python='$REMOTE_PYTHON'; \$project='$REMOTE_PROJECT'; \$gpu=$GPU_INDEX; \$minimum=$MIN_FREE_MIB; if (-not (Test-Path -LiteralPath \$python -PathType Leaf)) { throw 'Expected Python 3.10 executable is missing' }; \$smi=(Get-Command nvidia-smi.exe -ErrorAction Stop).Source; \$freeText=& \$smi --id=\$gpu --query-gpu=memory.free --format=csv,noheader,nounits; if (\$LASTEXITCODE -ne 0) { throw 'nvidia-smi memory query failed' }; \$free=[int]((\$freeText | Select-Object -First 1).Trim()); \$nameText=& \$smi --id=\$gpu --query-gpu=name --format=csv,noheader; if (\$LASTEXITCODE -ne 0) { throw 'nvidia-smi name query failed' }; \$version=& \$python --version 2>&1; Write-Output ('HOST=' + \$env:COMPUTERNAME); Write-Output ('PYTHON=' + \$python); Write-Output ('PYTHON_VERSION=' + \$version); Write-Output ('GPU_INDEX=' + \$gpu); Write-Output ('GPU_NAME=' + ((\$nameText | Select-Object -First 1).Trim())); Write-Output ('GPU_FREE_MIB=' + \$free); Write-Output ('MIN_FREE_MIB=' + \$minimum); Write-Output ('REMOTE_PROJECT=' + \$project); Write-Output ('REMOTE_PROJECT_EXISTS=' + (Test-Path -LiteralPath \$project -PathType Container)); if (\$free -lt \$minimum) { Write-Output 'PILOT_GPU_READY=false'; Write-Output 'PILOT_GPU_STATUS=LOW_VRAM' } else { Write-Output 'PILOT_GPU_READY=true'; Write-Output 'PILOT_GPU_STATUS=READY' }\""
}

sync_project() {
    ssh_benspc "$HOST" "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"New-Item -ItemType Directory -Force -Path '$REMOTE_PROJECT' | Out-Null\""

    # Copy regular project files while excluding generated/runtime state. Each
    # destination directory is created if needed. Nothing remote is deleted.
    find "$PROJECT_ROOT" \
        \( -type d \( -name .budget -o -name .runtime -o -name .git -o -name __pycache__ -o -name artifacts -o -name cache \) -prune \) -o \
        -type f -print |
    while IFS= read -r local_file; do
        relative=${local_file#"$PROJECT_ROOT/"}
        case "$relative" in
            *[!A-Za-z0-9_./-]*) die "Refusing to sync path with unsafe characters: $relative" ;;
        esac
        remote_file="$REMOTE_PROJECT/$relative"
        remote_dir=${remote_file%/*}
        ssh_benspc "$HOST" "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"New-Item -ItemType Directory -Force -Path '$remote_dir' | Out-Null\""
        scp_benspc -q -p -- "$local_file" "$HOST:$remote_file"
        printf 'synced %s\n' "$relative"
    done

    printf 'sync complete: %s:%s\n' "$HOST" "$REMOTE_PROJECT"
    printf 'No remote files were deleted. Generated .budget/.runtime/artifacts/cache data were not copied.\n'
}

remote_helper() {
    # $1 is the helper action; the remaining words are already-validated
    # helper arguments joined into the single remote command line.
    action=$1
    shift
    ssh_benspc "$HOST" "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $REMOTE_PROJECT/scripts/remote_benspc.ps1 -Action $action -ProjectPath $REMOTE_PROJECT $*"
}

join_run_args() {
    # Sets run_args_option for Pilot/Launch. No extra args means no invented
    # subcommand: run.py then takes its real default path (currently audit).
    run_args_text=""
    for arg in "$@"; do
        case "$arg" in
            *[!A-Za-z0-9_./:=,+-]*|'') die "run.py arguments may contain only conservative CLI characters: $arg" ;;
        esac
        if [ -z "$run_args_text" ]; then run_args_text=$arg; else run_args_text="$run_args_text $arg"; fi
    done
    # Windows rejects command lines over 8191 characters; stay well below.
    [ "${#run_args_text}" -le 2000 ] || die "run.py arguments exceed 2000 characters"
    run_args_option=""
    [ -z "$run_args_text" ] || run_args_option="-PilotArgsText \"$run_args_text\""
}

validate_run_id() {
    case "$1" in
        *[!A-Za-z0-9_-]*|-*|'') die "run_id must be 1-64 characters of A-Z a-z 0-9 _ - and must not start with -: $1" ;;
    esac
    [ "${#1}" -le 64 ] || die "run_id must be at most 64 characters: $1"
}

new_run_id() {
    # UTC timestamp plus 32 random bits, e.g. 20260918T141500Z-0a1b2c3d.
    printf '%s-%s' "$(date -u +%Y%m%dT%H%M%SZ)" "$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
}

run_pilot() {
    validate_gpu_config
    validate_pilot_seconds
    join_run_args "$@"
    remote_helper Pilot -MinFreeMiB "$MIN_FREE_MIB" -GpuIndex "$GPU_INDEX" -PilotSeconds "$PILOT_SECONDS" "$run_args_option"
}

launch_run() {
    validate_gpu_config
    join_run_args "$@"
    run_id=$(new_run_id)
    validate_run_id "$run_id"
    remote_helper Launch -RunId "$run_id" -MinFreeMiB "$MIN_FREE_MIB" -GpuIndex "$GPU_INDEX" "$run_args_option"
    printf 'RUN_ID=%s\n' "$run_id"
}

fetch_file() {
    # Never overwrites a local file. The copy lands in .partial first so an
    # interrupted transfer is not mistaken for a complete file next time.
    source=$1
    target=$2
    if [ -e "$target" ] || [ -L "$target" ]; then
        printf 'kept existing %s\n' "${target#"$PROJECT_ROOT/"}"
        return
    fi
    mkdir -p "${target%/*}"
    scp_benspc -q -p -- "$HOST:$source" "$target.partial"
    if [ -e "$target" ] || [ -L "$target" ]; then die "refusing to overwrite $target"; fi
    mv -- "$target.partial" "$target"
    printf 'fetched %s\n' "${target#"$PROJECT_ROOT/"}"
}

fetch_run() {
    run_id=$1
    listing=$(remote_helper Files -RunId "$run_id")
    remote_run="$REMOTE_PROJECT/.runtime/runs/$run_id"
    local_run="$PROJECT_ROOT/artifacts/benspc/$run_id"
    cr=$(printf '\r')
    while IFS= read -r line; do
        line=${line%"$cr"}
        case "$line" in
            RUNFILE=*)
                name=${line#RUNFILE=}
                source="$remote_run/$name"
                target="$local_run/$name"
                ;;
            ARTIFACT=artifacts/*)
                name=${line#ARTIFACT=artifacts/}
                source="$REMOTE_PROJECT/artifacts/$name"
                target="$local_run/artifacts/$name"
                ;;
            RUNFILE*|ARTIFACT*) die "unexpected fetch listing line: $line" ;;
            *) continue ;;
        esac
        case "$name" in
            .*|*[!A-Za-z0-9_.-]*|'') die "refusing unsafe fetch name: $name" ;;
        esac
        fetch_file "$source" "$target"
    done <<EOF
$listing
EOF
    printf 'fetch complete: %s\n' "artifacts/benspc/$run_id"
}

usage() {
    cat <<'EOF'
Usage: sh scripts/remote_benspc.sh preflight|sync|test|pilot|launch|status|fetch|stop [args...]

  preflight               read-only host, Python and GPU report
  sync                    copy project files (never deletes remote files)
  test                    CPU-only remote unittest run
  pilot [run.py args...]  blocking run, at most BENSPC_PILOT_SECONDS
  launch [run.py args...] detached run after the VRAM gate; prints RUN_ID
  status RUN_ID           alive/exited, exit code, last log lines, GPU memory
  fetch RUN_ID            copy an exited run into artifacts/benspc/RUN_ID/ (no overwrite)
  stop RUN_ID             stop only that run's verified process

Environment overrides:
  BENSPC_HOST            SSH host alias (default: benspc)
  BENSPC_REMOTE_PROJECT  remote project path below C:/Users/benja/
  BENSPC_MIN_FREE_MIB    pilot/launch VRAM floor; preflight reports it (default: 12000)
  BENSPC_GPU_INDEX       NVIDIA GPU used by preflight/pilot/launch/status (default: 0)
  BENSPC_PILOT_SECONDS   pilot wall-clock limit, 1..600 (default: 600)
EOF
}

command=${1:-}
case "$command" in
    preflight)
        [ "$#" -eq 1 ] || die "preflight takes no arguments"
        remote_preflight
        ;;
    sync)
        [ "$#" -eq 1 ] || die "sync takes no arguments"
        sync_project
        ;;
    test)
        [ "$#" -eq 1 ] || die "test takes no arguments"
        remote_helper Test
        ;;
    pilot)
        shift
        run_pilot "$@"
        ;;
    launch)
        shift
        launch_run "$@"
        ;;
    status|fetch|stop)
        [ "$#" -eq 2 ] || die "$command takes exactly one RUN_ID"
        validate_run_id "$2"
        case "$command" in
            status)
                validate_gpu_config
                remote_helper Status -RunId "$2" -GpuIndex "$GPU_INDEX"
                ;;
            fetch) fetch_run "$2" ;;
            stop) remote_helper Stop -RunId "$2" ;;
        esac
        ;;
    -h|--help|help|'')
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
