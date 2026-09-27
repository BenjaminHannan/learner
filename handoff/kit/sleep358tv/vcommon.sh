# rsn-358t v3 vast kit, shared Mac-side helpers (sleep research thread, 2026-09-27). Sourced by vstart.sh, vguard.sh, vcollect.sh.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
# Copy of handoff/kit/sleep358uv (rsn-358u kit v2, reviewed by the Thread manager 13:27 UTC) for rsn-358t v3: 8 graded runs, two
# checkpoints each (final.pt raw, graded; final-ema.pt report only). Destroy only after a verified copy, else stop.
A=artifacts/claude-rsn358t-20260926
LABEL=claude-sleep-358t3
G=${G358V:-$HOME/premonition-watch/rsn358t3-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MP=${MP358:-$HOME/premonition-models/rsn358t3}
VAST=${VAST358:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM358:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYM358:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEY358:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it
QUERY="gpu_name=RTX_5090 num_gpus=1 reliability>=0.98 disk_space>=40 cpu_cores_effective>=16 cuda_max_good>=12.8 inet_down>=200 rentable=true"
MAXDPH=0.65       # dollars per hour: offers above this are skipped (about 2 h must fit under the $1.45 stop)
CAP_STOP=1.45     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (cap $1.60)
TIME_CAP=12600    # seconds from the first rental (3 h 30 min): copy back, destroy, TIME-STOP
ORDER="loop-trm-s1 loop8-s1 loop-trm-s2 loop8-s2 loop-trm-s3 loop8-s3 loop-trm-s4 loop8-s4"   # graded only; loop8-trm (report only) is not run on the rental
CKPTS="final.pt final-ema.pt"
EXPECT="train_log.jsonl train_summary.json tests.json tests-ema.json"   # files every run that did not die must bring back
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
#   copy_back runs  -> also: SEAL-run arrived, and each of the 8 runs has a sealed final.pt whose Mac copy in $MP matches
#                      SEAL-run (both checkpoints) and every EXPECT file arrived, or drive.sh recorded it as DIED (no final.pt)
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
    for f in $EXPECT; do [ -s "$G/out/W/$R/$f" ] || { log "$R/$f: expected file missing"; bad=1; }; done
  done
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: not every run is sealed and copied (or recorded as died)"; return 1; }
  log "COPY-CHECK: all 8 runs accounted for (both checkpoints)"; return 0
}
