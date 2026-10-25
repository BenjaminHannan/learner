#!/bin/bash
# What is up, memory, and the last gateway log lines.
RUN="$HOME/learner-ops/assistant/run"
check() {  # name port path
  local pid="-"; [ -f "$RUN/$1.pid" ] && pid="$(cat "$RUN/$1.pid")"
  if curl -fsS -m 2 "http://127.0.0.1:$2$3" >/dev/null 2>&1; then
    echo "$1: UP (port $2, pid $pid)"
  elif [ "$pid" != "-" ] && kill -0 "$pid" 2>/dev/null; then
    echo "$1: STARTING / not answering yet (pid $pid)"
  else
    echo "$1: down"
  fi
}
check big 18080 /v1/models
check small 18081 /v1/models
check gateway 8090 /v1/models
[ -f "$HOME/learner-ops/PAUSE_OTHERS" ] && echo "note: PAUSE_OTHERS exists (another job reserved the Mac)"
echo
echo "Memory:"
if command -v memory_pressure >/dev/null 2>&1; then memory_pressure | tail -n 1; fi
if command -v vm_stat >/dev/null 2>&1; then vm_stat | head -n 6; fi
command -v free >/dev/null 2>&1 && free -h | head -n 2
echo
echo "Last gateway log lines:"
[ -f "$RUN/gateway.log" ] && tail -n 5 "$RUN/gateway.log" || echo "(no log yet)"
