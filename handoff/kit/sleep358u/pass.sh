#!/bin/bash
# rsn-358u builder-free pass, run on the Mac from the worktree by BASH-ONLY queue jobs (sleep research thread, 2026-09-27).
# rsn-358u version of handoff/kit/sleep358s (same design; free LLM builders stalled 09-27). Every step is state-driven, so a
# later pass picks up where the last one stopped. Before anything else, a pass sets up C:\Users\benja\rsn358u once from the
# pinned commit (scripts, the sealed 358u folder, 358i's tests) and runs the selftest and check-mask once:
#   collect  copy each finished run (sha256 into SEAL-run BEFORE any eval, logs to the artifact folder, final.pt to both
#            premonition-models folders) and record runs that died. Never launches or stops anything.
#   full     collect, then, if nothing of ours or anyone else's is running on BensPC: launch the next unstarted runs in
#            the sealed order (two at once, then one more each time 5 GB is still free 5 minutes later); once all eight are
#            trained or dead, launch V1 poison then the eval of every sealed checkpoint once; then copy the outputs back.
# Usage: pass.sh <kit-dir> <pinned-commit> collect|full <queue-job-name>        (bash 3.2 safe: macOS)
set -u
KD=$1; PIN=$2; MODE=$3; JOB=${4:-?}
A=artifacts/claude-rsn358u-20260927
SSH=${SSH358:-"ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o BatchMode=yes benspc"}
RB=${RB358:-'"C:\Program Files\Git\bin\bash.exe" /c/Users/benja/rsn358u/handoff/kit/sleep358u/remote/bo358u.sh'}
WIN=${WIN358:-'C:\Users\benja\rsn358u'}
MP=${MP358:-$HOME/premonition-models/rsn358u}
ORDER="loop-s13 plain-s13 loop-s14 plain-s14 loop-s15 plain-s15 loop-s16 plain-s16"
SEAL=$A/SEAL-run.sha256.txt
NOTE=$A/run/RUN-NOTE-bo.md
T0=$(date +%s)
rb() { $SSH "$RB $*" < /dev/null 2>&1 | tr -d '\r'; }
now() { date -u +%FT%TZ; }
note() { echo "- $(now) $*" >> "$NOTE"; echo "NOTE: $*"; }
field() { echo "$ST" | awk -v r="$1" -v k="$2" '$1=="RUN" && $2==r {for(i=3;i<=NF;i++){split($i,a,"="); if(a[1]==k) print a[2]}}'; }
line() { echo "$ST" | awk -v t="$1" -v r="$2" '$1==t && $2==r {sub("^" t " " r " ",""); print; exit}'; }

echo "rsn-358u pass ($MODE), kit $PIN, start $(now)"
if git cat-file -e "origin/main:$A/RESULTS.md" 2>/dev/null || git cat-file -e "origin/builder-outbox:$A/RESULTS.md" 2>/dev/null; then echo "DUPLICATE: RESULTS.md exists"; exit 0; fi
mkdir -p "$A/runs" "$A/run" "$MP"
# one pass at a time (a collect job and a GPU pass may overlap)
w=0; until mkdir "$A/run/.pass-lock" 2>/dev/null; do w=$((w+1)); [ $w -gt 40 ] && { echo "LOCKED: another pass holds $A/run/.pass-lock for 20 min; stopping"; exit 0; }; sleep 30; done
trap 'rmdir "$A/run/.pass-lock" 2>/dev/null' EXIT
if [ ! -s "$SEAL" ]; then git show "origin/main:$SEAL" > "$SEAL" 2>/dev/null || git show "origin/builder-outbox:$SEAL" > "$SEAL" 2>/dev/null || : > "$SEAL"; fi

# 1. the helper kit goes to BensPC as files (tar through cmd.exe), then its hashes are checked against the pinned commit
$SSH "if not exist $WIN mkdir $WIN" < /dev/null 2>&1 | tr -d '\r'
git archive "$PIN" handoff/kit/sleep358u/remote | $SSH "tar -xf - -C $WIN" 2>&1 | tr -d '\r'
want=$(cd "$KD/handoff/kit/sleep358u/remote" && shasum -a 256 bo358u.sh procs.ps1 launch.ps1 train1.cmd evals.cmd eval1.cmd | awk '{print $1}' | tr '\n' ' ')
got=$(rb kithash | awk '{print $1}' | tr '\n' ' ')
[ "$want" = "$got" ] || { echo "STOP: kit on BensPC does not match $PIN"; echo "want $want"; echo "got  $got"; exit 0; }
echo "kit on BensPC matches $PIN"

