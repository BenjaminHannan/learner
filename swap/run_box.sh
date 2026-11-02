#!/usr/bin/env bash
# Swap-1 box job: serve each candidate backbone with vLLM and run the tau2 retail store test on it
# (tasks 0-39, 2 trials, Haiku 5.5 as customer + judge, same patched tau2 as scoreboard1 on the Mac).
# Needs ANTHROPIC_API_KEY in the box env (vast_swap.py create --with-key). Results: out/<arm>/ + out/summary.jsonl
set -u
ROOT=$(pwd); OUT=$ROOT/out; mkdir -p $OUT
exec > >(tee -a $OUT/run_box.log) 2>&1
ARMS=${ARMS:-k2_7b_nothink,k2_37b_nothink,k2_7b_low,k2_37b_low,lfm8b_nothink,qwen4b_nothink,qwen9b_nothink,k2_7b_medium}
TRIALS=${TRIALS:-2}; CONC=${CONC:-10}; ARM_MIN=${ARM_MIN:-80}
echo "=== swap1 start $(date -u +%FT%TZ) arms=$ARMS"
nvidia-smi --query-gpu=name,memory.total --format=csv

(apt-get update -qq && apt-get install -y -qq git curl) > /dev/null 2>&1; git --version
pip install -q -U uv 2>&1 | tail -1
uv pip install --system -q -U vllm 2>&1 | tail -3
python3 -c "import vllm, torch; print('vllm', vllm.__version__, 'torch', torch.__version__)"

git clone -q https://github.com/sierra-research/tau2-bench /job/tau2 && cd /job/tau2 && git checkout -q cc1df47 && git apply $ROOT/swap/tau2-judge-haiku.patch && echo "tau2 patched" || { echo "=== BB FAIL tau2 setup"; exit 1; }
uv venv -q /job/t2venv && UV_PROJECT_ENVIRONMENT=/job/t2venv uv sync -q 2>&1 | tail -2
unset ANTHROPIC_BASE_URL; export ANTHROPIC_API_BASE=https://api.anthropic.com
/job/t2venv/bin/python -c "import os; print('key set:', bool(os.environ.get('ANTHROPIC_API_KEY')))"
cd $ROOT

T=$ROOT/swap/templates
arm_cfg() {  # -> REPO, SERVE (extra vllm args), KW (chat_template_kwargs json), MAXTOK
  case $1 in
    k2_7b_nothink)  REPO=IFM/K2-Horizon-7B;   SERVE="--trust-remote-code --tool-call-parser k2_horizon --chat-template $T/k2_nothink.jinja"; KW='{}'; MAXTOK=4096 ;;
    k2_7b_low)      REPO=IFM/K2-Horizon-7B;   SERVE="--trust-remote-code --tool-call-parser k2_horizon --reasoning-parser k2_horizon --chat-template $T/k2_nothink.jinja"; KW='{"reasoning_effort":"low"}'; MAXTOK=16384 ;;
    k2_7b_medium)   REPO=IFM/K2-Horizon-7B;   SERVE="--trust-remote-code --tool-call-parser k2_horizon --reasoning-parser k2_horizon --chat-template $T/k2_nothink.jinja"; KW='{"reasoning_effort":"medium"}'; MAXTOK=16384 ;;
    k2_37b_low)     REPO=IFM/K2-Horizon-3.7B; SERVE="--trust-remote-code --tool-call-parser k2_horizon --reasoning-parser k2_horizon --chat-template $T/k2_nothink.jinja"; KW='{"reasoning_effort":"low"}'; MAXTOK=16384 ;;
    k2_37b_nothink) REPO=IFM/K2-Horizon-3.7B; SERVE="--trust-remote-code --tool-call-parser k2_horizon --chat-template $T/k2_nothink.jinja"; KW='{}'; MAXTOK=4096 ;;
    lfm8b_nothink)  REPO=LiquidAI/LFM2.5-8B-A1B; SERVE="--tool-call-parser pythonic --chat-template $T/lfm25_nothink.jinja"; KW='{}'; MAXTOK=4096 ;;
    qwen36_35b_awq_nothink) REPO=QuantTrio/Qwen3.6-35B-A3B-AWQ; SERVE="--tool-call-parser qwen3_coder --limit-mm-per-prompt {\"image\":0,\"video\":0}"; KW='{"enable_thinking":false}'; MAXTOK=4096 ;;
    qwen38_27b_awq_nothink) REPO=cyankiwi/Qwen3.8-27B-AWQ-INT4; SERVE="--tool-call-parser qwen3_coder --limit-mm-per-prompt {\"image\":0,\"video\":0}"; KW='{"enable_thinking":false}'; MAXTOK=4096 ;;
    qwen36_35b_bf16_nothink) REPO=Qwen/Qwen3.6-35B-A3B; SERVE="--tool-call-parser qwen3_coder --moe-backend triton --gdn-prefill-backend triton --max-num-seqs 32 --limit-mm-per-prompt {\"image\":0,\"video\":0}"; KW='{"enable_thinking":false}'; MAXTOK=4096 ;;
    qwen38_27b_bf16_nothink) REPO=Qwen/Qwen3.8-27B; SERVE="--tool-call-parser qwen3_coder --gdn-prefill-backend triton --max-num-seqs 32 --limit-mm-per-prompt {\"image\":0,\"video\":0}"; KW='{"enable_thinking":false}'; MAXTOK=4096 ;;
    qwen4b_nothink) REPO=Qwen/Qwen3.5-4B;     SERVE="--tool-call-parser qwen3_coder --limit-mm-per-prompt {\"image\":0,\"video\":0}"; KW='{"enable_thinking":false}'; MAXTOK=4096 ;;
    qwen9b_nothink) REPO=Qwen/Qwen3.5-9B;     SERVE="--tool-call-parser qwen3_coder --limit-mm-per-prompt {\"image\":0,\"video\":0}"; KW='{"enable_thinking":false}'; MAXTOK=4096 ;;
    *) return 1 ;;
  esac
}

