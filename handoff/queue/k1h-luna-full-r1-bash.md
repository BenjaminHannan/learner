BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no. DISK: 1
The "Creative answers in chat" thread, Claude, wrote this job on 2026-09-27 10:53 UTC. Runs with no LLM builder (the Director's BASH-ONLY route, 2bf4f9ea7).
WHY: k1h-luna-full-mac (launched 06:41 UTC) ran its 7 Luna chat calls and answer chunk 1 (07:05 to 08:05 UTC: 286 answered, 0 failed, 645 not started of 971), then its builder went silent: its err file has not changed since 04:05 local, and its opencode PID 64555 was still alive at 10:45 UTC. This job continues the same sealed run (ADDENDUM-5-luna.md, 94accde3b) with one more 60-minute answer chunk (r1), from the old job's own files in its temp folder. It is not a relaunch: the old job's folder is only read, and nothing is sent twice (the sealed runner skips items that already have an answer).
Guards: it stops (exit 3) and starts nothing if the old job already pushed luna/full, if luna/full-r1 exists, or if any python or uv process has claude_k1h_luna.py in its arguments. It kills nothing. It touches the old job's .stop file only after those checks pass, so the old runner starts no second builder for it; no process is stopped. Luna: 1 call at once (k1h's share).
Prints counts only; no chat or answer text is printed.
PUSH: artifacts/claude-k1h-20260926/luna/full-r1

