#!/bin/bash
# rsn-358u vast collect (sleep research thread, 2026-09-27). Run on the Mac from the watcher worktree by the BASH-ONLY jobs
# handoff/held/rent358u-2-collect.md and -3-collect.md. Waits up to 70 min for the guard to end, then puts the copied-back files
# where the BensPC kit would have put them: $A/SEAL-run.sha256.txt, $A/runs/<R>/ (train_log.jsonl, train_summary.json,
# poison.json, tests.json, <R>.log, <R>.err, <R>.poison.log, <R>.eval.log) and the rental's own records in $A/run-vast/.
# It never touches the rental (the guard already destroyed it) and never pushes weights (final.pt stays in ~/premonition-models).
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/sleep358uv/vcommon.sh"
echo "rsn-358u vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/run-vast/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/run-vast/COLLECT.txt"; exit 0; }; done
[ -e "$G/rentals.txt" ] || { echo "NOT-STARTED: no rental record in $G"; exit 0; }
g=$(pgrep -f "vguard.sh $G" | tr '\n' ' '); echo "guard pid(s): ${g:-none}; live $LABEL instances: $(labelled)"
for w in $(seq 1 84); do [ -s "$G/END" ] && break; sleep 50; done
tail -8 "$G/log.txt"
[ -s "$G/END" ] || { echo "NOT-YET: the guard has not ended (spent \$$(spent)); the next collect job picks it up"; exit 0; }
echo "guard: $(cat "$G/END")"
O=$G/out/W; V=$A/run-vast
mkdir -p "$V" "$A/runs"
[ -s "$O/SEAL-run.sha256.txt" ] && cp "$O/SEAL-run.sha256.txt" "$A/SEAL-run.sha256.txt"
for R in $ORDER; do
  [ -d "$O/$R" ] || [ -f "$O/$R.log" ] || continue; mkdir -p "$A/runs/$R"
  for f in $R/train_log.jsonl $R/train_summary.json $R/poison.json $R/tests.json $R.log $R.err $R.poison.log $R.eval.log; do
    [ -f "$O/$f" ] && cp "$O/$f" "$A/runs/$R/$(basename "$f")"; done; done
for f in drive-state.txt torch.txt checks.txt; do [ -f "$O/$f" ] && cp "$O/$f" "$V/$f"; done
[ -f "$O/pip.log" ] && tail -20 "$O/pip.log" > "$V/pip-tail.txt"
[ -f "$G/out/drive.log" ] && cp "$G/out/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"
  [ -s "$A/SEAL-run.sha256.txt" ] && while read -r sha f; do R=${f%/final.pt}
    m=$(shasum -a 256 "$MP/$R/final.pt" 2>/dev/null | awk '{print $1}'); [ "$m" = "$sha" ] && echo "$R final.pt sealed, Mac copy sha256 ok" || echo "$R final.pt sealed, Mac copy sha256 MISMATCH or missing"
  done < "$A/SEAL-run.sha256.txt"
  for R in $ORDER; do echo "$R: $(cd "$A/runs/$R" 2>/dev/null && ls poison.json tests.json 2>/dev/null | tr '\n' ' ' || echo 'nothing')"; done
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
