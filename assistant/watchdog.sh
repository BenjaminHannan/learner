#!/bin/bash
# Memory watchdog: stops the assistant before macOS runs out of memory.
# The M1 (32 GB) hard-rebooted twice on Oct 25-26 when a 19 GB model ran on top of
# other jobs and swap. This stops ours at the first sign of trouble instead.
# Trips when memory pressure reaches "warning" or swap grows by more than SWAP_GROW_MB.
OPS="$HOME/learner-ops"
RUN="$OPS/assistant/run"
DIR="$(cd "$(dirname "$0")" && pwd)"
EVERY=${WATCHDOG_EVERY:-5}
SWAP_GROW_MB=${WATCHDOG_SWAP_GROW_MB:-2048}

swap_mb() { sysctl -n vm.swapusage | awk '{for (i=1;i<=NF;i++) if ($i=="used") {v=$(i+2); sub("M","",v); printf "%d", v}}'; }
level()   { sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1; }  # 1 normal, 2 warn, 4 critical

base=$(swap_mb)
echo "$(date '+%F %T') watchdog on: swap ${base} MB, trips at pressure>=2 or swap>$((base + SWAP_GROW_MB)) MB"
while :; do
  [ -f "$RUN/big.pid" ] && kill -0 "$(cat "$RUN/big.pid")" 2>/dev/null || { echo "$(date '+%F %T') big model gone; watchdog exits"; exit 0; }
  lv=$(level); sw=$(swap_mb)
  if [ "$lv" -ge 2 ] || [ "$sw" -gt $((base + SWAP_GROW_MB)) ]; then
    echo "$(date '+%F %T') TRIPPED: pressure level $lv, swap ${sw} MB (start ${base} MB); stopping the assistant"
    echo "$(date '+%F %T') stopped by watchdog: pressure $lv, swap ${sw} MB" > "$OPS/assistant/WATCHDOG_STOPPED"
    rm -f "$RUN/watchdog.pid"   # so stop.sh doesn't kill us halfway through
    "$DIR/stop.sh"
    exit 0
  fi
  sleep "$EVERY"
done
