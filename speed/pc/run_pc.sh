#!/usr/bin/env bash
# PC (RTX 5070 Ti, sm_120, 16 GB) timing job for the expert-matmul fix and padding-free packing, < 1 h. Run from a checkout of branch
# claude/project-thread-b0qz6e:  bash speed/pc/run_pc.sh   ->  speed/pc/out/pc_step.json + logs.
# Own venv (~/speedvenv) so ~/vllmvenv is untouched. Real Qwen3.6-35B-A3B weights, only the first 4 layers (~9 GB of shards downloaded).
set -u
cd "$(dirname "$0")/../.."
OUT=speed/pc/out; mkdir -p $OUT
T0=$SECONDS
[ -f ~/learner-ops/PAUSE_OTHERS ] && { echo "PAUSE_OTHERS set; exiting"; exit 0; }
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv | tee $OUT/gpu.txt
if [ ! -x ~/speedvenv/bin/python ]; then
  python3 -m venv ~/speedvenv
  ~/speedvenv/bin/pip install -q -U pip
  ~/speedvenv/bin/pip install -q torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128   # same torch as the Vast boxes (sm_120 grouped_mm falls back there too)
  ~/speedvenv/bin/pip install -q transformers==5.20.2 peft==0.21.2 accelerate==1.15.0 flash-linear-attention==0.6.0 huggingface_hub hf_xet safetensors numpy
fi
PY=~/speedvenv/bin/python
$PY -c "import torch,transformers,triton;print('torch',torch.__version__,'tf',transformers.__version__,'triton',triton.__version__,torch.cuda.get_device_name(0))" | tee $OUT/env.txt
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# 0. expert-matmul micro-bench at real shapes (~3 min): which backend wins on sm_120
timeout 600 $PY speed/qwen36_step/bench_gmm.py --out $OUT/bench_gmm.json --dtype bfloat16 > $OUT/bench_gmm.log 2>&1
echo "gmm rc=$? after $((SECONDS-T0)) s"; tail -5 $OUT/bench_gmm.log
# 1. parity + speed on 4 real layers: baseline vs each expert-matmul backend, KL cache, packing (profiler on baseline only)
timeout 2400 $PY speed/qwen36_step/profile_step.py --layers 4 --steps 4 --warmup 2 --no-profile-variants \
  --variants baseline,fast_experts_bmm,fast_experts_split,fast_experts_triton,kl_cache+fast_experts,packed,all --out $OUT/pc_step.json --work ~/qwen36_step_work > $OUT/pc_step.log 2>&1
echo "step rc=$? after $((SECONDS-T0)) s"; grep -E '^\[' $OUT/pc_step.log
echo "=== PC SPEED DONE $((SECONDS-T0)) s"
