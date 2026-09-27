#!/bin/bash
# rd-378g on ONE vast rental: start (Trustworthy notes thread, 2026-09-27). Built from handoff/kit/sleep358sv/vstart.sh, run by
# the BASH-ONLY job handoff/held/rent378g-1-start.md only after the Director releases it (Ben's standing vast order, 14:05-14:06
# UTC). The Director's card rules (14:15 UTC): GPU RAM checked client-side in MB, offers ranked by TFLOPS per $/h, a fit check
# (estimate x $/h <= 0.8 x the money stop), the time cap scaled by TFLOPS and waves, destroy only after a verified copy-back
# (otherwise stop), and the card, its TFLOPS and its $/h logged. It sends the pinned code, starts box/drive.sh detached, starts
# rsend.sh (R from the Mac, for G5) and leaves the Mac guard running (vguard.sh).
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
export COPYFILE_DISABLE=1
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/rd378gv/vcommon.sh"
echo "rd-378g vast start, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  for p in $A/RESULTS.md $A/benspc/RESULTS-benspc.md $V; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (a verdict, a BensPC run or an earlier rental exists)"; exit 0; }; done; done
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
git cat-file -e "$PIN:$A/ADDENDUM-N.md" 2>/dev/null || { echo "NO-SEAL: $PIN has no $A/ADDENDUM-N.md"; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"; for f in vcommon.sh vguard.sh rsend.sh; do cp "$KD/handoff/kit/rd378gv/$f" "$G/"; done
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" "$CAP_STOP" || { log "STOP: credit \$${CR:-?} is under the \$$CAP_STOP money stop; nothing rented"; exit 0; }
[ -f "$MR/model.safetensors" ] && log "R on the Mac: present ($MR); rsend.sh checks its sha256" || log "R on the Mac: absent ($MR); g5R will be skipped (ADDENDUM-K's 57% fallback)"
# the card: search, then every rule checked again on each raw offer (client-side), fit check, rank by TFLOPS per $/h, 3 hosts
$VAST search offers "$QUERY" -o dph --raw < /dev/null > "$G/offers.json" 2>/dev/null
OFFERS=$("$PYM" - "$G/offers.json" "$MAXDPH" "$MINRAM_MB" "$MINCC" "$TF5090" "$EST_MIN" "$WAVES" "$CAP_STOP" 2> "$G/offers-note.txt" <<'EOS'
import json, sys
try:
    d = json.load(open(sys.argv[1])); d = d.get("offers", d) if isinstance(d, dict) else d
except Exception:
    d = []
maxdph, minmb, mincc, tfref, est, waves, cap = [float(x) for x in sys.argv[2:9]]
rows = []; drop = {"price": 0, "ram": 0, "cc": 0, "cuda": 0, "fit": 0}
for o in d:
    dph = float(o.get("dph_total") or 0); tf = float(o.get("total_flops") or 0)
    if dph <= 0 or tf <= 0 or dph > maxdph: drop["price"] += 1; continue
    if float(o.get("gpu_ram") or 0) < minmb: drop["ram"] += 1; continue          # raw offers give gpu_ram in MB
    if float(o.get("compute_cap") or 0) < mincc: drop["cc"] += 1; continue        # bf16 needs compute capability 8.0
    if float(o.get("cuda_max_good") or 0) < 12.8: drop["cuda"] += 1; continue      # torch 2.11 cu128 wheel
    k = max(1.0, tfref / tf); hours = est / 60.0 * k * waves
    if hours * dph > 0.8 * cap: drop["fit"] += 1; continue                         # Director: estimate x $/h <= 0.8 x money stop
    rows.append((tf / dph, o))
rows.sort(key=lambda r: -r[0]); seen = set(); n = 0
for r, o in rows:
    if o.get("host_id") in seen: continue
    seen.add(o.get("host_id")); n += 1
    tf = float(o["total_flops"]); dph = float(o["dph_total"]); k = max(1.0, tfref / tf)
    print(o["id"], round(dph, 3), o.get("host_id"), str(o.get("gpu_name", "?")).replace(" ", "_"), round(tf, 1), int(o.get("gpu_ram") or 0), round(r, 1), round(k, 3), round(est / 60.0 * k * waves * dph, 2))
    if n == 3: break
print("offers read %d; kept %d; dropped: over $%.2f/h %d, under %d MB GPU RAM %d, compute capability under %d %d, CUDA under 12.8 %d, estimate over 0.8 x $%.2f %d"
      % (len(d), len(rows), maxdph, drop["price"], minmb, drop["ram"], mincc, drop["cc"], drop["cuda"], cap, drop["fit"]), file=sys.stderr)
EOS
)
log "$(cat "$G/offers-note.txt")"
echo "best offers (id \$/h host card TFLOPS GPU-RAM-MB TFLOPS-per-\$/h slowdown-vs-5090 estimated-\$):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer passes the card rules ($QUERY); nothing rented"; exit 0; }
ID=""; n=0; : > "$G/rentals.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH HID GPU TF RAM TFPD SLOW ESTD; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"
  log "CARD rental $n: instance $I (offer $OID, host $HID): $GPU, $TF TFLOPS, $RAM MB GPU RAM, \$$DPH/h, $TFPD TFLOPS per \$/h, slowdown vs 5090 x$SLOW, estimate \$$ESTD"
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep "${PS378:-10}"; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$PIN" scripts $A artifacts/claude-rd378u-20260926/notes_confirm.json artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md \
    handoff/kit/rd378gv handoff/kit/rd378gpc/remote/check378g.py | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  want=$(git show "$PIN:handoff/kit/rd378gv/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/rd378gv/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { log "rental $n: drive.sh on the rental ($got) does not match $PIN ($want)"; destroy "$I"; continue; }
  $SS "cd /root/r && setsid nohup bash handoff/kit/rd378gv/box/drive.sh $MINRAM_MB $RWAIT_MIN > /root/r/drive.log 2>&1 < /dev/null & echo launched" < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v e="$EST_MIN" -v r="$TF5090" -v t="$TF" -v w="$WAVES" -v rw="$RWAIT_MIN" -v su="$SETUP_MIN" 'BEGIN{x=r/t; if (x<1) x=1; printf "%d", (3*e*x*w + rw + su) * 60}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"
  log "time cap $TC s (3 x $EST_MIN min x slowdown $SLOW x $WAVES wave(s) + $RWAIT_MIN min for R + $SETUP_MIN min setup); money stop \$$CAP_STOP"; break
