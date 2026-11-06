#!/bin/zsh
# Full first-run test of the uncle .dmg's app under a fresh HOME + empty userData (no new macOS user: no admin password).
# Runs INSIDE realmodel-lock. A: first launch, stop mid-download. B: relaunch -> resume, warm up, setup, chat, name, a fact.
# C: quit + reopen -> remembered? Every app is stopped by its exact PID. Log: e2e.log; screenshots shot-*.png.
T=$HOME/learner-ops/uncle-mac/test; BASE_HOME=$HOME/learner-ops/uncle-mac/test-home; H=$BASE_HOME/runs/$(date +%Y%m%d-%H%M%S)-$$; PORT=9341
set -e
set -o pipefail
APP="$BASE_HOME/Applications/Premonition.app"; UD="$H/Library/Application Support/Premonition"; mkdir -p "$UD"
printf '%s\n' "$H" > "$T/last-home"
N=$HOME/learner-ops/node22/bin/node
rm -f "$T/marks.jsonl"
shasum -a 256 "$HOME/learner-ops/uncle-mac/Glim-2.0.0-mac.dmg" | awk '{print $1}' > "$T/dmg-under-test.sha256"
[[ ! -f "$UD/settings.json" ]] || { echo 'This test needs a fresh test home, not an old chat.' >> "$T/e2e.log"; exit 1; }
mark() { $N "$T/check.js" "$1" "$2" "$3"; }
log() { echo "$(date +%T) $*" | tee -a $T/e2e.log; }
cdp() { $N $T/cdp.mjs $PORT "$@" 2>&1; }
st() { cdp eval "desk.runtime.state().then(s=>JSON.stringify({p:s.phase,done:s.done,total:s.total,model:s.model,eyes:s.eyes,err:s.error}))"; }
launch() {
  env -i HOME="$H" USER="$USER" LOGNAME="$USER" PATH=/usr/bin:/bin:/usr/sbin:/sbin TMPDIR="$TMPDIR" LANG=en_US.UTF-8 PREMONITION_USER_NAME="Uncle Test" \
    "$APP/Contents/MacOS/Premonition" --user-data-dir="$UD" --remote-debugging-port=$PORT >> "$T/app-e2e-$1.log" 2>&1 &
  APID=$!; log "launch $1: app pid $APID"
  for i in {1..60}; do curl -fs -m 2 http://127.0.0.1:$PORT/json/list >/dev/null && break; sleep 1; done; sleep 6
}
llama_pid() { ps -axo pid=,ppid=,command= | awk -v p=$APID '$2==p && /llama-server/ {print $1}' | head -1; }
stop_app() {
  local lp=$(llama_pid); log "stop app $APID (llama ${lp:-none})"; kill $APID 2>/dev/null
  for i in {1..30}; do kill -0 $APID 2>/dev/null || break; sleep 1; done
  kill -0 $APID 2>/dev/null && { log "app still up; SIGKILL $APID"; kill -9 $APID; }
  sleep 3; [[ -n "$lp" ]] && kill -0 $lp 2>/dev/null && { log "llama-server $lp left behind; stopping it"; kill $lp; }
  APID=''
  return 0
}
cleanup() { [[ -n "$GUARD_PID" ]] && kill "$GUARD_PID" 2>/dev/null; [[ -n "$APID" ]] && stop_app; true; }
trap cleanup EXIT
trap 'log "Ben is back. Stopping this test, not marking a pass."; exit 75' TERM INT
/bin/zsh "$T/idle-guard.sh" $$ &
GUARD_PID=$!
wait_phase() {  # wait until phase matches $1 (regex) or timeout $2 s
  local s; for ((i=0; i<$2; i+=10)); do s=$(st); [[ "$s" =~ "\"p\":\"($1)\"" ]] && { echo "$s"; return 0; }; sleep 10; done; echo "TIMEOUT $s"; return 1
}
log "=== e2e start; idle $(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}') s; $(memory_pressure | tail -1)"
MOUNT=$(cat "$HOME/learner-ops/uncle-mac/.mnt")
[[ -d "$MOUNT/Premonition.app" ]] || { log 'FAIL: image mount missing; mount the image being tested first'; exit 1; }
hdiutil info -plist | plutil -convert json -o - - | $N -e 'let raw="";process.stdin.on("data",part=>raw+=part);process.stdin.on("end",()=>{const fs=require("node:fs"),images=JSON.parse(raw).images;const [image,mount]=process.argv.slice(1);if(!images.some(item=>fs.realpathSync(item["image-path"])===fs.realpathSync(image)&&(item["system-entities"]||[]).some(entity=>entity["mount-point"]&&fs.realpathSync(entity["mount-point"])===fs.realpathSync(mount))))process.exitCode=1})' "$HOME/learner-ops/uncle-mac/Glim-2.0.0-mac.dmg" "$MOUNT" || { log 'FAIL: mount is not this image'; exit 1; }
$N "$T/compare-apps.js" "$MOUNT/Premonition.app" "$APP" > "$T/app-image-diff.log" 2>&1 || { log 'FAIL: test app is not the mounted image app'; exit 1; }
# ---- A: first launch, stop partway through the download
launch A; log "A state: $(st)"; cdp shot $T/shot-A-start.png >/dev/null
for i in {1..360}; do s=$(st); d=$(echo $s | sed -E 's/.*"done":([0-9]+).*/\1/'); [[ "$d" =~ ^[0-9]+$ && $d -gt 1000000000 ]] && break; sleep 5; done
log "A before stop: $s"; cdp shot $T/shot-A-download.png >/dev/null
mark download "$s" 'value.p === "downloading" && value.done > 1000000000'
stop_app
PART=$(ls "$UD"/runtime/models/*.part 2>/dev/null); log "A left: $(ls -l "$UD"/runtime/models/ | tail -n +2)"
[[ -n "$PART" && -s "$PART" ]] || { log 'FAIL: no partial brain to resume'; exit 1; }
PART_BYTES=$(stat -f %z "$PART")
# ---- B: reopen -> resume -> ready
launch B; sleep 20; RESUME_STATE=$(st); log "B first state (should continue past the .part): $RESUME_STATE"
mark resume "$RESUME_STATE" 'value.p === "ready" || value.p === "starting" || value.done >= '"$PART_BYTES"
t0=$(date +%s); r=$(wait_phase 'ready|error|blocked' 5400); log "B: $r after $(( $(date +%s) - t0 )) s"; cdp shot $T/shot-B-ready.png >/dev/null
mark ready "$r" 'value.p === "ready"'
mark bundled-engine "$(cat "$UD/runtime/state.json")" 'Object.values(value.llama || {}).some(engine => engine.bundled === true)'
HAS_RECORDER=$(cdp eval 'typeof desk.recorder === "object"')
if [[ "$HAS_RECORDER" == true ]]; then
  mark recorder-default-off "$(cdp eval 'desk.recorder.status().then(s=>JSON.stringify(s))')" 'value.choice === null && value.enabled === false'
  cdp eval '(()=>{const no=document.getElementById("obRecorderNo");if(!no)throw Error("No recording choice screen");no.click();return true})()' >/dev/null
  sleep 2
  mark recorder-no "$(cdp eval 'desk.recorder.status().then(s=>JSON.stringify(s))')" 'value.choice === false && value.enabled === false'
fi
LP=$(llama_pid); log "llama-server pid $LP: $(ps -o command= -p $LP | cut -c1-400)"
log "memory: $(footprint -p $LP 2>/dev/null | grep -E 'phys_footprint' | head -2 | tr '\n' ' ') rss_kb=$(ps -o rss= -p $LP)"
log "app total footprint: $(for p in $APID $(pgrep -P $APID); do footprint -p $p 2>/dev/null | grep -E '^ *phys_footprint:' | head -1; done | tr '\n' ' ')"
log "files: $(cd "$UD/runtime" && ls -l models; shasum -a 256 models/*.gguf)"
# setup screens: Enter through them
for k in {1..10}; do v=$(cdp eval "(()=>{const o=document.getElementById('onboard');return o&&!o.hidden&&getComputedStyle(o).display!=='none'})()"); [[ "$v" == "true" ]] || break; cdp shot $T/shot-B-setup-$k.png >/dev/null; cdp eval "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));1" >/dev/null; sleep 2; done
sleep 4; cdp shot $T/shot-B-opener.png >/dev/null
TID=$(cdp eval "desk.threads.list().then(l=>{const t=l.find(x=>!x.helper);return t?t.id:''})"); log "thread $TID"
[[ -n "$TID" && "$TID" != undefined ]] || { log 'FAIL: no chat thread'; exit 1; }
log "first message: $(cdp eval "desk.threads.load('$TID').then(t=>JSON.stringify(t.messages.slice(0,1)))")"
for q in "Dave" "What's your name?" "Please remember that my favorite color is green." "What is 12 + 7?"; do
  log ">>> $q"; answer=$(cdp eval "$($N $T/say.js $TID "$q")"); log "$answer"
  mark "chat-$q" "$answer" 'typeof value.reply === "string" && value.reply.trim().length > 0'
  [[ "$q" != "What's your name?" ]] || mark name "$answer" '/\bGlim\b/i.test(value.reply)'
  [[ "$q" != 'What is 12 + 7?' ]] || mark arithmetic "$answer" '/\b19\b/.test(value.reply)'
done
cdp shot $T/shot-B-chat.png >/dev/null
log "memory notes: $(cdp eval "desk.memory.list().then(x=>JSON.stringify(x))" | head -c 1500)"
log "sleep: $(cdp eval "desk.sleep.status ? desk.sleep.status().then(x=>JSON.stringify(x).slice(0,400)) : 'n/a'")"
stop_app
# ---- C: reopen; a brand-new chat must still know the name and the fact (saved notes, not chat history)
launch C; r=$(wait_phase 'ready|error' 900); log "C: $r"
mark restart "$r" 'value.p === "ready"'
if [[ "$HAS_RECORDER" == true ]]; then mark recorder-restart-off "$(cdp eval 'desk.recorder.status().then(s=>JSON.stringify(s))')" 'value.choice === false && value.enabled === false'; fi
cdp eval "desk.threads.list().then(async l=>{for(const t of l) if(!t.helper) await desk.threads.remove(t.id);return l.length})" >/dev/null
TID=$(cdp eval "desk.threads.create().then(t=>t.id)"); log "new thread $TID ($(cdp eval "desk.threads.load('$TID').then(t=>t.messages.length)") messages)"
for q in "What's my name, and what is my favorite color?" "What's your name?"; do
  log ">>> $q"; answer=$(cdp eval "$($N $T/say.js $TID "$q")"); log "$answer"
  if [[ "$q" == "What's your name?" ]]; then mark restart-name "$answer" '/\bGlim\b/i.test(value.reply)'
  else mark remembered-fact "$answer" '/\bDave\b/i.test(value.reply) && /\bgreen\b/i.test(value.reply)'; fi
done
cdp shot $T/shot-C-chat.png >/dev/null
stop_app
log "userData after test: $(cd "$UD" && find . -maxdepth 2 | sort | head -60 | tr '\n' ' ')"
log "=== e2e done"
