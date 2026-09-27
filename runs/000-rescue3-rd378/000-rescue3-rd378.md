BASH-ONLY: yes
GPU: no. Fixed bash script, no LLM builder, no model call. The "Trustworthy notes" thread (Claude) wrote it on 2026-09-27 09:51 UTC. It fixes its own 000-rescue2-rd378, which matched the wrong process: its search for the Luna gate matched the prompt text of this thread's hung 000-rescue-rd378 builder (opencode PID 52568, title mimo:000-rescue-rd378.go4.*), because the real gate python had already ended. So its finisher waits on that builder and points at the wrong folder. This job:
1. finds the gate and writer pythons by EXECUTABLE name first (python), then by their command line, so a builder whose prompt quotes these words never matches;
2. stops this thread's own hung builder of 000-rescue-rd378 (opencode whose title starts mimo:000-rescue-rd378.go; its stop file was written 08:42 UTC, so its runner then ends with no retry): TERM, then -9 after 10 s;
3. stops this thread's own wrong finisher from 000-rescue2-rd378 (bash processes running artifacts/claude-rescue2-rd378-20260927/finish.sh and their sleep children only), after its writer half is idle; waits for any writer tag step to end;
4. starts the same sealed finisher (scripts/claude_rd378_finish.sh, sha256 6e01bfaf...) detached with the right folders: gate = job 006's temp tree, writer = job 008's temp tree and its still-running python;
5. waits up to 60 min for the gate part, prints the finisher log and the agree lines (counts only), then ends so the watcher pushes the gate files.
It never touches the Luna write python, the watcher, other jobs or BensPC.
DUPLICATE GATE: stops if artifacts/claude-rescue3-rd378-20260927/finisher.log or artifacts/claude-rd378k-20260926/gate3luna already exists in the worktree.

```bash
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
OLD=artifacts/claude-rescue2-rd378-20260927
OUT=artifacts/claude-rescue3-rd378-20260927
K=artifacts/claude-rd378k-20260926
G=/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rd378k-gate3luna-tmp
R=/private/tmp/rd378g-luna2-tFm5EW
[ -e "$OUT/finisher.log" ] && { echo "DUPLICATE: $OUT/finisher.log exists"; exit 1; }
[ -e "$K/gate3luna" ] && { echo "STOP: $K/gate3luna already exists in the worktree; nothing touched"; exit 1; }
mkdir -p "$OUT"
echo "start_utc: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
byexe() { ps -axo pid=,comm= | awk -v e="$1" 'tolower($2) ~ e {print $1}' | while read -r p; do c=$(ps -o command= -p "$p" 2>/dev/null); case "$c" in *"$2"*"$3"*) echo "$p";; esac; done; }
desc() { echo "$1"; for c in $(ps -axo pid=,ppid= | awk -v p="$1" '$2==p {print $1}'); do desc "$c"; done; }
GP=$(byexe python claude_rd378k_teacher3oc.py gate3luna | head -1); GP=${GP:-0}
RP=$(byexe python claude_rd378g_writemore_oc.py glm2N | head -1); RP=${RP:-0}
echo "gate_python: $GP writer_python: $RP"
echo "gate_dir_ok: $([ -d "$G/$K" ] && echo yes || echo no) writer_dir_ok: $([ -f "$R/write-run.log" ] && echo yes || echo no)"
GL="$G/gate-console.log"
[ -f "$GL" ] && echo "gate_ok: $(grep -c ' ok$' "$GL") gate_unparsed: $(grep -c ' unparsed$' "$GL") gate_call_failed: $(grep -c 'call failed' "$GL") gate_json_lines: $(grep -c '^{' "$GL")"
echo "gate_labels_lines: $([ -f "$G/$K/gate3luna/labels.jsonl" ] && wc -l < "$G/$K/gate3luna/labels.jsonl" | tr -d ' ' || echo none)"
[ -f "$R/write-run.log" ] && echo "writer_batch_ok: $(grep -cE 'batch [0-9]+ ok' "$R/write-run.log") writer_try: $(grep -cE 'batch [0-9]+ try' "$R/write-run.log") writer_skipped: $(grep -c 'skipped after 3 tries' "$R/write-run.log") writer_call_failed: $(grep -c 'call failed' "$R/write-run.log")"
# 1. this thread's hung builder of 000-rescue-rd378
for p in $(byexe opencode 'mimo:000-rescue-rd378.go' ''); do echo "stop_builder: $p elapsed $(ps -o etime= -p "$p" | tr -d ' ')"; kill "$p" 2>/dev/null; done
sleep 10
for p in $(byexe opencode 'mimo:000-rescue-rd378.go' ''); do echo "builder_still_alive: $p (kill -9)"; kill -9 "$p" 2>/dev/null; done
# 2. this thread's wrong finisher (rescue2)
if [ "$RP" = 0 ]; then i=0; while [ $i -lt 15 ] && ! grep -qE 'WRITER-(DONE|LOST)' "$OLD/finisher.log"; do sleep 60; i=$((i+1)); done; echo "old_writer_wait_min: $i"; fi
oldf() { ps -axo pid=,comm= | awk 'tolower($2) ~ /bash/ {print $1}' | while read -r p; do [ "$p" = $$ ] && continue; c=$(ps -o command= -p "$p" 2>/dev/null); case "$c" in "bash $OLD/finish.sh "*) echo "$p";; esac; done; }
OF=$(oldf)
ALL=$(for p in $OF; do desc "$p"; done | sort -u)
echo "old_finisher_pids: $(echo $ALL)"
for p in $ALL; do c=$(ps -o comm= -p "$p" 2>/dev/null); case "$c" in *bash|*sleep) kill "$p" 2>/dev/null;; *) echo "not_killed: $p $c";; esac; done
sleep 5
echo "old_finisher_left: $(oldf | wc -l | tr -d ' ')"
i=0; while [ -n "$(byexe 'uv|python' claude_rd378g_tagwriter.py '')" ] && [ $i -lt 60 ]; do sleep 10; i=$((i+1)); done; echo "tag_wait_10s: $i"
# 3. the sealed finisher with the right folders
git fetch -q origin main
git show origin/main:scripts/claude_rd378_finish.sh > "$OUT/finish.sh"
S=$(shasum -a 256 "$OUT/finish.sh" | cut -d' ' -f1)
[ "$S" = 6e01bfaf7d4ba6ea7ee5576012030a3cd961f7c75addf33fc9f26b1b8b21ad77 ] || { echo "SEAL-MISMATCH $S"; exit 1; }
nohup bash "$OUT/finish.sh" "$(pwd)" "$G" "$GP" "$R" "$RP" > "$OUT/finisher.log" 2>&1 < /dev/null &
FP=$!; disown
echo "finisher_pid: $FP"
i=0; while [ $i -lt 60 ] && ! grep -qE 'GATE-(DONE|LOST)' "$OUT/finisher.log"; do sleep 60; i=$((i+1)); done
echo "waited_min: $i"
grep -q 'GATE-LOST' "$OUT/finisher.log" && [ -f "$GL" ] && cp "$GL" "$OUT/gate-console.txt"
echo "--- finisher.log"; cat "$OUT/finisher.log"
[ -f "$K/gate3luna/agree.txt" ] && { echo "--- agree.txt"; cat "$K/gate3luna/agree.txt"; }
ls -l "$K/gate3luna" 2>/dev/null | awk '{print $5, $NF}'
echo "end_utc: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
```

PUSH: artifacts/claude-rd378k-20260926/gate3luna artifacts/claude-rd378k-20260926/pilot-luna/pilot-log.txt artifacts/claude-rescue3-rd378-20260927
DISK: 0
