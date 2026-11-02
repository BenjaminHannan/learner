#!/usr/bin/env bash
# gpuq: name=recallread-stage1
# gpuq: priority=60
# gpuq: gpus=1
# gpuq: hours=11
# gpuq: owner=Close the diary search gap on the real model
# gpuq: retries=1
# gpuq: commit=FILL_IN_FULL_SHA   # must contain sleep2/recallread/ AND backbone/ at a7ed69d79d (merge that commit into the branch first), else the fallback below fetches it
# gpuq: needs=recallread/frozen/
# Recall-then-read, stage 1 (INVENT-1.md, Pick 2). Keyless. Two phases on ONE 4090:
#   1. train the ab_ob_b4_nb sleep LoRA on K2-Horizon-3.7B (bf16) on the Week-2 world, seeds 1 and 2, with the project's sleepb.py (about 2.5-3.5 h each on a 4090);
#   2. run arms D0-D4, R, R+D3, R_tau on the frozen items with per-request adapter on/off (about 1-2 h).
# Estimated 6.5-9 h; limit 11. Resumable: finished seeds / arm files in $GPUQ_OUT are skipped on attempt 2.
# $GPUQ_FILES/recallread/frozen/ must hold: items.json items.sha256 week2.json alias_table_full.json alias_table_W.json
set -euo pipefail
cd "$GPUQ_SRC"
exec > >(tee -a "$GPUQ_OUT/run.log") 2>&1
echo "== recallread attempt ${GPUQ_ATTEMPT:-1} $(date -u +%FT%TZ) commit $(git rev-parse HEAD 2>/dev/null || echo ?)"
nvidia-smi --query-gpu=name,memory.total --format=csv || true
unset LEARNER_ANTHROPIC_API_KEY ANTHROPIC_API_KEY || true
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True TOKENIZERS_PARALLELISM=false
SEEDS="${RR_SEEDS:-1 2}"
OUT="$GPUQ_OUT"; mkdir -p "$OUT"

# private venv on top of the shared one (torch from the image); pins are the ones sleepb was run against (backbone/requirements.txt)
VENV=/tmp/recallread-venv
[ -x $VENV/bin/python ] || python3 -m venv --system-site-packages $VENV
$VENV/bin/pip install -q 'transformers==5.20.2' 'peft==0.21.2' 'accelerate==1.15.0' 'datasets>=2.19'
export PATH=$VENV/bin:$PATH
python - <<'PY'
import torch, transformers, peft
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "transformers", transformers.__version__, "peft", peft.__version__)
assert torch.cuda.is_available(), "no CUDA"
assert transformers.__version__ == "5.20.2" and peft.__version__ == "0.21.2", "version pins not in effect"
PY

# the Sleep-B code (branch claude/project-thread-cqc4bi, pinned commit). Use the checkout if it is byte-identical, else fetch exactly that commit.
PIN=a7ed69d79d9ca928bc77b577c2912c6655474ad0
SLEEPB_SHA=0ee7c88c10a7650b8b840ada5f2b3fa553746ba02e3e01f39f2b27fcfc168fc2
TRAIN_SHA=8c9a828235baa97521e545da058788c4b82a3e35c171de53770c672747af1763
ok() { [ -f "$1/sleep/brain/sleepb.py" ] && [ "$(sha256sum "$1/sleep/brain/sleepb.py" | cut -d' ' -f1)" = "$SLEEPB_SHA" ] && [ "$(sha256sum "$1/train.py" | cut -d' ' -f1)" = "$TRAIN_SHA" ]; }
if ok "$PWD/backbone"; then BB="$PWD/backbone"
else
  rm -rf /tmp/rr-bb && mkdir -p /tmp/rr-bb
  # shipped copy first (git archive of $PIN, in needs=), then a git fetch
  if [ -f "$GPUQ_FILES/recallread/frozen/backbone-a7ed69d.tgz" ]; then tar -xzf "$GPUQ_FILES/recallread/frozen/backbone-a7ed69d.tgz" -C /tmp/rr-bb
  else (git fetch -q origin "$PIN" || git fetch -q origin claude/project-thread-cqc4bi) && git archive "$PIN" backbone | tar -x -C /tmp/rr-bb || true; fi
  if ok /tmp/rr-bb/backbone; then BB=/tmp/rr-bb/backbone; else echo "GPUQ-STOP: Sleep-B code at $PIN not available; merge it into the job commit"; exit 1; fi
fi
echo "backbone: $BB"
export RR_BACKBONE="$BB"

FR="$GPUQ_FILES/recallread/frozen"
for f in items.json items.sha256 week2.json alias_table_full.json alias_table_W.json; do test -f "$FR/$f" || { echo "GPUQ-STOP: $FR/$f missing"; exit 1; }; done
[ "$(sha256sum "$FR/items.json" | cut -d' ' -f1)" = "$(cut -d' ' -f1 "$FR/items.sha256")" ] || { echo "GPUQ-STOP: items.json hash mismatch"; exit 1; }
[ "$(sha256sum "$FR/week2.json" | cut -d' ' -f1)" = "70db7146ed59d10cbd0d2e8d7a6fc0e245d4b07ec57add0c793db1fdff006e5b" ] || { echo "GPUQ-STOP: week2.json is not the pinned Week-2 world"; exit 1; }

echo "== phase 1: sleep (seeds: $SEEDS) $(date -u +%FT%TZ)"
python -m sleep2.recallread.train_sleep --backbone "$BB" --week "$FR/week2.json" --out "$OUT" --seeds $SEEDS

echo "== phase 2: eval $(date -u +%FT%TZ)"
ADAPT=(); for s in $SEEDS; do ADAPT+=(--adapter "$s=$OUT/sleep/s$s/adapter"); done
# 20-item smoke first (fast fail), then the full run; run_eval skips finished arm files, so the smoke files are removed before the full run
python -m sleep2.recallread.run_eval --frozen "$FR" --out "$OUT/smoke" --limit 20 "${ADAPT[@]}" --arms D0 R D3
rm -rf "$OUT/smoke"
python -m sleep2.recallread.run_eval --frozen "$FR" --out "$OUT" "${ADAPT[@]}"
echo "== done $(date -u +%FT%TZ); results in $OUT/results/recallread (grade here afterwards: grade.py, stats.py, report.py)"
