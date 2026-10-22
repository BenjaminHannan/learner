# 8aAT10M on one rented RTX 5090: the agent model (B3AT, arm AT), rung 10M, seed 400, the PC job's command on a box with no access to the PC's files.
# Runs as `bash -c "export NAME=VALUE ...; <this file>" cio` (vast.py create does that). Built from custom_io/box/box.sh + gx_box.sh (branch claude/project-thread-x2cm2v).
# CHECKPOINTS: custom_io at 6e72a5fae5 has no periodic checkpoint and no resume, so this box applies ONE changed file, train.py (embedded below, sha256 checked; the original's sha256 is
# checked first) and runs the job with --train-extra '--ckpt-every 500 --resume': AT/ckpt/step-<k>.pt (+ .json) every CKPT_EVERY updates, newest 2 kept. A job that dies and is started again on
# THIS box (the OOM restart below, or by hand) continues from the newest valid one. A LOST box is replaced only if its checkpoint was exported while it lived (EXPORT_CK_EVERY_H) and is
# imported on the new box (CK_IMPORT_URL / CK_IMPORT_WAIT): see vast_at10m.md, "Checkpoints".
# Env knobs (all optional): ACCUM (gradient-accumulation micro-batches, default 64, always 256 rows per update), OOM_DOUBLE (1: on a CUDA out-of-memory death restart with
# ACCUM doubled up to 256, as the PC card's on_spill does; default 1), MAXH (hard wall-clock stop, hours since the box started; default 40), DPH (dollars per hour of this
# box, for the guard), PROJ_CAP_USD (default 70), GUARD_STEP (default 1000), STEPS (default 24000), EXTRA_H (hours the final evals add to the projection, default 1.5),
# EXPORT_CK (1: after the result is printed, print AT/checkpoint.pt in 3 MB parts for vast.py collectck, ~25 min; default 1; 0 = skip), PACE (seconds between parts, default 100),
# CKPT_EVERY (updates between checkpoints, default 500; 0 = no checkpoint flags at all, the old one-shot run), EXPORT_CK_EVERY_H (hours between exports of the newest checkpoint through the
# log, 3 MB parts like EXPORT_CK, ~120 MB = ~40 parts = ~70 min each at PACE=100; default 0 = never, only the final checkpoint.pt at the end), CK_IMPORT_URL + CK_IMPORT_SHA (a https URL of a
# tar.gz holding 8aAT10M-10M-s400/AT/ckpt/step-<k>.{pt,json} and its sha256: downloaded and unpacked before training, for a replacement box), CK_IMPORT_WAIT (1: instead wait up to 6 h
# for you to put the two files into /job/w/8aAT10M-10M-s400/AT/ckpt and `touch /job/state/ck_ready`),
# TFVER (transformers, default 5.17.0), END_SLEEP / FAIL_SLEEP (seconds the container stays up after the end / a failure; it is billed meanwhile, destroy it).
# Markers in the container log: STAGE ..., AT10M START, TICK ..., GUARD ..., GUARD STOP, MAXH ..., AT10M JOB END rc=N, RBEGIN/R|/REND (result), AT10M DONE, CIO-FAIL <why>,
# CKX START/END <step> <jr> (a periodic checkpoint export; collect it with `vast.py collectck --want <jr>`), CK-IMPORT ..., RESUMED step=<k> from=<file> (train.py).
set -u
J=${J:-/job}; mkdir -p $J/out $J/res $J/state $J/work; cd $J
R=https://github.com/BenjaminHannan/learner
SRC_SHA=6e72a5fae514a343c217c4d95cde37bc3b587c8e          # custom_io at 6e72a5fae5 (branch claude/project-thread-emwjvn)
DATA_POOL_BR=claude/data-pool-8b; DATA_POOL_SHA=12d30d0ce9b8525cfa4fbb4c4bcc74542cf68d3c     # own72/web manifests and cloze_long.py (the PC pins cloze_long at 3d0afbeadd)
OWN_BR=claude/8a-own-data; CUR_BR=claude/project-thread-y0sxwe
MANIFEST_SHA=e8f32daf44d562910db6700bd73b64c720beb6e5c1c5a9a115e8c8880f0763b0
CAPS_PY_SHA=433475405ae7263579ebf4b9633916842567a5b1b1f3a8930311945e504f62d3    # g8a/caps.py of src-at (install_at10m.ps1's $CAPS)
CAPS_JSON_SHA=ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4   # g8a/caps_b3g2.json
CLOZE_SHA=ff6a2e12cf9e4b6a3880c503274898f64b3cb14cbaa853ceeaeb51819edb8cc9       # data_pool/cloze_long.py at 3d0afbeadd
TRAIN0_SHA=e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d      # custom_io/train.py at 6e72a5fae5 (the file the overlay replaces)
OVERLAY_TRAIN_SHA=e75e45fa43c6a6422c0a0e4222e05d8afc27580ec6551100680ed8f9ecdc5015   # overlay/custom_io/train.py of this kit (embedded below)
JOB=8aAT10M-10M-s400
ACCUM=${ACCUM:-64}; OOM_DOUBLE=${OOM_DOUBLE:-1}; MAXH=${MAXH:-40}; DPH=${DPH:-0}; PROJ_CAP_USD=${PROJ_CAP_USD:-70}; GUARD_STEP=${GUARD_STEP:-1000}
CKPT_EVERY=${CKPT_EVERY:-500}; EXPORT_CK_EVERY_H=${EXPORT_CK_EVERY_H:-0}; CK_IMPORT_URL=${CK_IMPORT_URL:-}; CK_IMPORT_SHA=${CK_IMPORT_SHA:-}; CK_IMPORT_WAIT=${CK_IMPORT_WAIT:-0}
STEPS=${STEPS:-24000}; EXTRA_H=${EXTRA_H:-1.5}; EXPORT_CK=${EXPORT_CK:-1}; PACE=${PACE:-100}; TFVER=${TFVER:-5.17.0}; END_SLEEP=${END_SLEEP:-14400}; FAIL_SLEEP=${FAIL_SLEEP:-14400}
T0=${T0:-$(date +%s)}
W=$J/work; O=$J/w/$JOB; D=$J/data; DB=$J/data_big
stage() { echo "$1" > $J/state/stage; echo "=== STAGE $1 $(date -u +%FT%TZ)"; }; stage start
say() { echo "=== $* $(date -u +%FT%TZ)"; }
die() { say "CIO-FAIL $*"; stage "failed:$*"; sleep $FAIL_SLEEP; exit 1; }
sha() { sha256sum "$1" | cut -c1-64; }
# a git step that cannot hang the box silently: timeout + retries + a visible line per failure
retry() { n=$1; shift; for k in $(seq 1 $n); do timeout 900 "$@" && return 0; say "retry $k/$n failed: $*"; sleep 20; done; return 1; }
fetch_sha() {   # dir repo sha sparse-dirs... : exactly that commit, blobs on demand
  d=$1; r=$2; s=$3; shift 3
  rm -rf $d; mkdir -p $d; git -C $d init -q && git -C $d remote add origin $r && git -C $d sparse-checkout init --cone && git -C $d sparse-checkout set "$@" || return 1
  retry 4 git -C $d fetch -q --depth 1 --filter=blob:none origin $s && git -C $d checkout -q FETCH_HEAD && [ "$(git -C $d rev-parse HEAD)" = "$s" ]
}
fetch_br() {    # dir repo branch sparse-dirs... (data branches: tip of the branch; the hashes below decide whether it is the approved content)
  d=$1; r=$2; b=$3; shift 3
  rm -rf $d; retry 4 git clone -q --depth 1 --filter=blob:none --sparse -b $b $r $d && { [ $# = 0 ] || git -C $d sparse-checkout set "$@"; }
}

# ---- the speed guard (python, testable on its own: `python guard.py LOGFILE T0 NOW DPH CAP STEP STEPS EXTRA_H`; prints GUARD lines, exit 3 = stop, 0 = fine, 4 = no line yet)
write_guard() { cat > $J/guard.py <<'PY'
import json, sys
log, t0, now, dph, cap, gstep, steps, extra = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), float(sys.argv[8])
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
up_h = (now - t0) / 3600                                          # hours the box has been up (setup + data + pool included, already paid)
total_h = up_h + (steps - line['step']) * spu / 3600 + extra
usd = total_h * dph
print('GUARD step=%d sec_per_update=%.3f train_total_h=%.2f up_h=%.2f projected_total_h=%.2f dph=%.3f projected_usd=%.2f cap_usd=%.0f' % (
    line['step'], spu, spu * steps / 3600, up_h, total_h, dph, usd, cap), flush=True)
if usd > cap:
    print('GUARD STOP projected %.2f USD > cap %.0f USD' % (usd, cap), flush=True)
    sys.exit(3)
PY
}
# anchored on the start of the command line: this script itself runs as `bash -c "<this text>"`, so an unanchored pkill -f would kill it too
PJ='^[^ ]*python[0-9.]* -m custom_io[.](g8a[.]job|train)( |$)'
kill_job() { pkill -f "$PJ"; sleep 10; pkill -9 -f "$PJ"; }
watch_loop() {   # background: guard once at GUARD_STEP, MAXH wall clock, a TICK line every 5 min
  last=0
  while true; do
    now=$(date +%s)
    if [ "$MAXH" != 0 ] && [ $((now - T0)) -ge $(awk "BEGIN{print int($MAXH*3600)}") ]; then
      say "MAXH $MAXH h reached: stopping the job (no result; the last checkpoint is in $O/AT/ckpt on this box only, unless an export reached you)"; echo maxh > $J/state/stopped; kill_job; return 0; fi
    if [ ! -f $J/state/guard_done ] && [ -f $O/AT/stdout.txt ]; then
      python $J/guard.py $O/AT/stdout.txt $T0 $now $DPH $PROJ_CAP_USD $GUARD_STEP $STEPS $EXTRA_H > $J/state/guard.out; g=$?
      { [ $g = 0 ] || [ $g = 3 ]; } && { cat $J/state/guard.out; touch $J/state/guard_done; }
      [ $g = 3 ] && { echo guard > $J/state/stopped; kill_job; return 0; }
    fi
    iv=300; [ -e $J/state/exporting ] && iv=60      # while a checkpoint export floods the log (8,300 lines a part) the 20,000-line window holds ~4 minutes: a TICK every minute then
    if [ $((now - last)) -ge $iv ]; then last=$now
      echo "TICK stage=$(cat $J/state/stage 2>/dev/null) up_min=$(( (now - T0) / 60 )) $(grep -h -E '"event": "train"|Traceback' $O/AT/stdout.txt 2>/dev/null | tail -1 | cut -c1-200) | disk_data8a=$(du -sm $W/data8a 2>/dev/null | cut -f1)MB shard=$(du -sm $W/data8a/shard 2>/dev/null | cut -f1)MB | gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader 2>/dev/null)"
    fi
    sleep 30
  done
}
emit() {   # name dir : the small result files as base64 lines between RBEGIN/REND with a sha256 (vast.py collect reads them). No .pt. Each stdout.txt is replaced by its
           # key lines (start, size, caps, cap_hits, train, quick_eval, done, errors), so the gate and readout read AT/stdout.txt the same way as on the PC
  n=$1; d=$2; bn=$(basename $d); T=$J/res/$n.tgz; st=$J/res/stage
  rm -rf $st; mkdir -p $st/$bn
  tar -C $d --exclude='*.pt' --exclude=stdout.txt -cf - . | tar -C $st/$bn -xf -
  for f in $(cd $d && find . -name stdout.txt); do
    grep -E '"event": "(start|size|caps|cap_hits|train|quick_eval|done)"|Traceback|Error|error|out of memory|RESULT' $d/$f | cut -c1-4000 > $st/$bn/$f; done
  tar -czf $T -C $st $bn
  h=$(sha $T)
  echo "RBEGIN|$n|$h|$(stat -c %s $T)"; base64 -w 300 $T | sed "s/^/R|$n|/"; echo "REND|$n"
}
ck_export() {   # the final checkpoint.pt (~40 MB: Gemma is not in it) through the log in 3 MB parts, as custom_io/box/ck_export.sh (vast.py collectck reassembles)
  LOG=${LOG:-/proc/1/fd/1}; c=$O/AT/checkpoint.pt; [ -f $c ] || { echo "CKDONE|0" >> $LOG; return; }
  T=$J/res/ck-AT.tgz; tar -czf $T -C $J/w $JOB/AT/checkpoint.pt; full=$(sha $T); rm -f $J/res/ck-AT.part.*
  split -b 3000000 -d -a 3 $T $J/res/ck-AT.part.; n=$(ls $J/res/ck-AT.part.* | wc -l); N=0
  echo "CKFULL|$JOB/AT|$full|$n" >> $LOG
  for p in $(ls $J/res/ck-AT.part.* | sort); do
    k=$((10#${p##*.})); N=$((N + 1)); h=$(sha $p)
    { echo "RBEGIN|ck$N|$h|$(stat -c %s $p)|$JOB/AT|$k|$n"; base64 -w 480 $p | sed "s/^/R|ck$N|/"; echo "REND|ck$N"; } >> $LOG
    echo "part ck$N $k/$n"; sleep $PACE
  done
  emit 8aAT10M-vast $O >> $LOG      # the result again, last, so one log read finds it
  echo "CKDONE|$N" >> $LOG
}
ckx_export() {   # the newest VALID checkpoint of AT/ckpt through the log in 3 MB parts (~120 MB = ~40 parts); vast.py collectck --want <jr> reassembles it to OUT/JOB/AT/ckpt/step-<k>.{pt,json}
  local T S d k full n N jr kk p h; LOG=${LOG:-/proc/1/fd/1}; d=$O/AT/ckpt; S=$J/res/ckx
  rm -rf $S $J/res/ckx.tgz $J/res/ckx.part.*; mkdir -p $S/$JOB/AT/ckpt $J/state
  cp -p $d/step-*.pt $d/step-*.json $S/$JOB/AT/ckpt/ 2>/dev/null       # a copy: train.py may delete the older one while we read
  k=$(python - $S/$JOB/AT/ckpt <<'PY'
import hashlib, json, os, re, sys
d, best = sys.argv[1], None
for f in sorted(os.listdir(d)):
    m = re.match(r'^step-(\d+)\.json$', f)
    if not m:
        continue
    try:
        side = json.load(open(os.path.join(d, f)))
        pt = os.path.join(d, side['file'])
        if os.path.getsize(pt) == side['bytes'] and hashlib.sha256(open(pt, 'rb').read()).hexdigest() == side['sha256'] and side['file'] == 'step-%s.pt' % m.group(1):
            best = max(best or 0, int(m.group(1)))
    except Exception:
        pass
if best:
    for f in os.listdir(d):
        if f not in ('step-%d.pt' % best, 'step-%d.json' % best):
            os.remove(os.path.join(d, f))
print(best or '')
PY
)
  [ -n "$k" ] || { echo "CKX none: no valid checkpoint in $d yet"; rm -rf $S; return 0; }
  T=$J/res/ckx.tgz; tar -czf $T -C $S $JOB; full=$(sha $T); rm -rf $S
  split -b 3000000 -d -a 3 $T $J/res/ckx.part.; n=$(ls $J/res/ckx.part.* | wc -l); N=0; jr=$JOB/AT-ck$k
  echo "CKX START step=$k jr=$jr parts=$n"; echo "CKFULL|$jr|$full|$n" >> $LOG; touch $J/state/exporting
  for p in $(ls $J/res/ckx.part.* | sort); do
    kk=$((10#${p##*.})); N=$((N + 1)); h=$(sha $p)
    { echo "RBEGIN|ckx${k}_$N|$h|$(stat -c %s $p)|$jr|$kk|$n"; base64 -w 480 $p | sed "s/^/R|ckx${k}_$N|/"; echo "REND|ckx${k}_$N"; } >> $LOG
    sleep $PACE
  done
  rm -f $T $J/res/ckx.part.* $J/state/exporting
  echo "CKX END step=$k jr=$jr"
}
ckx_loop() {   # background: every EXPORT_CK_EVERY_H hours (the first one that long after the start of training) export the newest checkpoint
  [ "$EXPORT_CK_EVERY_H" != 0 ] || return 0
  secs=$(awk "BEGIN{print int($EXPORT_CK_EVERY_H*3600)}"); next=$(( $(date +%s) + secs ))
  while true; do
    sleep 60; [ "$(date +%s)" -ge $next ] || continue
    ckx_export; next=$(( $(date +%s) + secs ))
  done
}
ck_import() {   # a replacement box: the checkpoint of the lost one (a tar.gz of JOB/AT/ckpt/step-<k>.{pt,json}, see vast_at10m.md) goes under $O/AT/ckpt before training; train.py --resume checks it
  mkdir -p $O/AT/ckpt
  if [ -n "$CK_IMPORT_URL" ]; then
    [ -n "$CK_IMPORT_SHA" ] || die "CK_IMPORT_URL needs CK_IMPORT_SHA (the sha256 of the tar.gz)"
    retry 4 curl -fsSL --retry 3 -o $J/res/ck-import.tgz "$CK_IMPORT_URL" || die ck-import-download
    [ "$(sha $J/res/ck-import.tgz)" = "$CK_IMPORT_SHA" ] || die "ck-import sha256 is $(sha $J/res/ck-import.tgz), not $CK_IMPORT_SHA"
    tar -xzf $J/res/ck-import.tgz -C $J/w --no-same-owner || die ck-import-untar
  elif [ "$CK_IMPORT_WAIT" = 1 ]; then
    say "CK-IMPORT waiting up to 6 h: put step-<k>.pt and step-<k>.json into $O/AT/ckpt, then touch $J/state/ck_ready"
    for i in $(seq 1 720); do [ -e $J/state/ck_ready ] && break; sleep 30; done
    [ -e $J/state/ck_ready ] || die ck-import-timeout
  else
    return 0
  fi
  ls $O/AT/ckpt/step-*.pt >/dev/null 2>&1 || die "ck-import: no step-*.pt in $O/AT/ckpt"
  say "CK-IMPORT ok: $(ls -la $O/AT/ckpt | tail -n +2 | awk '{print $5, $9}' | tr '\n' ' ')"
}
# >>> OVERLAY train.py (gzip + base64; regenerate with vast/embed_overlay.py; selftest.sh checks it against the pins and against ../overlay)
overlay_b64() { cat <<'B64'
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
bv8NDsqwQk+IAAA=
B64
}
# <<< OVERLAY
apply_overlay() {   # custom_io/train.py of 6e72a5fae5 (sha256 checked by the caller) -> the checkpoint / resume version (sha256 checked here)
  overlay_b64 | base64 -d | gzip -dc > $C/train.py.new || die overlay-decode
  [ "$(sha $C/train.py.new)" = "$OVERLAY_TRAIN_SHA" ] || die "overlay train.py is $(sha $C/train.py.new), not $OVERLAY_TRAIN_SHA"
  mv $C/train.py.new $C/train.py
  (cd $J/src-at && python -m custom_io.train --model plain_tf --ckpt-every 500 --resume 2>&1 | grep -q "need --out") || die "overlay: --ckpt-every / --resume are not accepted"
}
[ "${AT10M_SOURCE_ONLY:-0}" = 1 ] && return 0 2>/dev/null

# ---- 1. box + packages
say "CIO START"; stage setup
say "AT10M START accum=$ACCUM maxh=$MAXH dph=$DPH cap_usd=$PROJ_CAP_USD guard_step=$GUARD_STEP steps=$STEPS job=$JOB src=$SRC_SHA"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2; nproc; df -h $J | tail -1
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || die git
write_guard
watch_loop & WATCH=$!
PIP_BREAK_SYSTEM_PACKAGES=1 retry 3 pip install -q --break-system-packages "transformers==$TFVER" "safetensors==0.8.0" accelerate numpy pyarrow huggingface_hub > out/pip.log 2>&1 || { tail -3 out/pip.log; die pip; }
python -c "import torch, transformers; print(torch.__version__, transformers.__version__, torch.cuda.get_device_name(0))" || die torch
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 PYTHONUTF8=1

# ---- 2. code: src-at = custom_io at 6e72a5fae5, pinned files checked (install_at10m.ps1's list)
stage code
fetch_sha $J/src-at $R $SRC_SHA custom_io || die fetch-src-at
C=$J/src-at/custom_io
while read -r f h; do [ "$(sha $C/$f)" = "$h" ] || die "src-at file $f is not commit 6e72a5fae5's (got $(sha $C/$f))"; done <<PINS
train.py $TRAIN0_SHA
models/b3at.py 5b10aac1f20914baa72dfea114379682e6ddfc1dbdee2f749a546760e7fc1768
models/b3g2.py a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce
models/writer.py f3a40ad58749bbc24a964942dc650c79864d6a74442628aac7d752730e73309e
models/b3.py f3ef34d9f13256ccee1ca7dd47efc32cb7eaf51e3a09c4221e3be4c0858804c8
g8a/configs.py 343700363ae14cc31dcdbc705a9258b9c8384e48adac5d175997d1fbfbcef875
g8a/job.py d4d422aab845d0ed36396bdef7129f74fd6bca1205ae224feac20e324148c662
local_runner.py 0562a4bb065a02f6c048d919d68bb6d445f36e357518dc8826d9d545323db4ef
g8a/caps.py $CAPS_PY_SHA
g8a/caps_b3g2.json $CAPS_JSON_SHA
PINS
say "code ok: src-at pinned files match (train.py, caps.py and caps_b3g2.json included)"
apply_overlay
say "overlay ok: custom_io/train.py = the checkpoint/resume version $OVERLAY_TRAIN_SHA (--ckpt-every $CKPT_EVERY --resume)"

# ---- 3. EmbeddingGemma (frozen), pinned revision, anonymous download with the box.sh retry loop
stage gemma
for k in 1 2 3 4 5 6; do
  (cd $J/src-at && timeout 1500 python -c "from huggingface_hub import snapshot_download as s; from custom_io.models.eg import EG_ID, EG_REV; s(EG_ID, revision=EG_REV, local_dir='$J/eg2')") > out/eg_dl.log 2>&1 && break
  tail -2 out/eg_dl.log; [ $k = 6 ] && die eg-download; say "eg download try $k failed, retrying in 4 min"; sleep 240
done
export CUSTOM_IO_EG2=$J/eg2
(cd $J/src-at && python -m custom_io.models.eg check cuda) || die eg-check

# ---- 4. data, as gx_box.sh: skills curriculum (box.sh), data-pool branch, own-data branch, FineWeb shard + manifest sha check (custom_io.g8a.get_data)
stage skills
fetch_br $J/cur $R $CUR_BR skills_curriculum || die clone-cur
(cd $J/cur && python -m skills_curriculum.build --out $D --train 200000 --dev-per-cell 40 --seed 1 > $J/out/build.log 2>&1) || die build
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$D/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
(cd $J/cur && python -m skills_curriculum.build --out $DB --train 200000 --dev-per-cell 200 --seed 1 > $J/out/build_big.log 2>&1) || die build-big
[ "$(sha $D/train.jsonl)" = "$(sha $DB/train.jsonl)" ] || die big-train-hash
say "skills data ok"
stage data
fetch_sha $J/dp $R $DATA_POOL_SHA data_pool/built data_pool/panels || die clone-dp
fetch_br $J/od $R $OWN_BR || die clone-od
[ "$(sha $J/dp/data_pool/cloze_long.py)" = "$CLOZE_SHA" ] || die "cloze_long.py is not the pinned one (got $(sha $J/dp/data_pool/cloze_long.py))"
[ "$(sha $J/dp/data_pool/built/own72_MANIFEST.json)" = "$MANIFEST_SHA" ] || die own72-manifest
say "data branches fetched; building the 8a data (FineWeb-Edu shard 0 is 2.15 GB; the slices must hash to the manifest)"
(cd $J/src-at && timeout 7200 python -m custom_io.g8a.get_data --work $W --data-pool $J/dp --own-xz $J/od --out $O/data8a-check \
  --expect-manifest-sha $MANIFEST_SHA) > $J/out/get_data.log 2>&1 || { tail -8 $J/out/get_data.log; die get_data; }
tail -3 $J/out/get_data.log

# ---- 5. the job: the PC queue line `g8a: 8aAT10M-10M-s400 --rung 10M --seed 400 --arms AT --b2-extra '{"eg_embed": true}' --cloze-long ... --caps-file ... --accum AT=64`
#         with local_runner's own prefix (--work WORK/g8a --local --out OUT --skills WORK/data --big-data WORK/data_big --data8a WORK/data8a)
stage train
mkdir -p $O
ck_import
run_job() {   # AT/ckpt is kept: a restart of the job (the OOM restart, or by hand) resumes from it; everything else of the arm's folder is made again
  mkdir -p $O/AT; find $O/AT -mindepth 1 -maxdepth 1 ! -name ckpt -exec rm -rf {} +; rm -f $O/RESULT.json $O/box.json $J/state/guard_done
  extra=(); [ "$CKPT_EVERY" != 0 ] && extra=(--train-extra "--ckpt-every $CKPT_EVERY --resume")
  (cd $J/src-at && python -m custom_io.g8a.job --work $W/g8a --local --out $O --skills $D --big-data $DB --data8a $W/data8a \
    --rung 10M --seed 400 --arms AT --b2-extra '{"eg_embed": true}' --cloze-long $J/dp/data_pool/cloze_long.py \
    --caps-file $C/g8a/caps_b3g2.json --accum AT=$ACCUM ${extra[@]+"${extra[@]}"}) > $O/job.log 2>&1
}
say "AT10M TRAIN START job=$JOB accum=AT=$ACCUM ckpt_every=$CKPT_EVERY export_ck_every_h=$EXPORT_CK_EVERY_H"
ckx_loop & CKX=$!
while true; do
  run_job; rc=$?
  echo "rc=$rc" > $O/rc.txt
  if [ $rc != 0 ] && [ ! -e $J/state/stopped ] && [ "$OOM_DOUBLE" = 1 ] && [ $ACCUM -lt 256 ] && grep -q -i "out of memory" $O/AT/stdout.txt $O/job.log 2>/dev/null; then
    ACCUM=$((ACCUM * 2)); say "CUDA out of memory: restarting with accum AT=$ACCUM (the pool is reused)"; echo "oom->accum $ACCUM" >> $J/state/oom.txt; continue
  fi
  break
done
stage done
say "AT10M JOB END rc=$rc accum=$ACCUM stopped=$(cat $J/state/stopped 2>/dev/null || echo no)"
kill $WATCH $CKX 2>/dev/null
tail -3 $O/job.log; ls -la $O/AT 2>/dev/null | head
cp $J/state/guard.out $O/guard.out 2>/dev/null; cp $J/state/oom.txt $O/oom.txt 2>/dev/null; cp $J/out/get_data.log $O/get_data.log
emit 8aAT10M-vast $O
say "AT10M RESULT PRINTED rc=$rc (collect now; the checkpoint parts follow if EXPORT_CK=1)"
[ "$EXPORT_CK" = 1 ] && ck_export
say "AT10M DONE rc=$rc"
sleep $END_SLEEP
