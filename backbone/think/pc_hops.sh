#!/usr/bin/env bash
# PREREG-think2 Addendum G, round 1, on BensPC (WSL Ubuntu, RTX 5070 Ti). Run detached; it waits for its slot by itself.
#   bash pc_hops.sh B SRC OUT   pair B (hplains, hloops) between two race-mini arms: once C: has room, it pauses race-mini's driver
#                               (kill -STOP, never kill: its EXIT trap would hand the GPU on), waits for the running race arm to end, runs
#                               the hops preflight and pair B, then puts GPU-BUSY back, writes handoff/HOPS-B-DONE and resumes the driver.
#   bash pc_hops.sh A SRC OUT   pair A (hplain, hloop) in the GO-LOOP-P1 slot: waits for handoff/GO-LOOP-P1, runs pair B first if it has not
#                               run (race-mini ended before B got its gap), then pair A, then writes DONE_FLAG (default think2-p1/SEG2-DONE,
#                               the sleep chain's flag) and handoff/HOPS-A-DONE.
#   bash pc_hops.sh R SRC OUT   a later run of hops arms (the seed-1 replicate of pair B, Addendum G's next step after a pair B PASS; Addendum I's
#                               round-2 arms and pair A's seed-1 replicate): waits for GO_FLAG and an empty GPU-BUSY, runs HOPS_ARMS (env,
#                               space-separated, in order, stopping at the first failure; default "hplains hloops" = pair B with its preflight, as before)
#                               at SEED (default 1), writes OUT/SUMMARY_$HOPS_NAME.txt, empties GPU-BUSY, then writes DONE_FLAG and, if set,
#                               THEN_FLAG (the next job's go flag). THEN_FLAG may be an EMPTY DIRECTORY, or a directory holding one file named exactly
#                               HOLD, put there to hold the next job back (its waiter wants a file): hand_on removes HOLD (only that name, never rm -rf)
#                               and the directory, then writes the flag. If anything else is inside, the directory and HOLD are left alone, the log
#                               says "could not write THEN_FLAG ..." and the next job stays held back. The preflight and data of the first run are reused.
#                               Names (the env names are all HOPS_*: a bare NAME or ARMS may already be set by the shell, WSL sets NAME to the Windows
#                               computer name): HOPS_NAME defaults to hops<_s SEED if SEED > 0> for the default pair, so the committed SUMMARY_hops.txt and
#                               SUMMARY_hops_s1.txt are only ever written by the default pair, and to hops_<arms joined by ->< _s SEED> for any other
#                               arms, so a different run never overwrites them. DONE_FLAG defaults to handoff/HOPS-R-DONE for the default pair with no
#                               HOPS_NAME, else to handoff/HOPS-R-<HOPS_NAME>-DONE: a later job gated on a flag never finds an earlier run's. Examples:
#                                 HOPS_ARMS=hloopi SEED=0 HOPS_NAME=round2_hloopi      HOPS_ARMS="hplain hloop" SEED=1 HOPS_NAME=pairA_s1
#   bash pc_hops.sh F SRC OUT   the fresh rows, scored once (Addendum I, item 4): the same wait as R, then fresh_hops.py on HOPS_ARMS (default "hplains
#                               hloops") and HOPS_SEEDS (env, space-separated numbers, default "0 1"; anything else exits 2 at launch) from OUT/runs into
#                               OUT/fresh, then OUT/SUMMARY_fresh_<HOPS_NAME, default hops for the default pair, else hops_<arms joined by ->>_s<seed>.txt
#                               per seed (summarize_hops.py --split fresh --validation OUT/runs: each mark is held against its validation read), empties
#                               GPU-BUSY, then DONE_FLAG (default handoff/HOPS-F-DONE, else handoff/HOPS-F-<HOPS_NAME>-DONE, as in R) and THEN_FLAG as in R.
# SRC holds backbone/ (a git archive of the committed branch). OUT is the run root: OUT/data (built here and checked against the committed
# sha256), OUT/runs/<arm>_s<seed>, OUT/pair<X>.log, OUT/<arm>.log (OUT/<arm>_s<seed>.log for seed > 0), OUT/fresh.log, OUT/fresh/<arm>_s<seed>,
# OUT/SUMMARY_hops.txt. Every arm already finished is skipped on a rerun.
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
if [ "$PAIR" = R ] || [ "$PAIR" = F ]; then
  SEED=${SEED:-1}
  GO_FLAG=${GO_FLAG:?pair $PAIR needs GO_FLAG, the flag that gives it the GPU}
  ARMS=${HOPS_ARMS:-hplains hloops}
  for arm in $ARMS; do
    case $arm in hplain|hloop|hloopi|hloopd|hplains|hloops) ;; *) echo "pc_hops.sh $PAIR: $arm is not a hops arm (hplain hloop hloopi hloopd hplains hloops)" >&2; exit 2 ;; esac
  done
  ARMS=$(echo $ARMS)  # one space between arms, whatever HOPS_ARMS was separated with; the comma list for fresh_hops.py is built from these words
  [ -n "$ARMS" ] || { echo "pc_hops.sh $PAIR: HOPS_ARMS names no arm" >&2; exit 2; }