# 2. one-time setup of the run folder (never overwrites: only when the sealed folder is absent), then the checks once
if [ "$(rb hastree | tail -1)" != "TREE 1" ]; then
  git archive "$PIN" scripts $A artifacts/claude-rsn358i-20260926/tests | $SSH "tar -xf - -C $WIN" 2>&1 | tr -d '\r'
  note "set up $WIN from $PIN (scripts, $A, 358i tests)"; fi
$SSH "if not exist $WIN\\W mkdir $WIN\\W" < /dev/null 2>&1 | tr -d '\r'
ST=$(rb state); echo "$ST"
echo "$ST" | grep -q '^END-STATE' || { echo "STOP: no state from BensPC"; exit 0; }
set -- $(echo "$ST" | awk '$1=="SEAL"{print $2, $3}'); [ "${1:-0}" = 20 ] && [ "${2:-0}" = 20 ] || { echo "STOP: SEAL-code check is ${1:-?}/${2:-?}, not 20/20"; exit 0; }
[ "$(echo "$ST" | awk '$1=="WDIR"{print $2}')" = 1 ] || { echo "STOP: no W folder on BensPC"; exit 0; }
CK=$(echo "$ST" | awk '$1=="CHECKS"{print $2}')
if [ "$CK" != 1 ]; then c=$(rb checks); echo "$c"; note "checks: $(echo "$c" | tr '\n' ' ' | cut -c1-400)"
  echo "$c" | grep -q '^CHECKS 1' || { echo "STOP: selftest or check-mask failed; nothing launched"; exit 0; }; fi

# 3. collect
TMPD=$(mktemp -d)
for R in $ORDER; do
  fin=$(field $R final); tp=$(field $R train_proc); ep=$(field $R eval_proc)
  if [ "$fin" = 1 ] && [ "$tp" = 0 ] && ! grep -q " $R/final.pt\$" "$SEAL"; then
    sha=$(line SHA $R)
    echo "$sha" | grep -qE '^[0-9a-f]{64}$' || { echo "SKIP $R: bad sha '$sha'"; continue; }
    echo "$sha  $R/final.pt" >> "$SEAL"; note "sealed $R final.pt $sha (before any eval)"
    mkdir -p "$A/runs/$R"
    for f in train_log.jsonl train_summary.json; do
      $SSH "tar -cf - -C $WIN\\W $R/$f" < /dev/null 2>/dev/null | tar -x -C "$TMPD" && cp "$TMPD/$R/$f" "$A/runs/$R/$f" || echo "MISSING $R/$f"; done
    $SSH "tar -cf - -C $WIN\\W $R.log" < /dev/null 2>/dev/null | tar -x -C "$TMPD" && cp "$TMPD/$R.log" "$A/runs/$R/$R.log" || echo "MISSING $R.log"
    c=$(rb copy-model $R); echo "$c"
    echo "$c" | grep -q "^COPY $R $sha" && note "BensPC copy premonition-models/rsn358u/$R/final.pt sha256 ok" || note "BensPC copy of $R: $c"
    mkdir -p "$MP/$R"; $SSH "tar -cf - -C $WIN\\W $R/final.pt" < /dev/null 2>/dev/null | tar -x -C "$MP"
    m=$(shasum -a 256 "$MP/$R/final.pt" 2>/dev/null | awk '{print $1}')
    [ "$m" = "$sha" ] && note "Mac copy ~/premonition-models/rsn358u/$R/final.pt sha256 ok" || note "Mac copy of $R sha256 '$m' does not match"
  fi
  if [ "$(field $R tests)" = 1 ] && [ "$ep" = 0 ] && [ ! -s "$A/runs/$R/tests.json" ]; then
    mkdir -p "$A/runs/$R"
    for f in $R/tests.json $R.eval.log $R/poison.json $R.poison.log; do
      $SSH "tar -cf - -C $WIN\\W $f" < /dev/null 2>/dev/null | tar -x -C "$TMPD" && cp "$TMPD/$f" "$A/runs/$R/$(basename "$f")" || echo "MISSING $f"; done
    note "collected $R: $(cd "$A/runs/$R" && ls poison.json tests.json 2>/dev/null | tr '\n' ' ')"
  fi
