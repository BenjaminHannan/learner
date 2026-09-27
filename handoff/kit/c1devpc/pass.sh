#!/bin/bash
# c1-dev builder-free pass, run on the Mac from the watcher's worktree by the BASH-ONLY queue jobs 190-c1dev-benspc-bo-p*
# (Everyday chat thread, 2026-09-27). Replaces the LLM builder job k2-c1dev-benspc (Thread manager and Director: builders
# stall while holding the BensPC GPU). Modelled on the tested handoff/kit/y1tpc/pass.sh. Every pass is the same and
# state-driven, so a later pass picks up where the last one stopped:
#   tree     C:\Users\benja\lis301\work\c1dev\tree is made once from `git archive` of the pinned commit, then marked
#   checks   SEAL-2 (24 lines), the three models, and four selftests through the winnl2 wrapper, once (W/checks.txt)
#   launch   the chain (arms D, T, Q, L: remote/chain.cmd) starts once, detached through WMI, only on an idle BensPC with
#            4 GB free (the run writes about 2 MB; Ben's floor is 3 GB); a logger writes one nvidia-smi line a minute
#   running  report the arm and its log's age (a STALLED note after 30 minutes); nothing is ever stopped
#   done     copy the chats and logs back and write RESULTS-benspc.md (counts only; no verdict: the thread scores it)
# It never edits sealed code, never stops a process, never deletes anything on BensPC, never starts a second chain, never
# opens a TEST-ONLY panel (the practice chats are DEV), and writes no weights.
# Usage: pass.sh <kit-dir> <pinned-commit> <queue-job-name>          (bash 3.2 safe: macOS)
set -u
export LC_ALL=C COPYFILE_DISABLE=1
KD=$1; PIN=$2; JOB=${3:-?}
A=artifacts/claude-c1dev-20260927
R=$A/run
SSH=${SSHC1:-"ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o BatchMode=yes benspc"}
RB=${RBC1:-'"C:\Program Files\Git\bin\bash.exe" C:/Users/benja/lis301/work/c1dev/tree/handoff/kit/c1devpc/remote/boc1dev.sh'}
WIN=${WINC1:-'C:\Users\benja\lis301\work\c1dev\tree'}
S5=${S5C1:-300}; S1=${S1C1:-60}
NOTE=$R/RUN-NOTE-bo.md
ARMS="D T Q L"
WINNL="winnl2: Windows text-mode writes use Linux line endings (newline='')"
TWINB="twinb: the plain twin is Twin336b (enable_thinking=False)"
C1LINE="c1dev: talker = claude_e2e02d.Talker; W_PLACE02D=system; MAX_NEW02D=160; HIST_PAIRS=6; SLEEP02D=off; reader = none; reasoner = none"
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

echo "c1-dev BensPC pass, job $JOB, kit $PIN, start $(now)"
# 0. duplicates and lock
for b in main builder-outbox; do
  git cat-file -e "origin/$b:$A/RESULTS-benspc.md" 2>/dev/null && { echo "DUPLICATE: origin/$b has $A/RESULTS-benspc.md"; exit 0; }
  if git cat-file -e "origin/$b:$R" 2>/dev/null && ! git cat-file -e "origin/$b:$NOTE" 2>/dev/null; then
    echo "DUPLICATE: origin/$b has $R from another job (no RUN-NOTE-bo.md)"; exit 0; fi
done
[ -s "$A/RESULTS-benspc.md" ] && { echo "DONE: $A/RESULTS-benspc.md is already in this worktree"; exit 0; }
mkdir -p "$R"
[ -s "$NOTE" ] || git show "origin/builder-outbox:$NOTE" > "$NOTE" 2>/dev/null || : > "$NOTE"
[ -s "$NOTE" ] || echo "# c1-dev BensPC run notes (handoff/kit/c1devpc/pass.sh; UTC; one line per event)" > "$NOTE"
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
    git archive "$PIN" scripts design/v3/60-listener artifacts/claude-chatdev-20260926 "$A" \
      artifacts/claude-ch403-20260926/JUDGE-BRIEF.md handoff/kit/c1devpc | $SSH "tar -xf - -C $WIN" 2>&1 | tr -d '\r'
    ps="${PIPESTATUS[0]} ${PIPESTATUS[1]}"
    [ "$ps" = "0 0" ] || stop "STOP: extracting the tree failed (git archive, ssh tar: $ps); the next pass tries again"
    m=$(rb mark-tree "$PIN"); echo "$m"; note "tree $WIN made from $PIN ($P0): $m" ;;
  STARTED-NO-PIN) stop "STOP: $WIN has a chain but no pin mark; nothing done" ;;
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) stop "STOP: $WIN is marked with $P0, not $PIN; nothing done" ;;
  *) stop "STOP: no answer from BensPC ($P0)" ;;
