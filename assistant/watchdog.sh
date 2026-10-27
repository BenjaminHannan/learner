#!/bin/bash
# Memory watchdog: stops the assistant before macOS runs out of memory.
# The M1 (32 GB) hard-rebooted twice on Oct 25-26 when a 19 GB model ran on top of
# other jobs and swap. This stops ours at the first sign of trouble instead.
# Trips at "critical" pressure, at "warning" lasting WARN_MAX_SECS, or when swap has grown
# by SWAP_GROW_MB while "warning" has lasted SWAP_WARN_SECS. Short warnings and swap growth
# on their own are normal during a model load or one long prefill; on Oct 27 the old rules
# (warning 30 s, or swap +2 GB alone) stopped both Macs within a minute of every start.
OPS="$HOME/learner-ops"
RUN="$OPS/assistant/run"
DIR="$(cd "$(dirname "$0")" && pwd)"
EVERY=${WATCHDOG_EVERY:-5}
SWAP_GROW_MB=${WATCHDOG_SWAP_GROW_MB:-2048}
WARN_MAX_SECS=${WATCHDOG_WARN_MAX_SECS:-300}
SWAP_WARN_SECS=${WATCHDOG_SWAP_WARN_SECS:-10}

swap_mb() { sysctl -n vm.swapusage | awk '{for (i=1;i<=NF;i++) if ($i=="used") {v=$(i+2); sub("M","",v); printf "%d", v}}'; }
level()   { sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1; }  # 1 normal, 2 warn, 4 critical

base=$(swap_mb)
echo "$(date '+%F %T') watchdog on: swap ${base} MB; trips at critical, warning ${WARN_MAX_SECS}s, or warning ${SWAP_WARN_SECS}s with swap>$((base + SWAP_GROW_MB)) MB"
warn=0
while :; do
  [ -f "$RUN/big.pid" ] && kill -0 "$(cat "$RUN/big.pid")" 2>/dev/null || { echo "$(date '+%F %T') big model gone; watchdog exits"; exit 0; }
  lv=$(level); sw=$(swap_mb)
  if [ "$lv" -ge 2 ]; then warn=$((warn + EVERY)); else warn=0; fi
  if [ "$lv" -ge 4 ] || [ "$warn" -ge "$WARN_MAX_SECS" ] ||
     { [ "$warn" -ge "$SWAP_WARN_SECS" ] && [ "$sw" -gt $((base + SWAP_GROW_MB)) ]; }; then
    echo "$(date '+%F %T') TRIPPED: pressure level $lv, swap ${sw} MB (start ${base} MB); stopping the assistant"
    echo "$(date '+%F %T') stopped by watchdog: pressure $lv, swap ${sw} MB" > "$OPS/assistant/WATCHDOG_STOPPED"
    rm -f "$RUN/watchdog.pid"   # so stop.sh doesn't kill us halfway through
    WATCHDOG_CALL=1 "$DIR/stop.sh"
    break
  fi
  sleep "$EVERY"
done

# Recovery: bring the assistant back once memory has been normal for CALM_SECS, instead of
# leaving it off for hours (M1, Oct 27: three trips while Ben's apps came and went, nobody
# restarted it). serve.sh --autostart still applies PAUSE_OTHERS, other model jobs and the
# memory guard. At most MAX_RESTARTS per 6 h, so a Mac that is really full is left alone.
[ "${WATCHDOG_RECOVER:-1}" = 1 ] || exit 0
CALM_SECS=${WATCHDOG_CALM_SECS:-120}
MAX_RESTARTS=${WATCHDOG_MAX_RESTARTS:-4}
HIST="$RUN/watchdog-restarts.log"
now=$(date +%s)
recent=$(awk -v t=$((now - 21600)) '$1 > t' "$HIST" 2>/dev/null | wc -l | tr -d ' ')
if [ "$recent" -ge "$MAX_RESTARTS" ]; then
  echo "$(date '+%F %T') recovery: $recent restarts in 6 h already; staying off (start it by hand)"
  exit 0
fi
echo "$(date '+%F %T') recovery: waiting for ${CALM_SECS}s of normal memory pressure"
calm=0; end=$((now + 43200))
while [ "$(date +%s)" -lt "$end" ]; do
  sleep 30
  # Someone stopped it by hand (stop.sh removes the marker) or started it (serve.sh does): done.
  [ -f "$OPS/assistant/WATCHDOG_STOPPED" ] || { echo "$(date '+%F %T') recovery: stopped or started by hand; exiting"; exit 0; }
  if [ "$(level)" -le 1 ]; then calm=$((calm + 30)); else calm=0; fi
  [ "$calm" -ge "$CALM_SECS" ] || continue
  echo "$(date +%s)" >> "$HIST"
  echo "$(date '+%F %T') recovery: memory calm; running serve.sh --autostart"
  "$DIR/serve.sh" --autostart < /dev/null
  if [ -f "$RUN/big.pid" ] && kill -0 "$(cat "$RUN/big.pid")" 2>/dev/null; then
    echo "$(date '+%F %T') recovery: assistant restarted"; exit 0
  fi
  calm=0   # serve.sh declined (memory guard, PAUSE_OTHERS, another job): keep waiting
done
echo "$(date '+%F %T') recovery: gave up after 12 h"
