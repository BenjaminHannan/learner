# Reach-1: can the explorer solve jobs the model never solves by retrying?

Fixed 2026-10-25 ~00:55Z, before any run. Thread "Plan the creative model for v2". Plan and background:
/mnt/project-files/research/creative-v2/PLAN.md (Ben 00:38Z: wants a genuinely new way of thinking, not reshuffled answers).

## Setting (kept separate from tau2 and the village/puzzle models)
- Model: LiquidAI LFM2.5-8B-A1B, thinking off, served behind any OpenAI-compatible endpoint (mlx_lm.server,
  vLLM or llama-server). The serving build and quantization are logged in every result file.
- Jobs: the RLAIF practice-assistant sandbox (fake files/email/calendar/notes/reminders), all 420 tasks
  (rlaif tasks_train 320 + tasks_heldout 100, copied unchanged from branch claude/project-thread-7gkl2b).
  Success = every end-state check passes. Up to 6 turns per episode.
- Sampling: temperature 0.7, top_p 0.95 for every arm (diversity has to come from the method, not the sampler).

## Stages
1. Screen: 8 plain tries per task. Tasks with >= 1 success are "reachable" and leave the test.
2. Confirm: 56 more plain tries on the rest (64 total). Tasks with 0/64 are the HARD set. If HARD has fewer
   than 15 tasks, the test stops: report "the 8B already reaches almost everything here".
3. Arms on HARD, 16 tries each:
   - R+ (fair retry): the prompt shows 2 of the model's own failed transcripts for this task and says
     "these attempts did not complete the job; try a different approach." No check results are shown.
   - X (explorer), two moves, 8 tries each, same failed transcripts shown:
     - FLIP: one call asks the model to list the hidden assumptions its failed attempts made, pick one, and
       state the opposite as a new approach; the episode then runs with that approach in the system prompt.
       Each of the 8 tries flips a different assumption where the list allows.
     - BORROW: show the model's own successful transcript of a different task (from stage 1), chosen as the
       closest by word overlap among tasks of a DIFFERENT scenario type, labelled "a job you solved before
       that may have a similar shape". 8 tries use the 8 closest such tasks.
   - Reference answers, rubrics and check details are never shown to any arm.

## Pass marks
- P1 (new ideas exist): X cracks >= 5 HARD tasks (>= 1 success in its 16 tries).
- P2 (it's the method, not just seeing the failure): X cracked minus R+ cracked >= 3, and paired tasks
  where only X cracks outnumber tasks where only R+ cracks at least 2:1.
- P3 (wins are real): >= 2 of 3 replays of each X win, using the same approach text, succeed.
- PROVED WRONG: X cracks <= 1 HARD task, or X <= R+. Then prompting the model to restructure does not reach
  new solutions, and v2 builds new tools/chunks (trick 4) before more explorer work.
- Between the marks (2-4 cracked, or a gap of 1-2): inconclusive; a second sampling seed decides.
- Report per-move counts (FLIP vs BORROW) and per-scenario counts, but they don't decide pass/fail.

## Cost
No API calls (deterministic checks, no simulated user). Compute only: about 3,400 screen episodes plus up to
56 x HARD confirm episodes plus 48 x HARD arm episodes.
