#!/usr/bin/env bash
# gpuq: name=skillsleep2
# gpuq: gpus=2
# gpuq: hours=16
# gpuq: owner=Test sleep that improves skills
# gpuq: retries=1
# gpuq: secrets=anthropic
# gpuq: commit=<SHA>
# Skill-Sleep 2 (skillsleep/PREREG-2.md): day, fix, forks, 6 trainings (C1-C3 x 2 seeds), 7 evals. GPU0 serves and evaluates, GPU1 trains (skillsleep/run_v2.sh).
# Needs ANTHROPIC_API_KEY (Haiku customer + judge, Sonnet critiques) and internet (HF, PyPI, GitHub). Results land in $GPUQ_OUT; venvs, tau2 and merged models in $WORK.
set -euo pipefail
cd "$GPUQ_SRC"
export OUT="$GPUQ_OUT"                                  # run_v2.sh keeps a done-marker per stage in $OUT, so GPUQ_ATTEMPT > 1 resumes where the last attempt stopped
export WORK="${SS2_WORK:-/tmp/ss2_${GPUQ_NAME:-skillsleep2}}"
export HF_HOME="${HF_HOME:-$WORK/hf}"                   # the box's shared cache when the queue sets one
mkdir -p "$OUT" "$WORK"
if [ "${GPUQ_ATTEMPT:-1}" -gt 1 ]; then echo "attempt $GPUQ_ATTEMPT: resuming; done stages: $(ls "$OUT/.done" 2> /dev/null | tr '\n' ' ')"; fi
bash skillsleep/run_v2.sh
