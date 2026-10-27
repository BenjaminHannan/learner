#!/bin/bash
# rd-378g builder-free pass, run on the Mac from the watcher's worktree by the BASH-ONLY queue jobs *-rd378g-benspc-bo-p*
# (Trustworthy notes thread, 2026-09-27). Replaces the LLM-builder job handoff/held/rd378g-pc2-q.md (Thread manager
# 12:0x UTC; the Director's y1t call 11:12 UTC). Modelled on the Answering-from-memory thread's handoff/kit/y1tpc/pass.sh
# (itself from the sleep research thread's tested kit). Every pass is the same and state-driven, so a later pass
# picks up where the last one stopped:
#   tree     C:\Users\benja\rd378g2\tree is made once from `git archive` of the pinned commit, then marked with the pin
#   checks   seals, selftests, MiniLM snapshot and LoCoMo data hash, once (W/checks.txt on BensPC)
#   R        find the rd-378 writer (R) on BensPC; if absent, copy it from the Mac only when C: keeps >= 9 GB free
#            before the copy (Ben's 3 GB floor after R's ~2.1 GB and G's ~2.3 GB); otherwise G5 uses its sealed fallback
#   launch   the chain (remote/chain.cmd) starts once, detached through WMI, only on an idle BensPC with >= 6 GB free;
#            a logger writes one nvidia-smi line a minute until the chain ends
#   running  report the step and its log's age (a STALLED note after 30 minutes); nothing is ever stopped
#   done     copy the results back (LoCoMo files only to ~/rd378g-private, outside git), copy G's adapter, write
#            RESULTS-benspc.md (no verdict: the thread scores it)
# It never edits sealed code, never stops or deletes anything on BensPC, never starts a second chain, never pushes
# LoCoMo text or weights.
# Usage: pass.sh <kit-dir> <pinned-commit> <queue-job-name>          (bash 3.2 safe: macOS)
set -u
export LC_ALL=C COPYFILE_DISABLE=1
KD=$1; PIN=$2; JOB=${3:-?}
N=artifacts/claude-rd378g-20260926
RB=$N/benspc
NOTE=$RB/RUN-NOTE-bo.md
R_SHA=${RSHA378G:-dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510}
SSH=${SSH378G:-"ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o BatchMode=yes benspc"}
RBS=${RB378G:-'"C:\Program Files\Git\bin\bash.exe" C:/Users/benja/rd378g2/tree/handoff/kit/rd378gpc/remote/bo378g.sh'}
WIN=${WIN378G:-'C:\Users\benja\rd378g2\tree'}
PVW=${PVW378G:-'C:\Users\benja\rd378g2-private'}
MDW=${MDW378G:-'C:\Users\benja\premonition-models'}
MR=${MR378G:-$HOME/premonition-models/rd378-notes-merged}
MA=${MA378G:-$HOME/premonition-models/rd378g-adapter}
MP=${MP378G:-$HOME/rd378g-private}
S5=${S5378G:-300}; S1=${S1378G:-60}
STEPS="dialogs train devcheck write59 score whenoff g5G g5R"
rb() { $SSH "$RBS $*" < /dev/null 2>&1 | tr -d '\r'; }
now() { date -u +%FT%TZ; }
note() { echo "- $(now) $JOB: $*" >> "$NOTE"; echo "NOTE: $*"; }
sv() { echo "$ST" | awk -v k="$1" '$1==k {sub("^" k " ?",""); print; exit}'; }
stop() { note "$*"; echo "PASS-END $(now)"; exit 0; }
# copy one file from a BensPC folder ($1 = Windows folder, $2 = path inside it, forward slashes) to a local path ($3)
getf() {
  local t; t=$(mktemp -d)
  $SSH "tar -cf - -C $1 $2" < /dev/null 2>/dev/null | tar -x -C "$t" 2>/dev/null
  if [ -f "$t/$2" ]; then mkdir -p "$(dirname "$3")"; cp "$t/$2" "$3"; echo OK; else echo MISSING; fi
  rm -rf "$t"
}

echo "rd-378g BensPC pass, job $JOB, kit $PIN, start $(now)"
# 0. duplicates, data, lock
for b in main builder-outbox; do
  git cat-file -e "origin/$b:$RB/RESULTS-benspc.md" 2>/dev/null && { echo "DUPLICATE: origin/$b has $RB/RESULTS-benspc.md"; exit 0; }
  git cat-file -e "origin/$b:$N/RESULTS.md" 2>/dev/null && { echo "DUPLICATE: origin/$b has $N/RESULTS.md"; exit 0; }
