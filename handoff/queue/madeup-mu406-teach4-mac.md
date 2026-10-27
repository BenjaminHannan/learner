BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no (Mac CPU; GPT-6 Luna through Ben's Codex plan via scripts/claude_luna_codex.py: teaching replies for 220 practice chats, 5 turns each, at most 3 attempts per turn (1,100 calls, at most 3,300), at most 2 at a time (the Director's 03:54 UTC share); no opencode, no GLM, no rental, no BensPC, no OpenRouter). Label: madeup-mu406-teach4. DISK: 1.
"Making things up about you" thread, Claude, 2026-09-27. No LLM builder: rungo5 runs the bash block below (Director 2bf4f9ea7).
WHY: mu-406 step 4 (artifacts/claude-mu406-20260926/PASSMARKS.md, "Order"): Luna writes the assistant's reply to each session-2 turn of the 20 held-out chats first, then the 200 training chats (scripts/claude_mu406_teach.py). The writer stops itself at 50 minutes; a relaunch under a new file name seeds teach.jsonl from builder-outbox and writes only the chats not yet written.
CODEX RULES: nothing here reads, lists, prints, copies or commits anything under ~/.codex. The helper runs each call in an empty temp folder with a read-only sandbox.
LAUNCH 4 of step 4. Launch 3 (madeup-mu406-teach3-mac, rc=0) brought the total to 160 of 220 chats in 52.1 minutes and stopped itself on time. This copy seeds teach.jsonl from builder-outbox and writes the last 60; only the launch number, temp folder and results file names change.
OUTPUT: counts only. No chat or reply text is printed; the runner's log holds counts only.
PUSH: artifacts/claude-mu406-20260926/teach

```bash
set -u
L=4   # launch number: RESULTS-$L.md and teach-$L.log keep each launch's record
W=$(pwd); R=/tmp/madeup-mu406-teach4.RESULTS.md
exec > >(tee -a "$R") 2>&1
echo "# mu-406 teaching replies (BASH-ONLY) RESULTS"; echo "- start: $(date -u)"; echo "- uptime: $(uptime)"
if pgrep -fl claude_mu406_teach.py; then echo "STOP: a mu-406 teach run is already going; this job does nothing"; exit 3; fi
rm -rf /tmp/madeup-mu406-teach3 /tmp/madeup-mu406-teach3.RESULTS.md; echo "- launch 3 leftovers removed: $([ -e /tmp/madeup-mu406-teach3 ] && echo no || echo yes)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then PY="uv run --offline --no-project --python 3.12 python -B"; else echo "STOP: uv not found on PATH"; exit 4; fi
echo "- python: $($PY -c 'import sys; print(sys.version.split()[0])')"
D=/tmp/madeup-mu406-teach4; A=$D/artifacts/claude-mu406-20260926; O=$A/teach; mkdir -p "$D"
git -C "$W" fetch -q origin main || { echo "STOP: git fetch failed"; exit 4; }
echo "- origin/main: $(git -C "$W" rev-parse origin/main)"
git -C "$W" cat-file -e origin/main:artifacts/claude-mu406-20260926/practice/heldout.jsonl 2>/dev/null || { echo "STOP: the practice chats are not on main yet"; exit 7; }
git -C "$W" archive origin/main scripts artifacts/claude-mu406-20260926 artifacts/claude-mu405-20260926/JUDGE-claims405.md artifacts/claude-mu407-20260927/JUDGE-fit407.md artifacts/claude-mu407-20260927/prep/frames.json | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
cd "$D" || exit 4
echo "## SEAL"; shasum -a 256 -c artifacts/claude-mu406-20260926/SEAL.sha256.txt || { echo "STOP: seal check failed"; exit 5; }
( cd artifacts/claude-mu406-20260926 && shasum -a 256 -c SEAL-panel.sha256.txt ) || { echo "STOP: panel seal check failed"; exit 5; }
echo "## SELFTESTS"
chk() { want="$1"; shift; o=$($PY "$@" 2>&1); rc=$?; echo "$o" | tail -n 2; echo "  rc=$rc"; [ "$rc" = 0 ] && echo "$o" | grep -q "$want"; }
chk "mu406 teach selftest 9/9 ok" scripts/claude_mu406_teach.py selftest || { echo "STOP: mu406 teach selftest"; exit 6; }
chk "selftest ok: model gpt-6-luna" scripts/claude_luna_codex.py --selftest || { echo "STOP: luna helper selftest"; exit 6; }
echo "  both selftests ok"
mkdir -p "$O"
cat "$A/practice/heldout.jsonl" "$A/practice/items.jsonl" > "$O/items_all.jsonl"
cat "$A/practice/heldout_facts.jsonl" "$A/practice/facts.jsonl" > "$O/facts_all.jsonl"
echo "- chats to teach: $(wc -l < "$O/items_all.jsonl") (held-out first), facts rows $(wc -l < "$O/facts_all.jsonl")"
git -C "$W" fetch -q origin +builder-outbox:refs/remotes/origin/builder-outbox || echo "- note: builder-outbox fetch failed"
if git -C "$W" cat-file -e origin/builder-outbox:artifacts/claude-mu406-20260926/teach/teach.jsonl 2>/dev/null; then
  git -C "$W" show origin/builder-outbox:artifacts/claude-mu406-20260926/teach/teach.jsonl > "$O/teach.jsonl"; echo "- restart: seeded teach.jsonl from builder-outbox ($(wc -l < "$O/teach.jsonl") chats)"
fi
echo "## WRITE"
$PY scripts/claude_mu406_teach.py write --items "$O/items_all.jsonl" --facts "$O/facts_all.jsonl" --out "$O/teach.jsonl" --workers 2 --max-minutes 50 >> "$O/teach-$L.log" 2>&1 &
RP=$!; echo "- write started $(date -u), pid $RP"
S=$(date +%s); while kill -0 "$RP" 2>/dev/null && [ $(( $(date +%s) - S )) -lt 3600 ]; do sleep 30; done
if kill -0 "$RP" 2>/dev/null; then C=$(pgrep -P "$RP"); echo "- TIME STOP at 60 min: child ${C:-none}, parent $RP, $(date -u)"; [ -n "$C" ] && kill $C; kill "$RP"; fi
wait "$RP" 2>/dev/null; WRC=$?; echo "- write ended $(date -u), rc=$WRC"
echo "- teach-$L.log last line: $(tail -n 1 "$O/teach-$L.log")"
echo "## STATS"; $PY scripts/claude_mu406_teach.py stats --out "$O/teach.jsonl"; echo "  rc=$?"
echo "writer: Luna (gpt-6-luna), helper sha256 $(shasum -a 256 scripts/claude_luna_codex.py | cut -d' ' -f1)"
T="$W/artifacts/claude-mu406-20260926/teach"; mkdir -p "$T"
for f in teach.jsonl teach-$L.log; do [ -e "$O/$f" ] && cp "$O/$f" "$T/$f" && echo "- copied $f ($(wc -l < "$T/$f") lines)"; done
echo "- end: $(date -u)"
sleep 2; cp "$R" "$T/RESULTS-$L.md"
cd "$W"; rm -rf "/tmp/madeup-mu406-teach4"; [ -e /tmp/madeup-mu406-teach4 ] && echo "temp dir NOT removed" || echo "temp dir removed"
rm -f "$R"
```
