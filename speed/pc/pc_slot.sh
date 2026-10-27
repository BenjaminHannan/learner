#!/usr/bin/env bash
# PC slot wrapper (coordinator go, Oct 27): wait for add17 (pull3/DONE) and a free GPU, claim it, run run_pc.sh with the
# shared ~/bbvenv (torch 2.9.1+cu128, tf 5.20.2, peft, fla) under a 75 min hard cap, then ALWAYS release and hand off.
#   wsl:  bash speed/pc/pc_slot.sh      (from the unpacked source tree)
set -u
cd "$(dirname "$0")/../.."
W=/mnt/c/Users/benja; J=$W/pc-jobs; BUSY=$W/GPU-BUSY.txt; CARD=$J/speed-pc.md
mkdir -p speed/pc/out
LOG=$PWD/speed/pc/out/run.log
echo "waiting for $J/sleepb-pc/pull3/DONE and an empty GPU-BUSY ($(date -u +%FT%TZ))"
while [ ! -f "$J/sleepb-pc/pull3/DONE" ] || [ -s "$BUSY" ]; do sleep 60; done
echo "speed-pc (thread: Speed up training and runs everywhere) since $(date -u +%FT%TZ), cap 75 min" > "$BUSY"
printf 'job: speed-pc (expert-matmul + packing timing, 4 Qwen3.6 layers)\nowner: Speed up training and runs everywhere\nstarted: %s\ncap: 75 min\nlog: %s\n' "$(date -u +%FT%TZ)" "$LOG" > "$CARD"
release() { rc=$1; : > "$BUSY"; rm -f "$CARD"; mkdir -p $J/handoff; echo "$rc $(date -u +%FT%TZ)" > $J/handoff/GO-LOOP-BR; echo "released rc=$rc"; }
trap 'release 130; exit 130' INT TERM
PY=$HOME/bbvenv/bin/python timeout 4500 bash speed/pc/run_pc.sh > "$LOG" 2>&1
rc=$?
release $rc
touch speed/pc/out/DONE
exit $rc
