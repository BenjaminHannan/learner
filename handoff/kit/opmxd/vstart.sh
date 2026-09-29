#!/bin/bash
# opus-mxd (sparse-MoE mxd-1, GPU smoke + phase 1, NO holdout) on ONE vast rental: start. Copy of handoff/kit/s3v/vstart.sh, run by the BASH-ONLY job
# handoff/queue/opus-mxd-vast-1-start.md. Rents the single-GPU offer with the best TFLOPS per $/h (>= 16 GB GPU RAM, compute capability >= 8.0, at most $0.50/h;
# reliability >= 0.98, >= 8 CPU cores, inet_down >= 200; up to 3 hosts; only if estimate x price <= 0.8 x $2.50), attaches the Mac's ssh key, sends the pinned code
# (git archive: scripts, the sealed moe folder, the fewex folder, the loop-source sha file, this kit's box/), sends the loop control sources from the Mac if they
# match their recorded sha256 (else logs LOOP-SOURCE-MISSING and drive.sh omits --loop-source-root), starts box/drive.sh detached, waits until its checks
# (torch pin, seal, selftest) passed, then leaves the Mac guard running (vguard.sh: $2.50 money stop, 1.5 x the card's estimate; destroy only after a
# manifest-verified copy, else stop the instance, not destroy it).
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/opmxd/vcommon.sh"
echo "opus-mxd vast start, kit $PIN, job $JOB, $(now)"
# duplicates: an earlier rental's collected results, or the BensPC job mxd-1 (same science) having produced its GPU smoke or runs on main
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$OUT/run-vast/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $OUT/run-vast/COLLECT.txt (an earlier rental produced mxd-vast results)"; exit 0; }
  for p in $A/SMOKE-gpu.json $A/runs $A/eq-runs; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (BensPC job mxd-1 ran; the Director withdraws one of the two, neither chosen by score)"; exit 0; }; done; done
# a retry after HOST-FAIL (no rental ever launched, every rental ended, nothing live): keep the old record beside, start fresh
if [ -e "$G/rentals.txt" ] && [ ! -s "$G/END" ] && grep -q "HOST-FAIL: no rental got as far as launching" "$G/log.txt" 2>/dev/null \
   && [ "$(awk 'NF<4' "$G/rentals.txt" | wc -l | tr -d ' ')" = 0 ] && [ -z "$(labelled)" ]; then
  mv "$G" "$G.hostfail-$(date +%s)"; echo "RETRY: the earlier start ended HOST-FAIL with every rental ended; its record is kept at $G.hostfail-*"; fi
# a retry after START-FAIL (the rental was destroyed and confirmed gone before the phase started, every rental ended, nothing live): keep the old record beside, start fresh
if [ -e "$G/rentals.txt" ] && grep -q "^END START-FAIL spent" "$G/END" 2>/dev/null \
   && [ "$(awk 'NF<4' "$G/rentals.txt" | wc -l | tr -d ' ')" = 0 ] && [ -z "$(labelled)" ]; then
  mv "$G" "$G.startfail-$(date +%s)"; echo "RETRY: the earlier start ended START-FAIL with every rental ended; its record is kept at $G.startfail-*"; fi
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"; cp "$KD/handoff/kit/opmxd/vcommon.sh" "$KD/handoff/kit/opmxd/vguard.sh" "$G/"
CR=$($VAST show user --raw 2>/dev/null | grep -oE '"credit": *-?[0-9.]+' | grep -oE -- '-?[0-9.]+$' | head -1)
log "credit \$${CR:-?}"
over "${CR:-0}" "$CAP_STOP" || { log "STOP: credit \$${CR:-?} is under the \$$CAP_STOP cap; nothing rented"; exit 0; }
# the loop control sources on the Mac (mxd-1 step 2): both there and matching the recorded sha256, else LOOP-SOURCE-MISSING (the MoE parts still run)
LOOPOK=1
for S in 0 1; do
  want=$LSHA0; [ $S = 1 ] && want=$LSHA1
  got=$(shasum -a 256 "$LSRC/qual-loop-s$S/source.pt" 2>/dev/null | awk '{print $1}')
  [ -n "$got" ] && [ "$got" = "$want" ] || { LOOPOK=0; log "LOOP-SOURCE-MISSING: $LSRC/qual-loop-s$S/source.pt is missing or does not match the recorded sha256 (got ${got:-nothing})"; }
