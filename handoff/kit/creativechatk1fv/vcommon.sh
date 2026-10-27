# k1f vast kit, shared Mac-side helpers (Creative answers in chat thread, 2026-09-27). Sourced by vstart.sh, vguard.sh, vcollect.sh.
# bash 3.2 safe (macOS). The vast key is never read or printed here: the vastai CLI reads its own config.
# Built from handoff/kit/sleep358sv (the 358t v3 / 358u v2 kit the Thread manager reviewed). Changes: this job's paths and
# files, the adapter fetched from BensPC before any rental, GPU RAM checked in MB, and an estimate x $/h fit check.
# k1f is eval only (no training, no weights to bring back): the registered k1f run (PASSMARKS-k1f.md, ADDENDUM-2-vast.md).
A=artifacts/claude-k1f-20260926
LABEL=claude-creativechat-k1fv
G=${GK1F:-$HOME/premonition-watch/k1f-vast}   # Mac-only state (rentals, ssh host, guard log, copied-back files); never pushed
VAST=${VASTK1F:-vastai}
# Mac python: plain python3 under this bash can be a broken x86 binary, so use uv's 3.12 (as rent-rv390b does)
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYMK1F:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYMK1F:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
PYJ="$PYM -c"
KEY=${KEYK1F:-$HOME/.ssh/id_ed25519}
BSSH=${BSSHK1F:-ssh}   # how the Mac reaches BensPC (host alias benspc in ~/.ssh/config)
BSCP=${BSCPK1F:-scp}
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime   # eval only: the image's torch stays (330-rent-kit TORCH VERSION rule); recorded
# Any single-GPU card (Ben 14:05 UTC: "use cheap gpus, whatever gives most tflops/$/hr"), ranked by vast's TFLOPS per $/h.
# Needs: >= 24000 MB GPU RAM, checked client-side in MB (k1c's five arms at once peaked at 7237 MiB on a 5090; on a card
# under 30000 MiB drive.sh runs K, F, T first and Q, L after them, as rent-k1f said for a 4090), compute capability >= 8.0,
# a CUDA 12.8 driver for the image's cu128 torch, >= 8 CPU cores, 60 GB disk (four models and the image).
MINRAM_MB=24000
QUERY="num_gpus=1 gpu_ram>=24 compute_cap>=800 reliability>=0.98 disk_space>=60 cpu_cores_effective>=8 cuda_max_good>=12.8 inet_down>=200 rentable=true"
TF5090=104.8      # vast's listed TFLOPS for an RTX 5090 (the card the estimate and time cap are set for); logged beside the chosen card's
MAXDPH=0.60       # dollars per hour: offers above this are skipped
CAP_STOP=1.50     # dollars, all rentals of this task together: copy back, destroy, BUDGET-STOP (under the Director's $4 per-job cap)
EST_H=0.75        # hours on a 5090 for the whole rental (k1c: 5 arms x 2 panels plus setup took about 0.52 h on a 5090)
FIT=0.8           # fit check: EST_H x (5090 TFLOPS / card TFLOPS, never below 1) x $/h must be <= FIT x CAP_STOP
BASE_TIME=7200    # seconds from the first rental on a 5090 (2 h); vstart scales it by 5090 TFLOPS / chosen TFLOPS (never below 1x)
TIME_CAP=$BASE_TIME
BENSPC_AD=C:/Users/benja/lis301/work/e2e02c/tree/artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt
AD_SHA=a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5
S122_SHA=5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25
# the tree paths of rent-k1f / k1f-benspc2 step 1, plus this kit's box/
TREE="scripts design/v3/60-listener artifacts/claude-gram360-20260925 artifacts/claude-relationtable-20260922 artifacts/claude-table237-20260922 artifacts/fable-abstain76-20260921 artifacts/fable-self122-20260922 artifacts/fable-self127-20260922 artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt artifacts/claude-k1c-20260926/JUDGE-k1c.md artifacts/claude-k1f-20260926 artifacts/claude-k1fpanel-20260926 artifacts/claude-k1a-dev-20260926 handoff/kit/creativechatk1fv/box"
ARMS="F K T Q L"
# files a DONE rental must bring back (registered step 6), relative to /root/r
EXPECT="outF/creative_F.jsonl outF/creative_K.jsonl outF/creative_T.jsonl outF/creative_Q.jsonl outF/creative_L.jsonl outF/creative_judge.jsonl outF/creative_key.json outF/creative_judge_u.jsonl outF/creative_key_u.json outF/summary_creative.json outF/grammar_creative_F.jsonl outF/drafts_K.jsonl outF/drafts_F.jsonl outF/drafts_judge.jsonl outF/drafts_key.json W/logF.txt W/logK.txt W/logT.txt W/logQ.txt W/logL.txt W/logdevF.txt devk1f/creative_F.jsonl W/report.txt W/score.txt W/dedupe.txt W/draftpacket.txt"
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
# Copy the rental's W, outF and devk1f folders and drive.log back to $G/out, checked file by file against a sha256
# manifest made on the rental.
#   copy_back logs -> ok when every manifest file arrived and matches
#   copy_back runs -> also: when drive.sh ended DONE, every EXPECT file arrived non-empty
#                     (when it ended FAILED, what exists is all there is; the manifest check is enough)
# Returns 0 only when the check passes; the caller destroys only then.
copy_back() {
  mkdir -p "$G/out"; [ -f "$G/out/W/MANIFEST.sha256" ] && mv "$G/out/W/MANIFEST.sha256" "$G/out/W/MANIFEST.sha256.prev-$(date +%s)"
  $SS 'cd /root/r && mkdir -p W && find W outF devk1f drive.log -type f ! -name MANIFEST.sha256 2>/dev/null | sort | while IFS= read -r f; do sha256sum "$f"; done > W/MANIFEST.sha256 && tar -cf - W $(ls -d outF devk1f drive.log 2>/dev/null)' < /dev/null 2>> "$G/log.txt" | tar -x -C "$G/out" 2>> "$G/log.txt"
  M=$G/out/W/MANIFEST.sha256
  [ -s "$M" ] || { log "COPY-CHECK FAIL: no manifest came back"; return 1; }
  nm=$(wc -l < "$M" | tr -d ' '); nok=$(cd "$G/out" && shasum -a 256 -c W/MANIFEST.sha256 2>/dev/null | grep -c ': OK$')
  [ "$nm" = "$nok" ] || { log "COPY-CHECK FAIL: $nok of $nm files match the rental's manifest"; return 1; }
  log "COPY-CHECK: $nok of $nm files arrived and match the rental's manifest"
  [ "${1:-runs}" = logs ] && return 0
  tail -1 "$G/out/W/drive-state.txt" 2>/dev/null | grep -q ' DONE$' || { log "COPY-CHECK: drive.sh did not end DONE ($(tail -1 "$G/out/W/drive-state.txt" 2>/dev/null)); what exists is copied"; return 0; }
  bad=0; for f in $EXPECT; do [ -s "$G/out/$f" ] || { log "$f: expected file missing or empty"; bad=1; }; done
  [ $bad = 0 ] || { log "COPY-CHECK FAIL: a DONE rental is missing an expected file"; return 1; }
  log "COPY-CHECK: all $(echo $EXPECT | wc -w | tr -d ' ') expected files are here"; return 0
}