done
[ -s "$RB/RESULTS-benspc.md" ] && { echo "DONE: $RB/RESULTS-benspc.md is already in this worktree"; exit 0; }
git cat-file -e "$PIN:$N/ADDENDUM-L.md" 2>/dev/null || { echo "NO-SEAL: $PIN has no $N/ADDENDUM-L.md"; exit 0; }
[ "$(git show "$PIN:$N/SEAL-B.sha256.txt" 2>/dev/null | grep -c .)" = 8 ] || { echo "NO-DATA: $PIN has no 8-line SEAL-B"; exit 0; }
mkdir -p "$RB"
[ -s "$NOTE" ] || git show "origin/builder-outbox:$NOTE" > "$NOTE" 2>/dev/null || : > "$NOTE"
[ -s "$NOTE" ] || echo "# rd-378g BensPC run notes (handoff/kit/rd378gpc/pass.sh; UTC; one line per event)" > "$NOTE"
[ -d "$RB/.pass-lock" ] && [ -n "$(find "$RB/.pass-lock" -maxdepth 0 -mmin +80 2>/dev/null)" ] && rmdir "$RB/.pass-lock" && note "removed a lock older than 80 minutes"
mkdir "$RB/.pass-lock" 2>/dev/null || { echo "LOCKED: another pass holds $RB/.pass-lock; stopping"; exit 0; }
trap 'rmdir "$RB/.pass-lock" 2>/dev/null' EXIT
note "pass start"

# 1. the tree on BensPC (made once; an unmarked folder is re-extracted only if the chain never started)
P0=$($SSH "if exist $WIN\\W\\tree-pin.txt (type $WIN\\W\\tree-pin.txt) else if exist $WIN\\W\\chain.started (echo STARTED-NO-PIN) else if exist $WIN (echo NO-PIN) else (echo NO-TREE)" < /dev/null 2>&1 | tr -d '\r' | grep . | tail -1)
echo "tree: $P0"
case "$P0" in
  "$PIN") ;;
  NO-TREE|NO-PIN)
    [ "$P0" = NO-TREE ] && $SSH "mkdir $WIN" < /dev/null 2>&1 | tr -d '\r'
    git archive "$PIN" scripts "$N" artifacts/claude-rd378u-20260926/notes_confirm.json \
      artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md handoff/kit/rd378gpc | $SSH "tar -xf - -C $WIN" 2>&1 | tr -d '\r'
    ps="${PIPESTATUS[0]} ${PIPESTATUS[1]}"
    [ "$ps" = "0 0" ] || stop "STOP: extracting the tree failed (git archive, ssh tar: $ps); the next pass tries again"
    m=$(rb mark-tree "$PIN"); echo "$m"; note "tree $WIN made from $PIN ($P0): $m" ;;
  STARTED-NO-PIN) stop "STOP: $WIN has a chain but no pin mark; nothing done" ;;
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) stop "STOP: $WIN is marked with $P0, not $PIN; nothing done" ;;
  *) stop "STOP: no answer from BensPC ($P0)" ;;
esac

# 2. the kit in the tree must match the pinned commit
want=$(cd "$KD/handoff/kit/rd378gpc/remote" && shasum -a 256 bo378g.sh procs.ps1 launch.ps1 chain.cmd gpulog.cmd check378g.py | awk '{print $1}' | tr '\n' ' ')
got=$(rb kithash | awk '{print $1}' | tr '\n' ' ')
[ "$want" = "$got" ] || { echo "want $want"; echo "got  $got"; stop "STOP: the kit on BensPC does not match $PIN"; }
echo "kit on BensPC matches $PIN"

# 3. state and checks
ST=$(rb state); echo "$ST" | grep -v '^PROCLINE'
echo "$ST" | grep -q '^END-STATE' || stop "STOP: no state from BensPC"
[ "$(sv PIN)" = "$PIN" ] || stop "STOP: the tree's pin is '$(sv PIN)'"
if [ "$(sv CHAIN)" = "started=0 done=0" ] && [ "$(sv CHECKS)" = "- -" ]; then
  c=$(rb checks); echo "$c"
  note "checks: $(echo "$c" | grep -c '^CHECK .* rc=0 ') of 4 selftests ok; $(echo "$c" | grep -E '^(VERSIONS|GPUNAME|MINILM|DATA|BASESHA)' | tr '\n' ';')"
  ST=$(rb state); echo "$ST" | grep -E '^(CHECKS|MINILM|DATA)'
fi

