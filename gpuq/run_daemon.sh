#!/usr/bin/env bash
# Restart the gpuq daemon forever. Use: nohup ./run_daemon.sh >/dev/null 2>&1 &   (or inside tmux)
# Running jobs are separate sessions, so they survive a daemon restart and are adopted again.
cd "$(dirname "$0")" || exit 1
export GPUQ_HOME="${GPUQ_HOME:-$HOME/gpuq}"
export GPUQ_REPO="${GPUQ_REPO:-$HOME/learner}"      # clone used for each job's commit= checkout
export GPUQ_FILES="${GPUQ_FILES:-$GPUQ_HOME/files}"  # mirror of /mnt/project-files
mkdir -p "$GPUQ_HOME"
while true; do
    python3 ./gpuq.py daemon "$@" >>"$GPUQ_HOME/daemon.stderr" 2>&1
    echo "$(date '+%F %T') daemon exited rc=$?; restarting in 10s" >>"$GPUQ_HOME/daemon.stderr"
    sleep 10
done
