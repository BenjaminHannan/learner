# PC-queue job 8aPTC3S on one rented RTX 4090 (written 2026-10-13). Runs on a Vast GPU box as `bash -c "export NAME=VALUE ...; <this file>" cio`, like custom_io/box/box.sh
# (branch claude/project-thread-x2cm2v). It keeps box.sh's say()/die()/emit() conventions and its RBEGIN|R||REND log protocol, so vast.py collect / collectck read it.
#
# THE JOB (PC queue file results/8a-g/pc-job-cards/ptc/8aPTC3S-pc.txt): arm PTC = the plain 3M step model trained with the calculator (calc_train), seed 400, rung 3M,
# 24,000 updates, accum PTC=16, eg_embed (frozen EmbeddingGemma 2 front), caps_b3s.json, long-chunk pool p10-rung30-s400-a64-L. Nothing is decided here: the queue file's two
# job lines (the g8a-data line and the g8a line) become command lines through custom_io.local_runner's OWN parse_queue() and command(), imported from the assembled tree, so the
# flags are the ones the PC runner would pass (only {WORK} and the output folders differ). Code = custom_io at 74d6e92c75 (src-b3g2) + the six PTC overlay files of branch
# claude/project-thread-yha868 at c2bf1a71c7, assembled and sha256-checked the way install_ptc.ps1 does (every package file, base and overlay), then ptccheck.py on the CPU.
#
# STAGES (printed as `=== STAGE name time`): setup (packages) -> code (fetch by sha, assemble, verify, ptccheck, freeze) -> gemma (EmbeddingGemma 2 + `eg check cuda`)
#   -> data (custom_io.g8a.get_data, the PC's g8a-data line) -> skills (200k curriculum, hash checked) -> train (the job; pool, caps and training all happen inside it) -> result.
# MARKERS in the container log: CIO START, STAGE ..., TICK ..., GUARD ..., CODE-ID ..., CMD ..., PTC3S TRAIN START, PTC3S JOB END rc=N, RESULT-SUMMARY ..., RBEGIN/R|/REND (the
#   result tarball, name 8aPTC3S-3M-s400), PTC3S RESULT PRINTED, part ckN ..., CKFULL|, CKDONE|N, CIO DONE, CIO-FAIL <why> (then the box waits FAIL_SLEEP: read it, destroy it).
# No credential is on the box and nothing listens. GitHub (public repo) and Hugging Face (ungated model and dataset) are reached anonymously.
#
# ENV (vast.py create --env "NAME=VALUE ..."; no spaces inside a value). The first five are box.sh's interface:
#   MAXH        hard stop, hours since the script started (setup included); kills the running step's process group; default 6. train.py saves nothing before its end
#               (no resume), so a MAXH stop in training means no result: it is a cost cap, not a plan. Keep MAXH x (dollars per hour) <= 4.
#   END_SLEEP   seconds the box stays up after everything is printed (billed; destroy it as soon as you have collected); default 600.
#   FAIL_SLEEP  seconds the box stays up after a CIO-FAIL so the log can be read (billed); default 1800.
#   TFVER       transformers version; default 5.19.0 (the PC's; EmbeddingGemma 2 needs >= 5.19).
#   EG          must be 1 (default 1): the job has eg_embed. EG=0 refuses.
#   DPH, PROJ_CAP_USD, GUARD_STEP, EXTRA_H   speed guard. DPH = dollars per hour of this offer (dph_total from search; 0 = guard off). At the first train line with
#               step >= GUARD_STEP (default 1000) it projects total cost = (hours up + remaining updates at the measured speed + EXTRA_H final-evaluation hours) x DPH; above
#               PROJ_CAP_USD (default 4.0) it prints GUARD STOP and kills the job. EXTRA_H default 0.5 (a guess, untested).
#   EXPORT_CK   1 (default): print checkpoint.pt (about 16 MB) in 3 MB parts after the result, PACE seconds apart (100), CK_ROUNDS times (3: a collectck started up to 15 minutes after the result line still gets every part; each round is 5 parts = about 8 minutes of box time).
#   PTC_DRY, PTC_DRY_EXTRA, PTC_DRY_EG, STOP_AFTER, J, TICK_EVERY   CPU dry-run hooks (DRYRUN.md). Never set on Vast. J is the work root (default /job).
set -u
J=${J:-/job}; mkdir -p $J/out $J/res $J/state $J/w $J/work; cd $J || exit 1
R=https://github.com/BenjaminHannan/learner
BASE_SHA=74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6      # custom_io of src-b3g2 (branch claude/project-thread-emwjvn)
OVL_SHA=c2bf1a71c7386396a087e5993a3de4ce8873925d       # branch claude/project-thread-yha868: the PTC package
OVL_DIR=results/8a-g/pc-job-cards/ptc
DP_SHA=3d0afbeadd5f1775c7c92195348bab6f66da767d        # branch claude/data-pool-8b (cloze_long.py's commit; the manifests, web_slice.py and the panel index are the same files as at 12d30d0ce9)
OWN_SHA=8d012f1f97bd8203b15e88e369dc856721e13e6a       # branch claude/8a-own-data
CUR_SHA=57c45293fe7158aae92d017e6a9bd2d87e29dcdf       # branch claude/project-thread-y0sxwe (skills_curriculum; its 200k manifest decides, as in box.sh)
MANIFEST_SHA=e8f32daf44d562910db6700bd73b64c720beb6e5c1c5a9a115e8c8880f0763b0    # data_pool/built/own72_MANIFEST.json (the PC's --expect-manifest-sha)
CLOZE_SHA=@@CLOZE_SHA@@       # data_pool/cloze_long.py at 3d0afbeadd
CAPS_PY_SHA=@@CAPS_PY_SHA@@   # g8a/caps.py of 74d6e92c75 (install_ptc.ps1's $CAPS)
CAPS_B3S_SHA=@@CAPS_B3S_SHA@@ # g8a/caps_b3s.json of 74d6e92c75 (the PC's work\b3-inputs copy)
EG2_ST_SHA=197a32965d4b1105faf060417baa899e193fb73cd401f42ec9295234d5553d79       # model.safetensors of google/embeddinggemma-2 at 914f7f89 (Hugging Face API lfs oid)
MAXH=${MAXH:-6}; END_SLEEP=${END_SLEEP:-600}; FAIL_SLEEP=${FAIL_SLEEP:-1800}; TFVER=${TFVER:-5.19.0}; EG=${EG:-1}
DPH=${DPH:-0}; PROJ_CAP_USD=${PROJ_CAP_USD:-4.0}; GUARD_STEP=${GUARD_STEP:-1000}; EXTRA_H=${EXTRA_H:-0.5}; STEPS=24000
EXPORT_CK=${EXPORT_CK:-1}; PACE=${PACE:-100}; CK_ROUNDS=${CK_ROUNDS:-3}; TICK_EVERY=${TICK_EVERY:-180}
PTC_DRY=${PTC_DRY:-0}; PTC_DRY_EXTRA=${PTC_DRY_EXTRA:-[]}; PTC_DRY_EG=${PTC_DRY_EG:-0}; STOP_AFTER=${STOP_AFTER:-}
T0=${T0:-$(date +%s)}
W=$J/work; D=$W/data; DB=$W/data_big          # the PC's WORK, with its folder names
S=$J/src-ptc                                   # = the PC's src-ptc (custom_io inside)
QNAME=8aPTC3S-pc; RUN=8aPTC3S-3M-s400
RES=$W/results/$QNAME; O=$RES/$RUN             # = WORK\results\8aPTC3S-pc\8aPTC3S-3M-s400
OV=$J/ovl/$OVL_DIR; B=$J/base/custom_io
WATCH=
say() { echo "=== $* $(date -u +%FT%TZ)"; }
stage() { echo "$1" > $J/state/stage; echo "=== STAGE $1 $(date -u +%FT%TZ)"; }
sha() { sha256sum "$1" 2>/dev/null | cut -c1-64; }
# a git or pip step that cannot hang the box silently: timeout + retries + a visible line per failure
retry() { n=$1; shift; for k in $(seq 1 $n); do timeout -k 30 900 "$@" && return 0; say "retry $k/$n failed: $*"; sleep 20; done; return 1; }
fetch_sha() {   # dir sha sparse-dirs... : exactly that commit of the repo, blobs on demand (no dirs = the root files only)
  d=$1; s=$2; shift 2
  rm -rf $d; mkdir -p $d; git -C $d init -q && git -C $d remote add origin $R || return 1
  if [ $# -gt 0 ]; then git -C $d sparse-checkout init --cone && git -C $d sparse-checkout set "$@" || return 1; fi
  retry 4 git -C $d fetch -q --depth 1 --filter=blob:none origin $s && retry 3 git -C $d checkout -q FETCH_HEAD && [ "$(git -C $d rev-parse HEAD)" = "$s" ]
}
kill_cur() {    # stop the running step: its whole process group (runp keeps the leader's pid in state/cur.pid)
  p=$(cat $J/state/cur.pid 2>/dev/null); [ -n "$p" ] || return 0
  kill -TERM -- -$p 2>/dev/null; sleep 15; kill -KILL -- -$p 2>/dev/null; return 0
}
runp() {        # LOG DIR cmd... : run cmd in DIR in its own session, output appended to LOG; MAXH / the guard stop it through kill_cur; returns its status
  lf=$1; dir=$2; shift 2
  echo "$lf" > $J/state/curlog
  [ -e $J/state/maxh ] && { echo "MAXH already reached: $* not started" >> "$lf"; return 99; }
  setsid -w bash -c 'echo $$ > "$0"; cd "$1" || exit 1; shift; exec "$@"' $J/state/cur.pid "$dir" "$@" >> "$lf" 2>&1 &
  rp=$!; wait $rp; rc=$?
  rm -f $J/state/cur.pid
  return $rc
}
write_guard() { cat > $J/guard.py <<'PY'
import json, sys
log, t0, now, dph, cap, gstep, steps, extra, maxh = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9])
line = None
try:
    for ln in open(log, errors='replace'):
        if '"event": "train"' not in ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get('step', 0) >= gstep:
            line = e
            break
