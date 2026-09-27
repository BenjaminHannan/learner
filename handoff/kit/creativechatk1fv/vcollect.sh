#!/bin/bash
# k1f vast collect (Creative answers in chat thread, 2026-09-27; built from handoff/kit/sleep358sv/vcollect.sh). Run on the
# Mac from the watcher worktree by the BASH-ONLY jobs handoff/held/rent-k1fv-2-collect.md and -3-collect.md. Restarts the
# Mac guard if it died, waits up to 70 min for it to end, then lays the copied-back files out as the registered step 6
# does: $A/run/ gets the TEST-ONLY outF files (copied, never opened) and the five logs, $A/run/dev/ gets devk1f/ and
# logdevF.txt, and $A/run/vast/ gets the rental's records (progress file, report, versions, models, seals and tests,
# scorer outputs, CRLF counts, GPU memory peak, manifest, the Mac guard's log, rentals, END). It writes
# $A/RESULTS-vast.md from those records (counts only; no reply, draft or test item is read). It never touches the rental.
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/creativechatk1fv/vcommon.sh"
echo "k1f vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/run/vast/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/run/vast/COLLECT.txt"; exit 0; }; done
[ -e "$G/rentals.txt" ] || { echo "NOT-STARTED: no rental record in $G"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
g=$(pgrep -f "vguard.sh $G" | tr '\n' ' '); echo "guard pid(s): ${g:-none}; live $LABEL instances: $(labelled)"
# the guard is the only thing that ends the rental: if it died (Mac restart) before ending, start it again from its own copy
if [ -z "$g" ] && [ ! -s "$G/END" ] && [ -s "$G/state" ]; then
  (nohup caffeinate -i bash "$G/vguard.sh" "$G" >> "$G/guard.out" 2>&1 < /dev/null &); sleep 5
  log "GUARD-RESTARTED by $JOB: pid(s) $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; fi
for w in $(seq 1 84); do [ -s "$G/END" ] && break; sleep 50; done
tail -8 "$G/log.txt"
[ -s "$G/END" ] || { echo "NOT-YET: the guard has not ended (spent \$$(spent)); the next collect job picks it up"; exit 0; }
echo "guard: $(cat "$G/END")"
FLAG=""; case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) FLAG="FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state" 2>/dev/null) of $LABEL was NOT destroyed (see run/vast/mac-log.txt); the copy may be incomplete";; esac
[ -n "$FLAG" ] && echo "$FLAG"
O=$G/out; R=$A/run; V=$R/vast
mkdir -p "$R" "$R/dev" "$V"
for f in creative_F.jsonl creative_K.jsonl creative_T.jsonl creative_Q.jsonl creative_L.jsonl creative_judge.jsonl creative_key.json creative_judge_u.jsonl creative_key_u.json summary_creative.json grammar_creative_F.jsonl drafts_K.jsonl drafts_F.jsonl drafts_judge.jsonl drafts_key.json; do
  [ -f "$O/outF/$f" ] && cp "$O/outF/$f" "$R/$f"; done
for a in $ARMS; do [ -f "$O/W/log$a.txt" ] && cp "$O/W/log$a.txt" "$R/log$a.txt"; done
[ -d "$O/devk1f" ] && cp -R "$O/devk1f/." "$R/dev/"
[ -f "$O/W/logdevF.txt" ] && cp "$O/W/logdevF.txt" "$R/dev/logdevF.txt"
for f in drive-state.txt report.txt pids.txt torch.txt versions.txt models.txt route122.txt tests.txt score.txt dedupe.txt draftpacket.txt crlf.txt gpumem-peak.txt MANIFEST.sha256; do
  [ -f "$O/W/$f" ] && cp "$O/W/$f" "$V/$f"; done
[ -f "$O/W/pip.log" ] && tail -20 "$O/W/pip.log" > "$V/pip-tail.txt"
[ -f "$O/W/download.err" ] && tail -20 "$O/W/download.err" > "$V/download-err-tail.txt"
[ -f "$O/drive.log" ] && cp "$O/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
# check every copied run file against the rental's manifest
bad=0; nchk=0
while read -r sha f; do
  case "$f" in outF/*) d="$R/${f#outF/}";; devk1f/*) d="$R/dev/${f#devk1f/}";; W/log[FKTQL].txt) d="$R/${f#W/}";; W/logdevF.txt) d="$R/dev/logdevF.txt";; *) continue;; esac
  [ -f "$d" ] || continue; nchk=$((nchk+1))
  [ "$(shasum -a 256 "$d" | awk '{print $1}')" = "$sha" ] || { echo "MISMATCH $d"; bad=$((bad+1)); }
done 2>/dev/null < "$O/W/MANIFEST.sha256"
SP=$(spent)
{ echo "collected $(now) by $JOB (kit $PIN)"; echo "guard: $(cat "$G/END")"; [ -n "$FLAG" ] && echo "$FLAG"
  echo "run files checked against the rental's manifest: $nchk, mismatches $bad"; } > "$V/COLLECT.txt"
{ echo "# k1f on one vast card: RESULTS (written by $JOB from the rental's records, $(now); counts only, no reply quoted)"
  echo
  echo "Label: K, F and H run on 0.2c's build, whose talker carries the puzzle-trained 0.2c sleep adapter. H minus F is still one change, because both share that talker."
  echo
  echo "## End"
  echo "- guard: $(cat "$G/END")"; [ -n "$FLAG" ] && echo "- $FLAG"
  echo "- last progress line: $(tail -1 "$V/drive-state.txt" 2>/dev/null)"
  echo "- run files checked against the rental's sha256 manifest: $nchk, mismatches $bad"
  echo
  echo "## Money and card (the Mac guard's log, run/vast/mac-log.txt)"
  grep -E 'credit \$|rental [0-9]+: instance|card .* TFLOPS|DESTROYED|STOPPED|GUARD-END' "$G/log.txt" | sed 's/^/- /'
  echo "- dollars, all rentals of this task (dph x hours from rentals.txt): \$$SP"
  echo
  echo "## Rental report (run/vast/report.txt: setup, versions, model paths, seals, tests, adapter, DEV gate, V1, arms, CRLF, GPU memory)"
  sed 's/^/- /' "$V/report.txt" 2>/dev/null
  echo
  echo "## Scorer outputs (counts only)"
  for f in score.txt dedupe.txt draftpacket.txt; do echo "- $f:"; echo '```'; tail -30 "$V/$f" 2>/dev/null; echo '```'; done
  echo
  echo "## Suggested ledger line (the Director files it)"
  echo "$(date -u +%F) | k1f vast (rent-k1fv) | instance(s) $(awk '{printf "%s ", $1}' "$G/rentals.txt") | $(grep -o 'card [^,]*' "$G/log.txt" | tail -1) | \$$SP | $(cut -d' ' -f2 "$G/END")"
} > "$A/RESULTS-vast.md"
cat "$V/COLLECT.txt"; echo; cat "$A/RESULTS-vast.md" | grep -v '^- test \|^- seal ' | head -60
echo COLLECTED
