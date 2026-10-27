#!/bin/bash
# opus-mxd vast collect (copy of handoff/kit/s3v/vcollect.sh, adapted). Run on the Mac from the watcher worktree by the BASH-ONLY job
# handoff/queue/opus-mxd-vast-2-collect.md. Restarts the Mac guard if it died, waits up to 70 min for it to end, then puts the copied-back files under
# artifacts/opus-manager-20260929/mxd-vast/ (NEVER into the sealed artifacts/claude-moe-deep-20260929): runs/, eq-runs/, SMOKE-gpu.json, TIMING-gpu.json,
# logs/ (selftest, smoke, phase 1), and the rental's records in run-vast/. It never touches the rental itself. No .pt file exists in the copy; no holdout
# file exists (the holdout is not part of this job).
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/opmxd/vcommon.sh"
echo "opus-mxd vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$OUT/run-vast/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $OUT/run-vast/COLLECT.txt"; exit 0; }; done
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
flag() { case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) echo "FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see run-vast/mac-log.txt); the copy below may be incomplete";; esac; }
flag
O=$G/out/W; V=$OUT/run-vast
mkdir -p "$V" "$OUT/logs"
for d in runs eq-runs; do [ -d "$O/moe/$d" ] && { mkdir -p "$OUT/$d"; cp -R "$O/moe/$d/." "$OUT/$d/"; }; done
for f in SMOKE-gpu.json TIMING-gpu.json; do [ -f "$O/moe/$f" ] && cp "$O/moe/$f" "$OUT/$f"; done
for f in selftest_rental.txt smoke_log.txt log_phase1.txt; do [ -f "$O/$f" ] && cp "$O/$f" "$OUT/logs/$f"; done
find "$OUT" -name '*.pt' -exec rm -f {} + 2>/dev/null   # none expected (never mirrored); belt and braces
for f in drive-state.txt torch.txt seal.txt MANIFEST.sha256; do [ -f "$O/$f" ] && cp "$O/$f" "$V/$f"; done
[ -f "$O/pip.log" ] && tail -20 "$O/pip.log" > "$V/pip-tail.txt"
[ -f "$G/out/drive.log" ] && cp "$G/out/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"; flag
  echo "parts (drive-state): $(grep -E ' (PART-DONE|PART-SKIPPED|RESUME-ONCE|SMOKE-DONE|LOOP-SOURCE|SELFTEST-OK|SEAL)( |$)' "$O/drive-state.txt" 2>/dev/null | cut -d' ' -f2- | tr '\n' ';')"
  echo "last drive-state line: $(tail -1 "$O/drive-state.txt" 2>/dev/null)"
  echo "sha256 of every source.json, qualified.json and adapt.json now in $OUT:"
  find "$OUT" \( -name source.json -o -name qualified.json -o -name adapt.json \) -type f | sort | while IFS= read -r f; do shasum -a 256 "$f"; done
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
