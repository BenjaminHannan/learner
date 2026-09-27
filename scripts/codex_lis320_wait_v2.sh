#!/bin/bash
# Same ten-minute loop; uses uv's native Python (Mac /usr/local/bin/python3 is x86).
set -u
ROOT=$1
STATE=$2
UV=$(command -v uv || echo "$HOME/.local/bin/uv")
LIS_PY=$("$UV" python find 3.12) || exit 20
[ -x "$LIS_PY" ] || exit 20
cd "$ROOT" || exit 20
mkdir -p "$STATE"
mkdir "$STATE/loop.lock" 2>/dev/null || exit 21
echo $$ > "$STATE/loop.lock/pid"
trap 'rm -f "$STATE/loop.lock/pid"; rmdir "$STATE/loop.lock"' EXIT
while :; do
  "$LIS_PY" -B scripts/codex_lis320_continue.py --state "$STATE"
  rc=$?
  [ "$rc" = 0 ] || exit "$rc"
  sleep 600
done
