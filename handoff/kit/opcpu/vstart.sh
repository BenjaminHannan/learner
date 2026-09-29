#!/bin/bash
# opcpu (Opus manager, 2026-09-29): sealed CPU-only tests on ONE vast rental, used as a many-core CPU box. Copy of handoff/kit/s3v/vstart.sh (dir-s3 kit) with
# the changes listed in DEVIATIONS.md. Run by the BASH-ONLY job handoff/queue/opus-cpu-vast-1-start.md from the pinned commit. Refuses (rents nothing) if
# a run of this kit already exists on main / builder-outbox, a start already ran, an instance labelled opus-cpu is live, credit is under $2.50, the pinned
# commit lacks a sealed file, or a Mac-only input (the qual-loop-s0/s1 source.pt and source.json) is missing or does not match its sealed sha256.
# Rents the offer with the lowest $/h per CPU core (>= 32 effective cores, any GPU, unused; at most $0.35/h; reliability >= 0.98, disk >= 40, inet_down >= 200;
# up to 3 hosts), attaches the Mac's ssh key, sends the pinned code (git archive) and the Mac-only inputs, checks their sha256 on the rental, starts
# box/drive.sh detached, waits until every job has been launched, then leaves the Mac guard running (vguard.sh: $2.50 stop, 7 h time cap; destroy only after
# a manifest-verified copy, else stop the instance, not destroy it).
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/opcpu/vcommon.sh"
echo "opcpu vast start, kit $PIN, job $JOB, $(now)"
for ref in origin/main origin/builder-outbox; do
  git cat-file -e "$ref:$A/_rental/COLLECT.txt" 2>/dev/null && { echo "DUPLICATE: $ref already has $A/_rental/COLLECT.txt (an earlier rental of this kit was collected)"; exit 0; }; done
# a retry after HOST-FAIL (no rental ever launched, every rental ended, nothing live): keep the old record beside, start fresh
if [ -e "$G/rentals.txt" ] && [ ! -s "$G/END" ] && grep -q "HOST-FAIL: no rental got as far as launching" "$G/log.txt" 2>/dev/null \
   && [ "$(awk 'NF<4' "$G/rentals.txt" | wc -l | tr -d ' ')" = 0 ] && [ -z "$(labelled)" ]; then
  mv "$G" "$G.hostfail-$(date +%s)"; echo "RETRY: the earlier start ended HOST-FAIL with every rental ended; its record is kept at $G.hostfail-*"; fi
# a retry after START-FAIL (the rental was destroyed and confirmed gone before any run started, every rental ended, nothing live): keep the old record, start fresh
if [ -e "$G/rentals.txt" ] && grep -q "^END START-FAIL spent" "$G/END" 2>/dev/null \
   && [ "$(awk 'NF<4' "$G/rentals.txt" | wc -l | tr -d ' ')" = 0 ] && [ -z "$(labelled)" ]; then
  mv "$G" "$G.startfail-$(date +%s)"; echo "RETRY: the earlier start ended START-FAIL with every rental ended; its record is kept at $G.startfail-*"; fi
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
# ---- the pinned commit must hold every sealed file the jobs read (nothing is rented before this passes)
git cat-file -e "$PIN^{commit}" 2>/dev/null || { echo "STOP: pinned commit $PIN not found; rented nothing"; exit 0; }
TREE="scripts artifacts/claude-fewex-20260927 artifacts/claude-distill-20260928 artifacts/claude-dir-ks-20260928 artifacts/claude-sweep-s2-20260929 artifacts/claude-dir-trn-20260929 artifacts/claude-dir-pond-20260928 artifacts/claude-dir-h12-stop-20260928 artifacts/claude-s1-d4-20260929 handoff/kit/opcpu/box"
for f in artifacts/claude-dir-ks-20260928/SEAL-code.sha256.txt artifacts/claude-sweep-s2-20260929/SEAL-code.sha256.txt artifacts/claude-dir-trn-20260929/SEAL-trn.sha256.txt \
         artifacts/claude-dir-pond-20260928/SEAL-code.sha256.txt artifacts/claude-dir-h12-stop-20260928/SEAL-code.sha256.txt artifacts/claude-s1-d4-20260929/SEAL-code.sha256.txt \
         artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt artifacts/claude-fewex-20260927/SHA256-RAW.txt artifacts/claude-fewex-20260927/EQ-DEV-GATE.json \
         artifacts/claude-distill-20260928/checkpoints-sha256.txt handoff/kit/opcpu/box/drive.sh handoff/kit/opcpu/box/pack.sh handoff/kit/opcpu/box/jlib.sh \
         handoff/kit/opcpu/box/job-ks.sh handoff/kit/opcpu/box/job-s2think.sh handoff/kit/opcpu/box/job-trn.sh handoff/kit/opcpu/box/job-pond.sh \
         handoff/kit/opcpu/box/job-doubt.sh handoff/kit/opcpu/box/job-s1.sh; do
  git cat-file -e "$PIN:$f" 2>/dev/null || { echo "STOP: pinned commit $PIN has no $f; rented nothing"; exit 0; }; done
