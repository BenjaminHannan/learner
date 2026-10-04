set -u
J=/job; mkdir -p $J/out $J/export; cd $J
say() { echo "=== $* $(date -u +%FT%TZ)"; }
finish() {
  cd $J; cp -r $J/repo/pipeline/artifacts/plateau out/ 2>/dev/null; tar -czf export/results.tar.gz --exclude=pip.log out
  (cd export && sha256sum results.tar.gz > MANIFEST.sha256)
  mkdir -p b64 && base64 -w 76 export/results.tar.gz > b64/r.b64 && split -b 1000000 -d -a 3 b64/r.b64 b64/r.p
  (cd b64 && wc -c r.p*) > export/PARTS.txt
  say "MANIFEST"; cat export/MANIFEST.sha256; ls -la export/results.tar.gz
  echo "B64BEGIN"; base64 -w 76 export/results.tar.gz; echo "B64END"
  say "FIX $1"; sleep 14400; exit 0; }
say "FIX START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || finish FAIL-git
R=https://github.com/BenjaminHannan/learner
for i in $(seq 1 60); do  # wait up to ~2 h for main2 to land on the checkpoints branch
  rm -rf repo; git clone -q --depth 1 --filter=blob:none --sparse -b claude/real-pipeline-checkpoints $R repo && (cd repo && git sparse-checkout set pipeline skills) && [ -f repo/skills/main2/final-checkpoint.pt ] && break
  say "waiting for main2 ($i)"; sleep 120; done
[ -f repo/skills/main2/final-checkpoint.pt ] || finish FAIL-nomain2
git clone -q --depth 1 --filter=blob:none --sparse -b claude/project-thread-aya9pk $R mine || finish FAIL-clone2
(cd mine && git sparse-checkout set --no-cone /artifacts/fix-screen-v1/ /scripts/cap256_launch/skills_pretrain_v1.py /scripts/cap256_launch/score_plateau_v1.py) || finish FAIL-sparse2
(cd mine && git log -1 --format=%H) > out/mine-commit.txt
P=$J/repo/pipeline
cp mine/scripts/cap256_launch/skills_pretrain_v1.py mine/scripts/cap256_launch/score_plateau_v1.py $P/scripts/cap256_launch/
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
git clone -q --depth 1 --filter=blob:none --sparse -b claude/project-thread-y0sxwe $R cur && (cd cur && git sparse-checkout set skills_curriculum) || finish FAIL-clone3
(cd cur && python -m skills_curriculum.build --out $J/data --train 200000 --dev-per-cell 40 --seed 1 > $J/out/build.log 2>&1) || finish FAIL-build
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$J/data/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || finish FAIL-hash
D=$J/data
run() { # name extra...   each run in its own cwd (the GPU-BUSY marker path is relative on Linux)
  n=$1; shift; mkdir -p $J/w/$n; cd $J/w/$n
  python $P/scripts/cap256_launch/skills_pretrain_v1.py --root $P --data $D --out artifacts/plateau/$n \
    --parent-path $M2 --copy-path --no-checkpoint --minutes 150 "$@" > $J/out/run-$n.out 2>&1
  cd $J; }
say "SMOKE"
run smoke --families arith_bare,seq_next --sample-seed 9 --fixed-rows 20 --passes 2 --updates 40 --eval-every 20 --dev-n 10 --eval-at-start --rounds 8 --reader-hidden 256
grep -E "Traceback|Error|SKILLS-RESULT|widened" $J/out/run-smoke.out | head -5 | cut -c1-600
grep -q "SKILLS-RESULT" $J/out/run-smoke.out || { tail -30 $J/out/run-smoke.out; finish FAIL-smoke; }
rm -rf $P/artifacts/plateau/smoke
W=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
COMMON="--families $W --updates 6000 --eval-every 3000 --dev-n 320 --eval-at-start --fixed-rows 2000 --passes 3"
arm() { case $1 in W) echo "--reader-hidden 256";; L) echo "--rounds 8";; O) echo "--lr-mult 0.3";; esac; }
for WAVE in "W1 W2 W3 L1 L2" "L3 O1 O2 O3"; do
  say "WAVE $WAVE"; PIDS=""
  for x in $WAVE; do run $x $COMMON --sample-seed ${x:1:1} $(arm ${x:0:1}) & PIDS="$PIDS $!"; done
  (while true; do sleep 180; for f in $J/out/run-[WLO]*.out; do echo "$f $(grep -E 'skills-(progress|eval)' $f | tail -1 | cut -c1-160)"; done; nvidia-smi --query-gpu=memory.used --format=csv,noheader; done) & TICK=$!
  wait $PIDS; kill $TICK 2>/dev/null
done
for f in $J/out/run-[WLO]*.out; do grep -E "Traceback|Error" $f | head -3; done
finish DONE
