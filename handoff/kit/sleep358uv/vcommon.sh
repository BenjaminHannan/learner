# rsn-358u vast kit, shared Mac-side helpers (sleep research thread, 2026-09-27). Sourced by vstart.sh, vguard.sh, vcollect.sh.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
A=artifacts/claude-rsn358u-20260927
LABEL=claude-sleep-358u
G=${G358V:-$HOME/premonition-watch/rsn358u-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MP=${MP358:-$HOME/premonition-models/rsn358u}
VAST=${VAST358:-vastai}
PYJ=${PYJ358:-"uv run --offline --no-project --python 3.12 python -c"}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it
QUERY="gpu_name=RTX_5090 num_gpus=1 reliability>=0.98 disk_space>=40 cpu_cores_effective>=16 cuda_max_good>=12.8 rentable=true"
CAP_STOP=3.60     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (cap $4)
TIME_CAP=16200    # seconds from the first rental (4 h 30 min): copy back, destroy, TIME-STOP
ORDER="loop-s13 plain-s13 loop-s14 plain-s14 loop-s15 plain-s15 loop-s16 plain-s16"
now() { date -u +%FT%TZ; }
log() { mkdir -p "$G"; echo "$(now) $*" | tee -a "$G/log.txt"; }
# $G/rentals.txt: one line per instance created: id dph epoch_created [epoch_gone]
spent() { awk -v n="$(date +%s)" '{e=(NF>=4)?$4:n; s+=$2*(e-$3)/3600} END{printf "%.2f", s+0}' "$G/rentals.txt" 2>/dev/null; }
over() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a+0>=b+0)}'; }
labelled() { $VAST show instances --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("instances",d) if isinstance(d,dict) else d; print(" ".join(str(i["id"]) for i in d if i.get("label")=="'"$LABEL"'"))'; }
status_of() { $VAST show instances --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("instances",d) if isinstance(d,dict) else d; m=[i for i in d if str(i["id"])=="'"$1"'"]; print((m[0].get("actual_status") or "starting") if m else "gone")'; }
mark_gone() { awk -v id="$1" -v t="$(date +%s)" '$1==id && NF==3 {$0=$0" "t} {print}' "$G/rentals.txt" > "$G/rentals.tmp" && mv "$G/rentals.tmp" "$G/rentals.txt"; }
# destroy one instance by its exact id (only ids this task created: they are in rentals.txt) and confirm it is gone
destroy() {
  grep -q "^$1 " "$G/rentals.txt" || { log "REFUSED destroy $1: not created by this task"; return 1; }
  for try in 1 2 3; do
    $VAST destroy instance "$1" < /dev/null > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep 10; [ "$(status_of "$1")" = gone ] && { mark_gone "$1"; log "DESTROYED $1 (confirmed gone), spent so far \$$(spent)"; return 0; }; done
  done
  log "DESTROY-UNCONFIRMED $1: still listed after 3 tries"; return 1
}
sshto() { echo "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
# copy the rental's W folder back to $G/out and each sealed final.pt to $MP (sha256 checked against the rental's SEAL-run)
copy_back() {
  mkdir -p "$G/out" "$MP"
  $SS "cd /root/r && tar -cf - W drive.log" < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  log "copied back: $(ls "$G/out/W" 2>/dev/null | tr '\n' ' ' | cut -c1-300)"
  [ -s "$G/out/W/SEAL-run.sha256.txt" ] || return 0
  while read -r sha f; do R=${f%/final.pt}; mkdir -p "$MP/$R"
    [ -f "$G/out/W/$R/final.pt" ] && cp "$G/out/W/$R/final.pt" "$MP/$R/final.pt"
    m=$(shasum -a 256 "$MP/$R/final.pt" 2>/dev/null | awk '{print $1}')
    [ "$m" = "$sha" ] && log "Mac copy $MP/$R/final.pt sha256 ok" || log "Mac copy of $R sha256 '$m' does not match SEAL-run $sha"
  done < "$G/out/W/SEAL-run.sha256.txt"
}
