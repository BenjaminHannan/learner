set -u
J=/job; mkdir -p $J/out $J/export; cd $J
say() { echo "=== $* $(date -u +%FT%TZ)"; }
finish() {
  cd $J; cp -r $J/repo/pipeline/artifacts/stiffness out/ 2>/dev/null; tar -czf export/results.tar.gz out
  (cd export && sha256sum results.tar.gz > MANIFEST.sha256)
  mkdir -p b64 && base64 -w 76 export/results.tar.gz > b64/r.b64 && split -b 1000000 -d -a 3 b64/r.b64 b64/r.p
  (cd b64 && wc -c r.p*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256; say "STIFF $1"; sleep 14400; exit 0; }
say "STIFF START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || finish FAIL-git
R=https://github.com/BenjaminHannan/learner
for i in $(seq 1 60); do  # wait up to ~2 h for main2 to land on the checkpoints branch
  rm -rf repo; git clone -q --depth 1 --filter=blob:none --sparse -b claude/real-pipeline-checkpoints $R repo && (cd repo && git sparse-checkout set pipeline skills) && [ -f repo/skills/main2/final-checkpoint.pt ] && break
  say "waiting for main2 ($i)"; sleep 120; done
[ -f repo/skills/main2/final-checkpoint.pt ] || finish FAIL-nomain2
git clone -q --depth 1 --filter=blob:none --sparse -b claude/project-thread-aya9pk $R mine || finish FAIL-clone2
(cd mine && git sparse-checkout set --no-cone /artifacts/stiffness-test-v1/ /scripts/cap256_launch/skills_pretrain_v1.py /scripts/cap256_launch/score_stiffness_v1.py) || finish FAIL-sparse2
(cd mine && git log -1 --format=%H) > out/mine-commit.txt
P=$J/repo/pipeline
cp mine/scripts/cap256_launch/skills_pretrain_v1.py mine/scripts/cap256_launch/score_stiffness_v1.py $P/scripts/cap256_launch/
M2=$J/repo/skills/main2/final-checkpoint.pt
sha256sum $M2 | tee out/main2-sha.txt
sha256sum $P/artifacts/train-contextual-lr-stability-v1/control/seed0/contextual/final-resume.pt
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.17.0" "safetensors==0.8.0" accelerate > out/pip.log 2>&1 || { tail -3 out/pip.log; finish FAIL-pip; }
[ "$(python -c 'import importlib.metadata as m; print(m.version("torch"))')" = "2.11.0+cu128" ] || PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "torch==2.11.0+cu128" --index-url https://download.pytorch.org/whl/cu128 >> out/pip.log 2>&1
python -c "import torch, transformers, importlib.metadata as m; print(torch.__version__, m.version('torch'), transformers.__version__, m.version('safetensors'))"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
SNAP=$(python -c "from huggingface_hub import snapshot_download as s; print(s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b'))") || finish FAIL-hf
ls -la $SNAP | head; REV=0f604ada3f766f9f257460c4c9f0b5d6f69d431b
H=$J/hf/models--LiquidAI--LFM2.5-1.2B-Instruct; mkdir -p $H/snapshots/$REV $H/blobs; cp -L $SNAP/* $H/snapshots/$REV/ || finish FAIL-cpmodel
SNAP=$H/snapshots/$REV; ls -la $SNAP | head
CD=$P/artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/CONFIGS-v1; mkdir -p $CD
python -c "import json,sys; c=json.load(open('$P/configs/english-pilot-v1/TRAIN-CONFIG-v2.json')); c['lm']['model_path']=sys.argv[1]; json.dump(c,open('$CD/TRAIN-CONFIG-v2.json','w'),indent=1)" "$SNAP"
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch
D=$J/repo/../mine/artifacts/stiffness-test-v1/data
run() { # name seed extra...   each run in its own cwd (the GPU-BUSY marker path is relative on Linux)
  n=$1; s=$2; shift 2; mkdir -p $J/w/$n; cd $J/w/$n
  python $P/scripts/cap256_launch/skills_pretrain_v1.py --root $P --data $D/seed$s --out artifacts/stiffness/$n \
    --updates $UPD --eval-every $EVE --dev-n $DEVN --minutes 40 --copy-path --eval-at-start --no-checkpoint "$@" > $J/out/run-$n.out 2>&1
  cd $J; }
say "SMOKE"
UPD=30 EVE=15 DEVN=10
run smokeA 1 --parent-path $M2
grep -E "Traceback|Error|SKILLS-RESULT" $J/out/run-smokeA.out | head -5 | cut -c1-400
grep -q "SKILLS-RESULT" $J/out/run-smokeA.out || { tail -30 $J/out/run-smokeA.out; finish FAIL-smoke; }
rm -rf $P/artifacts/stiffness/smokeA
say "MAIN"
UPD=4000 EVE=1000 DEVN=200
for W in "1 2" "3 4" "5 6"; do
  PIDS=""
  for s in $W; do run A$s $s --parent-path $M2 & PIDS="$PIDS $!"; done
  for s in $W; do run B$s $s & PIDS="$PIDS $!"; done
  (while true; do sleep 120; for f in $J/out/run-[AB]*.out; do echo "$f $(grep -E 'skills-(progress|eval)' $f | tail -1 | cut -c1-120)"; done; nvidia-smi --query-gpu=memory.used --format=csv,noheader; done) & TICK=$!
  wait $PIDS; kill $TICK 2>/dev/null
done
for f in $J/out/run-[AB]*.out; do grep -E "Traceback|Error" $f | head -3; done
python $P/scripts/cap256_launch/score_stiffness_v1.py $P > $J/out/SCORE.txt 2>&1; cat $J/out/SCORE.txt
finish DONE
