#!/bin/bash
# pcwatch/watcher.sh: a job runner that lives on BensPC (git-bash), so GPU jobs no longer depend on the Mac.
# Every CYCLE seconds (default 120) it:
#   1. fetches origin/main over https (token file, see README.md) and looks in handoff/pcqueue/ and handoff/queue/
#      for job files whose header has both "GPU: yes" and "RUNNER: pc" (Mac jobs have no RUNNER line and are ignored);
#   2. runs at most ONE job at a time: the first ```bash block of the job file is the job (run with bash, cwd = a
#      checkout of that main commit, env TREE JOB JOBDIR). The job file also says "TIME CAP: N minutes" (default 180);
#   3. when a job ends, copies n.md n.log n.exit plus the paths on its "PUSH:" lines (files under 5 MB, never
#      notebook/, never weights) into runs/<job>/ (and their own paths) on the branch pc-outbox and pushes it;
#   4. every cycle pushes status/pc-watcher.txt to pc-outbox.
# Job exit codes: 0 done; 5 (WAITING, a precondition not true yet) and 75 (network/fetch failure) are RETRIED after a
# backoff (5,10,20,40,60 min, at most 8 tries) and are not marked done; any other code ends the job as finished.
# Stop it with: touch ~/pcwatch/STOP     Token file: ~/pcwatch/token (never read, echoed or logged by this script).
set -u
H=${PCW_HOME:-$HOME/pcwatch}; S=$H/state; W=$H/repo; O=$H/outbox; LOG=$H/watch.log
REPO_URL=${REPO_URL:-https://github.com/BenjaminHannan/learner.git}
CYCLE=${CYCLE:-120}; OUT=pc-outbox; IN=main
BUSYF=${BUSYF:-$HOME/GPU-BUSY.txt}; GPU_MEM_MAX=${GPU_MEM_MAX:-3000}   # Ben 10:30 UTC 09-29 "just use the gpu": desktop apps hold 1300-1400 MiB
TOKEN=$H/token
mkdir -p "$S" "$H"
log() { echo "$(date -u '+%F %T')Z $*" >> "$LOG"; }
# Auth: git asks a tiny helper for the password; the helper cats the token file. The token is never in an argument, a URL or the log.
cat > "$H/askpass.sh" <<'AP'
#!/bin/bash
case "$1" in Username*) echo x-access-token;; *) cat "$(dirname "$0")/token" 2>/dev/null;; esac
AP
chmod +x "$H/askpass.sh" 2>/dev/null
g() {  # git with the token helper (only when the token file exists; otherwise the PC's own credentials are used)
  if [ -s "$TOKEN" ]; then GIT_TERMINAL_PROMPT=0 GIT_ASKPASS="$H/askpass.sh" git -c credential.helper= "$@"
  else GIT_TERMINAL_PROMPT=0 git "$@"; fi
}
now() { date +%s; }
# ---- clones -------------------------------------------------------------------------------------------------------
if [ ! -d "$W/.git" ]; then
  g clone -q --depth 1 --branch "$IN" "$REPO_URL" "$W" >> "$LOG" 2>&1 || log "initial clone failed (will retry)"
fi
if [ ! -d "$O/.git" ]; then   # small separate repo that holds only results and status
  mkdir -p "$O" && git -C "$O" init -q && git -C "$O" remote add origin "$REPO_URL"
  git -C "$O" config user.name "BensPC runner"; git -C "$O" config user.email "pc-runner@localhost"
  git -C "$O" checkout -q -b "$OUT"
