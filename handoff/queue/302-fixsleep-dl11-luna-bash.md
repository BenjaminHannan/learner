BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Fix-sleep thread (Claude) job, no LLM builder (BASH-ONLY route). Rerun of 300-fixsleep-dl11-luna, whose LLM builder returned empty replies 7 times (rc=5, no data). Same task, same sealed script, unchanged: dl-11 Luna stage (5 Q frames plus about 600 everyday number questions from GPT-6 Luna via scripts/claude_luna_effort.py, one call at a time, $0). Runs in a mktemp tree of the sealed commit. Never reads ~/.codex, keys or auth files; prints counts only, never reply text; kills nothing it did not start. Nothing is trained.
```bash
set -u -o pipefail
W=$(pwd); A=artifacts/claude-dl11-20260927
UV=$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)
[ -n "$UV" ] || { echo "STOP: uv not found"; exit 6; }
PY() { "$UV" run --offline --no-project --python 3.12 python -B "$@"; }
git fetch -q origin main && git fetch -q origin +refs/heads/builder-outbox:refs/remotes/origin/builder-outbox || { echo "STOP: git fetch failed"; exit 4; }
for b in origin/main origin/builder-outbox; do for p in $A/luna/luna_texts.json $A/luna-stop.json; do git cat-file -e $b:$p 2>/dev/null && { echo "DUPLICATE: $b has $p"; exit 0; }; done; done
pgrep -f "claude_dl11_luna.py --out" >/dev/null && { echo "STOP: a dl11 luna run is already going; none started"; exit 3; }
COMMIT=$(git log -1 --format=%H origin/main -- $A/SEAL.sha256.txt); echo "COMMIT $COMMIT"
D=$(mktemp -d); DEST="$W/$A"
trap 'mkdir -p "$DEST/luna"; cp -f "$D/$A/luna/luna_texts.json" "$DEST/luna/" 2>/dev/null; cp -f "$D/$A/luna-stop.json" "$DEST/" 2>/dev/null; cp -f "$D/luna-log.txt" "$DEST/luna/luna-log.txt" 2>/dev/null; rm -rf "$D"; ls -l "$DEST" "$DEST/luna" | awk "{print \$5, \$NF}"' EXIT
git archive $COMMIT scripts $A artifacts/claude-glmframes-20260926 | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
cd "$D"
shasum -a 256 -c $A/SEAL.sha256.txt || { echo "SEAL-MISMATCH"; exit 5; }
PY scripts/claude_dl11_luna.py --selftest 2>&1 | tail -3
PY scripts/claude_dl11_luna.py --selftest 2>&1 | grep -q "dl11 luna selftest ok" || { echo "STOP: selftest failed"; exit 5; }
T0=$(date -u +%s); echo "run start $(date -u +%FT%TZ)"
PY scripts/claude_dl11_luna.py --out $A/luna > luna-log.txt 2>&1 &
P=$!
while kill -0 $P 2>/dev/null; do
  [ $(( $(date -u +%s) - T0 )) -gt 10800 ] && { kill $P; sleep 5; pkill -P $P 2>/dev/null; echo "TIME-STOP pid $P"; break; }
  sleep 30
done
wait $P; RC=$?
echo "run end $(date -u +%FT%TZ) rc=$RC minutes=$(( ($(date -u +%s)-T0)/60 ))"
grep -E "^\[dl11-luna\] wrote|STOP-LUNA" luna-log.txt | tail -2
echo "log lines: $(wc -l < luna-log.txt | tr -d ' '); error lines: $(grep -ciE 'error|failed|Traceback' luna-log.txt); rate/usage lines: $(grep -ciE 'rate.?limit|usage limit|quota|too many requests' luna-log.txt)"
exit $RC
```
PUSH: artifacts/claude-dl11-20260927/luna artifacts/claude-dl11-20260927/luna-stop.json