esac

# 2. the kit in the tree must match the pinned commit
want=$(cd "$KD/handoff/kit/c1devpc/remote" && shasum -a 256 boc1dev.sh procs.ps1 launch.ps1 chain.cmd gpulog.cmd | awk '{print $1}' | tr '\n' ' ')
got=$(rb kithash | awk '{print $1}' | tr '\n' ' ')
[ "$want" = "$got" ] || { echo "want $want"; echo "got  $got"; stop "STOP: the kit on BensPC does not match $PIN"; }
echo "kit on BensPC matches $PIN"

# 3. state and checks
ST=$(rb state); echo "$ST"
echo "$ST" | grep -q '^END-STATE' || stop "STOP: no state from BensPC"
[ "$(sv PIN)" = "$PIN" ] || stop "STOP: the tree's pin is '$(sv PIN)'"
if [ "$(sv CHAIN)" = "started=0 done=0" ] && [ "$(sv CHECKS)" = "- -" ]; then
  c=$(rb checks); echo "$c"
  note "checks: $(echo "$c" | grep -c '^CHECK .* ok=1 ') of 4 selftests ok; $(echo "$c" | grep '^VERSIONS' | head -1); $(echo "$c" | grep '^GPUNAME' | head -1)"
  ST=$(rb state); echo "$ST" | grep '^CHECKS'
fi

# 4. the chain has not started: launch it once, on an idle BensPC only
if [ "$(sv CHAIN)" = "started=0 done=0" ]; then
  [ "$(sv SEAL)" = "24 24" ] || stop "SEAL-MISMATCH: SEAL-2 $(sv SEAL) (needs 24 of 24); nothing launched"
  [ "$(sv MODELS)" = "1 1 1" ] || stop "MODEL-MISSING: MiniCPM, Qwen, LFM folders $(sv MODELS) (needs 1 1 1); nothing launched"
  [ "$(sv CHECKS)" = "4 4" ] || stop "CHECK-FAIL: selftests $(sv CHECKS) (needs 4 of 4; W/checks.txt); nothing launched"
  set -- $(sv PY); py=${1:-1}
  set -- $(sv GPU); gused=${1:-99999}
  mk=$(sv MARKER)
  [ "$py" = 0 ] && [ "$gused" -le 700 ] || stop "BUSY: $py python.exe, GPU $gused MiB used on BensPC; nothing launched"
  case "$mk" in ""|*"queue job $JOB "*) ;; *) stop "BUSY: GPU-BUSY.txt names another job ($mk); nothing launched";; esac
  [ "$(sv DISK)" -ge 4 ] 2>/dev/null || stop "NO-DISK: C: has $(sv DISK) GB free and the gate is 4 GB (Ben's floor 3 GB); nothing launched"
  out=$(rb launch-chain); echo "$out"; note "$(echo "$out" | tr '\n' ';')"
  echo "$out" | grep -q '^LAUNCH chain .*rc=0 pid=' || stop "STOP: the chain launch did not report rc=0"
  sleep "$S5"; ST=$(rb state)
  echo "$ST" | grep -E '^(GPU|PY|PROCLINE|CHAIN|STEP|LAST|ROWS|GPULOG)'
  note "5 minutes after launch: GPU (MiB used, MiB total, W) $(sv GPU); python.exe $(sv PY); $(echo "$ST" | grep '^LAST' | tail -1)"
  echo "PASS-END $(now)"; exit 0
fi

