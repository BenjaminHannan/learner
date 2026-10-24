# RLAIF-1: train a small model on sandboxed assistant tasks with Claude as grader

Ben's idea (2026-10-24): let the model do tasks while Claude grades it. Sonnet 5.5 sets the reward.
Arms: GRPO (baseline) vs JOLT+ (Ardywibowo, Dalal, Jiao, arXiv 2610.10447, "A Good Self-Teacher Meets the
Student Where They Are"). No official code yet; we implement from the published objectives (below).

## Pieces

1. `rlaif/sandbox.py`: pure-Python fake world (files, email, calendar, notes, reminders). No real disk, network
   or shell. Tools (OpenAI function schema, a subset of `data/assistant-sft/tools.json` in project files):
   read_file, write_file, list_dir, search_files, email_search, send_email, email_draft,
   calendar_list_events, calendar_create_event, notes_search, notes_append, set_reminder.
   `World.from_json(state)`, `world.call(name, args) -> str` (errors returned as text, never raised),
   `world.to_json()`.
2. `rlaif/checks.py`: end-state assertions, a small JSON DSL (file_exists, file_absent, file_contains,
   email_sent{to,subject_contains,body_contains}, no_email_sent, draft_exists, event_exists{title_contains,date,start},
   no_event_created, reminder_exists{text_contains,when_contains}, note_contains, reply_contains{any_of}).
   `run_checks(task, world, final_reply) -> list[bool]`.
3. `rlaif/make_tasks.py`: Sonnet 5.5 writes tasks (initial state, user request, checks, reference tool-call
   solution, short rubric for the soft part). Keep a task only if (a) the reference solution run in the sandbox
   passes every check and (b) the untouched world with an empty reply fails at least one check.
   Train set 320 tasks; held-out set 100 tasks from separate generation calls, never trained on.
   Scenario mix like the SFT set: single_tool, multi_step, parallel, clarify, confirm_irreversible,
   error_recovery, summarize_long, direct_answer.
4. `rlaif/grader.py`: Sonnet 5.5 (`claude-sonnet-5-5`) grades a transcript 0-10 against the rubric and returns a
   one-line critique. It sees the task, rubric and transcript, not the check results. Prompt-cached rubric
   header. 5% random slice also graded by `claude-opus-5-5` to measure agreement. Spend ledger with a hard stop.
5. `rlaif/train.py`: LoRA RL on Qwen3-1.7B (thinking off), multi-turn rollouts in the sandbox, loss only on
   model-written tokens. `--algo grpo|jolt_plus`.

## Reward (training)

r = 0.6 * (fraction of checks passed) + 0.4 * (Sonnet score / 10).

## JOLT+ (one set of weights, two roles)

Per task: the student sees the normal prompt. The teacher sees the same prompt plus a privileged block c:
the reference solution and Sonnet's critique of the worst student attempt in this group.

- Student samples G attempts, graded. Teacher samples G attempts with c, graded.
- A_S = r - mean(student group); A_T = r - mean(teacher group).
- Teacher term, on teacher attempts:  sum_t [ A_T * log pi(a_t | s_t, c) - beta_T * KL( pi(.|s_t,c) || sg pi(.|s_t) ) ]
- Student distillation, on student attempts: - beta_S * sum_t KL( pi(.|s_t) || sg pi(.|s_t,c) )   (full-vocab, reverse KL)
- Student reward term (the "+"), on student attempts: sum_t A_S * log pi(a_t | s_t)
- Maximize the sum. beta_T = 0.05, beta_S = 1.0 (paper does not publish values; these are our guesses).

GRPO arm: student term only (sum_t A_S * log pi), same tasks, same steps, same seed. Grader calls per step
are 2x for JOLT+; we report both per-step and per-grader-call curves.

## Preregistered pass marks (fixed 2026-10-24, before any training run)

Held-out = 100 tasks, check-only scoring (all checks pass = success), greedy decoding.
- "RL works": an arm's held-out success rises by >= 10 points over the untrained model.
- "JOLT+ beats GRPO": JOLT+ held-out success >= GRPO + 5 points at the same step count. Smaller gaps = tie.
- Grader-gaming alarm: train Sonnet score rises >= 15 points while held-out check success rises < 3 points.
- Proved wrong / stop: held-out success falls below the untrained model for either arm.
- Spot-check health: Sonnet vs Opus scores within 2 points on >= 80% of the slice.
