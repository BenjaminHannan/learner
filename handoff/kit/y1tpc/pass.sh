#!/bin/bash
# y1t builder-free pass, run on the Mac from the watcher's worktree by the BASH-ONLY queue jobs 180-y1t-benspc-bo-p*
# (Answering-from-memory thread, 2026-09-27). Replaces the LLM builder job handoff/held/benspc-y1t.md (its steps 1-7;
# Director 11:12 UTC). Modelled on the sleep research thread's tested handoff/kit/sleep358s/pass.sh. Every pass is the
# same and state-driven, so a later pass picks up where the last one stopped:
#   tree     C:\Users\benja\y1t\tree is made once from `git archive` of the pinned commit, then marked with the pin
#   checks   seals, items sha256 and the four selftests, once (W/checks.txt on BensPC)
#   launch   the chain (drafts, train, eval, eval_plain, h1_A, h1_B: remote/chain.cmd) starts once, detached through WMI,
#            only on an idle BensPC; a logger writes one nvidia-smi line a minute until the chain ends
#   running  report the step and its log's age (a STALLED note after 30 minutes); nothing is ever stopped
#   done     copy the results back, copy the model, write RESULTS-benspc.md (no verdict: the thread scores it)
# It never edits sealed code, never stops a process, never starts a second chain, never opens the TEST-ONLY panel or
# the H1 rows, and never pushes weights.
# Usage: pass.sh <kit-dir> <pinned-commit> <queue-job-name>          (bash 3.2 safe: macOS)
set -u
KD=$1; PIN=$2; JOB=${3:-?}
A=artifacts/claude-y1t-20260926
H=artifacts/claude-y1tH1-20260926
R=$A/run
RH=$H/run
D=$A/glm2/items
TRAIN_SHA=47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4
DEV_SHA=c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4
MINICPM=87179e5c1f455ef22e6223592d2d61351b525bfc
SSH=${SSHY1T:-"ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o BatchMode=yes benspc"}
RB=${RBY1T:-'"C:\Program Files\Git\bin\bash.exe" /c/Users/benja/y1t/tree/handoff/kit/y1tpc/remote/boy1t.sh'}
WIN=${WINY1T:-'C:\Users\benja\y1t\tree'}
MA=${MAY1T:-$HOME/y1t-adapter}
S5=${S5Y1T:-300}; S1=${S1Y1T:-60}
NOTE=$R/RUN-NOTE-bo.md
STEPS="drafts train eval eval_plain h1_A h1_B"
rb() { $SSH "$RB $*" < /dev/null 2>&1 | tr -d '\r'; }
now() { date -u +%FT%TZ; }
note() { echo "- $(now) $JOB: $*" >> "$NOTE"; echo "NOTE: $*"; }
sv() { echo "$ST" | awk -v k="$1" '$1==k {sub("^" k " ?",""); print; exit}'; }
stop() { note "$*"; echo "PASS-END $(now)"; exit 0; }
# copy one file of the BensPC tree ($1, forward slashes) to a local path ($2); prints OK or MISSING
getf() {
  local t; t=$(mktemp -d)
  $SSH "tar -cf - -C $WIN $1" < /dev/null 2>/dev/null | tar -x -C "$t" 2>/dev/null
  if [ -f "$t/$1" ]; then mkdir -p "$(dirname "$2")"; cp "$t/$1" "$2"; echo OK; else echo MISSING; fi
  rm -rf "$t"
}

echo "y1t BensPC pass, job $JOB, kit $PIN, start $(now)"
# 0. duplicates, data, lock
for b in main builder-outbox; do
  git cat-file -e "origin/$b:$R/RESULTS-benspc.md" 2>/dev/null && { echo "DUPLICATE: origin/$b has $R/RESULTS-benspc.md"; exit 0; }
  if git cat-file -e "origin/$b:$R" 2>/dev/null && ! git cat-file -e "origin/$b:$NOTE" 2>/dev/null; then
    echo "DUPLICATE: origin/$b has $R from another job (no RUN-NOTE-bo.md)"; exit 0; fi
done
[ -s "$R/RESULTS-benspc.md" ] && { echo "DONE: $R/RESULTS-benspc.md is already in this worktree"; exit 0; }
case "$(git show "origin/main:$A/gate/GATE-RESULT.md" 2>/dev/null | head -1)" in
  *GATE-PASS*) ;; *) echo "NO-DATA: origin/main:$A/gate/GATE-RESULT.md does not say GATE-PASS"; exit 0;; esac
