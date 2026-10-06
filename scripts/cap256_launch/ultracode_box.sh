# Ultracode learning-blocker queue box (2026-10-05). Runs on a Vast GPU box as `bash -c "$(this file)" uc`.
# Sets up the same stack as the plateau/fix-screen boxes ONCE (pipeline + main2 from claude/real-pipeline-checkpoints,
# transformers 5.17.0, LFM2.5-1.2B-Instruct @ 0f604ada, the 200k seed-1 skills curriculum with its hash check), then
# polls this branch every ~45 s for job files artifacts/ultracode-v4/queue/NN-name.sh and runs each once, up to MAXPAR
# at a time while the GPU has room. When a job ends, its outputs (SKILLS-RESULT.json etc.) and log are tarred and
# printed into the container log as base64 lines "R|name|..." between RBEGIN/REND markers with a sha256, so the
# cloud container can read them with the Vast logs API. No credential is on the box; nothing listens for connections.
# A file artifacts/ultracode-v4/queue/STOP ends the loop; REPRINT (one job name per line) re-prints finished results.
set -u
J=/job; mkdir -p $J/out $J/res $J/state $J/w; cd $J
BR=claude/ultracode-learning-blocker-gh011t
R=https://github.com/BenjaminHannan/learner
MAXPAR=${MAXPAR:-5}
QSUB=${QSUB:-}   # e.g. /b: this box reads queue/b/*.sh only, so two boxes never run the same job
say() { echo "=== $* $(date -u +%FT%TZ)"; }
die() { say "UC-FAIL $*"; sleep 21600; exit 1; }
say "UC START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2; nproc
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || die git
git clone -q --depth 1 --filter=blob:none --sparse -b claude/real-pipeline-checkpoints $R repo && (cd repo && git sparse-checkout set pipeline skills) || die clone-pipeline
[ -f repo/skills/main2/final-checkpoint.pt ] || die no-main2
git clone -q --depth 1 --filter=blob:none --sparse -b $BR $R mine || die clone-mine
(cd mine && git sparse-checkout set --no-cone /scripts/cap256_launch/ /artifacts/ultracode-v4/queue/) || die sparse-mine
P=$J/repo/pipeline
M2=$J/repo/skills/main2/final-checkpoint.pt
sha256sum $M2
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.17.0" "safetensors==0.8.0" accelerate > out/pip.log 2>&1 || { tail -3 out/pip.log; die pip; }
[ "$(python -c 'import importlib.metadata as m; print(m.version("torch"))')" = "2.11.0+cu128" ] || PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "torch==2.11.0+cu128" --index-url https://download.pytorch.org/whl/cu128 >> out/pip.log 2>&1
python -c "import torch, transformers, importlib.metadata as m; print(torch.__version__, transformers.__version__, m.version('safetensors'), torch.cuda.get_device_name(0))"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
REV=0f604ada3f766f9f257460c4c9f0b5d6f69d431b
SNAP=$(python -c "from huggingface_hub import snapshot_download as s; print(s('LiquidAI/LFM2.5-1.2B-Instruct', revision='$REV'))") || die hf
H=$J/hf/models--LiquidAI--LFM2.5-1.2B-Instruct; mkdir -p $H/snapshots/$REV $H/blobs; cp -L $SNAP/* $H/snapshots/$REV/ || die cpmodel
SNAP=$H/snapshots/$REV
CD=$P/artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/CONFIGS-v1; mkdir -p $CD
python -c "import json,sys; c=json.load(open('$P/configs/english-pilot-v1/TRAIN-CONFIG-v2.json')); c['lm']['model_path']=sys.argv[1]; json.dump(c,open('$CD/TRAIN-CONFIG-v2.json','w'),indent=1)" "$SNAP"
git clone -q --depth 1 --filter=blob:none --sparse -b claude/project-thread-y0sxwe $R cur && (cd cur && git sparse-checkout set skills_curriculum) || die clone-cur
(cd cur && python -m skills_curriculum.build --out $J/data --train 200000 --dev-per-cell 40 --seed 1 > $J/out/build.log 2>&1) || die build
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$J/data/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
D=$J/data
export J P D M2 SNAP PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch
cat > $J/prelude.sh <<'EOF'
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
FIT="--families $W8 --updates 6000 --eval-every 3000 --dev-n 320 --eval-at-start --fixed-rows 2000 --passes 3"
# run NAME args... : one skills_pretrain_v1 run from main2 in its own cwd (GPU-BUSY marker is a relative path on Linux)
run() { n=$1; shift; mkdir -p $J/w/$JOB/$n; (cd $J/w/$JOB/$n && python $P/scripts/cap256_launch/skills_pretrain_v1.py --root $P --data $D \
  --out artifacts/uc/$JOB/$n --parent-path $M2 --no-checkpoint --minutes 170 "$@" > $J/w/$JOB/$n/stdout.txt 2>&1); }
EOF
emit() {  # name : print the job's outputs as base64 lines
  n=$1; T=$J/res/$n.tgz
  mkdir -p $P/artifacts/uc/$n
  (cd $J/w/$n 2>/dev/null && for f in */stdout.txt stdout.txt; do [ -f "$f" ] && grep -E '"event"|Traceback|Error|error|SKILLS-RESULT|^PROBE|^RESULT' "$f" | cut -c1-4000 > "${f%.txt}.events.txt"; done)
  tar -czf $T --exclude='*.pt' --exclude='stdout.txt' -C $J/w $n -C $P/artifacts/uc $n 2>/dev/null
  h=$(sha256sum $T | cut -c1-64)
  ( flock 9
    echo "RBEGIN|$n|$h|$(stat -c %s $T)"
    base64 -w 300 $T | sed "s/^/R|$n|/"
    echo "REND|$n"
  ) 9>$J/print.lock
}
say "UC READY"
last=0
while true; do
  (cd mine && git fetch -q --depth 1 origin $BR && git reset -q --hard FETCH_HEAD) 2>/dev/null
  cp mine/scripts/cap256_launch/*.py $P/scripts/cap256_launch/ 2>/dev/null
  Q=mine/artifacts/ultracode-v4/queue${QSUB:-}
  [ -f $Q/STOP ] && { say "UC STOP"; break; }
  if [ -f $Q/REPRINT ]; then
    s=$(sha256sum $Q/REPRINT | cut -c1-16)
    [ -f $J/state/reprint.$s ] || { touch $J/state/reprint.$s; for n in $(cat $Q/REPRINT); do [ -f $J/state/$n.done ] && emit $n; done; }
  fi
  for f in $(ls $Q/*.sh 2>/dev/null | sort); do
    n=$(basename $f .sh)
    [ -e $J/state/$n.started ] && continue
    need=$(grep -m1 -oE '^# MEM [0-9]+' $f | awk '{print $3}'); need=${need:-6500}
    par=$(grep -m1 -oE '^# PAR [0-9]+' $f | awk '{print $3}'); par=${par:-1}
    free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    running=$(ls $J/state/*.running 2>/dev/null | wc -l)
    { [ $((running + par)) -gt $MAXPAR ] || [ ${free:-0} -lt $need ]; } && break
    touch $J/state/$n.started $J/state/$n.running
    cp $f $J/state/$n.sh
    say "JOB START $n (free ${free} MiB, running $running)"
    ( mkdir -p $J/w/$n; cd $J/w/$n; export JOB=$n; source $J/prelude.sh; bash -c "source $J/prelude.sh; source $J/state/$n.sh" > $J/w/$n/stdout.txt 2>&1
      echo "rc=$?" > $J/w/$n/rc.txt; emit $n; say "JOB END $n $(cat $J/w/$n/rc.txt)"; touch $J/state/$n.done; rm -f $J/state/$n.running ) &
    sleep 20
  done
  now=$(date +%s)
  if [ $((now - last)) -ge 240 ]; then
    last=$now
    for r in $(ls $J/state/*.running 2>/dev/null); do n=$(basename $r .running)
      for s in $(ls $J/w/$n/*/stdout.txt 2>/dev/null); do echo "TICK $n/$(basename $(dirname $s)) $(grep -E 'skills-(progress|eval)|Traceback' $s | tail -1 | cut -c1-220)"; done; done
    echo "TICK gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"
  fi
  sleep 45
done
wait
say "UC DONE"
sleep 21600
