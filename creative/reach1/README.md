# Reach-1 harness

Runs the experiment in `PREREG.md` (do not edit it): can the explorer moves (FLIP, BORROW) solve RLAIF-sandbox jobs that
plain retrying never solves? Model: LFM2.5-8B-A1B, thinking off, behind any OpenAI-compatible server. No GPU code lives here.

Files: `client.py` (HTTP client, tool-call parsing), `episode.py` (one episode), `run.py` (stages, resume, report),
`tests/test_reach1.py` (no network), `rlaif_copy/` (sandbox, checks, 420 tasks; unchanged).

## Install
    pip install httpx pytest
    python -m pytest tests -q

## Mac (mlx_lm)
    mlx_lm.server --model <path-to-LFM2.5-8B-A1B-mlx> --port 8080
    python run.py all --base-url http://127.0.0.1:8080/v1 --model <name> --out out/

## Linux GPU
vLLM:

    vllm serve LiquidAI/LFM2.5-8B-A1B --port 8080 --enable-auto-tool-choice --tool-call-parser <parser for LFM2.5>
    python run.py all --base-url http://127.0.0.1:8080/v1 --model LiquidAI/LFM2.5-8B-A1B --out out/ --concurrency 32

llama-server (GGUF):

    llama-server -m LFM2.5-8B-A1B-Q8_0.gguf --port 8080 --jinja -np 8 -c 65536 -ngl 99
    python run.py all --base-url http://127.0.0.1:8080/v1 --model lfm --out out/

If the server does not return `message.tool_calls`, the client parses LFM2.5 text (`<|tool_call_start|>[fn(a="x")]<|tool_call_end|>`)
and `<tool_call>{json}</tool_call>` itself.

## Subcommands
`screen` (8 plain tries/task), `confirm` (tries 8..63 on tasks with 0 successes), `hard` (writes `hard.json`), `arms` (R+ x16,
FLIP x8, BORROW x8 on HARD), `replay` (3 reruns per X-cracked task, same extra block), `report` (`report.json`, `report.md`),
`all` (all of it; stops and records it if HARD < 15). Everything appends to `out/results.jsonl` and skips finished
(task_id, arm, try_idx), so rerun the same command after a crash. `--concurrency N` (default 8), `--limit N` for a debug subset.
`out/run_meta.json` records CLI args and the server's `/v1/models`; `out/flip.json` caches the FLIP assumption lists.