# 4. the chain has not started: find R (copy it only with room), then launch once on an idle BensPC
if [ "$(sv CHAIN)" = "started=0 done=0" ]; then
  [ "$(sv SEALB)" = "8 8" ] || stop "SEAL-FAIL: SEAL-B $(sv SEALB) (needs 8 of 8); nothing launched"
  [ "$(sv SEALK)" = "6 6" ] || stop "SEAL-FAIL: SEAL-ADD-K $(sv SEALK) (needs 6 of 6); nothing launched"
  [ "$(sv SEALAB)" = "5 5" ] || stop "SEAL-FAIL: SEAL-ADD-A + B $(sv SEALAB) (needs 5 of 5); nothing launched"
  case "$(sv SEAL0)" in "13 1 scripts/claude_lis300_train.py"|"13 1 scripts/claude_lis300_train.py "*) ;; *) stop "SEAL-FAIL: SEAL.sha256.txt '$(sv SEAL0)' (needs 13 OK and only scripts/claude_lis300_train.py FAILED, which ADDENDUM-A replaces); nothing launched";; esac
  [ "$(sv CHECKS)" = "4 4" ] || stop "CHECK-FAIL: selftests $(sv CHECKS) (needs 4 of 4; W/checks.txt); nothing launched"
  echo "$ST" | grep -q '^MINILM ok' || stop "CHECK-FAIL: MiniLM snapshot ($(echo "$ST" | grep '^MINILM')); nothing launched"
  echo "$ST" | grep -q '^DATA ok' || stop "NO-DATA: LoCoMo file hash ($(echo "$ST" | grep '^DATA')); nothing launched"
  set -- $(sv PY); py=${1:-1}
  set -- $(sv GPU); gused=${1:-99999}
  mk=$(sv MARKER)
  [ "$py" = 0 ] && [ "$gused" -le 700 ] || stop "BUSY: $py python.exe, GPU $gused MiB used on BensPC; nothing launched"
  case "$mk" in ""|*"queue job $JOB "*) ;; *) stop "BUSY: GPU-BUSY.txt names another job ($mk); nothing launched";; esac
  if [ -z "$(sv RPATH)" ]; then
    fr=$(rb find-r); echo "$fr"; note "R on BensPC: $(echo "$fr" | tr '\n' ';')"
    if ! echo "$fr" | grep -q '^RFOUND'; then
      if [ "$(sv DISK)" -ge 9 ] 2>/dev/null && [ "$(shasum -a 256 "$MR/model.safetensors" 2>/dev/null | cut -c1-64)" = "$R_SHA" ]; then
        $SSH "if not exist $MDW mkdir $MDW" < /dev/null 2>&1 | tr -d '\r'
        tar -cf - -C "$(dirname "$MR")" "$(basename "$MR")" | $SSH "tar -xf - -C $MDW" 2>&1 | tr -d '\r'
        fr=$(rb find-r); echo "$fr"; note "copied R from the Mac ($MR, C: had $(sv DISK) GB free): $(echo "$fr" | tr '\n' ';')"
      else
        note "R-SKIPPED: not on BensPC; Mac copy $([ -f "$MR/model.safetensors" ] && echo present || echo absent); C: has $(sv DISK) GB free (a copy needs >= 9 GB to keep Ben's 3 GB floor); G5 uses ADDENDUM-K's 57% fallback"
      fi
    fi
    ST=$(rb state)
  fi
  [ "$(sv DISK)" -ge 6 ] 2>/dev/null || stop "NO-DISK: C: has $(sv DISK) GB free and the run needs 6 GB (G's ~2.3 GB plus Ben's 3 GB floor); nothing launched"
  out=$(rb launch-chain); echo "$out"; note "$(echo "$out" | tr '\n' ';') R path: $(sv RPATH)"
  echo "$out" | grep -q '^LAUNCH chain .*rc=0 pid=' || stop "STOP: the chain launch did not report rc=0"
  sleep "$S5"; ST=$(rb state)
  echo "$ST" | grep -E '^(GPU|PY|CHAIN|STEP|LAST|GPULOG|DISK)'
  note "5 minutes after launch: GPU (MiB used, MiB total, W) $(sv GPU); python.exe $(sv PY); disk $(sv DISK) GB; $(echo "$ST" | grep '^LAST' | tail -1)"
  echo "PASS-END $(now)"; exit 0
fi