else
  SEED=${SEED:-0}
  DONE_FLAG=${DONE_FLAG:-$JOBS/think2-p1/SEG2-DONE}  # pair A's last flag: it hands the GPU on (handoff/GO-RACE-MINI since 19:35Z Oct 27)
fi
SUF=""; [ "$SEED" = 0 ] || SUF=_s$SEED
TAG=hops  # the default pair (hplains hloops) keeps the committed names; any other arms get their own, so they never overwrite those
if [ "$PAIR" = R ] || [ "$PAIR" = F ]; then [ "$ARMS" = "hplains hloops" ] || TAG=hops_${ARMS// /-}; fi
case $PAIR in R) NAME=${HOPS_NAME:-$TAG$SUF} ;; F) NAME=${HOPS_NAME:-$TAG} ;; *) NAME=hops$SUF ;; esac  # R: OUT/SUMMARY_$NAME.txt, F: OUT/SUMMARY_fresh_${NAME}_s<seed>.txt; A and B keep the committed names
if [ "$PAIR" = R ] || [ "$PAIR" = F ]; then
  if [ -n "${HOPS_NAME:-}" ] || [ "$TAG" != hops ]; then DONE_FLAG=${DONE_FLAG:-$HAND/HOPS-$PAIR-$NAME-DONE}; else DONE_FLAG=${DONE_FLAG:-$HAND/HOPS-$PAIR-DONE}; fi  # per run, so an earlier run's flag never opens a later gate
fi
if [ "$PAIR" = F ]; then  # F scores several seeds; SEED then only labels GPU-BUSY and the logs
  SEEDS=${HOPS_SEEDS:-0 1}
  for s in $SEEDS; do
    case $s in *[!0-9]*) echo "pc_hops.sh F: seed '$s' in HOPS_SEEDS is not a number (space-separated, e.g. \"0 1\"; a comma list is fresh_hops.py's own syntax)" >&2; exit 2 ;; esac
  done
  SEEDS=$(echo $SEEDS)
  [ -n "$SEEDS" ] || { echo "pc_hops.sh F: HOPS_SEEDS names no seed" >&2; exit 2; }
  SEED=$SEEDS
fi
csv() { local IFS=,; echo "$*"; }  # csv a b c -> a,b,c: the words are split before the call, so a tab or a newline in the env never glues two names together
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
    log "released GPU-BUSY (rc $1)"
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

run_arms() {  # R: ARMS in order, stopping at the first failure; the default pair is pair B with its preflight, exactly as before
  if [ "$ARMS" = "hplains hloops" ]; then pair_b; return $?; fi
  local a
  for a in $ARMS; do run_arm "$a" || return $?; done
}

