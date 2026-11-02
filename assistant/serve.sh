#!/bin/bash
# Start the big model, optional small model, and the gateway. Idempotent.
# Usage: serve.sh [--yes | --autostart]
#   --yes        non-interactive, skips the safety questions.
#   --autostart  non-interactive for the login LaunchAgent, but keeps the safety checks: when
#                PAUSE_OTHERS exists, another model job runs, or memory is short, it logs a line and
#                exits 0 instead of asking.
# Saved settings (e.g. ASSISTANT_SMALL_MODEL) live in ~/learner-ops/assistant/config.sh.
[ -f "$HOME/learner-ops/assistant/config.sh" ] && . "$HOME/learner-ops/assistant/config.sh"
PY="${ASSISTANT_PY:-$HOME/learner-ops/speedbench/venv312/bin/python}"
BIG_MODEL="${ASSISTANT_BIG_MODEL:-mlx-community/Qwen3.6-35B-A3B-4bit}"
SMALL_MODEL="${ASSISTANT_SMALL_MODEL:-}"   # empty = no small server
SMALL_ARGS="${ASSISTANT_SMALL_ARGS:-}"     # e.g. "--trust-remote-code"
SMALL_TEMPLATE="${ASSISTANT_SMALL_TEMPLATE:-}"  # jinja file; K2 needs its no-think template
# Qwen3.6 caches cannot be trimmed, so every turn stores a full entry (~0.3 GB at a 16k OpenCode prefix);
# 1 GB kept only ~3 and evicted the shared system prefix (46 s re-prefill). 3 GB keeps ~10.
BIG_CACHE_SIZE="${ASSISTANT_CACHE_SIZE:-16}"
BIG_CACHE_BYTES="${ASSISTANT_CACHE_BYTES:-3GB}"
# Smaller prefill chunks lower the memory peak of long prompts (2048: 17.1 GB, 512: 16.1 GB on the M1).
BIG_PREFILL_STEP="${ASSISTANT_PREFILL_STEP:-2048}"
# 1 = gateway drops OpenCode's skills listing (~7k tokens) from system prompts; 0 = pass it through.
export ASSISTANT_STRIP_SKILLS="${ASSISTANT_STRIP_SKILLS:-1}"

# 1 = run the big server through mlx_server_persist.py, which saves the warmed system-prefix KV cache
# to disk and reloads it after a restart (untested on the Mac; leave 0 until verified).
PERSIST_CACHE="${ASSISTANT_PERSIST_CACHE:-0}"

# Image reading ("caption then answer"): a small VLM in its own venv (mlx-vlm needs a newer mlx than the
# main venv) describes each image; the gateway pastes the description into the big text-only model's prompt.
# ASSISTANT_VISION: 1/0; default 1 only if the vision venv and model exist (install.sh can create them).
VLM_VENV="${ASSISTANT_VLM_VENV:-$HOME/learner-ops/vlm-venv}"
VLM_MODEL="${ASSISTANT_VLM_MODEL:-$HOME/learner-ops/models/qwen35-2b-vlm}"
VLM_PORT="${ASSISTANT_VLM_PORT:-18082}"
VLM_PY="$VLM_VENV/bin/python"
# Ready = venv python, model config, and mlx_vlm importable (a half-made venv or download doesn't count).
vlm_ready() { [ -x "$VLM_PY" ] && [ -f "$VLM_MODEL/config.json" ] && "$VLM_PY" -c 'import mlx_vlm' >/dev/null 2>&1; }
if [ -z "${ASSISTANT_VISION:-}" ]; then
  if vlm_ready; then ASSISTANT_VISION=1; else ASSISTANT_VISION=0; fi
fi

OPS="$HOME/learner-ops"
RUN="$OPS/assistant/run"
DIR="$(cd "$(dirname "$0")" && pwd)"
BIG_PORT=18080; SMALL_PORT=18081; GW_PORT=8090  # models off 8080/8081, which experiment jobs use
YES=0; AUTO=0
for arg in "$@"; do
  case "$arg" in --yes) YES=1 ;; --autostart) AUTO=1 ;; esac
done
mkdir -p "$RUN" "$OPS/diary"

# One serve.sh at a time. A lock left by a crash or reboot (its pid is gone) is cleared.
take_lock() {
  mkdir "$RUN/serve.lock" 2>/dev/null && { echo $$ > "$RUN/serve.lock/pid"; return 0; }
  local lp; lp="$(cat "$RUN/serve.lock/pid" 2>/dev/null)"
  if [ -n "$lp" ] && ! kill -0 "$lp" 2>/dev/null; then
    rm -rf "$RUN/serve.lock"
    mkdir "$RUN/serve.lock" 2>/dev/null && { echo $$ > "$RUN/serve.lock/pid"; return 0; }
  fi
  return 1
}
if ! take_lock; then
  echo "$(date '+%F %T') another serve.sh is already running; not starting a second one."
  [ $AUTO = 1 ] && exit 0
  exit 1