fi
alive() { [ -n "${1:-}" ] && kill -0 "$1" 2>/dev/null; }
busy_names() { [ -f "$BUSYF" ] && sed -n 's/^BUSY: queue job \([^ ]*\) .*/\1/p' "$BUSYF" | head -1; }
# ---- publish ------------------------------------------------------------------------------------------------------
pushlines() { grep -h '^[0-9. ]*PUSH[^:]*:' "$1" 2>/dev/null | sed 's/^[0-9. ]*PUSH[^:]*://' | tr ' ' '\n' | grep -v '^$'; }
publish() {  # $1 = job name; marks $S/$n.pushed on success
  local n="$1" d="$O/runs/$n"; mkdir -p "$d"
  cp "$S/$n.md" "$S/$n.log" "$S/$n.exit" "$d/" 2>/dev/null
  pushlines "$S/$n.md" | while read -r p; do
    case "$p" in notebook*|/*|*..*) log "refused push path $p"; continue;; esac
    (cd "$W" && find $p -type f -size -5120k ! -name '*.pt' ! -name '*.safetensors' ! -name '*.gguf' ! -name '*.bin' 2>/dev/null) | while read -r f; do
      mkdir -p "$O/$(dirname "$f")"; cp "$W/$f" "$O/$f"; done
  done
  ( cd "$O" && g fetch -q origin "$OUT" 2>/dev/null && git reset -q --mixed FETCH_HEAD
    { echo "runs/$n"; pushlines "$S/$n.md"; } | while read -r p; do case "$p" in notebook*|/*|*..*) ;; *) git add -f -- "$p" 2>/dev/null;; esac; done
    git commit -qm "pc results: $n" 2>/dev/null; g push -q origin "HEAD:refs/heads/$OUT" ) >> "$LOG" 2>&1 \
    && touch "$S/$n.pushed" && log "pushed $n" || log "push failed $n (retry next cycle)"
}
# ---- job finish / stale handling ------------------------------------------------------------------------------------
finish() {  # $1 = job name, $2 = rc (job has ended, marker still present)
  local n="$1" rc="$2" tries=0 back
  rm -f "$S/$n.running"; [ "$(busy_names)" = "$n" ] && rm -f "$BUSYF"
  [ -f "$S/$n.tries" ] && tries=$(cat "$S/$n.tries")
  case "$rc" in
    5|75) tries=$((tries+1)); echo "$tries" > "$S/$n.tries"
      if [ "$tries" -lt 8 ]; then
        back=$((300 * (1 << (tries-1)))); [ "$back" -gt 3600 ] && back=3600
        echo $(( $(now) + back )) > "$S/$n.notbefore"; mv "$S/$n.log" "$S/$n.log.try$tries" 2>/dev/null
        rm -f "$S/$n.md"; log "$n rc=$rc, retry $tries in ${back}s (not marked done)"; return
      fi;;
  esac
  echo "rc=$rc" > "$S/$n.exit"; log "$n finished rc=$rc"
}
reap() {  # a marker whose process is gone: finished (.rc file) or died (machine reboot, kill)
  local r n pid
  for r in "$S"/*.running; do [ -e "$r" ] || continue; n=$(basename "$r" .running); pid=$(cat "$r" 2>/dev/null)
    if [ -e "$S/$n.rc" ]; then finish "$n" "$(cat "$S/$n.rc")"; rm -f "$S/$n.rc"
    elif ! alive "$pid"; then log "stale marker cleared: $n (pid ${pid:-?} not alive), will re-run"; finish "$n" 75; fi
  done
}
# ---- launch -------------------------------------------------------------------------------------------------------
eligible() {  # names of new pc jobs on origin/main, oldest name first
  local f n t
  for f in $(git -C "$W" ls-tree --name-only "origin/$IN" handoff/pcqueue/ handoff/queue/ 2>/dev/null | grep '\.md$'); do
    n=$(basename "$f" .md); [ -e "$S/$n.md" ] && continue; [ -e "$S/$n.exit" ] && continue
    [ -e "$S/$n.notbefore" ] && [ "$(now)" -lt "$(cat "$S/$n.notbefore")" ] && continue
    t=$(git -C "$W" show "origin/$IN:$f" 2>/dev/null) || continue
    echo "$t" | grep -qE '^RUNNER: *pc' || continue; echo "$t" | grep -qE '^GPU: *yes' || continue
    echo "$t" | grep -qE '^STATUS: *HELD' && continue
    echo "$f"
  done | awk -F/ '{print $NF" "$0}' | sort | awk '{print $2}'
}
launch_one() {
  local f n m capm cap gm bn
  ls "$S"/*.running >/dev/null 2>&1 && return                           # one job at a time
  bn=$(busy_names); if [ -f "$BUSYF" ]; then log "GPU-BUSY.txt present (names ${bn:-?}), holding"; return; fi
  gm=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc '0-9')
  if [ -n "$gm" ] && [ "$gm" -gt "$GPU_MEM_MAX" ]; then log "gpu memory ${gm} MiB > $GPU_MEM_MAX, holding"; return; fi
  f=$(eligible | head -1); [ -n "$f" ] || return; n=$(basename "$f" .md)
  base=$(echo "$n" | sed -E 's/-(benspc|pc)$//'); CL=${CLAIMDIR:-$HOME/claims}; mkdir -p "$CL" 2>/dev/null   # shared claim with the Mac watcher (it mkdirs C:\Users\benja\claims\<base> over ssh); atomic, so X runs once
  if ! mkdir "$CL/$base" 2>/dev/null; then echo "rc=CLAIMED" > "$S/$n.exit"; log "claim for $base already taken (Mac watcher or earlier run), $n marked done"; return; fi
  git -C "$W" checkout -q -f --detach "origin/$IN" 2>>"$LOG" || { log "checkout failed, holding $n"; return; }   # safe: nothing is running
  git -C "$W" show "origin/$IN:$f" > "$S/$n.md"
  awk '/^```bash/{f=1;next} /^```/{if(f)exit} f' "$S/$n.md" > "$S/$n.sh"
  if [ ! -s "$S/$n.sh" ]; then echo "rc=NOBLOCK" > "$S/$n.exit"; log "$n has no bash block, marked done"; return; fi
  capm=$(sed -n 's/.*TIME CAP: *\([0-9][0-9]*\) *minutes.*/\1/p' "$S/$n.md" | head -1); cap=$(( ${capm:-180} * 60 ))
  mkdir -p "$S/$n.d"; echo "BUSY: queue job $n since $(date -u +%FT%TZ) - do not use this GPU until this file is gone" > "$BUSYF"
  log "launch $n (cap ${cap}s, commit $(git -C "$W" rev-parse --short HEAD))"
  (
    cd "$W" && env -u GIT_ASKPASS TREE="$W" JOB="$n" JOBDIR="$S/$n.d" timeout "$cap" bash "$S/$n.sh" > "$S/$n.log" 2>&1
    echo $? > "$S/$n.rc"
  ) </dev/null >/dev/null 2>&1 &
  echo $! > "$S/$n.running"
}
# ---- status -------------------------------------------------------------------------------------------------------
status() {
  local t="$H/status.txt" r n
  { echo "pc-watcher status $(date -u '+%F %T')Z (pid $$, cycle ${CYCLE}s)"
    echo "gpu (util %, mem MiB): $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null | head -1 || true)"
    echo "gpu-busy file: $( [ -f "$BUSYF" ] && cat "$BUSYF" || echo none)"
    echo "running:"; for r in "$S"/*.running; do [ -e "$r" ] && basename "$r" .running; done
    echo "queued (eligible, not started):"; eligible | while read -r f; do basename "$f" .md; done
    echo "waiting to retry:"; for r in "$S"/*.notbefore; do [ -e "$r" ] || continue; n=$(basename "$r" .notbefore); [ -e "$S/$n.md" ] || echo "$n tries=$(cat "$S/$n.tries" 2>/dev/null) in $(( $(cat "$r") - $(now) ))s"; done
    echo "finished:"; for r in "$S"/*.exit; do [ -e "$r" ] || continue; n=$(basename "$r" .exit); echo "$n $(cat "$r") pushed=$( [ -e "$S/$n.pushed" ] && echo yes || echo no)"; done
    echo; echo "log tail:"; tail -40 "$LOG"; } > "$t"
  mkdir -p "$O/status"; cp "$t" "$O/status/pc-watcher.txt"
  ( cd "$O" && g fetch -q origin "$OUT" 2>/dev/null; git reset -q --mixed FETCH_HEAD 2>/dev/null
    git add status && git commit -qm "pc watcher status" && g push -q origin "HEAD:refs/heads/$OUT" ) >> "$LOG" 2>&1 || true
}
# ---- main loop ----------------------------------------------------------------------------------------------------
log "pc watcher started (pid $$)"
while [ ! -e "$H/STOP" ]; do
  g -C "$W" fetch -q --depth 1 origin "$IN" 2>>"$LOG" || log "fetch failed (will retry next cycle)"
  # self-update from main, so Ben starts the runner only once (running jobs keep going)
  if git -C "$W" show "origin/$IN:handoff/kit/pcwatch/watcher.sh" > "$H/watcher.new" 2>/dev/null && [ -s "$H/watcher.new" ] && ! cmp -s "$H/watcher.new" "$0"; then
    bash -n "$H/watcher.new" && [ -z "${NO_SELF_UPDATE:-}" ] && { cp "$H/watcher.new" "$0"; log "self-update, restarting"; exec bash "$0"; }
  fi
  reap
  for e in "$S"/*.exit; do [ -e "$e" ] || continue; n=$(basename "$e" .exit); [ -e "$S/$n.pushed" ] || [ -e "$S/$n.running" ] || publish "$n"; done
  launch_one
  status
  [ -n "${ONCE:-}" ] && break
  sleep "$CYCLE"
done
log "pc watcher stopped"
