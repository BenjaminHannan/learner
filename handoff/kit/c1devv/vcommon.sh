# c1-dev vast kit, shared Mac-side helpers (Everyday chat thread, 2026-09-27). Sourced by vstart.sh, vguard.sh, vcollect.sh.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
# Built from the rsn-358s vast kit (handoff/kit/sleep358sv, itself from the Thread manager-reviewed 358u kit v2) for c1-dev
# (artifacts/claude-c1dev-20260927/PLAN.md and ADDENDUM-2-vast.md): the four chat arms D, T, Q, L on one vast card.
# Eval only: nothing is trained and no weights come back. Destroy only after a verified copy, else stop.
A=artifacts/claude-c1dev-20260927
LABEL=claude-everydaychat-c1dev
G=${GC1V:-$HOME/premonition-watch/c1dev-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
VAST=${VASTC1V:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b and 358s do)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYMC1V:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYMC1V:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEYC1V:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; box/drive.sh pins torch 2.11.0+cu128 and transformers 5.17.0
# Card (Ben 14:05 UTC 09-27: "use cheap gpus, whatever gives most tflops/$/hr"; Director 14:15: GPU RAM checked client-side in
# MB, ranked by TFLOPS per $/h, estimate x $/h at most 0.8 x the money stop, time cap scaled by TFLOPS, card logged).
# Needs: >= 15,000 MB GPU RAM (the 16 GB class of BensPC's card, where this run was planned; the arms load one model at a time,
# the largest Qwen3.5-2B at about 4 GB in bf16), compute capability >= 8.0 (the talkers load in bf16), a CUDA 12.8 driver for
# the torch 2.11 cu128 wheel, and a fast download (about 13 GB: torch and the three pinned model snapshots).
MINRAM_MB=15000
MINCC=800
QUERY="num_gpus=1 gpu_ram>=15 compute_cap>=800 reliability>=0.98 disk_space>=40 cpu_cores_effective>=8 cuda_max_good>=12.8 inet_down>=200 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090, the reference card for the estimate and the time cap
SETUP_MIN=25      # minutes before arm D starts on any card: image, pip, the 3 model downloads, seal, selftests (estimate)
ARMS_MIN=60       # minutes for the 4 arms on a 5090 (estimate: ch-403's agent ran 336 turns in about 9 min on a 5090)
DL_GB=13          # GB each rental downloads (torch wheels about 3.5, model snapshots about 9); priced at the host's $/GB
CAP_STOP=1.50     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (task cap $2, inside Ben's $4)
FIT=0.8           # an offer is used only if its estimate (GPU hours x $/h + download) is at most FIT x CAP_STOP
BASE_TIME=${BTC1V:-10800}   # seconds from the first rental on a 5090 (3 h); vstart scales it by 5090 TFLOPS / chosen TFLOPS (never below 1x)
TIME_CAP=$BASE_TIME
ARMS="D T Q L"
# The measured code and chats come from the BensPC kit's pinned commit, whose tree matches SEAL-2 24/24 (main's
# claude_e2e02d.py changed later, at ADDENDUM-46/49: comments and a SLEEP02D refusal moved from the talker to the reasoner;
# with SLEEP02D off the talker path is the same). Only box/drive.sh comes from this kit's own pinned commit.
CODE=62a5944c8a17abd75322781763d2928326edeeda
now() { date -u +%FT%TZ; }
log() { mkdir -p "$G"; echo "$(now) $*" | tee -a "$G/log.txt"; }
# $G/rentals.txt: one line per instance created: id dph epoch_created [epoch_destroyed_or_stopped]
# $G/extra.txt:   one line per instance that was sent work: id dollars (its download at the host's $/GB, estimated)
spent() { { awk -v n="$(date +%s)" '{e=(NF>=4)?$4:n; s+=$2*(e-$3)/3600} END{printf "%.4f\n", s+0}' "$G/rentals.txt" 2>/dev/null
            awk '{s+=$2} END{printf "%.4f\n", s+0}' "$G/extra.txt" 2>/dev/null; } | awk '{s+=$1} END{printf "%.2f", s+0}'; }
rows() { [ -f "$1" ] && awk 'NF{n++} END{print n+0}' "$1" || echo 0; }
convs() { [ -f "$1" ] && grep -o '"item_id": "[^"]*"' "$1" | sort -u | awk 'END{print NR}' || echo 0; }
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
    for w in 1 2 3 4 5 6; do sleep ${SLV:-10}; [ "$(status_of "$1")" = gone ] && { mark_end "$1"; log "DESTROYED $1 (confirmed gone), spent so far \$$(spent)"; return 0; }; done
  done
  log "DESTROY-UNCONFIRMED $1: still listed after 3 tries"; return 1
}
# stop (not destroy) one instance of ours: GPU billing ends, the disk and its files stay (a small storage charge continues)
stop_inst() {
  mine "$1" stop || return 1
  for try in 1 2 3; do
    echo y | $VAST stop instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep ${SLV:-10}; s=$(status_of "$1"); case "$s" in exited|stopped|gone) mark_end "$1"; log "STOPPED $1 (status $s; not destroyed, files kept on its disk), spent so far \$$(spent)"; return 0;; esac; done
  done
  log "STOP-UNCONFIRMED $1: status $(status_of "$1") after 3 tries"; return 1
}
sshto() { echo "${SSHC1V:-ssh} -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
# Before copying on any end but DONE or FAILED, stop the rental's own run so no file changes during the copy: drive.sh wrote its
# PID to W/drive.pid and runs as the leader of its own process group (setsid), so the whole group is signalled by that exact id.
halt_drive() {
  $SS 'p=$(cat /root/r/W/drive.pid 2>/dev/null); [ -n "$p" ] && kill -0 "$p" 2>/dev/null && { kill -TERM -- -"$p"; sleep 10; kill -0 "$p" 2>/dev/null && kill -KILL -- -"$p"; echo "halted drive.sh group $p"; } || echo "drive.sh not running"' < /dev/null 2>> "$G/log.txt" | tee -a "$G/log.txt"; }
# Copy the rental's W and outC1 folders and drive.log back to $G/out, checked file by file against a sha256 manifest made on
# the rental. Returns 0 only when the manifest came back, every file in it arrived and matches, and the progress file is among
# them; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && find W outC1 drive.log -type f ! -name MANIFEST.sha256 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256 && tar -cf - W outC1 drive.log' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  grep -q ' W/drive-state.txt$' "$M" || { log "COPY-CHECK FAIL: the progress file W/drive-state.txt is not in the manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest (chat rows:$(for x in $ARMS; do printf ' %s=%s' $x "$(rows "$G/out/outC1/chat_$x.jsonl")"; done))"
  return 0
}
