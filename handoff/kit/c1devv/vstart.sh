#!/bin/bash
# c1-dev on ONE vast rental: start (Everyday chat thread, 2026-09-27). Built from handoff/kit/sleep358sv/vstart.sh; run by the
# BASH-ONLY job handoff/held/rent-c1dev-1-start.md only after release. Rents the single-GPU offer with the best TFLOPS per $/h
# that passes the client-side checks (GPU RAM >= 15,000 MB, compute capability >= 8.0, CUDA 12.8 driver) and the fit check
# (estimated hours x $/h + download at the host's $/GB <= 0.8 x the $1.50 money stop); up to 3 hosts. It re-checks before every
# create that this job is still released on main, attaches the Mac's ssh key, sends the sealed code (the c1-dev tree from the
# BensPC kit's commit, SEAL-2 24/24) and this kit's box/drive.sh, starts box/drive.sh detached and the Mac guard (vguard.sh: $1.50 stop, 3 h on a 5090 scaled by TFLOPS;
# destroy only after a manifest-verified copy, else stop the instance without destroying it), then reports how far the rental
# got in up to 35 minutes.
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/c1devv/vcommon.sh"
WQ=${WQC1V:-$HOME/premonition-watch/queue}
echo "c1-dev vast start, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  for p in $A/RESULTS-vast.md $A/run-vast $A/RESULTS-benspc.md; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (a c1-dev run exists)"; exit 0; }; done
  git show "$ref:$A/run/RUN-NOTE-bo.md" 2>/dev/null | grep -q 'LAUNCH chain' && { echo "DUPLICATE: $ref:$A/run/RUN-NOTE-bo.md shows the BensPC chain was launched"; exit 0; }
