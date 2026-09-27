#!/bin/bash
# 0.2d-G checks: Ben's Mac side of the ONE rental job (design/v3/30-modes/02d-gates-ADDENDUM-52.md). Run by the
# BASH-ONLY queue job handoff/queue/rent-e2e02dg-1.md from a git-archive tree of the pinned commit, because G's adapter is
# only on this Mac. bash 3.2 safe. Card rules and helpers follow handoff/kit/rd378gv (rd-378g's rental kit, which ran G
# on an RTX 5090). The vast key is never read here: the vastai CLI reads its own config.
#   1 guards: no earlier run, the vastai CLI, G's adapter present and matching SEAL-run, credit over the money stop
#   2 card: an RTX 5090 first (rd-378g's card: the merge and the notes are most likely to repeat bit for bit on it),
#     cheapest first, at most 3 hosts; any card with >= 16 GB and compute capability >= 8.0 only if no 5090 is offered
#   3 rent, attach the Mac's public key, wait for ssh (8 min, else destroy: nothing has run on it)
#   4 send the pinned code (with design/v3/60-listener: claude_lis300_compiler reads relation-names.txt; attempt 2
#     stopped at the selftests without it) and a copy of G's adapter (the Mac folder is only read, never moved or changed)
#   5 start kit/box.sh detached; a detached watchdog stops (never destroys) the instance at the time cap if this job
#     has not ended it by then
#   6 wait for /root/r/FINISHED (at most TCAP_MIN minutes)
#   7 copy W/ back and check every file against the rental's MANIFEST.sha256: destroy only when that passes, else stop
#   8 the files land in $W/artifacts/claude-e2e02dg-20260927/vast/ (the queue job's PUSH path; no weights in W/)
# Usage: mac.sh <code-tree> <pinned-commit> <mac-worktree> [results-folder] [hosts-to-skip] [spent-before]
set -u
export COPYFILE_DISABLE=1
KD=$1; PIN=$2; W=$3
E=artifacts/claude-e2e02dg-20260927
RUN=${4:-vast}                  # attempt's results folder: vast (rent-e2e02dg-1), vast2 (rent-e2e02dg-2), ...
OUT=$W/$E/$RUN
LABEL=claude-e2e02dg
H=${H02DG:-$HOME/premonition-watch/e2e02dg}; [ "$RUN" = vast ] || H=$H-$RUN   # Mac-only state (rentals, log); never pushed
SKIPHOSTS=${5:-}                # hosts not to rent again (comma-separated), e.g. one whose network failed an earlier attempt
SPENT_BEFORE=${6:-0}            # dollars spent by earlier attempts of this rental job (all attempts share Ben's $4 cap)
ADP=${ADP02DG:-$HOME/premonition-models/rd378g-vast-adapter}  # G's adapter (read only)
VAST=${VAST02DG:-vastai}
KEY=${KEY02DG:-$HOME/.ssh/id_ed25519}
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM02DG:-$("$U" python find 3.12 2>/dev/null)}
PYJ="$PYM -c"
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; box.sh pins torch 2.11.0+cu128 inside it
CAP_STOP=$(awk -v b="$SPENT_BEFORE" 'BEGIN{c=2.00; if (4.00-b < c) c=4.00-b; printf "%.2f", c}')   # this attempt: $2, and never past $4 with earlier attempts
MAXDPH=0.80        # dollars per hour, a sanity bound
TCAP_MIN=55        # box.sh must finish within this many minutes of its launch (rd-378g setup took 16 min)
Q5090="gpu_name=RTX_5090 num_gpus=1 compute_cap>=800 cuda_max_good>=12.8 reliability>=0.98 cpu_cores_effective>=8 disk_space>=40 inet_down>=200 direct_port_count>=1 rentable=true"
QANY="num_gpus=1 gpu_ram>=16 compute_cap>=800 cuda_max_good>=12.8 reliability>=0.98 cpu_cores_effective>=8 disk_space>=40 inet_down>=200 direct_port_count>=1 rentable=true"
ADPSHA=b1c69db46666e6dc68f41de760f6541a9174c4fbb92a26040b0edb208b064998
now() { date -u +%FT%TZ; }
log() { mkdir -p "$H"; echo "$(now) $*" | tee -a "$H/log.txt"; }
spent() { awk -v n="$(date +%s)" '{e=(NF>=4)?$4:n; s+=$2*(e-$3)/3600} END{printf "%.2f", s+0}' "$H/rentals.txt" 2>/dev/null; }
over() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a+0>=b+0)}'; }
insts() { $VAST show instances --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("instances",d) if isinstance(d,dict) else d
for i in d: print(i.get("id"), i.get("label"), i.get("actual_status") or "starting", i.get("ssh_host"), i.get("ssh_port"))'; }
labelled() { insts | awk -v l="$LABEL" '$2==l {printf "%s ", $1}'; }
status_of() { x=$(insts) || { echo ""; return; }; [ -z "$x" ] && { $VAST show instances --raw < /dev/null > /dev/null 2>&1 && echo gone || echo ""; return; }
              echo "$x" | awk -v id="$1" 'BEGIN{s="gone"} $1==id {s=$3} END{print s}'; }
hostport_of() { insts | awk -v id="$1" '$1==id {print $4, $5}'; }
mark_end() { awk -v id="$1" -v t="$(date +%s)" '$1==id && NF==3 {$0=$0" "t} {print}' "$H/rentals.txt" > "$H/rentals.tmp" && mv "$H/rentals.tmp" "$H/rentals.txt"; }
mine() { grep -q "^$1 " "$H/rentals.txt" || { log "REFUSED $2 $1: not created by this job"; return 1; }; }
destroy() {
  mine "$1" destroy || return 1
  for try in 1 2 3; do
    echo y | $VAST destroy instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep 10; [ "$(status_of "$1")" = gone ] && { mark_end "$1"; log "DESTROYED $1 (confirmed gone), spent \$$(spent)"; return 0; }; done
  done
  log "DESTROY-UNCONFIRMED $1"; return 1
}
stop_inst() {
  mine "$1" stop || return 1
  for try in 1 2 3; do
    echo y | $VAST stop instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep 10; s=$(status_of "$1"); case "$s" in exited|stopped|gone) mark_end "$1"; log "STOPPED $1 (status $s; not destroyed, files kept on its disk), spent \$$(spent)"; return 0;; esac; done
  done
  log "STOP-UNCONFIRMED $1: status $(status_of "$1")"; return 1
}
sshto() { echo "ssh -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
offers() {   # $1 = query; prints: id $/h host card TFLOPS GPU-RAM-MB (cheapest first, one per host, at most 3)
  $VAST search offers "$1" -o dph --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
maxdph=float(sys.argv[1])
try:
    d=json.load(sys.stdin); d=d.get("offers",d) if isinstance(d,dict) else d
except Exception:
    d=[]
seen=set(); n=0
for o in sorted(d, key=lambda o: float(o.get("dph_total") or 99)):
    dph=float(o.get("dph_total") or 0)
    if dph<=0 or dph>maxdph or float(o.get("gpu_ram") or 0)<16000 or float(o.get("compute_cap") or 0)<800 or o.get("host_id") in seen: continue
    if str(o.get("host_id")) in sys.argv[2].split(","): continue
    seen.add(o.get("host_id")); n+=1
    print(o["id"], round(dph,3), o.get("host_id"), str(o.get("gpu_name","?")).replace(" ","_"), round(float(o.get("total_flops") or 0),1), int(o.get("gpu_ram") or 0))
    if n==3: break' "$MAXDPH" "$SKIPHOSTS"; }

echo "0.2d-G rental job (ADDENDUM-52), pin $PIN, results $E/$RUN, skip hosts '${SKIPHOSTS}', spent before \$$SPENT_BEFORE, money stop \$$CAP_STOP, $(now)"
for ref in origin/main origin/builder-outbox; do
  git -C "$W" cat-file -e "$ref:$E/$RUN/MANIFEST.sha256" 2>/dev/null && { echo "DUPLICATE: $ref already has $E/$RUN"; exit 0; }; done
[ -e "$H/rentals.txt" ] && { echo "DUPLICATE: $H/rentals.txt exists (a start already ran)"; tail -5 "$H/log.txt" 2>/dev/null; exit 0; }
command -v "$VAST" > /dev/null || { echo "STOP: no vastai CLI; rented nothing"; exit 0; }
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv; rented nothing"; exit 0; }
[ -f "$KEY.pub" ] || { echo "STOP: no $KEY.pub to attach; rented nothing"; exit 0; }
for f in README.md adapter_config.json adapter_model.safetensors chat_template.jinja tokenizer.json tokenizer_config.json; do
  [ -f "$ADP/$f" ] || { echo "STOP: $ADP/$f missing; rented nothing"; exit 0; }; done
got=$(shasum -a 256 "$ADP/adapter_model.safetensors" | cut -c1-64)
[ "$got" = "$ADPSHA" ] || { echo "STOP: G's adapter_model.safetensors on the Mac is $got, not $ADPSHA; rented nothing"; exit 0; }
L=$(labelled); [ -n "$L" ] && { echo "DUPLICATE: live instance(s) labelled $LABEL: $L"; exit 0; }
mkdir -p "$H"
log "G's adapter on the Mac: $ADP, adapter_model.safetensors sha256 matches SEAL-run"
CR=$($VAST show user --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys; print(round(float(json.load(sys.stdin).get("credit",0)),2))')
log "credit \$${CR:-?}"
over "${CR:-0}" "$CAP_STOP" || { log "STOP: credit \$${CR:-?} is under the \$$CAP_STOP money stop; nothing rented"; exit 0; }
OF=$(offers "$Q5090"); KIND=5090
[ -n "$OF" ] || { OF=$(offers "$QANY"); KIND=any; }
echo "offers ($KIND; id \$/h host card TFLOPS GPU-RAM-MB):"; echo "$OF"
[ -n "$OF" ] || { log "STOP: no offer passes the card rules; nothing rented"; exit 0; }
: > "$H/rentals.txt"          # from here on a rerun of this job is refused (DUPLICATE)
ID=""; SS=""; n=0
while read -r OID DPH HID GPU TF RAM; do
  n=$((n+1)); over "$(spent)" "$CAP_STOP" && break
  out=$($VAST create instance "$OID" --image "$IMAGE" --disk 40 --label "$LABEL" --ssh --direct --raw < /dev/null 2>&1)
  I=$(echo "$out" | $PYJ 'import json,sys; print(json.load(sys.stdin).get("new_contract") or "")' 2>/dev/null)
  [ -n "$I" ] || { log "rental $n: create on offer $OID failed: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; continue; }
  echo "$I $DPH $(date +%s)" >> "$H/rentals.txt"
  log "CARD rental $n: instance $I (offer $OID, host $HID): $GPU, $TF TFLOPS, $RAM MB GPU RAM, \$$DPH/h ($KIND)"
  ok=""; s=""; att=0
  for w in $(seq 1 48); do
    s=$(status_of "$I")
    if [ "$s" = running ]; then set -- $(hostport_of "$I") x x; HO=$1; PO=$2
      if [ "$HO" != x ] && [ "$HO" != None ]; then
        [ $((att % 8)) = 0 ] && $VAST attach ssh "$I" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
        SS=$(sshto "$HO" "$PO"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
    sleep 10; done
  [ "$ok" = ssh-ok ] || { log "rental $n: no ssh within 8 min (status ${s:-?}); nothing ran on it"; destroy "$I"; continue; }
  tar -C "$KD" -cf - scripts design/v3/30-modes/02d-gates-ADDENDUM-52.md design/v3/60-listener $E \
      artifacts/claude-rd378g-20260926/PASSMARKS.md artifacts/claude-rd378g-20260926/SEAL.sha256.txt \
      artifacts/claude-rd378g-20260926/g5/dialogs.jsonl artifacts/claude-rd378g-20260926/vast/SEAL-run.sha256.txt \
      artifacts/claude-rd378g-20260926/vast/g5/notes_G.jsonl | $SS "mkdir -p /root/r && tar -x -C /root/r" 2>> "$H/log.txt"
  tar -C "$ADP" -cf - README.md adapter_config.json adapter_model.safetensors chat_template.jinja tokenizer.json tokenizer_config.json \
      | $SS "mkdir -p /root/r/adapter && tar -x -C /root/r/adapter" 2>> "$H/log.txt"
  want=$(shasum -a 256 "$KD/$E/kit/box.sh" | cut -c1-64)
  gotb=$($SS "sha256sum /root/r/$E/kit/box.sh" < /dev/null 2>/dev/null | cut -c1-64)
  gota=$($SS "sha256sum /root/r/adapter/adapter_model.safetensors" < /dev/null 2>/dev/null | cut -c1-64)
  [ "$want" = "$gotb" ] && [ "$gota" = "$ADPSHA" ] || { log "rental $n: code or adapter did not arrive intact (box $gotb vs $want; adapter $gota)"; destroy "$I"; continue; }
  $SS "cd /root/r && { setsid nohup bash $E/kit/box.sh 16000 > /root/r/box.log 2>&1 < /dev/null & } ; echo launched" < /dev/null 2>> "$H/log.txt"
  ID=$I; echo "$I $HO $PO $(date +%s)" > "$H/state"; break
done <<EOF
$OF
EOF
[ -n "$ID" ] || { log "HOST-FAIL: no rental got as far as launching; spent \$$(spent)"; echo "END HOST-FAIL spent $(spent)" > "$H/END"; echo "END HOST-FAIL"; exit 0; }
log "box.sh launched on $ID; time cap $TCAP_MIN min; money stop \$$CAP_STOP"
# watchdog: if this job is gone (the queue's 75-min cap, a Mac restart) and the instance is not ended by the cap, stop it
cat > "$H/watchdog.sh" <<EOW
#!/bin/bash
sleep $(( (TCAP_MIN + 8) * 60 ))
[ -e "$H/END" ] && exit 0
s=\$($VAST show instances --raw < /dev/null 2>/dev/null | $PYM -c 'import json,sys
d=json.load(sys.stdin); d=d.get("instances",d) if isinstance(d,dict) else d
print(" ".join(str(i.get("actual_status")) for i in d if str(i.get("id"))=="$ID"))')
[ -z "\$s" ] && exit 0
echo y | $VAST stop instance $ID > /dev/null 2>&1
echo "\$(date -u +%FT%TZ) WATCHDOG stopped $ID (status was \$s); not destroyed" >> "$H/log.txt"
echo "END WATCHDOG-STOPPED" > "$H/END"
EOW
(nohup bash "$H/watchdog.sh" > /dev/null 2>&1 < /dev/null &)
t0=$(date +%s); last=""
while [ $(( $(date +%s) - t0 )) -lt $(( TCAP_MIN * 60 )) ]; do
  sleep 30
  over "$(spent)" "$CAP_STOP" && { log "MONEY-STOP at \$$(spent)"; break; }
  $SS "test -e /root/r/FINISHED" < /dev/null 2>/dev/null && break
  l=$($SS "tail -1 /root/r/W/state.txt" < /dev/null 2>/dev/null); [ -n "$l" ] && [ "$l" != "$last" ] && { echo "  $l" | cut -c1-220; last=$l; }
done
$SS "test -e /root/r/FINISHED" < /dev/null 2>/dev/null && FIN=yes || FIN=no
[ $FIN = no ] && $SS "cd /root/r/W && find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum > MANIFEST.sha256" < /dev/null 2>/dev/null
log "finished on the rental: $FIN; copying back W/"
rm -rf "$H/W"; mkdir -p "$H/W"
$SS "tar -C /root/r/W -cf - ." < /dev/null 2>> "$H/log.txt" | tar -x -C "$H/W"
$SS "cat /root/r/box.log" < /dev/null > "$H/W/box.log" 2>/dev/null
CHK=$( (cd "$H/W" && shasum -a 256 -c MANIFEST.sha256 2>&1) | grep -c ': OK$'); ALL=$(grep -c . "$H/W/MANIFEST.sha256" 2>/dev/null)
if [ -s "$H/W/MANIFEST.sha256" ] && [ "$CHK" = "$ALL" ]; then
  log "copy-back checked: $CHK of $ALL files match the rental's manifest"
  destroy "$ID" && R=DESTROYED || { stop_inst "$ID"; R=STOPPED-DESTROY-UNCONFIRMED; }
else
  log "copy-back NOT checked ($CHK of ${ALL:-0}); stopping, not destroying"
  stop_inst "$ID"; R=STOPPED-NOT-DESTROYED
fi
mkdir -p "$OUT"; cp -R "$H/W/." "$OUT/"
awk '{print $1, $2, $3, $4}' "$H/rentals.txt" > "$OUT/rentals.txt"
grep -v "ssh\|key" "$H/log.txt" > "$OUT/mac-log.txt"
echo "END $R finished=$FIN copyback=$CHK/$ALL spent $(spent) (earlier attempts \$$SPENT_BEFORE)" | tee "$H/END" > "$OUT/END.txt"
echo "SUMMARY $(cat "$H/END")"
tail -25 "$OUT/state.txt" 2>/dev/null
