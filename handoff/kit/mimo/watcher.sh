#!/bin/bash
# watcher.sh: runs Muse builder tasks that the cloud director pushes to GitHub, and pushes the results back.
# The director (a cloud Claude session) cannot reach opencode.ai or BensPC, so this runs on Ben's Mac.
# Every 120 s it:
#   1. fetches the director's branch and looks for new task files in handoff/queue/*.md;
#   2. copies each new one to $Q and launches rungo4.sh on it (at most $MAX at once; a task whose
#      file contains the line "GPU: yes" waits until no other GPU task is running; "GPU: rent" tasks
#      rent their own cloud GPU and are not gated);
#   3. when a task finishes (.done, or rungo4 exits), copies its reply/err files plus the paths listed
#      on its "PUSH:" lines (files under 5 MB only; never notebook/, never weights) into the outbox
#      clone and pushes them to the branch $OUT.
# Stop it with: touch ~/premonition-watch/STOP
set -u
export OPENCODE_CONFIG_CONTENT='{"snapshot": false}'
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
H=$HOME/premonition-watch; Q=$H/queue; O=$H/outbox
IN=main; OUT=builder-outbox; MAX=${MAX:-8}   # 5 -> 8 (Director 03:56 UTC 09-27): 5 Go-limited GLM jobs sit hung in local slots; Luna pilots need room
RUN="$W/handoff/kit/mimo/rungo4.sh"
# rungo5 (no opencode-go fallback) is refreshed from main into $H each round and used when it passes bash -n (Director 03:17 UTC 09-27)
# builder model: muse-spark-1.3-contributor builders hung at "> build" with 0-byte replies from 01:21 UTC 09-27 (status diag 03:02 UTC; GLM calls were launched, not shown returning); opencode.log shows "Go usage limit exceeded" from ~00:57 UTC (Ben's Mac Claude, relayed 03:01); Ben 03:04:18 UTC "use muse spark 1.3": new launches start on the free Zen route, Go chain stays as fallback (Director 03:08 UTC 09-27)
BM=opencode/muse-spark-1.3-contributor-free
mkdir -p "$Q"; LOG=$H/watch.log
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
if [ ! -d "$O/.git" ]; then   # small separate repo that holds only builder results (no copy of the project)
  mkdir -p "$O" && git -C "$O" init -q && git -C "$O" remote add origin "$(git -C "$W" remote get-url origin)"
  git -C "$O" config user.name "$(git -C "$W" config user.name || echo Ben)"; git -C "$O" config user.email "$(git -C "$W" config user.email || echo ben@localhost)"
  git -C "$O" checkout -q -b "$OUT"
  if git -C "$O" fetch -q origin "$OUT" 2>/dev/null; then git -C "$O" reset -q --hard FETCH_HEAD; fi