done
rm -rf "$TMPD"

# 4. per-run state file
{ echo "rsn-358u run state at $(now) (pass $MODE, kit $PIN)"
  for R in $ORDER; do
    if grep -q " $R/final.pt\$" "$SEAL"; then s="FINISHED $(grep " $R/final.pt\$" "$SEAL" | cut -c1-64) minutes $(line MIN $R)"
    elif [ "$(field $R train_proc)" != 0 ]; then s="TRAINING: $(line LAST $R)"
    elif [ "$(field $R log)$(field $R dir)" != "00" ]; then s="DIED (no final.pt, no process): $(line LAST $R)"
    else s="NOT STARTED"; fi
    if [ -s "$A/runs/$R/tests.json" ]; then e="evaluated"; elif [ "$(field $R eval_proc)" != 0 ]; then e="eval running"
    elif [ "$(field $R evallog)" = 1 ]; then e="EVAL DIED: eval log without tests.json"; else e="not evaluated"; fi
    echo "$R: $s; $e"
  done; } > "$A/runs/COLLECT-STATE.txt"
cat "$A/runs/COLLECT-STATE.txt"
[ "$MODE" = full ] || { echo "PASS-END collect $(now)"; exit 0; }

# 5. launch, only on an idle BensPC
busy=$(echo "$ST" | awk '$1=="PY"{print $2}'); gused=$(echo "$ST" | awk '$1=="GPU"{print $2}'); mk=$(echo "$ST" | sed -n "s/^MARKER //p" | head -1)
if [ "${busy:-1}" != 0 ] || [ "${gused:-99999}" -gt 700 ]; then echo "BUSY: ${busy:-?} python.exe, GPU ${gused:-?} MiB used on BensPC; nothing launched"; echo "PASS-END full $(now)"; exit 0; fi
case "$mk" in ""|*"queue job $JOB "*) ;; *) echo "BUSY: GPU-BUSY.txt names another job ($mk); nothing launched"; echo "PASS-END full $(now)"; exit 0;; esac
NS=""; for R in $ORDER; do [ "$(field $R log)$(field $R dir)" = "00" ] && NS="$NS $R"; done
if [ -n "$NS" ]; then
  k=0
  for R in $NS; do
    [ $k -ge 2 ] && {
      sleep 300; ST=$(rb state)
      set -- $(echo "$ST" | awk '$1=="GPU"{print $2, $3}'); used=${1:-99999}; tot=${2:-0}
      fr=$((tot - used)); echo "GPU after 5 min: used $used of $tot MiB, free $fr MiB"
      echo "$ST" | grep -E '^(RUN|LAST|PROCLINE)'
      note "GPU memory with $k runs: used $used of $tot MiB ($fr MiB free)"
      [ $fr -ge 5120 ] || { echo "under 5 GB free: no more launches this pass"; break; }
      [ $(( $(date +%s) - T0 )) -lt 3000 ] || { echo "pass time used up: no more launches"; break; }; }
    out=$(rb launch-train $R); echo "$out"; note "$out"; k=$((k+1))
    echo "$out" | grep -q "rc=0 pid=" || { echo "launch of $R failed; stopping launches"; break; }
  done
  sleep 60; ST=$(rb state); echo "$ST" | grep -E '^(GPU|RUN|LAST|PROCLINE)'
  for R in $NS; do [ "$(field $R log)" = 1 ] && note "$R: train_proc=$(field $R train_proc), last log line: $(line LAST $R)"; done
else
  ok=1; EV=""
  for R in $ORDER; do
    grep -q " $R/final.pt\$" "$SEAL" || { [ "$(field $R final)" = 1 ] && ok=0; continue; }
    [ "$(field $R tests)$(field $R evallog)" = "00" ] && EV="$EV $R=$(grep " $R/final.pt\$" "$SEAL" | cut -c1-64)"
  done
  if [ $ok = 0 ]; then echo "a finished run is not sealed yet; no evals this pass"
  elif [ -n "$EV" ]; then out=$(rb launch-evals $EV); echo "$out"; note "$out"; sleep 120; rb state | grep -E '^(GPU|RUN|PROCLINE)'
  else echo "ALL-TRAINED-AND-EVALUATED: nothing left to launch"; fi
fi
echo "PASS-END full $(now)"