fi
trap 'rm -rf "$RUN/serve.lock"' EXIT

# Is this pid really our process? (A pid file can outlive a reboot and name an unrelated process.)
ours_re() {  # name -> pattern
  case "$1" in big) echo "mlx_lm|mlx_server_persist" ;; small) echo "mlx_lm" ;; vlm) echo "mlx_vlm" ;;
    gateway) echo "gateway.py" ;; watchdog) echo "watchdog" ;; esac
}
alive()   {  # name: pid file names a live process that is ours
  local pid; pid="$(cat "$RUN/$1.pid" 2>/dev/null)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && ps -p "$pid" -o command= 2>/dev/null | grep -qE "$(ours_re "$1")"
}
answers() { curl -fsS -m 2 "http://127.0.0.1:$1$2" >/dev/null 2>&1; }
up()      { alive "$1" && answers "$2" "$3"; }   # name port path

# Ask a yes/no question; under --autostart log and exit 0 (not an error) instead.
confirm() {  # reason
  if [ $AUTO = 1 ]; then echo "$(date '+%F %T') autostart: not starting ($1)"; exit 0; fi
  printf "%s" "$2"; read -r ans
  case "$ans" in y|Y|yes|YES) ;; *) echo "Not started."; exit 1 ;; esac
}

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
  if [ "$name" = watchdog ]; then   # append: the log must show earlier trips
    nohup "$@" >>"$RUN/$name.log" 2>&1 < /dev/null &
  else
    nohup "$@" >"$RUN/$name.log" 2>&1 < /dev/null &
  fi
  echo $! > "$RUN/$name.pid"
}

# A process that is alive but not answering yet (still loading) is "starting": wait for it below,
# never kill and relaunch it. Only a missing or dead one is launched.
need_big=1;   alive big && need_big=0
need_small=0; [ -n "$SMALL_MODEL" ] && { alive small || need_small=1; }
need_vlm=0;   [ "$ASSISTANT_VISION" = 1 ] && { alive vlm || need_vlm=1; }
need_gw=1;    alive gateway && need_gw=0

if up big $BIG_PORT /v1/models && [ $need_small = 0 ] && [ $need_vlm = 0 ] && [ $need_gw = 0 ] &&
   up gateway $GW_PORT /v1/models &&
   { [ -z "$SMALL_MODEL" ] || up small $SMALL_PORT /v1/models; } &&
   { [ "$ASSISTANT_VISION" != 1 ] || up vlm $VLM_PORT /health; }; then
  echo "Assistant is already running."; exit 0
fi
launching=$((need_big + need_small + need_vlm + need_gw))

# Another job may have reserved the Mac for experiments.
if [ -f "$OPS/PAUSE_OTHERS" ] && [ $YES = 0 ] && [ $launching -gt 0 ]; then
  echo "Another job reserved the Mac:"; cat "$OPS/PAUSE_OTHERS"; echo
  confirm "PAUSE_OTHERS exists" "Start the assistant anyway? [y/N] "
fi

[ -x "$PY" ] || { echo "Python not found at $PY (set ASSISTANT_PY)"; exit 1; }

# Don't stack models: warn if another model job is already loaded.
ours="$(cat "$RUN"/big.pid "$RUN"/small.pid "$RUN"/vlm.pid 2>/dev/null | tr '\n' ' ')"
others=$(ps axo pid=,command= | grep -E "mlx_lm|mlx-lm|llama-server|llama_cpp" | grep -v grep |
  while read -r pid cmd; do case " $ours " in (*" $pid "*) ;; (*) echo "$pid $cmd" ;; esac; done)
if [ -n "$others" ] && [ $need_big = 1 ] && [ $YES = 0 ]; then
  echo "Another model job is running on this Mac:"; echo "$others" | cut -c1-160
  confirm "another model job is running" "Running both can run the Mac out of memory. Start anyway? [y/N] "
fi

