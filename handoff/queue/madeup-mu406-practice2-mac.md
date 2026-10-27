BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no (Mac CPU; GPT-6 Luna through Ben's Codex plan via scripts/claude_luna_codex.py: 260 chats, at most 3 attempts each (up to 780 calls), at most 2 at a time (the Director's 03:54 UTC share); no opencode, no GLM, no rental, no BensPC, no OpenRouter). Label: madeup-mu406-practice2 (launch 2). DISK: 1.
"Making things up about you" thread, Claude, 2026-09-27. No LLM builder: rungo5 runs the bash block below (Director 2bf4f9ea7).
WHY: mu-406 step 3 (artifacts/claude-mu406-20260926/PASSMARKS.md, "Order"): Luna words 260 practice chats around facts code picks (seed 4061); code keeps the first 220 that pass and holds out 20 of them (seed 4062) for the teacher gate. At about 16 s per chat (the panel job) this needs 2 launches: the writer stops itself at 50 minutes, and a relaunch under a new file name seeds raw.jsonl from builder-outbox and writes only the chats not yet written. It runs only after the test panel is sealed (SEAL-panel.sha256.txt on main).
CODEX RULES: nothing here reads, lists, prints, copies or commits anything under ~/.codex. The helper runs each call in an empty temp folder with a read-only sandbox.
OUTPUT: counts only. No chat text is printed; the runner's log holds counts only.
PUSH: artifacts/claude-mu406-20260926/practice

```bash
set -u
W=$(pwd); R=/tmp/madeup-mu406-practice2.RESULTS.md
exec > >(tee -a "$R") 2>&1
echo "# mu-406 practice chats (BASH-ONLY) RESULTS"; echo "- start: $(date -u)"; echo "- uptime: $(uptime)"
if pgrep -fl claude_mu406_prep.py; then echo "STOP: a mu-406 prep run is already going; this job does nothing"; exit 3; fi
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then PY="uv run --offline --no-project --python 3.12 python -B"; else echo "STOP: uv not found on PATH"; exit 4; fi
echo "- python: $($PY -c 'import sys; print(sys.version.split()[0])')"
D=/tmp/madeup-mu406-practice2; O=$D/artifacts/claude-mu406-20260926/practice; mkdir -p "$D"
git -C "$W" fetch -q origin main || { echo "STOP: git fetch failed"; exit 4; }
echo "- origin/main: $(git -C "$W" rev-parse origin/main)"
git -C "$W" cat-file -e origin/main:artifacts/claude-mu406-20260926/SEAL-panel.sha256.txt 2>/dev/null || { echo "STOP: the test panel is not sealed on main yet"; exit 7; }
if [ ! -e "$O/raw.jsonl" ]; then
  git -C "$W" archive origin/main scripts artifacts/claude-mu406-20260926 artifacts/claude-mu405-20260926/JUDGE-claims405.md artifacts/claude-mu407-20260927/JUDGE-fit407.md artifacts/claude-mu407-20260927/prep/frames.json | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
else
  echo "- restart: practice/raw.jsonl already exists and is kept"
fi
cd "$D" || exit 4
echo "## SEAL"; shasum -a 256 -c artifacts/claude-mu406-20260926/SEAL.sha256.txt || { echo "STOP: seal check failed"; exit 5; }
echo "## SELFTESTS"
chk() { want="$1"; shift; o=$($PY "$@" 2>&1); rc=$?; echo "$o" | tail -n 2; echo "  rc=$rc"; [ "$rc" = 0 ] && echo "$o" | grep -q "$want"; }
chk "mu406 prep selftest 10/10 ok" scripts/claude_mu406_prep.py selftest || { echo "STOP: mu406 prep selftest"; exit 6; }
chk "mu407 prep-luna selftest 11/11 ok" scripts/claude_mu407_prep_luna.py selftest-luna || { echo "STOP: prep-luna selftest"; exit 6; }
chk "selftest ok: model gpt-6-luna" scripts/claude_luna_codex.py --selftest || { echo "STOP: luna helper selftest"; exit 6; }
echo "  all 3 selftests ok"
mkdir -p "$O"
git -C "$W" fetch -q origin +builder-outbox:refs/remotes/origin/builder-outbox || echo "- note: builder-outbox fetch failed"
if [ ! -e "$O/raw.jsonl" ] && git -C "$W" cat-file -e origin/builder-outbox:artifacts/claude-mu406-20260926/practice/raw.jsonl 2>/dev/null; then
  git -C "$W" show origin/builder-outbox:artifacts/claude-mu406-20260926/practice/raw.jsonl > "$O/raw.jsonl"; echo "- restart: seeded raw.jsonl from builder-outbox ($(wc -l < "$O/raw.jsonl") lines)"
fi
echo "## FACTS"; $PY scripts/claude_mu406_prep.py facts --set practice --out "$O/facts_all.jsonl"; echo "  rc=$?"
head -n 240 "$O/facts_all.jsonl" > "$O/facts_write.jsonl"; echo "- writing the first $(wc -l < "$O/facts_write.jsonl") candidates in id order (select keeps the first 220 that pass, so later candidates could never be chosen)"
echo "## WRITE"
$PY scripts/claude_mu406_prep.py write --facts "$O/facts_write.jsonl" --out "$O/raw.jsonl" --workers 2 --max-minutes 50 >> "$O/write-2.log" 2>&1 &
RP=$!; echo "- write started $(date -u), pid $RP"
S=$(date +%s); while kill -0 "$RP" 2>/dev/null && [ $(( $(date +%s) - S )) -lt 3600 ]; do sleep 30; done
if kill -0 "$RP" 2>/dev/null; then C=$(pgrep -P "$RP"); echo "- TIME STOP at 60 min: child ${C:-none}, parent $RP, $(date -u)"; [ -n "$C" ] && kill $C; kill "$RP"; fi
wait "$RP" 2>/dev/null; WRC=$?; echo "- write ended $(date -u), rc=$WRC"
echo "- write-2.log last line: $(tail -n 1 "$O/write-2.log")"
echo "## SELECT"; $PY scripts/claude_mu406_prep.py select --set practice --facts "$O/facts_all.jsonl" --raw "$O/raw.jsonl" --out-items "$O/items.jsonl" --out-facts "$O/facts.jsonl" --out-heldout "$O/heldout.jsonl" --out-heldout-facts "$O/heldout_facts.jsonl"; echo "  rc=$?"
echo "## SCAN"; $PY scripts/claude_mu406_prep.py scan --raw "$O/raw.jsonl"; echo "  rc=$?"
echo "writer: Luna (gpt-6-luna), helper sha256 $(shasum -a 256 scripts/claude_luna_codex.py | cut -d' ' -f1)"
T="$W/artifacts/claude-mu406-20260926/practice"; mkdir -p "$T"
for f in facts_all.jsonl raw.jsonl write-2.log items.jsonl facts.jsonl heldout.jsonl heldout_facts.jsonl; do [ -e "$O/$f" ] && cp "$O/$f" "$T/$f" && echo "- copied $f ($(wc -l < "$T/$f") lines)"; done
echo "- end: $(date -u)"
sleep 2; cp "$R" "$T/RESULTS-2.md"
cd "$W"; rm -rf "/tmp/madeup-mu406-practice2"; [ -e /tmp/madeup-mu406-practice2 ] && echo "temp dir NOT removed" || echo "temp dir removed"
rm -f "$R"
```
