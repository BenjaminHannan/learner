#!/bin/bash
# rsn-358t v3 on ONE vast rental: start (sleep research thread, 2026-09-27). Copy of handoff/kit/sleep358uv/vstart.sh (358u kit v2)
# for 358t v3, run by the BASH-ONLY job handoff/held/rent358t3-1-start.md only after Ben's yes. Rents the single-GPU offer with the best
# TFLOPS per $/h (>= 24 GB GPU RAM, compute capability >= 8.0, at most $0.65/h; reliability
# >= 0.98, >= 16 CPU cores, inet_down >= 200; up to 3 hosts), attaches the Mac's ssh key, sends the pinned code (scripts, the
# 358t folder, 358i's tests, box/drive.sh), starts box/drive.sh detached (torch 2.11.0 pin, SEAL-code-v3 22/22, selftests,
# audit, Stage 0 with the cache-off 0/12 line, the 8 graded trains, seal both checkpoints, eval each once), waits until the
# first run has launched, then leaves the Mac guard running (vguard.sh: $1.45 stop, 3 h 30 min on a 5090 scaled by TFLOPS; destroy only after a
# manifest-verified copy, else stop the instance without destroying it).
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/sleep358tv/vcommon.sh"
echo "rsn-358t v3 vast start, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  for p in $A/RESULTS-v3.md $A/SEAL-run-v3.sha256.txt $A/runs-v3 $A/run-vast-v3; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (BensPC or an earlier rental produced v3 runs)"; exit 0; }; done; done
# never beside the BensPC version of this experiment: refuse while its queue job is still active on main or running on the watcher
# (when the Director releases this rental it moves those jobs to handoff/held/superseded/)
for j in 260-claude-sleep-358t3pc; do
  git cat-file -e "origin/main:handoff/queue/$j.md" 2>/dev/null && { echo "HELD-BY-BENSPC: handoff/queue/$j.md is still active on main; rented nothing"; exit 0; }
  [ -e "${WQ358:-$HOME/premonition-watch/queue}/$j.running" ] && { echo "HELD-BY-BENSPC: $j is running on the watcher; rented nothing"; exit 0; }
done
# a retry after HOST-FAIL (no rental ever launched, every rental ended, nothing live): keep the old record beside, start fresh
if [ -e "$G/rentals.txt" ] && [ ! -s "$G/END" ] && grep -q "HOST-FAIL: no rental got as far as launching" "$G/log.txt" 2>/dev/null \
   && [ "$(awk 'NF<4' "$G/rentals.txt" | wc -l | tr -d ' ')" = 0 ] && [ -z "$(labelled)" ]; then
  mv "$G" "$G.hostfail-$(date +%s)"; echo "RETRY: the earlier start ended HOST-FAIL with every rental ended; its record is kept at $G.hostfail-*"; fi
