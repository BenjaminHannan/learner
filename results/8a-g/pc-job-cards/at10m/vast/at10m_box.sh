# 8aAT10M on one rented RTX 5090: the agent model (B3AT, arm AT), rung 10M, seed 400, the PC job's command on a box with no access to the PC's files.
# Runs as `bash -c "export NAME=VALUE ...; <this file>" cio` (vast.py create does that). Built from custom_io/box/box.sh + gx_box.sh (branch claude/project-thread-x2cm2v).
# One uninterrupted run: train.py has NO periodic checkpoint and NO resume (checkpoint.pt is written once, after the last step), so a lost box = start over.
# Env knobs (all optional): ACCUM (gradient-accumulation micro-batches, default 64, always 256 rows per update), OOM_DOUBLE (1: on a CUDA out-of-memory death restart with
# ACCUM doubled up to 256, as the PC card's on_spill does; default 1), MAXH (hard wall-clock stop, hours since the box started; default 40), DPH (dollars per hour of this
# box, for the guard), PROJ_CAP_USD (default 70), GUARD_STEP (default 1000), STEPS (default 24000), EXTRA_H (hours the final evals add to the projection, default 1.5),
# EXPORT_CK (1: after the result is printed, print AT/checkpoint.pt in 3 MB parts for vast.py collectck, ~25 min; default 1; 0 = skip), PACE (seconds between parts, default 100),
# TFVER (transformers, default 5.17.0), END_SLEEP / FAIL_SLEEP (seconds the container stays up after the end / a failure; it is billed meanwhile, destroy it).
# Markers in the container log: STAGE ..., AT10M START, TICK ..., GUARD ..., GUARD STOP, MAXH ..., AT10M JOB END rc=N, RBEGIN/R|/REND (result), AT10M DONE, CIO-FAIL <why>.
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
JOB=8aAT10M-10M-s400
ACCUM=${ACCUM:-64}; OOM_DOUBLE=${OOM_DOUBLE:-1}; MAXH=${MAXH:-40}; DPH=${DPH:-0}; PROJ_CAP_USD=${PROJ_CAP_USD:-70}; GUARD_STEP=${GUARD_STEP:-1000}
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
      say "MAXH $MAXH h reached: stopping the job (no checkpoint exists, so there is no result)"; echo maxh > $J/state/stopped; kill_job; return 0; fi
    if [ ! -f $J/state/guard_done ] && [ -f $O/AT/stdout.txt ]; then
      python $J/guard.py $O/AT/stdout.txt $T0 $now $DPH $PROJ_CAP_USD $GUARD_STEP $STEPS $EXTRA_H > $J/state/guard.out; g=$?
      { [ $g = 0 ] || [ $g = 3 ]; } && { cat $J/state/guard.out; touch $J/state/guard_done; }
      [ $g = 3 ] && { echo guard > $J/state/stopped; kill_job; return 0; }
    fi
    if [ $((now - last)) -ge 300 ]; then last=$now
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
say "code ok: src-at pinned files match (caps.py and caps_b3g2.json included)"

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
run_job() {
  rm -rf $O/AT $O/RESULT.json $O/box.json; rm -f $J/state/guard_done
  (cd $J/src-at && python -m custom_io.g8a.job --work $W/g8a --local --out $O --skills $D --big-data $DB --data8a $W/data8a \
    --rung 10M --seed 400 --arms AT --b2-extra '{"eg_embed": true}' --cloze-long $J/dp/data_pool/cloze_long.py \
    --caps-file $C/g8a/caps_b3g2.json --accum AT=$ACCUM) > $O/job.log 2>&1
}
say "AT10M TRAIN START job=$JOB accum=AT=$ACCUM"
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
kill $WATCH 2>/dev/null
tail -3 $O/job.log; ls -la $O/AT 2>/dev/null | head
cp $J/state/guard.out $O/guard.out 2>/dev/null; cp $J/state/oom.txt $O/oom.txt 2>/dev/null; cp $J/out/get_data.log $O/get_data.log
emit 8aAT10M-vast $O
say "AT10M RESULT PRINTED rc=$rc (collect now; the checkpoint parts follow if EXPORT_CK=1)"
[ "$EXPORT_CK" = 1 ] && ck_export
say "AT10M DONE rc=$rc"
sleep $END_SLEEP
