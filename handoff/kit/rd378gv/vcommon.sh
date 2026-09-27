# rd-378g vast kit, shared Mac-side helpers (Trustworthy notes thread, 2026-09-27). Sourced by vstart.sh, vguard.sh,
# vcollect.sh and rsend.sh. bash 3.2 safe (macOS). Built from the sleep research thread's handoff/kit/sleep358sv (the 358u
# kit v2 line the Thread manager reviewed), with the Director's 14:15 UTC card rules for Ben's standing vast order
# (14:05-14:06 UTC). The vast key is never read or printed here: the vastai CLI reads its own config.
A=artifacts/claude-rd378g-20260926
V=$A/vast                                              # where the collect puts pushable files (beside benspc/, never over it)
LABEL=claude-notes-rd378g
G=${G378V:-$HOME/premonition-watch/rd378g-vast}        # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MPRIV=${MPRIV378V:-$HOME/rd378g-private/vast}          # LoCoMo-derived files (dialogs59, g59, per_question): Mac only, never pushed
MADP=${MADP378V:-$HOME/premonition-models/rd378g-vast-adapter}   # G's adapter on the Mac (weights are never pushed)
MR=${MR378V:-$HOME/premonition-models/rd378-notes-merged}        # R, the rd-378 writer (merged), sent to the rental for G5
R_SHA=${RSHA378V:-dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510}
VAST=${VAST378:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b and 358sv do)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM378:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYM378:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEY378:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime    # base image only; drive.sh pins torch 2.11.0+cu128 inside it (fail-closed)
# THE CARD (Director 14:15 UTC): one GPU, ranked by vast's TFLOPS per $/h.
# - GPU RAM >= 16000 MB, checked on every offer client-side in MB (raw offers give gpu_ram in MB) and again on the rental
#   (nvidia-smi memory.total). 16 GB is BensPC's card, where the rd-378 writer trained with the same trainer, batch 16 and
#   max-len 512 without running out of memory (artifacts/claude-rd378-20260925/RESULTS-benspc.md, builder-outbox).
# - compute capability >= 8.0 (the trainer and writer run in bf16) and a CUDA 12.8 driver (torch 2.11 cu128 wheel).
MINRAM_MB=16000
MINCC=800
QUERY="num_gpus=1 gpu_ram>=16 compute_cap>=800 cuda_max_good>=12.8 reliability>=0.98 cpu_cores_effective>=8 disk_space>=40 inet_down>=200 direct_port_count>=1 rentable=true"
MAXDPH=1.00       # dollars per hour: a sanity bound only; the fit check below decides
CAP_STOP=2.50     # dollars, all rentals of this task together: copy back, destroy (or stop), BUDGET-STOP (Ben's cap is $4 per job)
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090, the reference card for the estimate
# Estimate, in minutes on an RTX 5090 (a guess, labelled so): setup 10 (pip, base and MiniLM download, LoCoMo fetch, seals,
# selftests), dialogs 1, train 8 (the rd-378 writer's 958 steps took 11.6 min on BensPC's 5070 Ti; G has 5,511 rows, about
# 690 steps), devcheck 3, write59 19 (rd-378u wrote 2,760 turns in about 17 min on a 5090), score 5, whenoff 5, g5G 4, g5R 4.
EST_MIN=60
WAVES=1           # one chain on one card: every step runs after the one before (no parallel runs), so one wave
RWAIT_MIN=60      # at most this long, after g5G, for R to reach the rental (rsend.sh); then g5R is skipped (ADDENDUM-K fallback)
SETUP_MIN=20      # rental start, ssh, code upload: not scaled by the card
# fit check (Director): estimate x $/h <= 0.8 x the money stop, with the estimate = EST_MIN x max(1, TF5090 / card TFLOPS) x WAVES
# time cap: 3 x that scaled estimate + RWAIT_MIN + SETUP_MIN, in seconds from the first rental (vstart writes it to $G/state)
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
    for w in 1 2 3 4 5 6; do sleep "${PS378:-10}"; [ "$(status_of "$1")" = gone ] && { mark_end "$1"; log "DESTROYED $1 (confirmed gone), spent so far \$$(spent)"; return 0; }; done
  done
  log "DESTROY-UNCONFIRMED $1: still listed after 3 tries"; return 1
}
# stop (not destroy) one instance of ours: GPU billing ends, the disk and its files stay (a small storage charge continues)
stop_inst() {
  mine "$1" stop || return 1
  for try in 1 2 3; do
    echo y | $VAST stop instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep "${PS378:-10}"; s=$(status_of "$1"); case "$s" in exited|stopped|gone) mark_end "$1"; log "STOPPED $1 (status $s; not destroyed, files kept on its disk), spent so far \$$(spent)"; return 0;; esac; done
  done
  log "STOP-UNCONFIRMED $1: status $(status_of "$1") after 3 tries"; return 1
}
sshto() { echo "${SSH378V:-ssh} -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
# Copy the rental's W and P folders back to $G/out (G's merged model stays on the rental; its sha256 is in SEAL-run), checked
# file by file against a sha256 manifest made on the rental.
#   copy_back logs -> ok when every manifest file arrived and matches
#   copy_back runs -> also: every step that ended rc=0 brought its expected files, SEAL-run arrived, and the Mac copy of G's
#                     adapter matches SEAL-run
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && find W P drive.log -type f ! -name MANIFEST.sha256 ! -path "W/g/merged/*" ! -path "W/g_b8/merged/*" 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256 && tar -cf - --exclude=W/g/merged --exclude=W/g_b8/merged W P drive.log' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  O=$G/out; bad=0; GD=$(cat "$O/W/g-dir.txt" 2>/dev/null); GD=${GD:-W/g}
  for s in $(awk '$2=="rc=0" {print $1}' "$O/W/steps.txt" 2>/dev/null); do
    case $s in
      train) need="$GD/summary.json $GD/train_log.jsonl $GD/adapter/adapter_model.safetensors";;
      devcheck) need="W/gdev.jsonl";;
      write59) need="P/g59.jsonl P/dialogs59.jsonl";;
      score) need="P/outg/notes_confirm.json P/outg/ranked_turns.jsonl";;
      whenoff) need="P/outg_whenoff/notes_confirm.json";;
      g5G) need="W/g5_G.jsonl";;
      g5R) need="W/g5_R.jsonl";;
      *) need="";;
    esac
    for f in $need; do [ -s "$O/$f" ] || { log "$s ended rc=0 but $f is missing"; bad=1; }; done
  done
  if grep -q '^train rc=0' "$O/W/steps.txt" 2>/dev/null; then
    S=$O/W/SEAL-run.sha256.txt
    [ -s "$S" ] || { log "SEAL-run missing after a finished train"; bad=1; }
    a=$(awk -v f="$GD/adapter/adapter_model.safetensors" '$2==f {print $1}' "$S" 2>/dev/null)
    m=$(shasum -a 256 "$O/$GD/adapter/adapter_model.safetensors" 2>/dev/null | awk '{print $1}')
    [ -n "$a" ] && [ "$a" = "$m" ] && log "G's adapter: sealed, Mac copy sha256 ok" || { log "G's adapter: Mac copy '$m' does not match SEAL-run '$a'"; bad=1; }
  fi
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: a finished step's files are missing or do not match"; return 1; }
  log "COPY-CHECK: every finished step's files are here"; return 0
}
