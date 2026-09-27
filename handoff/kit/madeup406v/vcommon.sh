# mu-406 vast kit, shared Mac-side helpers ("Making things up about you" thread, Claude, 2026-09-27). Sourced by vstart.sh,
# vguard.sh and vcollect.sh. bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own
# config. Built from the sleep research thread's kit handoff/kit/sleep358sv (itself from the Thread manager-reviewed 358u kit
# v2): the same rental, guard, copy check and destroy-or-stop rules; only the card rules, the paths and the checks differ.
# Ben's standing vast order (14:05-14:06 UTC 09-27, Director ledger ae27bb2b6): jobs waiting on BensPC go to vast, best
# TFLOPS per $/h, GPU RAM checked, time cap scaled to the card, at most $4 per job.
A=artifacts/claude-mu406-20260926
LABEL=claude-madeup-mu406
G=${G406V:-$HOME/premonition-watch/mu406-vast}      # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MP=${MP406:-$HOME/premonition-models/mu406-vast}    # the adapter's Mac copy; never pushed
VAST=${VAST406:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM406:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYM406:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEY406:-$HOME/.ssh/id_ed25519}
SSHBIN=${SSH406:-ssh}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it
# CARD: any single-GPU card, ranked by vast's TFLOPS per $/h (Ben 14:05 UTC). Needs, each checked on every offer here (not only
# in the search query): GPU RAM >= 23000 MB (the 24 GB class: the LoRA trains at batch 4 x 1,536 tokens as on BensPC's 16 GB
# card, then up to 9 inference runs share the card, each started only while 6 GB is free), compute capability >= 8.0 (bf16
# training), >= 32 GB CPU RAM (runs load weights on the CPU first), and a CUDA 12.8 driver for the torch 2.11 cu128 wheel.
MINRAM_MB=23000
MINCC=800
QUERY="num_gpus=1 gpu_ram>=23 compute_cap>=800 cpu_ram>=32 reliability>=0.98 disk_space>=60 cpu_cores_effective>=8 cuda_max_good>=12.8 inet_down>=200 direct_port_count>=1 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090, the reference card for the time estimate; logged beside the chosen card's
REFMIN=100        # ESTIMATE, minutes on a 5090 for the whole job: setup 15, train 12, merge 3, smoke 2, arms and no-harm 60
                  # (GSM8K at 512 new tokens is the longest), copy back 8. Not measured: no mu-406 step has run on a GPU yet.
                  # Scaled by 5090 TFLOPS / the card's TFLOPS, never below 1 (generation is limited more by memory speed than
                  # by TFLOPS, so this over-estimates slower cards: the safe side for a time cap)
MAXDPH=1.00       # dollars per hour: offers above this are skipped
CAP_STOP=3.00     # dollars, all rentals of this task together: copy back, destroy (or stop), BUDGET-STOP (inside the $4 per job cap)
FITSHARE=0.8      # fit check: estimated hours x 1.3 x $/h must be at most 0.8 x CAP_STOP, or the offer is skipped
BASE_TIME=12600   # seconds from the first rental on a 5090 (3.5 h, about twice REFMIN); scaled like REFMIN, never below 1x
TIME_CAP=$BASE_TIME
EXPECT="train/summary.json train/train_log.jsonl train/adapter/adapter_config.json smoke/talk_P_smoke.jsonl smoke/talk_T_smoke.jsonl run/talk_P.jsonl run/talk_T.jsonl run/talk_N.jsonl run/talk_PW.jsonl run/talk_TW.jsonl gen/mmlu_P.jsonl gen/mmlu_T.jsonl gen/gsm8k_P.jsonl gen/gsm8k_T.jsonl gen/noharm.json"
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
    for w in 1 2 3 4 5 6; do sleep ${PS406:-10}; [ "$(status_of "$1")" = gone ] && { mark_end "$1"; log "DESTROYED $1 (confirmed gone), spent so far \$$(spent)"; return 0; }; done
  done
  log "DESTROY-UNCONFIRMED $1: still listed after 3 tries"; return 1
}
# stop (not destroy) one instance of ours: GPU billing ends, the disk and its files stay (a small storage charge continues)
stop_inst() {
  mine "$1" stop || return 1
  for try in 1 2 3; do
    echo y | $VAST stop instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep ${PS406:-10}; s=$(status_of "$1"); case "$s" in exited|stopped|gone) mark_end "$1"; log "STOPPED $1 (status $s; not destroyed, files kept on its disk), spent so far \$$(spent)"; return 0;; esac; done
  done
  log "STOP-UNCONFIRMED $1: status $(status_of "$1") after 3 tries"; return 1
}
sshto() { echo "$SSHBIN -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
# Copy the rental's W folder back to $G/out, checked file by file against a sha256 manifest made on the rental.
# (The merged model and the public benchmark files live in /root/r/X on the rental and are never copied: the merged model
#  can be rebuilt from the adapter, the benchmark files from their pinned sha256.)
#   copy_back logs  -> ok when every manifest file arrived and matches
#   copy_back runs  -> also: if drive.sh sealed the adapter, its Mac copy in $MP matches SEAL-run; if drive.sh ended DONE,
#                      every EXPECT file arrived
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
  bad=0; S=$G/out/W/SEAL-run.sha256.txt
  if [ -s "$S" ]; then
    sha=$(awk '$2=="train/adapter/adapter_model.safetensors" {print $1}' "$S")
    mkdir -p "$MP/adapter"; cp "$G/out/W/train/adapter/"* "$MP/adapter/" 2>/dev/null
    m=$(shasum -a 256 "$MP/adapter/adapter_model.safetensors" 2>/dev/null | awk '{print $1}')
    [ -n "$sha" ] && [ "$m" = "$sha" ] && log "adapter: sealed, Mac copy sha256 ok ($MP/adapter)" || { log "adapter: Mac copy sha256 '$m' does not match SEAL-run '$sha'"; bad=1; }
  else log "adapter: not sealed on the rental (training did not finish), nothing to check"; fi
  if tail -1 "$G/out/W/drive-state.txt" 2>/dev/null | grep -q ' DONE$'; then
    for f in $EXPECT; do [ -s "$G/out/W/$f" ] || { log "$f: expected file missing"; bad=1; }; done
  fi
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: the adapter or an expected file did not come back"; return 1; }
  log "COPY-CHECK: everything accounted for"; return 0
}