t=$(git show "$PIN:$D/items_train.jsonl" 2>/dev/null | shasum -a 256 | cut -c1-64)
d=$(git show "$PIN:$D/items_dev.jsonl" 2>/dev/null | shasum -a 256 | cut -c1-64)
[ "$t" = $TRAIN_SHA ] && [ "$d" = $DEV_SHA ] || { echo "NO-DATA: the items at $PIN have sha256 $t / $d"; exit 0; }
mkdir -p "$R" "$RH"
[ -s "$NOTE" ] || git show "origin/builder-outbox:$NOTE" > "$NOTE" 2>/dev/null || : > "$NOTE"
[ -s "$NOTE" ] || echo "# y1t BensPC run notes (handoff/kit/y1tpc/pass.sh; UTC; one line per event)" > "$NOTE"
# one pass at a time; a lock older than 80 minutes is left from a pass the watcher's 75-minute alarm ended
[ -d "$R/.pass-lock" ] && [ -n "$(find "$R/.pass-lock" -maxdepth 0 -mmin +80 2>/dev/null)" ] && rmdir "$R/.pass-lock" && note "removed a lock older than 80 minutes"
mkdir "$R/.pass-lock" 2>/dev/null || { echo "LOCKED: another pass holds $R/.pass-lock; stopping"; exit 0; }
trap 'rmdir "$R/.pass-lock" 2>/dev/null' EXIT
note "pass start"

# 1. the tree on BensPC (made once; an unmarked folder is re-extracted only if the chain never started)
P0=$($SSH "if exist $WIN\\W\\tree-pin.txt (type $WIN\\W\\tree-pin.txt) else if exist $WIN\\W\\chain.started (echo STARTED-NO-PIN) else if exist $WIN (echo NO-PIN) else (echo NO-TREE)" < /dev/null 2>&1 | tr -d '\r' | grep . | tail -1)
echo "tree: $P0"
case "$P0" in
  "$PIN") ;;
  NO-TREE|NO-PIN)
    [ "$P0" = NO-TREE ] && $SSH "mkdir $WIN" < /dev/null 2>&1 | tr -d '\r'
    git archive "$PIN" scripts artifacts/claude-e2e331-dev-20260924 artifacts/claude-y1t-20260926 \
      artifacts/claude-spare401-20260926/panel/turns.jsonl artifacts/claude-spare401-20260926/SEAL-spare401.sha256.txt \
      handoff/kit/y1tpc | $SSH "tar -xf - -C $WIN" 2>&1 | tr -d '\r'
    ps="${PIPESTATUS[0]} ${PIPESTATUS[1]}"
    [ "$ps" = "0 0" ] || stop "STOP: extracting the tree failed (git archive, ssh tar: $ps); the next pass tries again"
    m=$(rb mark-tree "$PIN"); echo "$m"; note "tree $WIN made from $PIN ($P0): $m" ;;
  STARTED-NO-PIN) stop "STOP: $WIN has a chain but no pin mark; nothing done" ;;
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) stop "STOP: $WIN is marked with $P0, not $PIN; nothing done" ;;
  *) stop "STOP: no answer from BensPC ($P0)" ;;
esac

# 2. the kit in the tree must match the pinned commit
want=$(cd "$KD/handoff/kit/y1tpc/remote" && shasum -a 256 boy1t.sh procs.ps1 launch.ps1 chain.cmd gpulog.cmd | awk '{print $1}' | tr '\n' ' ')
got=$(rb kithash | awk '{print $1}' | tr '\n' ' ')
[ "$want" = "$got" ] || { echo "want $want"; echo "got  $got"; stop "STOP: the kit on BensPC does not match $PIN"; }
echo "kit on BensPC matches $PIN"

# 3. state and checks
ST=$(rb state); echo "$ST"
echo "$ST" | grep -q '^END-STATE' || stop "STOP: no state from BensPC"
[ "$(sv PIN)" = "$PIN" ] || stop "STOP: the tree's pin is '$(sv PIN)'"
if [ "$(sv CHAIN)" = "started=0 done=0" ] && [ "$(sv CHECKS)" = "- -" ]; then
  c=$(rb checks); echo "$c"
  note "checks: $(echo "$c" | grep -c '^CHECK .* rc=0 ') of 4 selftests ok; $(echo "$c" | grep '^VERSIONS' | head -1); $(echo "$c" | grep '^GPUNAME' | head -1)"
  ST=$(rb state); echo "$ST" | grep '^CHECKS'
fi

