# rsn-358u2 vast kit, shared Mac-side helpers (a stand-in chat for the stopped sleep research thread, 2026-09-28). Sourced by
# vstart.sh, vguard.sh, vcollect.sh. Copy of handoff/kit/sleep358uv/vcommon.sh (358u kit v2) for the loop-only re-run of rsn-358u
# (seeds 13-16, 358u's sealed code and settings unchanged; artifacts/claude-rsn358u2-20260928/PLAN.md). Kit changes only:
#   - the 4 loop runs only, and this re-run's own folder, label, Mac state folder and weights folder;
#   - ssh wait 15 min per new host, not 8 (358u's first 2 hosts stayed "loading" for 8 min);
#   - copy-back: the small files come in one tar (tried up to 3 times), and each final.pt comes one file at a time through a
#     tmp file, kept only if its sha256 matches both the rental's manifest and SEAL-run, up to 3 tries per file (358u's one big
#     tar broke on a broken pipe at 77 of 78 files); no `timeout` command (the Mac has none: rent358u-4c-recopy's copies all
#     came back empty);
#   - money stop $2.50 (cap $3) and time stop 3 h 30 min, for 4 runs instead of 8.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
A=artifacts/claude-rsn358u2-20260928    # this re-run's records (PLAN.md, SEAL-run, runs/, run-vast/)
AU=artifacts/claude-rsn358u-20260927    # 358u's sealed code seal and marks (read only; drive.sh checks SEAL-code 20/20 there)
LABEL=claude-sleep-358u2
G=${G358V:-$HOME/premonition-watch/rsn358u2-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
MP=${MP358:-$HOME/premonition-models/rsn358u2}      # the 4 re-run loop final.pt (weights never go to git)
VAST=${VAST358:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYM358:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYM358:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEY358:-$HOME/.ssh/id_ed25519}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # base image only; drive.sh pins torch 2.11.0+cu128 inside it
QUERY="gpu_name=RTX_5090 num_gpus=1 reliability>=0.98 disk_space>=40 cpu_cores_effective>=16 cuda_max_good>=12.8 inet_down>=200 rentable=true"
CAP_STOP=2.50     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (cap $3)
TIME_CAP=12600    # seconds from the first rental (3 h 30 min): copy back, destroy, TIME-STOP
SSH_WAIT=90       # x 10 s = 15 min for a new host to answer ssh
ORDER="loop-s13 loop-s14 loop-s15 loop-s16"
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
#   copy_back logs  -> ok when every manifest file except the final.pt files arrived and matches
#   copy_back runs  -> also: SEAL-run arrived, and each of the 4 runs has a sealed final.pt that was fetched one file at a
#                      time into $MP and matches both the manifest and SEAL-run, or drive.sh recorded it as DIED (no final.pt)
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out/W" "$MP"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && find W drive.log -type f ! -name MANIFEST.sha256 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256' < /dev/null 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256; MS=$G/out/W/MANIFEST.small.sha256
  for t in 1 2 3; do
    $SS 'cd /root/r && find W drive.log -type f ! -name final.pt 2>/dev/null | tar -cf - -T -' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
    [ -s "$M" ] || { log "copy-back try $t: no manifest came back"; sleep 10; continue; }
    grep -v '/final\.pt$' "$M" > "$MS"; nm=$(wc -l < "$MS" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c "$MS" 2>/dev/null | grep -c ': OK$')
    [ "$nm" = "$nok" ] && break; log "copy-back try $t: $nok of $nm small files match the rental's manifest"; sleep 10
  done
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm small files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm small files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  S=$G/out/W/SEAL-run.sha256.txt; bad=0
  for R in $ORDER; do
    sha=$(awk -v f="$R/final.pt" '$2==f {print $1}' "$S" 2>/dev/null); msha=$(awk -v f="W/$R/final.pt" '$2==f {print $1}' "$M")
    if [ -n "$sha" ]; then mkdir -p "$MP/$R"
      [ "$msha" = "$sha" ] || { log "$R: SEAL-run $sha and the rental's manifest '${msha:-none}' differ"; bad=1; continue; }
      m=$(shasum -a 256 "$MP/$R/final.pt" 2>/dev/null | awk '{print $1}')
      if [ "$m" = "$sha" ] || fetch1 "W/$R/final.pt" "$MP/$R/final.pt" "$sha"; then log "$R: sealed, Mac copy $MP/$R/final.pt sha256 ok"
      else log "$R: Mac copy of final.pt does not match SEAL-run $sha after 3 tries"; bad=1; fi
    elif grep -q " DIED $R " "$G/out/W/drive-state.txt" 2>/dev/null; then log "$R: DIED on the rental (no final.pt), recorded"
    else log "$R: no sealed final.pt and no DIED record"; bad=1; fi
  done
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: not every run is sealed and copied (or recorded as died)"; return 1; }
  log "COPY-CHECK: all 4 runs accounted for"; return 0
}
