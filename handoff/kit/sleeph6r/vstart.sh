#!/bin/bash
# dir-h6 (sleep length, arm B) on ONE vast rental: start. Kit sleeph6r, written 2026-09-28 by helper H7 from the sleep358n3r pattern.
# Run by a BASH-ONLY queue job (handoff/queue/h7-dirh6-1-start.md) only after the Director releases it. It refuses (renting nothing) unless:
#   - the pinned commit is on main and holds the sealed h6 files (3 of 3 match SEAL-code) and slp-358n3's sealed files (18 of 18);
#   - 358u's 4 loop checkpoints (the base slp-358n3 used) are sealed on main and the Mac copies in ~/premonition-models/rsn358u match;
#   - no earlier verdict/rental exists, no instance labelled claude-dir-h6-sleeplen is live, the credit is at least the $4 cap.
# Then: rent the single-GPU offer with the best TFLOPS per $/h that fits (offers.py), attach the Mac's ssh key, and AS SOON AS ssh
# answers write $G/state and start the Mac guard (before any long remote call), then upload the pinned code and the 4 checkpoints
# (every long call bounded), check them 4 of 4, and start box/drive.sh with the braces launch. Finally wait until the first seed
# run has launched. The guard, not this script, ends the rental (halt, verified copy-back, destroy by exact id).
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/sleeph6r/vcommon.sh"
echo "dir-h6 vast start (kit sleeph6r), kit $PIN, job $JOB, $(now)"
# ---- $0 checks: nothing below costs money until "rental 1" ----
for p in scripts/claude_dir_h6_sleeplen.py scripts/claude_slp358n3_nights.py $A/DESIGN.md $A/PASSMARKS.md $A/SEAL-code.sha256.txt \
         $N3A/SEAL-code.sha256.txt $N3A/PASSMARKS.md $N3A/run-vast/sizes.json handoff/kit/sleeph6r/box/drive.sh handoff/kit/sleeph6r/box/halt.sh; do
  git cat-file -e "$PIN:$p" 2>/dev/null || { echo "STOP: $p is not in $PIN; rented nothing"; exit 0; }; done
git merge-base --is-ancestor "$PIN" origin/main 2>/dev/null || { echo "STOP: $PIN is not on origin/main; rented nothing"; exit 0; }
K2=$(mktemp -d); git archive "$PIN" scripts $A $N3A artifacts/claude-rsn358i-20260926/tests | tar -x -C "$K2"
n6=$(cd "$K2" && shasum -a 256 -c "$A/SEAL-code.sha256.txt" 2>/dev/null | grep -c ': OK$'); n3=$(cd "$K2" && shasum -a 256 -c "$N3A/SEAL-code.sha256.txt" 2>/dev/null | grep -c ': OK$')
rm -rf "$K2"
[ "$n6" = 3 ] && [ "$n3" = 18 ] || { echo "STOP: the pinned files match dir-h6's SEAL-code $n6 of 3 and slp-358n3's SEAL-code $n3 of 18; rented nothing"; exit 0; }
echo "pinned commit: dir-h6 SEAL-code 3 of 3, slp-358n3 SEAL-code 18 of 18 match"
for ref in origin/main origin/builder-outbox; do
  for p in $A/RESULTS.md $A/runs $A/run-vast; do
    git cat-file -e "$ref:$p" 2>/dev/null && { echo "DUPLICATE: $ref already has $p (a verdict or an earlier rental exists)"; exit 0; }; done; done
# the inputs: 358u's 4 loop checkpoints, sealed on main, with matching Mac copies (weights never go to git)
git cat-file -e "origin/main:$SRU" 2>/dev/null || { echo "WAITING: $SRU is not on main; rented nothing"; exit 0; }
CKS=""; for S in 13 14 15 16; do
  sha=$(git show "origin/main:$SRU" | awk -v f="loop-s$S/final.pt" '$2==f {print $1}')
  m=$(shasum -a 256 "$MPU/loop-s$S/final.pt" 2>/dev/null | awk '{print $1}')
  [ -n "$sha" ] && [ "$m" = "$sha" ] || { echo "WAITING: loop-s$S/final.pt sealed '${sha:-none}', Mac copy '${m:-missing}'; rented nothing"; exit 0; }
  CKS="$CKS$sha  ck/s$S/final.pt
