#!/bin/bash
# mu-406 on ONE vast rental: start ("Making things up about you" thread, Claude, 2026-09-27). Built from the sleep research
# thread's handoff/kit/sleep358sv/vstart.sh. Run by the BASH-ONLY job handoff/held/rent406-1-start.md only after release.
# It rents nothing unless the teacher gate has passed and the training data is sealed (SEAL-data.sha256.txt on main).
# Card: the single-GPU offer with the best TFLOPS per $/h among those that pass every check in vcommon.sh (GPU RAM in MB,
# compute capability, price ceiling, and the fit check: estimated hours x 1.3 x $/h at most 0.8 x the $3.00 money stop), up to
# 3 hosts. It logs the card, its TFLOPS, its $/h and TFLOPS per $/h, scales the time cap by 5090 TFLOPS / the card's, attaches
# the Mac's ssh key, sends the sealed code and data (from the SEAL-data commit) and box/drive.sh (from this kit's pinned
# commit), starts drive.sh detached, waits until training has started, then leaves the Mac guard running (vguard.sh).
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/madeup406v/vcommon.sh"
echo "mu-406 vast start, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  for p in $A/vast $A/SEAL-run-vast.sha256.txt $A/VERIFY.md; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (an earlier rental or a verdict exists)"; exit 0; }; done; done
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
git cat-file -e "origin/main:$A/SEAL-data.sha256.txt" 2>/dev/null || { echo "STOP: $A/SEAL-data.sha256.txt is not on main (the teacher gate has not passed); rented nothing"; exit 0; }
DPIN=$(git log -1 --format=%H origin/main -- "$A/SEAL-data.sha256.txt")
echo "data commit (last change to SEAL-data): $DPIN"
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"; cp "$KD/handoff/kit/madeup406v/vcommon.sh" "$KD/handoff/kit/madeup406v/vguard.sh" "$G/"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" 4 || { log "STOP: credit \$${CR:-?} is under the \$4 cap; nothing rented"; exit 0; }
$VAST search offers "$QUERY" -o dph --raw < /dev/null 2> /dev/null > "$G/offers.json"
$PYM - "$G/offers.json" "$MAXDPH" "$MINRAM_MB" "$MINCC" "$TF5090" "$REFMIN" "$FITSHARE" "$CAP_STOP" > "$G/offers.txt" 2> "$G/offers-note.txt" <<'EOS'
import json, sys
try:
    d = json.load(open(sys.argv[1])); d = d.get("offers", d) if isinstance(d, dict) else d
except Exception:
    d = []
maxdph, minmb, mincc, ref, refmin, share, cap = (float(x) for x in sys.argv[2:9])
rows, drop, seen = [], {"price": 0, "gpu_ram": 0, "compute_cap": 0, "fit": 0, "same_host": 0}, set()
for o in d:
    dph, tf = float(o.get("dph_total") or 0), float(o.get("total_flops") or 0)
    if dph <= 0 or tf <= 0 or dph > maxdph: drop["price"] += 1; continue
    if float(o.get("gpu_ram") or 0) < minmb: drop["gpu_ram"] += 1; continue          # raw offers give GPU RAM in MB
    if float(o.get("compute_cap") or 0) < mincc: drop["compute_cap"] += 1; continue
    slow = max(1.0, ref / tf); est_h = refmin * slow / 60
    if est_h * 1.3 * dph > share * cap: drop["fit"] += 1; continue                  # estimate x $/h within 0.8 x the money stop
    rows.append((tf / dph, o))
rows.sort(key=lambda r: -r[0])
out = []
for tpd, o in rows:
    if o.get("host_id") in seen: drop["same_host"] += 1; continue
    seen.add(o.get("host_id"))
    slow = max(1.0, ref / float(o["total_flops"]))
    out.append("%s %.3f %s %s %s %.1f %d %.1f %.3f %d" % (o["id"], float(o["dph_total"]), o.get("cpu_cores_effective"), o.get("host_id"),
               str(o.get("gpu_name", "?")).replace(" ", "_"), float(o["total_flops"]), int(float(o.get("gpu_ram") or 0)), tpd, slow,
               round(refmin * slow)))