serve() {  # $1 arm, $2 extra flags
  pkill -f "vllm serve" 2>/dev/null; pkill -f EngineCore 2>/dev/null; sleep 5
  for i in $(seq 1 30); do  # the engine child process can keep the GPU memory after the API server dies
    [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)" -lt 2000 ] && break
    pkill -9 -f "vllm|EngineCore" 2>/dev/null; sleep 5
  done
  vllm serve $REPO --served-model-name m --port 8000 --dtype ${DTYPE:-bfloat16} --max-model-len ${MAXLEN:-49152} --gpu-memory-utilization ${GPU_UTIL:-0.90} \
    --enable-auto-tool-choice $SERVE $2 > $OUT/$1/vllm.log 2>&1 &
  for i in $(seq 1 180); do
    curl -s localhost:8000/v1/models >/dev/null 2>&1 && return 0
    pgrep -f "vllm serve" >/dev/null || return 1
    sleep 10
  done
  return 1
}

for ARM in ${ARMS//,/ }; do
  arm_cfg $ARM || { echo "=== unknown arm $ARM"; continue; }
  mkdir -p $OUT/$ARM; echo "=== ARM $ARM $REPO start $(date -u +%T)"
  if ! serve $ARM ""; then
    echo "=== $ARM native vllm failed; errors:"; grep -E "Error|error" $OUT/$ARM/vllm.log | grep -v "^ *File" | tail -6 | cut -c1-300; cp $OUT/$ARM/vllm.log $OUT/$ARM/vllm_native.log
    serve $ARM "--model-impl transformers" || { echo "=== $ARM SERVE-FAIL"; tail -20 $OUT/$ARM/vllm.log; continue; }
  fi
  python3 $ROOT/swap/smoke.py "$KW" > $OUT/$ARM/smoke.json 2>&1; echo "smoke: $(head -c 600 $OUT/$ARM/smoke.json)"
  ARGS=$(python3 -c "import json,sys; print(json.dumps({'api_base':'http://localhost:8000/v1','api_key':'none','max_tokens':int(sys.argv[2]),'num_retries':2,'extra_body':{'chat_template_kwargs':json.loads(sys.argv[1])}}))" "$KW" $MAXTOK)
  T0=$(date +%s)
  ( cd /job/tau2 && timeout $((ARM_MIN*60)) /job/t2venv/bin/tau2 run --domain retail --agent-llm openai/m --agent-llm-args "$ARGS" \
      --user-llm anthropic/claude-haiku-5-5 --user-llm-args '{"num_retries": 6}' \
      --task-ids $(seq -s ' ' 0 39) --num-trials $TRIALS --max-concurrency $CONC --save-to swap1_$ARM ) > $OUT/$ARM/tau2.log 2>&1
  echo "tau2 rc=$? $(( $(date +%s) - T0 ))s"
  R=/job/tau2/data/simulations/swap1_$ARM/results.json
  [ -f $R ] || R=$(ls -d /job/tau2/data/simulations/swap1_$ARM* 2>/dev/null | head -1)/results.json
  if [ -f "$R" ]; then
    python3 $ROOT/swap/summarize.py "$R" $ARM $(( $(date +%s) - T0 )) >> $OUT/summary.jsonl
    python3 $ROOT/swap/classify.py "$R" > $OUT/$ARM/classify.txt 2>&1
    gzip -c "$R" > $OUT/$ARM/results.json.gz
    echo "=== RESULT $(tail -1 $OUT/summary.jsonl)"
  else
    echo "=== $ARM no results.json"; tail -20 $OUT/$ARM/tau2.log
  fi
  grep -E "Error|error" $OUT/$ARM/vllm.log | tail -3
done
pkill -f "vllm serve"
tar czf $OUT.tgz -C $ROOT out && base64 -w0 $OUT.tgz > $ROOT/out.b64 && echo "=== packed $(stat -c %s $OUT.tgz) bytes"
echo "=== swap1 done $(date -u +%FT%TZ)"
