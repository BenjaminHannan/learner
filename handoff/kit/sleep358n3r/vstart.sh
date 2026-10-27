#!/bin/bash
# slp-358n3 on ONE vast rental: start (sleep research thread, 2026-09-27). Copy of the 358s kit's vstart.sh, run by the
# BASH-ONLY job handoff/held/rent358n3-1-start.md only after release. It refuses until 358u's 4 loop checkpoints are sealed on main
# and their Mac copies match. It rents the single-GPU offer with the best TFLOPS per $/h that fits the money (>= 24 GB, cc >= 8.0,
# at most $0.60/h, estimate x $/h <= 0.8 x $2.00), attaches the Mac's ssh key, sends the pinned code and the 4 checkpoints,
# starts box/drive.sh detached, waits until the first seed run has launched, then leaves the Mac guard running.
# sleep358n3r (2026-09-28): the base is the rsn-358u2 re-run (its own SEAL-run and Mac copies), per ADDENDUM-1.md, which must be
# on main first; a new host gets 15 min for ssh; copy-back fetches every .pt one file at a time (vcommon.sh). Run by the BASH-ONLY
# job handoff/queue/rent358n3r-1-start.md.
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/sleep358n3r/vcommon.sh"
echo "slp-358n3 vast start (kit sleep358n3r, base rsn-358u2), kit $PIN, job $JOB, $(now)"
git cat-file -e "origin/main:$A/ADDENDUM-1.md" 2>/dev/null || { echo "STOP: $A/ADDENDUM-1.md is not on main; rented nothing"; exit 0; }
for ref in origin/main origin/builder-outbox; do
  for p in $A/RESULTS.md $A/SEAL-run.sha256.txt $A/runs $A/run-vast; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (a verdict or an earlier rental exists)"; exit 0; }; done; done
# the inputs: 358u's 4 loop checkpoints, sealed on main, with matching Mac copies (weights never go to git)
git cat-file -e "origin/main:$SRU" 2>/dev/null || { echo "WAITING: $SRU is not on main yet (358u not collected); rented nothing"; exit 0; }
CKS=""; for S in 13 14 15 16; do
  sha=$(git show "origin/main:$SRU" | awk -v f="loop-s$S/final.pt" '$2==f {print $1}')
  m=$(shasum -a 256 "$MPU/loop-s$S/final.pt" 2>/dev/null | awk '{print $1}')
  [ -n "$sha" ] && [ "$m" = "$sha" ] || { echo "WAITING: loop-s$S/final.pt sealed '${sha:-none}', Mac copy '${m:-missing}'; rented nothing"; exit 0; }
  CKS="$CKS$sha  ck/s$S/final.pt
"; done
echo "inputs: rsn-358u2 loop-s13..16/final.pt sealed on main and matching on the Mac"
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"; cp "$KD/handoff/kit/sleep358n3r/vcommon.sh" "$KD/handoff/kit/sleep358n3r/vguard.sh" "$G/"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" 4 || { log "STOP: credit \$${CR:-?} is under the \$4 cap; nothing rented"; exit 0; }
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
ok=[o for o in d if o.get("dph_total") and o.get("total_flops") and float(o["dph_total"]) <= '"$MAXDPH"' and (o.get("gpu_ram") or 0) >= '"$MINRAM_GB"'*1000]
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
  for w in $(seq 1 $SSH_WAIT); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within $((SSH_WAIT / 6)) min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$PIN" scripts $A artifacts/claude-rsn358i-20260926/tests handoff/kit/sleep358n3r/box | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  for S in 13 14 15 16; do $SS "mkdir -p /root/r/ck/s$S && cat > /root/r/ck/s$S/final.pt" < "$MPU/loop-s$S/final.pt" 2>> "$G/log.txt"; done
  printf '%s' "$CKS" | $SS "cat > /root/r/ck/expected.sha256" 2>> "$G/log.txt"
  nck=$($SS "cd /root/r && sha256sum -c ck/expected.sha256 2>/dev/null | grep -c ': OK\$'" < /dev/null 2>/dev/null)
  [ "$nck" = 4 ] || { log "rental $n: checkpoint upload check $nck/4"; destroy "$I"; continue; }
  want=$(git show "$PIN:handoff/kit/sleep358n3r/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/sleep358n3r/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { log "rental $n: drive.sh on the rental ($got) does not match $PIN ($want)"; destroy "$I"; continue; }
  $SS "cd /root/r && { setsid nohup bash handoff/kit/sleep358n3r/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & } ; echo launched" < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v e="$EST" 'BEGIN{printf "%d", e*1.5*3600}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"; log "estimate $EST h ($WV waves at $RAM GB; 5090 $TF5090 / $GPU $TF TFLOPS, never below 1x); time cap $TC s (1.5x); money stop \$$CAP_STOP"; break
done <<EOF
$OFFERS
EOF
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; exit 0; }
log "drive.sh launched on $ID"
# watch the rental's own progress file until the first seed run has launched (pip + seal + checks + day sizes first), at most 15 min
last=""; for w in $(seq 1 30); do sleep 30
  last=$($SS "grep -E ' (FAILED |LAUNCH s13 )' /root/r/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"LAUNCH s13 "*) break;; esac; done
$SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
case "$last" in
  *"LAUNCH s13 "*) ;;
  *) log "STOPPED: drive.sh did not launch the first run (last: ${last:-none})"
     if copy_back logs || copy_back logs; then destroy "$ID" && R=START-FAIL || R=START-FAIL-DESTROY-UNCONFIRMED
     else stop_inst "$ID"; R=START-FAIL-STOPPED-NOT-DESTROYED; fi
     echo "END $R spent $(spent)" > "$G/END"; log "END $R"; exit 0;;
esac
(nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "first seed run launched on $ID (the rest start one by one while 5 GB of GPU memory is free); guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
echo "STARTED"
