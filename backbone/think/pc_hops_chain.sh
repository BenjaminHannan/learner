#!/usr/bin/env bash
# The hops steps that follow race-mini in the PC order of Oct 28 (coordinator): pair A's seed-1 replicate, the fresh rows scored once for every mark that
# earned them, and round-2 hloopd. pc_race_bridge.sh runs this as its THEN_CMD, so SEG2-DONE (which releases the sleep chain) is written only after it ends:
#   THEN_CMD="bash SRC/backbone/think/pc_hops_chain.sh SRC OUT" bash pc_race_bridge.sh        (it can also be run by hand)
# SRC and OUT are the ones pc_hops.sh was given. Each step is a foreground `bash SRC/backbone/think/pc_hops.sh` with GO_FLAG=handoff/HOPS-CHAIN-GO (this
# script's own flag, written first: each step still waits for an empty GPU-BUSY), an explicit HOPS_NAME and the DONE_FLAG default for it. In order:
#   a  R  HOPS_ARMS="hplain hloop" SEED=1, HOPS_NAME=pairA_s1           pair A's seed-1 replicate (always)
#   b  F  fresh rows, one run per group, in this order, each only if its mark is there (summarize_hops.py OUT/runs --data OUT/data --seed S --json):
#        pairB   HOPS_ARMS="hplains hloops" HOPS_SEEDS="0 1"   if B key == PASS at seed 0 and at seed 1
#        pairA   HOPS_ARMS="hplain hloop"   HOPS_SEEDS="0 1"   if A key == REPLICATES at seed 1
#        hloopi  HOPS_ARMS="hloopi hplain"  HOPS_SEEDS="0"     if R2.hloopi works or stops_itself at seed 0
#   c  if pair B passed (seed 0 and seed 1, as for pairB): R HOPS_ARMS=hloopd SEED=0, HOPS_NAME=round2_hloopd; then, if R2.hloopd works or stops_itself at
#      seed 0 and the hloopd run exited 0: F HOPS_ARMS="hloopd hplains" HOPS_SEEDS="0", HOPS_NAME=hloopd
# A group whose mark cannot be read (the summary fails, is not JSON, or lacks the key) is skipped and logged, never guessed. A failing step does not stop the
# later ones (hloopd's fresh group needs hloopd's own run to have succeeded). Every decision and step goes to OUT/chain.log. At the end handoff/HOPS-CHAIN-DONE
# is written ("0 <utc> ..." and one line of what ran, each rc, and what was skipped); the exit code is 0 if every step that ran exited 0, else 1.
# The env of the caller (JOBS, BUSY, POLL, MIN_FREE_MB, PY, CDRIVE ...) goes through to pc_hops.sh; its own job variables are cleared first.
#   bash pc_hops_chain.sh SRC OUT
set -u
[ $# -eq 2 ] || { echo "usage: bash pc_hops_chain.sh SRC OUT" >&2; exit 2; }
SRC=$1 OUT=$2
unset GO_FLAG DONE_FLAG THEN_FLAG HOPS_ARMS HOPS_SEEDS HOPS_NAME SEED  # a leftover from the shell or from the bridge must not steer a step
JOBS=${JOBS:-/mnt/c/Users/benja/pc-jobs}
PY=${PY:-$HOME/bbvenv/bin/python}
export JOBS PY  # the same values for the steps (pc_hops.sh has the same defaults)
HAND=$JOBS/handoff
GO=$HAND/HOPS-CHAIN-GO
HOPS=$SRC/backbone/think/pc_hops.sh
mkdir -p "$OUT" "$HAND"
LOG=$OUT/chain.log
RAN=""      # "label rc=N; ..."
SKIPPED=""  # "label (reason); ..."
FAILED=0
BPASS=""    # yes / no / unreadable, read once: nothing the chain runs changes pair B's results

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
oneline() { echo "$*" | tr '\n\t' '  '; }

decide() {  # decide SEED WHAT: prints "yes|no|unreadable REASON". WHAT: B (key PASS), A (key REPLICATES), R2:ARM (works or stops_itself)
  local seed=$1 what=$2 js rc
  js=$(cd "$SRC" && "$PY" backbone/think/summarize_hops.py "$OUT/runs" --data "$OUT/data" --seed "$seed" --json 2> "$OUT/chain_summary_s$seed.err")
  rc=$?
  if [ $rc -ne 0 ]; then echo "unreadable summarize_hops.py --seed $seed --json exited $rc: $(oneline "$(tail -n 1 "$OUT/chain_summary_s$seed.err" 2>/dev/null)")"; return 0; fi
  printf '%s' "$js" | "$PY" -c '
import json, sys
what, seed = sys.argv[1], sys.argv[2]
try:
    o = json.load(sys.stdin)
    if what == "B":
        k = o["B"]["key"]
        print("yes" if k == "PASS" else "no", f"pair B key {k} at seed {seed}")
    elif what == "A":
        k = o["A"]["key"]
        print("yes" if k == "REPLICATES" else "no", f"pair A key {k} at seed {seed}")
    elif what.startswith("R2:"):
        r = o["R2"][what[3:]]
        w, s = bool(r["works"]), bool(r["stops_itself"])
        print("yes" if (w or s) else "no", f"{what[3:]} works={w} stops_itself={s} at seed {seed}")
    else:
        raise KeyError(what)
except Exception as e:
    print("unreadable", f"seed {seed} summary has no {what} mark ({type(e).__name__}: {e})")
' "$what" "$seed" 2> /dev/null || echo "unreadable the decision reader failed on the seed $seed summary"
}

b_passed() {  # sets BPASS and BWHY: pair B's PASS at seed 0 and at seed 1; any "no" wins over an unreadable one
  [ -n "$BPASS" ] && return 0
  local v0 w0 v1 w1
  read -r v0 w0 <<< "$(decide 0 B)"
  read -r v1 w1 <<< "$(decide 1 B)"
  if [ "$v0" = no ] || [ "$v1" = no ]; then BPASS=no
  elif [ "$v0" = yes ] && [ "$v1" = yes ]; then BPASS=yes
  else BPASS=unreadable; fi
  BWHY="seed 0: $v0, $w0; seed 1: $v1, $w1"
}

step() {  # step LABEL MODE NAME [VAR=value ...]: one foreground pc_hops.sh; its code is recorded, never fatal
  local label=$1 mode=$2 name=$3 rc
  shift 3
  log "run $label: pc_hops.sh $mode with HOPS_NAME=$name $*"
  env GO_FLAG="$GO" HOPS_NAME="$name" "$@" bash "$HOPS" "$mode" "$SRC" "$OUT"
  rc=$?
  log "end $label rc=$rc"
  RAN="$RAN$label rc=$rc; "
  [ $rc -eq 0 ] || FAILED=1
  return $rc
}

skip() { log "skip $1: $2"; SKIPPED="$SKIPPED$1 ($(oneline "$2")); "; }

# the fresh group for one decision: gate "yes" runs it, "no" and "unreadable" skip it with the reason
group() {  # group LABEL NAME ARMS SEEDS VERDICT REASON
  local label=$1 name=$2 arms=$3 seeds=$4 verdict=$5 reason=$6
  log "decision $label: $verdict ($reason)"
  case $verdict in
    yes) step "$label" F "$name" HOPS_ARMS="$arms" HOPS_SEEDS="$seeds" ;;
    no) skip "$label" "mark not met: $reason" ;;
    *) skip "$label" "mark not readable, not guessed: $reason" ;;
  esac
}

