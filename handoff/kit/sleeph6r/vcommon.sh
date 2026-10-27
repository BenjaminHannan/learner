# dir-h6 vast kit (sleep-length test, arm B), Mac-side helpers. Sourced by vstart.sh, vguard.sh, vcollect.sh.
# Kit sleeph6r, written 2026-09-28 by helper H7 for the Director (artifacts/claude-dir-h6-sleeplen-20260928). It copies the
# pattern of handoff/kit/sleep358n3r and changes what dir-h6 needs. bash 3.2 safe (macOS): no arrays, no `timeout`, no bash-4 syntax.
# The vast key is never read or printed here: the vastai CLI reads its own config. Only ids this task created are ever destroyed.
# What differs from sleep358n3r (and nothing else):
#   1. dir-h6's own folder, label and Mac state folder; the base is 358u's loop nets (the ones slp-358n3 used: its result files
#      record ckpt_sha256 equal to 358u's SEAL-run), so the inputs are checked against artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt;
#   2. money stop $3.00 (hard cap $4.00), BASE_H 4.0 (inferred, see below), no CPU-only work on the rental (no RESUME, no S-final.pt);
#   3. the guard is started as soon as ssh answers, BEFORE any long remote call, and the state is written first (vast-launch-ssh-hang);
#   4. every long remote call in vstart is bounded (bounded), the launch uses the braces form (LAUNCH_CMD);
#   5. stops (money, time, stall, no launch) halt the runs by exact PID first, then copy back what exists, verified against a sha256
#      manifest, and only then destroy by exact id; a 30-minute snapshot of the rental's W folder is kept on the Mac meanwhile.
A=artifacts/claude-dir-h6-sleeplen-20260928
N3A=artifacts/claude-slp358n3-20260927      # sealed slp-358n3 code, tests and day sizes (run-vast/sizes.json) that dir-h6 imports
LABEL=claude-dir-h6-sleeplen
G=${GH6V:-$HOME/premonition-watch/dirh6-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files, snapshots); never pushed
MPU=${MPUH6:-$HOME/premonition-models/rsn358u}   # 358u's loop checkpoints loop-s13..16/final.pt (inputs; read only, uploaded)
SRU=artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt   # their sealed sha256 (on main)
VAST=${VASTH6:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b and sleep358n3r do)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYMH6:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYMH6:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEYH6:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it and fails closed
# Any single-GPU card, ranked by vast's TFLOPS per $/h (Ben 14:05 UTC 09-27: "use cheap gpus, whatever gives most tflops/$/hr").
# Needs: >= 24 GB GPU RAM (4 seed runs of about 6 GB each fit in 24 GB: slp-358n3 ran that way on a 3090; a run starts only while 5 GB is free), compute
# capability >= 8.0 (bf16 autocast), a CUDA 12.8 driver for the torch 2.11 cu128 wheel, reliability >= 0.98, and MINCPU cores:
# nothing here runs on the CPU any more (no RESUME), so the old 16-core line is gone, but 4 runs at once each need a feeding
# core, so 8 is kept as a floor (inferred, not measured; slp-358n3 ran on 48 cores).
MINRAM_GB=24
MINCPU=8
QUERY="num_gpus=1 gpu_ram>=$MINRAM_GB compute_cap>=800 reliability>=0.98 disk_space>=40 cpu_cores_effective>=$MINCPU cuda_max_good>=12.8 inet_down>=200 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090 (the card the time estimate is stated for)
MAXDPH=0.60       # dollars per hour: offers above this are skipped
CAP_STOP=3.00     # dollars, all rentals of this task together: halt, copy back, destroy, BUDGET-STOP (Director's hard cap per job $4.00)
CAP_HARD=4.00     # never rent another card once spent reaches this (spent is checked against CAP_STOP first)
# BASE_H = estimated hours on a 5090 (Director's queue file: 4.0, inferred). Per seed: S 900 + L 18,000 + B 18,000 night steps
# (about twice slp-358n3's busiest seed, which took 53.5 min on an RTX 3090 with four seeds sharing the card, 2026-09-28 02:34-03:30 UTC),
# plus 3 x 4 scorings. So 4.0 is well above what slp-358n3's numbers suggest (about 1 to 2 h on a 3090, inferred): it is the safe side.
BASE_H=4.0
RUNS=4; RUN_GB=6; FREE_GB=5   # a run starts only while 5 GB is free, so a card holds min(4, floor((GB - 5) / 6) + 1) at once.
                              # RUN_GB 6 is MEASURED: slp-358n3's gpumem.log (RTX 3090, 4 seed runs at once, arms S R Z N L) peaked at 5.03 to 5.93 GB
                              # per seed process; dir-h6 has 4 arms (N S L B), so at most that (inferred). The old kit guessed 3.