# 5. the chain is running: report only
if [ "$(sv CHAIN)" = "started=1 done=0" ]; then
  set -- $(sv PY); allpy=${1:-1}; ours=${2:-0}
  if [ "$allpy" = 0 ]; then sleep "$S1"; ST=$(rb state); set -- $(sv PY); allpy=${1:-1}; ours=${2:-0}; fi
  cur=$(echo "$ST" | awk '$1=="STEP" && $3=="start" {s=$2} END {print s}')
  lage=$(echo "$ST" | awk -v s="log$cur" '$1=="LAST" && $2==s {sub("age=","",$3); sub("m","",$3); print $3}')
  if [ "$allpy" != 0 ] || [ "$(sv CHAIN)" != "started=1 done=0" ]; then
    [ "$(sv CHAIN)" = "started=1 done=0" ] && {
      note "RUNNING: arm ${cur:-?}, python.exe $allpy (c1dev $ours), log age ${lage:-?} min, GPU $(sv GPU); $(echo "$ST" | grep '^ROWS' | tr '\n' ' ')"
      [ "${lage:-0}" -ge 30 ] 2>/dev/null && note "STALLED? arm $cur's log has not changed for $lage minutes; nothing was stopped (the thread decides)"
      echo "PASS-END $(now)"; exit 0; }
  elif [ "${lage:-0}" -ge 10 ] 2>/dev/null || [ -z "$cur" ]; then
    DIED=1; note "DIED: chain.started without chain.done, no python.exe on two looks $S1 s apart, arm ${cur:-none}'s log ${lage:-?} min old; collecting what exists (a chain is never started twice)"
  else
    note "between arms: no python.exe, arm ${cur:-?}; nothing to do this pass"; echo "PASS-END $(now)"; exit 0
  fi
fi

