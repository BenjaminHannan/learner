#!/bin/bash
# mu-406 vast collect ("Making things up about you" thread, Claude, 2026-09-27; built from the sleep research thread's
# handoff/kit/sleep358sv/vcollect.sh). Run on the Mac from the watcher worktree by the BASH-ONLY jobs
# handoff/held/rent406-2-collect.md and -3-collect.md. Restarts the Mac guard if it died, waits up to 70 min for it to end,
# then puts the copied-back files into $A/vast/ (every file from the rental's W folder except the adapter weights and the long
# pip and download logs, whose tails are kept) and $A/SEAL-run-vast.sha256.txt. It never touches the rental itself and never
# pushes weights (the adapter stays in ~/premonition-models/mu406-vast).
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/madeup406v/vcommon.sh"
echo "mu-406 vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/vast/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/vast/COLLECT.txt"; exit 0; }; done
[ -e "$G/rentals.txt" ] || { echo "NOT-STARTED: no rental record in $G"; exit 0; }
g=$(pgrep -f "vguard.sh $G" | tr '\n' ' '); echo "guard pid(s): ${g:-none}; live $LABEL instances: $(labelled)"
# the guard is the only thing that stops the rental: if it died (Mac restart) before ending, start it again from its own copy
if [ -z "$g" ] && [ ! -s "$G/END" ] && [ -s "$G/state" ]; then
  (nohup ${CAF406:-caffeinate -i} bash "$G/vguard.sh" "$G" >> "$G/guard.out" 2>&1 < /dev/null &); sleep 5
  log "GUARD-RESTARTED by $JOB: pid(s) $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; fi
for w in $(seq 1 84); do [ -s "$G/END" ] && break; sleep ${PC406:-50}; done
tail -8 "$G/log.txt"
[ -s "$G/END" ] || { echo "NOT-YET: the guard has not ended (spent \$$(spent)); the next collect job picks it up"; exit 0; }
echo "guard: $(cat "$G/END")"
FLAG=""; case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) FLAG="FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see vast/mac-log.txt); the copy below may be incomplete"; echo "$FLAG";; esac
O=$G/out/W; V=$A/vast; SR=$A/SEAL-run-vast.sha256.txt
mkdir -p "$V"
if [ -d "$O" ]; then
  (cd "$O" && find . -type f ! -name '*.safetensors' ! -name pip.log ! -name model.err ! -name 'MANIFEST.sha256.prev-*' | sort) | while IFS= read -r f; do
    mkdir -p "$V/$(dirname "$f")"; cp "$O/$f" "$V/$f"; done
  [ -f "$O/pip.log" ] && tail -20 "$O/pip.log" > "$V/pip-tail.txt"
  [ -f "$O/model.err" ] && tail -c 2000 "$O/model.err" > "$V/model-err-tail.txt"
  [ -s "$O/SEAL-run.sha256.txt" ] && cp "$O/SEAL-run.sha256.txt" "$SR"
fi
[ -f "$G/out/drive.log" ] && cp "$G/out/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
[ -f "$G/offers-note.txt" ] && cp "$G/offers-note.txt" "$V/offers-note.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"; [ -n "$FLAG" ] && echo "$FLAG"
  if [ -s "$SR" ]; then sha=$(awk '{print $1}' "$SR"); m=$(shasum -a 256 "$MP/adapter/adapter_model.safetensors" 2>/dev/null | awk '{print $1}')
    [ "$m" = "$sha" ] && echo "adapter sealed, Mac copy sha256 ok ($MP/adapter)" || echo "adapter sealed, Mac copy sha256 MISMATCH or missing"
  else echo "adapter: not sealed (training did not finish)"; fi
  for f in $EXPECT; do [ -s "$V/$f" ] && echo "$f: $(wc -l < "$V/$f" | tr -d ' ') lines" || echo "$f: MISSING"; done
  [ -s "$V/gen/noharm.json" ] && echo "noharm.json: $(tr -d '\n ' < "$V/gen/noharm.json" | cut -c1-400)"
  echo "last progress line: $(tail -1 "$V/drive-state.txt" 2>/dev/null)"
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
