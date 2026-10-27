#!/bin/bash
# k1f on ONE vast rental: start (Creative answers in chat thread, 2026-09-27). Built from handoff/kit/sleep358sv/vstart.sh; run
# by the BASH-ONLY job handoff/held/rent-k1fv-1-start.md only after release. Order:
#  1. refuses on a duplicate, while k1f-benspc2 is still queued or running, or while an instance labelled claude-creativechat-k1fv lives;
#  2. BEFORE any rental ($0 if it stops here): finds self122_head.pt on the Mac (sha256 5ca02173...) and copies 0.2c's
#     adapter02c.pt from BensPC over ssh (a file read; BensPC's GPU is not used), sha256 a33211dc...; if BensPC cannot be
#     reached it stops with NO-ADAPTER and rents nothing;
#  3. rents the single-GPU offer with the best TFLOPS per $/h among those that pass: >= 24000 MB GPU RAM (checked here, in
#     MB), at most $0.60/h, and the fit check (0.75 h on a 5090, scaled by 5090 TFLOPS / its TFLOPS, x $/h <= 0.8 x the
#     $1.50 money stop); up to 3 hosts; before each rental it re-checks that its own queue file is still released on main;
#  4. sends the pinned tree, self122_head.pt and the adapter (sha256 checked on the rental), starts box/drive.sh detached,
#     and leaves the Mac guard running (vguard.sh: $1.50 stop, 2 h on a 5090 scaled by TFLOPS; destroy only after a
#     manifest-verified copy, else stop the instance without destroying it). The Mac copy of the adapter is then removed.
# Usage: vstart.sh <kit-dir> <pinned-commit> <queue-job-name>
set -u
KD=$1; PIN=$2; JOB=${3:-?}
. "$KD/handoff/kit/creativechatk1fv/vcommon.sh"
echo "k1f vast start, kit $PIN, job $JOB, $(now)"
for p in $A/run $A/RESULTS-benspc.md $A/RESULTS-vast.md; do
  git cat-file -e "origin/builder-outbox:$p" 2>/dev/null && { echo "DUPLICATE: origin/builder-outbox already has $p (a k1f run exists)"; exit 0; }; done
for p in $A/run/vast $A/run/creative_F.jsonl $A/RESULTS-benspc.md $A/RESULTS-vast.md; do
  git cat-file -e "origin/main:$p" 2>/dev/null && { echo "DUPLICATE: origin/main already has $p (a k1f run exists)"; exit 0; }; done
# never beside the BensPC version of this run: refuse while k1f-benspc2 is still active on main or running on the watcher
# (when the Director releases this rental it moves handoff/queue/k1f-benspc2.md to handoff/held/superseded/)
for j in k1f-benspc2; do
  git cat-file -e "origin/main:handoff/queue/$j.md" 2>/dev/null && { echo "HELD-BY-BENSPC: handoff/queue/$j.md is still active on main; rented nothing"; exit 0; }
  [ -e "${WQK1F:-$HOME/premonition-watch/queue}/$j.running" ] && { echo "HELD-BY-BENSPC: $j is running on the watcher; rented nothing"; exit 0; }
