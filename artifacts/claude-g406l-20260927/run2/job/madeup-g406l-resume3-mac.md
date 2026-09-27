BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no (Mac CPU; GPT-6 Luna through Ben's Codex plan via scripts/claude_luna_codex.py: the 20 packets madeup-g406l-mac did not reach, at most 3 attempts each (up to 60 calls), ONE at a time; no opencode, no GLM, no rental, no BensPC, no OpenRouter). Label: madeup-g406l-resume3. DISK: 1.
"Making things up about you" thread, Claude, 2026-09-27. No LLM builder: rungo5 runs the bash block below (Director 2bf4f9ea7; the Thread manager suggested this route at 08:38 UTC).
WHY: g406b-L's resume (artifacts/claude-g406l-20260927/ADDENDUM-1-resume.md). The first launch (madeup-g406l-resume-mac) died on builder rate limits before any step, rc=1. madeup-g406l-resume2-mac was withdrawn to handoff/held/ before it launched, so it is not a launch. This is launch 2 under ADDENDUM-2's limit. Same steps and the same sealed command as resume2, with no builder.
CODEX RULES: nothing here reads, lists, prints, copies or commits anything under ~/.codex. The helper runs each call in an empty temp folder with a read-only sandbox.
OUTPUT: counts only. No transcript text and no Luna reply text are printed; the runner's log holds counts only.
PUSH: artifacts/claude-g406l-20260927/run2

```bash
set -u
W=$(pwd); Q=$HOME/premonition-watch/queue; R=/tmp/madeup-g406l-resume3.RESULTS.md
exec > >(tee -a "$R") 2>&1
echo "# g406b-L resume3 (BASH-ONLY) RESULTS"; echo "- start: $(date -u)"; echo "- uptime: $(uptime)"
for s in running exit pushed; do
  if [ -e "$Q/madeup-g406l-resume2-mac.$s" ]; then echo "STOP: madeup-g406l-resume2-mac.$s exists, so resume2 launched; resume3 does nothing"; exit 3; fi
done
if pgrep -fl claude_g406l_luna.py; then echo "STOP: a g406l run is already going; resume3 does nothing"; exit 3; fi
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then PY="uv run --offline --no-project --python 3.12 python -B"; else echo "STOP: uv not found on PATH"; exit 4; fi
echo "- python: $($PY -c 'import sys; print(sys.version.split()[0])')"
D=/tmp/madeup-g406l-resume3; O=$D/artifacts/claude-g406l-20260927/run2; mkdir -p "$D"
git -C "$W" fetch -q origin main || { echo "STOP: git fetch failed"; exit 4; }
echo "- origin/main: $(git -C "$W" rev-parse origin/main)"
if [ ! -e "$O/luna_b.jsonl" ]; then
  git -C "$W" archive origin/main scripts artifacts/claude-g406l-20260927 artifacts/claude-mu405-20260926/JUDGE-claims405.md artifacts/claude-mu405b-20260926/judge artifacts/claude-mu402-20260926/JUDGE-claims.md | tar -x -C "$D" || { echo "STOP: archive failed"; exit 4; }
  mkdir -p "$O"; cp "$D/artifacts/claude-g406l-20260927/run/luna_b.jsonl" "$O/luna_b.jsonl"; echo "- copied run/luna_b.jsonl to run2/"
else
  echo "- restart: run2/luna_b.jsonl already exists and is kept"
fi
cd "$D" || exit 4
echo "- luna_b.jsonl lines now: $(wc -l < "$O/luna_b.jsonl")"
H=$(head -n 220 "$O/luna_b.jsonl" | shasum -a 256 | cut -d' ' -f1); echo "- sha256 of its first 220 lines: $H"
[ "$H" = 19889ed299570f1adc3fecb5576246156dc98bdd4759f706e87f46f8e414f910 ] || { echo "STOP: start hash mismatch"; exit 5; }
echo "## SEAL"; shasum -a 256 -c artifacts/claude-g406l-20260927/SEAL.sha256.txt || { echo "STOP: seal check failed"; exit 5; }
echo "## SELFTESTS"
chk() { want="$1"; shift; o=$($PY "$@" 2>&1); rc=$?; echo "$o" | tail -n 2; echo "  rc=$rc"; [ "$rc" = 0 ] && echo "$o" | grep -q "$want"; }
chk "g406l luna selftest 7/7 ok" scripts/claude_g406l_luna.py selftest-luna || { echo "STOP: selftest-luna"; exit 6; }
chk "g406-2 selftest 7/7 ok" scripts/claude_g406l_luna.py --selftest || { echo "STOP: g406-2 selftest"; exit 6; }
chk "g406 count selftest 5/5 ok" scripts/claude_g406_count.py --selftest || { echo "STOP: count selftest"; exit 6; }
chk "selftest ok: model gpt-6-luna" scripts/claude_luna_codex.py --selftest || { echo "STOP: luna helper selftest"; exit 6; }
echo "  all 4 selftests ok"
echo "## RESUME"
$PY scripts/claude_g406l_luna.py --mode two --packets 'artifacts/claude-mu405b-20260926/judge/packets/claims_j*.jsonl' --out "$O/luna_b.jsonl" --workers 1 --attempts 3 --max-failed 60 --max-minutes 30 >> "$O/luna_b.log" 2>&1 &
RP=$!; echo "$RP" > "$O/run.pid"; echo "- resume started $(date -u), pid $RP"
S=$(date +%s); while kill -0 "$RP" 2>/dev/null && [ $(( $(date +%s) - S )) -lt 3600 ]; do sleep 30; done
if kill -0 "$RP" 2>/dev/null; then C=$(pgrep -P "$RP"); echo "- TIME STOP at 60 min: child ${C:-none}, parent $RP, $(date -u)"; [ -n "$C" ] && kill $C; kill "$RP"; fi
wait "$RP" 2>/dev/null; RRC=$?; echo "- resume ended $(date -u), rc=$RRC"
echo "- log last line: $(tail -n 1 "$O/luna_b.log")"
echo "- luna_b.jsonl lines: $(wc -l < "$O/luna_b.jsonl")"
echo "- error prefixes (first 60 chars, counts):"
$PY -c 'import json,sys,collections; c=collections.Counter((json.loads(l).get("error") or "")[:60] for l in open(sys.argv[1])); [print("  ", n, repr(k)) for k,n in c.most_common()]' "$O/luna_b.jsonl"
echo "## COUNT"
$PY scripts/claude_g406l_luna.py --glm "$O/luna_b.jsonl" --best-to "$O/best_b.jsonl"; echo "  rc=$?"
$PY scripts/claude_g406_count.py --glm "$O/best_b.jsonl" --judges artifacts/claude-mu405b-20260926/judge --write "$O/verdict_b.json"; echo "  rc=$?"
$PY scripts/claude_g406l_luna.py --arm-report --glm "$O/luna_b.jsonl" --judge artifacts/claude-mu405b-20260926/judge > "$O/arms_b.json"; echo "  rc=$?"
echo "labeller: Luna (gpt-6-luna), helper sha256 $(shasum -a 256 scripts/claude_luna_codex.py | cut -d' ' -f1)"
T="$W/artifacts/claude-g406l-20260927/run2"; mkdir -p "$T"
for f in luna_b.jsonl luna_b.log best_b.jsonl verdict_b.json arms_b.json; do cp "$O/$f" "$T/$f" && echo "- copied $f ($(wc -l < "$T/$f") lines)"; done
echo "- end: $(date -u)"
sleep 2; cp "$R" "$T/RESULTS.md"
cd "$W"; rm -rf "/tmp/madeup-g406l-resume3"; [ -e /tmp/madeup-g406l-resume3 ] && echo "temp dir NOT removed" || echo "temp dir removed"
rm -f "$R"
```
