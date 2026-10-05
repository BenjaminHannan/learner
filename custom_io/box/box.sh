# Custom-IO queue box (2026-10-05). Runs on a Vast GPU box as `bash -c "$(this file)" cio`.
# Adapted from scripts/cap256_launch/ultracode_box.sh (branch claude/ultracode-learning-blocker-gh011t).
# Sets up once: this branch's custom_io/ code, the 200k seed-1 skills curriculum with its hash check, transformers
# (only for the pretrained same-size baselines). Then polls this branch every ~45 s for custom_io/queue/NN-name.sh and
# runs each once, up to MAXPAR at a time while the GPU has room. When a job ends, its outputs (RESULT.json, logs; no
# .pt) are tarred and printed into the container log as base64 lines "R|name|..." between RBEGIN/REND with a sha256,
# so the cloud container reads them through the Vast logs API. No credential is on the box; nothing listens.
# custom_io/queue/STOP ends the loop; custom_io/queue/REPRINT (one job name per line) re-prints finished results.
set -u
J=/job; mkdir -p $J/out $J/res $J/state $J/w; cd $J
BR=claude/custom-reader-talker-4x309r
R=https://github.com/BenjaminHannan/learner
MAXPAR=${MAXPAR:-6}
QSUB=${QSUB:-}
say() { echo "=== $* $(date -u +%FT%TZ)"; }
die() { say "CIO-FAIL $*"; sleep 21600; exit 1; }
say "CIO START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2; nproc
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || die git
git clone -q --depth 1 --filter=blob:none --sparse -b $BR $R mine && (cd mine && git sparse-checkout set custom_io) || die clone-mine
git clone -q --depth 1 --filter=blob:none --sparse -b claude/project-thread-y0sxwe $R cur && (cd cur && git sparse-checkout set skills_curriculum) || die clone-cur
(cd cur && python -m skills_curriculum.build --out $J/data --train 200000 --dev-per-cell 40 --seed 1 > $J/out/build.log 2>&1) || die build
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$J/data/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
(cd cur && python -m skills_curriculum.build --out $J/data_big --train 200000 --dev-per-cell 200 --seed 1 > $J/out/build_big.log 2>&1) || die build-big
[ "$(sha256sum $J/data/train.jsonl | cut -c1-64)" = "$(sha256sum $J/data_big/train.jsonl | cut -c1-64)" ] || die big-train-hash
echo "big build train.jsonl hash matches"
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.17.0" "safetensors==0.8.0" accelerate numpy > out/pip.log 2>&1 || { tail -3 out/pip.log; die pip; }
python -c "import torch, transformers; print(torch.__version__, transformers.__version__, torch.cuda.get_device_name(0))"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
D=$J/data
DB=$J/data_big
export J D DB
emit() {  # name : print the job's outputs as base64 lines
  n=$1; T=$J/res/$n.tgz
  (cd $J/w/$n 2>/dev/null && for f in */stdout.txt stdout.txt; do [ -f "$f" ] && grep -E '"event"|Traceback|Error|error|RESULT' "$f" | cut -c1-4000 > "${f%.txt}.events.txt"; done)
  tar -czf $T --exclude='*.pt' --exclude='stdout.txt' -C $J/w $n 2>/dev/null
  h=$(sha256sum $T | cut -c1-64)
  ( flock 9
    echo "RBEGIN|$n|$h|$(stat -c %s $T)"
    base64 -w 300 $T | sed "s/^/R|$n|/"
    echo "REND|$n"
  ) 9>$J/print.lock
}
say "CIO READY"
last=0
while true; do
  (cd mine && git fetch -q --depth 1 origin $BR && git reset -q --hard FETCH_HEAD) 2>/dev/null
  Q=mine/custom_io/queue${QSUB:-}
  [ -f $Q/STOP ] && { say "CIO STOP"; break; }
  if [ -f $Q/REPRINT ]; then
    s=$(sha256sum $Q/REPRINT | cut -c1-16)
    [ -f $J/state/reprint.$s ] || { touch $J/state/reprint.$s; for n in $(cat $Q/REPRINT); do [ -f $J/state/$n.done ] && emit $n; done; }
  fi
  for f in $(ls $Q/*.sh 2>/dev/null | sort); do
    n=$(basename $f .sh)
    [ -e $J/state/$n.started ] && continue
    need=$(grep -m1 -oE '^# MEM [0-9]+' $f | awk '{print $3}'); need=${need:-4000}
    par=$(grep -m1 -oE '^# PAR [0-9]+' $f | awk '{print $3}'); par=${par:-1}
    free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    running=$(ls $J/state/*.running 2>/dev/null | wc -l)
    { [ $((running + par)) -gt $MAXPAR ] || [ ${free:-0} -lt $need ]; } && break
    touch $J/state/$n.started $J/state/$n.running
    cp $f $J/state/$n.sh
    # each job runs on a frozen copy of the code taken at its start, so later pushes never change a running job
    rm -rf $J/code/$n; mkdir -p $J/code/$n; cp -r mine/custom_io $J/code/$n/
    say "JOB START $n (free ${free} MiB, running $running)"
    ( mkdir -p $J/w/$n; export JOB=$n
      # run NAME args... : one custom_io.train run of this job, in its own output folder
      run() { m=$1; shift; mkdir -p $J/w/$JOB/$m; (cd $J/code/$JOB && python -m custom_io.train --data $D --big-data $DB --out $J/w/$JOB/$m "$@" > $J/w/$JOB/$m/stdout.txt 2>&1); }
      export -f run
      (cd $J/code/$n && bash -c "source $J/state/$n.sh") > $J/w/$n/stdout.txt 2>&1
      echo "rc=$?" > $J/w/$n/rc.txt; emit $n; say "JOB END $n $(cat $J/w/$n/rc.txt)"; touch $J/state/$n.done; rm -f $J/state/$n.running ) &
    sleep 15
  done
  now=$(date +%s)
  if [ $((now - last)) -ge 240 ]; then
    last=$now
    for r in $(ls $J/state/*.running 2>/dev/null); do n=$(basename $r .running)
      for s in $(ls $J/w/$n/*/stdout.txt 2>/dev/null); do echo "TICK $n/$(basename $(dirname $s)) $(grep -E '"event"|Traceback' $s | tail -1 | cut -c1-220)"; done; done
    echo "TICK gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"
  fi
  sleep 45
done
wait
say "CIO DONE"
sleep 21600
