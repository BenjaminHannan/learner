#!/bin/bash
# opcpu vast collect (Opus manager, 2026-09-29; copy of handoff/kit/s3v/vcollect.sh with the changes in DEVIATIONS.md). Run on the Mac from the watcher worktree
# by the BASH-ONLY job handoff/queue/opus-cpu-vast-2-collect.md. Restarts the Mac guard if it died, waits up to 70 min for it to end, then puts the copied-back
# small files (json, logs; never a .pt) in the repo, ONLY under artifacts/opus-manager-20260929/cpu-vast/:
#   <test>/...   one folder per test (ks-1-lead0, s2think, trn-decode, pond-a-dev, pond-b-dev, pond-c-dev, pond-z-dev, pond-doubt, s1-loop, s1-plain), holding
#                what that test's PUSH line names, under its repo-relative paths
#   _rental/     the rental's records: drive-state, torch check, inputs list and hashes, the manifest, job stdout, the Mac log, DEVIATIONS.md, COLLECT.txt
# It never touches the rental itself and never writes outside that folder (in particular not into any sealed folder).
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/opcpu/vcommon.sh"
echo "opcpu vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/_rental/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/_rental/COLLECT.txt"; exit 0; }; done
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
case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) FLAG="FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see _rental/mac-log.txt); the copy below may be incomplete"; echo "$FLAG";; esac
O=$G/out; V=$A/_rental
mkdir -p "$V"
for R in $JOBS; do
  [ -d "$O/out/$R" ] || continue; mkdir -p "$A/$R"
  # the same defensive filter as box/pack.sh: no .pt, nothing named holdout / test.pt / readpanel / blind
  ( cd "$O/out/$R" && find . -type f ! -name '*.pt' ! -name 'holdout*' ! -name 'test.pt' ! -name '*readpanel*' ! -name '*blind*' | tar -cf - -T - ) | tar -x -C "$A/$R"; done
for f in drive-state.txt torch.txt inputs-check.txt venv.log MANIFEST.sha256 EXCLUDED.txt; do [ -f "$O/W/$f" ] && cp "$O/W/$f" "$V/$f"; done
[ -f "$O/W/pip.log" ] && tail -20 "$O/W/pip.log" > "$V/pip-tail.txt"
for R in $JOBS; do [ -f "$O/W/$R.out" ] && cp "$O/W/$R.out" "$V/$R.stdout.txt"; done   # each job's own printed report (the Mac queue files ask for these in their REPORT)
[ -f "$O/drive.log" ] && cp "$O/drive.log" "$V/drive.log"
[ -f "$O/in/INPUTS.txt" ] && cp "$O/in/INPUTS.txt" "$V/INPUTS.txt"
[ -f "$KD/handoff/kit/opcpu/DEVIATIONS.md" ] && cp "$KD/handoff/kit/opcpu/DEVIATIONS.md" "$V/DEVIATIONS.md"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"; [ -n "$FLAG" ] && echo "$FLAG"
  for R in $JOBS; do echo "$R: $(grep " JOB $R " "$O/W/drive-state.txt" 2>/dev/null | sed 's/^[^ ]* //' | tr '\n' ';') files: $(cd "$A/$R" 2>/dev/null && find . -type f | wc -l | tr -d ' ')"; done
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
