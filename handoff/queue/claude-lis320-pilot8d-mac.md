BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Reading thread (Claude) job, no LLM builder (rungo5 BASH-ONLY route, Director 2bf4f9ea7). lis-320 pilot 8 (seed 328, GPT-6 Luna writer via scripts/claude_luna_codex.py, 60 dialogs, 3 parallel calls, $0) moved here because both builder attempts (lis320-pilot8-mac, lis320-pilot8b-mac) died on "Rate limit exceeded" before any step ran. Re-run of claude-lis320-pilot8c-mac, which stopped at its orphan check because the pattern also matched the stalled pilot8b opencode builder, whose prompt text names the script (no wording python was running). Now only non-opencode processes count, and outputs go to pilot8d/ so a late pilot8b builder cannot overwrite them. Same steps and files as origin/main:handoff/queue/lis320-pilot8b-mac.md; marks fixed in artifacts/claude-lis320-20260926/ADDENDUM-10-luna-pilot7-fixes.md. Touches the stop file of its own job lis320-pilot8b-mac (no kill), waits on any wording run it left (never kills it), then runs in a mktemp tree of origin/main. Never reads ~/.codex, keys or auth files. Nothing is trained.
```bash
set -u -o pipefail
Q=~/premonition-watch/queue
W=$(pwd)
DEST="$W/artifacts/claude-lis320-20260926/pilot8d"
UV=$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)
[ -n "$UV" ] || { echo "STOP: uv not found"; exit 6; }
PY() { "$UV" run --offline --no-project --python 3.12 python -B "$@"; }
touch "$Q/lis320-pilot8b-mac.stop"; echo "stop file for lis320-pilot8b-mac present $(date -u +%FT%TZ); its opencode builders (not killed):"; pgrep -fl "mimo:lis320-pilot8b-mac" | cut -c1-40
w=0
orph() { pgrep -fl "claude_lis320_luna2.py --seeds" | grep -v -e opencode -e rungo; }
while orph >/dev/null; do
  [ $w -eq 0 ] && { echo "ORPHAN wording run found (left running, waiting):"; orph | cut -c1-200; }
  w=$((w+1)); [ $w -gt 30 ] && { echo "STOP: orphan still running after 15 min; no new run started $(date -u +%FT%TZ)"; exit 3; }
  sleep 30
done
[ $w -gt 0 ] && echo "orphan finished after about $((w*30)) s; starting a fresh run"
git fetch -q origin main || { echo "STOP: git fetch failed"; exit 4; }
COMMIT=$(git rev-parse origin/main)
D=$(mktemp -d); O=artifacts/claude-lis320-20260926/pilot8d; R="$D/RESULTS.md"
trap 'mkdir -p "$DEST"; cp -f "$D/$O"/* "$DEST"/ 2>/dev/null; cp -f "$R" "$DEST/RESULTS.md" 2>/dev/null; rm -rf "$D"; [ -e "$D" ] && echo "tree NOT removed: $D" || echo "tree removed: $D"; ls -l "$DEST" | awk "{print \$5, \$NF}"' EXIT
git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-chatdev-20260926 artifacts/claude-e2e331-dev-20260924 | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
cd "$D"; mkdir -p "$O"
say() { echo "$@" | tee -a "$R"; }
run() { echo '```' >> "$R"; "$@" 2>&1 | tee -a "$R"; local rc=$?; echo '```' >> "$R"; return $rc; }
say "# lis-320 pilot 8 (seed 328, GPT-6 Luna, luna2 + check_we3) - BASH-ONLY job claude-lis320-pilot8d-mac"
say ""; say "origin/main: $COMMIT"; say "start: $(date -u +%FT%TZ)"; say "orphan wait loops: $w"
say "## seals"
for s in 6 8 9 10; do run shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-$s.sha256.txt || { say "STOP: seal $s failed"; exit 5; }; done
say "## selftests"
for t in claude_lis320_luna2 claude_lis320_seed_cr claude_lis320_check_we3 claude_lis320_rawcheck2; do run PY scripts/$t.py --selftest || { say "STOP: selftest $t failed"; exit 5; }; done
run PY scripts/claude_luna_codex.py --selftest || { say "STOP: live helper selftest failed"; exit 5; }
say "## seeds"
run PY scripts/claude_lis320_seed_cr.py --seed 328 --n 60 --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl || { say "STOP: seeds failed"; exit 5; }
say "## wording"
T0=$(date -u +%s); say "wording start: $(date -u +%FT%TZ) | $(uptime | sed 's/.*load/load/')"
PY scripts/claude_lis320_luna2.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 3 --max-minutes 40 > $O/glm.log 2>&1; rcw=$?
T1=$(date -u +%s); say "wording end: $(date -u +%FT%TZ) rc=$rcw | $(uptime | sed 's/.*load/load/')"
ROWS=$( [ -f $O/raw.jsonl ] && wc -l < $O/raw.jsonl | tr -d ' ' || echo 0)
say "raw rows: $ROWS; minutes: $(( (T1-T0)/60 )); dialogs per minute: $(awk -v r=$ROWS -v s=$((T1-T0)) 'BEGIN{printf "%.2f", (s>0? r*60/s : 0)}')"
say "last line of glm.log:"; run tail -1 $O/glm.log
say "call failed lines: $(grep -c 'call failed' $O/glm.log)"
say "distinct failure starts:"; run sh -c "grep -iE 'call failed|try [0-9]+ failed|Traceback|Error' $O/glm.log | sed -E 's/dlg[-_A-Za-z0-9]*//g' | cut -c1-120 | sort | uniq -c | sort -rn | head -8"
say "## rawcheck2"
run PY scripts/claude_lis320_rawcheck2.py --raw $O/raw.jsonl --seeds $O/seeds.jsonl --models gpt-6-luna || say "ROUTE-FAIL (steps below still run)"
say "## check_we3"
PY scripts/claude_lis320_check_we3.py --seeds $O/seeds.jsonl --raw $O/raw.jsonl --out $O/kept.jsonl --drops $O/drops.jsonl > $O/check.json 2> $O/check.err; say "check rc=$?"
run cat $O/check.json; [ -s $O/check.err ] && run tail -5 $O/check.err
say "## style"
run PY scripts/claude_lis320_style.py --kept $O/kept.jsonl --out $O/style.json
say "end: $(date -u +%FT%TZ)"
```
PUSH: artifacts/claude-lis320-20260926/pilot8d