# 5. the chain is running: report only
if [ "$(sv CHAIN)" = "started=1 done=0" ]; then
  set -- $(sv PY); allpy=${1:-1}; ours=${2:-0}
  if [ "$allpy" = 0 ]; then sleep "$S1"; ST=$(rb state); set -- $(sv PY); allpy=${1:-1}; ours=${2:-0}; fi
  cur=$(echo "$ST" | awk '$1=="STEP" && $3=="start" {s=$2} END {print s}')
  lage=$(echo "$ST" | awk -v s="$cur" '$1=="LAST" && $2==s {sub("age=","",$3); sub("m","",$3); print $3}')
  if [ "$allpy" != 0 ] || [ "$(sv CHAIN)" != "started=1 done=0" ]; then
    [ "$(sv CHAIN)" = "started=1 done=0" ] && {
      note "RUNNING: step ${cur:-?}, python.exe $allpy (ours $ours), log age ${lage:-?} min, GPU $(sv GPU), disk $(sv DISK) GB; $(echo "$ST" | grep "^LAST ${cur:-none} " | cut -c1-200)"
      [ "${lage:-0}" -ge 30 ] 2>/dev/null && note "STALLED? step $cur's log has not changed for $lage minutes; nothing was stopped (the thread decides)"
      echo "PASS-END $(now)"; exit 0; }
  elif [ "${lage:-0}" -ge 10 ] 2>/dev/null || [ -z "$cur" ]; then
    DIED=1; note "DIED: chain.started without chain.done, no python.exe at all on two looks $S1 s apart, step ${cur:-none}'s log ${lage:-?} min old; collecting what exists (a chain is never started twice)"
  else
    note "between steps: no python.exe, step ${cur:-?}; nothing to do this pass"; echo "PASS-END $(now)"; exit 0
  fi
fi

# 6. the chain is done (or died): collect, copy G's adapter, write RESULTS-benspc.md
DIED=${DIED:-0}
GD=$(sv GDIR); GD=${GD:-W/g}
MISS=""
for p in "$WIN|$GD/summary.json|$RB/train/summary.json" "$WIN|$GD/train_log.jsonl|$RB/train/train_log.jsonl" \
         "$WIN|W/gdev.jsonl|$RB/train/gdev.jsonl" "$WIN|W/g5_G.jsonl|$N/g5/notes_G.jsonl" "$WIN|W/g5_R.jsonl|$N/g5/notes_R.jsonl" \
         "$WIN|W/steps.txt|$RB/steps.txt" "$WIN|W/checks.txt|$RB/checks.txt" "$WIN|W/gpu_log.txt|$RB/gpu_log.txt" \
         "$WIN|W/r-path.txt|$RB/r-path.txt" \
         "$PVW|outg/notes_confirm.json|$RB/notes_confirm.json" "$PVW|outg/ranked_turns.jsonl|$RB/ranked_turns.jsonl" \
         "$PVW|outg_whenoff/notes_confirm.json|$RB/notes_confirm_whenoff.json" \
         "$PVW|g59.jsonl|$MP/g59.jsonl" "$PVW|dialogs59.jsonl|$MP/dialogs59.jsonl" "$PVW|outg/per_question.jsonl|$MP/per_question.jsonl"; do
  w=${p%%|*}; r=${p#*|}; src=${r%%|*}; dst=${r#*|}
  [ -s "$dst" ] && continue
  x=$(getf "$w" "$src" "$dst"); [ "$x" = OK ] || MISS="$MISS $src"
done
for s in $STEPS; do [ -s "$RB/logs/${s}_log.txt" ] || x=$(getf "$WIN" "W/${s}_log.txt" "$RB/logs/${s}_log.txt"); done
okst=$(echo "$ST" | awk '$1=="STEP" && $3 ~ /^rc=0$/ {printf "%s ", $2}')
need=""
for s in $okst; do case $s in
  train) need="$need $GD/summary.json";;
  devcheck) need="$need W/gdev.jsonl";;
  score) need="$need outg/notes_confirm.json";;
  g5G) need="$need W/g5_G.jsonl";;
  g5R) need="$need W/g5_R.jsonl";;
esac; done
lack=""; for f in $need; do case " $MISS " in *" $f "*) lack="$lack $f";; esac; done
if [ -n "$lack" ]; then
  tries=$(grep -c 'collect incomplete' "$NOTE" 2>/dev/null); tries=${tries:-0}
  if [ "$tries" -lt 2 ]; then stop "collect incomplete (try $((tries + 1)) of 3): missing$lack; the next pass tries again"; fi
  note "collect incomplete on the third try: missing$lack; writing RESULTS-benspc.md with what exists"