print("\n".join(out[:3]))
print("offers read %d; kept %d; dropped: over $%.2f/h or no price %d, under %d MB GPU RAM %d, compute capability under %d %d, "
      "estimate x 1.3 x $/h over %.2f %d, second offer on a host %d" % (len(d), len(out), maxdph, drop["price"], minmb,
      drop["gpu_ram"], mincc, drop["compute_cap"], share * cap, drop["fit"], drop["same_host"]), file=sys.stderr)
EOS
OFFERS=$(cat "$G/offers.txt")
log "$(cat "$G/offers-note.txt")"
echo "offers, best TFLOPS per \$/h first (id \$/h cores host gpu TFLOPS GPU-MB TFLOPS-per-\$/h slowdown-vs-5090 estimated-minutes):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer passes the card checks ($QUERY); nothing rented"; exit 0; }
ID=""; n=0; : > "$G/rentals.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH CORES HID GPU TF RAM TPD SLOW EST; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 60 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"
  log "rental $n: instance $I (offer $OID, host $HID, card $GPU, $TF TFLOPS, $RAM MB GPU RAM, $CORES cores, \$$DPH/h, $TPD TFLOPS per \$/h, estimated $EST min)"
  # running, then attach the Mac's ssh key (re-sent every 80 s, as rent-rv390b does) until ssh answers
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep ${PS406:-10}; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$DPIN" scripts $A artifacts/claude-mu405-20260926/JUDGE-claims405.md artifacts/claude-mu407-20260927/JUDGE-fit407.md \
    artifacts/claude-mu407-20260927/prep/frames.json artifacts/claude-bm390-20260925/data-manifest.json | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  git archive "$PIN" handoff/kit/madeup406v/box | $SS "tar -x -C /root/r" 2>> "$G/log.txt"
  want=$(git show "$PIN:handoff/kit/madeup406v/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/madeup406v/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { log "rental $n: drive.sh on the rental ($got) does not match $PIN ($want)"; destroy "$I"; continue; }
  wantd=$(git show "$DPIN:$A/SEAL-data.sha256.txt" | shasum -a 256 | awk '{print $1}')
  gotd=$($SS "sha256sum /root/r/$A/SEAL-data.sha256.txt" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$wantd" = "$gotd" ] || { log "rental $n: SEAL-data on the rental ($gotd) does not match $DPIN ($wantd)"; destroy "$I"; continue; }
  $SS "cd /root/r && { setsid nohup bash handoff/kit/madeup406v/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & }; echo launched" < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v b="$BASE_TIME" -v s="$SLOW" 'BEGIN{if (s<1) s=1; printf "%d", b*s}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"
  log "time cap $TC s ($BASE_TIME s on a 5090 x slowdown $SLOW = 5090 $TF5090 / $GPU $TF TFLOPS, never below 1x); money stop \$$CAP_STOP"; break
done <<EOF2
$OFFERS
EOF2
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; exit 0; }
log "drive.sh launched on $ID (code and data from $DPIN, drive.sh from $PIN)"
# watch the rental's own progress file until training starts (pip, model, seals, selftests and data first), at most 25 min
last=""; for w in $(seq 1 50); do sleep ${PW406:-30}
  last=$($SS "grep -E ' (FAILED |TRAIN-START)' /root/r/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"TRAIN-START"*) break;; esac; done
$SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
case "$last" in
  *"TRAIN-START"*) ;;
  *) log "STOPPED: drive.sh did not start training (last: ${last:-none})"
     if copy_back logs || copy_back logs; then destroy "$ID" && R=START-FAIL || R=START-FAIL-DESTROY-UNCONFIRMED
     else stop_inst "$ID"; R=START-FAIL-STOPPED-NOT-DESTROYED; fi
     echo "END $R spent $(spent)" > "$G/END"; log "END $R"; exit 0;;
esac
(nohup ${CAF406:-caffeinate -i} bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "training started on $ID; guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
echo "STARTED"
