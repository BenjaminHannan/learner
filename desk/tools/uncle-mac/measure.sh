#!/bin/zsh
# Load one GGUF in the bundled llama-server (same flags as the app: ctx 8192, -ngl 99, Glim's template, eyes mmproj),
# send one chat, read its memory (footprint = what Activity Monitor calls Memory), stop it by exact PID.
# usage: measure.sh <gguf> <label>
G=$1; L=$2; T=$HOME/learner-ops/uncle-mac/test
set -e
set -o pipefail
H=$(cat "$T/last-home")
RT="$H/Library/Application Support/Premonition/runtime"
EXE=$(ls "$RT"/llama-b11946-metal/llama-b11946/llama-server)
MM=$HOME/learner-ops/uncle-mac/test-home/Applications/Premonition.app/Contents/Resources/eyes/glim-eyes-mmproj-f16.gguf
"$EXE" -m "$G" --host 127.0.0.1 --port 18190 -c 8192 -np 1 --jinja --no-webui -ngl 99 --chat-template-file "$RT/nanbeige-chat-template.jinja" --mmproj "$MM" > "$T/measure-$L.log" 2>&1 &
P=$!
cleanup() { [[ -n "$GUARD_PID" ]] && kill "$GUARD_PID" 2>/dev/null; kill -0 $P 2>/dev/null && kill $P 2>/dev/null; true; }
trap cleanup EXIT
trap 'echo "Ben is back. Stopping this measurement."; exit 75' TERM INT
/bin/zsh "$T/idle-guard.sh" $$ &
GUARD_PID=$!
for i in {1..120}; do curl -fs -m 2 http://127.0.0.1:18190/health >/dev/null && break; sleep 1; done
curl -fs -m 300 http://127.0.0.1:18190/v1/chat/completions -H 'content-type: application/json' -d '{"messages":[{"role":"user","content":"What is 12 + 7? Answer with the number only."}],"max_tokens":400}' > "$T/measure-$L.reply.json"
$HOME/learner-ops/node22/bin/node "$T/check.js" "measure-$L" "$(cat "$T/measure-$L.reply.json")" 'Array.isArray(value.choices) && /\b19\b/.test(value.choices[0].message.content)'
echo "$L footprint: $(footprint -p $P 2>/dev/null | grep -E 'phys_footprint:' | head -1)"
echo "$L rss_kb: $(ps -o rss= -p $P)"
grep -E "buffer size|KV self size|compute buffer|model size" "$T/measure-$L.log" | head -8
kill $P; sleep 3; kill -0 $P 2>/dev/null && kill -9 $P
exit 0