# 6. the chain is done (or died): collect, write RESULTS-benspc.md
DIED=${DIED:-0}
MISS=""
for x in $ARMS; do
  for p in "outC1/chat_$x.jsonl:$R/chat_$x.jsonl" "W/log$x.txt:$R/log$x.txt" "W/log$x-retry.txt:$R/log$x-retry.txt"; do
    src=${p%%:*}; dst=${p#*:}
    [ -s "$dst" ] && continue
    r=$(getf "$src" "$dst"); [ "$r" = OK ] || MISS="$MISS $src"
  done
done
for p in "W/steps.txt:$R/steps.txt" "W/checks.txt:$R/checks.txt" "W/gpu_log.txt:$R/gpu_log.txt"; do
  src=${p%%:*}; dst=${p#*:}
  [ -s "$dst" ] && continue
  r=$(getf "$src" "$dst"); [ "$r" = OK ] || MISS="$MISS $src"
done
need=""; for x in $ARMS; do echo "$ST" | grep -q "^ROWS $x [1-9]" && need="$need outC1/chat_$x.jsonl"; done
lack=""; for f in $need; do case " $MISS " in *" $f "*) lack="$lack $f";; esac; done
if [ -n "$lack" ]; then
  tries=$(grep -c 'collect incomplete' "$NOTE" 2>/dev/null); tries=${tries:-0}
  if [ "$tries" -lt 2 ]; then stop "collect incomplete (try $((tries + 1)) of 3): missing$lack; the next pass tries again"; fi
  note "collect incomplete on the third try: missing$lack; writing RESULTS-benspc.md with what exists"
fi
[ -n "$MISS" ] && note "not on BensPC or not copied (a retry log exists only when an arm was retried):$MISS"
# counts, taken from the copied files; 336 rows and 60 conversations per arm is complete
full=0; rowsl=""
for x in $ARMS; do
  f=$R/chat_$x.jsonl
  n=$([ -f "$f" ] && grep -c . "$f" || echo 0); c=$([ -f "$f" ] && grep -o '"item_id": "[^"]*"' "$f" | sort -u | wc -l | tr -d ' ' || echo 0)
  [ "$n" = 336 ] && [ "$c" = 60 ] && full=$((full + 1))
  rowsl="$rowsl $x rows=$n conversations=$c;"
done
v1() {                                   # the old job's V1 lines, checked on the first log of each arm
  local f=$R/log$1.txt l1 l2 ok=1
  [ -f "$f" ] || { echo "V1 $1 no log"; return; }
  l1=$(tr -d '\r' < "$f" | sed -n 1p); l2=$(tr -d '\r' < "$f" | sed -n 2p)
  [ "$l1" = "$WINNL" ] || ok=0; [ "$l2" = "$TWINB" ] || ok=0
  if [ "$1" = D ]; then tr -d '\r' < "$f" | grep -qxF "$C1LINE" || ok=0; fi
  echo "V1 $1 $([ $ok = 1 ] && echo OK || echo FAIL)"
}
if [ "$DIED" = 1 ]; then status="DIED: the chain stopped without chain.done; $full of 4 arms complete"
elif [ "$full" = 4 ]; then status="COMPLETE: all 4 arms have 336 rows over 60 conversations"
else status="PARTIAL: $full of 4 arms complete;$rowsl"; fi
lastl() { [ -s "$1" ] && tr -d '\r' < "$1" | grep . | tail -"$2" | cut -c1-300 | sed 's/^/    /' || echo "    (no file)"; }
{
  echo "# c1-dev BensPC run record (handoff/kit/c1devpc/pass.sh, job $JOB, kit $PIN, written $(now))"
  echo
  echo "**$status.** Counts only, no verdict: the Everyday chat thread scores it (PLAN.md). Every line below is copied"
  echo "by the script, never retyped. The replies are in the chat files and are not quoted here."
  echo
  echo "## V1 (first two log lines; logD also has the c1dev settings line)"
  echo; for x in $ARMS; do echo "- $(v1 $x)"; done
  echo; echo "- c1dev line in logD: $(tr -d '\r' < "$R/logD.txt" 2>/dev/null | grep '^c1dev: ' | head -1)"
  echo
  echo "## Rows per arm (expected 336 rows, 60 conversations)"
  echo; echo "   $rowsl"
  echo
  echo "## Steps (W/steps.txt; BensPC local time)"
  echo; tr -d '\r' < "$R/steps.txt" 2>/dev/null | sed 's/^/    /'; echo
  echo "Minutes per arm: $(tr -d '\r' < "$R/steps.txt" 2>/dev/null | awk '{split($NF,a,":"); m=a[1]*60+a[2]+a[3]/60; if($2=="start") s[$1]=m; else if($1 in s) {d=m-s[$1]; if(d<0) d+=1440; printf "%s %.1f; ", $1, d}}')"
  echo
  echo "## Last lines of each log"
  for x in $ARMS; do echo "- log$x.txt:"; echo; lastl "$R/log$x.txt" 2; echo
    [ -s "$R/log$x-retry.txt" ] && { echo "- log$x-retry.txt:"; echo; lastl "$R/log$x-retry.txt" 2; echo; }; done
  echo "## Machine and files"
  echo "- $(grep '^VERSIONS' "$R/checks.txt" 2>/dev/null | head -1) (torch, CUDA, transformers, python)"
  echo "- $(grep '^GPUNAME' "$R/checks.txt" 2>/dev/null | head -1)"
  echo "- selftests: $(grep -c '^CHECK .* ok=1 ' "$R/checks.txt" 2>/dev/null) of 4 ok (checks.txt); SEAL-2 now: $(sv SEAL) (OK of lines)"
  echo "- GPU log (one line a minute: UTC, MiB used, MiB total, W): $(sv GPULOG)"
  echo "- CR bytes per chat file (expected 0):$(for x in $ARMS; do printf ' %s=%s' $x "$(tr -cd '\r' < "$R/chat_$x.jsonl" 2>/dev/null | wc -c | tr -d ' ')"; done)"
  echo
  echo "| file | bytes | sha256 |"
  echo "|---|---|---|"
  for f in $(find "$R" -type f ! -name 'RUN-NOTE-bo.md' 2>/dev/null | sort); do
    echo "| $f | $(wc -c < "$f" | tr -d ' ') | $(shasum -a 256 "$f" | cut -c1-64) |"; done
  echo
  echo "## Notes (RUN-NOTE-bo.md)"
  echo; sed 's/^/    /' "$NOTE"
} > "$A/RESULTS-benspc.md"
note "wrote RESULTS-benspc.md: $status"
echo "PASS-END $(now)"
