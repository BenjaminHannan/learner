#!/usr/bin/env bash
# Stage B: same 40 retail tasks (ids 0..39, numeric order), agent = local OpenAI-compatible server,
# user simulator + NL judge = claude-haiku-5-5 on api.anthropic.com. 1 trial.
# Usage: LEARNER_ANTHROPIC_API_KEY=sk-ant-... ./run_local.sh HOST:PORT MODEL_NAME [SAVE_NAME] [CONCURRENCY]
#   llama.cpp:  llama-server -m model.gguf --port 8080 --jinja -c 32768     (--jinja is needed for tool calls)
#   mlx:        mlx_lm.server --model <hf-or-path> --port 8080
#   then:       ./run_local.sh localhost:8080 qwen3.6-35b-a3b qwen36
# Setup once:  git clone https://github.com/sierra-research/tau2-bench && (cd tau2-bench && git checkout cc1df47 && git apply ../patches/tau2-judge-haiku.patch) && uv venv .venv && cd tau2-bench && UV_PROJECT_ENVIRONMENT=../.venv uv sync
# NOTE: tau2-bench/ here is patched (judge models -> claude-haiku-5-5, JSON-fence parsing); use this copy.
set -euo pipefail
HOSTPORT=${1:?HOST:PORT}; MODEL=${2:?model name}; SAVE=${3:-local_$MODEL}; CONC=${4:-2}
cd "$(dirname "$0")"
unset ANTHROPIC_BASE_URL                      # some sandboxes set a non-Anthropic proxy here
export ANTHROPIC_API_KEY="${LEARNER_ANTHROPIC_API_KEY:?set LEARNER_ANTHROPIC_API_KEY}"
export ANTHROPIC_API_BASE=https://api.anthropic.com
cd tau2-bench
# Local agent args: no temperature unless you want it (add e.g. "temperature":0.6 to the JSON).
../.venv/bin/tau2 run --domain retail \
  --agent-llm "openai/$MODEL" \
  --agent-llm-args "{\"api_base\":\"http://$HOSTPORT/v1\",\"api_key\":\"none\"}" \
  --user-llm anthropic/claude-haiku-5-5 --user-llm-args '{}' \
  --task-ids $(seq -s ' ' 0 39) --num-trials 1 --max-concurrency "$CONC" --save-to "$SAVE"
# Score: python3 ../merge.py (edit run names) or read the Pass^1 line; DB-match is the prereg success metric.