```bash
set -o pipefail
Q=~/premonition-watch/queue
W=$(pwd)
OLD=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.08G1HFx4hV
A=artifacts/claude-k1h-20260926
R=$A/luna/full-r1
echo "k1h-luna-full-r1 start $(date -u '+%F %T') UTC in $W"
k1hpy() {
  for p in $(pgrep -f 'claude_k1h_luna\.py'); do
    c=$(ps -o comm= -p "$p" 2>/dev/null); c=${c##*/}
    case "$c" in python*|Python*|uv) echo "$p $c $(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')";; esac
  done
}
okstats() { grep 'kind=ok' "$1" | grep -o 'secs=[0-9.]*' | cut -d= -f2 | sort -n | awk '{a[NR]=$1} END{if(NR){m=(NR%2)?a[(NR+1)/2]:(a[NR/2]+a[NR/2+1])/2; print "kind=ok tries " NR ", median secs " m ", largest secs " a[NR]} else print "kind=ok tries 0"}'; }
x=$(ps -o pid=,ppid=,etime=,stat=,comm= -p 64555 2>/dev/null | tr -s ' '); echo "old builder 64555: ${x:-gone}"
x=$(ps -o pid=,etime=,comm= -p 64533 2>/dev/null | tr -s ' '); echo "old runner 64533: ${x:-gone}"
echo "== 1. the old job's folder (size, local time, name)"
[ -d "$OLD/O/answers" ] || { echo "OLD-GONE: $OLD/O/answers is missing; nothing started"; exit 3; }
ls -lT "$OLD/O" "$OLD/O/answers" "$OLD/O/chats" 2>&1 | awk 'NF>=10{print $5, $6, $7, $8, $NF}'
echo "old answers.jsonl lines: $(wc -l < "$OLD/O/answers/answers.jsonl" | tr -d ' ')"
for f in "$OLD/O/chats-log.txt" "$OLD"/O/answer-log-*.txt; do
  [ -f "$f" ] || continue
  echo "-- $(basename "$f"): $(wc -l < "$f" | tr -d ' ') lines; tries by kind: $(grep -o 'kind=[a-z]*' "$f" | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
  echo "   $(okstats "$f")"
  grep '^{' "$f" | sed 's/^/   counts: /'
  echo "   error names: $(grep -oE '^[A-Za-z_.]*(Error|Exception)' "$f" | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
  echo "   last line starts: $(tail -1 "$f" | cut -c1-15)"
done
echo "== 2. guards"
git -C "$W" fetch -q origin main builder-outbox || { echo "ABORT: fetch failed"; exit 4; }
for b in origin/main origin/builder-outbox; do
  for p in $A/luna/full $R; do
    git -C "$W" cat-file -e "$b:$p" 2>/dev/null && { echo "STOP: $p already exists on $b; nothing started"; exit 3; }
  done
done
X=$(k1hpy); if [ -n "$X" ]; then echo "STILL-RUNNING: python or uv claude_k1h_luna.py (pid comm elapsed): $(echo "$X" | tr '\n' ';')"; echo "nothing started, nothing stopped"; exit 3; fi
echo "no python or uv claude_k1h_luna.py process is going"
touch "$Q/k1h-luna-full-mac.stop" && echo "touched $Q/k1h-luna-full-mac.stop (its runner starts no second builder; no process stopped)"
echo "== 3. tree, seals, data"
D=$(mktemp -d /tmp/k1h-full-r1.XXXXXX) || exit 4
git -C "$W" archive origin/main scripts artifacts/claude-k1e-20260926/train/items.jsonl $A artifacts/claude-k1f-20260926 artifacts/claude-k1fpanel-20260926/SEAL.sha256.txt | tar -x -C "$D" || exit 4
echo "origin/main $(git -C "$W" rev-parse origin/main)"
cd "$D" || exit 4
for s in SEAL-k1h SEAL-addendum1 SEAL-addendum2 SEAL-addendum3 SEAL-addendum4 SEAL-addendum5 SEAL-addendum6; do
  r=$(shasum -a 256 -c "$A/$s.sha256.txt" 2>&1); n=$(echo "$r" | grep -c ': OK$'); b=$(echo "$r" | grep -vc ': OK$')
  echo "$s: $n OK, $b other"; [ "$b" = 0 ] || { echo "SEAL-MISMATCH"; exit 5; }
done
K=artifacts/claude-k1e-20260926/train/items.jsonl; G=$A/glm/chats.jsonl
cat > want.sha256 <<'EOF'
ae4e4d7b257ca3a54d8820061d37829e68e4ca787b6b6d3dfa1fc164eb68c92f  artifacts/claude-k1e-20260926/train/items.jsonl
49c74254ea797454d98967b4b3123f23f51498ae8e70089ff978191db76ee8a2  artifacts/claude-k1h-20260926/glm/chats.jsonl
8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603  artifacts/claude-k1h-20260926/luna/pilot/answers.jsonl
EOF
shasum -a 256 -c want.sha256 || { echo "DATA-MISMATCH"; exit 5; }
O=$D/O; mkdir -p "$O/answers" "$O/chats"
cp "$OLD/O/chats/chats.jsonl" "$O/chats/chats.jsonl" || { echo "ABORT: no old chats.jsonl"; exit 5; }
cp "$OLD/O/answers/answers.jsonl" "$O/answers/answers.jsonl" || { echo "ABORT: no old answers.jsonl"; exit 5; }
echo "copied from the old folder:"; shasum -a 256 "$O/chats/chats.jsonl" "$O/answers/answers.jsonl" | sed "s|$D/||"
[ "$(wc -l < "$O/chats/chats.jsonl" | tr -d ' ')" = 138 ] || { echo "DATA-MISMATCH: the old chats.jsonl is not 138 lines"; exit 5; }
[ "$(head -40 "$O/answers/answers.jsonl" | shasum -a 256 | cut -d' ' -f1)" = 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603 ] || { echo "DATA-MISMATCH: the first 40 answer lines are not the pilot's"; exit 5; }
echo "first 40 answer lines are the pilot's"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYBIN=$("$U" python find 3.12 2>/dev/null); [ -x "$PYBIN" ] || PYBIN=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
[ -x "$PYBIN" ] || { echo "ABORT: no python 3.12 from uv"; exit 6; }
echo "python: $("$PYBIN" --version 2>&1)"
for t in "claude_k1h_luna.py|k1h luna selftest 8/8 ok" "claude_k1h_glm.py|k1h glm selftest 3/3 ok" "claude_k1h_routefilter.py|k1h routefilter selftest 2/2 ok"; do
  s=${t%%|*}; want=${t#*|}; got=$("$PYBIN" -B scripts/$s selftest 2>&1 | tail -1)
  echo "$s selftest: $got"; [ "$got" = "$want" ] || { echo "SELFTEST-FAIL"; exit 8; }
done
cat > "$D/counts.py" <<'EOF'
import json, sys
from collections import Counter
f, item_files = sys.argv[1], sys.argv[2:]
items = {json.loads(x)["item_id"] for p in item_files for x in open(p, encoding="utf-8") if x.strip()}
raw = open(f, "rb").read()
rows, bad = [], 0
for x in raw.decode("utf-8").splitlines():
    if x.strip():
        try:
            rows.append(json.loads(x))
        except ValueError:
            bad += 1
ok = [r for r in rows if r.get("answer")]
okids = {r["item_id"] for r in ok}
print(json.dumps({"file": f.split("/")[-1], "lines": len(rows), "bad_lines": bad, "nonempty": len(ok), "empty": len(rows) - len(ok),
                  "empty_errors": dict(Counter(str(r.get("error")) for r in rows if not r.get("answer"))),
                  "distinct_ids": len({r.get("item_id") for r in rows}), "answered_ids": len(okids),
                  "answered_ids_by_prefix": dict(sorted(Counter(i[:3] for i in okids).items())),
                  "items": len(items), "items_answered": len(okids & items), "items_left": len(items - okids),
                  "answered_ids_not_items": len(okids - items), "models": sorted({str(r.get("model")) for r in rows}),
                  "crlf": raw.count(b"\r\n")}))
EOF
echo "start counts: $("$PYBIN" -B "$D/counts.py" "$O/answers/answers.jsonl" $K $G "$O/chats/chats.jsonl")"
echo "== 4. answer chunk r1 (60-minute cap, 1 call at once)"
echo "chunk r1 start $(date -u '+%F %T') UTC"
( i=0; while [ ! -e "$O/.chunk-done" ] && [ $i -lt 140 ]; do i=$((i+1)); sleep 30; n=$(k1hpy | wc -l | tr -d ' '); [ "$n" -gt 1 ] && echo "$(date -u +%T) $n python/uv claude_k1h_luna.py processes: $(k1hpy | tr '\n' ';')" >> "$O/others.txt"; done ) &
perl -e 'alarm shift; exec @ARGV' 3960 "$PYBIN" -B scripts/claude_k1h_luna.py answer --items $K --items $G --items "$O/chats/chats.jsonl" --out "$O/answers" --workers 1 --cap-minutes 60 > "$O/answer-log-r1.txt" 2>&1
rc=$?; touch "$O/.chunk-done"; wait
echo "chunk r1 rc=$rc end $(date -u '+%F %T') UTC"
echo "last line: $(tail -1 "$O/answer-log-r1.txt" | grep '^{' || echo '(not a counts line)')"
echo "r1 tries by kind: $(grep -o 'kind=[a-z]*' "$O/answer-log-r1.txt" | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
echo "r1 $(okstats "$O/answer-log-r1.txt")"
echo "r1 error names: $(grep -oE '^[A-Za-z_.]*(Error|Exception)' "$O/answer-log-r1.txt" | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
if [ -f "$O/others.txt" ]; then echo "OTHER k1h luna process seen during the chunk ($(wc -l < "$O/others.txt" | tr -d ' ') checks):"; head -5 "$O/others.txt"; else echo "no other claude_k1h_luna.py process seen during the chunk"; fi
echo "== 5. route filter and counts"
"$PYBIN" -B scripts/claude_k1h_routefilter.py --answers "$O/answers/answers.jsonl" --out "$O/answers/answers_filtered.jsonl"
for f in answers.jsonl answers_filtered.jsonl; do echo "counts: $("$PYBIN" -B "$D/counts.py" "$O/answers/$f" $K $G "$O/chats/chats.jsonl")"; done
"$PYBIN" - "$O/chats/chats.jsonl" <<'EOF'
import json, sys
from collections import Counter
raw = open(sys.argv[1], "rb").read()
rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
print("chats counts: " + json.dumps({"lines": len(rows), "distinct_ids": len({r["item_id"] for r in rows}),
      "prefix": dict(Counter(r["item_id"][:4] for r in rows)), "chat_writer": dict(Counter(str(r.get("chat_writer")) for r in rows)),
      "kind": dict(Counter(str(r.get("kind")) for r in rows)), "crlf": raw.count(b"\r\n")}))
EOF
echo "== 6. copy back"
mkdir -p "$W/$R"
cp "$O/answers/answers.jsonl" "$O/answers/answers_filtered.jsonl" "$O/chats/chats.jsonl" "$O/answer-log-r1.txt" "$W/$R/"
[ -f "$O/others.txt" ] && cp "$O/others.txt" "$W/$R/"
[ -f "$OLD/O/chats-log.txt" ] && cp "$OLD/O/chats-log.txt" "$W/$R/old-chats-log.txt"
for f in "$OLD"/O/answer-log-*.txt; do [ -f "$f" ] && cp "$f" "$W/$R/old-$(basename "$f")"; done
for f in answers/answers.jsonl answers/answers_filtered.jsonl chats/chats.jsonl answer-log-r1.txt; do
  cmp -s "$O/$f" "$W/$R/$(basename "$f")" && echo "copy same: $(basename "$f")" || echo "COPY-DIFFERS: $(basename "$f")"
done
(cd "$W/$R" && shasum -a 256 *)
cd "$W" && rm -rf "$D" && [ ! -e "$D" ] && echo "removed $D"
echo "the old job's folder $OLD is left as it is"
echo "end $(date -u '+%F %T') UTC"
```
