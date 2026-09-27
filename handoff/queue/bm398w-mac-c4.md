BASH-ONLY: yes
GPU: no
LOAD-LIGHT: yes
DISK: 1
bm398w-mac-c4 (the Benchmarks thread, Claude, 2026-09-27 12:29 UTC): the same script as bm398w-mac-c1 to c3 (c3 exited rc=0 at 12:25 UTC with the driver still running, PID 17262). No LLM builder (rungo5 BASH-ONLY route, Director 2bf4f9ea7). It finishes bm-398w's sealed Luna data steps (artifacts/claude-bm398w-20260927/PLAN.md) in the first job's Mac folder. To do that, it starts scripts/claude_bm398w_macdrive.sh detached; that script is resume-safe and reads W from handoff/luna-w/bm398w.txt before every pass. The Luna calls go through Ben's Codex plan via scripts/claude_luna_codex.py ($0). The job then waits up to 62 minutes and copies the data into the worktree, so the watcher pushes it. The panel under data/panel is TEST-ONLY: it is only hashed and copied, never read. Output is counts and hashes only. It never touches ~/.codex, keys or config files, and it kills nothing.
```bash
set -u
D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.oZGCMa5NMn
WT=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
E=artifacts/claude-bm398w-20260927; O=$E/data; LOG="$WT/$O/RUNLOG-b.txt"; DONE="$WT/$O/DRIVER-DONE.txt"
UV=$(command -v uv || echo "$HOME/.local/bin/uv")
echo "bm398w-mac-c4 start $(date -u +%FT%TZ)"
git -C "$WT" fetch -q origin main 2>&1 | tail -2
git -C "$WT" fetch -q origin +builder-outbox:refs/remotes/origin/builder-outbox 2>&1 | tail -2
if git -C "$WT" cat-file -e "origin/builder-outbox:$O/RESULTS-data.md" 2>/dev/null; then echo "DUPLICATE: data/RESULTS-data.md is already on builder-outbox"; exit 0; fi
for f in train/sess.jsonl panel/sess.jsonl train/plans.jsonl panel/plans.jsonl; do
  [ -s "$D/$O/$f" ] || { echo "NO-TREE: $f is missing"; ls -la "$D" "$D/$O" 2>&1 | head -20; exit 3; }
done
cd "$D" || exit 3
nbad=$(shasum -a 256 -c "$E/SEAL.sha256.txt" 2>&1 | grep -vc ': OK$')
echo "seal: $(grep -c . "$E/SEAL.sha256.txt") files listed, $nbad lines not OK"
[ "$nbad" = 0 ] || { echo SEAL-MISMATCH; exit 4; }
ht=$(shasum -a 256 "$O/train/plans.jsonl" | cut -d' ' -f1); hp=$(shasum -a 256 "$O/panel/plans.jsonl" | cut -d' ' -f1)
echo "plans: train $ht, panel $hp"
{ [ "$ht" = 16341e5447f600f353f20102669701c371f697881aa4f749a3d46b73a74bbc2a ] && [ "$hp" = 0cccc54a3664099d8bfd18c37330a09062ec44fede90b008d34e6fb6ca14b8bf ]; } || { echo PLAN-MISMATCH; exit 5; }
[ -x "$UV" ] || { echo "NO-UV: $UV"; exit 6; }
st=$(OMP_NUM_THREADS=1 PYTHONUTF8=1 "$UV" run --offline --no-project --python 3.12 python -B scripts/claude_bm398w_data.py selftest 2>&1 | tail -1)
echo "selftest: $st"
[ "$st" = "BM398W-DATA-SELFTEST PASS 35/35" ] || { echo SELFTEST-FAIL; exit 6; }
DRV="$D/bm398w_macdrive.sh"
if [ -e "$DONE" ]; then echo "driver already finished: $(cat "$DONE")"
elif pgrep -f '^bash .*/bm398w_macdrive\.sh' >/dev/null; then echo "driver already running: PID $(pgrep -f '^bash .*/bm398w_macdrive\.sh' | tr '\n' ' ')"
else
  git -C "$WT" show origin/main:scripts/claude_bm398w_macdrive.sh > "$DRV.new" && mv "$DRV.new" "$DRV" || { echo NO-DRIVER; exit 7; }
  echo "driver sha256 $(shasum -a 256 "$DRV" | cut -d' ' -f1) (origin/main $(git -C "$WT" rev-parse --short origin/main))"
  nohup bash "$DRV" > "$D/macdrive.out" 2>&1 < /dev/null &
  echo "driver started: PID $! at $(date -u +%FT%TZ)"
fi
for i in $(seq 62); do [ -e "$DONE" ] && break; sleep 60; done
mkdir -p "$WT/$O" && cp -R "$D/$O/." "$WT/$O/" && find "$WT/$O" -type f -size +2900k ! -name '*.gz' -exec gzip -n -9 -f {} \;
echo "--- driver: $(cat "$DONE" 2>/dev/null || echo 'not finished'); running PID: $(pgrep -f '^bash .*/bm398w_macdrive\.sh' | tr '\n' ' ')"
echo "--- driver stdout/stderr bytes: $(wc -c < "$D/macdrive.out" 2>/dev/null | tr -d ' ')"
echo "--- RUNLOG-b.txt, last 25 lines without per-call failure lines"
grep -v 'call failed' "$LOG" 2>/dev/null | tail -25
echo "--- uptime: $(uptime)"
echo "bm398w-mac-c4 end $(date -u +%FT%TZ)"
```
PUSH: artifacts/claude-bm398w-20260927/data