done
[ $LOOPOK = 1 ] && log "loop control sources on the Mac: both match the recorded sha256"
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
ex=set("'"$EXCLUDE_HOSTS"'".split())
ok=[o for o in d if str(o.get("host_id")) not in ex and o.get("dph_total") and o.get("total_flops") and float(o["dph_total"]) <= '"$MAXDPH"' and 800 <= float(o.get("compute_cap") or 0) < 1200 and (o.get("gpu_ram") or 0) >= '"$MINRAM_GB"'*1000]
def est(o): return '"$BASE_H"' * max(1.0, '"$TF5090"' / float(o["total_flops"]))
ok=[o for o in ok if est(o) * float(o["dph_total"]) <= '"$FIT"' * '"$CAP_STOP"']
ok.sort(key=lambda o: -float(o["total_flops"]) / float(o["dph_total"]))
seen=set()
for o in ok:
    if o.get("host_id") in seen: continue
    seen.add(o.get("host_id"))
    print(o["id"], round(o["dph_total"],3), o.get("cpu_cores_effective"), o.get("host_id"), str(o.get("gpu_name","?")).replace(" ","_"), round(float(o["total_flops"]),1), round((o.get("gpu_ram") or 0)/1000), round(est(o),2))' | head -3)
echo "offers, best TFLOPS per \$/h first (id \$/h cores host gpu TFLOPS GB est_hours):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer at or under \$$MAXDPH/h with >= $MINRAM_GB GB whose estimate ($BASE_H h x max(1, $TF5090/TFLOPS)) x price fits 0.8 x \$$CAP_STOP ($QUERY); nothing rented"; exit 0; }
ID=""; n=0; : > "$G/rentals.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH CORES HID GPU TF RAM EST; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"; log "rental $n: instance $I (offer $OID, host $HID, $GPU, $TF TFLOPS, $RAM GB, $CORES cores, \$$DPH/h, $(awk -v t="$TF" -v d="$DPH" 'BEGIN{printf "%.0f", t/d}') TFLOPS per \$/h)"
  # running, then attach the Mac's ssh key (re-sent every 80 s) until ssh answers
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$PIN" scripts $A artifacts/claude-fewex-20260927 artifacts/claude-distill-20260928/checkpoints-sha256.txt handoff/kit/opmxd/box | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  want=$(git show "$PIN:handoff/kit/opmxd/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/opmxd/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { log "rental $n: drive.sh on the rental ($got) does not match $PIN ($want)"; destroy "$I"; continue; }
  # loop control sources (mxd-1 step 3): scp source.pt, then source.json from the archive already on the rental
  if [ $LOOPOK = 1 ]; then SC=$(scpto "$H" "$P"); lc=1
    for S in 0 1; do
      $SS "mkdir -p /root/r/loopsrc/qual-loop-s$S" < /dev/null 2>> "$G/log.txt" \
        && $SC "$LSRC/qual-loop-s$S/source.pt" "root@$H:/root/r/loopsrc/qual-loop-s$S/source.pt" < /dev/null 2>> "$G/log.txt" \
        && $SS "cp /root/r/artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json /root/r/loopsrc/qual-loop-s$S/source.json" < /dev/null 2>> "$G/log.txt" || lc=0; done
    [ $lc = 1 ] && log "loop control sources sent to the rental (drive.sh re-checks their sha256)" || log "LOOP-SOURCE-MISSING: sending the loop sources to the rental failed (drive.sh will omit --loop-source-root)"; fi
  $SS "cd /root/r && { setsid nohup bash handoff/kit/opmxd/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & } ; echo launched" < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v e="$EST" 'BEGIN{printf "%d", e*1.5*3600}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"; log "estimate $EST h (5090 $TF5090 / $GPU $TF TFLOPS, never below 1x); time cap $TC s (1.5x); money stop \$$CAP_STOP"; break
done <<EOT
$OFFERS
EOT
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; exit 0; }
log "drive.sh launched on $ID"
# watch the rental's own progress file until its checks passed (pip + seal + selftest first), at most 15 min
last=""; for w in $(seq 1 30); do sleep 30
  last=$($SS "grep -E ' (FAILED |CHECKS-OK)' /root/r/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"CHECKS-OK"*) break;; esac; done
$SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
case "$last" in
  *"CHECKS-OK"*) ;;
  *) log "STOPPED: drive.sh did not pass its checks (last: ${last:-none})"
     if copy_back logs || copy_back logs; then destroy "$ID" && R=START-FAIL || R=START-FAIL-DESTROY-UNCONFIRMED
     else stop_inst "$ID"; R=START-FAIL-STOPPED-NOT-DESTROYED; fi
     echo "END $R spent $(spent)" > "$G/END"; log "END $R"; exit 0;;
esac
(nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "checks passed on $ID (smoke and phase 1 running); guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
echo "STARTED"
