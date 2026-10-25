# Guess-1 harness

Runs `PREREG.md` (do not edit it): do prompts that ask for many different guesses (LIST, MENU) crack more RLAIF-sandbox jobs than plain
retries (IND) or a hotter sampler (HOT)? Model: K2-Horizon-3.7B, thinking off. Reuses `../reach1` (client, episode, Store, `rlaif_copy/`).
Reach-1 got one optional hook: `client.chat(..., **sampling)` and `run_episode(..., sampling=None)`; defaults unchanged.

## Install and test
    pip install httpx pytest
    python -m pytest creative/guess1/tests creative/reach1/tests -q

## Serve
Mac:

    mlx_lm.server --model mlx-community/K2-Horizon-3.7B-4bit --port 8080

Linux (vLLM; `k2_nothink.jinja` is the template from branch `origin/claude/project-thread-16ok47`, `swap/templates/k2_nothink.jinja`; it defaults to no thinking):

    vllm serve <K2-Horizon-3.7B> --port 8080 --enable-auto-tool-choice --tool-call-parser k2_horizon \
      --reasoning-parser k2_horizon --chat-template creative/guess1/k2_nothink.jinja

With the swap template no extra body is needed. With the stock template, switch thinking off per request, e.g.
`--extra-body '{"chat_template_kwargs": {"reasoning_effort": "none"}}'` (the template reads `reasoning_effort`, default `none` after the patch;
check the stock template for its switch). If the server does not return `tool_calls`, reach1's client parses `<tool_call>{json}</tool_call>` and
LFM text; K2's own XML call format is NOT parsed client-side, so the server's tool-call parser must be on.

## Run (from `creative/guess1`)
    python run.py all --base-url http://127.0.0.1:8080/v1 --model <name> --out out/ --concurrency 16

Stages (each appends to `out/results.jsonl`, skips finished (task_id, arm, try_idx); rerun the same command after a crash):

- `screen`: 8 plain tries on the 210-task subset (every second task in file order).
- `pick`: writes `target.json` (T = 0-3 of 8 successes, first 48); if |T| < 20 it records the stop message and later stages refuse to run.
- `arms`: IND, HOT, LIST, MENU, 12 tries each on T (LIST sequential per task, tasks in parallel; menus cached in `menu.json`).
- `topup`: IND extra plain tries (cap 16) until LIST and MENU generated tokens are within 15% of IND's.
- `report`: `report.json` and `report.md` (all metrics, P1-P4, verdict).
- `all`: all of it. `--seed 2` re-runs Stage 2 + top-up on the same T if the verdict is INCONCLUSIVE; `report` then sums both seeds with doubled marks.
- `--limit N` is a debug subset (applied before taking every second task).

`out/run_meta.json` logs `/v1/models`, sampler settings, whether the server returned 2xx for `min_p` and `seed` (HOT drops `min_p` if not;
a server can still ignore it silently), and the seed formula `seed*100000 + crc32(task|arm|try) % 100000`; each record stores its seed and sampling.
