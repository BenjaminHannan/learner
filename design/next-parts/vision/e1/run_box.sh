#!/bin/bash
# Runs on the rented vast.ai box (no ssh needed): fetch code from the public branch, run E1, print results to the log.
BR=${E1_BRANCH:-claude/project-thread-7pb58a}
RAW=https://raw.githubusercontent.com/BenjaminHannan/learner/$BR/design/next-parts/vision
mkdir -p /work/vision/e1 && cd /work/vision
curl -fsSL $RAW/vision_adapter.py -o vision_adapter.py && curl -fsSL $RAW/e1/e1.py -o e1/e1.py || { echo "FETCH_FAILED"; exit 1; }
cd e1; export E1_OUT=/work/out HF_HUB_DISABLE_PROGRESS_BARS=1
pip install -q -U "transformers>=4.56" accelerate sentencepiece pillow 2>&1 | tail -2
nvidia-smi --query-gpu=name,memory.total --format=csv; python -c "import torch,transformers;print('torch',torch.__version__,'tf',transformers.__version__)"
set -o pipefail
python e1.py prep 2>&1 | grep -v Warning | tail -20 || { echo "PREP_FAILED"; exit 1; }
# smoke: 40 steps of one arm into a scratch dir, reusing the prepared data
mkdir -p /work/smoke && cp /work/out/* /work/smoke/ && E1_OUT=/work/smoke E1_STEPS=40 python e1.py train --arms real --seeds 0 2>&1 | tail -15 || { echo "SMOKE_FAILED"; exit 1; }
echo SMOKE_OK
python e1.py train 2>&1 | grep -v Warning
python e1.py report
echo E1_DONE
