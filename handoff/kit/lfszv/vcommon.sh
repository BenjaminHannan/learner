# lf-sz vast kit (loop2 vs loop8 forgetting test), shared Mac-side helpers (sleep research thread, 2026-09-27). Sourced by
# vstart.sh, vguard.sh, vcollect.sh.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
# Copy of handoff/kit/sleep358tv (the 358t v3 kit at 7a1e0b85e, itself a copy of the Thread manager-reviewed 358u kit v2) for
# lf-sz: 6 runs (loop8 / loop2w / loop4w x seeds 9, 10), all at once on one card. No checkpoints are kept: each run's result is its
# result.json and log.jsonl. Destroy only after a verified copy (every run's files arrived and match), else stop.
A=artifacts/claude-lfsz-20260928
LABEL=claude-lfsz
G=${G358V:-$HOME/premonition-watch/lfsz-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MP=${MP358:-$HOME/premonition-models/lfsz}   # unused: no weights are copied
VAST=${VAST358:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM358:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYM358:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEY358:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it
# Any single-GPU card (Ben 14:05 UTC: "use cheap gpus, whatever gives most tflops/$/hr"), ranked by vast's TFLOPS per $/h.
# Needs: >= 12 GB GPU RAM (4 small runs, d 256, batch 64; about 2 GB each, inferred, not measured), compute capability >= 8.0
# (bf16 autocast), and a CUDA 12.8 driver for the torch 2.11 cu128 wheel.
MINRAM_GB=16
EXCLUDE_HOSTS="406325"   # hosts that gave no ssh (406325: 358t3 start and y1t p1, 2026-09-27)
QUERY="num_gpus=1 gpu_ram>=$MINRAM_GB compute_cap>=800 reliability>=0.98 disk_space>=40 cpu_cores_effective>=16 cuda_max_good>=12.8 inet_down>=200 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090 (the card the time cap was set for); logged beside the chosen card's
MAXDPH=0.65       # dollars per hour: offers above this are skipped
CAP_STOP=0.45     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (task cap under $0.50, the standing money rule of 09-28)
BASE_H=0.5        # estimated hours on a 5090 for all 6 runs at once: lf-sz is 6 runs of about the same per-round compute as lf-8 (2 x 512^2 = 8 x 256^2 = 4 x 360^2, about), lf-8 took 16 min of rental at $0.47/h for 4 runs (run-vast/rentals.txt), so 0.5 h is a guess with room; the time cap is 1.5x this
                 # thread at 2 layers; 8 layers took about 4.6x the CPU time per step over 3 timed steps; the small net is
                 # launch-bound on a GPU, so the GPU time is a guess; the time cap is 1.5x this)
RUNS=6; RUN_GB=2; FREE_GB=3   # a card holds min(6, floor((GB - 3) / 2) + 1) at once; 13 GB and up hold all 6 (per-run GB inferred)
FIT=0.8           # an offer is used only if its estimated hours x $/h <= 0.8 x CAP_STOP (the Thread manager, 14:19 UTC)
# estimate for a card = BASE_H x max(1, 5090 TFLOPS / card TFLOPS) x (its waves / a 5090's waves), waves = ceil(8 / at once);
# the guard's time cap is 1.5 x that estimate, so the money stop (>= 1.25 x the estimate by the fit check) never comes first
TIME_CAP=$(awk -v b="$BASE_H" 'BEGIN{printf "%d", b*1.5*3600}')
ORDER="loop8-s9 loop2w-s9 loop4w-s9 loop8-s10 loop2w-s10 loop4w-s10"
EXPECT="result.json log.jsonl lfsz.json"   # files every run that did not die must bring back
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
# Copy the rental's W folder back to $G/out, checked file by file against a sha256 manifest made on the rental.
#   copy_back logs  -> ok when every manifest file arrived and matches
#   copy_back runs  -> also: each of the 6 runs brought back every EXPECT file, or drive.sh recorded it as DIED
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out" "$MP"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && find W drive.log -type f ! -name MANIFEST.sha256 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256 && tar -cf - W drive.log' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  bad=0
  for R in $ORDER; do
    if grep -q " DIED $R " "$G/out/W/drive-state.txt" 2>/dev/null; then log "$R: DIED on the rental (no result.json), recorded"; continue; fi
    for f in $EXPECT; do [ -s "$G/out/W/$R/$f" ] || { log "$R/$f: expected file missing"; bad=1; }; done
  done
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: not every run brought back its files (or was recorded as died)"; return 1; }
  log "COPY-CHECK: all 6 runs accounted for"; return 0
}
