#!/bin/bash
# slp-358n3 vast collect (sleep research thread, 2026-09-27; copy of the 358s kit's collect). Run on the Mac by the BASH-ONLY jobs
# handoff/held/rent358n3-2-collect.md and -3-collect.md. Restarts the Mac guard if it died, waits up to 70 min for it to end, then
# puts the copied-back files in the repo: $A/SEAL-run.sha256.txt, $A/runs/<R>/ (slp358n3-seed<S>.json, <R>.log, <R>.err) and the
# rental's records (progress file, torch check, checks, day sizes, RESUME result, manifest) in $A/run-vast/. It never touches the
# rental and never pushes weights (the slept reasoners stay in ~/premonition-models/slp358n3; RESUME's .pt files stay in $G).
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/sleep358nv/vcommon.sh"
echo "slp-358n3 vast collect, kit $PIN, job $JOB, $(now)"
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
case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) echo "FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see run-vast/mac-log.txt); the copy below may be incomplete";; esac
O=$G/out/W; V=$A/run-vast; SR=$A/SEAL-run.sha256.txt
mkdir -p "$V" "$A/runs"
[ -s "$O/SEAL-run.sha256.txt" ] && cp "$O/SEAL-run.sha256.txt" "$SR"
for R in $ORDER; do
  [ -d "$O/$R" ] || [ -f "$O/$R.log" ] || continue; mkdir -p "$A/runs/$R"
  for f in $R/slp358n3-seed${R#s}.json $R.log $R.err; do
    [ -f "$O/$f" ] && cp "$O/$f" "$A/runs/$R/$(basename "$f")"; done; done
for f in drive-state.txt torch.txt checks.txt MANIFEST.sha256 sizes.json pick-sizes.log gpumem.log resume.log resume/resume.json; do [ -f "$O/$f" ] && cp "$O/$f" "$V/$(basename "$f")"; done
[ -f "$O/pip.log" ] && tail -20 "$O/pip.log" > "$V/pip-tail.txt"
[ -f "$G/out/drive.log" ] && cp "$G/out/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"
case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) echo "FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see run-vast/mac-log.txt); the copy below may be incomplete";; esac
  [ -s "$SR" ] && while read -r sha f; do
    m=$(shasum -a 256 "$MP/$f" 2>/dev/null | awk '{print $1}'); [ "$m" = "$sha" ] && echo "$f sealed, Mac copy sha256 ok" || echo "$f sealed, Mac copy sha256 MISMATCH or missing"
  done < "$SR"
  for R in $ORDER; do echo "$R: $(cd "$A/runs/$R" 2>/dev/null && ls slp358n3-seed*.json 2>/dev/null | tr '\n' ' ' || echo 'nothing')"; done
  echo "RESUME: $(tr -d '\n ' < "$V/resume.json" 2>/dev/null | grep -o '"RESUME_identical":[a-z]*' || echo 'no result')"
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
