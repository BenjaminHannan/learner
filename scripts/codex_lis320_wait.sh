#!/bin/bash
# The background shell checks outbox every ten minutes; no model polling.
set -u
ROOT=$1
STATE=$2
cd "$ROOT" || exit 20
mkdir -p "$STATE"
mkdir "$STATE/loop.lock" 2>/dev/null || exit 21
echo $$ > "$STATE/loop.lock/pid"
trap 'rm -f "$STATE/loop.lock/pid"; rmdir "$STATE/loop.lock"' EXIT
while :; do
  python3 -B scripts/codex_lis320_continue.py --state "$STATE"
  rc=$?
  [ "$rc" = 0 ] || exit "$rc"
  sleep 600
done
