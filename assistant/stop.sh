#!/bin/bash
# Stop the model servers and gateway, and clear the "assistant is running" marker.
OPS="$HOME/learner-ops"
RUN="$OPS/assistant/run"
ours_re() {
  case "$1" in big) echo "mlx_lm|mlx_server_persist" ;; small) echo "mlx_lm" ;; vlm) echo "mlx_vlm" ;;
    gateway) echo "gateway.py" ;; watchdog) echo "watchdog" ;; esac
}
for n in watchdog gateway vlm small big; do
  f="$RUN/$n.pid"
  [ -f "$f" ] || continue
  pid="$(cat "$f")"
  # A pid file can outlive a reboot; only kill the pid if it is really our process.
  if kill -0 "$pid" 2>/dev/null && ps -p "$pid" -o command= 2>/dev/null | grep -qE "$(ours_re "$n")"; then
    kill "$pid" 2>/dev/null
    i=0; while kill -0 "$pid" 2>/dev/null && [ $i -lt 10 ]; do sleep 1; i=$((i + 1)); done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    echo "stopped $n"
  fi
  rm -f "$f"
done
rm -f "$OPS/ASSISTANT_RUNNING"
echo "Assistant stopped."
