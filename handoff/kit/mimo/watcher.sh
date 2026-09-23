#!/bin/bash
# watcher.sh: runs Muse builder tasks that the cloud director pushes to GitHub, and pushes the results back.
# The director (a cloud Claude session) cannot reach opencode.ai or BensPC, so this runs on Ben's Mac.
# Every 120 s it:
#   1. fetches the director's branch and looks for new task files in handoff/queue/*.md;
#   2. copies each new one to $Q and launches rungo4.sh on it (at most $MAX at once; a task whose
#      file contains the line "GPU: yes" waits until no other GPU task is running);
#   3. when a task finishes (.done, or rungo4 exits), copies its reply/err files plus the paths listed
#      on its "PUSH:" lines (files under 5 MB only; never notebook/, never weights) into the outbox
#      clone and pushes them to the branch $OUT.
# Stop it with: touch ~/premonition-watch/STOP
set -u
export OPENCODE_CONFIG_CONTENT='{"snapshot": false}'
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
H=$HOME/premonition-watch; Q=$H/queue; O=$H/outbox
IN=main; OUT=builder-outbox; MAX=${MAX:-3}
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
  for e in "$Q"/*.exit; do [ -e "$e" ] || continue; n=$(basename "$e" .exit); [ -e "$Q/$n.pushed" ] || [ -e "$Q/$n.running" ] || publish "$n"; done
  for f in $(git -C "$W" ls-tree --name-only "origin/$IN" handoff/queue/ 2>/dev/null | grep '\.md$'); do
    n=$(basename "$f" .md)
    [ -e "$Q/$n.md" ] && continue
    running=$(ls "$Q"/*.running 2>/dev/null | wc -l)
    [ "$running" -ge "$MAX" ] && break
    git -C "$W" show "origin/$IN:$f" > "$Q/$n.md.tmp"
    if grep -q '^GPU: yes' "$Q/$n.md.tmp" && grep -l '^GPU: yes' $(ls "$Q"/*.running 2>/dev/null | sed 's/\.running$/.md/') 2>/dev/null | grep -q .; then
      rm -f "$Q/$n.md.tmp"; continue   # another GPU task is running; try next round
    fi
    mv "$Q/$n.md.tmp" "$Q/$n.md"; touch "$Q/$n.running"; log "launch $n"
    ( bash "$RUN" "$Q/$n.md"; echo "rc=$?" > "$Q/$n.exit"; rm -f "$Q/$n.running" ) &
  done
  sleep 120
done
log "watcher stopped"