fi
publish() {  # $1 = task name; marks $Q/$n.pushed on success
  # index = the fetched outbox tip, then stage ONLY this job's paths (git add -A once deleted other jobs' results, 09-26)
  local n="$1" d="$O/runs/$n"; mkdir -p "$d"
  cp "$Q/$n".md "$Q/$n".go* "$Q/$n".exit "$d/" 2>/dev/null
  grep -h '^[0-9. ]*PUSH[^:]*:' "$Q/$n.md" | sed 's/^[0-9. ]*PUSH[^:]*://' | tr ' ' '\n' | grep -v '^$' | while read -r p; do
    case "$p" in notebook*|/*|*..*) log "refused push path $p"; continue;; esac
    (cd "$W" && find $p -type f -size -5120k ! -name '*.pt' ! -name '*.safetensors' ! -name '*.gguf' ! -name '*.bin' 2>/dev/null) | while read -r f; do
      mkdir -p "$O/$(dirname "$f")"; cp "$W/$f" "$O/$f"; done
  done
  (cd "$O" && git fetch -q origin "$OUT" 2>/dev/null && git reset -q --mixed FETCH_HEAD; { echo "runs/$n"; grep -h '^[0-9. ]*PUSH[^:]*:' "$Q/$n.md" | sed 's/^[0-9. ]*PUSH[^:]*://' | tr ' ' '\n' | grep -v '^$'; } | while read -r p; do git add -f -- "$p" 2>/dev/null; done; git commit -qm "builder results: $n"; git push -q origin "HEAD:$OUT") >> "$LOG" 2>&1 \
    && touch "$Q/$n.pushed" && log "pushed $n" || log "push failed $n (retry next round)"
}
log "watcher started (pid $$)"
while [ ! -e "$H/STOP" ]; do
  rm -f $(find "$H" -maxdepth 1 -name "clean.lock" -mmin +30 2>/dev/null) 2>/dev/null   # a clean that died leaves no stale lock
  git -C "$W" fetch -q origin "$IN" 2>>"$LOG"
  # self-update: when the watcher on $IN changes, restart into the new version (running tasks keep going)
  if git -C "$W" show "origin/$IN:handoff/kit/mimo/watcher.sh" > "$H/watcher.new" 2>/dev/null && [ -s "$H/watcher.new" ] && ! cmp -s "$H/watcher.new" "$0"; then
    bash -n "$H/watcher.new" && { mv "$H/watcher.new" "$0"; log "self-update, restarting"; exec bash "$0"; }
  fi
  # briefs point at OPUS-RULES.txt under /private/tmp, which macOS can wipe: restore it from main each round (Director 19:20 UTC 09-26)
  RB=/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs
  mkdir -p "$RB" 2>/dev/null && git -C "$W" show "origin/$IN:handoff/kit/briefs/OPUS-RULES.txt" > "$RB/OPUS-RULES.txt.new" 2>/dev/null && [ -s "$RB/OPUS-RULES.txt.new" ] && mv "$RB/OPUS-RULES.txt.new" "$RB/OPUS-RULES.txt"
  git -C "$W" show "origin/$IN:handoff/kit/mimo/rungo5.sh" > "$H/rungo5.new" 2>/dev/null && [ -s "$H/rungo5.new" ] && bash -n "$H/rungo5.new" && mv "$H/rungo5.new" "$H/rungo5.sh"; [ -s "$H/rungo5.sh" ] && RUN="$H/rungo5.sh"
  # orphan repair: a task whose watcher subshell died (e.g. an old loop was stopped) still gets published
  for r in "$Q"/*.running; do [ -e "$r" ] || continue; n=$(basename "$r" .running)
    pgrep -f "rungo[45].sh $Q/$n.md" >/dev/null || { echo "rc=orphan" > "$Q/$n.exit"; rm -f "$r"; log "orphan finished $n"; }; done
  for e in "$Q"/*.exit; do [ -e "$e" ] || continue; n=$(basename "$e" .exit); [ -e "$Q/$n.pushed" ] || [ -e "$Q/$n.running" ] || publish "$n"; done
  for f in $(git -C "$W" ls-tree --name-only "origin/$IN" handoff/queue/ 2>/dev/null | grep '\.md$'); do
    n=$(basename "$f" .md)
    [ -e "$Q/$n.md" ] && continue
    running=$(ls "$Q"/*.running 2>/dev/null | wc -l)
    # BensPC GPU jobs (task line 'GPU: yes'; the Director names them 1xx-/2xx-/3xx-): the Mac only waits on ssh, so they skip the local-slot cap and the load hold (GPU-BUSY still allows one at a time); the count excludes those prefixes (Director 23:42 UTC 09-26)
    # rentals mostly wait on vast (polls, uploads), so they get extra slots beyond MAX (Director 13:47 UTC 09-26, Ben 13:30 "BensPC's gpu should not be the blocker")
    git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -qE '^STATUS: *HELD' && continue   # read from origin like the tests below; a cwd-relative $f never matched (TM 14:00 UTC 09-27)
    z5=0; for r5 in "$Q"/*.running; do [ -e "$r5" ] || continue; j5=$(basename "$r5" .running); [ -e "$Q/$j5.stop" ] && continue; grep -qE '^(GPU: *yes|BASH-ONLY: yes)' "$Q/$j5.md" 2>/dev/null && continue; pgrep -f "rungo5.sh $Q/$j5.md" >/dev/null && z5=$((z5+1)); done
    zexempt=0; case "$n" in 000-*) zexempt=1;; esac; git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -qE '^(GPU: *yes|BASH-ONLY: yes)' && zexempt=1
    # BASH-ONLY cap: at most 5 non-000 BASH-ONLY jobs at once, whatever their prefix (they skip the zen and local-slot caps; Luna shares still set each job's workers) (Director 08:4x UTC 09-27)
    if [ "${n#000-}" = "$n" ] && git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -q '^BASH-ONLY: yes'; then
      b5=0; for r5 in "$Q"/*.running; do [ -e "$r5" ] || continue; j5=$(basename "$r5" .running); [ "${j5#000-}" = "$j5" ] && grep -q '^BASH-ONLY: yes' "$Q/$j5.md" 2>/dev/null && b5=$((b5+1)); done
      [ "$b5" -ge 5 ] && { log "bash-only cap: $b5 running, holding $n"; continue; }
    fi
    [ "$z5" -ge 4 ] && [ "$zexempt" = 0 ] && { log "zen cap: $z5 non-GPU rungo5 builders running, holding $n"; continue; }   # cap 2 -> 4 (Director 05:13 UTC 09-27); BensPC and 000- jobs never held; continue so later exempt jobs still launch   # free Zen builders: at most 2 at once until 2 real jobs finish (Thread manager 03:07 UTC 09-27; mimo-skill.md:17,19 rate limits)
    [ "$running" -ge 18 ] && break; localrun=$(ls "$Q"/*.running 2>/dev/null | xargs -n1 basename 2>/dev/null | grep -cvE '^(rent-|000-|claude-|[1-3][0-9][0-9]-)'); gpuj=0; git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -qE '^GPU: *yes' && gpuj=1; [ "$localrun" -ge "$MAX" ] && [ "$gpuj" = 0 ] && case "$n" in rent-*|000-*|claude-*) ;; *) continue;; esac
    load=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print int($2)}'); [ -z "$load" ] && load=0
    # Ben 13:30 UTC 09-26 "BensPC's gpu should not be the blocker": rentals and read-only 000-* checks do their work off the Mac, so a busy Mac holds only local jobs
    lightj=0; git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -qE '^LOAD-LIGHT: *yes' && lightj=1   # network-bound jobs (e.g. Luna/Codex calls) declare this header and skip the load hold (Director 04:06 UTC 09-27)
    if [ "${localrun:-0}" -ge 2 ] && [ "$load" -gt 60 ] && [ "$gpuj" = 0 ] && [ "$lightj" = 0 ]; then case "$n" in rent-*|000-*|claude-*) ;; *) log "load $load, holding $n ($running running)"; continue;; esac; fi
    freegb=$(df -g / | tail -1 | awk '{print $4}')
    # Ben 06:54 UTC 09-26 made Mac disk the pipeline's job ("You have this responsibility"): jobs marked LOWDISK-OK
    # (no model copy-back to the Mac) may launch down to 2 GB free; everything else keeps the 5 GB rule
    if [ "${freegb:-0}" -lt 5 ] && [ "${freegb:-0}" -ge 2 ] && git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -q '^LOWDISK-OK: yes'; then log "disk ${freegb} GB free, launching LOWDISK-OK $n"; freegb=5; fi
    # Ben 11:26 UTC 09-26 "yes, clean pipeline files" / "I can't be your storage babysitter": below 10 GB (before it fills), remove scratch the pipeline itself made once the job
    # that made it is gone (rent-kit mktemp code trees and tree.tgz bundles), then re-read free space. Never models or Ben's files.
    if [ "${freegb:-0}" -lt 10 ] && [ ! -e "$H/clean.$(date +%Y%m%d%H%M | cut -c1-11)" ] && [ ! -e "$H/clean.lock" ]; then touch "$H/clean.$(date +%Y%m%d%H%M | cut -c1-11)" "$H/clean.lock"
      # runs in the background so a slow disk walk can never stall the watcher loop; only exact rent-kit scratch names
      ( b=$(df -g / | tail -1 | awk '{print $4}'); TD=$(getconf DARWIN_USER_TEMP_DIR 2>/dev/null); TD=${TD:-${TMPDIR:-/tmp}}
        for t in "$TD"tmp.*/tree "$TD"/tmp.*/tree; do [ -d "$t" ] || continue
          [ -n "$(find "$t" -maxdepth 0 -mmin -120 2>/dev/null)" ] && continue   # touched in the last 2 h: a job may still use it
          for r in "$Q"/*.running; do [ -e "$r" ] || continue; grep -qs "$(basename "$(dirname "$t")")" "${r%.running}".go*.err.txt && continue 2; done   # a running job's log names it: in use
          rm -rf "$(dirname "$t")" 2>/dev/null && log "clean: removed $(dirname "$t")"; done
        for z in "$W/tree.tgz" "$TD"tmp.*/tree.tgz; do [ -f "$z" ] || continue
          [ -n "$(find "$z" -mmin -120 2>/dev/null)" ] && continue
          rm -f "$z" && log "clean: removed $z"; done
        log "clean: ${b} -> $(df -g / | tail -1 | awk '{print $4}') GB free"; rm -f "$H/clean.lock" ) </dev/null >/dev/null 2>&1 &
    fi
    # per-job reservation: header "DISK: <GB>" = the job's peak Mac use (default 3 for rent-*, else 1); launch only if it fits above the floor
    need=$(git -C "$W" show "origin/$IN:$f" 2>/dev/null | sed -n 's/^DISK: *\([0-9]*\).*/\1/p' | head -1); case "$n" in rent-*) need=${need:-3};; *) need=${need:-1};; esac
    floor=5; git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -q '^LOWDISK-OK: yes' && floor=2
    if [ "${freegb:-0}" -ge 5 ] && [ $((freegb - need)) -lt "$floor" ]; then log "disk ${freegb} GB free, $n reserves ${need} GB, holding"; continue; fi
    if [ "${freegb:-0}" -lt 5 ]; then log "disk ${freegb} GB free, holding new launches"
      # uv cache prune when low (never uv cache clean); Trash emptied at most once
      # Ben 02:16/02:17 UTC 09-26: yes to trashing these two models and "also have it empty the trash"; Finder timed out, so remove exactly these two from the Trash
        for d in rd371-verifier-merged lis318-merged; do [ -d "$HOME/.Trash/$d" ] || continue
          b=$(df -g / | tail -1 | awk '{print $4}'); rm -rf "$HOME/.Trash/$d" 2>>"$LOG" && log "lowdisk: removed Trash/$d (${b} -> $(df -g / | tail -1 | awk '{print $4}') GB)" || log "lowdisk: remove Trash/$d failed"; done
      if [ ! -e "$H/lowdisk.$(date +%Y%m%d%H)" ]; then touch "$H/lowdisk.$(date +%Y%m%d%H)"
        { U=$(command -v uv || echo "$HOME/.local/bin/uv"); "$U" cache prune >/dev/null 2>&1 && log "lowdisk: uv cache prune" || log "lowdisk: uv cache prune failed"; }
        # one time only (Ben's 02:17 yes covered the two models moved to the Trash that night); never a standing auto-delete
        if [ ! -e "$H/lowdisk.trash-once" ]; then touch "$H/lowdisk.trash-once"
          osascript -e 'with timeout of 900 seconds' -e 'tell application "Finder" to empty trash' -e 'end timeout' >/dev/null 2>&1 && log "lowdisk: emptied Trash (one time)" || log "lowdisk: empty Trash failed"; fi
        log "lowdisk: now $(df -g / | tail -1 | awk '{print $4}') GB free"; fi
      break; fi
    git -C "$W" show "origin/$IN:$f" > "$Q/$n.md.tmp" 2>/dev/null; [ -s "$Q/$n.md.tmp" ] || { rm -f "$Q/$n.md.tmp"; continue; }   # file moved to held mid-round: skip, never launch empty
    if grep -q '^QUIET: yes' "$Q/$n.md.tmp" && { [ "$running" -gt 0 ] || [ "$load" -gt 20 ]; }; then rm -f "$Q/$n.md.tmp"; continue; fi   # timing jobs wait for an idle Mac
    if ls "$Q"/*.running >/dev/null 2>&1 && grep -l '^QUIET: yes' $(ls "$Q"/*.running | sed 's/\.running$/.md/') 2>/dev/null | grep -q .; then rm -f "$Q/$n.md.tmp"; break; fi   # nothing starts beside a quiet job
    if grep -q '^GPU: yes' "$Q/$n.md.tmp" && grep -l '^GPU: yes' $(ls "$Q"/*.running 2>/dev/null | sed 's/\.running$/.md/') 2>/dev/null | grep -q .; then
      rm -f "$Q/$n.md.tmp"; continue   # another GPU task is running; try next round
    fi
    # a finished job can leave detached GPU runs alive on BensPC (156 at 07:47 UTC 09-27). Under WDDM, nvidia-smi's compute-app list is often empty, so hold a GPU job if
    # GPU memory.used > 700 MiB (idle 250-560) or any python.exe runs (pythonw.exe, e.g. 13036, is not counted); an ssh failure also holds
    # a job that adopts orphaned runs of its own sealed experiment says 'GPU-ADOPT: yes' and skips this busy check (the one-GPU-job rule above still holds)
    if grep -q '^GPU: yes' "$Q/$n.md.tmp" && ! grep -q '^GPU-ADOPT: yes' "$Q/$n.md.tmp"; then
      ga=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o BatchMode=yes benspc "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits & tasklist /FI \"IMAGENAME eq python.exe\" /NH" </dev/null 2>/dev/null; echo "rc=$?")
      gm=$(echo "$ga" | grep -v '^rc=' | head -1 | tr -dc '0-9'); gp=$(echo "$ga" | grep -ic '^python.exe')   # never read rc=255 as memory
      if [ "$(echo "$ga" | tail -1)" != "rc=0" ]; then log "BensPC unreachable (ssh $(echo "$ga" | tail -1)), holding $n"; rm -f "$Q/$n.md.tmp"; continue; fi
      if [ "$(echo "$ga" | tail -1)" != "rc=0" ] || [ -z "$gm" ] || [ "$gm" -gt 700 ] || [ "$gp" -gt 0 ]; then log "gpu busy on BensPC, holding $n: mem ${gm:-?} MiB, python.exe $gp, $(echo "$ga" | tail -1)"; rm -f "$Q/$n.md.tmp"; continue; fi
    fi
    mv "$Q/$n.md.tmp" "$Q/$n.md"; touch "$Q/$n.running"; log "launch $n"
    # a GPU: yes job claims BensPC visibly: C:\Users\benja\GPU-BUSY.txt names the job while it runs (outside agents: do not use the GPU while it exists)
    gpu=0; grep -q '^GPU: yes' "$Q/$n.md" && gpu=1
    [ $gpu = 1 ] && { ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o BatchMode=yes benspc "echo BUSY: queue job $n since $(date -u +%FT%TZ) - do not use this GPU until this file is gone > C:\Users\benja\GPU-BUSY.txt" </dev/null >/dev/null 2>&1 & }
    ( bash "$RUN" "$Q/$n.md" "$BM"; echo "rc=$?" > "$Q/$n.exit"; rm -f "$Q/$n.running"
      [ $gpu = 1 ] && ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o BatchMode=yes benspc "del C:\Users\benja\GPU-BUSY.txt" </dev/null >/dev/null 2>&1 ) &
  done
  # status: every round, publish which tasks are running and the log tail, so the director can see launches
  { date '+%F %T'; echo "running:"; ls "$Q"/*.running 2>/dev/null | xargs -n1 basename 2>/dev/null; echo "launched (no exit yet) / finished:"; ls "$Q"/*.md 2>/dev/null | wc -l; echo; tail -150 "$LOG"; } > "$H/status.txt"
  # diagnostics (Director 03:00 UTC 09-27, jobs hanging since 01:21): per running job, err/reply file sizes+mtimes and the last 5 err lines, filtered; process names only (no command lines, so no task text or keys)
  { echo; echo "diag:"; for r in "$Q"/*.running; do [ -e "$r" ] || continue; j=$(basename "$r" .running); echo "== $j"; ls -la "$Q/$j".go* 2>/dev/null | awk '{print $5, $6, $7, $8, $NF}' | sed "s|$Q/||"; for e in "$Q/$j".go*.err.txt; do [ -f "$e" ] && tail -5 "$e" | grep -viE 'key|token|auth|secret|passw|bearer|cookie' | cut -c1-200; done; done; echo "top5cpu:"; ps -axro pcpu,comm 2>/dev/null | head -6 | awk '{c=$2; n=split(c,a,"/"); print $1, a[n]}'; echo "procs:"; ps -axo pid,ppid,etime,stat,comm 2>/dev/null | grep -E 'opencode|rungo4|ssh|bun' | grep -v grep | head -60; } >> "$H/status.txt" 2>/dev/null || true
  mkdir -p "$O/status"; if ! cmp -s "$H/status.txt" "$O/status/watcher.txt"; then cp "$H/status.txt" "$O/status/watcher.txt"
    (cd "$O" && git fetch -q origin "$OUT" 2>/dev/null && git reset -q --soft FETCH_HEAD; git add status && git commit -qm "watcher status" && git push -q origin "HEAD:$OUT") >> "$LOG" 2>&1 || true; fi
  sleep 120
done
log "watcher stopped"