"; done
echo "inputs: 358u loop-s13..16/final.pt sealed on main and matching on the Mac"
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already ran)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" 4 || { log "STOP: credit \$${CR:-?} is under the \$4 cap; nothing rented"; exit 0; }
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYM "$KD/handoff/kit/sleeph6r/offers.py" $MAXDPH $MINRAM_GB $RUNS $RUN_GB $FREE_GB $BASE_H $TF5090 $FIT $CAP_STOP $MINCPU 2>> "$G/log.txt")
echo "offers, best TFLOPS per \$/h first (id \$/h cores host gpu TFLOPS GB waves est_hours):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { log "STOP: no offer at or under \$$MAXDPH/h with >= $MINRAM_GB GB that fits ($QUERY); nothing rented"; exit 0; }
# ---- from here money can be spent ----
PRE_ID=""; GUARD_UP=0
# if this job is killed (BASH-ONLY alarm) after a rental exists but before its guard runs, nothing is on the rental worth saving: destroy it
cleanup() { [ -n "$PRE_ID" ] && [ "$GUARD_UP" = 0 ] && { log "start ended before the guard was running: destroying $PRE_ID (nothing on it to save)"; destroy "$PRE_ID"; }; }
trap cleanup EXIT
trap 'exit 143' TERM HUP INT
guard_start() {
  rm -f "$G/END" "$G/guard.pid"
  cp "$KD/handoff/kit/sleeph6r/vcommon.sh" "$KD/handoff/kit/sleeph6r/vguard.sh" "$G/"
  (nohup caffeinate -i bash "$G/vguard.sh" "$G" >> "$G/guard.out" 2>&1 < /dev/null &)
  for w in 1 2 3 4 5 6 7 8 9 10; do [ -s "$G/guard.pid" ] && break; sleep 1; done
  [ -s "$G/guard.pid" ]
}
guard_stop() {   # by the exact pid the guard wrote itself, and only if that pid still is a vguard.sh
  [ -s "$G/guard.pid" ] || return 0
  gp=$(cat "$G/guard.pid")
  case "$(ps -p "$gp" -o command= 2>/dev/null)" in *vguard.sh*) kill "$gp" 2>/dev/null
    for w in 1 2 3 4 5; do kill -0 "$gp" 2>/dev/null || break; sleep 1; done; kill -0 "$gp" 2>/dev/null && kill -9 "$gp" 2>/dev/null;; esac
  rm -f "$G/guard.pid"
}
bail() { log "rental $n: $1"; guard_stop; GUARD_UP=0; destroy "$I"; PRE_ID=""; }
up_code() { git archive "$PIN" scripts $A $N3A artifacts/claude-rsn358i-20260926/tests handoff/kit/sleeph6r/box | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"; }
up_ck() { for S in 13 14 15 16; do $SS "mkdir -p /root/r/ck/s$S && cat > /root/r/ck/s$S/final.pt" < "$MPU/loop-s$S/final.pt" 2>> "$G/log.txt" || return 1; done; }
ID=""; n=0; : > "$G/rentals.txt"   # from here on a rerun of this start is refused (DUPLICATE)
while read -r OID DPH CORES HID GPU TF RAM WV EST <&3; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"; PRE_ID=$I
  log "rental $n: instance $I (offer $OID, host $HID, $GPU, $TF TFLOPS, $RAM GB, $CORES cores, \$$DPH/h, $(awk -v t="$TF" -v d="$DPH" 'BEGIN{printf "%.0f", t/d}') TFLOPS per \$/h)"
  # running, then attach the Mac's ssh key (~/.ssh/id_ed25519.pub; re-sent every 80 s) until ssh answers
  ok=""; s=""; att=0; H=x; P=x
  for w in $(seq 1 $SSH_WAIT); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$(bounded 40 $SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { bail "no ssh within $((SSH_WAIT / 6)) min (status ${s:-?})"; continue; }
  # the guard's state is written and the guard is running BEFORE any long remote call (358u lost its guard to a hung call)
  TC=$(awk -v e="$EST" 'BEGIN{printf "%d", e*1.5*3600}')
  echo "$I $H $P $TC" > "$G/state"
  guard_start || { bail "the guard did not start"; continue; }
  GUARD_UP=1; log "guard started (pid $(cat "$G/guard.pid")) on $I before any upload; estimate $EST h ($WV waves at $RAM GB; 5090 $TF5090 / $GPU $TF TFLOPS, never below 1x); time cap $TC s (1.5x); money stop \$$CAP_STOP"
  bounded $UPLOAD_MAX up_code < /dev/null || { bail "code upload failed or took over $UPLOAD_MAX s"; continue; }
  bounded $UPLOAD_MAX up_ck < /dev/null || { bail "checkpoint upload failed or took over $UPLOAD_MAX s"; continue; }
  printf '%s' "$CKS" | bounded 120 $SS "cat > /root/r/ck/expected.sha256" 2>> "$G/log.txt"
  nck=$(bounded 300 $SS "cd /root/r && sha256sum -c ck/expected.sha256 2>/dev/null | grep -c ': OK\$'" < /dev/null 2>/dev/null)
  [ "$nck" = 4 ] || { bail "checkpoint upload check ${nck:-none}/4"; continue; }
  want=$(git show "$PIN:handoff/kit/sleeph6r/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$(bounded 60 $SS "sha256sum /root/r/handoff/kit/sleeph6r/box/drive.sh" < /dev/null 2>/dev/null | awk '{print $1}')
  [ "$want" = "$got" ] || { bail "drive.sh on the rental (${got:-none}) does not match $PIN ($want)"; continue; }
  la=$(bounded 60 $SS "$LAUNCH_CMD" < /dev/null 2>> "$G/log.txt"); log "launch call answered '${la:-nothing}'"
  st=""; for w in 1 2 3 4 5 6; do st=$(bounded 30 $SS 'head -1 /root/r/W/drive-state.txt' < /dev/null 2>/dev/null); case "$st" in *" START") break;; esac; sleep 10; done
  case "$st" in *" START") ;; *) bail "drive.sh did not start (progress file: ${st:-none})"; continue;; esac
  ID=$I; PRE_ID=""; log "drive.sh launched on $ID"; break
