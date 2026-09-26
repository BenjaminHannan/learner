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
IN=main; OUT=builder-outbox; MAX=${MAX:-5}
RUN="$W/handoff/kit/mimo/rungo4.sh"
mkdir -p "$Q"; LOG=$H/watch.log
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
if [ ! -d "$O/.git" ]; then   # small separate repo that holds only builder results (no copy of the project)
  mkdir -p "$O" && git -C "$O" init -q && git -C "$O" remote add origin "$(git -C "$W" remote get-url origin)"
  git -C "$O" config user.name "$(git -C "$W" config user.name || echo Ben)"; git -C "$O" config user.email "$(git -C "$W" config user.email || echo ben@localhost)"
  git -C "$O" checkout -q -b "$OUT"
  if git -C "$O" fetch -q origin "$OUT" 2>/dev/null; then git -C "$O" reset -q --hard FETCH_HEAD; fi
fi
publish() {  # $1 = task name; marks $Q/$n.pushed on success
  local n="$1" d="$O/runs/$n"; mkdir -p "$d"
  cp "$Q/$n".md "$Q/$n".go* "$Q/$n".exit "$d/" 2>/dev/null
  grep -h '^PUSH:' "$Q/$n.md" | sed 's/^PUSH://' | tr ' ' '\n' | grep -v '^$' | while read -r p; do
    case "$p" in notebook*|/*|*..*) log "refused push path $p"; continue;; esac
    (cd "$W" && find $p -type f -size -5M ! -name '*.pt' ! -name '*.safetensors' ! -name '*.gguf' ! -name '*.bin' 2>/dev/null) | while read -r f; do
      mkdir -p "$O/$(dirname "$f")"; cp "$W/$f" "$O/$f"; done
  done
  (cd "$O" && git fetch -q origin "$OUT" 2>/dev/null && git reset -q --soft FETCH_HEAD; git add -A && git commit -qm "builder results: $n"; git push -q origin "HEAD:$OUT") >> "$LOG" 2>&1 \
    && touch "$Q/$n.pushed" && log "pushed $n" || log "push failed $n (retry next round)"
}
log "watcher started (pid $$)"
while [ ! -e "$H/STOP" ]; do
  git -C "$W" fetch -q origin "$IN" 2>>"$LOG"
  # self-update: when the watcher on $IN changes, restart into the new version (running tasks keep going)
  if git -C "$W" show "origin/$IN:handoff/kit/mimo/watcher.sh" > "$H/watcher.new" 2>/dev/null && [ -s "$H/watcher.new" ] && ! cmp -s "$H/watcher.new" "$0"; then
    bash -n "$H/watcher.new" && { mv "$H/watcher.new" "$0"; log "self-update, restarting"; exec bash "$0"; }
  fi
  # orphan repair: a task whose watcher subshell died (e.g. an old loop was stopped) still gets published
  for r in "$Q"/*.running; do [ -e "$r" ] || continue; n=$(basename "$r" .running)
    pgrep -f "rungo4.sh $Q/$n.md" >/dev/null || { echo "rc=orphan" > "$Q/$n.exit"; rm -f "$r"; log "orphan finished $n"; }; done
  for e in "$Q"/*.exit; do [ -e "$e" ] || continue; n=$(basename "$e" .exit); [ -e "$Q/$n.pushed" ] || [ -e "$Q/$n.running" ] || publish "$n"; done
  for f in $(git -C "$W" ls-tree --name-only "origin/$IN" handoff/queue/ 2>/dev/null | grep '\.md$'); do
    n=$(basename "$f" .md)
    [ -e "$Q/$n.md" ] && continue
    running=$(ls "$Q"/*.running 2>/dev/null | wc -l)
    [ "$running" -ge "$MAX" ] && break
    load=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print int($2)}'); [ -z "$load" ] && load=0
    if [ "$running" -ge 2 ] && [ "$load" -gt 60 ]; then log "load $load, holding new launches ($running running)"; break; fi
    freegb=$(df -g / | tail -1 | awk '{print $4}')
    # Ben 06:54 UTC 09-26 made Mac disk the pipeline's job ("You have this responsibility"): jobs marked LOWDISK-OK
    # (no model copy-back to the Mac) may launch down to 2 GB free; everything else keeps the 5 GB rule
    if [ "${freegb:-0}" -lt 5 ] && [ "${freegb:-0}" -ge 2 ] && git -C "$W" show "origin/$IN:$f" 2>/dev/null | grep -q '^LOWDISK-OK: yes'; then log "disk ${freegb} GB free, launching LOWDISK-OK $n"; freegb=5; fi
    if [ "${freegb:-0}" -lt 5 ]; then log "disk ${freegb} GB free, holding new launches"
      # uv cache prune when low (never uv cache clean); Trash emptied at most once
      if [ ! -e "$H/lowdisk.$(date +%Y%m%d%H)" ]; then touch "$H/lowdisk.$(date +%Y%m%d%H)"
        { U=$(command -v uv || echo "$HOME/.local/bin/uv"); "$U" cache prune >/dev/null 2>&1 && log "lowdisk: uv cache prune" || log "lowdisk: uv cache prune failed"; }
        # Ben 02:16/02:17 UTC 09-26: yes to trashing these two models and "also have it empty the trash"; Finder timed out, so remove exactly these two from the Trash
        for d in rd371-verifier-merged lis318-merged; do [ -d "$HOME/.Trash/$d" ] || continue
          b=$(df -g / | tail -1 | awk '{print $4}'); rm -rf "$HOME/.Trash/$d" 2>>"$LOG" && log "lowdisk: removed Trash/$d (${b} -> $(df -g / | tail -1 | awk '{print $4}') GB)" || log "lowdisk: remove Trash/$d failed"; done
        # one time only (Ben's 02:17 yes covered the two models moved to the Trash that night); never a standing auto-delete
        if [ ! -e "$H/lowdisk.trash-once" ]; then touch "$H/lowdisk.trash-once"
          osascript -e 'with timeout of 900 seconds' -e 'tell application "Finder" to empty trash' -e 'end timeout' >/dev/null 2>&1 && log "lowdisk: emptied Trash (one time)" || log "lowdisk: empty Trash failed"; fi
        log "lowdisk: now $(df -g / | tail -1 | awk '{print $4}') GB free"; fi
      break; fi
    git -C "$W" show "origin/$IN:$f" > "$Q/$n.md.tmp"
    if grep -q '^QUIET: yes' "$Q/$n.md.tmp" && { [ "$running" -gt 0 ] || [ "$load" -gt 20 ]; }; then rm -f "$Q/$n.md.tmp"; continue; fi   # timing jobs wait for an idle Mac
    if ls "$Q"/*.running >/dev/null 2>&1 && grep -l '^QUIET: yes' $(ls "$Q"/*.running | sed 's/\.running$/.md/') 2>/dev/null | grep -q .; then rm -f "$Q/$n.md.tmp"; break; fi   # nothing starts beside a quiet job
    if grep -q '^GPU: yes' "$Q/$n.md.tmp" && grep -l '^GPU: yes' $(ls "$Q"/*.running 2>/dev/null | sed 's/\.running$/.md/') 2>/dev/null | grep -q .; then
      rm -f "$Q/$n.md.tmp"; continue   # another GPU task is running; try next round
    fi
    mv "$Q/$n.md.tmp" "$Q/$n.md"; touch "$Q/$n.running"; log "launch $n"
    ( bash "$RUN" "$Q/$n.md"; echo "rc=$?" > "$Q/$n.exit"; rm -f "$Q/$n.running" ) &
  done
  # status: every round, publish which tasks are running and the log tail, so the director can see launches
  { date '+%F %T'; echo "running:"; ls "$Q"/*.running 2>/dev/null | xargs -n1 basename 2>/dev/null; echo "launched (no exit yet) / finished:"; ls "$Q"/*.md 2>/dev/null | wc -l; echo; tail -150 "$LOG"; } > "$H/status.txt"
  mkdir -p "$O/status"; if ! cmp -s "$H/status.txt" "$O/status/watcher.txt"; then cp "$H/status.txt" "$O/status/watcher.txt"
    (cd "$O" && git fetch -q origin "$OUT" 2>/dev/null && git reset -q --soft FETCH_HEAD; git add status && git commit -qm "watcher status" && git push -q origin "HEAD:$OUT") >> "$LOG" 2>&1 || true; fi
  sleep 120
done
log "watcher stopped"
