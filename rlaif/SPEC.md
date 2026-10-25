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

## Numerical checks

- Softmax Cancellation/Collapse (arXiv 2610.31642) checked 2026-10-24, PR #109: not reachable in _lp_kl; no change to numbers.

## Round 2 notes (not part of the preregistered RLAIF-1 marks)

- Held-out is check-only, so grader bias cannot move the headline number; grader calibration (position/length bias, kappa vs labels) matters for the training signal only.
- With a base near 25/100, a 5-10 point gap needs ~300 held-out tasks and 3 training seeds per arm (greedy eval has no eval-seed noise). Source: /mnt/project-files/research/dopamine-rlaif-grader.md.
- JOLT details are verified from the arXiv paper itself (Table 3, Appendix A.1), not only press coverage.

## RLAIF-1 result (Kaggle 2x T4, fp16, 20 steps, 2026-10-25)

Held-out success: base 25/100, GRPO@20 25/100 (pass mark +10 not met). JOLT+@20 eval OOMed; re-eval pending.
Diagnosis (from eval_*.jsonl and log.jsonl, rlaif/kaggle-run1 in project files):
- Say-instead-of-do: 45/100 base episodes end on turn 1 with "Let me check..." and no tool call; GRPO raised this to 71/100.
  Doing nothing earned check credit (no_email_sent etc. pass on an untouched world): base no-tool episodes got reward 0.32 vs 0.37 for tool use, so the cheap, safe narration was nearly as good.
- Updates were tiny for GRPO (grad norm mean 0.09 at lr 1e-5, clip 1.0). JOLT+ grad norm mean 4.4, dominated by the KL terms (pg terms ~1e-4) with beta_S=1.0, beta_T=0.05.
- Paired by step (same tasks), JOLT+ train success tracked GRPO for 15 steps, then dipped at steps 16 and 20.

## RLAIF-2 (preregistered 2026-10-25, before running)

Changes vs RLAIF-1, applied to both arms: `--reward-v2` (credit only for checks that need action; any failed don't-do check zeroes the reward; Sonnet scales action credit 0.7-1.0; an untouched world now scores 0.03 vs 0.21 before), `--lr 1e-4`, 30 steps. JOLT+ also takes the paper's `--beta-t 0.001 --beta-s 0.1`. Same tasks, seed 0, one seed (a limit: differences under ~8 points are within noise).
Held-out evals at steps 10, 20, 30 (check-only, keyless).
- RL works: an arm's held-out success at step 30 >= 35/100 (base 25).
- JOLT+ beats GRPO: >= GRPO + 5 at step 30.
- Narration guard: held-out turn-1 no-tool endings must not exceed base (45/100); if they do, the reward fix failed.
- Proved wrong: held-out success < 25 for an arm at step 30, or train reward rises while held-out success falls between steps 10 and 30 (gaming).