fi
[ -n "$MISS" ] && note "not on BensPC or not copied:$MISS"
# the watcher pushes only files of 4 MiB or less: a bigger file is pushed as a gzip copy (split if still too big)
for f in $(find "$RB" "$N/g5" -type f -size +3900k ! -name '*.gz' ! -name '*.gz.part-*' 2>/dev/null); do
  [ -s "$f.gz" ] || [ -s "$f.gz.part-aa" ] && continue
  gzip -9 -c "$f" > "$f.gz"
  if [ "$(wc -c < "$f.gz" | tr -d ' ')" -gt 3993600 ]; then
    split -b 3500k "$f.gz" "$f.gz.part-" && rm -f "$f.gz"; note "$f pushed as parts $f.gz.part-* (join with cat, then gunzip)"
  else note "$f is $(wc -c < "$f" | tr -d ' ') bytes: pushed as $f.gz"; fi
done
# G's adapter: BensPC premonition-models\rd378g and the Mac (never pushed); the merged model stays in the BensPC tree
cm=$(rb copy-adapter); echo "$cm"; note "BensPC: $(echo "$cm" | tr '\n' ';')"
if [ ! -d "$MA" ] && echo "$cm" | grep -q '^COPY adapter'; then
  t=$(mktemp -d); $SSH "tar -cf - -C $WIN\\$(echo "$GD" | tr '/' '\\') adapter" < /dev/null 2>/dev/null | tar -x -C "$t" 2>/dev/null
  [ -d "$t/adapter" ] && mkdir -p "$(dirname "$MA")" && cp -r "$t/adapter" "$MA" && note "Mac copy of G's adapter: $MA ($(ls "$MA" | wc -l | tr -d ' ') files)"; rm -rf "$t"
fi
nok=$(echo "$ST" | awk '$1=="STEP" && $3=="rc=0"' | wc -l | tr -d ' ')
if [ "$DIED" = 1 ]; then status="DIED: the chain stopped without chain.done; $nok of 8 steps ended rc=0"
elif [ "$nok" = 8 ]; then status="COMPLETE: all 8 steps ended rc=0"
else status="PARTIAL: $nok of 8 steps ended rc=0; $(echo "$ST" | awk '$1=="STEP" && ($3 ~ /^rc=/ && $3!="rc=0" || $3=="skipped") {print "step " $2 " " $3 " " $4}' | head -2 | tr '\n' ';')"; fi
lastl() { [ -s "$1" ] && tr -d '\r' < "$1" | grep . | tail -"$2" | cut -c1-600 | sed 's/^/    /' || echo "    (no file)"; }
{
  echo "# rd-378g BensPC run record (handoff/kit/rd378gpc/pass.sh, job $JOB, kit $PIN, written $(now))"
  echo
  echo "**$status.** No verdict here: the thread scores G1-G4 from notes_confirm.json and G5 with the blind judges."
  echo "Every line below is copied by the script, never retyped. LoCoMo files (dialogs59, g59, per_question) were copied"
  echo "to ~/rd378g-private on the Mac only, never into git."
  echo
  echo "## Steps (W/steps.txt; BensPC local time)"
  echo; tr -d '\r' < "$RB/steps.txt" 2>/dev/null | sed 's/^/    /'; echo
  echo "## Last lines of each log"
  for s in $STEPS; do echo "- ${s}_log.txt:"; echo; lastl "$RB/logs/${s}_log.txt" 2; echo; done
  echo "## Machine and files"
  for k in VERSIONS GPUNAME MINILM DATA BASESHA; do echo "- $(grep "^$k" "$RB/checks.txt" 2>/dev/null | head -1)"; done
  echo "- selftests: $(grep -c '^CHECK .* rc=0 ' "$RB/checks.txt" 2>/dev/null) of 4 ok (checks.txt)"
  echo "- G trained in: $GD; $(echo "$cm" | grep '^MERGED')"
  echo "- R (rd-378 writer) path on BensPC: $(cat "$RB/r-path.txt" 2>/dev/null | tr -d '\r' || echo none)"
  echo "- GPU log (one line a minute: UTC, MiB used, MiB total, W): $(sv GPULOG)"
  echo "- disk now: $(sv DISK) GB free on C:"
  echo
  echo "| file | bytes | sha256 |"
  echo "|---|---|---|"
  for f in $(find "$RB" "$N/g5" -type f ! -name 'RESULTS-benspc.md' ! -name 'RUN-NOTE-bo.md' 2>/dev/null | sort); do
    echo "| $f | $(wc -c < "$f" | tr -d ' ') | $(shasum -a 256 "$f" | cut -c1-64) |"; done
  echo
  echo "## Notes (RUN-NOTE-bo.md)"
  echo; sed 's/^/    /' "$NOTE"
} > "$RB/RESULTS-benspc.md"
note "wrote RESULTS-benspc.md: $status"
echo "PASS-END $(now)"