done <<EOF
$OFFERS
EOF
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done
  echo "END HOST-FAIL-NOTHING-LAUNCHED spent $(spent)" > "$G/END"; exit 0; }
log "drive.sh launched on $ID"
(nohup caffeinate -i bash "$G/rsend.sh" "$G" > "$G/rsend.out" 2>&1 < /dev/null &)
# watch the rental's progress until the chain has started training (setup, downloads, seals, selftests first), at most 25 min
last=""; tr=0; for w in $(seq 1 50); do sleep "${PW378:-30}"
  last=$($SS "tail -1 /root/r/W/drive-state.txt" < /dev/null 2>/dev/null)
  tr=$($SS "grep -c '^train start' /root/r/W/steps.txt" < /dev/null 2>/dev/null | tr -dc '0-9')
  [ "${tr:-0}" -ge 1 ] && break; case "$last" in *" FAILED "*|*" DONE") break;; esac; done
$SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
if [ "${tr:-0}" -ge 1 ]; then :
elif case "$last" in *" DONE") true;; *) false;; esac; then log "the chain ended before training (see steps); the guard copies back and destroys"
else
  log "STOPPED: drive.sh did not reach training (last: ${last:-none})"
  if copy_back logs || copy_back logs; then destroy "$ID" && R=START-FAIL || R=START-FAIL-DESTROY-UNCONFIRMED
  else stop_inst "$ID"; R=START-FAIL-STOPPED-NOT-DESTROYED; fi
  echo "END $R spent $(spent)" > "$G/END"; log "END $R"; exit 0
fi
(nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "training started on $ID; guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
echo "STARTED"
