#!/bin/bash
# y1v (Answering-from-memory thread, 2026-09-27; artifacts/claude-y1v-20260927/PLAN.md): a copy of y1t's tested vast
# kit (handoff/kit/y1tvast at 44c385094, ADDENDUM-9 to 11) with only these changes: the model is plain
# LFM2.5-1.2B-Instruct at 0f604ada; the train step runs scripts/claude_y1v_train.py (y1t's trainer with the LoRA on
# LFM's attention q/k/v/out_proj); the chain has 4 steps (drafts, train, eval, eval_plain; no H1 step); the label is
# claude-memory-y1v; results go to artifacts/claude-y1v-20260927/run; cap $1.00, at most $0.70/h; the rental checks
# artifacts/claude-y1v-20260927/SEAL.sha256.txt instead of the H1 and panel seals. The notes below are y1t's.
# y1t vast chain (Answering-from-memory thread, 2026-09-27; ADDENDUM-9). The same six steps, commands and order as
# handoff/kit/y1tpc/remote/chain.cmd: drafts, train, eval, eval_plain, h1_A, h1_B, each logged to W/<step>_log.txt with
# its exit code in W/steps.txt (UTC). Started once by bov.sh launch-chain (W/chain.started); W/chain.done at the end.
# A step that fails ends the chain, as in chain.cmd (so h1_B does not run when h1_A fails; ADDENDUM-8 discloses this).
# The Linux watch (ADDENDUM-9): while a step runs, this script looks at it every 30 s and stops it (its own child, by
# the exact PID it started: TERM, then KILL after 60 s) when its log has not changed for 20 minutes, the step passes
# its time cap, the chain passes W/chaincap.txt minutes, or a pass asked for a stop (W/stop.request: the last pass's
# deadline or the money cap). That step is recorded as rc=stopped and the chain ends. Nothing is started again.
set -u
export PATH=/opt/conda/bin:$PATH
cd "${BVY1T:-$HOME/tree}" || exit 3
[ -e W/chain.started ] && exit 9
mkdir -p W
date -u +%FT%TZ > W/chain.started
export PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
PY=$(cat W/python.txt); BASE=$(cat W/base.txt)
D=artifacts/claude-y1t-20260926/glm2/items
STALL=${STALLY1T:-20}; TICK=${TICKY1T:-30}; CAP=$(cat W/chaincap.txt 2>/dev/null || echo 180)
C0=$(date +%s)
now() { date -u +%FT%TZ; }
mins() { echo $(( ( $(date +%s) - $1 ) / 60 )); }
# one nvidia-smi line a minute (UTC, MiB used, MiB total, W) until chain.done, at most 8 hours
( i=0; while [ ! -e W/chain.done ] && [ $i -lt 480 ]; do
    echo "$(now) $(timeout 20 nvidia-smi --query-gpu=memory.used,memory.total,power.draw --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ' | tr ',' ' ')" >> W/gpu_log.txt
    i=$((i+1)); sleep "${GLY1T:-60}"; done ) &
step() {  # name, cap in minutes, script and arguments
  local s=$1 cap=$2 pid t0 why="" la rc j
  shift 2
  echo "$s start $(now)" >> W/steps.txt
  "$PY" -B "$@" > "W/${s}_log.txt" 2>&1 < /dev/null &
  pid=$!; t0=$(date +%s)
  echo "$s pid=$pid $(now) $*" >> W/pids.txt
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$TICK"
    kill -0 "$pid" 2>/dev/null || break
    la=$(( ( $(date +%s) - $(stat -c %Y "W/${s}_log.txt") ) / 60 ))
    if [ -e W/stop.request ]; then why="asked: $(head -1 W/stop.request)"
    elif [ "$la" -ge "$STALL" ]; then why="log unchanged for $la min"
    elif [ "$(mins "$t0")" -ge "$cap" ]; then why="step cap $cap min"
    elif [ "$(mins "$C0")" -ge "$CAP" ]; then why="chain cap $CAP min"; fi
    if [ -n "$why" ]; then
      echo "$s STOP pid=$pid $(now) $why" >> W/steps.txt
      kill -TERM "$pid" 2>/dev/null
      j=0; while kill -0 "$pid" 2>/dev/null && [ $j -lt 12 ]; do sleep 5; j=$((j+1)); done
      kill -0 "$pid" 2>/dev/null && { kill -KILL "$pid" 2>/dev/null; echo "$s KILL pid=$pid $(now)" >> W/steps.txt; }
      break
    fi
  done
  wait "$pid"; rc=$?
  [ -n "$why" ] && rc=stopped
  echo "$s rc=$rc end $(now)" >> W/steps.txt
  [ "$rc" = 0 ]
}
step drafts 120 scripts/claude_y1t_data.py drafts --model "$BASE" --dir $D &&
step train 60 scripts/claude_y1v_train.py --base "$BASE" --train $D/train.jsonl --dev $D/dev.jsonl --out tr &&
step eval 30 scripts/claude_y1g_doubt.py --model tr/merged --out eval &&
step eval_plain 30 scripts/claude_y1g_doubt.py --model "$BASE" --out eval_plain
echo "done $(now)" > W/chain.done
