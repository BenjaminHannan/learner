BASH-ONLY: yes
GPU: no. Fixed bash script, no LLM builder, no model call. The "Trustworthy notes" thread (Claude) wrote it on 2026-09-27 11:38 UTC. It is the second try of 000-collect-rd378g, which waited its full 70 min while the write had 19 of 21 batches done (11:37 UTC). The sealed finisher that 000-rescue3-rd378 started (scripts/claude_rd378_finish.sh) waits for the Luna write python of 008-rd378g-writeluna2 to end. It then runs the writer tag step (scripts/claude_rd378g_tagwriter.py) in job 008's temp tree and copies artifacts/claude-rd378g-20260926/glm2N/ into this worktree. This job only waits up to 70 min for that, prints counts and hashes (never dialog or note text), and ends so the watcher pushes glm2N/. It never kills or starts anything.
DUPLICATE GATE: stops if artifacts/claude-rd378g-20260926/glm2N/collect.txt already exists in the worktree.

```bash
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
F=artifacts/claude-rescue3-rd378-20260927/finisher.log
N=artifacts/claude-rd378g-20260926/glm2N
R=/private/tmp/rd378g-luna2-tFm5EW
[ -e "$N/collect.txt" ] && { echo "DUPLICATE: $N/collect.txt exists"; exit 1; }
[ -f "$F" ] || { echo "NO-FINISHER-LOG: $F"; exit 1; }
echo "start_utc: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
i=0; while [ $i -lt 70 ] && ! grep -qE 'WRITER-(DONE|LOST)' "$F"; do sleep 60; i=$((i+1)); done
echo "waited_min: $i"
echo "--- finisher.log"; cat "$F"
[ -f "$R/write-run.log" ] && echo "writer_batch_ok: $(grep -cE 'batch [0-9]+ ok' "$R/write-run.log") writer_try: $(grep -cE 'batch [0-9]+ try' "$R/write-run.log") writer_skipped: $(grep -c 'skipped after 3 tries' "$R/write-run.log") writer_call_failed: $(grep -c 'call failed' "$R/write-run.log") writer_json_lines: $(grep -c '^{' "$R/write-run.log")"
if grep -q 'WRITER-DONE' "$F"; then
  echo "--- tag.txt"; cat "$N/tag.txt"
  wc -l "$N/notes_w1.jsonl" "$N/notes_w1_tagged.jsonl"
  shasum -a 256 "$N/notes_w1.jsonl" "$N/notes_w1_tagged.jsonl"
  date -u '+%Y-%m-%d %H:%M:%S UTC' > "$N/collect.txt"
else
  echo "WRITER-NOT-DONE (a later collect job is needed)"
fi
ls -l "$N" 2>/dev/null | awk '{print $5, $NF}'
echo "end_utc: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
```

PUSH: artifacts/claude-rd378g-20260926/glm2N artifacts/claude-rescue3-rd378-20260927/finisher.log
DISK: 0
