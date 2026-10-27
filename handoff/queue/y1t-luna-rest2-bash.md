BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes. DISK: 1
The "Answering from memory" thread, Claude, wrote this job on 2026-09-27 09:14 UTC. Runs with no LLM builder (the Director's BASH-ONLY route, 2bf4f9ea7), because the free builders are rate-limited or hanging.
WHY: ADDENDUM-5 (sealed in SEAL-y1t-add5.sha256.txt); its 60-dialog pilot passed (luna/PILOT-RESULT.md, 5bb3e414e). This is pass 1 of the other 255 Luna dialogs, with the same runner and 3 workers (the Director's share). It resumes from the pilot's 60 rows and stops starting batches after 50 minutes. A job for whatever is left is queued only after this one lands.
Re-run of y1t-luna-rest1-bash, which made no Luna call: it stopped at its running-job check (rc=3) because the pattern also matched the hung opencode builder of y1t-luna-rest-mac, whose prompt text names the script. Now only processes whose program is python or uv count (tested on a decoy). Outputs go to rest2/ so nothing can overwrite rest1's files. If a real wording run is going, it still stops (exit 3) and kills nothing. The old job's stop file is touched again (no kill).
Nothing is trained, checked or judged here. The script prints counts only; Luna's text is never printed.
PUSH: artifacts/claude-y1t-20260926/luna/rest2

```bash
set -o pipefail
Q=~/premonition-watch/queue
touch "$Q/y1t-luna-rest-mac.stop"
W=$(pwd); R=artifacts/claude-y1t-20260926/luna/rest2
echo "start $(date -u '+%F %T') UTC in $W"
orph() {
  for p in $(pgrep -f 'claude_y1t_luna\.py --seeds'); do
    c=$(ps -o comm= -p "$p" 2>/dev/null); c=${c##*/}
    case "$c" in python*|Python*|uv) echo "$p $c";; esac
  done
}
echo "processes naming the script (first 40 chars, any program):"; pgrep -fl 'claude_y1t_luna\.py' | cut -c1-40
X=$(orph); if [ -n "$X" ]; then echo "ABORT: a python claude_y1t_luna.py run is already going: $X"; exit 3; fi
echo "no python wording run is going"
git -C "$W" fetch -q origin main builder-outbox || { echo "ABORT: fetch failed"; exit 4; }
D=$(mktemp -d /tmp/y1t-rest2.XXXXXX) || exit 4
git -C "$W" archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-y1t-20260926/ADDENDUM-5-luna-writer.md artifacts/claude-y1t-20260926/SEAL-y1t-add5.sha256.txt | tar -x -C "$D" || exit 4
git -C "$W" archive origin/builder-outbox artifacts/claude-y1t-20260926/glm/raw.jsonl artifacts/claude-y1t-20260926/topup/raw_new.jsonl artifacts/claude-y1t-20260926/luna/raw_luna_rf.jsonl | tar -x -C "$D" || exit 4
cd "$D" || exit 4
O=artifacts/claude-y1t-20260926/luna; mkdir -p "$O/rest2"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYBIN=$("$U" python find 3.12 2>/dev/null); [ -x "$PYBIN" ] || PYBIN=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
[ -x "$PYBIN" ] || { echo "ABORT: no python 3.12 from uv"; exit 6; }
echo "python: $("$PYBIN" --version 2>&1)"
shasum -a 256 -c artifacts/claude-y1t-20260926/SEAL-y1t-add5.sha256.txt || { echo "SEAL-MISMATCH"; exit 5; }
"$PYBIN" -B scripts/claude_lis320_seed.py --seed 4027 --n 2400 --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl || exit 7
"$PYBIN" -B scripts/claude_y1t_topup.py split --seeds $O/seeds.jsonl --raw artifacts/claude-y1t-20260926/glm/raw.jsonl --out $O/split || exit 7
"$PYBIN" -B scripts/claude_y1t_luna.py pick --redo $O/split/seeds_redo.jsonl --done artifacts/claude-y1t-20260926/topup/raw_new.jsonl --out $O/luna_seeds.jsonl || exit 7
cat > $O/want.sha256 <<'EOF'
42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43  artifacts/claude-y1t-20260926/luna/seeds.jsonl
e80e84156cb2ac003711c97ad8d9d4761962c6c42b83d3730477dad8abc4ef8b  artifacts/claude-y1t-20260926/luna/split/seeds_redo.jsonl
6184cd224078ad2eb71cdd606129cb29fc14e513960c26c0ee0b295f57b483de  artifacts/claude-y1t-20260926/luna/luna_seeds.jsonl
5e98dec2f5f48042123e9c0b52a114923d8842a5b0148441f02c179d162e6e78  artifacts/claude-y1t-20260926/luna/raw_luna_rf.jsonl
EOF
shasum -a 256 -c $O/want.sha256 || { echo "SEED-MISMATCH"; exit 5; }
"$PYBIN" -B scripts/claude_y1t_luna.py --selftest | tail -1 || exit 8
"$PYBIN" -B scripts/claude_y1t_routefilter.py --selftest | tail -1 || exit 8
uptime; df -g / | tail -1
cp $O/raw_luna_rf.jsonl $O/rest2/raw_luna.jsonl
echo "pass start $(date -u '+%F %T') UTC"
perl -e 'alarm shift; exec @ARGV' 3900 "$PYBIN" -B scripts/claude_y1t_luna.py --seeds $O/luna_seeds.jsonl --out $O/rest2/raw_luna.jsonl --workers 3 --batch 20 --max-minutes 50 --max-failed 20 > $O/rest2/luna_rest2.log 2>&1
echo "pass rc=$? end $(date -u '+%F %T') UTC"
echo "totals: $(tail -1 $O/rest2/luna_rest2.log)"
grep '\[y1tluna\] call failed' $O/rest2/luna_rest2.log | cut -c1-160 | sort | uniq -c | head -5
"$PYBIN" -B scripts/claude_y1t_routefilter.py filter --raw $O/rest2/raw_luna.jsonl --out $O/rest2/raw_luna_rf.jsonl
"$PYBIN" - "$O" <<'EOF'
import json, sys
O = sys.argv[1]
rows = [json.loads(x) for x in open(f"{O}/rest2/raw_luna.jsonl", encoding="utf-8") if x.strip()]
want = [json.loads(x)["dialog_id"] for x in open(f"{O}/luna_seeds.jsonl", encoding="utf-8") if x.strip()]
ids = [r["dialog_id"] for r in rows]
pilot = open(f"{O}/raw_luna_rf.jsonl", encoding="utf-8").read()
print(json.dumps({"rows": len(rows), "distinct_ids": len(set(ids)), "parsed_not_null": sum(r.get("parsed") is not None for r in rows),
                  "ids_in_315": len(set(ids) & set(want)), "ids_not_in_315": len(set(ids) - set(want)), "left_of_315": len(set(want) - set(ids)),
                  "models": sorted({str(r.get("model")) for r in rows}),
                  "first_60_lines_same_as_pilot": open(f"{O}/rest2/raw_luna.jsonl", encoding="utf-8").read().startswith(pilot)}))
EOF
mkdir -p "$W/$R"
cp $O/rest2/raw_luna.jsonl $O/rest2/raw_luna_rf.jsonl $O/rest2/luna_rest2.log "$W/$R/"
shasum -a 256 "$W/$R"/* | sed "s|$W/||"
cd "$W" && rm -rf "$D" && [ ! -e "$D" ] && echo "removed $D"
echo "end $(date -u '+%F %T') UTC"
```
