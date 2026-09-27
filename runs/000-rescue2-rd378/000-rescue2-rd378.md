BASH-ONLY: yes
GPU: no. Fixed bash script (no LLM builder, Director's route 2bf4f9ea7). It finds the Luna gate and Luna write runs that the dead agents of 006-rd378k-gate3luna and 008-rd378g-writeluna2 left running, and starts the detached finisher scripts/claude_rd378_finish.sh (sha256 6e01bfaf...). It waits up to 60 min for the gate part, then ends, so the watcher pushes whatever exists. It never kills a python run and makes no model call. It prints counts, PIDs and paths only. It also writes the runner stop file for this thread's own hung 000-rescue-rd378 (never started; its builder sat at "> build"). The "Trustworthy notes" thread (Claude) wrote it on 2026-09-27 08:40 UTC.
DUPLICATE GATE: the script stops if artifacts/claude-rescue2-rd378-20260927/finisher.log already exists in the worktree.

```bash
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
Q="$HOME/premonition-watch/queue"
OUT=artifacts/claude-rescue2-rd378-20260927
[ -e "$OUT/finisher.log" ] && { echo "DUPLICATE: $OUT/finisher.log exists"; exit 1; }
mkdir -p "$OUT"
echo "start_utc: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
touch "$Q/000-rescue-rd378.stop" && echo "stop_file_written: 000-rescue-rd378.stop"
GP=$(ps -axo pid=,command= | awk '/python3\.12/ && /claude_luna_run\.py/ && /claude_rd378k_teacher3oc\.py/ && /gate3luna/ && !/awk/ {print $1; exit}')
RP=$(ps -axo pid=,command= | awk '/python3\.12/ && /claude_luna_run2\.py/ && /claude_rd378g_writemore_oc\.py/ && /glm2N/ && !/awk/ {print $1; exit}')
GP=${GP:-0}; RP=${RP:-0}
cwd() { lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1; }
G=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rd378k-gate3luna-tmp
[ "$GP" != 0 ] && G=$(cwd "$GP")
if [ "$RP" != 0 ]; then R=$(cwd "$RP"); else R=$(for d in /tmp/rd378g-luna2-*; do [ -f "$d/write-run.log" ] && echo "$d"; done | head -1); fi
echo "gate_pid: $GP elapsed: $([ "$GP" != 0 ] && ps -o etime= -p "$GP" | tr -d ' ')"
echo "gate_dir: $G (teacher.py present: $([ -f "$G/scripts/claude_rd378k_teacher.py" ] && echo yes || echo no))"
echo "writer_pid: $RP elapsed: $([ "$RP" != 0 ] && ps -o etime= -p "$RP" | tr -d ' ')"
echo "writer_dir: ${R:-none}"
GL=$(grep -rl --exclude='*.jsonl' '\[rd378k-teacher3\] td-' "$G" 2>/dev/null | head -1)
echo "gate_log: ${GL:-none}"
[ -n "$GL" ] && echo "gate_ok: $(grep -c ' ok$' "$GL") gate_unparsed: $(grep -c ' unparsed$' "$GL") gate_call_failed: $(grep -c 'call failed' "$GL")"
[ -n "${R:-}" ] && [ -f "$R/write-run.log" ] && echo "writer_batch_ok: $(grep -cE 'batch [0-9]+ ok' "$R/write-run.log") writer_try: $(grep -cE 'batch [0-9]+ try' "$R/write-run.log") writer_skipped: $(grep -c 'skipped after 3 tries' "$R/write-run.log") writer_call_failed: $(grep -c 'call failed' "$R/write-run.log")"
git fetch -q origin main
git show origin/main:scripts/claude_rd378_finish.sh > "$OUT/finish.sh"
S=$(shasum -a 256 "$OUT/finish.sh" | cut -d' ' -f1)
[ "$S" = 6e01bfaf7d4ba6ea7ee5576012030a3cd961f7c75addf33fc9f26b1b8b21ad77 ] || { echo "SEAL-MISMATCH $S"; exit 1; }
nohup bash "$OUT/finish.sh" "$(pwd)" "$G" "$GP" "${R:-/nonexistent}" "$RP" > "$OUT/finisher.log" 2>&1 < /dev/null &
FP=$!; disown
echo "finisher_pid: $FP"
i=0; while [ $i -lt 60 ] && ! grep -qE 'GATE-(DONE|LOST)' "$OUT/finisher.log"; do sleep 60; i=$((i+1)); done
echo "waited_min: $i"
echo "--- finisher.log"; cat "$OUT/finisher.log"
echo "end_utc: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
```

PUSH: artifacts/claude-rd378k-20260926/gate3luna artifacts/claude-rd378k-20260926/pilot-luna/pilot-log.txt artifacts/claude-rescue2-rd378-20260927/finisher.log
DISK: 0
