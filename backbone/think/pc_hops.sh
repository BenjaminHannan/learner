#!/usr/bin/env bash
# PREREG-think2 Addendum G, round 1, on BensPC (WSL Ubuntu, RTX 5070 Ti). Run detached; it waits for its slot by itself.
#   bash pc_hops.sh B SRC OUT   pair B (hplains, hloops) between two race-mini arms: once C: has room, it pauses race-mini's driver
#                               (kill -STOP, never kill: its EXIT trap would hand the GPU on), waits for the running race arm to end, runs
#                               the hops preflight and pair B, then puts GPU-BUSY back, writes handoff/HOPS-B-DONE and resumes the driver.
#   bash pc_hops.sh A SRC OUT   pair A (hplain, hloop) in the GO-LOOP-P1 slot: waits for handoff/GO-LOOP-P1, runs pair B first if it has not
#                               run (race-mini ended before B got its gap), then pair A, then writes DONE_FLAG (default think2-p1/SEG2-DONE,
#                               the sleep chain's flag) and handoff/HOPS-A-DONE.
#   bash pc_hops.sh R SRC OUT   the seed-1 replicate of pair B (Addendum G's next step after a pair B PASS): waits for GO_FLAG and an empty
#                               GPU-BUSY, runs hplains and hloops at SEED (default 1), writes OUT/SUMMARY_hops_s<SEED>.txt, empties GPU-BUSY,
#                               then writes DONE_FLAG (default handoff/HOPS-R-DONE) and, if set, THEN_FLAG (the next job's go flag; a directory
#                               of that name, used to hold the next job back, is removed first). The preflight and data of the first run are reused.
# SRC holds backbone/ (a git archive of the committed branch). OUT is the run root: OUT/data (built here and checked against the committed
# sha256), OUT/runs/<arm>_s<seed>, OUT/pair<X>.log, OUT/<arm>.log (OUT/<arm>_s<seed>.log for seed > 0), OUT/SUMMARY_hops.txt. Every arm already finished is skipped on a rerun.
set -u
PAIR=$1 SRC=$2 OUT=$3
JOBS=${JOBS:-/mnt/c/Users/benja/pc-jobs}  # the overrides are for the CPU dry run in test_hops.py
HAND=$JOBS/handoff
BUSY=${BUSY:-/mnt/c/Users/benja/GPU-BUSY.txt}
CDRIVE=${CDRIVE:-/mnt/c}
RACE_LOG=${RACE_LOG:-$HOME/race-mini/out/job.log}
CARD=$JOBS/hops-$PAIR.md
PY=${PY:-$HOME/bbvenv/bin/python}
MIN_FREE_MB=${MIN_FREE_MB:-3000}
POLL=${POLL:-60}  # seconds between checks
if [ "$PAIR" = R ]; then
  SEED=${SEED:-1}
  GO_FLAG=${GO_FLAG:?pair R needs GO_FLAG, the flag that gives it the GPU}
  DONE_FLAG=${DONE_FLAG:-$HAND/HOPS-R-DONE}
else
  SEED=${SEED:-0}
  DONE_FLAG=${DONE_FLAG:-$JOBS/think2-p1/SEG2-DONE}  # pair A's last flag: it hands the GPU on (handoff/GO-RACE-MINI since 19:35Z Oct 27)
fi
SUF=""; [ "$SEED" = 0 ] || SUF=_s$SEED
mkdir -p "$OUT/runs"
LOG=$OUT/pair$PAIR.log
DRV=""
OWN=0

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
c_free() { df -Pm "$CDRIVE" | awk 'NR == 2 {print $4}'; }

DRIVER_RE='^(/usr/bin/|/bin/)?bash [^ ]*pc_race_mini\.sh( |$)'
find_driver() {  # prints race-mini's driver PID (nothing if none runs); fails if the match is ambiguous or not a driver. DRIVER_PID, if given,
  # is checked the same way. Anchored: a plain pgrep -f also matches any shell whose command line merely mentions pc_race_mini.sh.
  local pids
  pids=${DRIVER_PID:-$(pgrep -f "$DRIVER_RE")}
  [ -z "$pids" ] && return 0
  if [ "$(echo "$pids" | wc -w)" != 1 ]; then echo "more than one match: $pids" >&2; return 4; fi
  tr '\0' ' ' < "/proc/$pids/cmdline" 2>/dev/null | grep -Eq "$DRIVER_RE" || { echo "PID $pids is not a pc_race_mini.sh driver" >&2; return 4; }
  echo "$pids"
}

