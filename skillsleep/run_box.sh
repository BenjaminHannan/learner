#!/usr/bin/env bash
# Skill-Sleep 1 box job (see skillsleep/PREREG.md): day -> fix -> build -> train A1/A2 -> eval A0/A1/A2 -> report, on one RTX 5090.
# Needs ANTHROPIC_API_KEY in the env. Everything lands in out/ (pack root = cwd) and out.tgz. Rerun-safe: each stage leaves out/.done/<stage>.
#   STAGES=setup,day,fix,evalA0,arcA0,build,trainA1,trainA2,evalA2,evalA1,report   (aliases: train = trainA1,trainA2; eval = evalA0,arcA0,evalA2,evalA1)
#   CONC=10 EVAL_CONC=$CONC ARM_MIN=35 TOTAL_MIN=145 DAY_MIN=45 FIX_MIN=25 FIX_PAR=5 FORCE=1 (ignore done-markers); LR/EPOCHS/ACCUM/BETA/... go to train.py
set -u
ROOT=$(pwd); OUT=$ROOT/out; SS=$ROOT/skillsleep; mkdir -p $OUT/.done $OUT/data $OUT/day $OUT/fix
exec > >(tee -a $OUT/run_box.log) 2>&1
expand() { local o="" s; for s in ${1//,/ }; do case $s in train) o+=trainA1,trainA2,;; eval) o+=evalA0,arcA0,evalA2,evalA1,;; *) o+=$s,;; esac; done; echo ${o%,}; }
STAGES=$(expand "${STAGES:-setup,day,fix,evalA0,arcA0,build,trainA1,trainA2,evalA2,evalA1,report}")
want() { [[ ",$STAGES," == *",$1,"* ]]; }
want setup || STAGES=setup,$STAGES
CONC=${CONC:-10}; EVAL_CONC=${EVAL_CONC:-$CONC}; ARM_MIN=${ARM_MIN:-35}; TOTAL_MIN=${TOTAL_MIN:-145}; DAY_MIN=${DAY_MIN:-45}; FIX_MIN=${FIX_MIN:-25}
FIX_PAR=${FIX_PAR:-5}; FIX_TRIALS=3; FIX_CONC=3; FIX_TASK_MIN=20
[ -f $OUT/.start ] || date +%s > $OUT/.start
START=$(cat $OUT/.start); PY2=/job/t2venv/bin/python; SERVED=""
echo "=== skillsleep start $(date -u +%FT%TZ) stages=$STAGES conc=$CONC"
nvidia-smi --query-gpu=name,memory.total --format=csv

pending() { want $1 && { [ ! -f $OUT/.done/$1 ] || [ "${FORCE:-0}" = 1 ]; }; }
stage() {  # stage NAME FN [args]: run once, log timing, leave a done-marker
  local n=$1; shift
  pending $n || { echo "=== STAGE $n skipped"; return 0; }
  local t0=$(date +%s); echo "=== STAGE $n start $(date -u +%T)"
  "$@"; local rc=$?; local dt=$(( $(date +%s) - t0 ))
  echo "=== STAGE $n rc=$rc ${dt}s"; printf '%s\t%s\t%s\n' $n $rc $dt >> $OUT/timings.tsv
  [ $rc -eq 0 ] && touch $OUT/.done/$n
  return $rc
}
left() { echo $(( TOTAL_MIN * 60 - ($(date +%s) - START) )); }

kill_vllm() {
  pkill -f "vllm serve" 2> /dev/null; pkill -f EngineCore 2> /dev/null; sleep 5; SERVED=""
  for i in $(seq 1 30); do  # the engine child can keep GPU memory after the API server dies
    [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)" -lt 2000 ] && return 0
    pkill -9 -f "vllm|EngineCore" 2> /dev/null; sleep 5
  done
}
serve() {  # serve MODEL_DIR TAG: the swap-1 serving config (thinking off, k2_horizon tool parser, nothink template)
  if [ "$SERVED" = "$2" ] && curl -sf localhost:8000/v1/models > /dev/null; then return 0; fi
  kill_vllm
  local extra
  for extra in "" "--model-impl transformers"; do
    vllm serve $1 --served-model-name m --port 8000 --dtype bfloat16 --max-model-len 49152 --gpu-memory-utilization 0.90 \
      --trust-remote-code --tool-call-parser k2_horizon --chat-template $SS/templates/k2_nothink.jinja --enable-auto-tool-choice $extra > $OUT/vllm_$2.log 2>&1 &
    for i in $(seq 1 90); do
      curl -sf localhost:8000/v1/models > /dev/null 2>&1 && { SERVED=$2; echo "vllm up: $2 $extra"; return 0; }
      pgrep -f "vllm serve" > /dev/null || break
      sleep 10
    done
    echo "=== vllm failed for $2 ($extra):"; grep -E "Error|error" $OUT/vllm_$2.log | grep -v "^ *File" | tail -5 | cut -c1-300
    cp $OUT/vllm_$2.log $OUT/vllm_$2.first.log; kill_vllm
  done
  return 1
}
summ() { python3 $SS/common.py summarize "$@" >> $OUT/summary.jsonl; }  # summ ARM DOMAIN WALL_S FILES...

# ---------- setup ----------
setup_fn() {
  (apt-get update -qq && apt-get install -y -qq git curl) > /dev/null 2>&1; git --version
  pip install -q -U uv 2>&1 | tail -1
  python3 -c "from huggingface_hub import snapshot_download as s; print(s('IFM/K2-Horizon-3.7B'))" > $OUT/data/base_path 2> $OUT/data/base_dl.log &
  local DL=$!
  uv pip install --system -q -U vllm 2>&1 | tail -3
  uv pip install --system -q peft pyarrow 2>&1 | tail -2
  python3 -c "import vllm, torch, transformers, peft; print('vllm', vllm.__version__, 'torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__)" || return 1
  [ -d /job/tau2 ] || git clone -q https://github.com/sierra-research/tau2-bench /job/tau2
  cd /job/tau2 && git checkout -q cc1df47 \
    && { git apply --check $SS/tau2-judge-haiku.patch 2> /dev/null && git apply $SS/tau2-judge-haiku.patch || echo "judge patch already applied"; } \
    && python3 $SS/patch_hint.py /job/tau2 || { echo "=== tau2 setup failed"; return 1; }
  [ -x /job/t2venv/bin/tau2 ] || { uv venv -q /job/t2venv && UV_PROJECT_ENVIRONMENT=/job/t2venv uv sync -q 2>&1 | tail -2; }
  cd $ROOT; $PY2 -c "import os; print('key set:', bool(os.environ.get('ANTHROPIC_API_KEY')))"
  $PY2 -c "import tau2.agent.llm_agent as a, inspect; assert 'SKILLSLEEP_HINT' in inspect.getsource(a.LLMAgent); print('hint patch active')" || return 1
  (cd /job/tau2 && $PY2 $SS/dump_env.py $OUT/data retail airline) || return 1
  wait $DL; local BASE=$(tail -1 $OUT/data/base_path)
  [ -f $BASE/config.json ] || { echo "=== base model download failed"; tail -3 $OUT/data/base_dl.log; return 1; }
  echo "stage 0: render unit check"; python3 $SS/render.py $BASE $OUT/data/env_retail.json || { echo "=== RENDER SELFTEST FAILED"; return 1; }
}
unset ANTHROPIC_BASE_URL; export ANTHROPIC_API_BASE=https://api.anthropic.com
if ! stage setup setup_fn; then echo "=== BB FAIL setup"; exit 1; fi
BASE=$(tail -1 $OUT/data/base_path)
KW='{}'; MAXTOK=4096
export OUT SS FIX_TRIALS FIX_CONC FIX_TASK_MIN
export ARGS=$(python3 -c "import json,sys; print(json.dumps({'api_base':'http://localhost:8000/v1','api_key':'none','max_tokens':int(sys.argv[2]),'num_retries':2,'extra_body':{'chat_template_kwargs':json.loads(sys.argv[1])}}))" "$KW" $MAXTOK)
SIM=/job/tau2/data/simulations

# ---------- 1 day, 2 fix ----------
day_fn() {
  python3 $SS/anchors.py $BASE $OUT/data/anchors.jsonl > $OUT/anchors.log 2>&1; tail -2 $OUT/anchors.log
  local t0=$(date +%s)
  bash $SS/t2.sh ss_day retail train 2 $CONC $((DAY_MIN * 60)) > $OUT/day/tau2.log 2>&1; echo "day tau2 rc=$?"
  [ -f $SIM/ss_day/results.json ] || { echo "=== no day results"; tail -20 $OUT/day/tau2.log; return 1; }
  python3 $SS/common.py strip $SIM/ss_day/results.json $OUT/day/results.json.gz && summ day retail_train $(( $(date +%s) - t0 )) $OUT/day/results.json.gz
  tail -1 $OUT/summary.jsonl | cut -c1-200
}
fix_fn() {
  [ -f $OUT/day/results.json.gz ] || { echo "=== fix needs the day results"; return 1; }
  $PY2 $SS/fix.py $OUT/day/results.json.gz $OUT/data/env_retail.json $OUT/fix/hints.json > $OUT/fix/fix.log 2>&1; tail -3 $OUT/fix/fix.log
  local tasks=$(python3 -c "import json; print(' '.join(json.load(open('$OUT/fix/hints.json'))))")
  [ -n "$tasks" ] || { echo "no tasks to fix"; return 0; }
  local t0=$(date +%s) t
  echo $tasks | tr ' ' '\n' | timeout -k 30 $((FIX_MIN * 60)) xargs -P $FIX_PAR -I{} bash $SS/retry_one.sh {}
  for t in $tasks; do
    [ -f $SIM/ss_fix_$t/results.json ] && python3 $SS/common.py strip $SIM/ss_fix_$t/results.json $OUT/fix/$t.json.gz
  done
  summ fix retail_train_retry $(( $(date +%s) - t0 )) $(ls $OUT/fix/[0-9]*.json.gz 2> /dev/null); tail -1 $OUT/summary.jsonl | cut -c1-200
}

# ---------- 5 eval ----------
evalrun() {  # evalrun ARM: retail test x4 + airline test x2 in parallel, cut off after ARM_MIN (or the job budget); partial results are kept
  local arm=$1 t0=$(date +%s) d; mkdir -p $OUT/$arm
  local lim=$(( ARM_MIN * 60 )) rem=$(( $(left) - 600 ))
  [ $rem -lt $lim ] && lim=$rem
  [ $lim -lt 300 ] && { echo "=== no time left for $arm eval"; return 1; }
  local rc=$(( EVAL_CONC * 4 / 5 )); [ $rc -lt 1 ] && rc=1; local ac=$(( EVAL_CONC - rc )); [ $ac -lt 1 ] && ac=1
  bash $SS/t2.sh ss_${arm}_retail retail test 4 $rc $lim > $OUT/$arm/tau2_retail.log 2>&1 &
  bash $SS/t2.sh ss_${arm}_airline airline test 2 $ac $lim > $OUT/$arm/tau2_airline.log 2>&1 &
  wait
  for d in retail airline; do
    if [ -f $SIM/ss_${arm}_$d/results.json ]; then
      python3 $SS/common.py strip $SIM/ss_${arm}_$d/results.json $OUT/$arm/${d}_test.json.gz && summ $arm ${d}_test $(( $(date +%s) - t0 )) $OUT/$arm/${d}_test.json.gz
      tail -1 $OUT/summary.jsonl | cut -c1-160
    else echo "=== $arm $d: no results"; tail -5 $OUT/$arm/tau2_$d.log; fi
  done
}
arc_arm() {  # arc_arm ARM MODEL_DIR (stops vLLM first; the HF model needs the GPU)
  kill_vllm; mkdir -p $OUT/$1
  local line=$(python3 $SS/arc.py $2 $1 2> $OUT/$1/arc.log | grep '^{' | tail -1)
  [ -n "$line" ] || { echo "=== ARC failed for $1"; tail -5 $OUT/$1/arc.log; return 1; }
  echo "$line" >> $OUT/summary.jsonl; echo "$line" | cut -c1-160
}
eval_arm() {  # eval_arm ARM: serve the merged model, smoke test, tau2 test sets, then ARC with vLLM stopped
  local arm=$1 d=/job/merged_$1; mkdir -p $OUT/$arm
  [ -f $d/config.json ] || { echo "=== $arm: no merged model"; return 1; }
  serve $d $arm || { echo "=== $arm SERVE-FAIL"; return 1; }
  python3 $SS/smoke.py "$KW" > $OUT/$arm/smoke.json 2>&1; echo "smoke: $(head -c 400 $OUT/$arm/smoke.json)"
  evalrun $arm; arc_arm $arm $d
  rm -f "${d:?}"/*.safetensors  # free disk; config/tokenizer stay
}

# ---------- 3 build, 4 train ----------
build_fn() {
  python3 $SS/build.py $BASE $OUT/data/env_retail.json $OUT/data $OUT/day/results.json.gz $(ls $OUT/fix/[0-9]*.json.gz 2> /dev/null) || return 1
  [ -s $OUT/data/anchors.jsonl ] || { echo "=== anchors missing"; return 1; }
}
train_fn() {  # train_fn ARM
  kill_vllm
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python3 $SS/train.py $1 $BASE $OUT/data/night.jsonl $OUT/data/anchors.jsonl /job/merged_$1 2>&1 | grep -v "Loading weights" | tail -n 400
  local rc=${PIPESTATUS[0]}
  cp /job/merged_$1.log $OUT/train_$1.log 2> /dev/null; cp /job/merged_$1/train_info.json $OUT/train_info_$1.json 2> /dev/null
  [ $rc -eq 0 ] && grep -q "TRAIN DONE" /job/merged_$1.log
}
arcA0_fn() { arc_arm A0 $BASE; }
evalA0_fn() { serve $BASE base && evalrun A0; }   # shares the base server with the day and the retries
report_fn() { python3 $SS/analyze.py $OUT/summary.jsonl | tee $OUT/report.md; }

# ---------- run ----------
trap 'pkill -f "vllm serve" 2> /dev/null; tar czf $OUT.tgz -C $ROOT out && base64 -w0 $OUT.tgz > $ROOT/out.b64 && echo "=== packed $(stat -c %s $OUT.tgz) bytes"' EXIT
if pending day || pending fix || pending evalA0; then
  serve $BASE base || { echo "=== base SERVE-FAIL"; exit 1; }
  ( stage day day_fn; stage fix fix_fn ) &
  ( stage evalA0 evalA0_fn ) &
  wait
fi
stage arcA0 arcA0_fn
stage build build_fn
stage trainA1 train_fn A1
stage trainA2 train_fn A2
stage evalA2 eval_arm A2
stage evalA1 eval_arm A1
FORCE=1 stage report report_fn
echo "=== skillsleep done $(date -u +%FT%TZ) elapsed $(( $(date +%s) - START ))s"
