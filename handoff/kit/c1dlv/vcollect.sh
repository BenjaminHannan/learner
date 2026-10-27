#!/bin/bash
# c1-dl vast collect (Everyday chat thread, 2026-09-27; copied from c1-dev's handoff/kit/c1devv/vcollect.sh). Run on the Mac
# from the watcher worktree by the BASH-ONLY jobs handoff/held/rent-c1dl-2-collect.md and -3-. Restarts the Mac guard if it died, waits
# up to 70 min for it to end, then puts the copied-back files in $A/run-vast/ (the DL chat file, its logs, the rental's records,
# the guard's log) and writes $A/RESULTS-vast.md (counts only, no verdict: the thread scores the chats per PLAN.md). It never
# touches the rental itself and never touches c1-dev's folder.
# Usage: vcollect.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/c1dlv/vcommon.sh"
echo "c1-dl vast collect, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/RESULTS-vast.md" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/RESULTS-vast.md"; exit 0; }; done
[ -s "$A/RESULTS-vast.md" ] && { echo "DONE: $A/RESULTS-vast.md is already in this worktree"; exit 0; }
[ -e "$G/rentals.txt" ] || { echo "NOT-STARTED: no rental record in $G"; exit 0; }
g=$(pgrep -f "vguard.sh $G" | tr '\n' ' '); echo "guard pid(s): ${g:-none}; live $LABEL instances: $(labelled)"
# the guard is the only thing that stops the rental: if it died (Mac restart) before ending, start it again from its own copy
if [ -z "$g" ] && [ ! -s "$G/END" ] && [ -s "$G/state" ]; then
  (nohup ${CAFC1V-caffeinate -i} bash "$G/vguard.sh" "$G" >> "$G/guard.out" 2>&1 < /dev/null &); sleep 5
  log "GUARD-RESTARTED by $JOB: pid(s) $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; fi
for w in $(seq 1 ${WAITC1V:-84}); do [ -s "$G/END" ] && break; sleep ${SLW:-50}; done
tail -8 "$G/log.txt"
[ -s "$G/END" ] || { echo "NOT-YET: the guard has not ended (spent \$$(spent)); the next collect job picks it up"; exit 0; }
echo "guard: $(cat "$G/END")"
FLAG=""; case "$(cat "$G/END")" in *STOPPED-NOT-DESTROYED*|*UNCONFIRMED*) FLAG="FLAG-DIRECTOR: instance $(cut -d' ' -f1 "$G/state" 2>/dev/null) of $LABEL was NOT destroyed (see run-vast/mac-log.txt); the copy below may be incomplete";; esac
[ -n "$FLAG" ] && echo "$FLAG"
O=$G/out; V=$A/run-vast
mkdir -p "$V"
for x in $ARMS; do
  [ -f "$O/outC1/chat_$x.jsonl" ] && cp "$O/outC1/chat_$x.jsonl" "$V/chat_$x.jsonl"
  for f in log$x.txt log$x-retry.txt; do [ -f "$O/W/$f" ] && cp "$O/W/$f" "$V/$f"; done; done
for f in drive-state.txt steps.txt checks.txt torch.txt models.txt gpu_log.txt MANIFEST.sha256; do [ -f "$O/W/$f" ] && cp "$O/W/$f" "$V/$f"; done
[ -f "$O/W/pip.log" ] && tail -20 "$O/W/pip.log" > "$V/pip-tail.txt"
[ -f "$O/W/dl.log" ] && tail -c 3000 "$O/W/dl.log" | tr '\r' '\n' | grep . | tail -20 > "$V/dl-tail.txt"
[ -f "$O/drive.log" ] && cp "$O/drive.log" "$V/drive.log"
cp "$G/log.txt" "$V/mac-log.txt"; cp "$G/END" "$V/END.txt"
awk '{print $1, $2, $3, (NF>=4?$4:"-")}' "$G/rentals.txt" > "$V/rentals.txt"   # id, $/h, created, gone (epoch seconds)
# counts and checks, taken from the copied files; 336 rows over 60 conversations per arm is complete
NA=$(echo $ARMS | wc -w | tr -d ' ')
WINNL="winnl2: not Windows, nothing changed"
TWINB="twinb: the plain twin is Twin336b (enable_thinking=False)"
C1LINE="c1dev: talker = claude_e2e02d.Talker; W_PLACE02D=system; MAX_NEW02D=160; HIST_PAIRS=6; SLEEP02D=off; reader = none; reasoner = none"
full=0; rowsl=""
for x in $ARMS; do
  n=$(rows "$V/chat_$x.jsonl"); c=$(convs "$V/chat_$x.jsonl")
  [ "$n" = 336 ] && [ "$c" = 60 ] && full=$((full + 1)); rowsl="$rowsl $x rows=$n conversations=$c;"
done
v1() { local f=$V/log$1.txt ok=1
  [ -f "$f" ] || { echo "V1 $1 no log"; return; }
  [ "$(sed -n 1p "$f")" = "$WINNL" ] || ok=0; [ "$(sed -n 2p "$f")" = "$TWINB" ] || ok=0
  if [ "$1" = DL ]; then grep -qxF "$C1LINE" "$f" || ok=0; fi
  echo "V1 $1 $([ $ok = 1 ] && echo OK || echo FAIL)"; }
