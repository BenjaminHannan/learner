#!/bin/bash
# RLAIF-2 on one CUDA GPU (Ben's PC, RTX 5070 Ti 16 GB, bf16). Same plan as the Kaggle rlaif-run2 kernel (rlaif/SPEC.md):
# eval base -> eval round-1 JOLT+ adapter -> GRPO 30 steps -> JOLT+ 30 steps -> evals at steps 10/20/30. Steps run in order; a failure is logged, the next step still runs.
# Needs: torch (CUDA), transformers, peft, anthropic; LEARNER_ANTHROPIC_API_KEY in env (training grades live; evals use Message Batches).
# Usage: bash rlaif/run2_pc.sh OUTDIR [ROUND1_JOLT_ADAPTER]
set -u
OUT=${1:?outdir}; R1=${2:-}
cd "$(dirname "$0")/.." || exit 1
mkdir -p "$OUT"
COMMON="--reward-v3 --lr 1e-4 --steps 30 --tasks-per-step 8 --group 4 --seed 0 --save-every 10 --gen-batch 8 --max-usd 14"
EVAL="--eval-only --eval-grade --gen-batch 4"
step() { local name=$1; shift; echo "=== $name start $(date -u +%FT%TZ)"; python -m rlaif.train "$@" > "$OUT/$name.log" 2>&1; echo "=== $name rc=$? $(date -u +%FT%TZ)" | tee -a "$OUT/status.tsv"; }
step eval_base $EVAL --outdir "$OUT/eval_base"
[ -n "$R1" ] && step eval_r1_jolt $EVAL --adapter "$R1" --outdir "$OUT/eval_r1_jolt"
step train_grpo --algo grpo $COMMON --outdir "$OUT/grpo"
step train_jolt --algo jolt_plus $COMMON --beta-t 0.001 --beta-s 0.1 --outdir "$OUT/jolt"
for arm in grpo jolt; do for s in 10 20 30; do
  [ -d "$OUT/$arm/adapter_step$s" ] && step eval_${arm}_$s $EVAL --adapter "$OUT/$arm/adapter_step$s" --outdir "$OUT/eval_${arm}_$s"
done; done
echo "=== RLAIF-2 DONE $(date -u +%FT%TZ)"
