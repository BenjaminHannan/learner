#!/bin/zsh
parent=$1
while kill -0 "$parent" 2>/dev/null; do
  idle=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
  if [[ -z "$idle" || $idle -lt 300 ]]; then
    kill -TERM "$parent" 2>/dev/null
    exit 0
  fi
  sleep 2
done