# a retry after START-FAIL (the rental was destroyed and confirmed gone before any run started, every rental ended, nothing
# live; added after rent-358t3-1b-start failed on a kit bug in the checks gate): keep the old record beside, start fresh
if [ -e "$G/rentals.txt" ] && grep -q "^END START-FAIL spent" "$G/END" 2>/dev/null \
   && [ "$(awk 'NF<4' "$G/rentals.txt" | wc -l | tr -d ' ')" = 0 ] && [ -z "$(labelled)" ]; then
  mv "$G" "$G.startfail-$(date +%s)"; echo "RETRY: the earlier start ended START-FAIL with every rental ended; its record is kept at $G.startfail-*"; fi
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"; cp "$KD/handoff/kit/sleep358tv/vcommon.sh" "$KD/handoff/kit/sleep358tv/vguard.sh" "$G/"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" 1.60 || { log "STOP: credit \$${CR:-?} is under the \$1.60 cap; nothing rented"; exit 0; }
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
ex=set("'"$EXCLUDE_HOSTS"'".split())
ok=[o for o in d if str(o.get("host_id")) not in ex and o.get("dph_total") and o.get("total_flops") and float(o["dph_total"]) <= '"$MAXDPH"' and (o.get("gpu_ram") or 0) >= '"$MINRAM_GB"'*1000]
def waves(gb): return -(-'"$RUNS"' // min('"$RUNS"', int((gb - '"$FREE_GB"') // '"$RUN_GB"') + 1))
w5090 = waves(32.6)
def est(o): return '"$BASE_H"' * max(1.0, '"$TF5090"' / float(o["total_flops"])) * waves((o.get("gpu_ram") or 0) / 1000) / w5090
ok=[o for o in ok if est(o) * float(o["dph_total"]) <= '"$FIT"' * '"$CAP_STOP"']
ok.sort(key=lambda o: -float(o["total_flops"]) / float(o["dph_total"]))
seen=set()
for o in ok:
    if o.get("host_id") in seen: continue
    seen.add(o.get("host_id"))
    print(o["id"], round(o["dph_total"],3), o.get("cpu_cores_effective"), o.get("host_id"), str(o.get("gpu_name","?")).replace(" ","_"), round(float(o["total_flops"]),1), round((o.get("gpu_ram") or 0)/1000), waves((o.get("gpu_ram") or 0)/1000), round(est(o),2))' | head -3)
echo "offers, best TFLOPS per \$/h first (id \$/h cores host gpu TFLOPS GB waves est_hours):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer at or under \$$MAXDPH/h with >= $MINRAM_GB GB matches ($QUERY); nothing rented"; exit 0; }
ID=""; n=0; : > "$G/rentals.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH CORES HID GPU TF RAM WV EST; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"; log "rental $n: instance $I (offer $OID, host $HID, $GPU, $TF TFLOPS, $RAM GB, $CORES cores, \$$DPH/h, $(awk -v t="$TF" -v d="$DPH" 'BEGIN{printf "%.0f", t/d}') TFLOPS per \$/h)"
  # running, then attach the Mac's ssh key (~/.ssh/id_ed25519.pub; re-sent every 80 s, as rent-rv390b does) until ssh answers
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$PIN" scripts $A artifacts/claude-rsn358i-20260926/tests handoff/kit/sleep358tv/box | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  want=$(git show "$PIN:handoff/kit/sleep358tv/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/sleep358tv/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { log "rental $n: drive.sh on the rental ($got) does not match $PIN ($want)"; destroy "$I"; continue; }
  $SS "cd /root/r && { setsid nohup bash handoff/kit/sleep358tv/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & } ; echo launched" < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v e="$EST" 'BEGIN{printf "%d", e*1.5*3600}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"; log "estimate $EST h ($WV waves at $RAM GB; 5090 $TF5090 / $GPU $TF TFLOPS, never below 1x); time cap $TC s (1.5x); money stop \$$CAP_STOP"; break
done <<EOF
$OFFERS
EOF
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; exit 0; }
log "drive.sh launched on $ID"
# watch the rental's own progress file until all 8 trains have launched (pip + seal + selftests first), at most 15 min
last=""; for w in $(seq 1 30); do sleep 30
  last=$($SS "grep -E ' (FAILED |LAUNCH loop-trm-s1 )' /root/r/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"LAUNCH loop-trm-s1 "*) break;; esac; done
$SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
case "$last" in
  *"LAUNCH loop-trm-s1 "*) ;;
  *) log "STOPPED: drive.sh did not launch the first run (last: ${last:-none})"
     if copy_back logs || copy_back logs; then destroy "$ID" && R=START-FAIL || R=START-FAIL-DESTROY-UNCONFIRMED
     else stop_inst "$ID"; R=START-FAIL-STOPPED-NOT-DESTROYED; fi
     echo "END $R spent $(spent)" > "$G/END"; log "END $R"; exit 0;;
esac
(nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "first run launched on $ID (the rest start one by one while 5 GB of GPU memory is free); guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
echo "STARTED"
