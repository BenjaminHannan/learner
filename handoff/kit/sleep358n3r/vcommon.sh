# slp-358n3 vast kit, shared Mac-side helpers (sleep research thread, 2026-09-27). Sourced by vstart.sh, vguard.sh, vcollect.sh.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
# Copy of handoff/kit/sleep358sv (the 358s kit after the Thread manager's fit and wave checks) for slp-358n3, the build's sleep
# gate H-B: nights on the 4 358u loop checkpoints (seeds 13-16), uploaded from the Mac and sha-checked against 358u's SEAL-run,
# plus the RESUME check on the rental's CPU. Destroy only after a verified copy, else stop.
# sleep358n3r (2026-09-28, a stand-in chat for the stopped sleep research thread; artifacts/claude-slp358n3-20260927/ADDENDUM-1.md):
# copy of sleep358nv whose base is the rsn-358u2 re-run of 358u's loop nets. Changes, and nothing else:
#   1. the checkpoint sha check reads the re-run's SEAL-run (SRU) and its Mac copies (MPU);
#   2. kit only: a new host gets 15 min to answer ssh, not 8 (SSH_WAIT);
#   3. kit only: copy-back takes the small files in one tar (up to 3 tries) and every .pt file one file at a time through a
#      tmp file, kept only if its sha256 matches the rental's manifest (up to 3 tries per file); no `timeout` command.
A=artifacts/claude-slp358n3-20260927
LABEL=claude-sleep-358n3
G=${G358V:-$HOME/premonition-watch/rsn358n3-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MP=${MP358:-$HOME/premonition-models/slp358n3}   # the slept reasoners (S-final.pt per seed)
MPU=${MPU358:-$HOME/premonition-models/rsn358u2}   # the rsn-358u2 re-run's loop checkpoints (inputs; read only)
SRU=artifacts/claude-rsn358u2-20260928/SEAL-run.sha256.txt   # their sealed sha256 (the rsn-358u2 re-run's own SEAL-run, on main after its collect)
VAST=${VAST358:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM358:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYM358:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEY358:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it
# Any single-GPU card (Ben 14:05 UTC: "use cheap gpus, whatever gives most tflops/$/hr"), ranked by vast's TFLOPS per $/h.
# Needs: >= 24 GB GPU RAM (a seed run holds 5 small nets, about 3 GB, inferred; runs start only while 5 GB is free),
# compute capability >= 8.0 (bf16 autocast), a CUDA 12.8 driver for the torch 2.11 cu128 wheel, and >= 16 CPU cores (RESUME runs on the CPU).
MINRAM_GB=24
QUERY="num_gpus=1 gpu_ram>=$MINRAM_GB compute_cap>=800 reliability>=0.98 disk_space>=40 cpu_cores_effective>=16 cuda_max_good>=12.8 inet_down>=200 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090 (the card the time cap was set for); logged beside the chosen card's
MAXDPH=0.60       # dollars per hour: offers above this are skipped
CAP_STOP=2.00     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (cap $2.40)
BASE_H=2.0       # estimated hours on a 5090 (inferred from 358i: 8 runs at once in 75 min; not measured): 4 seed runs at once, 2,700 graded night steps each, 18,000 L steps on 2, 16-19 scorings of ~2,600 items at 48 rounds; RESUME on the CPU beside them
RUNS=4; RUN_GB=3; FREE_GB=5   # runs start only while 5 GB is free, so a card holds min(4, floor((GB - 5) / 3) + 1) at once (per-run GB inferred)
FIT=0.8           # an offer is used only if its estimated hours x $/h <= 0.8 x CAP_STOP (the Thread manager, 14:19 UTC)
# estimate for a card = BASE_H x max(1, 5090 TFLOPS / card TFLOPS) x (its waves / a 5090's waves), waves = ceil(4 / at once);
# the guard's time cap is 1.5 x that estimate, so the money stop (>= 1.25 x the estimate by the fit check) never comes first
TIME_CAP=$(awk -v b="$BASE_H" 'BEGIN{printf "%d", b*1.5*3600}')
SSH_WAIT=90       # x 10 s = 15 min for a new host to answer ssh
ORDER="s13 s14 s15 s16"   # one run per 358u loop seed (all arms inside it); s13 and s14 also run the report-only L arm
CKPTS="S-final.pt"
EXPECT="slp358n3-seed%S.json"   # files every run that did not die must bring back (%S = its seed)
now() { date -u +%FT%TZ; }
log() { mkdir -p "$G"; echo "$(now) $*" | tee -a "$G/log.txt"; }
# $G/rentals.txt: one line per instance created: id dph epoch_created [epoch_destroyed_or_stopped]
spent() { awk -v n="$(date +%s)" '{e=(NF>=4)?$4:n; s+=$2*(e-$3)/3600} END{printf "%.2f", s+0}' "$G/rentals.txt" 2>/dev/null; }
over() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a+0>=b+0)}'; }
insts() { $VAST show instances --raw < /dev/null 2>/dev/null | $PYJ 'import json,sys
d=json.load(sys.stdin); d=d.get("instances",d) if isinstance(d,dict) else d
for i in d: print(i.get("id"), i.get("label"), i.get("actual_status") or "starting", i.get("ssh_host"), i.get("ssh_port"))'; }
labelled() { insts | awk -v l="$LABEL" '$2==l {printf "%s ", $1}'; }
status_of() { x=$(insts) || { echo ""; return; }; [ -z "$x" ] && { $VAST show instances --raw < /dev/null > /dev/null 2>&1 && echo gone || echo ""; return; }
              echo "$x" | awk -v id="$1" 'BEGIN{s="gone"} $1==id {s=$3} END{print s}'; }
hostport_of() { insts | awk -v id="$1" '$1==id {print $4, $5}'; }
mark_end() { awk -v id="$1" -v t="$(date +%s)" '$1==id && NF==3 {$0=$0" "t} {print}' "$G/rentals.txt" > "$G/rentals.tmp" && mv "$G/rentals.tmp" "$G/rentals.txt"; }
mine() { grep -q "^$1 " "$G/rentals.txt" || { log "REFUSED $2 $1: not created by this task"; return 1; }; }
# destroy one instance by its exact id (only ids this task created: they are in rentals.txt) and confirm it is gone
destroy() {
  mine "$1" destroy || return 1
  for try in 1 2 3; do
    echo y | $VAST destroy instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep 10; [ "$(status_of "$1")" = gone ] && { mark_end "$1"; log "DESTROYED $1 (confirmed gone), spent so far \$$(spent)"; return 0; }; done
  done
  log "DESTROY-UNCONFIRMED $1: still listed after 3 tries"; return 1
}
# stop (not destroy) one instance of ours: GPU billing ends, the disk and its files stay (a small storage charge continues)
stop_inst() {
  mine "$1" stop || return 1
  for try in 1 2 3; do
    echo y | $VAST stop instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep 10; s=$(status_of "$1"); case "$s" in exited|stopped|gone) mark_end "$1"; log "STOPPED $1 (status $s; not destroyed, files kept on its disk), spent so far \$$(spent)"; return 0;; esac; done
  done
  log "STOP-UNCONFIRMED $1: status $(status_of "$1") after 3 tries"; return 1
}
sshto() { echo "ssh -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
# fetch1 <path under /root/r> <Mac path> <sha256>: one file through a tmp file, kept only if its sha256 matches; up to 3 tries
fetch1() {
  for t in 1 2 3; do
    $SS "cat /root/r/$1" < /dev/null > "$2.tmp" 2>> "$G/log.txt"
    m=$(shasum -a 256 "$2.tmp" 2>/dev/null | awk '{print $1}')
    [ "$m" = "$3" ] && { mv "$2.tmp" "$2"; return 0; }
    log "fetch $1 try $t: sha256 ${m:-none} does not match $3"; sleep 10
  done; rm -f "$2.tmp"; return 1; }
# Copy the rental's W folder back to $G/out, checked file by file against a sha256 manifest made on the rental.
#   copy_back logs  -> ok when every manifest file arrived and matches
#   copy_back runs  -> also: SEAL-run arrived, and each of the 8 runs has a sealed final.pt whose Mac copy in $MP matches
#                      SEAL-run and every EXPECT file arrived, or drive.sh recorded it as DIED (no final.pt)
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out/W" "$MP"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && find W drive.log -type f ! -name MANIFEST.sha256 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256' < /dev/null 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256; MS=$G/out/W/MANIFEST.small.sha256; nm=0; nok=0
  # the small files (everything but .pt) in one tar, up to 3 tries
  for t in 1 2 3; do
    $SS 'cd /root/r && find W drive.log -type f ! -name "*.pt" 2>/dev/null | tar -cf - -T -' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
    [ -s "$M" ] || { log "copy-back try $t: no manifest came back"; sleep 10; continue; }
    grep -v '\.pt$' "$M" > "$MS"; nm=$(wc -l < "$MS" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c "$MS" 2>/dev/null | grep -c ': OK$')
    [ "$nm" = "$nok" ] && break; log "copy-back try $t: $nok of $nm small files match the rental's manifest"; sleep 10
  done
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  # every .pt file one at a time through a tmp file, checked against the manifest (skipped if an earlier try already has it)
  grep '\.pt$' "$M" | while read -r sha f; do mkdir -p "$G/out/$(dirname "$f")"
    [ "$(shasum -a 256 "$G/out/$f" 2>/dev/null | awk '{print $1}')" = "$sha" ] || fetch1 "$f" "$G/out/$f" "$sha" || log "$f: no matching copy after 3 tries"; done
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  S=$G/out/W/SEAL-run.sha256.txt; bad=0
  for R in $ORDER; do
    if grep -q " DIED $R " "$G/out/W/drive-state.txt" 2>/dev/null; then log "$R: DIED on the rental (no final.pt), recorded"; continue; fi
    for C in $CKPTS; do
      sha=$(awk -v f="$R/$C" '$2==f {print $1}' "$S" 2>/dev/null)
      if [ -n "$sha" ]; then mkdir -p "$MP/$R"; cp "$G/out/W/$R/$C" "$MP/$R/$C" 2>/dev/null
        m=$(shasum -a 256 "$MP/$R/$C" 2>/dev/null | awk '{print $1}')
        [ "$m" = "$sha" ] && log "$R/$C: sealed, Mac copy sha256 ok" || { log "$R/$C: Mac copy sha256 '$m' does not match SEAL-run $sha"; bad=1; }
      else log "$R/$C: not sealed and no DIED record"; bad=1; fi
    done
    for f in $EXPECT; do f=${f//%S/${R#s}}; [ -s "$G/out/W/$R/$f" ] || { log "$R/$f: expected file missing"; bad=1; }; done
  done
  [ -s "$G/out/W/resume/resume.json" ] || { log "COPY-CHECK: no W/resume/resume.json (the RESUME check did not finish)"; bad=1; }
  [ -s "$G/out/W/sizes.json" ] || { log "COPY-CHECK: no W/sizes.json"; bad=1; }
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: not every run is sealed and copied (or recorded as died)"; return 1; }
  log "COPY-CHECK: all 4 runs, sizes and RESUME accounted for"; return 0
}
