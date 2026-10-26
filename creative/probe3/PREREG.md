# Probe-3: teach K2 to write tests the way Haiku does

Fixed 2026-10-26 ~10:25Z, before any training example is built or any model trained. Follows Probe-2 (sealed
26f4be281e): with the start state in view, Haiku-written tests picked the winning try 44.3% (AUROC .759) of 192 pools,
K2-written tests 36.5% (.661), K2 self-judge 34.4%. Probe-2's prereg named this next step: distil Haiku's tests.

## One change
K2 writes the tests exactly as in Probe-2 (same prompt with start state, 4 samples at T0.7, same pools, replay,
scoring, pickers, tie-breaks), but with a LoRA adapter trained to imitate Haiku's tests.

## Training data (never touches the 48 target tasks)
- Tasks: the 372 sandbox tasks not in Guess-1's target set (`target.json` T). The 48 target tasks are excluded from
  every step.
- Haiku (Batches, default sampling) writes 4 test sets per task with the Probe-2 prompt (submitted
  msgbatch_018QHDEwMzN2jvc4aQdZXyJS before this file was committed; no output was read).
- Keep a set only if it parses, has 2-6 checks, every check passes the sandbox validator, and every check holds on
  the end state of the task's reference plan. (The reference is used only to filter training data on non-target
  tasks; it is never seen by the writer.) Keep at most 2 sets per task, chosen at random (seed 0).
- Target text = the kept set as compact JSON {"checks": [...]}; prompt = the Probe-2 prompt, chat template k2_nothink.

## Training (fixed)
LoRA r 16, alpha 32, dropout 0.05 on all attention and MLP projections; lr 1e-4, cosine, 3% warmup; 2 epochs;
effective batch 16; loss on the answer tokens only; fp16 on a T4 or bf16 on newer cards; seed 0. No tuning on target
tasks; no early stopping on them. 10% of the training tasks are held out to report validation loss only.

## Pass marks (fixed now; on the same 192 pools)
- P1: PROBE-S (K2+LoRA) pick rate >= SELF + 5 points (>= 39.4%).
- P2: AUROC of the probe score >= 0.75.
PASS = P1 and P2. PROVED WRONG: PROBE-S <= Probe-2's K2 + 1 point (<= 37.5%): training added nothing that matters.
Otherwise INCONCLUSIVE.

## Diagnostics (do not decide)
Reference agreement of valid tests on the target tasks (Probe-2: K2 60.2%, Haiku 74.5%), validity rate, all-tie rate,
kept training sets / tasks.

## Caveats
The 192 pools come from 48 tasks, so the effective sample is near 48. Target and training tasks share scenario
families (written by the same generator), so a pass shows transfer within this sandbox, not to new kinds of jobs.

## If it passes
Probe-then-pick with a tuned K2 becomes the "many guesses" picker; the next test runs it end to end on fresh tasks
(12 tries + tests vs one try and vs self-judge), and on the Ben's-week jobs if they fit the check language.

## Cost
Haiku batch ~$0.26. One T4 (or a 4090) for ~1 h: training plus 192 generations.