rowsl=${rowsl%;}
case "$(cat "$G/END")" in
  "END DONE "*) [ "$full" = "$NA" ] && status="COMPLETE: arm DL has 336 rows over 60 conversations" || status="PARTIAL: drive.sh finished but $full of $NA arms are complete;$rowsl";;
  *) status="ENDED EARLY ($(cut -d' ' -f2 "$G/END")): $full of $NA arms complete;$rowsl";;
esac
read -r CGPU CTF CDPH CTPD CEST < "$G/card" 2>/dev/null
lastl() { [ -s "$1" ] && grep . "$1" | tail -"$2" | cut -c1-300 | sed 's/^/    /' || echo "    (no file)"; }
{
  echo "# c1-dl vast run record (handoff/kit/c1dlv, job $JOB, kit $PIN, written $(now))"
  echo
  echo "**$status.** Counts only, no verdict: the Everyday chat thread scores it (PLAN.md) against c1-dev's T, Q and L chats. Every line"
  echo "below is copied by the script, never retyped. The replies are in the chat files and are not quoted here."
  [ -n "$FLAG" ] && { echo; echo "**$FLAG**"; }
  echo
  echo "## Card and money"
  echo
  echo "- Card: ${CGPU:-?}, ${CTF:-?} TFLOPS, \$${CDPH:-?}/h, ${CTPD:-?} TFLOPS per \$/h (estimate ${CEST:-?} min); guard: $(cat "$G/END")"
  echo "- Rentals (id, \$/h, created, gone; epoch seconds):"; sed 's/^/    /' "$V/rentals.txt"
  echo "- Spent by the kit's own count (GPU \$/h x hours plus each started host's download at its \$/GB): \$$(spent). The Director's ledger is the record."
  echo
  echo "## V1 (first two log lines; logDL also has the c1dev settings line)"
  echo; for x in $ARMS; do echo "- $(v1 $x)"; done
  echo; echo "- c1dev line in logDL: $(grep '^c1dev: ' "$V/logDL.txt" 2>/dev/null | head -1)"
  echo
  echo "## Rows per arm (expected 336 rows, 60 conversations)"
  echo; echo "   $rowsl"
  echo
  echo "## Steps (W/steps.txt, UTC)"
  echo; sed 's/^/    /' "$V/steps.txt" 2>/dev/null; echo
  echo "Minutes per arm: $("$PYM" -c 'import sys, datetime as D
s = {}
for l in open(sys.argv[1]):
    p = l.split()
    if len(p) < 3: continue
    t = D.datetime.strptime(p[-1], "%Y-%m-%dT%H:%M:%SZ")
    if p[1] == "start": s[p[0]] = t
    elif p[0] in s: print("%s %.1f;" % (p[0], (t - s[p[0]]).total_seconds() / 60), end=" ")' "$V/steps.txt" 2>/dev/null)"
  echo
  echo "## Last lines of each log"
  for x in $ARMS; do echo "- log$x.txt:"; echo; lastl "$V/log$x.txt" 2; echo
    [ -s "$V/log$x-retry.txt" ] && { echo "- log$x-retry.txt:"; echo; lastl "$V/log$x-retry.txt" 2; echo; }; done
  echo "## Machine and files"
  echo "- $(grep '^VERSIONS' "$V/checks.txt" 2>/dev/null | head -1) (torch, CUDA, transformers, python)"
  echo "- $(grep '^GPUNAME' "$V/checks.txt" 2>/dev/null | head -1)"
  echo "- selftests: $(grep -c '^CHECK .* ok=1 ' "$V/checks.txt" 2>/dev/null) of 4 ok (checks.txt); SEAL-2: $(grep -o 'SEAL-2 [0-9]*/24' "$V/drive-state.txt" 2>/dev/null | head -1)"
  echo "- model (pinned snapshot path, models.txt; LFM only): $(awk -F/ '{printf "%s@%s ", $(NF-2), $NF}' "$V/models.txt" 2>/dev/null)"
  echo "- GPU log (one line a minute: UTC, MiB used, MiB total, W, GPU %): $(awk '{n++; if($2+0>m)m=$2+0; if($4+0>p)p=$4+0} END{printf "lines=%d peak_used=%d MiB peak_power=%.1f W", n, m, p}' "$V/gpu_log.txt" 2>/dev/null)"
  echo "- Manifest check at copy-back: $(grep 'COPY-CHECK' "$G/log.txt" | tail -1 | cut -c1-200)"
  echo
  echo "| file | bytes | sha256 |"
  echo "|---|---|---|"
  for f in $(find "$V" -type f 2>/dev/null | sort); do
    echo "| $f | $(wc -c < "$f" | tr -d ' ') | $(shasum -a 256 "$f" | cut -c1-64) |"; done
} > "$A/RESULTS-vast.md"
cat "$A/RESULTS-vast.md" | head -30
echo "COLLECTED: $status"
