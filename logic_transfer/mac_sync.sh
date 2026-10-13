#!/bin/bash
# Copy LT-1 results (small files only, no checkpoints) from the Mac run root into a clone of branch
# claude/lt1-parent-checkpoints under results/mac/, commit and push; repeat every hour until the driver exits, then once more.
# usage: logic_transfer/mac_sync.sh ROOT RESULTS_CLONE DRIVER_PID
ROOT=$1; CLONE=$2; PID=$3
sync_once() {
  mkdir -p "$CLONE/results/mac"
  rsync -a --prune-empty-dirs --exclude='/rows/***' --include='*/' --include='*.json' --include='*.jsonl' --include='*.txt' --include='*.log' \
        --include='DONE' --include='FAILED' --exclude='*' "$ROOT/" "$CLONE/results/mac/"
  ( cd "$CLONE" && git add -A results/mac && git -c user.name="Claude (Mac)" -c user.email="noreply@anthropic.com" \
      commit -q -m "LT-1 Mac results $(date -u +%Y-%m-%dT%H:%MZ)" && \
    for i in 1 2 3 4; do git pull -q --rebase origin claude/lt1-parent-checkpoints && git push -q origin HEAD:claude/lt1-parent-checkpoints && break; sleep $((2**i)); done ) || true
}
while kill -0 "$PID" 2>/dev/null; do sync_once; sleep 3600; done
sync_once
