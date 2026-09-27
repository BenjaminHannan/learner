#!/bin/bash
# rd-378g vast collect (Trustworthy notes thread, 2026-09-27; built from handoff/kit/sleep358sv/vcollect.sh). Run on the Mac
# from the watcher worktree by the BASH-ONLY jobs handoff/held/rent378g-2-collect.md and -3-collect.md. It restarts the Mac
# guard if the guard died before ending, waits up to 70 min for it to end, then puts the copied-back files in $V (beside
# benspc/, never over it): steps, logs, checks, the torch and host lines, notes_confirm.json, ranked_turns.jsonl (positions
# only), notes_confirm_whenoff.json, train/ (summary, train log, dev notes), g5/ (G's and R's notes on the 43 G5 dialogs),
# SEAL-run, the manifest, the rental list, the guard's log and COLLECT.txt. LoCoMo-derived files go to ~/rd378g-private/vast
# only, and G's adapter to ~/premonition-models/rd378g-vast-adapter only (never pushed). It never touches the rental itself.
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/rd378gv/vcommon.sh"
echo "rd-378g vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$V/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $V/COLLECT.txt"; exit 0; }; done
[ -e "$G/rentals.txt" ] || { echo "NOT-STARTED: no rental record in $G"; exit 0; }
g=$(pgrep -f "vguard.sh $G" | tr '\n' ' '); echo "guard pid(s): ${g:-none}; live $LABEL instances: $(labelled)"
# the guard is the only thing that stops the rental: if it died (Mac restart) before ending, start it again from its own copy
if [ -z "$g" ] && [ ! -s "$G/END" ] && [ -s "$G/state" ]; then
  (nohup caffeinate -i bash "$G/vguard.sh" "$G" >> "$G/guard.out" 2>&1 < /dev/null &); sleep 5
  log "GUARD-RESTARTED by $JOB: pid(s) $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; fi
for w in $(seq 1 84); do [ -s "$G/END" ] && break; sleep "${PC378:-50}"; done
tail -8 "$G/log.txt"
[ -s "$G/END" ] || { echo "NOT-YET: the guard has not ended (spent \$$(spent)); the next collect job picks it up"; exit 0; }
echo "guard: $(cat "$G/END")"
O=$G/out; GD=$(cat "$O/W/g-dir.txt" 2>/dev/null); GD=${GD:-W/g}
mkdir -p "$V/logs" "$V/train" "$V/g5"
for f in steps.txt checks.txt torch.txt drive-state.txt hf.txt SEAL-run.sha256.txt MANIFEST.sha256 notes_confirm.json ranked_turns.jsonl notes_confirm_whenoff.json r-path.txt g-dir.txt; do
  [ -f "$O/W/$f" ] && cp "$O/W/$f" "$V/$f"; done
for s in dialogs train devcheck write59 score whenoff g5G g5R; do [ -f "$O/W/${s}_log.txt" ] && cp "$O/W/${s}_log.txt" "$V/logs/"; done
[ -f "$O/W/pip.log" ] && tail -20 "$O/W/pip.log" > "$V/logs/pip-tail.txt"
[ -f "$O/drive.log" ] && cp "$O/drive.log" "$V/logs/drive.log"
for f in summary.json train_log.jsonl; do [ -f "$O/$GD/$f" ] && cp "$O/$GD/$f" "$V/train/$f"; done
[ -f "$O/W/gdev.jsonl" ] && cp "$O/W/gdev.jsonl" "$V/train/gdev.jsonl"
[ -f "$O/W/g5_G.jsonl" ] && cp "$O/W/g5_G.jsonl" "$V/g5/notes_G.jsonl"
[ -f "$O/W/g5_R.jsonl" ] && cp "$O/W/g5_R.jsonl" "$V/g5/notes_R.jsonl"
# LoCoMo-derived files and G's adapter stay on the Mac, outside git
if [ -d "$O/P" ]; then mkdir -p "$MPRIV"; cp -R "$O/P/." "$MPRIV/"; fi
if [ -d "$O/$GD/adapter" ] && [ ! -d "$MADP" ]; then mkdir -p "$(dirname "$MADP")"; cp -R "$O/$GD/adapter" "$MADP"; fi
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"; [ -f "$G/offers-note.txt" ] && cp "$G/offers-note.txt" "$V/offers-note.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"
  case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) echo "FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state") of $LABEL was NOT destroyed (see vast/mac-log.txt); the copy may be incomplete";; esac
  grep 'CARD rental' "$G/log.txt" | tail -1
  echo "steps: $(awk '$2 ~ /^rc=/ || $2=="skipped" {printf "%s %s; ", $1, $2}' "$O/W/steps.txt" 2>/dev/null)"
  a=$(awk -v f="$GD/adapter/adapter_model.safetensors" '$2==f {print $1}' "$O/W/SEAL-run.sha256.txt" 2>/dev/null)
  m=$(shasum -a 256 "$MADP/adapter_model.safetensors" 2>/dev/null | awk '{print $1}')
  [ -n "$a" ] && { [ "$a" = "$m" ] && echo "G's adapter: $MADP matches SEAL-run" || echo "G's adapter: $MADP MISMATCH or missing"; }
  echo "G merged sha256 (stays on the rental; rebuildable from base + adapter): $(awk '$2 ~ /merged\/model.safetensors$/ {print $1}' "$O/W/SEAL-run.sha256.txt" 2>/dev/null)"
  echo "LoCoMo-derived files: $(ls "$MPRIV" 2>/dev/null | tr '\n' ' ')in $MPRIV (Mac only)"
  echo "spent \$$(spent) (rentals.txt: id, \$/h, created, gone)"
} > "$V/COLLECT.txt"
cat "$V/COLLECT.txt"
echo COLLECTED
