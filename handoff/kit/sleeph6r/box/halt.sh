#!/bin/bash
# Runs ON the rental (kit sleeph6r, 2026-09-28). Usage: halt.sh <REASON-without-spaces>.
# Stops drive.sh, the seed runs and the GPU-memory monitor by the EXACT pids drive.sh wrote to W/pids.txt (`kind name pid` lines,
# drive.sh first so it cannot write DIED lines afterwards), so that nothing writes while the Mac guard copies the files back.
# TERM first, KILL after 5 s for any still alive (a zombie counts as gone). Then it appends one HALT line to W/drive-state.txt.
# It kills nothing else.
cd /root/r 2>/dev/null || { echo "halt: no /root/r, nothing to stop"; exit 0; }
[ -f W/pids.txt ] || { echo "halt: no W/pids.txt, nothing to stop"; exit 0; }
alive() { [ -r "/proc/$1/status" ] && ! grep -q '^State:[[:space:]]*Z' "/proc/$1/status"; }
n=0
while read -r kind name pid; do [ -n "${pid:-}" ] && kill "$pid" 2>/dev/null && n=$((n+1)); done < W/pids.txt
sleep 5
k=0
while read -r kind name pid; do [ -n "${pid:-}" ] && alive "$pid" && { kill -9 "$pid" 2>/dev/null; k=$((k+1)); }; done < W/pids.txt
sleep 2
left=0
while read -r kind name pid; do [ -n "${pid:-}" ] && alive "$pid" && left=$((left+1)); done < W/pids.txt
echo "$(date -u +%FT%TZ) HALT ${1:-?} (TERM to $n pids, $k needed KILL, $left still alive)" >> W/drive-state.txt
echo "halt: TERM to $n pids, $k needed KILL, $left still alive"
