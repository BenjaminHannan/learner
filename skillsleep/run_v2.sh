#!/usr/bin/env bash
# Skill-Sleep 2 (skillsleep/PREREG-2.md) on two RTX 4090s. GPU0 = the vLLM server for all tau2 work (day, fix, forks, evals); GPU1 = training.
#   setup -> day -> fix -> build -> [GPU1: train C2s1, C1s1, C3s1, C2s2, C1s2, C3s2 one after another]
#                                 [GPU0: forks -> buildf -> eval A0 -> eval each arm as soon as its merged model exists, then delete its weights]
# Needs ANTHROPIC_API_KEY. Everything lands in $OUT. Rerun-safe: each stage leaves $OUT/.done/<stage> (FORCE=1 ignores them). Models, venvs, tau2 live in $WORK.
#   OUT (default $GPUQ_OUT)  WORK (default /tmp/ss2_$GPUQ_NAME)  CONC=10 EVAL_CONC=16 EPOCHS=8 ARM_MIN=40 TOTAL_MIN=990 DAY_MIN=45 FIX_MIN=25 FORK_MIN=90
#   ORDER="C2s1 C1s1 C3s1 C2s2 C1s2 C3s2"  MAXTOK=16384 MAXTOK_PAIR=12288 (night length caps, see build.py)  other train.py knobs (LR, ACCUM, BETA, ...) pass through.
# Never a bare `wait`: it would also wait for the vLLM server and the tee process substitution (that hung run 1). Every wait names its PID.
set -u
ROOT=${GPUQ_SRC:-$(pwd)}; SS=$ROOT/skillsleep; OUT=${OUT:-${GPUQ_OUT:-$ROOT/out}}; WORK=${WORK:-/tmp/ss2_${GPUQ_NAME:-run}}
mkdir -p $OUT/.done $OUT/.skip $OUT/data $OUT/day $OUT/fix $OUT/forks $WORK; exec > >(tee -a $OUT/run_v2.log) 2>&1
IFS=, read -r G0 G1 _ <<< "${CUDA_VISIBLE_DEVICES:-0,1}"; G1=${G1:-1}  # the two cards the queue gave us (as nvidia-smi ids)
CONC=${CONC:-10}; EVAL_CONC=${EVAL_CONC:-16}; EPOCHS=${EPOCHS:-8}; ARM_MIN=${ARM_MIN:-40}; TOTAL_MIN=${TOTAL_MIN:-990}; DAY_MIN=${DAY_MIN:-45}; FIX_MIN=${FIX_MIN:-25}
FORK_MIN=${FORK_MIN:-90}; FIX_PAR=${FIX_PAR:-5}; ORDER=${ORDER:-"C2s1 C1s1 C3s1 C2s2 C1s2 C3s2"}; export OUT SS EPOCHS
export FIX_TRIALS=3 FIX_CONC=3 FIX_TASK_MIN=20 HF_HOME=${HF_HOME:-$WORK/hf} SPEED_RETRY_LOG=$OUT/speed_retry.log
export T2DIR=$WORK/tau2 T2VENV=$WORK/t2venv; PYV=$WORK/venv/bin/python; PY2=$T2VENV/bin/python; SIM=$T2DIR/data/simulations; PORT=8000
START=$(date +%s); echo ${GPUQ_ATTEMPT:-1} > $OUT/.attempt; SERVED=""; VLLM_PID=""; TRAIN_PID=""; KW='{}'; MAXTOK_GEN=4096
echo "=== skillsleep2 start $(date -u +%FT%TZ) attempt=${GPUQ_ATTEMPT:-1} gpu0=$G0 gpu1=$G1 conc=$CONC eval_conc=$EVAL_CONC epochs=$EPOCHS done=[$(ls $OUT/.done | tr '\n' ' ')]"
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "=== BB FAIL ANTHROPIC_API_KEY not set"; exit 1; }
export ANTHROPIC_API_BASE=${ANTHROPIC_API_BASE:-${ANTHROPIC_BASE_URL:-https://api.anthropic.com}}
nvidia-smi --query-gpu=index,name,memory.total --format=csv

stage() {  # stage NAME FN [args]: run once, log timing, leave a done-marker
  local n=$1; shift
  [ ! -f $OUT/.done/$n ] || [ "${FORCE:-0}" = 1 ] || { echo "=== STAGE $n skipped (done)"; return 0; }
  local t0=$(date +%s); echo "=== STAGE $n start $(date -u +%T)"
  "$@"; local rc=$?; local dt=$(( $(date +%s) - t0 ))
  echo "=== STAGE $n rc=$rc ${dt}s"; printf '%s\t%s\t%s\n' $n $rc $dt >> $OUT/timings.tsv
  [ $rc -eq 0 ] && touch $OUT/.done/$n
  return $rc
}
left() { echo $(( TOTAL_MIN * 60 - ($(date +%s) - START) )); }
summ() { python3 $SS/common.py summarize "$@" >> $OUT/summary.jsonl; }  # summ ARM DOMAIN WALL_S FILES...

# ---------- GPU0: the vLLM server (only ever touches GPU0) ----------
g0_used() { local u; u=$(nvidia-smi -i $G0 --query-gpu=memory.used --format=csv,noheader,nounits 2> /dev/null | head -1 | tr -d ' '); echo ${u:-99999}; }
kill_vllm() {
  [ -n "$VLLM_PID" ] && kill -TERM -- -$VLLM_PID 2> /dev/null
  for i in $(seq 1 30); do  # the engine child can keep GPU memory after the API server dies
    [ "$(g0_used)" -lt 2000 ] && { VLLM_PID=""; SERVED=""; return 0; }
    if [ $i -eq 6 ]; then
      [ -n "$VLLM_PID" ] && kill -KILL -- -$VLLM_PID 2> /dev/null
      nvidia-smi -i $G0 --query-compute-apps=pid --format=csv,noheader 2> /dev/null | xargs -r kill -9 2> /dev/null  # whatever still holds GPU0, nothing on GPU1
    fi
    sleep 5
  done
  echo "=== WARN kill_vllm: GPU0 memory still in use"; return 1
}
serve() {  # serve MODEL_DIR TAG: the swap-1 serving config (thinking off, k2_horizon tool parser, nothink template) on GPU0.
  # 24 GB: 0.80 of it for vLLM and 2048-token prefill chunks, so the prompt-logprob buffers of the forks stage (vocab 250k) fit outside the pool.
  if [ "$SERVED" = "$2" ] && curl -sf localhost:$PORT/v1/models > /dev/null; then return 0; fi
  kill_vllm || return 1
  local extra
  for extra in "" "--model-impl transformers"; do
    CUDA_VISIBLE_DEVICES=$G0 setsid $WORK/venv/bin/vllm serve $1 --served-model-name m --port $PORT --dtype bfloat16 --max-model-len 49152 --gpu-memory-utilization 0.80 \
      --max-num-batched-tokens 2048 --trust-remote-code --tool-call-parser k2_horizon --chat-template $SS/templates/k2_nothink.jinja --enable-auto-tool-choice $extra \
      > $OUT/vllm_$2.log 2>&1 &
    VLLM_PID=$!
    for i in $(seq 1 120); do
      curl -sf localhost:$PORT/v1/models > /dev/null 2>&1 && { SERVED=$2; echo "vllm up: $2 $extra"; return 0; }
      kill -0 $VLLM_PID 2> /dev/null || break
      sleep 10
    done
    echo "=== vllm failed for $2 ($extra):"; grep -E "Error|error" $OUT/vllm_$2.log | grep -v "^ *File" | tail -5 | cut -c1-300
    cp $OUT/vllm_$2.log $OUT/vllm_$2.first.log; kill_vllm
  done
  return 1
}

# ---------- setup ----------
setup_fn() {
  git --version || return 1
  export PATH=$PATH:$HOME/.local/bin
  command -v uv > /dev/null || pip install -q --user -U uv 2>&1 | tail -1
  # our own venv for vLLM + training (the shared one is left alone): the versions of run 1 (vllm 0.32.0, peft 0.21.2, transformers 5.19), wheels picked for this driver
  [ -x $PYV ] || uv venv -q --python 3.12 $WORK/venv || return 1
  uv pip install -q -p $PYV --torch-backend=auto "vllm==0.32.0" "peft==0.21.2" pyarrow huggingface_hub anthropic numpy 2>&1 | tail -3
  $PYV -c "from huggingface_hub import snapshot_download as s; print(s('IFM/K2-Horizon-3.7B'))" > $OUT/data/base_path 2> $OUT/data/base_dl.log &
  local DL=$!
  $PYV -c "import vllm, torch, transformers, peft, anthropic; print('vllm', vllm.__version__, 'torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__, 'cuda', torch.cuda.device_count())" || return 1
  [ -d $T2DIR ] || git clone -q https://github.com/sierra-research/tau2-bench $T2DIR
  (cd $T2DIR && git checkout -q cc1df47 \
    && { git apply --check $SS/tau2-judge-haiku.patch 2> /dev/null && git apply $SS/tau2-judge-haiku.patch || echo "judge patch already applied"; } \
    && python3 $SS/patch_hint.py $T2DIR) || { echo "=== tau2 setup failed"; return 1; }
  [ -x $T2VENV/bin/tau2 ] || { uv venv -q $T2VENV && (cd $T2DIR && UV_PROJECT_ENVIRONMENT=$T2VENV uv sync -q 2>&1 | tail -2); }
  $PY2 -c "import tau2.agent.llm_agent as a, inspect; assert 'SKILLSLEEP_HINT' in inspect.getsource(a.LLMAgent); print('hint patch active')" 2> /dev/null || return 1
  (cd $T2DIR && $PY2 $SS/dump_env.py $OUT/data retail airline) 2> /dev/null || return 1
  wait $DL; BASE=$(tail -1 $OUT/data/base_path)
  [ -f $BASE/config.json ] || { echo "=== base model download failed"; tail -3 $OUT/data/base_dl.log; return 1; }
  echo "stage 0: render unit check"; $PYV $SS/render.py $BASE $OUT/data/env_retail.json || { echo "=== RENDER SELFTEST FAILED"; return 1; }
}
trap '[ -n "$TRAIN_PID" ] && { pkill -TERM -P $TRAIN_PID; kill $TRAIN_PID; } 2> /dev/null; kill_vllm' EXIT
# a retry on a box that lost $WORK (or the model cache) must redo the setup even though its marker is in $OUT
[ -x $PYV ] && [ -x $T2VENV/bin/tau2 ] && [ -f "$(tail -1 $OUT/data/base_path 2> /dev/null)/config.json" ] || rm -f $OUT/.done/setup
if ! stage setup setup_fn; then echo "=== BB FAIL setup"; exit 1; fi
BASE=$(tail -1 $OUT/data/base_path)
export ARGS=$(python3 -c "import json,sys; print(json.dumps({'api_base':'http://localhost:%s/v1' % sys.argv[3],'api_key':'none','max_tokens':int(sys.argv[2]),'num_retries':2,'extra_body':{'chat_template_kwargs':json.loads(sys.argv[1])}}))" "$KW" $MAXTOK_GEN $PORT)

# ---------- day, fix ----------
day_fn() {
  $PYV $SS/anchors.py $BASE $OUT/data/anchors.jsonl > $OUT/anchors.log 2>&1; tail -2 $OUT/anchors.log
  local t0=$(date +%s)
  bash $SS/t2.sh ss_day retail train 2 $CONC $((DAY_MIN * 60)) > $OUT/day/tau2.log 2>&1; echo "day tau2 rc=$?"
  [ -f $SIM/ss_day/results.json ] || { echo "=== no day results"; tail -20 $OUT/day/tau2.log; return 1; }
  python3 $SS/common.py strip $SIM/ss_day/results.json $OUT/day/results.json.gz && summ day retail_train $(( $(date +%s) - t0 )) $OUT/day/results.json.gz
  tail -1 $OUT/summary.jsonl | cut -c1-200
}
fix_fn() {
  [ -f $OUT/day/results.json.gz ] || { echo "=== fix needs the day results"; return 1; }
  $PYV $SS/fix.py $OUT/day/results.json.gz $OUT/data/env_retail.json $OUT/fix/hints.json > $OUT/fix/fix.log 2>&1; tail -4 $OUT/fix/fix.log
  [ -f $OUT/fix/hints.json ] || return 1
  local tasks=$(python3 -c "import json; print(' '.join(json.load(open('$OUT/fix/hints.json'))))")
  [ -n "$tasks" ] || { echo "no tasks to fix"; return 0; }
  local t0=$(date +%s) t
  echo $tasks | tr ' ' '\n' | timeout -k 30 $((FIX_MIN * 60)) xargs -P $FIX_PAR -I{} bash $SS/retry_one.sh {}
  for t in $tasks; do
    [ -f $SIM/ss_fix_$t/results.json ] && python3 $SS/common.py strip $SIM/ss_fix_$t/results.json $OUT/fix/$t.json.gz
  done
  summ fix retail_train_retry $(( $(date +%s) - t0 )) $(ls $OUT/fix/[0-9]*.json.gz 2> /dev/null); tail -1 $OUT/summary.jsonl | cut -c1-200
}
fixfiles() { ls $OUT/fix/[0-9]*.json.gz 2> /dev/null; }

# ---------- build (positives, pairs, negatives), forks, fork pairs ----------
build_fn() {
  $PYV $SS/build.py $BASE $OUT/data/env_retail.json $OUT/data $OUT/day/results.json.gz $(fixfiles) | tail -3 || return 1
  [ -s $OUT/data/anchors.jsonl ] && [ -s $OUT/data/night.jsonl ] || { echo "=== night data missing"; return 1; }
}
forks_fn() {  # score the day with the base model, force runner-ups, replay the forks in tau2; time cap FORK_MIN, partial results kept
  local dl=$(( $(date +%s) + FORK_MIN * 60 ))
  [ -s $OUT/forks/forks.json.gz ] || $PYV $SS/forks.py make $BASE $OUT/data/env_retail.json $OUT/forks/forks.json.gz $OUT/day/results.json.gz $(fixfiles) > $OUT/forks/make.log 2>&1
  tail -2 $OUT/forks/make.log
  [ -s $OUT/forks/forks.json.gz ] || { echo "=== no forks made"; return 1; }
  local left=$(( dl - $(date +%s) )); [ $left -lt 120 ] && left=120
  (cd $T2DIR && PYTHONPATH=$SS/retry timeout -k 30 $left $PY2 $SS/forks_run.py retail train $OUT/forks/forks.json.gz $OUT/forks/results.jsonl $EVAL_CONC $dl "$ARGS") > $OUT/forks/run.log 2>&1
  echo "forks_run rc=$?"; tail -2 $OUT/forks/run.log; return 0
}
buildf_fn() {
  [ -s $OUT/forks/results.jsonl ] || { echo "=== no fork results: C3 will equal C2"; : > $OUT/data/forks.jsonl; return 0; }
  $PYV $SS/forks.py pairs $BASE $OUT/data/env_retail.json $OUT/forks/results.jsonl $OUT/forks/forks.json.gz $OUT/data/forks.jsonl $OUT/day/results.json.gz $(fixfiles) | tail -3
  [ -f $OUT/data/forks.jsonl ] || : > $OUT/data/forks.jsonl
}

# ---------- GPU1: training, one arm after another ----------
train_need() { case $1 in C1*) echo 90;; *) echo 210;; esac; }  # minutes on a 4090 (a guess; the budget guard only skips a start that cannot finish)
train_fn() {  # train_fn ARMSEED, e.g. C2s1
  local a=$1 c=${1%s*} s=${1##*s} d=$WORK/merged_$1
  if [ $(( $(left) / 60 )) -lt $(( $(train_need $a) + 40 )) ]; then echo "=== $a: not enough time left, skipped"; touch $OUT/.skip/train_$a; return 1; fi
  rm -rf $d; ln -sf $OUT/train_$a.log $d.log; : > $OUT/train_$a.log
  CUDA_VISIBLE_DEVICES=$G1 SEED=$s FORKS=$OUT/data/forks.jsonl PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    $PYV $SS/train.py $c $BASE $OUT/data/night.jsonl $OUT/data/anchors.jsonl $d > $OUT/train_$a.out 2>&1
  local rc=$?; cp $d/train_info.json $OUT/train_info_$a.json 2> /dev/null; tail -n 3 $OUT/train_$a.out | cut -c1-200
  [ $rc -eq 0 ] && grep -q "TRAIN DONE" $OUT/train_$a.log || { touch $OUT/.skip/train_$a; return 1; }
}
trainer() {  # runs in the background; C3 waits for the fork pairs
  local a
  for a in $ORDER; do
    if [ -f $OUT/.done/train_$a ] && { [ -f $OUT/.done/eval_$a ] || ls $WORK/merged_$a/*.safetensors > /dev/null 2>&1; }; then echo "[gpu1] $a already trained"; continue; fi
    rm -f $OUT/.done/train_$a $OUT/.skip/train_$a
    case $a in C3*) while [ ! -f $OUT/.done/buildf ] && [ ! -f $OUT/.skip/buildf ]; do sleep 30; done;; esac
    echo "[gpu1] training $a $(date -u +%T)"; stage train_$a train_fn $a
  done
  echo "[gpu1] trainer finished"
}

# ---------- evals on GPU0 ----------
evalrun() {  # evalrun ARM: retail test x4 + airline test x2 in parallel, cut off after ARM_MIN (or the job budget); partial results are kept
  local arm=$1 t0=$(date +%s) d; mkdir -p $OUT/$arm; rm -rf $SIM/ss_${arm}_retail $SIM/ss_${arm}_airline
  local lim=$(( ARM_MIN * 60 )) rem=$(( $(left) - 600 ))
  [ $rem -lt $lim ] && lim=$rem
  [ $lim -lt 300 ] && { echo "=== no time left for $arm eval"; return 1; }
  local rc=$(( EVAL_CONC * 4 / 5 )); [ $rc -lt 1 ] && rc=1; local ac=$(( EVAL_CONC - rc )); [ $ac -lt 1 ] && ac=1
  bash $SS/t2.sh ss_${arm}_retail retail test 4 $rc $lim > $OUT/$arm/tau2_retail.log 2>&1 & local p1=$!
  bash $SS/t2.sh ss_${arm}_airline airline test 2 $ac $lim > $OUT/$arm/tau2_airline.log 2>&1 & local p2=$!
  wait $p1 $p2
  for d in retail airline; do
    if [ -f $SIM/ss_${arm}_$d/results.json ]; then
      python3 $SS/common.py strip $SIM/ss_${arm}_$d/results.json $OUT/$arm/${d}_test.json.gz && summ $arm ${d}_test $(( $(date +%s) - t0 )) $OUT/$arm/${d}_test.json.gz
      tail -1 $OUT/summary.jsonl | cut -c1-160
    else echo "=== $arm $d: no results"; tail -5 $OUT/$arm/tau2_$d.log; fi
  done
}
arc_arm() {  # arc_arm ARM MODEL_DIR (stops the GPU0 server first; the HF model needs the card)
  kill_vllm; mkdir -p $OUT/$1
  local line=$(CUDA_VISIBLE_DEVICES=$G0 $PYV $SS/arc.py $2 $1 2> $OUT/$1/arc.log | grep '^{' | tail -1)
  [ -n "$line" ] || { echo "=== ARC failed for $1"; tail -5 $OUT/$1/arc.log; return 1; }
  echo "$line" >> $OUT/summary.jsonl; echo "$line" | cut -c1-160
}
evalA0_fn() {
  serve $BASE base || return 1
  evalrun A0; arc_arm A0 $BASE
}
eval_arm() {  # eval_arm ARMSEED: wait for the merged model, serve it, smoke test, tau2 test sets, ARC, then delete the weights
  local a=$1 d=$WORK/merged_$1
  while [ ! -f $OUT/.done/train_$a ] && [ ! -f $OUT/.skip/train_$a ] && kill -0 $TRAIN_PID 2> /dev/null; do sleep 30; done
  [ -f $OUT/.done/train_$a ] || { echo "=== $a: no trained model, eval skipped"; return 1; }
  [ -f $d/config.json ] || { echo "=== $a: no merged model"; return 1; }
  serve $d $a || { echo "=== $a SERVE-FAIL"; return 1; }
  python3 $SS/smoke.py "$KW" > $OUT/$a/smoke.json 2>&1; echo "smoke: $(head -c 300 $OUT/$a/smoke.json)"
  evalrun $a; arc_arm $a $d
  rm -f "${d:?}"/*.safetensors  # free disk; config/tokenizer stay
}

# ---------- run ----------
if [ ! -f $OUT/.done/evalA0 ] || [ ! -f $OUT/.done/forks ] || [ ! -f $OUT/.done/day ] || [ ! -f $OUT/.done/fix ]; then serve $BASE base || { echo "=== base SERVE-FAIL"; exit 1; }; fi
stage day day_fn; stage fix fix_fn
stage build build_fn || { echo "=== BB FAIL build"; exit 1; }
trainer & TRAIN_PID=$!  # GPU1 starts as soon as the night data (without fork pairs) exists
stage forks forks_fn; stage buildf buildf_fn || touch $OUT/.skip/buildf
stage evalA0 evalA0_fn
for a in $ORDER; do stage eval_$a eval_arm $a; done
wait $TRAIN_PID; TRAIN_PID=""
kill_vllm
FORCE=1 stage report bash -c "$PYV $SS/analyze.py $OUT/summary.jsonl | tee $OUT/report.md"
gzip -f $OUT/data/night.jsonl $OUT/data/forks.jsonl $OUT/forks/results.jsonl 2> /dev/null
echo "=== skillsleep2 done $(date -u +%FT%TZ) elapsed $(( $(date +%s) - START ))s"