except OSError:
    pass
if line is None:
    sys.exit(4)
spu = line['elapsed'] / line['step']                              # seconds per update, from the start of training
up_h = (now - t0) / 3600                                          # hours the box has been up (setup, data and pool included: already paid)
total_h = up_h + (steps - line['step']) * spu / 3600 + extra
usd = total_h * dph
print('GUARD step=%d sec_per_update=%.3f train_total_h=%.2f up_h=%.2f projected_total_h=%.2f dph=%.3f projected_usd=%.2f cap_usd=%.2f' % (
    line['step'], spu, spu * steps / 3600, up_h, total_h, dph, usd, cap), flush=True)
if usd > cap:
    print('GUARD STOP projected %.2f USD > cap %.2f USD' % (usd, cap), flush=True)
    sys.exit(3)
if maxh and total_h > maxh:             # MAXH would kill the job before it ends, and training saves nothing before its end: stop now, not hours later
    print('GUARD STOP projected %.2f h > MAXH %.2f h' % (total_h, maxh), flush=True)
    sys.exit(3)
PY
}
tick() {        # one TICK line: stage, uptime, training progress (or the current step's log size and last line), folder sizes, disk, GPU
  now=$(date +%s); tl=$(grep -h '"event": "train"' $O/PTC/stdout.txt 2>/dev/null | tail -1)
  prog=$(echo "$tl" | sed -n 's/.*"step": \([0-9]*\), "loss": \([0-9.eE+-]*\), .*"elapsed": \([0-9.]*\).*/step=\1 loss=\2 train_elapsed_s=\3/p')
  if [ -n "$prog" ]; then      # projection from the speed so far: hours of training in all, and (with DPH) dollars for the whole box = (hours up + updates left at this speed + EXTRA_H) x DPH
    prog="$prog $(echo "$prog" | tr '=' ' ' | awk -v n=$STEPS -v now=$now -v t0=$T0 -v dph=$DPH -v x=$EXTRA_H '{s=$2; e=$6; if (s > 0) printf "proj_train_h=%.2f proj_usd=%.2f", e/s*n/3600, ((now-t0)/3600 + (n-s)*e/s/3600 + x)*dph}')"
  fi
  if [ -z "$prog" ]; then lf=$(cat $J/state/curlog 2>/dev/null); prog="log=$(basename "$lf" 2>/dev/null) bytes=$(stat -c %s "$lf" 2>/dev/null) last=$(tail -n 1 "$lf" 2>/dev/null | tr -c '[:print:]' ' ' | cut -c1-110)"; fi
  echo "TICK at=$(date -u +%FT%TZ) stage=$(cat $J/state/stage 2>/dev/null) up_min=$(( (now - T0) / 60 )) $prog | mb data8a=$(du -sm $W/data8a 2>/dev/null | cut -f1) skills=$(du -sm $D 2>/dev/null | cut -f1) pools=$(du -sm $W/g8a 2>/dev/null | cut -f1) free=$(df -m $J | awk 'NR==2{print $4}') ram_avail=$(free -m | awk '/^Mem:/{print $7}') | gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader 2>/dev/null)"
}
watch_loop() {  # background: MAXH, the speed guard (once, at GUARD_STEP), a TICK line every TICK_EVERY seconds
  last=0; maxs=$(awk "BEGIN{print int($MAXH*3600)}")
  while true; do
    now=$(date +%s)
    if [ "$MAXH" != 0 ] && [ $((now - T0)) -ge $maxs ]; then      # from now on every step that is running is killed, every 20 s, and runp starts no new one
      [ -e $J/state/maxh ] || say "CIO MAXH $MAXH h reached: stopping the running step (training saves nothing before its end)"; touch $J/state/maxh; kill_cur; sleep 20; continue; fi
    if [ "$DPH" != 0 ] && [ ! -f $J/state/guard_done ] && [ -f $O/PTC/stdout.txt ]; then
      python $J/guard.py $O/PTC/stdout.txt $T0 $now $DPH $PROJ_CAP_USD $GUARD_STEP $STEPS $EXTRA_H $MAXH > $J/state/guard.out 2>&1; g=$?
      { [ $g = 0 ] || [ $g = 3 ]; } && { cat $J/state/guard.out; touch $J/state/guard_done; }
      [ $g = 3 ] && { touch $J/state/guard_stop; kill_cur; return 0; }
    fi
    if [ $((now - last)) -ge $TICK_EVERY ]; then last=$now; tick; fi
    sleep 20
  done
}
emit() {        # name dir : the folder as a tar.gz (no *.pt, no stdout.txt: each gets an events file and a tail file) printed as RBEGIN / R| / REND lines with a sha256
  n=$1; d=$2; T=$J/res/$n.tgz
  (cd $d && find . -name stdout.txt | while read -r f; do
     grep -E '"event"|Traceback|Error|error|RESULT' "$f" | cut -c1-4000 > "${f%.txt}.events.txt"; tail -n 100 "$f" | cut -c1-600 > "${f%.txt}.tail.txt"; done)
  tar -czf $T --exclude='*.pt' --exclude=stdout.txt -C "$(dirname "$d")" "$(basename "$d")" 2>/dev/null
  echo "RBEGIN|$n|$(sha $T)|$(stat -c %s $T)"; base64 -w 300 $T | sed "s/^/R|$n|/"; echo "REND|$n"
}
boxfiles() {    # the setup logs and pins travel with the result, in RUN/box/
  mkdir -p $O/box; cp $J/out/*.log $J/out/*.txt $J/out/*.sha256 $J/state/guard.out $J/state/cmd.*.txt $S/PTC-SETUP-OK.txt $O/box/ 2>/dev/null
  { date -u +%FT%TZ; uname -a; python --version; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv 2>/dev/null; } > $O/box/box.txt 2>&1
}
summary() {     # one line from RESULT.json (the acceptance fields of RUNBOOK.md); status 0 only if the job and the PTC arm say ok and the final evaluation is in
  python - $O <<'PY'
import json, os, sys
o = sys.argv[1]
def load(p):
    try:
        return json.load(open(os.path.join(o, p)))
    except Exception:
        return {}
r, j = load('PTC/RESULT.json'), load('RESULT.json')
ch = r.get('cap_hits') or {}
print('RESULT-SUMMARY', json.dumps(dict(job_status=j.get('status'), arm_status=r.get('status'), steps=r.get('steps'), n_params=r.get('n_params'), steps_per_s=round(r.get('steps_per_s') or 0, 3),
      train_s=round(r.get('train_s') or 0), wall_s=round(r.get('wall_s') or 0), peak_mem_mib=r.get('peak_mem_mib'), cap_total=ch.get('total'), calc_mismatch=ch.get('calc_mismatch'),
      calc_rows=ch.get('calc_rows'), calc_forced=ch.get('calc_forced'), final_eval=bool(r.get('final_eval')), chain5='chain5' in r, lesions=sorted((r.get('lesions') or {}).keys()))))
sys.exit(0 if j.get('status') == 'ok' and r.get('status') == 'ok' and r.get('final_eval') else 1)
PY
}
ck_export() {   # checkpoint.pt (about 16 MB; Gemma is not in it) through the log: tar.gz, 3 MB parts, one part every PACE seconds, CK_ROUNDS times; vast.py collectck reassembles
  c=$O/PTC/checkpoint.pt
  [ -f $c ] || { echo "CKDONE|0"; return 0; }
  T=$J/res/ck-PTC.tgz; tar -czf $T -C $RES $RUN/PTC/checkpoint.pt || { echo "CKDONE|0"; return 0; }
  full=$(sha $T); rm -f $J/res/ck-PTC.part.*; split -b 3000000 -d -a 3 $T $J/res/ck-PTC.part.
  n=$(ls $J/res/ck-PTC.part.* | wc -l); N=0
  for rd in $(seq 1 $CK_ROUNDS); do
    echo "CKFULL|$RUN/PTC|$full|$n"
    for p in $(ls $J/res/ck-PTC.part.* | sort); do
      k=$((10#${p##*.})); N=$((N + 1))
      echo "RBEGIN|ck$N|$(sha $p)|$(stat -c %s $p)|$RUN/PTC|$k|$n"; base64 -w 480 $p | sed "s/^/R|ck$N|/"; echo "REND|ck$N"
      echo "part ck$N $RUN/PTC $k/$n round $rd"; [ $N -lt $((n * CK_ROUNDS)) ] && sleep $PACE
    done
  done
  echo "CKDONE|$N"
}
die() {
  say "CIO-FAIL $*"; stage failed
  [ -n "$WATCH" ] && kill $WATCH 2>/dev/null
  lf=$(cat $J/state/curlog 2>/dev/null); [ -f "$lf" ] && { echo "--- tail of $lf"; grep -v '^R|' "$lf" | tail -n 15 | cut -c1-400; }
  if [ -d $O ]; then boxfiles; emit $RUN $O; [ "$EXPORT_CK" = 1 ] && [ -f $O/PTC/checkpoint.pt ] && { ck_export; emit $RUN $O; }; fi      # a finished training whose evaluation died still gives its checkpoint
  sleep $FAIL_SLEEP; exit 1
}
stop_after() { [ "$STOP_AFTER" = "$1" ] || return 0; say "STOP-AFTER $1 (dry-run hook)"; [ -n "$WATCH" ] && kill $WATCH 2>/dev/null; exit 0; }

# ---- 1. box + packages
say "CIO START"; stage setup
say "PTC3S START job=$RUN maxh=$MAXH dph=$DPH guard=$([ "$DPH" != 0 ] && echo on || echo OFF-set-DPH) cap_usd=$PROJ_CAP_USD tf=$TFVER eg=$EG dry=$PTC_DRY base=$BASE_SHA overlay=$OVL_SHA"
[ "$EG" = 1 ] || die "EG=1 is required: the job has eg_embed"
if [ "$DPH" != 0 ] && [ "$MAXH" != 0 ] && awk "BEGIN{exit !($MAXH * $DPH > $PROJ_CAP_USD + 0.5)}"; then say "WARN MAXH x DPH = $(awk "BEGIN{print $MAXH * $DPH}") USD is above the cap $PROJ_CAP_USD USD plus 0.5: lower MAXH"; fi
[ "$PTC_DRY" = 1 ] || nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
free -g | head -2; nproc; df -h $J | tail -1
[ "$PTC_DRY" = 1 ] || [ "$(df -m $J | awk 'NR==2{print $4}')" -ge 20000 ] || die "less than 20 GB free disk on $J (the run needs about 15 GB)"
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || die git
git config --global core.autocrlf false
write_guard
watch_loop & WATCH=$!
PIP_BREAK_SYSTEM_PACKAGES=1 retry 3 pip install -q --break-system-packages "transformers==$TFVER" "safetensors==0.8.0" "tokenizers==0.23.2" accelerate numpy pyarrow huggingface_hub > $J/out/pip.log 2>&1 || { tail -3 $J/out/pip.log; die pip; }
python - $TFVER <<'PY' > $J/out/versions.txt 2>&1 || { cat $J/out/versions.txt; die versions; }
import importlib.metadata as m, sys
want = {'transformers': sys.argv[1], 'safetensors': '0.8.0', 'tokenizers': '0.23.2'}     # the PC's: transformers 5.19.0, tokenizers 0.23.2, safetensors 0.8.0
got = {k: m.version(k) for k in ('transformers', 'safetensors', 'tokenizers', 'huggingface_hub', 'numpy', 'pyarrow', 'accelerate')}
import torch
got['torch'] = torch.__version__ + ' cuda ' + str(torch.version.cuda)
print('versions', got)
bad = {k: (got[k], v) for k, v in want.items() if got[k] != v}
assert not bad, 'version mismatch (got, want): %s' % bad
PY
cat $J/out/versions.txt
if [ "$PTC_DRY" != 1 ]; then python -c "import torch; assert torch.cuda.is_available(), 'no cuda'; print('gpu', torch.cuda.get_device_name(0), 'bf16', torch.cuda.is_bf16_supported())" || die torch-cuda; fi
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 PYTHONUTF8=1
stop_after setup

# ---- 2. code: base commit, PTC package, every hash checked as install_ptc.ps1 does, ptccheck on the CPU, a frozen copy as local_runner makes
stage code
fetch_sha $J/base $BASE_SHA custom_io || die fetch-base
fetch_sha $J/ovl $OVL_SHA $OVL_DIR || die fetch-overlay
# the package files (README.md tables and install_ptc.ps1): sha256 of the file here
while read -r f h; do [ "$(sha $OV/$f)" = "$h" ] || die "package file $f is not the pinned one (got $(sha $OV/$f))"; done <<'PKG'
@@PKG_PINS@@
PKG
# the six files PTC replaces: file here, path under custom_io, sha256 at 74d6e92c75 (- = none, a new file), sha256 of the PTC file
while read -r f dest old new; do
  [ "$(sha $OV/$f)" = "$new" ] || die "$f here is not the PTC file (got $(sha $OV/$f))"
  [ "$old" = - ] || [ "$(sha $B/$dest)" = "$old" ] || die "$dest in the base commit is not 74d6e92c75's (got $(sha $B/$dest))"
  for h in $new $old; do [ "$h" = - ] && continue; grep -qi $h $OV/README.md || die "README.md does not list $h"; grep -qi $h $OV/install_ptc.ps1 || die "install_ptc.ps1 does not list $h"; done
done <<'OVERLAYS'
@@OVERLAY_PINS@@
OVERLAYS
[ "$(sha $B/g8a/caps.py)" = "$CAPS_PY_SHA" ] || die "base g8a/caps.py is not 74d6e92c75's (got $(sha $B/g8a/caps.py))"
[ "$(sha $B/g8a/caps_b3s.json)" = "$CAPS_B3S_SHA" ] || die "base g8a/caps_b3s.json is not 74d6e92c75's (got $(sha $B/g8a/caps_b3s.json))"
grep -qi $CAPS_PY_SHA $OV/install_ptc.ps1 || die "install_ptc.ps1 does not list the caps.py hash"
# src-ptc = a copy of the base custom_io, checked again, then the six overlay files, checked again, then the two queue files
rm -rf $S; mkdir -p $S; cp -a $B $S/custom_io || die copy-base
[ "$(sha $S/custom_io/g8a/caps.py)" = "$CAPS_PY_SHA" ] || die "the copy of caps.py differs"
# PTC-SETUP-OK.txt in the format install_ptc.ps1 writes on the PC (upper-case hashes, backslash paths), so the two markers can be diffed
{ echo "caps.py ${CAPS_PY_SHA^^} (src-b3g2's, unchanged)"; echo "base: src-b3g2 = custom_io at 74d6e92c75"; } > $S/PTC-SETUP-OK.txt
while read -r f dest old new; do
  [ "$old" = - ] || [ "$(sha $S/custom_io/$dest)" = "$old" ] || die "the copy of $dest differs from the base"
  cp $OV/$f $S/custom_io/$dest || die "cannot copy $f"
  [ "$(sha $S/custom_io/$dest)" = "$new" ] || die "$f did not copy to $dest"
  if [ "$old" = - ]; then echo "${dest//\//\\} ${new^^} (new)" >> $S/PTC-SETUP-OK.txt; else echo "${dest//\//\\} ${new^^} (was ${old^^})" >> $S/PTC-SETUP-OK.txt; fi
done <<'OVERLAYS'
@@OVERLAY_PINS@@
OVERLAYS
mkdir -p $S/custom_io/queue_local
for q in 8aPTC3S 8aPTC10S; do cp $OV/$q-pc.txt $S/custom_io/queue_local/$q-pc.txt; cmp -s $OV/$q-pc.txt $S/custom_io/queue_local/$q-pc.txt || die "$q-pc.txt did not copy"; done
say "src-ptc: base files and caps.py are 74d6e92c75's, the 6 PTC files and 2 queue files are in, all sha256 ok"
say "ptccheck on the CPU (about 2 minutes)"
for k in 1 2; do     # the check is deterministic, but one failure in about ten CPU runs was seen on the dry-run box (cause not found): one more try, and on a second failure the whole test output
  runp $J/out/ptccheck.log $S env CUDA_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python $OV/ptccheck.py $J/base
  rc=$?; tail -n 6 $J/out/ptccheck.log | cut -c1-300
  { [ $rc = 0 ] && tail -n 1 $J/out/ptccheck.log | grep -q 'PTC CPU CHECK OK'; } && break
  [ -e $J/state/maxh ] && die maxh
  if [ $k = 2 ]; then
    (cd $S && CUDA_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$S PTC_ORIG_TREE=$J/base python -m custom_io.tests.test_ptc 2>&1 | tail -n 40 | cut -c1-300; df -m $J /tmp | cat)
    die "ptccheck failed twice (rc $rc)"
  fi
  say "ptccheck try 1 failed (rc $rc), trying once more; disk: $(df -m $J /tmp | awk 'NR>1{printf "%s MB free on %s; ", $4, $6}')"
done
echo "queues 8aPTC3S and 8aPTC10S in custom_io\\queue_local; ptccheck ok (CPU); ptc3s_box.sh (Linux box, not install_ptc.ps1)" >> $S/PTC-SETUP-OK.txt
# the frozen copy local_runner makes (WORK/code/QUEUE-HASH, no results/, __pycache__, *.pt) and its hash: compare with the PC log's `code:` line
CODE_H=$(cd $S && python -c "from custom_io.local_runner import code_hash; print(code_hash())") || die code-hash
CODE=$W/code/$QNAME-$CODE_H
rm -rf $CODE; mkdir -p $CODE; (cd $S && tar -c --exclude=results --exclude=__pycache__ --exclude='*.pt' custom_io | tar -x -C $CODE) || die freeze
(cd $CODE && find custom_io -type f \( -name '*.py' -o -name '*.json' -o -name '*.txt' \) | sort | xargs sha256sum) > $J/out/code_files.sha256
# code_identity.py (the same file is in the kit folder; the PC runs it on WORK\code\8aPTC3S-pc-<hash>): sha256 of every .py/.json/.txt file with CRLF turned into LF, and a code hash that does not depend on line endings or on how the OS sorts paths
cat > $J/code_identity.py <<'PYID'
@@CODE_IDENTITY_PY@@
PYID
python -I $J/code_identity.py $CODE files > $J/out/code_files_lf.sha256 && python -I $J/code_identity.py $CODE hash > $J/out/code_hash_lf.txt && python -I $J/code_identity.py $CODE > $J/out/code_identity.txt || die code-identity
say "CODE-ID $QNAME-$CODE_H (PC: WORK\\code\\$QNAME-<same 10 hex>); code_identity.py (CRLF as LF): $(tr "\n" " " < $J/out/code_identity.txt); raw-bytes file list sha256 $(sha $J/out/code_files.sha256); caps.py $CAPS_PY_SHA"
# the two job lines as local_runner would run them (its parse_queue and command), plus its child environment
cat > $J/mkcmd.py <<'PY'
import json, os, shlex, sys
from pathlib import Path
from custom_io.local_runner import parse_queue, command, child_env, queue_env
queue, work, outroot, code, device, extra = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]), sys.argv[4], sys.argv[5], json.loads(sys.argv[6])
runs = parse_queue(queue, work)
assert [(r[0], r[1]) for r in runs] == [('8a-data', 'g8a-data'), ('8aPTC3S-3M-s400', 'g8a')], [(r[0], r[1]) for r in runs]
state = Path(os.environ['J']) / 'state'
for (name, kind, args, mem), fn in zip(runs, ('cmd.data', 'cmd.job')):
    out = outroot / name
    line = ' '.join(shlex.quote(c) for c in command(kind, args + (extra if kind == 'g8a' else []), work, out, device))
    (state / (fn + '.sh')).write_text('#!/bin/bash\ncd %s || exit 1\nexec %s\n' % (shlex.quote(code), line))
    (state / (fn + '.txt')).write_text(line + '\n')                      # what the runner writes as cmd.txt
    (state / (fn + '.mem')).write_text('%d\n' % mem)
    print('CMD', name, 'mem', mem, 'MiB:', line)
env = child_env(device)
(state / 'env.sh').write_text(''.join('export %s=%s\n' % (k, shlex.quote(v)) for k, v in sorted(env.items()) if os.environ.get(k) != v))
print('CHILD-ENV (added to the environment):', {k: v for k, v in sorted(env.items()) if os.environ.get(k) != v})
print('QUEUE-ENV (the PC\'s # ENV lines, Windows paths, not used here):', json.dumps(queue_env(queue)))
PY
# (the commands are always built for cuda: local_runner's command() adds --device cpu to EVERY line kind on cpu, which get_data rejects; the dry run gets --device cpu through PTC_DRY_EXTRA)
(cd $CODE && export J PYTHONPATH=$CODE && python $J/mkcmd.py $CODE/custom_io/queue_local/8aPTC3S-pc.txt $W $RES $CODE cuda "$PTC_DRY_EXTRA") > $J/out/mkcmd.log 2>&1 || { cat $J/out/mkcmd.log; die mkcmd; }
cut -c1-1500 $J/out/mkcmd.log
stop_after code

# ---- 3. EmbeddingGemma 2 (frozen), pinned revision, anonymous download with box.sh's retry loop, then its 3-vector check
stage gemma
if [ "$PTC_DRY" != 1 ] || [ "$PTC_DRY_EG" = 1 ]; then
  for k in 1 2 3 4 5 6; do   # anonymous Hugging Face downloads are rate limited per IP (a shared box IP can be out of requests): wait and retry
    runp $J/out/eg_dl.log $S python -c "from huggingface_hub import snapshot_download as s; from custom_io.models.eg import EG_ID, EG_REV; s(EG_ID, revision=EG_REV, local_dir='$J/eg2')" && break
    tail -2 $J/out/eg_dl.log; [ -e $J/state/maxh ] && die maxh; [ $k = 6 ] && die eg-download; say "eg download try $k failed, retrying in 4 min"; sleep 240
  done
  [ "$(sha $J/eg2/model.safetensors)" = "$EG2_ST_SHA" ] || die "EmbeddingGemma model.safetensors sha256 is $(sha $J/eg2/model.safetensors), not $EG2_ST_SHA"
  export CUSTOM_IO_EG2=$J/eg2
  EGDEV=cuda; [ "$PTC_DRY" = 1 ] && EGDEV=cpu
  runp $J/out/eg_check.log $CODE python -m custom_io.models.eg check $EGDEV; rc=$?; tail -n 4 $J/out/eg_check.log | cut -c1-400
  [ $rc = 0 ] || die eg-check
fi
stop_after gemma

# ---- 4. the PC's inputs under WORK/8a-inputs and WORK/b3-inputs, then its g8a-data line (get_data: own text, FineWeb-Edu shard 0, web slices hash-checked)
stage data
fetch_sha $W/8a-inputs/data-pool $DP_SHA data_pool/built data_pool/panels || die fetch-data-pool
fetch_sha $W/8a-inputs/own-data $OWN_SHA || die fetch-own-data
mkdir -p $W/b3-inputs; cp $W/8a-inputs/data-pool/data_pool/cloze_long.py $W/b3-inputs/cloze_long.py; cp $S/custom_io/g8a/caps_b3s.json $W/b3-inputs/caps_b3s.json
[ "$(sha $W/b3-inputs/cloze_long.py)" = "$CLOZE_SHA" ] || die "cloze_long.py is not the pinned one (got $(sha $W/b3-inputs/cloze_long.py))"
[ "$(sha $W/b3-inputs/caps_b3s.json)" = "$CAPS_B3S_SHA" ] || die "caps_b3s.json is not the pinned one"
[ "$(sha $W/8a-inputs/data-pool/data_pool/built/own72_MANIFEST.json)" = "$MANIFEST_SHA" ] || die own72-manifest
say "data branches fetched at $DP_SHA and $OWN_SHA; building the 8a data (FineWeb-Edu shard 0 is 2.15 GB; the slices must hash to the manifest)"
mkdir -p $RES/8a-data
for k in 1 2 3; do
  runp $J/out/get_data.log $CODE bash $J/state/cmd.data.sh && break
  tail -n 8 $J/out/get_data.log | cut -c1-400; [ -e $J/state/maxh ] && die maxh; [ $k = 3 ] && die get_data; say "get_data try $k failed, retrying in 3 min (it resumes)"; sleep 180
done
tail -n 3 $J/out/get_data.log | cut -c1-300
[ -f $W/data8a/READY.json ] && [ ! -f $W/data8a/REFUSED.txt ] || die "data8a not ready"
stop_after data

# ---- 5. the skills curriculum, as box.sh (200k seed-1 build, dev 40 per cell, hashes against FULL-BUILD-MANIFEST-200k-seed1.json; then the dev-200 build with the same train.jsonl)
stage skills
fetch_sha $J/cur $CUR_SHA skills_curriculum || die clone-cur
runp $J/out/build.log $J/cur python -m skills_curriculum.build --out $D --train 200000 --dev-per-cell 40 --seed 1 || { tail -3 $J/out/build.log; die build; }
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$D/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
runp $J/out/build_big.log $J/cur python -m skills_curriculum.build --out $DB --train 200000 --dev-per-cell 200 --seed 1 || { tail -3 $J/out/build_big.log; die build-big; }
[ "$(sha $D/train.jsonl)" = "$(sha $DB/train.jsonl)" ] || die big-train-hash
echo "big build train.jsonl hash matches"
stop_after skills

# ---- 6. the job: the queue file's g8a line with local_runner's own prefix (--work WORK/g8a --local --out OUT --skills WORK/data --big-data WORK/data_big --data8a WORK/data8a)
stage train
if [ "$PTC_DRY" != 1 ]; then
  need=$(cat $J/state/cmd.job.mem); free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  [ "${free:-0}" -ge "$need" ] || die "gpu memory free ${free:-?} MiB < $need (the queue's MEM line)"
fi
. $J/state/env.sh              # local_runner's child_env: PYTHONUNBUFFERED, PYTHONUTF8, OMP_NUM_THREADS=2, TOKENIZERS_PARALLELISM, HF_HUB_DISABLE_PROGRESS_BARS, TRANSFORMERS_VERBOSITY, PYTORCH_CUDA_ALLOC_CONF
mkdir -p $O; cp $J/state/cmd.job.txt $O/cmd.txt
say "PTC3S TRAIN START job=$RUN accum=PTC=16 seed=400 rung=3M expected_pool=p10-rung30-s400-a64-L code=$QNAME-$CODE_H"
runp $O/stdout.txt $CODE bash $J/state/cmd.job.sh; rc=$?
echo "rc=$rc" > $O/rc.txt
stage result
kill $WATCH 2>/dev/null; WATCH=
say "PTC3S JOB END rc=$rc maxh_hit=$([ -e $J/state/maxh ] && echo yes || echo no) guard_stop=$([ -e $J/state/guard_stop ] && echo yes || echo no)"
tail -n 3 $O/stdout.txt | cut -c1-300; ls -la $O/PTC 2>/dev/null | head -8
ls -d $W/g8a/pools/* 2>/dev/null | head;
boxfiles; summary; jobok=$?
emit $RUN $O
say "PTC3S RESULT PRINTED rc=$rc job_ok=$([ $jobok = 0 ] && echo yes || echo NO) (collect now; the checkpoint parts follow)"
stage export
[ "$EXPORT_CK" = 1 ] && ck_export
emit $RUN $O      # the result again, last, so a late collect still finds it in the 20,000-line window
if [ $rc = 0 ] && [ $jobok = 0 ]; then
  say "CIO DONE"
  sleep $END_SLEEP
else
  stage failed
  say "CIO-FAIL the job did not finish cleanly (rc=$rc; RESULT-SUMMARY above: job_status, arm_status, final_eval). Collect what was printed, then destroy the box"
  sleep $FAIL_SLEEP; exit 1
fi
