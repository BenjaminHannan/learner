#!/bin/sh
# lis-311 server starter (new file only). Starts scripts/claude_lis311_server.py
# in the background with nohup; log in ~/premonition-chat/lis311-server.log.
# Own state dir ~/premonition-chat/lis311-state. Never touches 8765/8766.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
LOG="$HOME/premonition-chat/lis311-server.log"
mkdir -p "$HOME/premonition-chat"
cd "$ROOT" || exit 1
if [ -f "$HOME/premonition-chat/lis311-port.txt" ] && \
   curl -s -m 3 http://127.0.0.1:8767/ready 2>/dev/null | grep -q '"ready": true'; then
  echo "lis311 already serving on 8767"
  exit 0
fi
nohup uv run --offline --no-project --python 3.12 --with torch --with numpy \
  --with transformers --with safetensors python -B scripts/claude_lis311_server.py \
  >>"$LOG" 2>&1 &
echo "lis311 starting (pid $!), log $LOG"
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 10
  if curl -s -m 5 http://127.0.0.1:8767/ready 2>/dev/null | grep -q '"ready": true'; then
    echo "lis311 ready on 8767"
    exit 0
  fi
done
echo "lis311 not ready yet; see $LOG"
exit 1