# 4. the chain has not started: launch it once, on an idle BensPC only
if [ "$(sv CHAIN)" = "started=0 done=0" ]; then
  [ "$(sv SEALR)" = "16 16" ] || stop "SEAL-FAIL: SEAL-y1t-rental $(sv SEALR) (needs 16 of 16); nothing launched"
  [ "$(sv SEALH)" = "1 1" ] || stop "SEAL-FAIL: SEAL-y1tH1-runner $(sv SEALH) (needs 1 of 1); nothing launched"
  [ "$(sv SEALP)" = "1 1" ] || stop "SEAL-FAIL: the spare401 panel line $(sv SEALP) (needs 1 of 1); nothing launched"
  [ "$(sv ITEMS)" = "$TRAIN_SHA $DEV_SHA" ] || stop "NO-DATA: the tree's items are $(sv ITEMS); nothing launched"
  [ "$(sv CHECKS)" = "4 4" ] || stop "CHECK-FAIL: selftests $(sv CHECKS) (needs 4 of 4; W/checks.txt); nothing launched"
  set -- $(sv PY); py=${1:-1}
  set -- $(sv GPU); gused=${1:-99999}
  mk=$(sv MARKER)
  [ "$py" = 0 ] && [ "$gused" -le 700 ] || stop "BUSY: $py python.exe, GPU $gused MiB used on BensPC; nothing launched"
  case "$mk" in ""|*"queue job $JOB "*) ;; *) stop "BUSY: GPU-BUSY.txt names another job ($mk); nothing launched";; esac
  [ "$(sv DISK)" -ge 10 ] 2>/dev/null || stop "NO-DISK: C: has $(sv DISK) GB free and the run needs 10 GB; nothing launched"
  out=$(rb launch-chain); echo "$out"; note "$(echo "$out" | tr '\n' ';')"
  echo "$out" | grep -q '^LAUNCH chain .*rc=0 pid=' || stop "STOP: the chain launch did not report rc=0"
  sleep "$S5"; ST=$(rb state)
  echo "$ST" | grep -E '^(GPU|PY|PROCLINE|CHAIN|STEP|LAST|GPULOG)'
  note "5 minutes after launch: GPU (MiB used, MiB total, W) $(sv GPU); python.exe $(sv PY); $(echo "$ST" | grep '^LAST' | tail -1)"
  echo "PASS-END $(now)"; exit 0
fi

# 5. the chain is running: report only
if [ "$(sv CHAIN)" = "started=1 done=0" ]; then
  # "ours" counts y1t python.exe; any python.exe that is not recognisably ours also blocks the DIED call
  set -- $(sv PY); allpy=${1:-1}; ours=${2:-0}
  if [ "$allpy" = 0 ]; then sleep "$S1"; ST=$(rb state); set -- $(sv PY); allpy=${1:-1}; ours=${2:-0}; fi
  cur=$(echo "$ST" | awk '$1=="STEP" && $3=="start" {s=$2} END {print s}')
  lage=$(echo "$ST" | awk -v s="$cur" '$1=="LAST" && $2==s {sub("age=","",$3); sub("m","",$3); print $3}')
  if [ "$allpy" != 0 ] || [ "$(sv CHAIN)" != "started=1 done=0" ]; then
    [ "$(sv CHAIN)" = "started=1 done=0" ] && {
      note "RUNNING: step ${cur:-?}, python.exe $allpy (y1t $ours), log age ${lage:-?} min, GPU $(sv GPU); $(echo "$ST" | grep "^LAST ${cur:-none} " | cut -c1-200)"
      [ "${lage:-0}" -ge 30 ] 2>/dev/null && note "STALLED? step $cur's log has not changed for $lage minutes; nothing was stopped (the thread decides)"
      echo "PASS-END $(now)"; exit 0; }
  elif [ "${lage:-0}" -ge 10 ] 2>/dev/null || [ -z "$cur" ]; then
    DIED=1; note "DIED: chain.started without chain.done, no python.exe at all on two looks $S1 s apart, step ${cur:-none}'s log ${lage:-?} min old; collecting what exists (a chain is never started twice)"
  else
    note "between steps: no python.exe, step ${cur:-?}; nothing to do this pass"; echo "PASS-END $(now)"; exit 0
  fi
fi