summarize() {
  (cd "$SRC" && "$PY" backbone/think/summarize_hops.py "$OUT/runs" --data "$OUT/data" --seed "$SEED") > "$OUT/SUMMARY_$NAME.txt" 2>&1
  log "summary: $(grep -E 'OUTCOME' "$OUT/SUMMARY_$NAME.txt" | tr '\n' ' ')"
}

fresh() {  # F: fresh_hops.py checks fresh.jsonl against the committed sha256 itself; the summaries are written for whatever it scored, even if an arm failed;
  # each is held against the validation read in OUT/runs (a mark that passed there and fails on fresh rows "did not hold")
  local rc s
  log "start fresh rows: arms $ARMS, seeds $SEEDS"
  (cd "$SRC" && "$PY" backbone/think/fresh_hops.py "$OUT/runs" --data "$OUT/data" --out "$OUT/fresh" --arms "$(csv $ARMS)" --seeds "$(csv $SEEDS)") >> "$OUT/fresh.log" 2>&1
  rc=$?
  log "end fresh rc=$rc"
  if [ -d "$OUT/fresh" ]; then
    for s in $SEEDS; do
      (cd "$SRC" && "$PY" backbone/think/summarize_hops.py "$OUT/fresh" --data "$OUT/data" --split fresh --validation "$OUT/runs" --seed "$s") > "$OUT/SUMMARY_fresh_${NAME}_s$s.txt" 2>&1
      log "fresh summary seed $s: $(grep -E 'OUTCOME' "$OUT/SUMMARY_fresh_${NAME}_s$s.txt" | tr '\n' ' ')"
    done
  fi
  return $rc
}

hand_on() {  # R and F, after release_gpu: the flags hand the GPU on whatever happened, the exit code ($1) is recorded after a leading 0; $2 says what ran
  mkdir -p "$(dirname "$DONE_FLAG")"
  echo "0 $(date -u +%FT%TZ) $2 rc=$1" > "$DONE_FLAG"  # as in pair A: the flags hand the GPU on whatever happened
  log "wrote $DONE_FLAG"
  if [ -n "${THEN_FLAG:-}" ]; then
    if [ -d "$THEN_FLAG" ]; then  # a directory of that name holds the next job back: it may contain one file named exactly HOLD, nothing else is ever removed
      if [ -z "$(find "$THEN_FLAG" -mindepth 1 -maxdepth 1 ! -name HOLD 2>/dev/null)" ]; then
        [ -f "$THEN_FLAG/HOLD" ] && rm -f "$THEN_FLAG/HOLD"
        rmdir "$THEN_FLAG"
      fi
      if [ -d "$THEN_FLAG" ]; then
        log "could not write THEN_FLAG $THEN_FLAG: it is a directory that cannot be removed (inside: $(ls -A "$THEN_FLAG" | tr '\n' ' ')); the next job stays held back"
        return 0
      fi
    fi
    if echo "go $(date -u +%FT%TZ) after $2" > "$THEN_FLAG"; then log "wrote $THEN_FLAG"; else log "could not write THEN_FLAG $THEN_FLAG (the write failed); the next job is not released"; fi
  fi
  return 0
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
  run_arms
  rc=$?
  summarize
  release_gpu "$rc"
  hand_on "$rc" "hops replicate seed $SEED"
  exit $rc
fi
if [ "$PAIR" = F ]; then
  log "waiting for $GO_FLAG and an empty GPU-BUSY"
  until [ -f "$GO_FLAG" ] && [ ! -s "$BUSY" ]; do sleep "$POLL"; done
  wait_room
  take_gpu
  fresh
  rc=$?
  release_gpu "$rc"
  hand_on "$rc" "hops fresh rows seeds $SEEDS"
  exit $rc
fi
log "unknown pair $PAIR (use A, B, R or F)"
exit 2