# ---- the Mac-only inputs: source.pt / source.json of the qualified nets, sha256-checked the way the jobs check them
EQ=$(git show "$PIN:artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt"); RAW=$(git show "$PIN:artifacts/claude-fewex-20260927/SHA256-RAW.txt")
CKS=$(git show "$PIN:artifacts/claude-distill-20260928/checkpoints-sha256.txt")
lookup() { echo "$1" | awk -v f="$2" '$2==f {print $1}'; }          # sealed hash of a path in a sha list
FR=artifacts/claude-fewex-20260927; LIST=""; SHAS=""; NOTE=""
addf() { LIST="$LIST$1
"; SHAS="$SHAS$(shasum -a 256 "$MB/$1" | awk '{print $1}')  ${1}
"; }
for S in 0 1; do d=$FR/runs/qual-loop-s$S
  [ -f "$MB/$d/source.pt" ] && [ -f "$MB/$d/source.json" ] || { echo "STOP: Mac input missing: $MB/$d/source.pt or source.json; rented nothing"; exit 0; }
  w=$(lookup "$EQ" "$d/source.json"); h=$(shasum -a 256 "$MB/$d/source.json" | awk '{print $1}')
  [ -n "$w" ] && [ "$w" = "$h" ] || { echo "STOP: $d/source.json sha256 '$h' does not match the sealed '$w' (SHA256-EQ-RAW.txt); rented nothing"; exit 0; }
  w=$(lookup "$CKS" "qual-loop-s$S/source.pt"); h=$(shasum -a 256 "$MB/$d/source.pt" | awk '{print $1}')
  [ -n "$w" ] && [ "$w" = "$h" ] || { echo "STOP: $d/source.pt sha256 '$h' does not match the sealed '$w' (checkpoints-sha256.txt); rented nothing"; exit 0; }
  addf "$d/source.pt"; addf "$d/source.json"; done
NOTE="$NOTE
qual-loop s0 s1: source.json matches SHA256-EQ-RAW.txt, source.pt matches checkpoints-sha256.txt (required inputs, sent)"
# optional group 1: the plain qualified sources (s1-plain); json checked against SHA256-EQ-RAW.txt, the source.pt has no sealed hash (its sha256 is recorded)
PLAIN=1; SAVE_L=$LIST; SAVE_S=$SHAS
for S in 0 1; do d=$FR/runs/qual-plain-s$S
  [ -f "$MB/$d/source.pt" ] && [ -f "$MB/$d/source.json" ] || { PLAIN=0; NOTE="$NOTE
qual-plain s$S: missing on the Mac ($d): s1-plain will be SKIPPED"; break; }
  w=$(lookup "$EQ" "$d/source.json"); h=$(shasum -a 256 "$MB/$d/source.json" | awk '{print $1}')
  [ -n "$w" ] && [ "$w" = "$h" ] || { PLAIN=0; NOTE="$NOTE
qual-plain s$S: source.json sha256 does not match SHA256-EQ-RAW.txt: s1-plain will be SKIPPED"; break; }
  addf "$d/source.pt"; addf "$d/source.json"; done
[ $PLAIN = 1 ] && NOTE="$NOTE
qual-plain s0 s1: source.json matches SHA256-EQ-RAW.txt; source.pt has no sealed sha256 (recorded only) (sent)" || { LIST=$SAVE_L; SHAS=$SAVE_S; }
# optional group 2: what trn-decode reads from the Mac (loop and plain source.pt, plain k16384); the loop k16384 is the one ks-1-lead0 rebuilds on the rental
TRN=1; SAVE_L=$LIST; SAVE_S=$SHAS
for S in 0 1; do
  for AR in loop plain; do d=$FR/runs/$AR-s$S
    if [ -f "$MB/$d/source.pt" ] && [ -f "$MB/$d/source.json" ]; then
      w=$(lookup "$RAW" "$d/source.json"); h=$(shasum -a 256 "$MB/$d/source.json" | awk '{print $1}')
      [ -n "$w" ] && [ "$w" = "$h" ] || { TRN=0; NOTE="$NOTE
trn: $d/source.json does not match SHA256-RAW.txt: trn-decode will be SKIPPED"; break 2; }
      addf "$d/source.pt"
    else TRN=0; NOTE="$NOTE
trn: $d/source.pt or source.json missing on the Mac: trn-decode will be SKIPPED"; break 2; fi; done
  d=$FR/eq-runs/plain-s$S-pre/k16384.pt
  [ -f "$MB/$d" ] || { TRN=0; NOTE="$NOTE
trn: $d missing on the Mac: trn-decode will be SKIPPED"; break; }
  addf "$d"; done
[ $TRN = 1 ] && NOTE="$NOTE
trn: loop/plain source.pt (json checked against SHA256-RAW.txt) and plain k16384 (no sealed sha256, recorded only) (sent)" || { LIST=$SAVE_L; SHAS=$SAVE_S; }
mkdir -p "$G"; cp "$KD/handoff/kit/opcpu/vcommon.sh" "$KD/handoff/kit/opcpu/vguard.sh" "$G/"
printf '%s' "$LIST" > "$G/inputs.list"; printf '%s' "$SHAS" > "$G/INPUTS.sha256"
{ echo "Mac-only inputs sent to the rental (paths relative to the Mac checkout $MB), $(now):"; echo "$NOTE"; echo; cat "$G/INPUTS.sha256"; } > "$G/INPUTS.txt"
log "inputs: $(wc -l < "$G/inputs.list" | tr -d ' ') files; plain=$PLAIN trn=$TRN"
CR=$($VAST show user --raw 2>/dev/null | grep -oE '"credit": *-?[0-9.]+' | grep -oE -- '-?[0-9.]+$' | head -1)
log "credit \$${CR:-?}"
over "${CR:-0}" "$CREDIT_FLOOR" || { log "STOP: credit \$${CR:-?} is under the \$$CREDIT_FLOOR floor; nothing rented"; exit 0; }
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
ex=set("'"$EXCLUDE_HOSTS"'".split())
ok=[o for o in d if str(o.get("host_id")) not in ex and o.get("dph_total") and o.get("cpu_cores_effective") and float(o["dph_total"]) <= '"$MAXDPH"' and float(o["cpu_cores_effective"]) >= '"$MINCORES"']
ok=[o for o in ok if '"$BASE_H"' * float(o["dph_total"]) <= '"$FIT"' * '"$CAP_STOP"']
ok.sort(key=lambda o: float(o["dph_total"]) / float(o["cpu_cores_effective"]))
seen=set()
for o in ok:
    if o.get("host_id") in seen: continue
    seen.add(o.get("host_id"))
    print(o["id"], round(o["dph_total"],3), int(float(o["cpu_cores_effective"])), o.get("host_id"), str(o.get("gpu_name","?")).replace(" ","_"), round(1000*float(o["dph_total"])/float(o["cpu_cores_effective"]),2), '"$BASE_H"')' | head -3)
echo "offers, lowest \$/h per CPU core first (id \$/h cores host gpu milli-\$/h-per-core est_hours):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer at or under \$$MAXDPH/h with >= $MINCORES cores matches ($QUERY); nothing rented"; exit 0; }
ID=""; n=0; : > "$G/rentals.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH CORES HID GPU MPC EST; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"; log "rental $n: instance $I (offer $OID, host $HID, gpu $GPU unused, $CORES cores, \$$DPH/h, $MPC milli-\$/h per core)"
  # running, then attach the Mac's ssh key (~/.ssh/id_ed25519.pub; re-sent every 80 s) until ssh answers
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  # the pinned code (git archive of the pinned commit), then every box file's sha256 against the pinned commit
  git archive "$PIN" $TREE | $SS "mkdir -p $BR/r && tar -x -C $BR/r" 2>> "$G/log.txt"
  bad=0
  for f in $(git ls-tree -r --name-only "$PIN" handoff/kit/opcpu/box); do
    want=$(git show "$PIN:$f" | shasum -a 256 | awk '{print $1}')
    got=$($SS "sha256sum $BR/r/$f" < /dev/null 2>/dev/null | awk '{print $1}')
    [ "$want" = "$got" ] || { log "rental $n: $f on the rental ($got) does not match $PIN ($want)"; bad=1; }; done
  [ $bad = 0 ] || { destroy "$I"; continue; }
  # the Mac-only inputs (hash list checked again on the rental by drive.sh before anything runs)
  ( cd "$MB" && tar -cf - $(cat "$G/inputs.list") ) | $SS "mkdir -p $BR/in && tar -x -C $BR/in" 2>> "$G/log.txt"
  $SS "cat > $BR/in/INPUTS.sha256" < "$G/INPUTS.sha256" 2>> "$G/log.txt"; $SS "cat > $BR/in/INPUTS.txt" < "$G/INPUTS.txt" 2>> "$G/log.txt"
  [ $PLAIN = 1 ] && $SS "touch $BR/in/QUAL-PLAIN-OK" < /dev/null 2>> "$G/log.txt"
  [ $TRN = 1 ] && $SS "touch $BR/in/TRN-OK" < /dev/null 2>> "$G/log.txt"
  $SS "cd $BR/in && sha256sum -c INPUTS.sha256 > /dev/null 2>&1 && echo inputs-ok" < /dev/null 2>/dev/null | grep -q inputs-ok || { log "rental $n: the inputs on the rental do not match the Mac's list"; destroy "$I"; continue; }
  $SS "cd $BR/r && { setsid nohup bash handoff/kit/opcpu/box/drive.sh > $BR/drive.log 2>&1 < /dev/null & } ; echo launched" < /dev/null 2>> "$G/log.txt"
  ID=$I; echo "$I $H $P $TIME_CAP" > "$G/state"; log "estimate $EST h; time cap $TIME_CAP s (7 h); money stop \$$CAP_STOP"; break
done <<EOT
$OFFERS
EOT
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; exit 0; }
log "drive.sh launched on $ID"
# watch the rental's own progress file until every job has been launched (pip + inputs check first), at most 15 min
last=""; for w in $(seq 1 30); do sleep 30
  last=$($SS "grep -E ' (FAILED |LAUNCHED-ALL)' $BR/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"LAUNCHED-ALL"*) break;; esac; done
$SS "cat $BR/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
case "$last" in
  *"LAUNCHED-ALL"*) ;;
  *) log "STOPPED: drive.sh did not launch the jobs (last: ${last:-none})"
     if copy_back logs || copy_back logs; then destroy "$ID" && R=START-FAIL || R=START-FAIL-DESTROY-UNCONFIRMED
     else stop_inst "$ID"; R=START-FAIL-STOPPED-NOT-DESTROYED; fi
     echo "END $R spent $(spent)" > "$G/END"; log "END $R"; exit 0;;
esac
(nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "all jobs launched on $ID; guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
echo "STARTED"