# 6. the chain is done (or died): collect, copy the model, write RESULTS-benspc.md
DIED=${DIED:-0}
MISS=""
for p in "$D/drafts.jsonl:$R/drafts.jsonl" "$D/train.jsonl:$R/train.jsonl" "$D/dev.jsonl:$R/dev.jsonl" \
         "$D/drafts_summary.json:$R/drafts_summary.json" "tr/train398r.json:$R/train398r.json" \
         "eval/y1g_rows.jsonl:$R/eval/y1g_rows.jsonl" "eval/y1g_summary.json:$R/eval/y1g_summary.json" \
         "eval_plain/y1g_rows.jsonl:$R/eval_plain/y1g_rows.jsonl" "eval_plain/y1g_summary.json:$R/eval_plain/y1g_summary.json" \
         "W/drafts_log.txt:$R/drafts_log.txt" "W/train_log.txt:$R/train_log.txt" "W/eval_log.txt:$R/eval_log.txt" \
         "W/eval_plain_log.txt:$R/eval_plain_log.txt" "W/steps.txt:$R/steps.txt" "W/checks.txt:$R/checks.txt" \
         "W/gpu_log.txt:$R/gpu_log.txt" \
         "h1/rows_A.jsonl:$RH/rows_A.jsonl" "h1/rows_B.jsonl:$RH/rows_B.jsonl" "W/h1_A_log.txt:$RH/h1_A_log.txt" \
         "W/h1_B_log.txt:$RH/h1_B_log.txt"; do
  src=${p%%:*}; dst=${p#*:}
  [ -s "$dst" ] && continue
  r=$(getf "$src" "$dst"); [ "$r" = OK ] || MISS="$MISS $src"
done
# steps that ended rc=0 must have their files; anything else missing is reported, not waited for
okst=$(echo "$ST" | awk '$1=="STEP" && $3 ~ /^rc=0$/ {printf "%s ", $2}')
need=""
for s in $okst; do case $s in
  drafts) need="$need $D/drafts.jsonl $D/train.jsonl $D/dev.jsonl $D/drafts_summary.json";;
  train) need="$need tr/train398r.json";;
  eval) need="$need eval/y1g_summary.json";;
  eval_plain) need="$need eval_plain/y1g_summary.json";;
  h1_A) need="$need h1/rows_A.jsonl";;
  h1_B) need="$need h1/rows_B.jsonl";;
esac; done
lack=""; for f in $need; do case " $MISS " in *" $f "*) lack="$lack $f";; esac; done
if [ -n "$lack" ]; then
  tries=$(grep -c 'collect incomplete' "$NOTE" 2>/dev/null); tries=${tries:-0}
  if [ "$tries" -lt 2 ]; then stop "collect incomplete (try $((tries + 1)) of 3): missing$lack; the next pass tries again"; fi
  note "collect incomplete on the third try: missing$lack; writing RESULTS-benspc.md with what exists"
fi
[ -n "$MISS" ] && note "not on BensPC or not copied:$MISS"
# the watcher pushes only files that `find -size -5M` matches, which (rounding up to whole MiB) means 4 MiB or less:
# a bigger file is pushed as a gzip copy, split into 3,500 KiB parts if the gzip copy is still too big
for f in $(find "$R" "$RH" -type f -size +3900k ! -name '*.gz' ! -name '*.gz.part-*' 2>/dev/null); do
  [ -s "$f.gz" ] || [ -s "$f.gz.part-aa" ] && continue
  gzip -9 -c "$f" > "$f.gz"
  if [ "$(wc -c < "$f.gz" | tr -d ' ')" -gt 3993600 ]; then
    split -b 3500k "$f.gz" "$f.gz.part-" && rm -f "$f.gz"
    note "$f is $(wc -c < "$f" | tr -d ' ') bytes: pushed as $(ls "$f.gz.part-"* | wc -l | tr -d ' ') parts $f.gz.part-* (join with cat, then gunzip)"
  else note "$f is $(wc -c < "$f" | tr -d ' ') bytes: pushed as $f.gz ($(wc -c < "$f.gz" | tr -d ' ') bytes)"; fi