FIT=0.8           # an offer is used only if its estimated hours x $/h <= 0.8 x CAP_STOP (Thread manager 14:19 UTC 09-27)
# estimate for a card = BASE_H x max(1, 5090 TFLOPS / card TFLOPS) x (its waves / a 5090's waves), waves = ceil(4 / at once);
# the guard's time cap is 1.5 x that estimate; the money stop comes at 3.00 / ($/h), which the fit check puts at >= 1.25 x the
# estimate. Both bound the run, and whichever is reached first ends it (a dear card meets the money stop first, a cheap one the time cap).
TIME_CAP=$(awk -v b="$BASE_H" 'BEGIN{printf "%d", b*1.5*3600}')
SSH_WAIT=90       # x 10 s = 15 min for a new host to answer ssh
PRE_MAX=2700      # s: the guard gives up on a rental whose drive.sh has not launched the first seed 45 min after ssh answered (uploads, pip, checks, smoke)
UPLOAD_MAX=1800   # s: longest any one upload call may take before vstart kills it and moves on to the next host
SNAP_EVERY=6      # guard cycles (x 5 min): copy the rental's small files to $G/snap every 30 min, a save during the run
ORDER="s13 s14 s15 s16"   # one run per 358u loop seed (arms N, S, L, B all inside it)
EXPECT="dirh6-seed%S.json"   # the file every run that did not die brings back (%S = its seed)
# the launch on the rental: braces, so ssh returns at once (without them the whole `cd && setsid ...` list is backgrounded and keeps
# ssh's stdout open until drive.sh ends: 358u's start hung there, 2026-09-27 14:04 UTC, and the guard never started)
LAUNCH_CMD='cd /root/r && { setsid nohup bash handoff/kit/sleeph6r/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & } ; echo launched'
POLL='cd /root/r 2>/dev/null; echo "last=$(tail -1 W/drive-state.txt 2>/dev/null)"; echo "bytes=$(cat W/*.log W/*.err W/drive-state.txt 2>/dev/null | wc -c | tr -d " ")"; echo "gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d " ")"; echo "launches=$(grep -c " LAUNCH " W/drive-state.txt 2>/dev/null)"'
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
# kill_tree <pid>: the process and everything below it (pgrep -P works on macOS and Linux)
kill_tree() { for c in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$c"; done; kill "$1" 2>/dev/null; }
# bounded <seconds> <command...>: run a command (or shell function), kill it and its children after <seconds>; exit 124 if it was killed.
# macOS has no `timeout`. stdin is passed through (a plain `&` job would get /dev/null).
bounded() {
  bt=$1; shift
  bm=$(mktemp "${TMPDIR:-/tmp}/bounded.XXXXXX"); rm -f "$bm"   # the watchdog creates this file when it fires
  "$@" <&0 & bp=$!
  ( sleep "$bt"; : > "$bm"; kill_tree "$bp" ) > /dev/null 2>&1 & bw=$!
  wait "$bp" 2> /dev/null; brc=$?
  kill "$bw" 2> /dev/null; wait "$bw" 2> /dev/null
  if [ -e "$bm" ]; then rm -f "$bm"; return 124; fi
  return $brc
}
# Copy the rental's W folder (and drive.log) back to $G/out, checked file by file against a sha256 manifest made on the rental
# after everything was halted or finished (no weights exist in this test: .pt files are never copied).
#   copy_back partial -> ok when every manifest file arrived and matches (also when the rental has no W folder at all).
#                        Used after a halt (money, time, stall, no launch) and after FAILED: a seed with no result file is a dead
#                        seed, the recount says so; it is not a reason to keep paying for the card.
#   copy_back runs    -> the same, plus: sizes.json and torch.txt arrived, and each of the 4 runs either has its result file or
#                        drive.sh recorded it as DIED (else the rental is kept, stopped, for the Director).
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  cmode=${1:-runs}
  has=$($SS '[ -d /root/r/W ] && echo yes || echo no' < /dev/null 2>/dev/null)
  if [ "$has" != yes ]; then
    [ "$has" = no ] && [ "$cmode" != runs ] && { log "COPY-CHECK: no W folder on the rental, nothing to copy"; return 0; }
    log "COPY-CHECK FAIL: cannot tell whether the rental has a W folder (ssh answered '${has:-nothing}')"; return 1
  fi
  mkdir -p "$G/out/W"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && find W drive.log -type f ! -name MANIFEST.sha256 ! -name "*.pt" 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256' < /dev/null 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256; nm=0; nok=0
  for t in 1 2 3; do   # every file in one tar, up to 3 tries, each checked against the manifest
    $SS 'cd /root/r && find W drive.log -type f ! -name "*.pt" 2>/dev/null | tar -cf - -T -' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
    [ -s "$M" ] || { log "copy-back try $t: no manifest came back"; sleep 10; continue; }
    nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c "$M" 2>/dev/null | grep -c ': OK$')
    [ "$nm" = "$nok" ] && break; log "copy-back try $t: $nok of $nm files match the rental's manifest"; sleep 10
  done
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c "$M" 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] && [ "$nm" -gt 0 ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "$cmode" = partial ] && return 0
  WD=$G/out/W; bad=0
  for R in $ORDER; do
    if grep -q " DIED $R " "$WD/drive-state.txt" 2>/dev/null; then log "$R: DIED on the rental (no result file), recorded"; continue; fi
    for f in $EXPECT; do f=${f//%S/${R#s}}; [ -s "$WD/$R/$f" ] || { log "$R/$f: expected file missing and no DIED record"; bad=1; }; done
  done
  [ -s "$WD/sizes.json" ] || { log "COPY-CHECK: no W/sizes.json"; bad=1; }
  [ -s "$WD/torch.txt" ] || { log "COPY-CHECK: no W/torch.txt"; bad=1; }
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: not every run is finished and copied (or recorded as died)"; return 1; }
  log "COPY-CHECK: all 4 runs, sizes and the torch record accounted for"; return 0
}