live_children() {  # live (not zombie) descendants of $1: the race arm it started, and anything that arm started
  ps -e -o pid=,ppid=,stat= | awk -v root="$1" '{pid[NR] = $1; par[NR] = $2; st[NR] = $3}
    END {keep[root] = 1; more = 1
         while (more) {more = 0; for (i = 1; i <= NR; i++) if ((par[i] in keep) && !(pid[i] in keep)) {keep[pid[i]] = 1; more = 1}}
         n = 0; for (i = 1; i <= NR; i++) if ((pid[i] in keep) && pid[i] != root && st[i] !~ /^Z/) n++
         print n}'
}

wait_room() {
  while [ "$(c_free)" -lt "$MIN_FREE_MB" ]; do
    log "waiting: C: has $(c_free) MB free, need $MIN_FREE_MB (the WSL disk file lives on C:)"
    sleep $((POLL * 5))
  done
}

data() {
  local want=$SRC/backbone/results/hops/HOPS_REPORT.json
  if [ ! -f "$OUT/data/HOPS_REPORT.json" ]; then
    log "building the hops data"
    (cd "$SRC" && "$PY" backbone/think/build_hops.py "$OUT/data") > "$OUT/build.log" 2>&1 || { log "build_hops failed"; return 1; }
  fi
  "$PY" - "$OUT/data/HOPS_REPORT.json" "$want" <<'EOF' || { log "data sha256 differs from the committed HOPS_REPORT.json: not running"; return 1; }
import json, sys
a, b = (json.load(open(p))["files"] for p in sys.argv[1:])
sys.exit(0 if {k: v["sha256"] for k, v in a.items()} == {k: v["sha256"] for k, v in b.items()} else 1)
EOF
  log "data ok (sha256 matches the committed report)"
}

take_gpu() {
  OWN=1
  echo "hops pair $PAIR seed $SEED (loop thread, Addendum G) since $(date -u +%FT%TZ)" > "$BUSY"
  printf 'job: hops pair %s seed %s (PREREG-think2 Addendum G)\nthread: Make the thinking block pay off\nlog: %s\nstarted: %s\n' "$PAIR" "$SEED" "$LOG" "$(date -u +%FT%TZ)" > "$CARD"
}

release_gpu() {  # before any flag that hands the GPU on, so the next owner's GPU-BUSY line is never wiped
  if [ "$OWN" = 1 ]; then
    if [ "$PAIR" = B ] && [ -n "$DRV" ]; then
      echo "race-mini (sleep race, both sides) resumed $(date -u +%FT%TZ)" > "$BUSY"
    else
      : > "$BUSY"
    fi
    rm -f "$CARD"
    if [ "$PAIR" = B ]; then echo "$1 $(date -u +%FT%TZ)" > "$HAND/HOPS-B-DONE"; fi
  fi
  OWN=0
}

finish() {
  local rc=$?
  release_gpu "$rc"
  if [ "$PAIR" = B ] && [ -n "$DRV" ] && kill -0 "$DRV" 2>/dev/null; then kill -CONT "$DRV"; log "race-mini driver $DRV resumed"; fi
  log "exit $rc"
}

run_arm() {
  local arm=$1 res=$OUT/runs/${1}_s$SEED/result_${1}_s$SEED.json
  if [ -f "$res" ]; then log "$arm seed $SEED already done"; return 0; fi
  log "start $arm seed $SEED"
  (cd "$SRC" && "$PY" backbone/think/think1.py --arm "$arm" --seed "$SEED" --data "$OUT/data" --out "$OUT/runs/${arm}_s$SEED" --micro-bsz 8) >> "$OUT/$arm$SUF.log" 2>&1
  local rc=$?
  log "end $arm rc=$rc"
  return $rc
}

