#!/bin/bash
# rd-378 rescue finisher (Trustworthy notes thread, 2026-09-27). New file.
# 006-rd378k-gate3luna and 008-rd378g-writeluna2 lost their job agents to the agent model's "Rate limit exceeded" while
# their nohup'd python runs (the Luna gate and the Luna write) kept going in the jobs' temp dirs, where nothing copies
# the results out. Started detached by 009-rd378-rescue, this waits for each python PID to exit, then runs the steps
# the dead agents would have run next (gate: the two agree lines; writer: the writer tag) from the same temp dir, with
# the same sealed code, and copies the outputs into the watcher's worktree paths. A later short job pushes them. It
# never kills anything, calls no model, and prints no row text.
# usage: claude_rd378_finish.sh WORKTREE GATE_DIR GATE_PID WRITER_DIR WRITER_PID   (PID 0 = not running)
W=$1; G=$2; GP=$3; R=$4; RP=$5
K=artifacts/claude-rd378k-20260926; N=artifacts/claude-rd378g-20260926
run() { uv run --offline --no-project --python 3.12 python -B "$@"; }
wait_pid() { while [ "$1" != 0 ] && kill -0 "$1" 2>/dev/null; do sleep 60; done; }
say() { echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*"; }

gate() {
  wait_pid "$GP"
  if [ ! -s "$G/$K/gate3luna/labels.jsonl" ]; then say "GATE-LOST: no $K/gate3luna/labels.jsonl in the gate dir"; return; fi
  mkdir -p "$W/$K/gate3luna" "$W/$K/pilot-luna"
  ( cd "$G" && run scripts/claude_rd378k_teacher.py agree --labels $K/gate3luna/labels.jsonl \
        --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl \
      && run scripts/claude_rd378k_teacher.py agree --labels $K/gate3luna/labels_passA.jsonl \
        --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl ) > "$W/$K/gate3luna/agree.txt" 2>&1
  for f in labels.jsonl labels_passA.jsonl failures.jsonl; do cp "$G/$K/gate3luna/$f" "$W/$K/gate3luna/$f"; done
  log=$(grep -rl --exclude='*.jsonl' '\[rd378k-teacher3\] td-' "$G" 2>/dev/null | head -1)
  [ -n "$log" ] && cp "$log" "$W/$K/gate3luna/teacher-log.txt"
  [ -f "$G/$K/pilot-luna/pilot-log.txt" ] && cp "$G/$K/pilot-luna/pilot-log.txt" "$W/$K/pilot-luna/pilot-log.txt"
  say "GATE-DONE labels $(wc -l < "$W/$K/gate3luna/labels.jsonl") failures $(wc -l < "$W/$K/gate3luna/failures.jsonl") log ${log:+found}"
}

writer() {
  wait_pid "$RP"
  mkdir -p "$W/$N/glm2N"
  [ -f "$R/$N/glm2N/diag-log.txt" ] && cp "$R/$N/glm2N/diag-log.txt" "$W/$N/glm2N/diag-log.txt"
  [ -f "$R/write-run.log" ] && cp "$R/write-run.log" "$W/$N/glm2N/teacher-log.txt"
  if [ ! -s "$R/$N/glm2N/notes_w1.jsonl" ]; then say "WRITER-LOST: no $N/glm2N/notes_w1.jsonl in the writer dir"; return; fi
  ( cd "$R" && run scripts/claude_rd378g_tagwriter.py tag --have $N/glm/notes_w1.jsonl --in $N/glm2N/notes_w1.jsonl \
      --out $N/glm2N/notes_w1_tagged.jsonl ) > "$W/$N/glm2N/tag.txt" 2>&1
  for f in notes_w1.jsonl notes_w1_tagged.jsonl; do [ -f "$R/$N/glm2N/$f" ] && cp "$R/$N/glm2N/$f" "$W/$N/glm2N/$f"; done
  say "WRITER-DONE dialogs $(wc -l < "$W/$N/glm2N/notes_w1.jsonl") tagged $(wc -l < "$W/$N/glm2N/notes_w1_tagged.jsonl" 2>/dev/null)"
}

say "START gate_pid=$GP writer_pid=$RP"
gate & writer & wait
say "END"