rm -f "$HAND/HOPS-CHAIN-DONE"
echo "go $(date -u +%FT%TZ) hops chain for $OUT" > "$GO"
log "pc_hops_chain.sh start (src $SRC, out $OUT, go flag $GO)"

# a. pair A's seed-1 replicate
step "R pairA_s1" R pairA_s1 HOPS_ARMS="hplain hloop" SEED=1

# b. the fresh rows, one run per group
b_passed
group "F pairB" pairB "hplains hloops" "0 1" "$BPASS" "$BWHY"
read -r v w <<< "$(decide 1 A)"
group "F pairA" pairA "hplain hloop" "0 1" "$v" "$w"
read -r v w <<< "$(decide 0 R2:hloopi)"
group "F hloopi" hloopi "hloopi hplain" "0" "$v" "$w"

# c. round-2 hloopd, only after a pair B PASS at both seeds
log "decision R round2_hloopd: $BPASS ($BWHY)"
if [ "$BPASS" = yes ]; then
  if step "R round2_hloopd" R round2_hloopd HOPS_ARMS=hloopd SEED=0; then
    read -r v w <<< "$(decide 0 R2:hloopd)"
    group "F hloopd" hloopd "hloopd hplains" "0" "$v" "$w"
  else
    skip "F hloopd" "the hloopd run did not exit 0, so there is nothing sound to score"
  fi
else
  if [ "$BPASS" = no ]; then skip "R round2_hloopd" "pair B did not pass at seed 0 and seed 1: $BWHY"
  else skip "R round2_hloopd" "pair B's marks not readable, not guessed: $BWHY"; fi
  skip "F hloopd" "hloopd did not run"
fi

rc=$FAILED
log "chain end: ran: ${RAN:-nothing; }skipped: ${SKIPPED:-nothing}; exit $rc"
echo "0 $(date -u +%FT%TZ) hops chain done; ran: ${RAN:-nothing; }skipped: ${SKIPPED:-nothing}; exit $rc" > "$HAND/HOPS-CHAIN-DONE"
log "wrote $HAND/HOPS-CHAIN-DONE"
exit $rc
