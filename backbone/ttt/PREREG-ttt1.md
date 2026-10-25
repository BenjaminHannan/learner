# TTT-1: test-time training on a puzzle's own examples (written 2026-10-25 ~21:55Z, before any TTT code or run)

Labels: shown / suggested / untested. Backbone v2 small tier only (K2-Horizon-3.7B). Not the card experiments (multistep / creative B2),
not the village model, not Sleep-B. Owner: thread "Make the model great at spotting patterns", branch claude/project-thread-9q2vwk.

## Why
Ben (2026-10-25 21:26Z): make the model "super good at pattern recognition". Puzzle patterns (a rule shown by a few input -> output
examples) are the classic test. Published (suggested, not checked here): test-time training, a few LoRA steps on the puzzle's own
examples before answering, is what lifted ARC-AGI-1 scores in 2024 (Akyurek et al. 2024; ARC Prize 2024 winners). In our own card
experiments the only thing that helped multistep puzzles was more self-practice nights (Hard 10 -> 26); TTT is the per-puzzle version of
that, done in seconds right before answering.

## Data
ARC-AGI-1 **evaluation** set (fchollet/ARC-AGI, data/evaluation, 400 tasks; not the training tasks, which thread "Let the model practice
puzzles, then sleep" uses). Grids written as digit rows, one row per line. Fixed rule: keep tasks whose full prompt (all demos, the first
test input, and its answer) is <= 2,000 tokens in K2's tokenizer, sort by task id, take the first 100. Only each task's FIRST test input
is scored. Exact grid match.

## Arms (each task starts from the same base weights; LoRA is thrown away after the task)
- **B (base):** K2-3.7B, thinking off (empty think block), greedy, no training.
- **T (test-time training):** LoRA rank 16, alpha 32, on attention q/k/v/o and MLP gate/up/down. Training examples from the task's own
  demos only: leave-one-out (each demo in turn is the question, the other demos are the examples) x 8 grid symmetries (identity, 3
  rotations, 2 flips, 2 transposes; one symmetry applied to every grid of the example). 48 steps, batch 1, lr 1e-4, AdamW, loss on the
  answer tokens only, fp16 base with fp32 LoRA and a dynamic loss scale. Then answer greedily.
- **C (equal-compute control):** exactly T's recipe, step count and seeds, but the training examples come from a DIFFERENT task (task
  k+1 in the sorted list; the last task uses the first). This tests whether the gain comes from this puzzle's own rule or from generic
  practice on the ARC format.

## Pass marks (fixed now)
- **T1 (TTT learns the puzzle's own pattern):** T solves >= 5 more of the 100 tasks than C, and exact McNemar on the paired T-vs-C
  outcomes gives p < 0.05.
- **Wrong if:** T <= C. Then the per-puzzle training adds nothing beyond format practice at this size; drop TTT for the small tier.
- Reported, not marked: T vs B, C vs B (format practice alone), solved tasks per grid size, seconds per task (T4) and the projected
  seconds per task on Ben's Mac.
- Expectation (not a mark): B 2-8 of 100; T - C between +3 and +15.

## Compute
Free: Kaggle 2x T4 (second account, through thread "Run experiments on Kaggle GPUs"), two lanes of 50 tasks, about 3-4 h. Exits before
11 h. No Vast.
