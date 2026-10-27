#!/bin/bash
# Stop the model servers and gateway, and clear the "assistant is running" marker.
OPS="$HOME/learner-ops"
RUN="$OPS/assistant/run"
for n in watchdog gateway vlm small big; do
  f="$RUN/$n.pid"
  [ -f "$f" ] || continue
  pid="$(cat "$f")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    i=0; while kill -0 "$pid" 2>/dev/null && [ $i -lt 10 ]; do sleep 1; i=$((i + 1)); done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    echo "stopped $n"
  fi
  rm -f "$f"
done
rm -f "$OPS/ASSISTANT_RUNNING"
echo "Assistant stopped."
