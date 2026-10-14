# LT-2 ladder box (2026-10-14). Runs on a Vast GPU box as `bash -c "$(this file)" lt2`; launch with
#   VAST_BOX=logic_transfer/box/lt2_box.sh python custom_io/box/vast.py create --offer ID --label lt2 --env "MAXH=3"
# Setup (once): this branch's custom_io/ logicgen/ logic_transfer/; the 200k seed-1 skills curriculum (hash-checked) + the 200-per-cell dev build for in_dist
# scoring; the three T1SDR parents from branch claude/lt1-parent-checkpoints (sha256-checked). Then:
#   1. AGREE: GPU course of parent s200 / course seed 1 on rung 0 for 500 updates (full logs: loss and eval at 250, 500, s/update) and the same
#      checkpoint decoded on CPU and GPU (lt2.py agree). Result block "lt2-agree".
#   2. Polls this branch's logic_transfer/box/GO.txt about every 45 s. Each new GO.txt content (sha256) is one order: first line `RUNGS=1 2 3` (the rungs to
#      run, in order, six runs each: parents s200 s201 s204 x course seeds 1 2) and optionally `PROCS=6`, `UPDATES=8000`; a line `STOP` ends the box.
#      After each rung: in_dist scoring of the parents and the stopped checkpoints, then result block "lt2-rung<r>" (no .pt files).
# Result blocks are printed into the container log as base64 (RBEGIN|name|sha|size, R|name|..., REND|name), read with vast.py collect.
# Env: BR (branch), MAXH (stop everything after that many hours of uptime), END_SLEEP / FAIL_SLEEP (seconds the box idles after a clean end / a setup failure).
# No credential is on the box; nothing listens.
set -u
J=/job; mkdir -p $J/out $J/res $J/state $J/w; cd $J
BR=${BR:-claude/project-thread-8u449i}
R=https://github.com/BenjaminHannan/learner
PBR=claude/lt1-parent-checkpoints
MAXH=${MAXH:-0}; END_SLEEP=${END_SLEEP:-600}; FAIL_SLEEP=${FAIL_SLEEP:-1800}; TFVER=${TFVER:-5.17.0}
T0=$(date +%s)
say() { echo "=== $* $(date -u +%FT%TZ)"; }
die() { say "LT2-FAIL $*"; sleep $FAIL_SLEEP; exit 1; }
say "LT2 START"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2; nproc
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || die git
git clone -q --depth 1 --filter=blob:none --sparse -b $BR $R mine && (cd mine && git sparse-checkout set custom_io logicgen logic_transfer && git log -1 --format='mine %H') || die clone-mine
git clone -q --depth 1 --filter=blob:none --sparse -b claude/project-thread-y0sxwe $R cur && (cd cur && git sparse-checkout set skills_curriculum) || die clone-cur
git clone -q --depth 1 --filter=blob:none --sparse -b $PBR $R par && (cd par && git sparse-checkout set t1sdr) || die clone-parents
(cd par/t1sdr && sha256sum -c SHA256SUMS) || die parent-hash
(cd cur && python -m skills_curriculum.build --out $J/data --train 200000 --dev-per-cell 40 --seed 1 > $J/out/build.log 2>&1) || die build
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$J/data/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
(cd cur && python -m skills_curriculum.build --out $J/data_big --train 200000 --dev-per-cell 200 --seed 1 > $J/out/build_big.log 2>&1) || die build-big
[ "$(sha256sum $J/data/train.jsonl | cut -c1-64)" = "$(sha256sum $J/data_big/train.jsonl | cut -c1-64)" ] || die big-train-hash
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==$TFVER" "safetensors==0.8.0" accelerate numpy > out/pip.log 2>&1 || { tail -3 out/pip.log; die pip; }
python -c "import torch, transformers; print(torch.__version__, transformers.__version__, torch.cuda.get_device_name(0))"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
export PYTHONPATH=$J/mine
PD=$J/par/t1sdr
LT="python -m logic_transfer.lt2"
emit() {  # name dir...: tar the small outputs (no .pt, no stdout logs) and print them as base64 lines
  n=$1; shift; T=$J/res/$n.tgz
  tar -czf $T --exclude='*.pt' --exclude='stdout.log' --exclude='train.jsonl' --exclude='dev.jsonl' --exclude='wording.jsonl' --exclude='newwords.jsonl' \
      --exclude='gate.jsonl' --exclude='deeper.jsonl' -C $J/w "$@" 2>/dev/null
  h=$(sha256sum $T | cut -c1-64)
  echo "RBEGIN|$n|$h|$(stat -c %s $T)"; base64 -w 300 $T | sed "s/^/R|$n|/"; echo "REND|$n"
}
over() { [ "$MAXH" != 0 ] && [ $(( $(date +%s) - T0 )) -ge $(awk "BEGIN{print int($MAXH*3600)}") ]; }
say "LT2 READY"
# rows of rungs 1-5 are built in the background (deterministic; sha256 checked against logic_transfer/ladder-hashes.json when listed) while the agreement run goes
mkdir -p $J/w/ladder/rows
for r in 1 2 3 4 5; do (cd mine && nohup python -m logic_transfer.ladder build --rung $r --out $J/w/ladder/rows > $J/out/build-rung$r.log 2>&1 &); done