pair_b() {
  if [ ! -f "$OUT/preflight/preflight.json" ]; then
    log "preflight (hloops at 6 loops on every row, then hplains)"
    (cd "$SRC" && "$PY" backbone/think/preflight.py --arms hloops,hplains --data "$OUT/data" --out "$OUT/preflight" --micro-bsz 8) >> "$OUT/preflight.log" 2>&1 \
      || { log "PREFLIGHT FAILED: see $OUT/preflight.log"; return 1; }
    log "$(grep 'PREFLIGHT OK' "$OUT/preflight.log" | tail -1)"
  fi
  run_arm hplains && run_arm hloops
}

summarize() {
  (cd "$SRC" && "$PY" backbone/think/summarize_hops.py "$OUT/runs" --data "$OUT/data" --seed "$SEED") > "$OUT/SUMMARY_hops$SUF.txt" 2>&1
  log "summary: $(grep -E 'OUTCOME' "$OUT/SUMMARY_hops$SUF.txt" | tr '\n' ' ')"
}

trap finish EXIT
trap 'exit 143' TERM INT
log "pc_hops.sh $PAIR start (src $SRC)"
wait_room  # before the 202 MB data build: the WSL disk file grows on C:
data || exit 1

if [ "$PAIR" = B ]; then
  while true; do
    wait_room
    DRV=$(find_driver 2>> "$LOG") || { DRV=""; log "race-mini's driver could not be identified safely: not touching race-mini"; exit 4; }
    if [ -z "$DRV" ]; then
      log "race-mini's driver is not running: pair B moves to the GO-LOOP-P1 slot (pc_hops.sh A runs it first)"
      exit 3
    fi
    kill -STOP "$DRV"
    log "race-mini driver $DRV paused; waiting for its running arm to end"
    while [ "$(live_children "$DRV")" -gt 0 ]; do sleep "$POLL"; done
    if [ "$(c_free)" -ge "$MIN_FREE_MB" ]; then break; fi
    kill -CONT "$DRV"
    log "C: fell below $MIN_FREE_MB MB again; race-mini resumed, trying again at its next arm"
    DRV=""
    sleep $((POLL * 10))
  done
  log "race-mini's arm ended; the GPU is ours (tail of its job.log follows)"
  tail -5 "$RACE_LOG" >> "$LOG" 2>/dev/null
  take_gpu
  pair_b
  rc=$?
  summarize
  exit $rc
fi

if [ "$PAIR" = A ]; then
  log "waiting for $HAND/GO-LOOP-P1"
  while [ ! -f "$HAND/GO-LOOP-P1" ]; do sleep "$POLL"; done
  wait_room
  take_gpu
  if [ ! -f "$OUT/runs/hloops_s$SEED/result_hloops_s$SEED.json" ]; then pair_b; fi
  run_arm hplain && run_arm hloop
  rc=$?
  summarize
  release_gpu "$rc"
  mkdir -p "$(dirname "$DONE_FLAG")"
  # The flag hands the GPU on (to race-mini, whose bridge then writes SEG2-DONE; SEG2-DONE gates the later think2 segments on their own
  # code's preflight). A hops failure says nothing about that code, so the flag always reads 0; the hops exit code goes after it.
  echo "0 $(date -u +%FT%TZ) hops pair A rc=$rc" > "$DONE_FLAG"
  echo "$rc $(date -u +%FT%TZ)" > "$HAND/HOPS-A-DONE"
  exit $rc
fi
if [ "$PAIR" = R ]; then
  log "waiting for $GO_FLAG and an empty GPU-BUSY"
  until [ -f "$GO_FLAG" ] && [ ! -s "$BUSY" ]; do sleep "$POLL"; done
  wait_room
  take_gpu
  pair_b
  rc=$?
  summarize
  release_gpu "$rc"
  mkdir -p "$(dirname "$DONE_FLAG")"
  echo "0 $(date -u +%FT%TZ) hops replicate seed $SEED rc=$rc" > "$DONE_FLAG"  # as in pair A: the flags hand the GPU on whatever happened
  if [ -n "${THEN_FLAG:-}" ]; then
    [ -d "$THEN_FLAG" ] && rmdir "$THEN_FLAG"
    echo "go $(date -u +%FT%TZ) after hops replicate seed $SEED" > "$THEN_FLAG"
    log "wrote $THEN_FLAG"
  fi
  exit $rc
fi
log "unknown pair $PAIR (use A, B or R)"
exit 2
