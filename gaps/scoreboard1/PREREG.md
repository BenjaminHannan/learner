# Scoreboard-1: a ruler for real assistant work (pre-registration, 2026-10-24 ~02:45Z)

Labels: shown / suggested / untested. Not the village model, not the card experiments.

## Why
Every thread scores its own toy (village quiz, puzzles, GSM, PopQA). Nothing measures whether a change makes the
MacBook assistant better at a job: several turns with a person, calling tools, following a policy, finishing the task.

## Ruler
tau2-bench (Sierra), retail domain: a simulated customer asks for returns, exchanges or address changes; the agent
has the store's tools and policy; success = the final database state matches the gold state (pass^1).
The simulated customer is `claude-haiku-5-5` (effort low) in every run, so only the agent changes between runs.
The agent is anything with an OpenAI-compatible endpoint (llama.cpp / mlx_lm.server on Ben's PC or Mac) or Claude.

## Stage A (now, Claude API only): does the ruler work?
- Agent `claude-haiku-5-5` on the first 40 retail tasks (task ids sorted), 1 trial each.
- A1 runs end to end with no harness crashes on >= 38/40 tasks.
- A2 the score lands within 15 points of tau2's published retail number for the closest published Claude model,
  if one exists (otherwise report only, no pass mark).
Wrong if more than 2 tasks crash, or failures are mostly harness errors (bad tool-call parsing) rather than agent errors
(checked by reading 10 failed transcripts).

## Stage B (when the PC or Mac is free): first real numbers
Qwen3.5-4B and Qwen3.6-35B-A3B as the agent on the same 40 tasks, local server. Pass: the 35B-A3B lands within 10 points
of the score on its Hugging Face model card (if listed), which shows our local setup is not handicapping it.
This becomes the scoreboard every v2 mechanism (notebook, sleep, tools, cascade) is judged on.

Cost cap Stage A: $5 of Claude API credit.