# ---- 1. agreement + speed rehearsal (rung 0, one run, 500 updates) ----
(cd mine && $LT run --rung 0 --work $J/w/agree --parents-dir $PD --sk200k $J/data --device cuda --procs 1 --threads 2 --updates 500 --eval-n 400 \
   --runs s200:1 --no-falsifier > $J/out/agree-run.log 2>&1); echo "agree-run rc=$?"
tail -3 $J/out/agree-run.log
CK=$J/w/agree/rung0/s200-s1/checkpoint.pt
if [ -f $CK ]; then
  (cd mine && $LT agree --ckpt $CK --rows $J/w/agree/rows/rung0/dev.jsonl --n 400 --out $J/w/agree/agree.json) 2>&1 | tail -2
fi
nvidia-smi --query-gpu=name,memory.used --format=csv,noheader
emit lt2-agree agree/rung0/s200-s1 agree/agree.json agree/rows/rung0/summary.json agree/rung0/DONE.json
say "LT2 AGREE DONE"

# ---- 2. orders from GO.txt ----
last=""
while true; do
  over && { say "LT2 MAXH $MAXH h reached"; break; }
  (cd mine && git fetch -q --depth 1 origin $BR && git reset -q --hard FETCH_HEAD) 2>/dev/null
  G=mine/logic_transfer/box/GO.txt
  if [ -f $G ]; then
    s=$(sha256sum $G | cut -c1-16)
    if [ "$s" != "$last" ]; then
      last=$s
      grep -q '^STOP' $G && { say "LT2 STOP"; break; }
      RUNGS=$(grep -m1 -oE '^RUNGS=.*' $G | cut -d= -f2-); PROCS=$(grep -m1 -oE '^PROCS=[0-9]+' $G | cut -d= -f2); UPDATES=$(grep -m1 -oE '^UPDATES=[0-9]+' $G | cut -d= -f2)
      say "LT2 ORDER $s RUNGS=$RUNGS PROCS=${PROCS:-6} UPDATES=${UPDATES:-8000}"
      for r in $RUNGS; do
        over && break
        say "RUNG $r START"
        for k in $(seq 1 360); do [ -f $J/w/ladder/rows/rung$r/summary.json ] && break; grep -q Traceback $J/out/build-rung$r.log 2>/dev/null && break; sleep 20; done
        [ -f $J/w/ladder/rows/rung$r/summary.json ] || { say "RUNG $r rows missing"; tail -5 $J/out/build-rung$r.log; continue; }
        (cd mine && $LT run --rung $r --work $J/w/ladder --parents-dir $PD --sk200k $J/data --device cuda --procs ${PROCS:-6} --threads 1 --updates ${UPDATES:-8000} \
           --eval-n 0 > $J/out/rung$r-run.log 2>&1); echo "rung $r run rc=$?"; tail -4 $J/out/rung$r-run.log
        (cd mine && $LT indist --work $J/w/ladder --rung $r --parents-dir $PD --big-data $J/data_big --device cuda > $J/out/rung$r-indist.log 2>&1); tail -c 600 $J/out/rung$r-indist.log
        (cd mine && $LT report --work $J/w/ladder --rung $r > $J/w/ladder/rung$r/report.json 2>$J/out/rung$r-report.err)
        emit lt2-rung$r ladder/rung$r ladder/indist ladder/rows/rung$r/summary.json
        say "RUNG $r DONE"
      done
    fi
  fi
  [ $(( $(date +%s) - T0 )) -ge 0 ] && sleep 45
done
say "LT2 DONE"
sleep $END_SLEEP