# Memory guard: the big model needs ~21 GB. Ben's Mac swapped hard on Oct 25 when two
# big jobs ran at once, so refuse to start unless enough memory can be freed.
if [ $need_big = 1 ] && [ $YES = 0 ] && command -v vm_stat >/dev/null; then
  pg=$(vm_stat | awk '/page size of/ {print $8}')
  avail=$(vm_stat | awk -v pg="$pg" '/Pages (free|inactive|speculative|purgeable)/ {gsub("\\.","",$NF); s+=$NF} END {printf "%d", s*pg/1073741824}')
  need=20; [ $need_small = 1 ] && need=25; [ $need_vlm = 1 ] && need=$((need + 2))
  if [ "$avail" -lt "$need" ]; then
    echo "Only about $avail GB of memory is free; the assistant needs about $need GB."
    confirm "only about $avail GB of memory is free, need about $need" \
      "Quit big apps (or other model jobs) first. Start anyway? [y/N] "
  fi
fi

if [ $need_big = 1 ]; then
  echo "Starting big model ($BIG_MODEL) ..."
  if [ "$PERSIST_CACHE" = 1 ]; then
    BIG_CMD=("$PY" "$DIR/mlx_server_persist.py" --cache-dir "$RUN/kvcache")
  else
    BIG_CMD=("$PY" -m mlx_lm.server)
  fi
  launch big "${BIG_CMD[@]}" --model "$BIG_MODEL" --host 127.0.0.1 --port $BIG_PORT \
    --max-tokens 8192 --prompt-cache-size "$BIG_CACHE_SIZE" --prompt-cache-bytes "$BIG_CACHE_BYTES" \
    --prefill-step-size "$BIG_PREFILL_STEP" \
    --temp 0.6 --top-p 0.95 --top-k 20
fi
if [ $need_small = 1 ]; then
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
if [ $need_vlm = 1 ]; then
  if ! vlm_ready; then
    echo "Image reader not installed ($VLM_VENV / $VLM_MODEL); run install.sh --vision. Continuing without it."
    need_vlm=0; ASSISTANT_VISION=0
  else
    echo "Starting image reader ($VLM_MODEL) on port $VLM_PORT ..."
    # The gateway must send this same --model string, or mlx_vlm.server would try to load another model.
    launch vlm "$VLM_PY" -m mlx_vlm.server --model "$VLM_MODEL" --host 127.0.0.1 --port $VLM_PORT \
      --max-tokens 512
  fi
fi
if [ $need_gw = 1 ]; then
  echo "Starting gateway on port $GW_PORT ..."
  launch gateway "$PY" -u "$DIR/gateway.py" --big-url "http://127.0.0.1:$BIG_PORT" \
    --small-url "http://127.0.0.1:$SMALL_PORT" --port $GW_PORT \
    --vision-url "$([ "$ASSISTANT_VISION" = 1 ] && echo "http://127.0.0.1:$VLM_PORT")" --vision-model "$VLM_MODEL" --diary-dir "$OPS/diary" \
    --prefix-file "$RUN/prefix.json" \
    $([ "$PERSIST_CACHE" = 1 ] && echo --persist-cache)   # prewarms the last chat's system prompt + tools
fi

# Tell experiment jobs that Ben is using the Mac.
write_marker() {
  { echo "started: $(date)"
    for n in big small vlm gateway; do [ -f "$RUN/$n.pid" ] && echo "$n pid: $(cat "$RUN/$n.pid")"; done
  } > "$OPS/ASSISTANT_RUNNING"
}
write_marker

# Memory watchdog (stops everything at critical pressure or sustained warning; see watchdog.sh).
if ! alive watchdog; then
  # Keep a record of earlier trips before clearing the marker.
  if [ -f "$OPS/assistant/WATCHDOG_STOPPED" ]; then
    echo "$(date '+%F %T') $(cat "$OPS/assistant/WATCHDOG_STOPPED")" >> "$RUN/watchdog-history.log"
  fi
  rm -f "$OPS/assistant/WATCHDOG_STOPPED"
  launch watchdog /bin/bash "$DIR/watchdog.sh"
fi

BIG_WAIT=${ASSISTANT_BIG_TIMEOUT:-300}
wait_for gateway $GW_PORT /v1/models 30 || { "$DIR/stop.sh"; exit 1; }
echo "Waiting for the big model to load (up to $BIG_WAIT s) ..."
wait_for big $BIG_PORT /v1/models "$BIG_WAIT" || { "$DIR/stop.sh"; exit 1; }
if [ -n "$SMALL_MODEL" ]; then
  wait_for small $SMALL_PORT /v1/models 120 || echo "  Small helper unavailable; continuing without it."
fi
if [ "$ASSISTANT_VISION" = 1 ]; then
  wait_for vlm $VLM_PORT /health 120 || echo "  Image reader unavailable; images will show as unreadable."
fi
echo "Assistant is ready: http://127.0.0.1:$GW_PORT/v1"