done
# never beside the BensPC version of this check: refuse while one of its passes is active on main or running on the watcher
# (when the Director releases this rental it moves those passes to handoff/held/superseded/; names matched by *c1dev-benspc*)
q=$(git ls-tree --name-only origin/main handoff/queue/ 2>/dev/null | grep -i 'c1dev-benspc' | tr '\n' ' ')
[ -n "$q" ] && { echo "HELD-BY-BENSPC: $q is still active on main; rented nothing"; exit 0; }
r=$(ls "$WQ" 2>/dev/null | grep -i 'c1dev-benspc.*\.running$' | tr '\n' ' ')
[ -n "$r" ] && { echo "HELD-BY-BENSPC: $r on the watcher; rented nothing"; exit 0; }
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
git cat-file -e "$PIN:handoff/kit/c1devv/box/drive.sh" 2>/dev/null || { echo "STOP: pinned commit $PIN has no box/drive.sh; rented nothing"; exit 0; }
git cat-file -e "$CODE:$A/SEAL-2.sha256.txt" 2>/dev/null || { echo "STOP: code commit $CODE (SEAL-2) not found; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"; cp "$KD/handoff/kit/c1devv/vcommon.sh" "$KD/handoff/kit/c1devv/vguard.sh" "$G/"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" 2 || { log "STOP: credit \$${CR:-?} is under this task's \$2 cap; nothing rented"; exit 0; }
# every offer is checked here, not only by the server's filter: GPU RAM in MB, compute capability, CUDA driver, price and TFLOPS
# present; then the estimate and the fit check; ranked by TFLOPS per $/h, one offer per host, the best 3
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
ref, setup, arms, dlgb, cap, fit = '"$TF5090"', '"$SETUP_MIN"', '"$ARMS_MIN"', '"$DL_GB"', '"$CAP_STOP"', '"$FIT"'
ok = []
for o in d:
    try:
        dph, tf = float(o.get("dph_total") or 0), float(o.get("total_flops") or 0)
        ram, cc, cu = float(o.get("gpu_ram") or 0), float(o.get("compute_cap") or 0), float(o.get("cuda_max_good") or 0)
        dlc, ng = float(o.get("inet_down_cost") or 0), int(o.get("num_gpus") or 0)
    except (TypeError, ValueError):
        continue
    if dph <= 0 or tf <= 0 or ng != 1 or ram < '"$MINRAM_MB"' or cc < '"$MINCC"' or cu < 12.8:
        continue
    est = setup + arms * max(1.0, ref / tf)                  # minutes
    cost = est / 60 * dph + dlgb * dlc
    if cost > fit * cap:
        continue
    ok.append((tf / dph, o, est, cost, dlgb * dlc))
ok.sort(key=lambda t: -t[0])
seen = set()
for r, o, est, cost, dl in ok:
    if o.get("host_id") in seen:
        continue
    seen.add(o.get("host_id"))
    print(o["id"], round(float(o["dph_total"]), 3), o.get("cpu_cores_effective"), o.get("host_id"),
          str(o.get("gpu_name", "?")).replace(" ", "_"), round(float(o["total_flops"]), 1), int(float(o["gpu_ram"])),
          round(r), int(est), round(cost, 2), round(dl, 3))' | head -3)
echo "offers, best TFLOPS per \$/h first (id \$/h cores host gpu TFLOPS MB TFLOPS-per-\$/h est-min est-\$ download-\$):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer passes the checks and the fit (estimate <= $FIT x \$$CAP_STOP) ($QUERY); nothing rented"; exit 0; }
ID=""; n=0; WHY=HOST-FAIL; : > "$G/rentals.txt"; : > "$G/extra.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH CORES HID GPU TF RAM TPD EST COST DLD; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && { log "rental $n: not tried, spent \$$(spent) has reached the \$$CAP_STOP stop"; WHY=BUDGET-STOP; break; }
  # RE-CHECK BEFORE EACH RENTAL (330 kit): this job must still be released (in handoff/queue/ on main, no STATUS: HELD line)
  git fetch -q origin main 2>/dev/null
  if [ -z "${NOQC1V:-}" ]; then
    git cat-file -e "origin/main:handoff/queue/$JOB.md" 2>/dev/null && ! git show "origin/main:handoff/queue/$JOB.md" 2>/dev/null | grep -q '^STATUS: HELD' \
      || { log "rental $n: not created, handoff/queue/$JOB.md is no longer released on main"; WHY=NOT-RELEASED; break; }
  fi
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"
  log "rental $n: instance $I (offer $OID, host $HID, card $GPU, $TF TFLOPS, $RAM MB GPU RAM, $CORES cores, \$$DPH/h, $TPD TFLOPS per \$/h; estimate $EST min, about \$$COST with \$$DLD download; fit limit \$$(awk -v f="$FIT" -v c="$CAP_STOP" 'BEGIN{printf "%.2f", f*c}'))"
  # running, then attach the Mac's ssh key (re-sent every 80 s, as rent-rv390b does) until ssh answers; at most 8 min
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep ${SLV:-10}; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$CODE" scripts design/v3/60-listener artifacts/claude-chatdev-20260926 $A artifacts/claude-ch403-20260926/JUDGE-BRIEF.md \
    | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  git archive "$PIN" handoff/kit/c1devv/box | $SS "tar -x -C /root/r" 2>> "$G/log.txt"
  want=$(git show "$PIN:handoff/kit/c1devv/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/c1devv/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { log "rental $n: drive.sh on the rental ($got) does not match $PIN ($want)"; destroy "$I"; continue; }
  echo "$I $DLD" >> "$G/extra.txt"
  # braces: only setsid goes to the background. Without them the whole `cd && setsid` list is backgrounded, its subshell keeps
  # ssh's output open until drive.sh ends, and ssh never returns (358u's start stalled that way at 14:04 UTC 09-27)
  $SS "cd /root/r && { setsid nohup bash handoff/kit/c1devv/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & } ; echo launched" < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v b="$BASE_TIME" -v r="$TF5090" -v t="$TF" 'BEGIN{x=r/t; if (x<1) x=1; printf "%d", b*x}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"; echo "$GPU $TF $DPH $TPD $EST" > "$G/card"
  log "time cap $TC s (3 h x 5090 $TF5090 / $GPU $TF TFLOPS, never below 1x); money stop \$$CAP_STOP"; break
done <<EOF
$OFFERS
EOF
[ -n "$ID" ] || { log "$WHY: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; echo "END $WHY spent $(spent)" > "$G/END"; exit 0; }
log "drive.sh launched on $ID"
(nohup ${CAFC1V-caffeinate -i} bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' '))"
# report how far the rental got: arm D started, or the guard ended (a failed start is copied back and ended by the guard)
last=""; for w in $(seq 1 ${WAITC1V:-42}); do sleep ${SLW:-50}
  [ -s "$G/END" ] && break
  last=$($SS "grep -E ' (FAILED |ARM D start)' /root/r/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"ARM D start"*) break;; esac; done
$SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
if [ -s "$G/END" ]; then echo "ENDED: $(cat "$G/END") (see the collect job)"
else case "$last" in
  *"ARM D start"*) log "arm D started on $ID; spent so far \$$(spent)"; echo "STARTED";;
  *"FAILED "*) echo "START-FAILED on the rental: ${last#* FAILED }; the guard copies back and ends it within 5 min (see the collect job)";;
  *) echo "NOT-YET: arm D had not started after $((${WAITC1V:-42} * ${SLW:-50} / 60)) min (last: ${last:-none}); the guard keeps watching (see the collect job)";;
esac; fi
