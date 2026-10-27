#!/bin/bash
# Start the Premonition chat-demo server. Exits 0 once GET / answers.
# If a server is already answering on the port, does nothing.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHAT="$HOME/premonition-chat"
LOG="$CHAT/server.log"
mkdir -p "$CHAT"

answers() {
  curl -s -o /dev/null -m 2 "http://127.0.0.1:$1/" 2>/dev/null
}

if answers 8765 || answers 8766; then
  exit 0
fi

# A previous server process may be starting; give it a moment, re-check.
pkill -f claude_chatdemo_server.py 2>/dev/null || true
sleep 1
if answers 8765 || answers 8766; then
  exit 0
fi

cd "$ROOT"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
nohup uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/claude_chatdemo_server.py >>"$LOG" 2>&1 &
echo "chatdemo starting, logging to $LOG"

for i in $(seq 1 240); do
  if answers 8765 || answers 8766; then
    exit 0
  fi
  sleep 2
done
echo "chatdemo did not answer within timeout; see $LOG" >&2
exit 1
