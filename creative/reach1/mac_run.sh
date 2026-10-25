#!/bin/bash
# Reach-1 on Ben's Mac. Usage: bash mac_run.sh OUT_DIR [extra run.py args]
# Shares the Mac with the backbone thread: while ~/learner-ops/PAUSE_OTHERS exists, our server is stopped and
# run.py waits. Port 8091 (8080 belongs to the backbone thread's tau2 server). Never touches the model copy.
OUT=${1:?out dir}; shift
MODEL=${MODEL:-$HOME/learner-ops/models/lfm25-8b-q4-nothink}
PAUSE=$HOME/learner-ops/PAUSE_OTHERS
PORT=8091
PY=${PY:-python3}
mkdir -p "$OUT"
start_server() {
  $PY -m mlx_lm.server --model "$MODEL" --port $PORT --max-tokens 512 $SERVER_ARGS >> "$OUT/server.log" 2>&1 &
  echo $! > "$OUT/server.pid"
  for i in $(seq 60); do curl -s localhost:$PORT/v1/models >/dev/null && return; sleep 5; done
}
watchdog() {  # stop our server during the backbone thread's training, restart after
  while true; do
    pid=$(cat "$OUT/server.pid" 2>/dev/null)
    if [ -e "$PAUSE" ]; then
      [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && kill "$pid" && echo "$(date -u +%FT%TZ) paused, server stopped" >> "$OUT/status.log"
    elif [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
      echo "$(date -u +%FT%TZ) starting server" >> "$OUT/status.log"; start_server
    fi
    [ "$(df -g "$HOME" | awk 'NR==2{print $4}')" -lt 3 ] && echo "$(date -u +%FT%TZ) disk < 3 GB" >> "$OUT/status.log"
    sleep 20
  done
}
watchdog & WD=$!
trap 'kill $WD; kill $(cat "$OUT/server.pid" 2>/dev/null) 2>/dev/null' EXIT
$PY "$(dirname "$0")/run.py" all --base-url http://127.0.0.1:$PORT/v1 --model "$MODEL" --out "$OUT" \
  --pause-file "$PAUSE" --concurrency 4 "$@" 2>&1 | tee -a "$OUT/run.log"