done
# the model: BensPC keeps it in premonition-models/y1t; the Mac gets the adapter only (never pushed)
ad=$(sv ADAPTER | awk '{print $1}')
if [ -n "$ad" ]; then
  cm=$(rb copy-model); echo "$cm"; note "BensPC: $(echo "$cm" | tr '\n' ';')"
  mkdir -p "$MA"
  if [ "$(shasum -a 256 "$MA/adapter398r.pt" 2>/dev/null | cut -c1-64)" != "$ad" ]; then
    t=$(mktemp -d); $SSH "tar -cf - -C $WIN\\tr adapter398r.pt" < /dev/null 2>/dev/null | tar -x -C "$t" 2>/dev/null
    [ -f "$t/adapter398r.pt" ] && cp "$t/adapter398r.pt" "$MA/adapter398r.pt"; rm -rf "$t"
  fi
  mac=$(shasum -a 256 "$MA/adapter398r.pt" 2>/dev/null | cut -c1-64)
  [ "$mac" = "$ad" ] && note "Mac copy ~/y1t-adapter/adapter398r.pt sha256 matches $ad" || note "Mac copy of the adapter: sha256 '$mac' does not match $ad"
fi
nst=$(echo "$ST" | awk '$1=="STEP" && $3 ~ /^rc=/' | wc -l | tr -d ' ')
nok=$(echo "$ST" | awk '$1=="STEP" && $3=="rc=0"' | wc -l | tr -d ' ')
if [ "$DIED" = 1 ]; then status="DIED: the chain stopped without chain.done; $nok of 6 steps ended rc=0"
elif [ "$nok" = 6 ]; then status="COMPLETE: all 6 steps ended rc=0"
else status="PARTIAL: $nok of 6 steps ended rc=0; $(echo "$ST" | awk '$1=="STEP" && $3 ~ /^rc=/ && $3!="rc=0" {print "step " $2 " ended " $3}' | head -1)"; fi
lastl() { [ -s "$1" ] && tr -d '\r' < "$1" | grep . | tail -"$2" | cut -c1-600 | sed 's/^/    /' || echo "    (no file)"; }
{
  echo "# y1t BensPC run record (handoff/kit/y1tpc/pass.sh, job $JOB, kit $PIN, written $(now))"
  echo
  echo "**$status.** No verdict here: the thread scores the sealed DEV marks in VERIFY-y1t.md. Every line below is"
  echo "copied by the script, never retyped. The H1 rows are in $RH (never opened by this job)."
  echo
  echo "## Steps (W/steps.txt; BensPC local time)"
  echo; tr -d '\r' < "$R/steps.txt" 2>/dev/null | sed 's/^/    /'; echo
  echo "Minutes per step: $(tr -d '\r' < "$R/steps.txt" 2>/dev/null | awk '{split($NF,a,":"); m=a[1]*60+a[2]+a[3]/60; if($2=="start") s[$1]=m; else if($1 in s) {d=m-s[$1]; if(d<0) d+=1440; printf "%s %.1f; ", $1, d}}')"
  echo
  echo "## Last lines"
  for f in drafts_log train_log; do echo "- $f.txt:"; echo; lastl "$R/$f.txt" 1; echo; done
  for f in eval_log eval_plain_log; do echo "- $f.txt (last two):"; echo; lastl "$R/$f.txt" 2; echo; done
  for f in h1_A_log h1_B_log; do echo "- $f.txt:"; echo; lastl "$RH/$f.txt" 1; echo; done
  echo "## Machine and files"
  echo "- $(grep '^VERSIONS' "$R/checks.txt" 2>/dev/null | head -1) (torch, CUDA, transformers)"
  echo "- $(grep '^GPUNAME' "$R/checks.txt" 2>/dev/null | head -1)"
  echo "- MiniCPM5-1B snapshot $MINICPM (remote/chain.cmd's BASE); Python C:\\Users\\benja\\lis300\\venv"
  echo "- items: $(sv ITEMS) (train, dev; both match GATE-RESULT.md)"
  echo "- adapter sha256 on BensPC tr/: ${ad:-none}; Mac copy: ${mac:-none}"
  echo "- GPU log (one line a minute: UTC, MiB used, MiB total, W): $(sv GPULOG)"
  echo "- selftests: $(grep -c '^CHECK .* rc=0 ' "$R/checks.txt" 2>/dev/null) of 4 ok (checks.txt)"
  echo
  echo "| file | bytes | sha256 |"
  echo "|---|---|---|"
  for f in $(find "$R" "$RH" -type f ! -name 'RESULTS-benspc.md' ! -name 'RUN-NOTE-bo.md' 2>/dev/null | sort); do
    echo "| $f | $(wc -c < "$f" | tr -d ' ') | $(shasum -a 256 "$f" | cut -c1-64) |"; done
  echo
  echo "## Notes (RUN-NOTE-bo.md)"
  echo; sed 's/^/    /' "$NOTE"
} > "$R/RESULTS-benspc.md"
note "wrote RESULTS-benspc.md: $status"
echo "PASS-END $(now)"
