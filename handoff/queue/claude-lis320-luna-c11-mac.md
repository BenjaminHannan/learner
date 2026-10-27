BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Reading thread (Claude) job, no LLM builder (rungo5 BASH-ONLY route). lis-320 Luna full run, chunk 11 (seed 324, 6000 dialogs; GPT-6 Luna via scripts/claude_luna_codex.py, LW parallel calls (6 from chunk 2, Director 09:56 UTC; 3 after any rate-limit sign), $0). Mechanics fixed in artifacts/claude-lis320-20260926/ADDENDUM-11-luna-full-run-chunks.md and ADDENDUM-12-luna-six-calls.md (sealed). Runs in a mktemp tree of origin/main; reads earlier chunks from origin/builder-outbox (read only). Never reads ~/.codex, keys or auth files; kills nothing. Nothing is trained.
```bash
set -u -o pipefail
K=11; LW=6; N=6000
W=$(pwd)
F=artifacts/claude-lis320-20260926/full-luna
DEST="$W/$F/chunk$K"
UV=$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)
[ -n "$UV" ] || { echo "STOP: uv not found"; exit 6; }
PY() { "$UV" run --offline --no-project --python 3.12 python -B "$@"; }
orph() { for p in $(pgrep -f "claude_lis320_luna[23].py --seeds"); do c=$(ps -p "$p" -o comm= 2>/dev/null); case "$c" in *python*|*/uv|uv) echo "$p $c";; esac; done | grep .; }
w=0
while orph >/dev/null; do
  [ $w -eq 0 ] && { echo "ORPHAN wording run found (left running, waiting):"; orph | cut -c1-200; }
  w=$((w+1)); [ $w -gt 20 ] && { echo "STOP: wording run still going after 10 min; no new run started $(date -u +%FT%TZ)"; echo "CHUNK-SUMMARY K=$K stop=orphan"; exit 3; }
  sleep 30
done
git fetch -q origin main && git fetch -q origin +refs/heads/builder-outbox:refs/remotes/origin/builder-outbox || { echo "STOP: git fetch failed"; echo "CHUNK-SUMMARY K=$K stop=fetch"; exit 4; }
COMMIT=$(git rev-parse origin/main)
D=$(mktemp -d); O=$F; C=$F/chunk$K; R="$D/RESULTS.md"
trap 'mkdir -p "$DEST"; cp -f "$D/$C"/* "$DEST"/ 2>/dev/null; cp -f "$R" "$DEST/RESULTS.md" 2>/dev/null; rm -rf "$D"; [ -e "$D" ] && echo "tree NOT removed: $D" || echo "tree removed: $D"; ls -l "$DEST" | awk "{print \$5, \$NF}"' EXIT
git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-chatdev-20260926 artifacts/claude-e2e331-dev-20260924 | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
cd "$D"; mkdir -p "$C"
say() { echo "$@" | tee -a "$R"; }
run() { echo '```' >> "$R"; "$@" 2>&1 | tee -a "$R"; local rc=$?; echo '```' >> "$R"; return $rc; }
stop() { say "STOP: $1"; say "CHUNK-SUMMARY K=$K stop=$2"; exit 5; }
say "# lis-320 Luna full run, chunk $K - BASH-ONLY job claude-lis320-luna-c11-mac"
say ""; say "origin/main: $COMMIT"; say "builder-outbox: $(git -C "$W" rev-parse origin/builder-outbox)"; say "start: $(date -u +%FT%TZ)"; say "orphan wait loops: $w"
say "## seals"
for s in 6 8 9 10 11 12; do run shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-$s.sha256.txt || stop "seal $s failed" seal; done
say "## selftests and probe"
for t in claude_lis320_luna3 claude_lis320_seed_cr claude_lis320_check_we3 claude_lis320_rawcheck2 claude_lis320_resume_clean; do run PY scripts/$t.py --selftest || stop "selftest $t failed" selftest; done
run PY scripts/claude_luna_codex.py --selftest || stop "live helper probe failed" probe
say "## seeds"
run PY scripts/claude_lis320_seed_cr.py --seed 324 --n $N --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl >/dev/null || stop "seeds failed" seeds
shasum -a 256 $O/seeds.jsonl | awk '{print $1}' > $C/SEEDS.sha256.txt; say "seeds sha256: $(cat $C/SEEDS.sha256.txt)"
if [ $K -gt 1 ]; then S1=$(git -C "$W" show origin/builder-outbox:$F/chunk1/SEEDS.sha256.txt) || stop "chunk1 SEEDS.sha256.txt missing" seeds; [ "$S1" = "$(cat $C/SEEDS.sha256.txt)" ] || stop "seeds hash differs from chunk 1" seeds; say "seeds hash equals chunk 1"; fi
say "## resume"
: > $O/joined.jsonl
j=1; while [ $j -lt $K ]; do git -C "$W" show origin/builder-outbox:$F/chunk$j/raw.new.jsonl.gz | gunzip >> $O/joined.jsonl || stop "chunk $j raw.new.jsonl.gz missing" resume; j=$((j+1)); done
say "joined rows from chunks 1..$((K-1)): $(wc -l < $O/joined.jsonl | tr -d ' ')"
run PY scripts/claude_lis320_resume_clean.py --raw $O/joined.jsonl --out $O/raw.jsonl || stop "resume_clean failed" resume
B=$(wc -l < $O/raw.jsonl | tr -d ' '); say "rows after clean (B): $B"
say "## wording"
T0=$(date -u +%s); say "wording start: $(date -u +%FT%TZ) | $(uptime | sed 's/.*load/load/')"
PY scripts/claude_lis320_luna3.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers $LW --batch 12 --max-minutes 55 > $C/glm.log 2>&1; rcw=$?
T1=$(date -u +%s); say "wording end: $(date -u +%FT%TZ) rc=$rcw | $(uptime | sed 's/.*load/load/')"
tail -n +$((B + 1)) $O/raw.jsonl > $C/raw.new.jsonl; NEW=$(wc -l < $C/raw.new.jsonl | tr -d ' ')
say "new rows: $NEW; minutes: $(( (T1-T0)/60 )); dialogs per minute: $(awk -v r=$NEW -v s=$((T1-T0)) 'BEGIN{printf "%.2f", (s>0? r*60/s : 0)}')"
gzip -9 -f $C/raw.new.jsonl
say "last line of glm.log:"; run tail -1 $C/glm.log
TRY=$(grep -c "^\[luna-try\] failed" $C/glm.log); RL=$(grep -ciE "rate.?limit|usage limit|quota|too many requests" $C/glm.log)
say "call failed lines: $(grep -c 'call failed' $C/glm.log); failed helper tries: $TRY; rate-limit/usage lines: $RL; parallel calls: $LW"
say "distinct failure starts:"; run sh -c "grep -iE 'call failed|try [0-9]+ failed|Traceback|Error' $C/glm.log | sed -E 's/s320cr-[0-9-]*//g' | cut -c1-120 | sort | uniq -c | sort -rn | head -8"
PR=$(tail -1 $C/glm.log | "$UV" run --offline --no-project --python 3.12 python -c "import json,sys
try:
    t=json.loads(sys.stdin.read()); print('%d %d %.3f %s' % (t['calls'], t['parsed'], (t['parsed']/t['calls'] if t['calls'] else 1.0), t['stopped']))
except Exception:
    print('0 0 0.000 unreadable')")
set -- $PR; CALLS=$1; PARSED=$2; RATE=$3; STOPPED=$4
say "## rawcheck2 (all rows so far)"
PY scripts/claude_lis320_rawcheck2.py --raw $O/raw.jsonl --seeds $O/seeds.jsonl --models gpt-6-luna > $C/rawcheck.json 2>&1; RC2=$?; run cat $C/rawcheck.json
say "## check_we3 and style (all rows so far)"
PY scripts/claude_lis320_check_we3.py --seeds $O/seeds.jsonl --raw $O/raw.jsonl --out $O/kept.jsonl --drops $O/drops.jsonl > $C/check.json 2> $C/check.err; say "check rc=$?"
run cat $C/check.json
PY scripts/claude_lis320_style.py --kept $O/kept.jsonl --out $C/style.json > /dev/null 2>&1; run cat $C/style.json
OKN=$("$UV" run --offline --no-project --python 3.12 python -c "import json,sys
print(sum(1 for l in open(sys.argv[1]) if l.strip() and json.loads(l).get('parsed') is not None))" $O/raw.jsonl)
ST=ok
awk -v r=$RATE 'BEGIN{exit !(r < 0.85)}' && ST=parsed_below_85
[ $RC2 -ne 0 ] && ST=rawcheck2
say "end: $(date -u +%FT%TZ)"
say "CHUNK-SUMMARY K=$K B=$B new=$NEW calls=$CALLS parsed=$PARSED rate=$RATE stopped=$STOPPED rawcheck2_rc=$RC2 lw=$LW tries_failed=$TRY ratelimit=$RL worded_ok=$OKN of=$N stop=$ST"
```
PUSH: artifacts/claude-lis320-20260926/full-luna/chunk11
