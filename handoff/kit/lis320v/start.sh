#!/bin/bash
# One queue launch; detached Mac runner owns the entire rental and copy-back.
set -eu
REPO=$1
PIN=$2
OUTBOX=$3
JOB=$4
STATE=$HOME/premonition-watch/lis320-vast
[ ! -e "$STATE/STARTED" ] || { echo 'STOP: duplicate lis320 rental state'; exit 1; }
mkdir -p "$STATE"
# Runtime code is outside the watcher's scratch tree, so it survives the queue timeout.
git -C "$REPO" show "$PIN:handoff/kit/lis320v/host.py" > "$STATE/host.py"
UV=$(command -v uv || echo "$HOME/.local/bin/uv")
LIS_PY=$("$UV" python find 3.12)
nohup caffeinate -i "$LIS_PY" -B "$STATE/host.py" --repo "$REPO" --pin "$PIN" --outbox "$OUTBOX" --job "$JOB" --state "$STATE" > "$STATE/runner.log" 2>&1 < /dev/null &
echo $! > "$STATE/launcher.pid"
echo "lis320 single rental job launched; process $(cat "$STATE/launcher.pid"); final record $STATE/END.json"
