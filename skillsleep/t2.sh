#!/usr/bin/env bash
# One patched tau2 run against the local vLLM. usage: t2.sh NAME DOMAIN SPLIT TRIALS CONC TIMEOUT_S [more tau2 args]   (env ARGS = agent llm args json)
name=$1; dom=$2; split=$3; trials=$4; conc=$5; to=$6; shift 6
cd /job/tau2 && timeout -k 30 $to /job/t2venv/bin/tau2 run --domain $dom --agent-llm openai/m --agent-llm-args "$ARGS" \
  --user-llm anthropic/claude-haiku-5-5 --user-llm-args '{"num_retries": 6}' \
  --task-split-name $split --num-trials $trials --max-concurrency $conc --save-to $name "$@" < /dev/null
