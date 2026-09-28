#!/bin/bash
# dir-h6 vast collect (kit sleeph6r, 2026-09-28; pattern of the sleep358n3r collect). Run on the Mac by the BASH-ONLY jobs
# handoff/queue/h7-dirh6-2-collect.md and -3-collect.md. Restarts the Mac guard if it died before ending, waits up to 70 min for it
# to end, then puts the copied-back files in the repo: $A/runs/<R>/ (dirh6-seed<S>.json, <R>.log, <R>.err) and the rental's records
# (progress file, torch record, seal and check outputs, smoke output, day sizes, GPU memory log, file manifest, rental list, the
# guard's log) in $A/run-vast/, and writes $A/run-vast/COLLECT.txt. It never touches the rental, never pushes weights (there are
# none) and prints NO test score: only whether each result file exists, how many nights each arm finished, and the integrity
# fields (torch, GPU, minutes, learning rates, plan flags). The blind recount step reads the counts.
# If the guard has not ended it prints NOT-YET and changes nothing. If smoke failed, the first traceback is printed verbatim.
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/sleeph6r/vcommon.sh"
echo "dir-h6 vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/run-vast/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/run-vast/COLLECT.txt"; exit 0; }; done
[ -e "$G/rentals.txt" ] || { echo "NOT-STARTED: no rental record in $G"; exit 0; }
g=$(pgrep -f "vguard.sh $G" | tr '\n' ' '); echo "guard pid(s): ${g:-none}; live $LABEL instances: $(labelled)"
# the guard is the only thing that stops the rental: if it died (Mac restart) before ending, start it again from its own copy
if [ -z "$g" ] && [ ! -s "$G/END" ] && [ -s "$G/state" ]; then
  (nohup caffeinate -i bash "$G/vguard.sh" "$G" >> "$G/guard.out" 2>&1 < /dev/null &); sleep 5
  log "GUARD-RESTARTED by $JOB: pid(s) $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; fi
for w in $(seq 1 84); do [ -s "$G/END" ] && break; sleep 50; done
tail -8 "$G/log.txt"
[ -s "$G/END" ] || { echo "NOT-YET: the guard has not ended (spent \$$(spent)); the next collect job picks it up"; exit 0; }
echo "guard: $(cat "$G/END")"
FLAG=""
case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) FLAG="FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see run-vast/mac-log.txt); the copy below may be incomplete";; esac
[ -n "$FLAG" ] && echo "$FLAG"
O=$G/out/W; V=$A/run-vast; SRC="the verified copy-back"
if [ ! -d "$O" ] && [ -d "$G/snap/W" ]; then O=$G/snap/W; SRC="the 30-minute SNAPSHOT (NOT checked against a manifest; the final copy-back did not happen)"; fi
mkdir -p "$V" "$A/runs"
for R in $ORDER; do
  [ -d "$O/$R" ] || [ -f "$O/$R.log" ] || continue; mkdir -p "$A/runs/$R"
  for f in $R/dirh6-seed${R#s}.json $R.log $R.err; do
    [ -f "$O/$f" ] && cp "$O/$f" "$A/runs/$R/$(basename "$f")"; done; done
for f in drive-state.txt torch.txt pip-freeze.txt seals.txt checks.txt smoke.txt MANIFEST.sha256 sizes.json gpumem.log pids.txt; do [ -f "$O/$f" ] && cp "$O/$f" "$V/$(basename "$f")"; done
[ -f "$O/pip.log" ] && tail -20 "$O/pip.log" > "$V/pip-tail.txt"
[ -f "$G/out/drive.log" ] && cp "$G/out/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN); files from $SRC"; echo "guard: $(cat "$G/END")"; echo "spent \$$(spent) (rental list: run-vast/rentals.txt)"
  [ -n "$FLAG" ] && echo "$FLAG"
  if [ -f "$V/smoke.txt" ]; then
    if grep -q '^smoke ok' "$V/smoke.txt"; then echo "smoke: ok"; else echo "smoke: FAILED, first traceback verbatim (STOP: do not fix the script, report this):"; sed -n '/Traceback/,$p' "$V/smoke.txt" | head -40; fi
  else echo "smoke: not run"; fi
  [ -f "$V/torch.txt" ] && echo "torch record: $(head -1 "$V/torch.txt")"
  for R in $ORDER; do f=$A/runs/$R/dirh6-seed${R#s}.json
    if [ -s "$f" ]; then $PYM - "$f" "$R" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
m = d.get("morning", {})
done = {a: sum(1 for n in "123" if a in m.get(n, {})) for a in "NSLB"}
print(sys.argv[2] + ": result file yes; nights finished per arm " + ", ".join("%s %d of 3" % (a, done[a]) for a in "NSLB")
      + "; torch " + str(d.get("torch")) + "; gpu " + str(d.get("gpu")) + "; minutes " + str(d.get("minutes"))
      + "; arm_lr " + json.dumps(d.get("arm_lr")) + "; plan_identical_L_B " + str(d.get("plan_identical_L_B"))
      + "; plan_first300_identical_S_L " + str(d.get("plan_first300_identical_S_L")))
PY
    else echo "$R: no result file ($(grep -E " (DIED|HALT) " "$V/drive-state.txt" 2>/dev/null | grep -E "$R|HALT" | tail -1 | cut -c1-160))"; fi
  done
  echo "seed runs: $(grep -c ' LAUNCH ' "$V/drive-state.txt" 2>/dev/null) launched, $(grep -c ' FINISHED ' "$V/drive-state.txt" 2>/dev/null) finished, $(grep -c ' DIED ' "$V/drive-state.txt" 2>/dev/null) died (a seed with fewer than 4 finished arms counts as dead, PASSMARKS.md)"
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
