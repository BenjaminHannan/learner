# opcpu vast kit (Opus manager, 2026-09-29): sealed CPU-only tests on ONE rented many-core vast box. Shared Mac-side helpers, sourced by
# vstart.sh, vguard.sh, vcollect.sh. Copy of handoff/kit/s3v/vcommon.sh (dir-s3 kit) with the changes listed in DEVIATIONS.md.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
A=artifacts/opus-manager-20260929/cpu-vast           # the ONLY repo folder this kit writes to (vcollect.sh)
LABEL=opus-cpu
G=${GOPC:-$HOME/premonition-watch/opcpu-vast}        # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
VAST=${VASTOPC:-vastai}
# Mac python for the offer json only: uv's 3.12 (as the s3v kit does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYMOPC:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYMOPC:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEYOPC:-$HOME/.ssh/id_ed25519}                 # only "$KEY.pub" is ever read
BR=${BROPC:-/root}                                   # the rental's base folder (tests point it at a scratch folder)
MB=${MBOPC:-/Users/ben-hannan/Desktop/projects/beautiful-model}   # the Mac checkout that holds the Mac-only nets
FEW=$MB/artifacts/claude-fewex-20260927
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime  # base image only (known to take ssh in the earlier kits); drive.sh builds a venv with torch 2.14.0 CPU
# Any GPU (never used), many CPU cores: cost per CPU core decides. cuda_max_good keeps the CUDA image startable on the host driver.
QUERY="num_gpus=1 cpu_cores_effective>=32 reliability>=0.98 disk_space>=40 inet_down>=200 cpu_ram>=32 cuda_max_good>=12.8 rentable=true"
MINCORES=32
EXCLUDE_HOSTS="406325"   # hosts that gave no ssh in earlier kits (406325: 358t3 start and y1t p1, 2026-09-27)
MAXDPH=0.35       # dollars per hour: offers above this are skipped
CAP_STOP=${CAPSTOPOPC:-2.50}     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (the ${..OPC} overrides here and below exist for test/fake_run.sh only)
CREDIT_FLOOR=2.50 # start refuses if the vast credit is under this
BASE_H=${BASEHOPC:-5.0}    # estimated wall hours (schedule in DEVIATIONS.md: about 4.5 h typical, 6.9 h worst case); an estimate, not a measurement
FIT=0.8           # an offer is used only if BASE_H x $/h <= 0.8 x CAP_STOP
TIME_CAP=${TIMECAPOPC:-25200}   # seconds since the first rental: 7 h
JOBS="ks-1-lead0 s2think trn-decode pond-a-dev pond-b-dev pond-c-dev pond-z-dev pond-doubt s1-loop s1-plain"   # test names = folders under $A
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
# stop (not destroy) one instance of ours: billing of the compute ends, the disk and its files stay (a small storage charge continues)
stop_inst() {
  mine "$1" stop || return 1
  for try in 1 2 3; do
    echo y | $VAST stop instance "$1" > /dev/null 2>&1
    for w in 1 2 3 4 5 6; do sleep 10; s=$(status_of "$1"); case "$s" in exited|stopped|gone) mark_end "$1"; log "STOPPED $1 (status $s; not destroyed, files kept on its disk), spent so far \$$(spent)"; return 0;; esac; done
  done
  log "STOP-UNCONFIRMED $1: status $(status_of "$1") after 3 tries"; return 1
}
sshto() { echo "ssh -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -p $2 root@$1"; }
# Copy the rental's small files back to $G/out, checked file by file against a sha256 manifest made on the rental by box/pack.sh
# (json, logs, small text; never a .pt; nothing named holdout / test.pt / readpanel / blind).
#   copy_back logs  -> ok when every manifest file arrived and matches
#   copy_back runs  -> also: every job of $JOBS is accounted for in drive-state.txt (END with its return code, or SKIPPED with the reason)
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS "bash $BR/r/handoff/kit/opcpu/box/pack.sh $BR" < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  npt=$(find "$G/out" -name '*.pt' | wc -l | tr -d ' '); [ "$npt" = 0 ] || { log "COPY-CHECK FAIL: $npt .pt file(s) arrived (never copied back)"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  bad=0
  for R in $JOBS; do
    grep -q " JOB $R \(END\|SKIPPED\)" "$G/out/W/drive-state.txt" 2>/dev/null || { log "$R: neither END nor SKIPPED in drive-state.txt"; bad=1; }; done
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: not every job is accounted for"; return 1; }
  log "COPY-CHECK: all jobs accounted for"; return 0
}
