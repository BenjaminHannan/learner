#!/bin/bash
# Start the big model, optional small model, and the gateway. Idempotent.
# Usage: serve.sh [--yes]
# Saved settings (e.g. ASSISTANT_SMALL_MODEL) live in ~/learner-ops/assistant/config.sh.
[ -f "$HOME/learner-ops/assistant/config.sh" ] && . "$HOME/learner-ops/assistant/config.sh"
PY="${ASSISTANT_PY:-$HOME/learner-ops/speedbench/venv312/bin/python}"
BIG_MODEL="${ASSISTANT_BIG_MODEL:-mlx-community/Qwen3.6-35B-A3B-4bit}"
SMALL_MODEL="${ASSISTANT_SMALL_MODEL:-}"   # empty = no small server
SMALL_ARGS="${ASSISTANT_SMALL_ARGS:-}"     # e.g. "--trust-remote-code"
SMALL_TEMPLATE="${ASSISTANT_SMALL_TEMPLATE:-}"  # jinja file; K2 needs its no-think template

OPS="$HOME/learner-ops"
RUN="$OPS/assistant/run"
DIR="$(cd "$(dirname "$0")" && pwd)"
BIG_PORT=8080; SMALL_PORT=8081; GW_PORT=8090
YES=0; [ "${1:-}" = "--yes" ] && YES=1
mkdir -p "$RUN" "$OPS/diary"

alive()   { [ -f "$RUN/$1.pid" ] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }
answers() { curl -fsS -m 2 "http://127.0.0.1:$1$2" >/dev/null 2>&1; }
up()      { alive "$1" && answers "$2" "$3"; }   # name port path

wait_for() {  # name port path timeout
  local i=0
  while [ $i -lt "$4" ]; do
    answers "$2" "$3" && return 0
    alive "$1" || { echo "  $1 stopped; last log lines:"; tail -n 8 "$RUN/$1.log"; return 1; }
    sleep 2; i=$((i + 2))
  done
  echo "  $1 did not answer within $4 s (see $RUN/$1.log)"; return 1
}

launch() {  # name command...
  local name="$1"; shift
  nohup "$@" >"$RUN/$name.log" 2>&1 < /dev/null &
  echo $! > "$RUN/$name.pid"
}

need_big=1;   up big   $BIG_PORT /v1/models && need_big=0
need_small=0; [ -n "$SMALL_MODEL" ] && { up small $SMALL_PORT /v1/models || need_small=1; }
need_gw=1;    up gateway $GW_PORT /v1/models && need_gw=0

if [ $need_big = 0 ] && [ $need_small = 0 ] && [ $need_gw = 0 ]; then
  echo "Assistant is already running."; exit 0
fi

# Another job may have reserved the Mac for experiments.
if [ -f "$OPS/PAUSE_OTHERS" ] && [ $YES = 0 ]; then
  echo "Another job reserved the Mac:"; cat "$OPS/PAUSE_OTHERS"; echo
  printf "Start the assistant anyway? [y/N] "; read -r ans
  case "$ans" in y|Y|yes|YES) ;; *) echo "Not started."; exit 1 ;; esac
fi

[ -x "$PY" ] || { echo "Python not found at $PY (set ASSISTANT_PY)"; exit 1; }

if [ $need_big = 1 ]; then
  alive big && kill "$(cat "$RUN/big.pid")" 2>/dev/null
  echo "Starting big model ($BIG_MODEL) ..."
  launch big "$PY" -m mlx_lm.server --model "$BIG_MODEL" --host 127.0.0.1 --port $BIG_PORT \
    --max-tokens 8192 --prompt-cache-size 16 --prompt-cache-bytes 3GB \
    --temp 0.6 --top-p 0.95 --top-k 20
fi
if [ $need_small = 1 ]; then
  alive small && kill "$(cat "$RUN/small.pid")" 2>/dev/null
  echo "Starting small model ($SMALL_MODEL) ..."
  # SMALL_ARGS is split on spaces on purpose; mlx_lm wants the template text, not a path
  if [ -n "$SMALL_TEMPLATE" ] && [ -f "$SMALL_TEMPLATE" ]; then
    launch small "$PY" -m mlx_lm.server --model "$SMALL_MODEL" --host 127.0.0.1 --port $SMALL_PORT \
      --max-tokens 2048 --prompt-cache-size 8 --prompt-cache-bytes 1GB \
      --temp 0.6 --top-p 0.95 $SMALL_ARGS --chat-template "$(cat "$SMALL_TEMPLATE")"
  else
    launch small "$PY" -m mlx_lm.server --model "$SMALL_MODEL" --host 127.0.0.1 --port $SMALL_PORT \
      --max-tokens 2048 --prompt-cache-size 8 --prompt-cache-bytes 1GB \
      --temp 0.6 --top-p 0.95 $SMALL_ARGS
  fi
fi
if [ $need_gw = 1 ]; then
  alive gateway && kill "$(cat "$RUN/gateway.pid")" 2>/dev/null
  echo "Starting gateway on port $GW_PORT ..."
  launch gateway "$PY" -u "$DIR/gateway.py" --big-url "http://127.0.0.1:$BIG_PORT" \
    --small-url "http://127.0.0.1:$SMALL_PORT" --port $GW_PORT --diary-dir "$OPS/diary"
fi

# Tell experiment jobs that Ben is using the Mac.
write_marker() {
  { echo "started: $(date)"
    for n in big small gateway; do [ -f "$RUN/$n.pid" ] && echo "$n pid: $(cat "$RUN/$n.pid")"; done
  } > "$OPS/ASSISTANT_RUNNING"
}
write_marker

BIG_WAIT=${ASSISTANT_BIG_TIMEOUT:-300}
wait_for gateway $GW_PORT /v1/models 30 || { "$DIR/stop.sh"; exit 1; }
echo "Waiting for the big model to load (up to $BIG_WAIT s) ..."
wait_for big $BIG_PORT /v1/models "$BIG_WAIT" || { "$DIR/stop.sh"; exit 1; }
if [ -n "$SMALL_MODEL" ]; then
  wait_for small $SMALL_PORT /v1/models 120 || echo "  Small helper unavailable; continuing without it."
fi
echo "Assistant is ready: http://127.0.0.1:$GW_PORT/v1"