done
[ -e "$G/rentals.txt" ] && { echo "DUPLICATE: $G/rentals.txt exists (a start already rented)"; tail -5 "$G/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$G/adapter"; cp "$KD/handoff/kit/creativechatk1fv/vcommon.sh" "$KD/handoff/kit/creativechatk1fv/vguard.sh" "$G/"
# --- before any rental: self122_head.pt (Mac) and adapter02c.pt (BensPC) ---
S122=""
for c in ${S122K1F:-} "$PWD/artifacts/fable-self122-20260922/self122_head.pt" "$HOME/Desktop/projects/beautiful-model/artifacts/fable-self122-20260922/self122_head.pt"; do
  [ -f "$c" ] && [ "$(shasum -a 256 "$c" | awk '{print $1}')" = "$S122_SHA" ] && { S122=$c; break; }; done
[ -n "$S122" ] || { log "STOP NO-SELF122: no self122_head.pt with sha256 $S122_SHA on the Mac; rented nothing"; echo "NO-SELF122"; exit 0; }
log "self122_head.pt: $S122 (sha256 ok)"
AM=$G/adapter/adapter02c.pt; rm -f "$AM"
$BSCP -q -o BatchMode=yes -o ConnectTimeout=20 "benspc:$BENSPC_AD" "$AM" < /dev/null 2>> "$G/log.txt"; brc=$?
if [ $brc != 0 ] || [ ! -s "$AM" ]; then
  $BSSH -o BatchMode=yes -o ConnectTimeout=20 benspc "echo reached" < /dev/null > /dev/null 2>&1 && why="BensPC answered ssh but the copy failed (scp rc $brc)" || why="BensPC does not answer ssh"
  rm -f "$AM"; log "STOP NO-ADAPTER: $why; 0.2c's adapter02c.pt exists only on BensPC and arms K and F need it; rented nothing, \$0"; echo "NO-ADAPTER"; exit 0; fi
as=$(shasum -a 256 "$AM" | awk '{print $1}')
[ "$as" = "$AD_SHA" ] || { rm -f "$AM"; log "STOP ADAPTER-MISMATCH: sha256 $as, want $AD_SHA; rented nothing"; echo "ADAPTER-MISMATCH"; exit 0; }
git show origin/builder-outbox:artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.json > "$G/adapter/adapter02c.json" 2>/dev/null
[ -s "$G/adapter/adapter02c.json" ] || { rm -f "$AM"; log "STOP: adapter02c.json not on origin/builder-outbox; rented nothing"; exit 0; }
log "adapter02c.pt copied from BensPC to $AM (sha256 ok, $(wc -c < "$AM" | tr -d ' ') bytes); sidecar adapter02c.json from origin/builder-outbox"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" 4 || { rm -f "$AM"; log "STOP: credit \$${CR:-?} is under the \$4 per-job cap; nothing rented"; exit 0; }
OFFERS=$($VAST search offers "$QUERY" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
ok=[]
for o in d:
    dph, tf, mb = float(o.get("dph_total") or 0), float(o.get("total_flops") or 0), float(o.get("gpu_ram") or 0)
    if dph <= 0 or tf <= 0 or dph > '"$MAXDPH"' or mb < '"$MINRAM_MB"': continue      # GPU RAM in MB, checked here
    est = '"$EST_H"' * max(1.0, '"$TF5090"' / tf)                                    # hours on this card
    if est * dph > '"$FIT"' * '"$CAP_STOP"': continue                                # fit check
    ok.append((tf / dph, o, est))
ok.sort(key=lambda x: -x[0])
seen=set()
for r, o, est in ok:
    if o.get("host_id") in seen: continue
    seen.add(o.get("host_id"))
    print(o["id"], round(float(o["dph_total"]),3), o.get("cpu_cores_effective"), o.get("host_id"), str(o.get("gpu_name","?")).replace(" ","_"), round(float(o["total_flops"]),1), int(float(o.get("gpu_ram") or 0)), round(est,2))' | head -3)
echo "offers, best TFLOPS per \$/h first (id \$/h cores host gpu TFLOPS MB est_hours):"; echo "$OFFERS"
[ -n "$OFFERS" ] || { rm -f "$AM"; log "STOP: no offer passes (>= $MINRAM_MB MB, <= \$$MAXDPH/h, fit check $EST_H h x \$/h <= $FIT x \$$CAP_STOP; $QUERY); nothing rented"; exit 0; }
ID=""; n=0
while read -r OID DPH CORES HID GPU TF MB EST; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  # RE-CHECK BEFORE EACH RENTAL (330-rent-kit): this job's file must still be released in handoff/queue/ on main
  git fetch -q origin main 2>/dev/null
  { git cat-file -e "origin/main:handoff/queue/$JOB.md" 2>/dev/null && ! git show "origin/main:handoff/queue/$JOB.md" | grep -q '^STATUS: HELD'; } || { log "RE-CHECK: handoff/queue/$JOB.md is not released on origin/main; no rental $n"; break; }
  touch "$G/rentals.txt"   # from the first create on, a rerun of this start is refused (DUPLICATE)
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 60 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$G/rentals.txt"; log "rental $n: instance $I (offer $OID, host $HID, card $GPU, $TF TFLOPS, $MB MB, $CORES cores, \$$DPH/h, $(awk -v t="$TF" -v d="$DPH" 'BEGIN{printf "%.0f", t/d}') TFLOPS per \$/h, estimate $EST h = \$$(awk -v e="$EST" -v d="$DPH" 'BEGIN{printf "%.2f", e*d}'))"
  # running, then attach the Mac's ssh key (re-sent every 80 s, as rent-rv390b does) until ssh answers
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; H=$1; P=$2
      if [ "$H" != x ] && [ "$H" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?})"; destroy "$I"; continue; }
  git archive "$PIN" $TREE | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$G/log.txt"
  $SS "mkdir -p /root/r/artifacts/fable-self122-20260922 && cat > /root/r/artifacts/fable-self122-20260922/self122_head.pt" < "$S122" 2>> "$G/log.txt"
  $SS "mkdir -p /root/adapter && cat > /root/adapter/adapter02c.pt" < "$AM" 2>> "$G/log.txt"
  $SS "cat > /root/adapter/adapter02c.json" < "$G/adapter/adapter02c.json" 2>> "$G/log.txt"
  want=$(git show "$PIN:handoff/kit/creativechatk1fv/box/drive.sh" | shasum -a 256 | awk '{print $1}')
  got=$($SS "sha256sum /root/r/handoff/kit/creativechatk1fv/box/drive.sh /root/adapter/adapter02c.pt /root/r/artifacts/fable-self122-20260922/self122_head.pt" < /dev/null 2>/dev/null | awk '{printf "%s ", $1}')
  [ "$got" = "$want $AD_SHA $S122_SHA " ] || { log "rental $n: files on the rental do not match (got: $got)"; destroy "$I"; continue; }
  $SS "cd /root/r && { setsid nohup bash handoff/kit/creativechatk1fv/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & } ; echo launched"   # braced: only drive.sh goes to the background, so ssh returns at once (358u lost its guard to the unbraced form) < /dev/null 2>> "$G/log.txt"
  TC=$(awk -v b="$BASE_TIME" -v r="$TF5090" -v t="$TF" 'BEGIN{x=r/t; if (x<1) x=1; printf "%d", b*x}')
  ID=$I; echo "$I $H $P $TC" > "$G/state"; log "card $GPU, $TF TFLOPS, \$$DPH/h; time cap $TC s (5090 $TF5090 / $TF TFLOPS, never below 1x); money stop \$$CAP_STOP"; break
done <<EOF
$OFFERS
EOF
rm -f "$AM"; [ ! -e "$AM" ] && log "removed the Mac copy $AM"
[ -n "$ID" ] || [ -s "$G/rentals.txt" ] || { rm -f "$G/rentals.txt"; log "STOP: no instance was created (see the lines above); nothing rented, \$0"; exit 0; }
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; for i in $(labelled); do grep -q "^$i " "$G/rentals.txt" && destroy "$i"; done; echo "END HOST-FAIL spent $(spent)" > "$G/END"; exit 0; }
log "drive.sh launched on $ID"
# the guard is the only thing that ends the rental from here on (DONE, FAILED, money, time, stall, lost host)
(nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &)
sleep 5; log "guard started ($(pgrep -f "vguard.sh $G" | tr '\n' ' ')); spent so far \$$(spent)"
# for the record only: the rental's progress after about 5 min (the guard handles any FAILED line)
sleep 300; $SS "cat /root/r/W/drive-state.txt" < /dev/null 2>/dev/null | tee -a "$G/log.txt"
echo "STARTED"
