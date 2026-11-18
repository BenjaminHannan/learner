# Scoreboard-1 Stage A results (2026-10-24)

Labels: shown = measured here; suggested = inferred; untested = not run.

## Setup (shown)
tau2-bench 2.0 (commit cc1df47), retail, tasks 0..39 (numeric order; the file has 114), 1 trial, agent and user both
`anthropic/claude-haiku-5-5`, no temperature / thinking args (`--agent-llm-args '{}'`), litellm hit https://api.anthropic.com
(checked via response api_base; ANTHROPIC_BASE_URL unset). Concurrency 8. Vendored copy in `tau2-bench/` with 3 patches:
(1) NL-assertion judge gpt-5.4-mini -> claude-haiku-5-5 (no OpenAI key; 112 of 114 retail tasks use it),
(2) semantic-communicate judge gpt-5.5 -> claude-haiku-5-5, (3) strip ```json fences before parsing the judge reply.
Note: tau2 2.0 is not comparable with the 1.x leaderboard (README); judge is Haiku, not GPT.

## Score (shown)
**29/40 = 72.5% pass^1** (reward = 1). DB-match was also 29/40, so no task failed on the NL judge alone.
Merge: 36 sims from the main run + 4 reruns (tasks 4,19,29,38) after crashes; tasks 19 and 38 failed on rerun.
Raw: `tau2-bench/data/simulations/stageA*/results.json`; `merge.py` recomputes.

## Crashes (shown)
First pass: **4/40 crashed** (tasks 4,19,29,38), all "Expecting value: line 1 column 1" = Haiku-as-judge wrapped JSON in
code fences, i.e. caused by my judge swap, fixed by patch 3. Reruns then hit Anthropic 429s (2M input-tokens/min org limit,
probably shared with another worker); 2 more reruns at lower concurrency finished all 4. No crash from the agent, tool-call
parsing, or the user simulator. Strict reading of A1 (>=38/40 in one pass): first pass 36/40 = FAIL; after the
one-line fix and reruns 40/40 ran = pass. Both stated.

## Failure classes (shown; 11 of 11 failed transcripts read, 10 required)
- Agent error, 10: 0 and 1 (never offered "Google Assistant" for "Google Home", so partial/no exchange), 5 (exchanged lamp
  after one confirmation; user then wanted a return, blocked by one-action rule), 19 (did exchange first, which blocked
  the more valuable return), 20 (picked a wrong keyboard variant), 27 (return then exchange fails because the return changed the order status),
  31 (returned the tablet instead of the sneaker, no cancel), 34 (used profile address the user never gave), 38 (cancel
  reason chosen by agent "ordered by mistake" vs gold "no longer needed"; plus a failed lookup), 39 (did not update address).
- User-sim misbehaving, 1: task 11 (user was told to swear then accept original-payment refund; instead demanded a human).
- Harness: 0 tool-call parsing errors. One latent upstream bug seen in task 20: `modify_pending_order_items` reuses the last
  `variant` in its second loop, so every modified item gets the last item's price/options (src/tau2/domains/retail/tools.py ~l.583).
  It did not cause that failure (wrong item id already), but can distort multi-item modify tasks; gold replay has it too.
- Verdict on "mostly harness vs agent": mostly agent errors (suggested; one reader, me).

## Published comparison numbers
- Qwen3.6-35B-A3B card https://huggingface.co/Qwen/Qwen3.6-35B-A3B : no tau2 retail. Lists **TAU3-Bench 67.2**
  (Qwen3.5-35B-A3B 68.9), official user model gpt-5.2 low effort. Not retail, not comparable.
- Qwen3.5-4B card https://huggingface.co/Qwen/Qwen3.5-4B : **TAU2-Bench 79.9** (Qwen3.5-9B 79.1), single number, no domain
  split; airline evaluated non-officially. No retail number.
- taubench.com leaderboard (https://taubench.com): shows combined tau2 text only, e.g. Qwen3.5-397B-A17B 87.9, Claude Opus 4.5 85.3;
  no retail-only, no Haiku (fetch of the front page only; full leaderboard not browsed).
- Third-party aggregator (unverified, not Anthropic): Claude Haiku 4.5 tau2 retail 83.2 (https://benchmarklist.com/benchmarks/tau2_bench_retail/
  via search snippet; I did not open the page). No published Haiku 5.5 number found.
- tau2-bench README: no per-model retail table.

## Spend
Tracked tokens on the 40 kept sims: 5.09M in / 0.14M out = **$0.58** at $0.10/$0.50 per M. Not tracked: smoke (2 sims, ~0.03),
discarded crashed/retried sims and judge calls (est. another $0.5-1.0). Estimated total **under $2**, far below the $5 stop (estimate; confirm in the Anthropic console).

## Verdicts
- A1 (runs end to end, no harness crashes on >=38/40): **first pass FAIL (36/40), after judge-parser fix + reruns 40/40 ran.**
  The "wrong if >2 crash" clause technically triggered, but the cause was my judge substitution, not tau2 or the agent.
  Fair reading (suggested): ruler works; keep patch 3 for Stage B. Rate limits need concurrency <= 4.
- A2 (within 15 pts of published closest Claude): **no official published retail number for Haiku 5.5 -> report only.**
  Against the unverified third-party Haiku 4.5 figure 83.2, gap = 10.7 pts (would be within 15; suggested only, different
  model, tau2 version and judge).
- Wrong-if clause "failures mostly harness": not triggered (10/11 agent errors).
- Untested: Stage B, trial-to-trial variance (task 0 passed in the 2-task smoke and failed in Stage A, so noise on 40 tasks is large, roughly +/-7 pts per sd).

## Stage B, first local model (2026-10-24 ~08:10Z, run by the backbone thread on Ben's M1 Pro)
`LiquidAI/LFM2.5-24B-A2B-MLX-4bit`, thinking on, `mlx_lm.server --max-tokens 8192` (the default 512 truncates its thinking),
same 40 retail tasks, Haiku 5.5 as the customer and judge, concurrency 2, about 5 min per task. File: `sims/lfm25_think_results.json`
(sha256 77e0c258c5d1...).
- **Shown:** reward 1 on **29/40 = 72.5% pass^1**, the same as Claude Haiku 5.5 as the agent (29/40). The backbone thread
  reports DB match on 30/40 and 0 harness errors.
- **Shown:** the two agents fail different tasks. Haiku fails 0,1,5,11,19,20,27,31,34,38,39 and LFM fails
  3,5,11,13,16,20,21,23,31,32,37. They share only 4 (5, 11, 20, 31), so 36/40 tasks are solved by at least one of them.
- Suggested: one trial per task and 40 tasks means a ~7-point standard error, so "tied with Haiku" is the honest reading.
  Low overlap means a second try or a check-and-retry step could add points. Untested.
- The thinking-off run stopped at 4/40 when the Mac disk filled.