done 3<<EOF
$OFFERS
EOF
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; exit 0; }
# watch the rental's own progress file until the first seed run has launched (pip + seals + checks + smoke first), at most 20 min
last=""; for w in $(seq 1 40); do sleep 30
  [ -s "$G/END" ] && break
  last=$(bounded 40 $SS "grep -E ' (FAILED |LAUNCH s13 )' /root/r/W/drive-state.txt | tail -1" < /dev/null 2>/dev/null)
  case "$last" in *"FAILED "*|*"LAUNCH s13 "*) break;; esac; done
bounded 40 $SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
case "$last" in
  *"LAUNCH s13 "*) ;;
  *"FAILED "*) log "STOPPED: drive.sh failed before the first run ($last); the guard halts, copies back and destroys"
     for w in $(seq 1 60); do [ -s "$G/END" ] && break; sleep 15; done
     echo "START-FAIL: $(cat "$G/END" 2>/dev/null || echo 'the guard is still finishing; see the collect job')"; exit 0;;
  *) [ -s "$G/END" ] && { echo "START-FAIL: the guard ended the rental: $(cat "$G/END")"; exit 0; }
     log "NO-LAUNCH-YET: drive.sh has not launched the first run after 20 min; the guard keeps watching and stops it $((PRE_MAX / 60)) min after ssh answered"
     echo "STARTED-NO-LAUNCH-YET"; exit 0;;
esac
log "first seed run launched on $ID (the rest start one by one while 5 GB of GPU memory is free); guard running (pid $(cat "$G/guard.pid" 2>/dev/null)); spent so far \$$(spent)"
echo "STARTED"
