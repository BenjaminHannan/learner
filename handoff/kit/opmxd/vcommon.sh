# opus-mxd vast kit (sparse-MoE job mxd-1: GPU smoke + phase 1, NO holdout), shared Mac-side helpers.
# Opus manager session for Ben (Ben asked for vast use 2026-09-29). Sourced by vstart.sh, vguard.sh, vcollect.sh.
# Copy of handoff/kit/s3v (structure and safety logic unchanged), adapted: one rental, one job, phase-1 outputs.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
A=artifacts/claude-moe-deep-20260929                 # sealed folder: sent to the rental, NEVER written to in the repo
OUT=artifacts/opus-manager-20260929/mxd-vast         # where vcollect.sh puts results (its own folder)
LABEL=opus-mxd
G=${GOPMXD:-$HOME/premonition-watch/opmxd-vast}      # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
VAST=${VASTOPMXD:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as s3v does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYMOPMXD:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYMOPMXD:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEYOPMXD:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; box/drive.sh pins torch 2.14.0+cu126 inside it
# Loop control sources (mxd-1 step 2): the Mac's copies, checked against the recorded sha256 (artifacts/claude-distill-20260928/checkpoints-sha256.txt)
LSRC=${LSRCOPMXD:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/runs}
LSHA0=${LSHA0OPMXD:-1f15f8990a1fd768841d0bfa989e8aba809f54951d7eabf375c42bb82f0c12fe}
LSHA1=${LSHA1OPMXD:-17e7217bedc7559f3ed17ab13e4f2c717e34a12124d618b4acef24097f65abd9}
# Any single-GPU card, ranked by vast's TFLOPS per $/h. Needs: >= 16 GB GPU RAM (untested guess: L8-E64 is 19.5M weights, batch 64,
# 48-round inference of 32 mazes; a few GB), compute capability >= 8.0, CUDA >= 12.6 driver for the cu126 wheel (no cu128 build of 2.14.0 exists; cu126 lacks sm_120, so compute capability 12.x cards are filtered out in vstart.sh), >= 8 CPU cores (the
# smoke's CPU half runs on the rental: about 20 s per maze batch on one thread here).
MINRAM_GB=16
EXCLUDE_HOSTS="406325"   # hosts that gave no ssh (406325: 358t3 start and y1t p1, 2026-09-27)
QUERY="num_gpus=1 gpu_ram>=$MINRAM_GB compute_cap>=800 reliability>=0.98 disk_space>=40 cpu_cores_effective>=8 cuda_max_good>=12.6 inet_down>=200 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090 (the card BASE_H is written for); logged beside the chosen card's
MAXDPH=0.50       # dollars per hour: offers above this are skipped
CAP_STOP=2.50     # dollars, all rentals of this task together (this task's own cap of Ben's $5 for the session): copy back, destroy, BUDGET-STOP
# BASE_H: estimated hours on an RTX 5090 for the WHOLE job (pip + seal + selftest + smoke + phase 1: 2 MoE sources, 2 MoE dev ladders, 2 loop-control
# ladders). AN UNTESTED GUESS, not a measurement. Derivation (CPU numbers: artifacts/claude-moe-deep-20260929/CHECKS-before-gpu.md, 1 thread, main entry L8-E64;
# step counts: scripts/claude_moe_deep_run.py):
#   Steps: a source is 12000 practice steps (SOURCE_STEPS, batch 64). A dev ladder is 4096 maze batches (4 updates each) + 1024 sleep steps + 11 scoring
#   stages (see time_config). Phase 1 = 2 sources + 2 MoE ladders + 2 loop-control ladders (source_dir of loopctl is the recorded loop source: no practice).
#   CPU: 5.2 s/practice step, 20.7 s/maze batch (= 4 x a step), 21.1 s per 32-maze 48-round scoring pass.  Check: 12000 x 5.2 s = 17.3 h (the "17 h" in PASSMARKS).
#   GPU guess: the net is small (d 256, ~19.5M stored weights, 8 layers, a step is at most 16 rounds) so it is LAUNCH-BOUND, not FLOP-bound.
#   Kernel launches: about 80 per layer per round forward (attention ~25, router+top-k+sort+scatter ~40, two batched matmuls, shared FFN); 8 layers = ~640 per round.
#   A practice step runs avg 8.5 rounds forward and ~3.3 rounds with gradient (backward ~2x): 640 x (8.5 + 2 x 3.3) = ~9.7k launches at ~25 us (eager PyTorch,
#   host syncs from counts.max()/tolist included) = ~0.25 s per practice step (CPU 5.2 s: a 21x speed-up, guess).  Maze batch = 4 steps = ~1.0 s.
#   A scoring pass: 48 rounds x 640 = 31k launches = ~0.6 s (CPU 21.1 s).  The loop control is 2 shared blocks with no MoE (~30 launches per block per
#   round vs ~80 x 8): about 10x fewer launches than the MoE net.
#   Per MoE source:        12000 x 0.25 s                         = 3000 s = 0.83 h
#   Per MoE dev ladder:    4096 x 1.0 s + 1024 x 0.3 s + ~11 x 14 s scoring = 4096 + 307 + 154 = ~4560 s = 1.27 h
#   Per loop-control ladder (~1/8 of the MoE ladder's launches): ~0.17 h (10 min)
#   Per seed (source + MoE ladder + loop control) = 0.83 + 1.27 + 0.17 = 2.27 h; two seeds = 4.55 h.
#   Fixed: pip torch ~0.1 h, seal + CPU selftest ~0.1 h, smoke (CPU half ~20 s per maze batch on the rental CPU + GPU half + 7 timing configs) ~0.5 h = 0.7 h.
#   BASE_H = 0.7 + 4.55 = 5.25 h.   Not counted: a source retry at lr 5e-4 (+0.83 h per source that fails V1/V2), checkpoint I/O, host CPU slower than here.
BASE_H=5.25
# the time cap is 1.5 x the card's estimate (guard TIME-STOP); the money stop ($CAP_STOP) may well come first: box/drive.sh runs the parts in the order
# selftest, smoke, MX source s0, MX ladder s0, loop control s0, then seed 1, so a money stop leaves seed 0 whole (copied back, resumable elsewhere)
FIT=0.8           # an offer is used only if its estimated hours x $/h <= 0.8 x CAP_STOP
# estimate for a card = BASE_H x max(1, 5090 TFLOPS / card TFLOPS). Conservative for a launch-bound job (a slower card is not really slower then);
# it only decides which offers pass the FIT check and the time cap.
TIME_CAP=$(awk -v b="$BASE_H" 'BEGIN{printf "%d", b*1.5*3600}')
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
sshopts() { echo "-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3"; }
sshto() { echo "ssh $(sshopts) -p $2 root@$1"; }
scpto() { echo "scp $(sshopts) -P $2"; }
# Copy the rental's W folder back to $G/out, checked file by file against a sha256 manifest made on the rental. The rental's small result files
# (runs/, eq-runs/, SMOKE-gpu.json, TIMING-gpu.json; never a .pt) are first mirrored into W/moe by `drive.sh mirror`.
#   copy_back logs  -> ok when every manifest file arrived and matches
#   copy_back runs  -> also: every part drive-state.txt says finished brought back its files, and a DONE run has every part finished or skipped
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && { bash handoff/kit/opmxd/box/drive.sh mirror || true; } && find W drive.log -type f ! -name MANIFEST.sha256 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256 && tar -cf - W drive.log' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  bad=0; O=$G/out/W; S=$O/drive-state.txt
  need() { [ -s "$O/$1" ] || { log "$1: expected file missing"; bad=1; }; }
  grep -q ' SELFTEST-OK' "$S" 2>/dev/null && need selftest_rental.txt
  if grep -q ' SMOKE-DONE ' "$S" 2>/dev/null; then need smoke_log.txt; need moe/SMOKE-gpu.json; need moe/TIMING-gpu.json; fi
  grep -q ' PART-START ' "$S" 2>/dev/null && need log_phase1.txt
  for p in $(awk '$2=="PART-DONE" {print $3}' "$S" 2>/dev/null); do
    case $p in
      src-s0) need moe/runs/L8-E64-s0/qualified.json;; src-s1) need moe/runs/L8-E64-s1/qualified.json;;
      mx-s0) need moe/eq-runs/L8-E64-pre-s0/adapt.json;; mx-s1) need moe/eq-runs/L8-E64-pre-s1/adapt.json;;
      ctl-s0) need moe/eq-runs/loopctl-pre-s0/adapt.json;; ctl-s1) need moe/eq-runs/loopctl-pre-s1/adapt.json;;
    esac; done
  if grep -q ' DONE$' "$S" 2>/dev/null; then
    for p in src-s0 mx-s0 ctl-s0 src-s1 mx-s1 ctl-s1; do
      grep -qE " PART-(DONE|SKIPPED) $p( |\$)" "$S" || { log "$p: DONE run but this part is neither finished nor skipped"; bad=1; }; done; fi
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: a finished part did not bring back its files"; return 1; }
  log "COPY-CHECK: every part the rental recorded as finished is accounted for"; return 0
}
